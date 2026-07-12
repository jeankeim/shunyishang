"""
LangGraph Agent 节点函数
包含 4 个核心节点：analyze_intent, retrieve_items, generate_advice, format_output
"""

import os
import time
import json
import hashlib
import logging
from typing import Dict, List, Optional, Generator, Any
from pathlib import Path

from openai import OpenAI, APITimeoutError, APIError, RateLimitError

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.core.cache import cache as redis_cache
from packages.ai_agents.state import AgentState
from packages.ai_agents.wardrobe_client import wardrobe_client
from packages.utils.bazi_calculator import (
    calculate_bazi,
    infer_elements_from_text,
    merge_recommendations,
)
from packages.utils.destiny_calculator import (
    analyze_year_fortune,
    get_current_major_luck,
)
from packages.utils.scene_mapper import (
    extract_scene_from_text,
    extract_scene_multidimensional,
    get_scene_elements,
    get_color_by_element,
    build_search_query,
)
from packages.utils.scene_mapping import calculate_scene_match_score
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

logger = logging.getLogger(__name__)

# ============================================================
# LLM 配置与重试机制
# ============================================================
# 默认重试参数（优化：减少重试次数，加快失败响应）
DEFAULT_MAX_RETRIES = 1  # 从 3 降低到 1，失败快速降级
DEFAULT_MIN_WAIT = 0.5  # 秒（优化：从 1.0 降低到 0.5，加快重试）
DEFAULT_MAX_WAIT = 1.5  # 秒（优化：从 3.0 降低到 1.5）


_llm_client: Optional[OpenAI] = None  # 模块级单例，避免每次请求重新建连

def get_llm_client(timeout: int = 8) -> OpenAI:
    """
    获取阿里百炼千问客户端（单例模式，复用 HTTP 连接池）
    
    Args:
        timeout: 请求超时时间（秒）
    """
    global _llm_client
    if _llm_client is not None:
        return _llm_client

    api_key = settings.dashscope_api_key

    if not api_key:
        logger.error("[Agent] ❌ DASHSCOPE_API_KEY 未设置！")
        raise ValueError("DASHSCOPE_API_KEY 未配置，请检查 .env 文件")

    logger.info(f"[Agent] ✅ LLM 客户端初始化（单例），Base URL: {settings.dashscope_base_url}")

    _llm_client = OpenAI(
        api_key=api_key,
        base_url=settings.dashscope_base_url,
        timeout=timeout,
        max_retries=0,  # 我们自己实现重试
    )
    return _llm_client


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
            # 生成缓存键：基于用户出生信息
            bazi_cache_key = f"bazi:{bazi_input['birth_year']}:{bazi_input['birth_month']}:{bazi_input['birth_day']}:{bazi_input['birth_hour']}"
            
            # 尝试从缓存获取（使用统一的 cache.py 同步接口）
            cached_bazi = None
            if settings.redis_enabled:
                try:
                    cached_bazi = redis_cache.get_sync(bazi_cache_key)
                    if cached_bazi:
                        logger.info(f"[Agent] 八字缓存命中: {bazi_cache_key}")
                except Exception as e:
                    logger.debug(f"缓存读取失败: {e}")
            
            if cached_bazi:
                bazi_result = cached_bazi
            else:
                # 缓存未命中，计算并缓存
                bazi_result = calculate_bazi(
                    birth_year=bazi_input["birth_year"],
                    birth_month=bazi_input["birth_month"],
                    birth_day=bazi_input["birth_day"],
                    birth_hour=bazi_input["birth_hour"],
                    gender=bazi_input["gender"]
                )
                # 缓存 24 小时（使用统一的 cache.py 同步接口）
                if settings.redis_enabled:
                    try:
                        redis_cache.set_sync(bazi_cache_key, bazi_result, ttl=settings.cache_ttl_bazi)
                        logger.info(f"[Agent] 八字已缓存: {bazi_cache_key}")
                    except Exception as e:
                        logger.debug(f"缓存写入失败: {e}")
        except Exception as e:
            logger.warning(f"[Agent] 八字计算失败: {e}")
    
    # 1.1 计算流年运势和当前大运（如果有八字结果）
    annual_luck_data = None
    major_luck_data = None
    if bazi_result:
        try:
            from datetime import date
            current_year = date.today().year
            
            # 流年运势
            annual_result = analyze_year_fortune(bazi_result, current_year)
            annual_luck_data = annual_result
            
            # 计算流年 lucky_elements 对 target_elements 的增强
            annual_lucky = annual_result.get("lucky_elements", [])
            logger.info(f"[Agent] 流年运势: year={current_year}, lucky_elements={annual_lucky}, overall={annual_result.get('overall_score')}")
            
            # 当前大运
            birth_year = bazi_input.get("birth_year")
            if birth_year:
                # 计算当前年龄
                current_age = current_year - birth_year
                gender = bazi_input.get("gender", "男")
                major_luck_data = get_current_major_luck(
                    bazi_result, gender, current_age,
                    birth_year=birth_year,
                    birth_month=bazi_input.get("birth_month"),
                    birth_day=bazi_input.get("birth_day"),
                )
                logger.info(f"[Agent] 当前大运: {major_luck_data}")
        except Exception as e:
            logger.warning(f"[Agent] 流年/大运计算失败: {e}")
    
    # 2. 意图推断
    intent_result = infer_elements_from_text(user_input)
    
    # 3. Task 03: 提取场曷（多维度识别）
    scene_data = extract_scene_multidimensional(user_input)
    scene = state.get("scene") or scene_data.get("main_scene")
    sub_scene = scene_data.get("sub_scene")  # 子场景
    emotion = scene_data.get("emotion")  # 情感倾向
    
    scene_result = get_scene_elements(scene) if scene else None
    
    # 4. 合并推荐五行（八字 + 场景 + 意图 + 天气）
    weather_element = state.get("weather_element")
    target_elements, boost_elements = merge_recommendations(
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
    
    # 4.2 流年运势增强：将流年幸运元素加入推荐五行（优先级低于喜用神）
    if annual_luck_data:
        annual_lucky_elements = annual_luck_data.get("lucky_elements", [])
        avoid_elements = bazi_result.get("avoid_elements", []) if bazi_result else []
        for elem in annual_lucky_elements[:2]:  # 最多取前2个流年幸运元素
            if elem not in target_elements and elem not in xiyong_elements and elem not in avoid_elements:
                target_elements.append(elem)
                added_elements.append(elem)
                logger.info(f"[Agent] 流年增强: 添加流年幸运元素 {elem}")
            elif elem in avoid_elements:
                logger.info(f"[Agent] 流年增强: 跳过忌神 {elem}（不纳入 target_elements）")
    
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
        "sub_scene": sub_scene,  # Task 03: 子场景
        "emotion": emotion,  # Task 03: 情感倾向
        "bazi_result": bazi_result,
        "annual_luck": annual_luck_data,
        "major_luck": major_luck_data,
        "intent_result": intent_result,
        "target_elements": target_elements,
        "xiyong_elements": xiyong_elements,
        "added_elements": added_elements,
        "boost_elements": boost_elements,
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
# 推荐权重配置化（替代原硬编码 if-else 链）
# ============================================================

# 基础权重预设表：(has_bazi, has_scene, has_prefs) -> weights
_WEIGHT_PRESETS = {
    # 有八字 + 有场景
    (True,  True,  True):  {"semantic": 0.50, "wuxing": 0.25, "scene": 0.15, "pref": 0.10, "temp": 0.00},
    (True,  True,  False): {"semantic": 0.50, "wuxing": 0.30, "scene": 0.20, "pref": 0.00, "temp": 0.00},
    # 有八字 + 无场景
    (True,  False, True):  {"semantic": 0.50, "wuxing": 0.35, "scene": 0.00, "pref": 0.15, "temp": 0.00},
    (True,  False, False): {"semantic": 0.55, "wuxing": 0.45, "scene": 0.00, "pref": 0.00, "temp": 0.00},
    # 无八字 + 有场景
    (False, True,  True):  {"semantic": 0.55, "wuxing": 0.15, "scene": 0.20, "pref": 0.10, "temp": 0.00},
    (False, True,  False): {"semantic": 0.60, "wuxing": 0.20, "scene": 0.20, "pref": 0.00, "temp": 0.00},
    # 无八字 + 无场景
    (False, False, True):  {"semantic": 0.55, "wuxing": 0.30, "scene": 0.00, "pref": 0.15, "temp": 0.00},
    (False, False, False): {"semantic": 0.60, "wuxing": 0.40, "scene": 0.00, "pref": 0.00, "temp": 0.00},
}

# 极端温度时，温度维度占比
_EXTREME_TEMP_RATIO = 0.25


def _compute_recommend_weights(
    has_bazi: bool,
    has_scene: bool,
    has_prefs: bool,
    is_extreme_temp: bool = False,
) -> Dict[str, float]:
    """
    配置化计算推荐权重（替代原 20+ 分支的 if-else 链）
    
    策略：
    1. 从预设表查基础权重
    2. 极端温度时，温度维度占 25%，其余维度按比例缩减
    
    Args:
        has_bazi: 是否有八字信息
        has_scene: 是否有场景信息
        has_prefs: 是否有用户偏好
        is_extreme_temp: 是否极端温度（≤5°C 或 ≥32°C）
    
    Returns:
        Dict[str, float]: 各维度权重（总和=1.0）
    """
    preset = _WEIGHT_PRESETS.get(
        (has_bazi, has_scene, has_prefs),
        _WEIGHT_PRESETS[(False, False, False)],  # 默认兜底
    ).copy()
    
    if is_extreme_temp:
        preset["temp"] = _EXTREME_TEMP_RATIO
        # 按原比例缩减其他维度，确保总和=1.0
        remaining = 1.0 - _EXTREME_TEMP_RATIO
        other_sum = sum(v for k, v in preset.items() if k != "temp")
        if other_sum > 0:
            scale = remaining / other_sum
            for k in preset:
                if k != "temp":
                    preset[k] = round(preset[k] * scale, 4)
        # 修正浮点精度
        total = sum(preset.values())
        if abs(total - 1.0) > 0.001:
            preset["semantic"] = round(preset["semantic"] + (1.0 - total), 4)
    
    return preset


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
    sub_scene = state.get("sub_scene")  # 新增：子场景
    bazi_result = state.get("bazi_result")
    user_gender = state.get("user_gender")
    weather_info = state.get("weather_info")
    user_id = state.get("user_id")
    retrieval_mode = state.get("retrieval_mode", "public")
    top_k = state.get("top_k", 5)
    boost_elements = state.get("boost_elements", [])  # 相生辅助五行
    
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
        from apps.api.services.embedding_service import embedding_service
        query_embedding = embedding_service.generate_embedding(search_query)
        
        # 从衣橱检索
        items = wardrobe_client.vector_search_wardrobe(
            user_id=user_id,
            query_embedding=query_embedding,  # 已经是 List[float]，无需 .tolist()
            target_elements=target_elements,
            weather_info=weather_info,
            limit=50
        )
        
        # 调试日志：检查返回的 items
        logger.info(f"[衣橱检索] 返回物品数量: {len(items)}")
        if items:
            logger.info(f"[衣橱检索] 第一个物品类型: {type(items[0])}")
            logger.info(f"[衣橱检索] 第一个物品: {items[0] if isinstance(items[0], dict) else 'N/A'}")
        
        # 防御性检查：确保 items 是列表且每个元素都是字典
        if not isinstance(items, list):
            logger.error(f"[衣橱检索] 错误: items 不是列表类型，type={type(items)}")
            items = []
        else:
            # 过滤掉非字典类型的元素
            valid_items = []
            for idx, item in enumerate(items):
                if isinstance(item, dict):
                    valid_items.append(item)
                else:
                    logger.error(f"[衣橱检索] 错误: items[{idx}] 不是字典类型，type={type(item)}")
            items = valid_items
        
        # 标记来源
        for item in items:
            item_sources[str(item.get("id"))] = "wardrobe"
            item["source"] = "wardrobe"
            item["source_label"] = "🏠 自有"
    
    elif retrieval_mode == "hybrid":
        # 模式 C: 混合推荐 - 优先衣橱，不足补充公共库
        if user_id and not wardrobe_client.check_wardrobe_empty(user_id):
            # 生成查询向量
            from apps.api.services.embedding_service import embedding_service
            query_embedding = embedding_service.generate_embedding(search_query)
            
            # 先从衣橱检索
            wardrobe_items = wardrobe_client.vector_search_wardrobe(
                user_id=user_id,
                query_embedding=query_embedding,  # 已经是 List[float]，无需 .tolist()
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
                scene=scene,  # 传入场景参数
                sub_scene=sub_scene  # 传入子场景
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
            scene=scene,  # 传入场景参数
            sub_scene=sub_scene  # 传入子场景
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
    
    # 获取用户偏好（用于偏好加权评分）
    user_prefs = {}
    if user_id:
        try:
            from apps.api.services.preference_service import preference_service
            user_prefs = preference_service.get_user_preferences(user_id)
        except Exception as e:
            logger.debug(f"[检索节点] 获取用户偏好失败: {e}")

    # 动态计算权重（配置化：消除硬编码 if-else 链）
    has_prefs = bool(user_prefs)
    is_extreme_temp = False
    if weather_info:
        temp_val = weather_info.get("temperature") or 25
        is_extreme_temp = (temp_val <= 5 or temp_val >= 32)
    
    weights = _compute_recommend_weights(
        has_bazi=bool(bazi_result),
        has_scene=bool(scene),
        has_prefs=has_prefs,
        is_extreme_temp=is_extreme_temp,
    )
    semantic_weight = weights["semantic"]
    wuxing_weight = weights["wuxing"]
    scene_weight = weights["scene"]
    pref_weight = weights["pref"]
    temp_weight = weights["temp"]
    
    # Task 01: 提取子场景（如果有多维度场景识别）
    sub_scene = state.get("sub_scene")
    
    # 计算加权分数
    scored_items = []
    for idx, item in enumerate(items):
        # 防御性检查：确保 item 是字典
        if not isinstance(item, dict):
            logger.error(f"[检索节点] 错误: items[{idx}] 不是字典类型，type={type(item)}, value={item}")
            continue
        
        semantic_score = item.get("semantic_score", 0.5)
        
        # 计算五行匹配分
        wuxing_score = 0.0
        primary = item.get("primary_element", "")
        secondary = item.get("secondary_element")
        
        if primary in target_elements:
            wuxing_score += 0.6
        if secondary and secondary in target_elements:
            wuxing_score += 0.3
        
        # 相生加分：忌神但生喜用神的五行，给予适度加分（弱于 target 元素）
        if boost_elements:
            if primary in boost_elements:
                wuxing_score += 0.08
            if secondary and secondary in boost_elements:
                wuxing_score += 0.04
        
        # wear_count 联动：穿着次数少的物品略加分（鼓励轮换）
        wear_count = item.get("wear_count", 0)
        if wear_count is not None and isinstance(wear_count, (int, float)) and wear_count >= 0:
            wuxing_score += max(0, 0.1 - wear_count * 0.02)  # 0次=+0.1, 5次=0
        
        # 温度匹配评分
        temp_score = _calculate_temp_score(item, weather_info)
        
        # Task 01: 计算场景匹配分（新增）
        scene_score = 0.5  # 默认基础分
        if scene and scene_weight > 0:
            scene_score = calculate_scene_match_score(item, scene, sub_scene)
        
        # 计算偏好匹配分
        preference_score = 0.5  # 默认中性分
        if user_prefs and pref_weight > 0:
            try:
                preference_score = preference_service.calculate_preference_score(item, user_prefs)
            except Exception:
                preference_score = 0.5
        
        # 加权最终分数
        final_score = (
            semantic_score * semantic_weight +
            wuxing_score * wuxing_weight +
            scene_score * scene_weight +
            preference_score * pref_weight +
            temp_score * temp_weight
        )
        
        scored_items.append({
            **item,
            "semantic_score": semantic_score,
            "wuxing_score": wuxing_score,
            "scene_score": scene_score,
            "preference_score": preference_score,
            "temp_score": temp_score,
            "final_score": final_score,
        })
    
    # 过滤掉场景分为0的物品（硬排除）
    scored_items = [item for item in scored_items if item.get("scene_score", 0.5) > 0]
    
    # 温度硬过滤：极端温度下排除不合适厚度的衣物（增强版：同时检查thickness_level和名称推断）
    if weather_info:
        temp = weather_info.get("temperature")
        if temp is not None:
            temp_filtered = []
            for item in scored_items:
                thickness = item.get("thickness_level", "")
                item_name = item.get("name", "")
                
                # 数据矛盾检测：名称暗示厚重但DB标记为轻薄，以名称为准
                heavy_name_keywords = ["羽绒", "棉袄", "棉衣", "大衣", "毛呢", "羊毛"]
                if any(k in item_name for k in heavy_name_keywords):
                    thickness = "厚重"  # 名称优先级高于DB标注
                elif not thickness:
                    # 如果thickness_level缺失且名称无明确指示，从名称推断
                    if any(k in item_name for k in ["毛衣", "卫衣"]):
                        thickness = "中厚"
                    elif any(k in item_name for k in ["衬衫", "T恤", "短裤", "薄"]):
                        thickness = "轻薄"
                
                # 温度硬过滤（分层级）
                if temp >= 30:
                    # 高温：排除厚重和中厚
                    if thickness in ("厚重", "中厚"):
                        continue
                elif temp >= 25:
                    # 中高温：排除厚重
                    if thickness == "厚重":
                        continue
                elif temp <= 0:
                    # 严寒：排除极薄和轻薄
                    if thickness in ("极薄", "轻薄"):
                        continue
                elif temp <= 10:
                    # 低温：排除极薄
                    if thickness == "极薄":
                        continue
                
                temp_filtered.append(item)
            if temp_filtered:  # 只在过滤后有剩余时才应用
                scored_items = temp_filtered
    
    # 按分数排序，取 Top K
    scored_items.sort(key=lambda x: x["final_score"], reverse=True)
    top_items = scored_items[:top_k]
    
    # 分类多样性优化（含温度安全检查）
    top_items = _ensure_category_diversity(scored_items, top_k)
    
    # 五行多样性约束：确保 top-k 中至少覆盖 2 种不同五行属性
    top_items = _ensure_wuxing_diversity(top_items, scored_items, top_k)
    
    # 温度安全检查：确保推荐结果中没有极端不合适的物品
    if weather_info:
        temp = weather_info.get("temperature")
        if temp is not None and (temp <= 5 or temp >= 32):
            # 在极端温度下，替换 temp_score < 0.3 的物品
            temp_safe_items = [i for i in top_items if (i.get("temp_score") or 1.0) >= 0.3]
            if len(temp_safe_items) < len(top_items) and scored_items:
                # 从备选中找温度安全的物品补充
                used_ids = {i.get("id") for i in temp_safe_items}
                for candidate in scored_items:
                    if candidate.get("id") not in used_ids and (candidate.get("temp_score") or 0) >= 0.3:
                        temp_safe_items.append(candidate)
                        used_ids.add(candidate.get("id"))
                        if len(temp_safe_items) >= top_k:
                            break
                top_items = temp_safe_items[:top_k]
    
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
    
    # ========== 旅行/出差场景：生成多天行程规划 ==========
    travel_plan = None
    travel_days = state.get("travel_days")
    destination = state.get("destination")
    luggage_size = state.get("luggage_size", "中")
    
    if travel_days and destination and travel_days >= 2:
        # 传递更大的物品池给旅行规划器（至少20件，确保多日行程有足够多样性）
        travel_item_pool = scored_items[:max(20, top_k * 4)] if len(scored_items) > len(top_items) else scored_items
        travel_plan = _generate_travel_plan(
            state=state,
            top_items=travel_item_pool,
            travel_days=travel_days,
            destination=destination,
            luggage_size=luggage_size,
        )
        logger.info(f"[旅行规划] 生成{travel_days}天行程方案: {destination}, 物品池={len(travel_item_pool)}件")
    
    result = {"retrieved_items": top_items, "item_sources": item_sources}
    if travel_plan:
        result["travel_plan"] = travel_plan
    
    return result


def _generate_travel_plan(
    state: AgentState,
    top_items: List[Dict],
    travel_days: int,
    destination: str,
    luggage_size: str,
) -> Optional[Dict]:
    """
    生成多天旅行穿搭规划
    
    将已有的检索结果与旅行规划服务整合：
    1. 用用户八字信息构建 bazi 参数
    2. 调用 travel_recommend_service 生成多天行程
    3. 将实际检索到的衣物注入行程规划中
    
    Args:
        state: 当前 Agent 状态
        top_items: 已检索排序后的推荐物品
        travel_days: 旅行天数
        destination: 目的地城市
        luggage_size: 行李箱大小
        
    Returns:
        多天行程规划字典，失败返回 None
    """
    try:
        from apps.api.services.travel_recommend_service import generate_travel_recommendation
        from packages.utils.travel_planner import plan_travel_outfits, optimize_luggage, calculate_luggage_score
        from packages.utils.weather_forecast import get_destination_weather, predict_weather_element
        from packages.utils.wuxing_rules import WUXING_LIST
        
        # 构建八字信息
        bazi_result = state.get("bazi_result")
        bazi_info = None
        if bazi_result:
            bazi_info = {
                "suggested_elements": bazi_result.get("suggested_elements", []),
                "reasoning": bazi_result.get("reasoning"),
            }
        
        # 智能构建多天场景（第1天可穿插面板场景，其余天旅行主场景）
        scenes_per_day = _build_travel_scenes(state, travel_days)
        
        # 获取目的地天气
        weather_forecast = get_destination_weather(destination, travel_days)
        
        # 如果有实际检索到的衣物，注入到行程规划中
        available_items = None
        if top_items:
            available_items = []
            for item in top_items:
                available_items.append({
                    "id": item.get("id", item.get("item_code", "")),
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "primary_element": item.get("primary_element", ""),
                    "secondary_element": item.get("secondary_element"),
                    "functionality": item.get("functionality", []),
                    "thickness_level": item.get("thickness_level", ""),
                    "wuxing_score": item.get("wuxing_score", 0.5),
                    "final_score": item.get("final_score", 0.5),
                    "image_url": item.get("image_url"),
                    "source": item.get("source", "public"),
                })
        
        # 目标五行
        target_elements = bazi_info["suggested_elements"] if bazi_info else WUXING_LIST[:2]
        user_bazi = {
            "suggested_elements": target_elements,
            "reasoning": bazi_info.get("reasoning") if bazi_info else None,
        }
        
        # 生成多天穿搭计划
        outfits_plan = plan_travel_outfits(
            user_bazi=user_bazi,
            destination_weather=weather_forecast,
            days=travel_days,
            scenes_per_day=scenes_per_day,
            luggage_capacity=luggage_size,
            available_items=available_items,
        )
        
        # 优化行李箱
        optimized_days = optimize_luggage(outfits_plan.get("days", []), luggage_size)
        
        # 收集所有唯一物品
        all_items = []
        seen_ids = set()
        for day in optimized_days:
            for item in day.get("items", []):
                item_id = item.get("id", item.get("name", ""))
                if item_id not in seen_ids:
                    all_items.append(item)
                    seen_ids.add(item_id)
        
        # 行李评分（传入每日物品以计算天数覆盖率）
        daily_items = [day.get("items", []) for day in optimized_days]
        luggage_score = calculate_luggage_score(all_items, luggage_size, daily_items)
        
        # 五行分析
        element_distribution = {}
        for item in all_items:
            elem = item.get("primary_element", "")
            if elem:
                element_distribution[elem] = element_distribution.get(elem, 0) + 1
        
        # 天气五行
        weather_elements = []
        for wf in weather_forecast:
            weather_desc = wf.get("weather_desc", "")
            element = predict_weather_element(weather_desc)
            weather_elements.append({
                "date": wf.get("date"),
                "weather": weather_desc,
                "element": element,
            })
        
        return {
            "destination": destination,
            "days": travel_days,
            "luggage_size": luggage_size,
            "daily_plans": optimized_days,
            "luggage_summary": {
                **outfits_plan.get("luggage_summary", {}),
                "luggage_score": luggage_score,
            },
            "weather_forecast": weather_forecast,
            "wuxing_analysis": {
                "target_elements": target_elements,
                "weather_elements": weather_elements,
                "item_element_distribution": element_distribution,
                "balance_score": round(len(element_distribution) / 5.0, 3) if element_distribution else 0.0,
            },
        }
    except Exception as e:
        logger.error(f"[旅行规划] 生成失败: {e}", exc_info=True)
        return None


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
    
    # 防御性检查：过滤掉非字典类型的元素
    valid_items = []
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            valid_items.append(item)
        else:
            logger.error(f"[分类多样性] 错误: items[{idx}] 不是字典类型，type={type(item)}")
    
    if not valid_items:
        return []
    
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
    accessory_items = [item for item in valid_items if item.get("category") == "配饰"]
    
    for item in valid_items:
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


def _ensure_wuxing_diversity(items: List[Dict], all_scored: List[Dict], limit: int) -> List[Dict]:
    """
    五行多样性约束：确保推荐结果至少覆盖 2 种不同五行属性
    
    策略：
    - 如果 top-k 中所有物品都是同一五行，用次高分的不同五行物品替换最低分的重复物品
    - 最多替换 1 件，避免过度干预排序
    
    Args:
        items: 当前 top-k 物品列表
        all_scored: 所有已评分物品（已排序）
        limit: top-k 数量
    
    Returns:
        List[Dict]: 五行多样性优化后的物品列表
    """
    if len(items) < 2:
        return items
    
    # 统计当前五行分布
    elements = set()
    for item in items:
        elem = item.get("primary_element", "")
        if elem:
            elements.add(elem)
    
    # 已满足多样性（≥2 种五行），无需调整
    if len(elements) >= 2:
        return items
    
    # 找出当前主导五行
    dominant_element = elements.pop() if elements else None
    
    # 从备选物品中找分数最高的不同五行物品
    used_ids = {str(item.get("id", item.get("item_code", ""))) for item in items}
    best_replacement = None
    for candidate in all_scored:
        cand_elem = candidate.get("primary_element", "")
        cand_id = str(candidate.get("id", candidate.get("item_code", "")))
        if cand_elem and cand_elem != dominant_element and cand_id not in used_ids:
            best_replacement = candidate
            break
    
    if best_replacement:
        # 替换分数最低的重复五行物品
        for i in range(len(items) - 1, -1, -1):
            if items[i].get("primary_element", "") == dominant_element:
                logger.debug(
                    f"[五行多样性] 替换: {items[i].get('name')}({dominant_element}) "
                    f"→ {best_replacement.get('name')}({best_replacement.get('primary_element')})"
                )
                items[i] = best_replacement
                break
    
    return items


def _get_versatile_items(target_elements: List[str], limit: int) -> List[Dict]:
    """
    获取百搭单品兜底
    
    当数据库无匹配结果时，返回中性百搭的单品
    """
    # 百搭单品特征：土属性（中性、包容）+ 基础色
    versatile_query = "百搭 中性 基础款 黑色 白色 灰色 米色 舒适"
    
    items = _vector_search(versatile_query, limit=limit)
    
    return items if items else []


def _calculate_temp_score(item: Dict, weather_info: Optional[Dict]) -> float:
    """计算物品的温度适配分（0.0-1.0）"""
    if not weather_info:
        return 0.5
    
    temp = weather_info.get("temperature")
    if temp is None:
        return 0.5
    
    score = 0.5
    thickness = item.get("thickness_level", "")
    functionality = item.get("functionality", [])
    if isinstance(functionality, str):
        import json
        try:
            functionality = json.loads(functionality)
        except Exception:
            functionality = []
    
    # 高温场景
    if temp >= 30:
        if thickness in ("极薄", "轻薄"):
            score += 0.3
        elif thickness == "适中":
            score += 0.1
        elif thickness in ("中厚", "厚重"):
            score -= 0.3
        if any(f in functionality for f in ["透气", "速干", "防晒"]):
            score += 0.2
    # 低温场景
    elif temp <= 5:
        if thickness in ("厚重", "中厚"):
            score += 0.3
        elif thickness == "适中":
            score += 0.1
        elif thickness in ("极薄", "轻薄"):
            score -= 0.3
        if any(f in functionality for f in ["保暖", "防风"]):
            score += 0.2
    # 适中温度
    else:
        if thickness == "适中":
            score += 0.2
    
    return max(0.0, min(1.0, score))


def _build_travel_scenes(state: AgentState, travel_days: int) -> List[str]:
    """
    构建多天旅行场景列表（多样化）
    
    策略：第1天可安排面板场景，其余天使用旅行主场景
    """
    panel_scene = state.get("scene")
    user_input = state.get("user_input", "")
    
    # 从用户输入提取旅行主场景
    from packages.utils.scene_mapper import extract_scene_multidimensional
    travel_scene_data = extract_scene_multidimensional(user_input)
    travel_main_scene = travel_scene_data.get("main_scene", "旅行")
    
    scenes = []
    for day in range(travel_days):
        if day == 0 and panel_scene and panel_scene != travel_main_scene:
            # 第1天安排面板选择的场景（如商务）
            scenes.append(panel_scene)
        else:
            # 其余天使用旅行主场景
            scenes.append(travel_main_scene)
    
    return scenes


# 全局模型单例
_EMBEDDING_MODEL = None

# Embedding 缓存（LRU，最多缓存 256 条，避免重复调用 DashScope API）
_EMBEDDING_CACHE: Dict[str, list] = {}
_EMBEDDING_CACHE_MAX = 256


def _get_embedding_model():
    """获取 embedding 模型（使用 DashScope API，无需本地模型）"""
    return None


def _encode_text_with_dashscope(text: str) -> list:
    """
    使用 DashScope API 生成文本向量（带 LRU 缓存）
    
    相同文本不会重复调用 API，直接返回缓存结果。
    缓存满时自动淘汰最早插入的条目。
    
    Args:
        text: 输入文本
        
    Returns:
        embedding 向量 (1024 维)
    """
    # 查缓存
    if text in _EMBEDDING_CACHE:
        logger.debug(f"[Embedding缓存] 命中: {text[:30]}...")
        return _EMBEDDING_CACHE[text]
    
    import dashscope
    from dashscope import TextEmbedding
    
    # 确保使用国际端点
    if 'intl' in settings.dashscope_base_url:
        dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'
    
    response = TextEmbedding.call(
        model='text-embedding-v3',
        input=text
    )
    
    if response.status_code == 200:
        result = response.output['embeddings'][0]['embedding']
        # 写入缓存（超限时删除最早的一条）
        if len(_EMBEDDING_CACHE) >= _EMBEDDING_CACHE_MAX:
            oldest_key = next(iter(_EMBEDDING_CACHE))
            del _EMBEDDING_CACHE[oldest_key]
        _EMBEDDING_CACHE[text] = result
        return result
    else:
        raise Exception(f"DashScope embedding API error: {response.code} - {response.message}")


def _vector_search(
    query: str, 
    limit: int = 20, 
    user_gender: Optional[str] = None,
    weather_info: Optional[Dict] = None,
    scene: Optional[str] = None,  # 新增场景参数
    sub_scene: Optional[str] = None  # 新增子场景参数
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
        sub_scene: 子场景名称，用于更精细的过滤
    """
    import numpy as np
    
    # 使用 DashScope API 生成查询向量
    query_embedding = _encode_text_with_dashscope(query)
    query_vector = np.array(query_embedding, dtype=np.float32)
    
    # 数据库查询
    items = []
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                # 性别过滤逻辑（优化：无性别时默认排除女性专属物品）
                if user_gender == "男":
                    gender_filter = "AND (gender = '中性' OR gender = '男')"
                elif user_gender == "女":
                    gender_filter = "AND (gender = '中性' OR gender = '女')"
                else:
                    # 未指定性别时，排除女性专属物品（gender='女'），保留中性+男性
                    gender_filter = "AND (gender = '中性' OR gender = '男' OR gender IS NULL)"
                
                # 天气过滤逻辑
                weather_filter = _build_weather_filter(weather_info)
                
                # 场景过滤逻辑（新增）
                scene_filter = _build_scene_filter(scene, sub_scene)
                
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
                vector_list = query_vector.tolist()
                cur.execute(sql, (vector_list, vector_list, limit))
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
                        "semantic_score": float(row[13]) if len(row) > 13 and row[13] else 0.5,
                        "source": "public",
                    })
    except Exception as e:
        import traceback
        logger.error(f"[Agent] 向量搜索失败: {e}")
        logger.error(f"[Agent] 错误堆栈: {traceback.format_exc()}")
    
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
    
    # 天气状况过滤（软过滤：不硬性排除，只在 SQL 中不添加过滤条件）
    # 天气过滤已移至评分逻辑中处理，这里不再硬性过滤
    # 原因：硬过滤会导致结果过少，应该让向量搜索先返回结果，再根据天气评分
    if weather_desc:
        weather_desc_lower = weather_desc.lower()
        
        # 注释掉硬过滤，改为在评分时考虑天气因素
        # if any(kw in weather_desc_lower for kw in ['雨', '雪', '阴雨']):
        #     conditions.append(
        #         "(applicable_weather ? '雨天' OR "
        #         "functionality->>'防水' = 'true' OR "
        #         "applicable_weather ? '多云')"
        #     )
        # elif any(kw in weather_desc_lower for kw in ['晴', '晴朗']):
        #     conditions.append(
        #         "(applicable_weather ? '晴天' OR "
        #         "functionality->>'防晒' = 'true' OR "
        #         "applicable_weather ? '温和')"
        #     )
    
    return " AND ".join(conditions) if conditions else ""


def _build_scene_filter(scene: Optional[str], sub_scene: Optional[str] = None) -> str:
    """
    构建场景过滤SQL条件（统一从 scene_mapping.py 读取规则）
    
    消除原先硬编码的 scene_exclusions 字典与 scene_mapping.py 的不同步问题。
    所有场景的 excluded_categories / excluded_keywords 统一来源于 SCENE_MAPPING。
    
    Args:
        scene: 场景名称
        sub_scene: 子场景名称（可选）
    
    Returns:
        str: SQL过滤条件
    """
    if not scene:
        return ""
    
    from packages.utils.scene_mapping import get_scene_rules, get_sub_scene_rules
    
    rules = get_scene_rules(scene)
    if not rules:
        return ""
    
    conditions = []
    
    # 1. 排除特定类别（来自 SCENE_MAPPING.excluded_categories）
    excluded_cats = rules.get("excluded_categories", [])
    if excluded_cats:
        categories_str = ",".join([f"'{cat}'" for cat in excluded_cats])
        conditions.append(f"category NOT IN ({categories_str})")
    
    # 2. 排除包含特定关键词的衣物（来自 SCENE_MAPPING.excluded_keywords）
    excluded_kws = rules.get("excluded_keywords", [])
    if excluded_kws:
        keyword_conditions = []
        for keyword in excluded_kws:
            keyword_conditions.append(f"name NOT LIKE '%%{keyword}%%'")
        conditions.append(" AND ".join(keyword_conditions))
    
    # 2.1 子场景特殊排除关键词
    if sub_scene:
        sub_rules = get_sub_scene_rules(sub_scene)
        if sub_rules and "extra_excluded_keywords" in sub_rules:
            for keyword in sub_rules["extra_excluded_keywords"]:
                conditions.append(f"name NOT LIKE '%%{keyword}%%'")
    
    # 3. 排除特定厚度的衣物（基于 preferred_thickness 的反向过滤）
    # 仅当场景明确指定了 preferred_thickness 时，排除不在列表中的厚度
    preferred_thickness = rules.get("preferred_thickness", [])
    if preferred_thickness and scene in ("运动", "度假"):
        # 仅对极端场景做硬过滤：运动排除厚重，度假排除厚重
        all_thickness = ["极薄", "轻薄", "适中", "中厚", "厚重"]
        exclude_thickness = [t for t in all_thickness if t not in preferred_thickness]
        if exclude_thickness:
            thickness_str = ",".join([f"'{t}'" for t in exclude_thickness])
            conditions.append(f"thickness_level NOT IN ({thickness_str})")
    
    # 4. 运动场景功能硬过滤（来自 SCENE_MAPPING.preferred_functionality）
    if scene == "运动":
        preferred_funcs = rules.get("preferred_functionality", [])
        sport_funcs = [f for f in preferred_funcs if f in ("透气", "速干", "运动", "弹性")]
        if sport_funcs:
            func_conditions = []
            for func in sport_funcs:
                func_conditions.append(f"(functionality->>'{func}')::boolean = true")
            if func_conditions:
                conditions.append(f"({' OR '.join(func_conditions)})")
    
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
    
    # 推荐物品的天气特性（增强版：包含材质、风格、五行等全维度信息）
    if retrieved_items:
        item_features = []
        for item in retrieved_items[:5]:
            features = []
            thickness = item.get("thickness_level")
            functionality = item.get("functionality", {})
            material = item.get("material", "")
            style = item.get("style", "")
            
            if thickness:
                features.append(f"厚度【{thickness}】")
            if material:
                features.append(f"材质【{material}】")
            
            # 功能性（处理列表和字典两种情况）
            funcs = []
            if isinstance(functionality, dict):
                for key in ["防水", "透气", "保暖", "防晒", "抗皱", "速干", "弹性"]:
                    if functionality.get(key):
                        funcs.append(key)
            elif isinstance(functionality, list):
                for func in functionality:
                    if func in ["防水", "透气", "保暖", "防晒", "抗皱", "速干", "弹性"]:
                        funcs.append(func)
            
            if funcs:
                features.append(f"功能【{'、'.join(funcs)}】")
            
            if features:
                item_features.append(f"{item['name']}：{' | '.join(features)}")
        
        if item_features:
            details.append("推荐物品特性：" + "；".join(item_features[:5]))
    
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
    boost_elements = state.get("boost_elements", [])  # 相生辅助五行
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
    
    # 注入流年/大运信息到八字推理文本
    annual_luck = state.get("annual_luck")
    major_luck = state.get("major_luck")
    if annual_luck:
        annual_info = annual_luck.get("annual_luck", {})
        annual_score = annual_luck.get("overall_score", 0)
        annual_advice = annual_luck.get("outfit_advice", "")
        bazi_reasoning += f"\n流年: {annual_info.get('ganzhi', '')}({annual_info.get('element', '')})，综合运势{annual_score}分。{annual_advice}"
    if major_luck:
        bazi_reasoning += f"\n当前大运: {major_luck.get('ganzhi', '')}({major_luck.get('element', '')})，旺衰: {major_luck.get('luck_level', '')}"
        
    # 清晰标识各因素是否存在
    scene_display = scene if scene else "无"
    weather_display = weather_element if weather_element else "无"
    has_bazi = "有" if bazi_result else "无"
    has_weather = "有" if weather_element else "无"
    has_scene = "有" if scene else "无"
    
    # 构建天气详情
    weather_details = _build_weather_details(weather_info, retrieved_items)
    
    # 旅行上下文增强：如果有多天行程规划，注入到用户输入中
    travel_plan = state.get("travel_plan")
    effective_user_input = user_input
    if travel_plan:
        destination = travel_plan.get("destination", "")
        days = travel_plan.get("days", 0)
        luggage_score = travel_plan.get("luggage_summary", {}).get("luggage_score", 0)
        luggage_size = travel_plan.get("luggage_size", "中")
        travel_context = (
            f"\n\n[旅行信息] 这是一次去{destination}的{days}天行程，"
            f"行李箱大小：{luggage_size}，行李评分：{luggage_score:.0%}。"
        )
        # 添加每日天气摘要（仅在用户未明确指定天气时作为主要参考）
        weather_forecast = travel_plan.get("weather_forecast", [])
        if weather_forecast and not weather_info:
            # 用户未指定天气，使用行程天气预报
            weather_summary = "、".join([
                f"第{i+1}天{w.get('weather_desc', '?')}({w.get('temperature_min', '?')}~{w.get('temperature_max', '?')}°C)"
                for i, w in enumerate(weather_forecast[:days])
            ])
            travel_context += f"\n目的地天气：{weather_summary}"
        elif weather_forecast and weather_info:
            # 用户已指定天气，行程天气仅作参考，以用户指定为准
            user_temp = weather_info.get("temperature")
            travel_context += f"\n用户指定天气条件：{user_temp}°C（以此为准，行程天气预报仅作参考）"
        effective_user_input = user_input + travel_context
        
    # 构建"场景/天气加成"的完整指令文本（避免 LLM 误判条件）
    added_elements_str = "、".join(added_elements) if added_elements else ""
    if added_elements_str:
        added_instruction = f'接着说"结合【场景/天气】，再加入【{added_elements_str}】元素..."'
    else:
        added_instruction = '不要提及"再加入"或场景加成元素'
    
    # 构建"辅助加分"指令（boost_elements：忌神但生喜用神，不可作为正面推荐）
    boost_elements_str = "、".join(boost_elements) if boost_elements else ""
    if boost_elements_str:
        boost_instruction = f'注意：【{boost_elements_str}】为辅助加分元素（虽生喜用神，但属相克关系），可少量提及提升专业感/气场，不可作为主推荐元素，不可说"推荐穿X色"'
    else:
        boost_instruction = '无辅助加分元素'
    
    prompt_template = load_prompt("generator.txt")
    prompt = prompt_template.format(
        user_input=effective_user_input,
        scene=scene_display,
        weather_element=weather_display,
        target_elements="、".join(target_elements) if target_elements else "综合推荐",
        xiyong_elements="、".join(xiyong_elements) if xiyong_elements else "无",
        added_elements=added_elements_str or "无",
        added_instruction=added_instruction,
        boost_instruction=boost_instruction,
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
            max_tokens=200,  # 优化：从 300 降低到 200，理由通常不需要这么多
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
    boost_elements = state.get("boost_elements", [])  # 相生辅助五行
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
    
    # 注入流年/大运信息到八字推理文本
    annual_luck = state.get("annual_luck")
    major_luck = state.get("major_luck")
    if annual_luck:
        annual_info = annual_luck.get("annual_luck", {})
        annual_score = annual_luck.get("overall_score", 0)
        annual_advice = annual_luck.get("outfit_advice", "")
        bazi_reasoning += f"\n流年: {annual_info.get('ganzhi', '')}({annual_info.get('element', '')})，综合运势{annual_score}分。{annual_advice}"
    if major_luck:
        bazi_reasoning += f"\n当前大运: {major_luck.get('ganzhi', '')}({major_luck.get('element', '')})，旺衰: {major_luck.get('luck_level', '')}"
    
    # 清晰标识各因素是否存在
    scene_display = scene if scene else "无"
    weather_display = weather_element if weather_element else "无"
    has_bazi = "有" if bazi_result else "无"
    has_weather = "有" if weather_element else "无"
    has_scene = "有" if scene else "无"
    
    # 构建天气详情
    weather_details = _build_weather_details(weather_info, retrieved_items)
    
    # 旅行上下文增强
    travel_plan = state.get("travel_plan")
    effective_user_input = user_input
    if travel_plan:
        destination = travel_plan.get("destination", "")
        days = travel_plan.get("days", 0)
        luggage_score = travel_plan.get("luggage_summary", {}).get("luggage_score", 0)
        luggage_size = travel_plan.get("luggage_size", "中")
        travel_context = (
            f"\n\n[旅行信息] 这是一次去{destination}的{days}天行程，"
            f"行李箱大小：{luggage_size}，行李评分：{luggage_score:.0%}。"
        )
        weather_forecast = travel_plan.get("weather_forecast", [])
        if weather_forecast:
            weather_summary = "、".join([
                f"第{i+1}天{w.get('weather_desc', '?')}({w.get('temperature_min', '?')}~{w.get('temperature_max', '?')}°C)"
                for i, w in enumerate(weather_forecast[:days])
            ])
            travel_context += f"\n目的地天气：{weather_summary}"
        effective_user_input = user_input + travel_context
    
    # 构建"场景/天气加成"的完整指令文本（避免 LLM 误判条件）
    added_elements_str = "、".join(added_elements) if added_elements else ""
    if added_elements_str:
        added_instruction = f'接着说"结合【场景/天气】，再加入【{added_elements_str}】元素..."'
    else:
        added_instruction = '不要提及"再加入"或场景加成元素'
    
    # 构建"辅助加分"指令（boost_elements：忌神但生喜用神，不可作为正面推荐）
    boost_elements_str = "、".join(boost_elements) if boost_elements else ""
    if boost_elements_str:
        boost_instruction = f'注意：【{boost_elements_str}】为辅助加分元素（虽生喜用神，但属相克关系），可少量提及提升专业感/气场，不可作为主推荐元素，不可说"推荐穿X色"'
    else:
        boost_instruction = '无辅助加分元素'
    
    prompt_template = load_prompt("generator.txt")
    prompt = prompt_template.format(
        user_input=effective_user_input,
        scene=scene_display,
        weather_element=weather_display,
        target_elements="、".join(target_elements) if target_elements else "综合推荐",
        xiyong_elements="、".join(xiyong_elements) if xiyong_elements else "无",
        added_elements=added_elements_str or "无",
        added_instruction=added_instruction,
        boost_instruction=boost_instruction,
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
    bazi_reasoning = bazi_result.get("reasoning") if bazi_result else None
    
    # 注入流年/大运信息到 bazi_reasoning
    if bazi_reasoning:
        annual_luck = state.get("annual_luck")
        major_luck = state.get("major_luck")
        if annual_luck:
            annual_info = annual_luck.get("annual_luck", {})
            annual_score = annual_luck.get("overall_score", 0)
            bazi_reasoning += f" 流年{annual_info.get('ganzhi', '')}({annual_info.get('element', '')})运势{annual_score}分。"
        if major_luck:
            bazi_reasoning += f" 当前大运{major_luck.get('ganzhi', '')}({major_luck.get('element', '')})，旺衰{major_luck.get('luck_level', '')}。"
    
    analysis = {
        "target_elements": target_elements,
        "bazi_reasoning": bazi_reasoning,
        "intent_reasoning": intent_result.get("reasoning") if intent_result else None,
        "scene": scene,
        "boost_elements": state.get("boost_elements", []),
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
    
    # 优化：包含旅行行程规划（如果有）
    travel_plan = state.get("travel_plan")
    if travel_plan:
        final_response["travel_plan"] = travel_plan
    
    return {"final_response": final_response}
