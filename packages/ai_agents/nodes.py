"""
LangGraph Agent 节点函数
包含 4 个核心节点：analyze_intent, retrieve_items, generate_advice, format_output
"""

import os
import time
import logging
from typing import Dict, List, Optional, Generator, Any
from pathlib import Path

from openai import OpenAI, APITimeoutError, APIError, RateLimitError

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from packages.ai_agents.state import AgentState
from packages.ai_agents.wardrobe_client import wardrobe_client
from packages.utils.bazi_calculator import (
    calculate_bazi,
    infer_elements_from_text,
    merge_recommendations,
)
from packages.utils.scene_mapper import (
    extract_scene_from_text,
    get_scene_elements,
    get_color_by_element,
    build_search_query,
)
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

logger = logging.getLogger(__name__)

# ============================================================
# LLM 配置与重试机制
# ============================================================
# 默认重试参数
DEFAULT_MAX_RETRIES = 3
DEFAULT_MIN_WAIT = 2.0  # 秒
DEFAULT_MAX_WAIT = 10.0  # 秒


def get_llm_client(timeout: int = 60) -> OpenAI:
    """
    获取阿里百炼千问客户端
    
    Args:
        timeout: 请求超时时间（秒）
    """
    return OpenAI(
        api_key=settings.dashscope_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout=timeout,
        max_retries=0,  # 我们自己实现重试
    )


def call_llm_with_retry(
    client: OpenAI,
    messages: List[Dict],
    model: str,
    max_tokens: int = 300,
    stream: bool = False,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Any:
    """
    带重试的 LLM 调用
    
    使用指数退避策略，自动重试失败的 LLM 调用。
    
    Args:
        client: OpenAI 客户端
        messages: 消息列表
        model: 模型名称
        max_tokens: 最大 token 数
        stream: 是否流式
        max_retries: 最大重试次数
    
    Returns:
        LLM 响应对象
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            if stream:
                return client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=True,
                )
            else:
                return client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                )
        
        except (APITimeoutError, RateLimitError, APIError, TimeoutError, OSError) as e:
            last_error = e
            
            if attempt < max_retries:
                # 计算等待时间：指数退避
                wait_time = min(DEFAULT_MIN_WAIT * (2 ** (attempt - 1)), DEFAULT_MAX_WAIT)
                
                # 判断错误类型
                if isinstance(e, RateLimitError):
                    error_type = "速率限制"
                elif isinstance(e, APITimeoutError):
                    error_type = "超时"
                else:
                    error_type = "网络错误"
                
                logger.warning(
                    f"[Agent] LLM {error_type}，第 {attempt}/{max_retries} 次尝试失败，"
                    f"等待 {wait_time:.1f}s 后重试... 错误: {str(e)[:100]}"
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[Agent] LLM 调用重试 {max_retries} 次后失败: {e}")
                raise
        
        except Exception as e:
            logger.error(f"[Agent] LLM 调用未知错误: {e}")
            raise
    
    # 所有重试都失败
    raise RuntimeError(f"LLM 调用失败，已重试 {max_retries} 次: {last_error}")


def load_prompt(filename: str) -> str:
    """加载 Prompt 模板"""
    prompt_path = Path(__file__).parent / "prompts" / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# ============================================================
# Node A: analyze_intent_node
# ============================================================
def analyze_intent_node(state: AgentState) -> Dict:
    """
    意图分析节点
    
    1. 如果有八字输入，计算八字喜用神
    2. 从文本推断五行意图（规则优先）
    3. 提取场景
    4. 合并得到目标五行
    5. 生成增强的搜索查询
    """
    user_input = state["user_input"]
    bazi_input = state["bazi_input"]
    
    # 1. 计算八字（如果有输入）
    bazi_result = None
    if bazi_input:
        try:
            bazi_result = calculate_bazi(
                birth_year=bazi_input["birth_year"],
                birth_month=bazi_input["birth_month"],
                birth_day=bazi_input["birth_day"],
                birth_hour=bazi_input["birth_hour"],
                gender=bazi_input["gender"]
            )
        except Exception as e:
            print(f"[Agent] 八字计算失败: {e}")
    
    # 2. 意图推断
    intent_result = infer_elements_from_text(user_input)
    
    # 3. 提取场景
    scene = state.get("scene") or extract_scene_from_text(user_input)
    scene_result = get_scene_elements(scene) if scene else None
    
    # 4. 合并推荐五行（八字 + 场景 + 意图 + 天气）
    weather_element = state.get("weather_element")
    target_elements = merge_recommendations(
        bazi_result=bazi_result,
        intent_result=intent_result,
        scene_result=scene_result,
        weather_element=weather_element
    )
        
    # 4.1 区分喜用神与场景/天气添加的五行
    xiyong_elements = bazi_result["suggested_elements"] if bazi_result else []
        
    # 计算场景/天气额外添加的五行
    added_elements = []
    for elem in target_elements:
        if elem not in xiyong_elements:
            added_elements.append(elem)
    
    # 5. 生成搜索查询
    # 如果规则已足够，直接构建查询
    if intent_result["method"] == "rule" and target_elements:
        search_query = build_search_query(
            target_elements=target_elements,
            scene=scene,
            user_query=user_input
        )
    else:
        # 需要 LLM 兜底增强
        search_query = _enhance_query_with_llm(
            user_input=user_input,
            scene=scene,
            bazi_result=bazi_result,
            target_elements=target_elements
        )
    
    return {
        "scene": scene,
        "bazi_result": bazi_result,
        "intent_result": intent_result,
        "target_elements": target_elements,
        "xiyong_elements": xiyong_elements,
        "added_elements": added_elements,
        "search_query": search_query,
    }


def _enhance_query_with_llm(
    user_input: str,
    scene: Optional[str],
    bazi_result: Optional[Dict],
    target_elements: List[str]
) -> str:
    """使用 LLM 增强搜索查询（带重试机制）"""
    try:
        client = get_llm_client()
        prompt_template = load_prompt("analyzer.txt")
        
        # 准备变量
        bazi_reasoning = bazi_result.get("reasoning", "无八字信息") if bazi_result else "无八字信息"
        rule_elements = ", ".join(target_elements) if target_elements else "未确定"
        element_colors = []
        for elem in target_elements:
            colors = get_color_by_element(elem)
            element_colors.extend(colors[:2])
        element_colors_str = "、".join(element_colors[:4]) if element_colors else "未确定"
        
        prompt = prompt_template.format(
            user_input=user_input,
            scene=scene or "未指定",
            bazi_reasoning=bazi_reasoning,
            rule_elements=rule_elements,
            element_colors=element_colors_str
        )
        
        # 使用重试机制调用 LLM
        response = call_llm_with_retry(
            client=client,
            messages=[{"role": "user", "content": prompt}],
            model=settings.qwen_model,
            max_tokens=100,
            stream=False,
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"[Agent] LLM 增强查询失败（重试后）: {e}")
        # 降级：直接使用用户输入
        return user_input


# ============================================================
# Node B: retrieve_items_node
# ============================================================
def retrieve_items_node(state: AgentState) -> Dict:
    """
    物品检索节点（增强版 + Task 3 三种模式）
    
    支持三种检索模式：
    - 'public': 仅从公共库检索
    - 'wardrobe': 仅从用户衣橱检索
    - 'hybrid': 优先衣橱，不足补充公共库
    
    流程：
    1. 根据 retrieval_mode 选择数据源
    2. 用 search_query 做向量搜索
    3. 动态权重计算：根据八字/场景调整语义与五行权重
    4. 按分数排序，返回 Top K
    5. 标记物品来源（🏠 自有 / 🛒 建议）
    """
    search_query = state["search_query"]
    target_elements = state["target_elements"]
    scene = state.get("scene")
    bazi_result = state.get("bazi_result")
    user_gender = state.get("user_gender")
    weather_info = state.get("weather_info")
    user_id = state.get("user_id")
    retrieval_mode = state.get("retrieval_mode", "public")
    top_k = state.get("top_k", 5)
    
    if not search_query:
        return {"error": "搜索查询为空", "retrieved_items": [], "item_sources": {}}
    
    # ========== Task 3: 根据模式检索 ==========
    items = []
    item_sources = {}
    
    if retrieval_mode == "wardrobe":
        # 模式 B: 仅从用户衣橱检索
        logger.info(f"衣橱模式检索: user_id={user_id}, search_query={search_query}")
        
        if not user_id:
            logger.error("衣橱模式错误: user_id为空")
            return {
                "error": "衣橱模式需要登录用户",
                "retrieved_items": [],
                "item_sources": {}
            }
        
        # 检查衣橱是否为空
        is_empty = wardrobe_client.check_wardrobe_empty(user_id)
        logger.info(f"衣橱空状态: user_id={user_id}, is_empty={is_empty}")
        
        if is_empty:
            return {
                "error": "您的衣橱还没有添加衣物，请先添加衣物或切换推荐模式",
                "retrieved_items": [],
                "item_sources": {}
            }
        
        # 生成查询向量
        model = _get_embedding_model()
        query_embedding = model.encode(search_query, normalize_embeddings=True)
        
        # 从衣橱检索
        items = wardrobe_client.vector_search_wardrobe(
            user_id=user_id,
            query_embedding=query_embedding.tolist(),
            target_elements=target_elements,
            weather_info=weather_info,
            limit=50
        )
        
        # 标记来源
        for item in items:
            item_sources[str(item.get("id"))] = "wardrobe"
            item["source"] = "wardrobe"
            item["source_label"] = "🏠 自有"
    
    elif retrieval_mode == "hybrid":
        # 模式 C: 混合推荐 - 优先衣橱，不足补充公共库
        if user_id and not wardrobe_client.check_wardrobe_empty(user_id):
            # 生成查询向量
            model = _get_embedding_model()
            query_embedding = model.encode(search_query, normalize_embeddings=True)
            
            # 先从衣橱检索
            wardrobe_items = wardrobe_client.vector_search_wardrobe(
                user_id=user_id,
                query_embedding=query_embedding.tolist(),
                target_elements=target_elements,
                weather_info=weather_info,
                limit=top_k
            )
            
            items.extend(wardrobe_items)
            for item in wardrobe_items:
                item_sources[str(item.get("id"))] = "wardrobe"
                item["source"] = "wardrobe"
                item["source_label"] = "🏠 自有"
        
        # 如果衣橱结果不足，从公共库补充
        if len(items) < top_k:
            public_items = _vector_search(
                search_query,
                limit=top_k * 2,
                user_gender=user_gender,
                weather_info=weather_info,
                scene=scene  # 传入场景参数
            )
            
            # 标记公共库物品
            for item in public_items:
                item["source"] = "public"
                item["source_label"] = "🛒 建议"
                item_sources[item.get("item_code", str(item.get("id")))] = "public"
            
            # 合并，避免重复
            existing_ids = {str(i.get("id")) for i in items}
            for item in public_items:
                if str(item.get("id")) not in existing_ids:
                    items.append(item)
                    if len(items) >= top_k * 2:
                        break
    
    else:
        # 模式 A: 默认从公共库检索
        items = _vector_search(
            search_query, 
            limit=50, 
            user_gender=user_gender,
            weather_info=weather_info,
            scene=scene  # 传入场景参数
        )
        
        # 标记来源
        for item in items:
            item["source"] = "public"
            item["source_label"] = "🛒 建议"
            item_sources[item.get("item_code", str(item.get("id")))] = "public"
    
    # ========== 后续处理（保持原有逻辑） ==========
    if not items:
        # 根据模式决定如何处理空结果
        if retrieval_mode == "wardrobe":
            # 衣橱模式：不fallback到公共库，提示用户衣橱中没有匹配物品
            return {
                "error": "您的衣橱中没有符合当前五行需求的衣物，建议添加更多衣物或切换推荐模式",
                "retrieved_items": [],
                "item_sources": {}
            }
        elif retrieval_mode == "hybrid":
            # 混合模式：已经从衣橱检索过，现在从公共库补充
            pass  # 继续执行下面的公共库检索
        
        # 尝试百搭单品兜底（仅public模式和hybrid模式）
        fallback_items = _get_versatile_items(target_elements, top_k)
        if fallback_items:
            for item in fallback_items:
                item["source"] = "public"
                item["source_label"] = "🛒 建议"
            return {"retrieved_items": fallback_items, "item_sources": item_sources}
        
        # 根据模式返回不同的错误信息
        if retrieval_mode == "public":
            return {"error": "公共库中没有找到符合条件的衣物，请尝试调整筛选条件", "retrieved_items": [], "item_sources": {}}
        else:
            return {"error": "数据库查询无结果", "retrieved_items": [], "item_sources": {}}
    
    # 动态计算权重
    semantic_weight = 0.6
    wuxing_weight = 0.4
    
    if bazi_result and scene:
        semantic_weight = 0.5
        wuxing_weight = 0.5
    elif bazi_result:
        semantic_weight = 0.55
        wuxing_weight = 0.45
    elif scene:
        semantic_weight = 0.65
        wuxing_weight = 0.35
    
    # 计算加权分数
    scored_items = []
    for item in items:
        semantic_score = item.get("semantic_score", 0.5)
        
        # 计算五行匹配分
        wuxing_score = 0.0
        primary = item.get("primary_element", "")
        secondary = item.get("secondary_element")
        
        if primary in target_elements:
            wuxing_score += 0.6
        if secondary and secondary in target_elements:
            wuxing_score += 0.3
        
        # 加权最终分数
        final_score = semantic_score * semantic_weight + wuxing_score * wuxing_weight
        
        scored_items.append({
            **item,
            "semantic_score": semantic_score,
            "wuxing_score": wuxing_score,
            "final_score": final_score,
        })
    
    # 按分数排序，取 Top K
    scored_items.sort(key=lambda x: x["final_score"], reverse=True)
    top_items = scored_items[:top_k]
    
    # 分类多样性优化
    top_items = _ensure_category_diversity(scored_items, top_k)
    
    # 检查是否全部五行不匹配 → 降级策略
    if all(item["wuxing_score"] == 0 for item in top_items):
        scored_items.sort(key=lambda x: x["semantic_score"], reverse=True)
        top_items = _ensure_category_diversity(scored_items, top_k)
        
        if not top_items:
            top_items = _get_versatile_items(target_elements, top_k)
    
    # 更新 item_sources
    for item in top_items:
        item_id = str(item.get("id")) if item.get("source") == "wardrobe" else item.get("item_code", str(item.get("id")))
        item_sources[item_id] = item.get("source", "public")
    
    return {"retrieved_items": top_items, "item_sources": item_sources}


def _ensure_category_diversity(items: List[Dict], limit: int) -> List[Dict]:
    """
    确保推荐结果包含不同分类的物品（增强版）
    
    策略：
    - 核心服装（上装/下装/裙装/外套）每类最多2件
    - 配饰/鞋履每类最多1件（但优先保留至少1件配饰）
    - 优先取高分，但保证多样性
    
    Args:
        items: 已排序的物品列表
        limit: 返回数量
        
    Returns:
        List[Dict]: 多样化后的物品列表
    """
    result = []
    category_count = {}
    
    # 分类限制：核心服装最多2件，配饰/鞋履最多1件
    max_per_category = {
        "上装": 2,
        "下装": 2,
        "裙装": 2,
        "外套": 2,
        "配饰": 1,
        "鞋履": 1,
    }
    
    # 先遍历一次，记录配饰在排序中的位置
    accessory_items = [item for item in items if item.get("category") == "配饰"]
    
    for item in items:
        category = item.get("category", "其他")
        
        # 获取该分类的限制
        max_count = max_per_category.get(category, 1)
        current_count = category_count.get(category, 0)
        
        if current_count < max_count:
            result.append(item)
            category_count[category] = current_count + 1
            
            if len(result) >= limit:
                break
    
    # 确保至少有1件配饰（如果存在配饰且未入选）
    has_accessory = any(item.get("category") == "配饰" for item in result)
    if not has_accessory and accessory_items and len(result) >= limit:
        # 替换分数最低的非核心服装
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("category") in ["上装", "下装", "裙装", "外套", "鞋履"]:
                # 检查替换后该分类是否还有其他物品
                cat = result[i].get("category")
                same_cat_count = sum(1 for item in result if item.get("category") == cat)
                if same_cat_count > 1:  # 该分类还有其他物品，可以替换
                    result[i] = accessory_items[0]
                    break
    
    return result


def _get_versatile_items(target_elements: List[str], limit: int) -> List[Dict]:
    """
    获取百搭单品兜底
    
    当数据库无匹配结果时，返回中性百搭的单品
    """
    # 百搭单品特征：土属性（中性、包容）+ 基础色
    versatile_query = "百搭 中性 基础款 黑色 白色 灰色 米色 舒适"
    
    items = _vector_search(versatile_query, limit=limit)
    
    return items if items else []


# 全局模型单例
_EMBEDDING_MODEL = None


def _get_embedding_model():
    """获取 embedding 模型单例（本地缓存优先）"""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        import os
        # 优先使用本地缓存，不连接 HuggingFace
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer('BAAI/bge-m3')
    return _EMBEDDING_MODEL


def _vector_search(
    query: str, 
    limit: int = 20, 
    user_gender: Optional[str] = None,
    weather_info: Optional[Dict] = None,
    scene: Optional[str] = None  # 新增场景参数
) -> List[Dict]:
    """
    向量搜索（支持性别过滤、天气过滤和场景过滤）
    
    使用 pgvector 进行语义相似度搜索
    
    Args:
        query: 搜索查询文本
        limit: 返回数量
        user_gender: 用户性别（男/女），用于过滤专属物品
        weather_info: 天气信息 {"temperature": int, "weather_desc": str}
        scene: 场景名称，用于过滤不合适的衣物
    """
    import numpy as np
    
    # 加载 embedding 模型（单例）
    model = _get_embedding_model()
    
    # 生成查询向量
    query_embedding = model.encode(query)
    query_vector = np.array(query_embedding, dtype=np.float32)
    
    # 数据库查询
    items = []
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                # 性别过滤逻辑
                if user_gender == "男":
                    gender_filter = "AND (gender = '中性' OR gender = '男')"
                elif user_gender == "女":
                    gender_filter = "AND (gender = '中性' OR gender = '女')"
                else:
                    gender_filter = ""
                
                # 天气过滤逻辑
                weather_filter = _build_weather_filter(weather_info)
                
                # 场景过滤逻辑（新增）
                scene_filter = _build_scene_filter(scene)
                
                # 调试日志
                if scene:
                    logger.info(f"[场景过滤] scene={scene}, filter={scene_filter}")
                
                sql = f"""
                    SELECT 
                        item_code, name, category, 
                        primary_element, secondary_element,
                        attributes_detail, gender,
                        applicable_weather, applicable_seasons,
                        temperature_range, functionality, thickness_level,
                        image_url,
                        1 - (embedding <=> %s::vector) AS semantic_score
                    FROM items
                    WHERE embedding IS NOT NULL
                    {gender_filter}
                    {f'AND ({weather_filter})' if weather_filter else ''}
                    {f'AND ({scene_filter})' if scene_filter else ''}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cur.execute(sql, (query_vector.tolist(), query_vector.tolist(), limit))
                rows = cur.fetchall()
                
                for row in rows:
                    items.append({
                        "item_code": row[0],
                        "name": row[1],
                        "category": row[2],
                        "primary_element": row[3],
                        "secondary_element": row[4],
                        "attributes_detail": row[5],
                        "gender": row[6],
                        "applicable_weather": row[7],
                        "applicable_seasons": row[8],
                        "temperature_range": row[9],
                        "functionality": row[10],
                        "thickness_level": row[11],
                        "image_url": row[12],
                        "semantic_score": float(row[13]) if row[13] else 0.5,
                        "source": "public",
                    })
    except Exception as e:
        import traceback
        print(f"[Agent] 向量搜索失败: {e}")
        print(f"[Agent] 错误堆栈: {traceback.format_exc()}")
    
    return items


def _build_weather_filter(weather_info: Optional[Dict]) -> str:
    """
    构建天气过滤SQL条件
    
    根据温度和天气状况生成过滤条件：
    - 温度过滤：优先推荐适合当前温度的衣物
    - 天气状况过滤：雨天推荐防水衣物等
    
    Args:
        weather_info: 天气信息 {"temperature": int, "weather_desc": str}
    
    Returns:
        str: SQL过滤条件
    """
    if not weather_info:
        return ""
    
    conditions = []
    temperature = weather_info.get("temperature")
    weather_desc = weather_info.get("weather_desc", "")
    
    # 温度过滤逻辑
    if temperature is not None:
        # 根据温度范围筛选适合的衣物
        # 低温（<10°C）：优先厚衣物
        # 中温（10-20°C）：中等厚度
        # 高温（>20°C）：优先薄衣物
        if temperature < 5:
            # 极冷：优先厚重/中厚衣物
            conditions.append(
                "(thickness_level IN ('厚重', '中厚') OR "
                "temperature_range->>'最低' IS NOT NULL AND "
                "(temperature_range->>'最低')::int <= 5)"
            )
        elif temperature < 15:
            # 较冷：优先中厚/适中衣物
            conditions.append(
                "(thickness_level IN ('厚重', '中厚', '适中') OR "
                "temperature_range->>'最低' IS NOT NULL AND "
                "(temperature_range->>'最低')::int <= 15)"
            )
        elif temperature < 25:
            # 温和：适中/轻薄衣物
            conditions.append(
                "(thickness_level IN ('适中', '轻薄', '极薄') OR "
                "temperature_range->>'最高' IS NOT NULL AND "
                "(temperature_range->>'最高')::int >= 15)"
            )
        else:
            # 炎热：优先轻薄/极薄衣物
            conditions.append(
                "(thickness_level IN ('轻薄', '极薄', '适中') OR "
                "temperature_range->>'最高' IS NOT NULL AND "
                "(temperature_range->>'最高')::int >= 25)"
            )
    
    # 天气状况过滤
    if weather_desc:
        weather_desc_lower = weather_desc.lower()
        
        if any(kw in weather_desc_lower for kw in ['雨', '雪', '阴雨']):
            # 雨雪天气：优先防水或有雨天标签的衣物
            conditions.append(
                "(applicable_weather ? '雨天' OR "
                "functionality->>'防水' = 'true' OR "
                "applicable_weather ? '多云')"
            )
        elif any(kw in weather_desc_lower for kw in ['晴', '晴朗']):
            # 晴天：优先防晒或有晴天标签的衣物
            conditions.append(
                "(applicable_weather ? '晴天' OR "
                "functionality->>'防晒' = 'true' OR "
                "applicable_weather ? '温和')"
            )
    
    return " AND ".join(conditions) if conditions else ""


def _build_scene_filter(scene: Optional[str]) -> str:
    """
    构建场景过滤SQL条件
    
    根据场景排除不合适的衣物类型：
    - 运动场景：排除风衣、围巾、西装等
    - 商务场景：排除运动装、睡衣等
    - 居家场景：排除正装、礼服等
    
    Args:
        scene: 场景名称
    
    Returns:
        str: SQL过滤条件
    """
    if not scene:
        return ""
    
    # 场景排除规则：某些场景下不应该出现的衣物类别
    scene_exclusions = {
        "运动": {
            "categories": ["外套", "配饰"],  # 排除外套、配饰（围巾等）
            "keywords": ["风衣", "大衣", "围巾", "西装", "礼服", "睡衣"],
            "require_functionality": ["透气", "速干", "运动"],  # 优先运动功能
        },
        "商务": {
            "categories": [],  # 不排除类别
            "keywords": ["运动裤", "睡衣", "泳衣", "拖鞋"],
            "require_functionality": [],
        },
        "居家": {
            "categories": ["外套"],  # 排除外套
            "keywords": ["西装", "礼服", "高跟鞋"],
            "require_functionality": [],
        },
        "婚礼": {
            "categories": [],
            "keywords": ["运动裤", "睡衣", "拖鞋", "泳衣"],
            "require_functionality": [],
        },
        "派对": {
            "categories": [],
            "keywords": ["睡衣", "运动裤", "泳衣"],
            "require_functionality": [],
        },
        "面试": {
            "categories": [],
            "keywords": ["运动裤", "睡衣", "拖鞋", "泳衣", "短裤"],
            "require_functionality": [],
        },
        "旅行": {
            "categories": [],
            "keywords": ["毛衣", "卫衣", "棉袄", "羽绒服"],  # 排除厚重衣物
            "thickness_exclude": ["厚重", "中厚"],  # 排除厚重和中厚
            "require_functionality": [],
        },
    }
    
    if scene not in scene_exclusions:
        return ""
    
    rules = scene_exclusions[scene]
    conditions = []
    
    # 1. 排除特定类别
    if rules["categories"]:
        categories_str = ",".join([f"'{cat}'" for cat in rules["categories"]])
        conditions.append(f"category NOT IN ({categories_str})")
    
    # 2. 排除包含特定关键词的衣物
    if rules["keywords"]:
        keyword_conditions = []
        for keyword in rules["keywords"]:
            # 使用 %% 转义 % 符号，避免与 SQL 参数占位符冲突
            keyword_conditions.append(f"name NOT LIKE '%%{keyword}%%'")
        if keyword_conditions:
            conditions.append(" AND ".join(keyword_conditions))
    
    # 3. 排除特定厚度的衣物（新增）
    if rules.get("thickness_exclude"):
        thickness_str = ",".join([f"'{t}'" for t in rules["thickness_exclude"]])
        conditions.append(f"thickness_level NOT IN ({thickness_str})")
    
    # 4. 优先特定功能（作为排序因子，不做硬过滤）
    # 这个逻辑会在评分时体现，不在SQL过滤
    
    return " AND ".join(conditions) if conditions else ""


def _build_weather_details(weather_info: Optional[Dict], retrieved_items: List[Dict]) -> str:
    """
    构建天气详情描述（用于LLM prompt）
    
    Args:
        weather_info: 天气信息 {"temperature": int, "weather_desc": str, ...}
        retrieved_items: 推荐物品列表（用于提取物品特性）
    
    Returns:
        str: 天气详情描述
    """
    if not weather_info:
        return "未提供天气信息"
    
    details = []
    temperature = weather_info.get("temperature")
    weather_desc = weather_info.get("weather_desc", "")
    humidity = weather_info.get("humidity")
    wind_level = weather_info.get("wind_level")
    
    # 温度信息
    if temperature is not None:
        temp_desc = f"当前气温：{temperature}°C"
        if temperature < 5:
            temp_desc += "（寒冷，需注意保暖）"
        elif temperature < 15:
            temp_desc += "（较冷，建议穿厚外套）"
        elif temperature < 25:
            temp_desc += "（温和，穿衣自由度高）"
        else:
            temp_desc += "（炎热，建议轻薄透气）"
        details.append(temp_desc)
    
    # 天气状况
    if weather_desc:
        weather_desc_detail = f"天气状况：{weather_desc}"
        if "雨" in weather_desc or "雪" in weather_desc:
            weather_desc_detail += "（建议携带雨具，注意防水）"
        elif "晴" in weather_desc:
            weather_desc_detail += "（适合户外活动）"
        elif "霾" in weather_desc or "雾" in weather_desc:
            weather_desc_detail += "（注意防护）"
        details.append(weather_desc_detail)
    
    # 湿度
    if humidity is not None:
        humidity_desc = f"湿度：{humidity}%"
        if humidity > 80:
            humidity_desc += "（潮湿）"
        elif humidity < 30:
            humidity_desc += "（干燥）"
        details.append(humidity_desc)
    
    # 风力
    if wind_level is not None:
        wind_desc = f"风力：{wind_level}级"
        if wind_level >= 5:
            wind_desc += "（风大，注意防风）"
        details.append(wind_desc)
    
    # 推荐物品的天气特性
    if retrieved_items:
        item_features = []
        for item in retrieved_items[:3]:
            thickness = item.get("thickness_level")
            functionality = item.get("functionality", {})
            
            if thickness:
                item_features.append(f"{item['name']}厚度【{thickness}】")
            
            # 功能性
            funcs = []
            if functionality.get("防水"):
                funcs.append("防水")
            if functionality.get("透气"):
                funcs.append("透气")
            if functionality.get("保暖"):
                funcs.append("保暖")
            if functionality.get("防晒"):
                funcs.append("防晒")
            
            if funcs:
                item_features.append(f"{item['name']}具有【{'、'.join(funcs)}】功能")
        
        if item_features:
            details.append("推荐物品特性：" + "；".join(item_features[:3]))
    
    if details:
        return "\n".join(details)
    return "天气信息不完整"


# ============================================================
# Node C: generate_advice_node
# ============================================================
def generate_advice_node(state: AgentState) -> Dict:
    """
    生成推荐理由节点
    
    使用 LLM 生成个性化推荐理由（支持流式）
    """
    user_input = state["user_input"]
    bazi_result = state["bazi_result"]
    target_elements = state["target_elements"]
    xiyong_elements = state.get("xiyong_elements", [])
    added_elements = state.get("added_elements", [])
    retrieved_items = state["retrieved_items"]
    scene = state.get("scene")
    weather_element = state.get("weather_element")
    weather_info = state.get("weather_info")  # 新增：天气详情
        
    if not retrieved_items:
        # 兜底策略：优先百搭单品，其次颜色建议
            
        # 1. 尝试获取百搭单品
        versatile_items = _get_versatile_items(target_elements, 3)
            
        if versatile_items:
            # 有百搭单品，格式化推荐
            items_list = []
            for item in versatile_items:
                items_list.append(
                    f"- {item['name']}（{item['category']}，五行：{item['primary_element']}）"
                )
            items_list_str = "\n".join(items_list)
                
            suggestion = f"暂未找到完全匹配的衣物，但为您推荐以下百搭单品：\n{items_list_str}\n这些单品风格中性，易于搭配，适合多种场合。"
                
            return {
                "reasoning_text": suggestion,
                "final_response": {"reason": suggestion, "items": versatile_items}
            }
            
        # 2. 没有百搭单品，给出五行颜色建议
        color_suggestions = []
        for elem in target_elements[:2]:
            colors = get_color_by_element(elem)
            if colors:
                color_suggestions.append(f"{elem}系（如{colors[0]}、{colors[1] if len(colors) > 1 else colors[0]}）")
            
        if color_suggestions:
            suggestion = f"抱歉，暂未找到匹配的衣物。根据您的需求，建议选择{'或'.join(color_suggestions)}的服饰。"
        else:
            suggestion = "抱歉，暂未找到匹配的衣物，请尝试其他描述。"
            
        return {
            "reasoning_text": suggestion,
            "final_response": {"reason": suggestion, "items": []}
        }
    
    # 格式化物品列表
    items_list = []
    for item in retrieved_items:
        items_list.append(
            f"- {item['name']}（{item['category']}，五行：{item['primary_element']}"
            f"{', ' + item['secondary_element'] if item['secondary_element'] else ''}）"
        )
    items_list_str = "\n".join(items_list)
    
    # 准备 Prompt
    bazi_reasoning = bazi_result.get("reasoning", "无") if bazi_result else "无"
        
    # 清晰标识各因素是否存在
    scene_display = scene if scene else "无"
    weather_display = weather_element if weather_element else "无"
    has_bazi = "有" if bazi_result else "无"
    has_weather = "有" if weather_element else "无"
    has_scene = "有" if scene else "无"
    
    # 构建天气详情
    weather_details = _build_weather_details(weather_info, retrieved_items)
        
    prompt_template = load_prompt("generator.txt")
    prompt = prompt_template.format(
        user_input=user_input,
        scene=scene_display,
        weather_element=weather_display,
        target_elements="、".join(target_elements) if target_elements else "综合推荐",
        xiyong_elements="、".join(xiyong_elements) if xiyong_elements else "无",
        added_elements="、".join(added_elements) if added_elements else "无",
        bazi_reasoning=bazi_reasoning,
        items_list=items_list_str,
        has_bazi=has_bazi,
        has_weather=has_weather,
        has_scene=has_scene,
        weather_details=weather_details,
    )
    
    # 调用 LLM（非流式，流式在 Task 04 实现）
    try:
        client = get_llm_client()
        
        # 使用重试机制调用 LLM
        response = call_llm_with_retry(
            client=client,
            messages=[{"role": "user", "content": prompt}],
            model=settings.qwen_model,
            max_tokens=300,
            stream=False,
        )
        
        reasoning_text = response.choices[0].message.content.strip()
        
        # 反幻觉验证：检查提到的物品名是否在列表中
        item_names = [item["name"] for item in retrieved_items]
        # 简单验证：确保至少提到一个真实物品
        mentioned = any(name in reasoning_text for name in item_names)
        if not mentioned:
            # 添加提示
            reasoning_text = f"推荐：{retrieved_items[0]['name']}。" + reasoning_text
        
    except Exception as e:
        logger.error(f"[Agent] LLM 生成失败（重试后）: {e}")
        reasoning_text = f"根据您的需求，推荐 {retrieved_items[0]['name']} 等衣物。"
    
    return {
        "reasoning_text": reasoning_text,
    }


def generate_advice_stream(state: AgentState) -> Generator[str, None, None]:
    """
    流式生成推荐理由（供 SSE 使用）
    
    Yields:
        str: 逐个 token
    """
    user_input = state["user_input"]
    bazi_result = state["bazi_result"]
    target_elements = state["target_elements"]
    xiyong_elements = state.get("xiyong_elements", [])
    added_elements = state.get("added_elements", [])
    retrieved_items = state["retrieved_items"]
    scene = state.get("scene")
    weather_element = state.get("weather_element")
    weather_info = state.get("weather_info")  # 新增：天气详情
            
    if not retrieved_items:
        # 兜底策略：优先百搭单品，其次颜色建议
            
        # 1. 尝试获取百搭单品
        versatile_items = _get_versatile_items(target_elements, 3)
            
        if versatile_items:
            # 有百搭单品，生成推荐
            items_list = []
            for item in versatile_items:
                items_list.append(f"- {item['name']}（{item['category']}，五行：{item['primary_element']}）")
            items_list_str = "\n".join(items_list)
                
            yield f"暂未找到完全匹配的衣物，但为您推荐以下百搭单品：\n{items_list_str}\n这些单品风格中性，易于搭配，适合多种场合。"
            return
            
        # 2. 没有百搭单品，给出五行颜色建议
        color_suggestions = []
        for elem in target_elements[:2]:
            colors = get_color_by_element(elem)
            if colors:
                color_suggestions.append(f"{elem}系（如{colors[0]}、{colors[1] if len(colors) > 1 else colors[0]}）")
                    
        if color_suggestions:
            yield f"抱歉，暂未找到匹配的衣物。根据您的需求，建议选择{'或'.join(color_suggestions)}的服饰。"
        else:
            yield "抱歉，暂未找到匹配的衣物，请尝试其他描述。"
        return
    
    # 格式化物品列表
    items_list = []
    for item in retrieved_items:
        items_list.append(
            f"- {item['name']}（{item['category']}，五行：{item['primary_element']}"
            f"{', ' + item['secondary_element'] if item['secondary_element'] else ''}）"
        )
    items_list_str = "\n".join(items_list)
    
    bazi_reasoning = bazi_result.get("reasoning", "无") if bazi_result else "无"
    
    # 清晰标识各因素是否存在
    scene_display = scene if scene else "无"
    weather_display = weather_element if weather_element else "无"
    has_bazi = "有" if bazi_result else "无"
    has_weather = "有" if weather_element else "无"
    has_scene = "有" if scene else "无"
    
    # 构建天气详情
    weather_details = _build_weather_details(weather_info, retrieved_items)
    
    prompt_template = load_prompt("generator.txt")
    prompt = prompt_template.format(
        user_input=user_input,
        scene=scene_display,
        weather_element=weather_display,
        target_elements="、".join(target_elements) if target_elements else "综合推荐",
        xiyong_elements="、".join(xiyong_elements) if xiyong_elements else "无",
        added_elements="、".join(added_elements) if added_elements else "无",
        bazi_reasoning=bazi_reasoning,
        items_list=items_list_str,
        has_bazi=has_bazi,
        has_weather=has_weather,
        has_scene=has_scene,
        weather_details=weather_details,
    )
    
    try:
        client = get_llm_client()
        
        # 使用重试机制调用 LLM
        stream = call_llm_with_retry(
            client=client,
            messages=[{"role": "user", "content": prompt}],
            model=settings.qwen_model,
            max_tokens=300,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    except Exception as e:
        logger.error(f"[Agent] LLM 流式生成失败（重试后）: {e}")
        yield f"根据您的需求，推荐 {retrieved_items[0]['name']} 等衣物。"


# ============================================================
# Node D: format_output_node
# ============================================================
def format_output_node(state: AgentState) -> Dict:
    """
    格式化输出节点
    
    将状态数据格式化为最终响应
    """
    bazi_result = state["bazi_result"]
    intent_result = state["intent_result"]
    target_elements = state["target_elements"]
    retrieved_items = state["retrieved_items"]
    reasoning_text = state["reasoning_text"]
    scene = state.get("scene")
    
    # 构建分析结果
    analysis = {
        "target_elements": target_elements,
        "bazi_reasoning": bazi_result.get("reasoning") if bazi_result else None,
        "intent_reasoning": intent_result.get("reasoning") if intent_result else None,
        "scene": scene,
    }
    
    # 构建物品列表
    items = []
    for item in retrieved_items:
        items.append({
            "item_code": item.get("item_code", ""),
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "primary_element": item.get("primary_element", ""),
            "secondary_element": item.get("secondary_element"),
            "final_score": round(item.get("final_score", 0), 3),
            "semantic_score": round(item.get("semantic_score", 0), 3),
            "wuxing_score": round(item.get("wuxing_score", 0), 3),
            "source": item.get("source") or "public",
            "item_id": item.get("id"),
            "image_url": item.get("image_url"),
        })
    
    # 最终响应
    final_response = {
        "analysis": analysis,
        "items": items,
        "reason": reasoning_text,
    }
    
    return {"final_response": final_response}
