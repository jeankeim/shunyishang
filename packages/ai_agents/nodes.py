"""
LangGraph Agent 节点函数
包含 4 个核心节点：analyze_intent, retrieve_items, generate_advice, format_output
"""

import os
import re
import time
import json
import hashlib
import random
import logging
from typing import Dict, List, Optional, Generator, Any
from pathlib import Path

from openai import OpenAI, APITimeoutError, APIError, RateLimitError

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.core.cache import cache as redis_cache
from apps.api.core.retry import llm_retry
from apps.api.services.llm_usage_service import extract_llm_usage, merge_llm_usage
from packages.ai_agents.state import AgentState
from packages.ai_agents.wardrobe_client import wardrobe_client
from packages.utils.bazi_calculator import (
    calculate_bazi,
    infer_elements_from_text,
    extract_explicit_element_intent,
    merge_recommendations,
)
from packages.utils.anchor_item import (
    extract_anchor_specs,
    find_anchor_item,
    item_conflicts_with_anchor,
)
from packages.utils.destiny_calculator import (
    analyze_year_fortune,
    get_current_major_luck,
)
from packages.utils.scene_mapper import (
    extract_scene_multidimensional,
    get_scene_elements,
    get_color_by_element,
    build_search_query,
)
from packages.recommendation.engine import score_and_rank_items
from packages.recommendation.filters import (
    build_weather_filter as _build_weather_filter,
    build_scene_filter as _build_scene_filter,
    build_gender_filter as _build_gender_filter,
)

logger = logging.getLogger(__name__)

# ============================================================
# LLM 配置与重试机制
# ============================================================
# 默认重试参数（优化：减少重试次数，加快失败响应）
DEFAULT_MAX_RETRIES = 1  # 从 3 降低到 1，失败快速降级
DEFAULT_MIN_WAIT = 0.5  # 秒（优化：从 1.0 降低到 0.5，加快重试）
DEFAULT_MAX_WAIT = 1.5  # 秒（优化：从 3.0 降低到 1.5）

# 推荐五行数量上限（与 merge_recommendations 的截断保持一致，避免流年等增强突破上限）
MAX_TARGET_ELEMENTS = 3


def _canonical_item_key(item: Dict) -> str:
    """
    生成物品在 item_sources 中的统一 key。

    统一规则：优先用 item_code（公共库稳定编码），缺失时回退到 str(id)。
    避免衣橱物品用 id、公共库物品用 item_code 造成的键不一致。
    """
    return item.get("item_code") or str(item.get("id"))


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
    include_usage: bool = False,
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
                stream_kwargs: Dict = {}
                if include_usage:
                    # 流式末尾追加仅含 usage 的 chunk，用于成本核算
                    stream_kwargs["stream_options"] = {"include_usage": True}
                return client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=True,
                    **stream_kwargs,
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
            # 生成缓存键：基于用户出生信息（含性别，避免男女同生辰串号）
            bazi_cache_key = f"bazi:{bazi_input['birth_year']}:{bazi_input['birth_month']}:{bazi_input['birth_day']}:{bazi_input['birth_hour']}:{bazi_input.get('gender', '')}"
            
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
                # P3-52 年龄精确计算：考虑今年生日是否已过，避免大运判断误差 1 岁
                birth_month = bazi_input.get("birth_month")
                birth_day = bazi_input.get("birth_day")
                current_age = current_year - birth_year
                today = date.today()
                try:
                    if birth_month and birth_day:
                        birthday_this_year = date(current_year, int(birth_month), int(birth_day))
                        if today < birthday_this_year:
                            current_age -= 1  # 今年生日还未到，周岁减 1
                except (ValueError, TypeError):
                    pass  # 非法月/日（如 2 月 30 日）保持原估算
                gender = bazi_input.get("gender", "男")
                major_luck_data = get_current_major_luck(
                    bazi_result, gender, current_age,
                    birth_year=birth_year,
                    birth_month=birth_month,
                    birth_day=birth_day,
                )
                logger.info(f"[Agent] 当前大运: {major_luck_data}")
        except Exception as e:
            logger.warning(f"[Agent] 流年/大运计算失败: {e}")
    
    # 2. 意图推断
    intent_result = infer_elements_from_text(user_input)

    # 2.0 LLM token 用量累加器（成本核算，随状态传递给后续节点/调用方）
    usage_sink: Dict = {}

    # 2.1 显式五行修正意图（用户实时意图，最高优先级，可覆盖八字预设）
    explicit_intent = extract_explicit_element_intent(user_input)
    if explicit_intent["add"] or explicit_intent["avoid"]:
        logger.info(f"[Agent] 检测到用户显式五行意图: {explicit_intent}")

    # 2.2 锚点单品识别（用户显式指定某件单品，如「白衬衫和什么搭配」，支持多锚点）
    anchor_specs = extract_anchor_specs(user_input)
    if anchor_specs:
        logger.info(
            f"[Agent] 检测到锚点单品: "
            f"{'、'.join(s['phrase'] for s in anchor_specs)}"
        )

    # 3. Task 03: 提取场曷（多维度识别）
    scene_data = extract_scene_multidimensional(user_input)
    scene = state.get("scene") or scene_data.get("main_scene")
    sub_scene = scene_data.get("sub_scene")  # 子场景
    emotion = scene_data.get("emotion")  # 情感倾向
    
    scene_result = get_scene_elements(scene) if scene else None
    
    # 4. 合并推荐五行（显式意图 + 八字 + 场景 + 意图 + 天气）
    weather_element = state.get("weather_element")
    target_elements, boost_elements = merge_recommendations(
        bazi_result=bazi_result,
        intent_result=intent_result,
        scene_result=scene_result,
        weather_element=weather_element,
        explicit_intent=explicit_intent,
    )

    # P3-56 防御：八字已计算但 suggested_elements 为空时，target 可能全空，
    # 导致后续五行评分全 0、退化到纯 semantic 排序，丢失命理推荐意义。
    # 此时用五行全集（金木水火土）减去忌神，按固定优先级补充兜底。
    _WUXING_UNIVERSE = ["金", "木", "水", "火", "土"]
    if bazi_result and not bazi_result.get("suggested_elements") and not target_elements:
        avoid_set = set(bazi_result.get("avoid_elements", []))
        fallback = [e for e in _WUXING_UNIVERSE if e not in avoid_set]
        target_elements = fallback[:MAX_TARGET_ELEMENTS]
        logger.warning(
            f"[Agent] P3-56 触发: 八字 suggested_elements 为空，"
            f"使用五行全集-忌神兜底 target_elements={target_elements}"
        )
        
    # 4.1 区分喜用神与场景/天气添加的五行
    xiyong_elements = bazi_result["suggested_elements"] if bazi_result else []

    # 计算场景/天气额外添加的五行（显式意图属于用户实时意图，不计入场景加成）
    added_elements = []
    for elem in target_elements:
        if elem not in xiyong_elements and elem not in explicit_intent["add"]:
            added_elements.append(elem)
    
    # 4.2 流年运势增强：将流年幸运元素加入推荐五行（优先级低于喜用神）
    # 注意：target_elements 在 merge_recommendations 中已截断为最多 MAX_TARGET_ELEMENTS 个，
    # 流年元素只能填充剩余名额，不得突破上限，避免五行数量失控、评分被稀释。
    if annual_luck_data:
        annual_lucky_elements = annual_luck_data.get("lucky_elements", [])
        avoid_elements = bazi_result.get("avoid_elements", []) if bazi_result else []
        for elem in annual_lucky_elements[:2]:  # 最多取前2个流年幸运元素
            if len(target_elements) >= MAX_TARGET_ELEMENTS:
                logger.info(f"[Agent] 流年增强: target 已达上限 {MAX_TARGET_ELEMENTS}，跳过 {elem}")
                break
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
            target_elements=target_elements,
            usage_sink=usage_sink,
        )
    
    return {
        "scene": scene,
        "sub_scene": sub_scene,  # Task 03: 子场景
        "emotion": emotion,  # Task 03: 情感倾向
        "bazi_result": bazi_result,
        "annual_luck": annual_luck_data,
        "major_luck": major_luck_data,
        "intent_result": intent_result,
        "explicit_intent": explicit_intent,
        "anchor_spec": anchor_specs[0] if anchor_specs else None,
        "anchor_specs": anchor_specs,
        "target_elements": target_elements,
        "xiyong_elements": xiyong_elements,
        "added_elements": added_elements,
        "boost_elements": boost_elements,
        "search_query": search_query,
        "llm_token_usage": usage_sink or None,
    }


def _enhance_query_with_llm(
    user_input: str,
    scene: Optional[str],
    bazi_result: Optional[Dict],
    target_elements: List[str],
    usage_sink: Optional[Dict] = None,
) -> str:
    """使用 LLM 增强搜索查询（带重试机制）

    Args:
        usage_sink: 可选，传入 dict 时将本次调用的 token 用量累加其中（成本核算）
    """
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

        if usage_sink is not None:
            merged = merge_llm_usage(usage_sink, extract_llm_usage(response))
            if merged:
                usage_sink.clear()
                usage_sink.update(merged)

        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"[Agent] LLM 增强查询失败（重试后）: {e}")
        # 降级：直接使用用户输入
        return user_input


# ============================================================
# Node B: retrieve_items_node
# ============================================================
@llm_retry(max_attempts=3, min_wait=1.0, max_wait=6.0)
def _embed_query_with_retry(text: str) -> list:
    """
    带指数退避重试的查询向量生成（衣橱/混合模式用）。

    向量 API 出现超时/限流/连接抖动时自动重试 2 次（1s→2s 退避）；
    3 次仍失败会抛出异常，由调用方决定降级策略。
    公共库走的是另一套带缓存的 _encode_text_with_dashscope，不经过这里。
    """
    from apps.api.services.embedding_service import embedding_service

    max_attempts = 3
    last_error = None
    for attempt in range(max_attempts):
        try:
            return embedding_service.generate_embedding(text)
        except Exception as e:
            last_error = e
            if attempt < max_attempts - 1:
                backoff = 2 ** attempt  # 1s → 2s
                logger.warning(
                    f"[向量生成] 第 {attempt + 1}/{max_attempts} 次失败，{backoff}s 后重试: {e}"
                )
                time.sleep(backoff)
            else:
                logger.error(
                    f"[向量生成] 重试 {max_attempts} 次仍失败: {e}", exc_info=True
                )
    raise last_error


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
    batch_index = state.get("batch_index", 0)  # 换一批：批次索引
    anchor_spec = state.get("anchor_spec")  # 用户显式指定的锚点单品
    anchor_specs = state.get("anchor_specs") or (
        [anchor_spec] if anchor_spec else []
    )  # 多锚点列表（兼容单锚点字段）
    
    if not search_query:
        return {"error": "搜索查询为空", "retrieved_items": [], "item_sources": {}}
    
    # ========== 获取用户不喜欢的物品列表（推荐时排除）==========
    disliked_item_codes = set()
    if user_id:
        try:
            from apps.api.core.database import DatabasePool as _DBPool
            with _DBPool.get_connection() as _conn:
                with _conn.cursor() as _cur:
                    _cur.execute(
                        "SELECT item_code FROM user_disliked_items WHERE user_id = %s",
                        [user_id]
                    )
                    disliked_item_codes = {row[0] for row in _cur.fetchall()}
        except Exception:
            pass
    
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
        # embedding 服务异常（如向量 API 超时/限流）时：先自动重试；
        # 重试仍失败则不再直接报错中断，而是【降级到公共库】并带 retrieval_fallback
        # 标志，让前端明确告知用户"衣橱暂时不可用，已临时用公共库"。
        try:
            query_embedding = _embed_query_with_retry(search_query)
        except Exception as e:
            logger.error(f"[衣橱检索] 向量生成重试后仍失败，降级公共库: {e}", exc_info=True)
            public_items = _vector_search(
                search_query,
                limit=50,
                user_gender=user_gender,
                weather_info=weather_info,
                scene=scene,
                sub_scene=sub_scene,
            )
            for item in public_items:
                item["source"] = "public"
                item["source_label"] = "🛒 建议"
                item_sources[_canonical_item_key(item)] = "public"
            return {
                "retrieved_items": public_items,
                "item_sources": item_sources,
                # 通知：前端据此提示"衣橱暂时不可用，已切公共库"
                "retrieval_fallback": "wardrobe_to_public",
            }
        
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
            item_sources[_canonical_item_key(item)] = "wardrobe"
            item["source"] = "wardrobe"
            item["source_label"] = "🏠 自有"
    
    elif retrieval_mode == "hybrid":
        # 模式 C: 混合推荐 - 优先衣橱，不足补充公共库
        if user_id and not wardrobe_client.check_wardrobe_empty(user_id):
            # 生成查询向量
            # 混合模式下 embedding 失败时跳过衣橱检索，继续用公共库兜底，
            # 避免异常中断整个推荐流程（先重试，仍失败再降级）。
            try:
                query_embedding = _embed_query_with_retry(search_query)
                
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
                    item_sources[_canonical_item_key(item)] = "wardrobe"
                    item["source"] = "wardrobe"
                    item["source_label"] = "🏠 自有"
            except Exception as e:
                logger.error(f"[混合检索] 衣橱检索失败，降级为公共库: {e}", exc_info=True)
        
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
                item_sources[_canonical_item_key(item)] = "public"
            
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
            item_sources[_canonical_item_key(item)] = "public"
    
    # ========== 配饰辅路召回（双路召回策略） ==========
    # 主路向量检索偏服装语义，配饰天然语义距离远，需辅路补充
    # 场景校验：若当前场景规则明确排除配饰/饰品类（如运动），跳过辅路召回，
    # 避免配饰绕过场景过滤漏入结果（bad case：健身场景推荐木戒指）
    _accent_blocked_by_scene = False
    if scene and retrieval_mode in ("public", "hybrid") and target_elements:
        try:
            from packages.utils.scene_mapping import get_scene_rules
            _scene_rules = get_scene_rules(scene) or {}
            _excluded_cats = set(_scene_rules.get("excluded_categories", []))
            if _excluded_cats & {"配饰", "饰品", "文玩"}:
                _accent_blocked_by_scene = True
                logger.info(f"[配饰辅路] 场景「{scene}」排除配饰类，跳过辅路召回")
        except Exception:
            pass

    if retrieval_mode in ("public", "hybrid") and target_elements and not _accent_blocked_by_scene:
        existing_ids = {item.get("item_code") for item in items}
        accent_items = _search_accent_items(
            target_elements=target_elements,
            user_gender=user_gender,
            limit=5,
            exclude_ids=existing_ids,
        )
        for item in accent_items:
            item["source"] = "public"
            item["source_label"] = "🛒 建议"
            item_sources[_canonical_item_key(item)] = "public"
            items.append(item)

    # ========== 后续处理（保持原有逻辑） ==========
    
    # 过滤用户不喜欢的物品
    if disliked_item_codes:
        before_count = len(items)
        items = [item for item in items if item.get("item_code") not in disliked_item_codes]
        if before_count != len(items):
            logger.info(f"[不喜欢过滤] 排除了 {before_count - len(items)} 件用户不喜欢的物品")

    # ========== 锚点物品硬约束（用户显式指定单品，支持多锚点） ==========
    # 用户已拥有锚点物品，推荐结果应为搭配件；
    # 排除同品类冲突物品，避免与锚点冲突（如指定白衬衫却推其他颜色衬衫）
    anchor_items: List[Dict] = []
    if anchor_specs:
        for spec in anchor_specs:
            matched = find_anchor_item(spec, user_gender=user_gender)
            if matched:
                anchor_items.append(matched)
        before_count = len(items)
        items = [
            i for i in items
            if not any(item_conflicts_with_anchor(i, s) for s in anchor_specs)
        ]
        logger.info(
            f"[锚点约束] {'、'.join(s['phrase'] for s in anchor_specs)} → 排除"
            f" {before_count - len(items)} 件冲突物品"
            + (
                f"，库内匹配锚点 {[a['item_code'] for a in anchor_items]}"
                if anchor_items else "，库内无精确匹配（仅排除）"
            )
        )
    
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
        fallback_items = _get_versatile_items(target_elements, top_k, user_gender=user_gender)
        if anchor_specs:
            fallback_items = [
                i for i in fallback_items
                if not any(item_conflicts_with_anchor(i, s) for s in anchor_specs)
            ]
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
    user_skin_tone: Optional[str] = None
    user_style_preference: Optional[str] = None
    user_body_type: Optional[str] = None
    if user_id:
        try:
            from apps.api.services.preference_service import preference_service
            user_prefs = preference_service.get_user_preferences(user_id)
        except Exception as e:
            logger.warning(f"[检索节点] 获取用户偏好失败: {e}")
        # Week 4: 获取用户审美画像信息（肤色/风格/体型）
        try:
            from apps.api.core.database import DatabasePool
            with DatabasePool.get_connection() as _conn:
                with _conn.cursor() as _cur:
                    _cur.execute(
                        "SELECT skin_tone, style_preference, body_type FROM users WHERE id = %s",
                        [user_id]
                    )
                    _row = _cur.fetchone()
                    if _row:
                        if _row[0]:
                            user_skin_tone = _row[0]
                        if _row[1]:
                            user_style_preference = _row[1]
                        if _row[2]:
                            user_body_type = _row[2]
        except Exception:
            pass

    # ========== 委托推荐引擎完成评分/过滤/排序/多样性 ==========
    engine_result = score_and_rank_items(
        items=items,
        target_elements=target_elements,
        boost_elements=boost_elements,
        bazi_result=bazi_result,
        scene=scene,
        sub_scene=sub_scene,
        weather_info=weather_info,
        user_id=user_id,
        user_prefs=user_prefs,
        user_skin_tone=user_skin_tone,
        user_style_preference=user_style_preference,
        user_body_type=user_body_type,
        user_gender=user_gender,
        top_k=top_k,
        batch_index=batch_index,
        retrieval_mode=retrieval_mode,
    )
    scored_items = engine_result["scored_items"]
    top_items = engine_result["top_items"]

    # 兜底：引擎返回空时尝试百搭单品
    if not top_items:
        top_items = _get_versatile_items(target_elements, top_k, user_gender=user_gender)
        if anchor_specs:
            top_items = [
                i for i in top_items
                if not any(item_conflicts_with_anchor(i, s) for s in anchor_specs)
            ]

    # 锚点置顶：库内匹配到的锚点物品置于结果首位并标记
    if anchor_specs and anchor_items:
        anchor_codes = {a.get("item_code") for a in anchor_items}
        top_items = anchor_items + [
            i for i in top_items if i.get("item_code") not in anchor_codes
        ][: max(0, top_k - len(anchor_items))]

    # 更新 item_sources（统一 key 规则，消除衣橱用 id / 公共库用 item_code 的键不一致）
    for item in top_items:
        item_sources[_canonical_item_key(item)] = item.get("source", "public")
    
    # ========== 旅行/出差场景：生成多天行程规划 ==========
    travel_plan = None
    travel_days = state.get("travel_days")
    destination = state.get("destination")
    luggage_size = state.get("luggage_size", "中")
    
    if travel_days and destination and travel_days >= 1:
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
        
        # 获取目的地天气：仅当用户提供明确出行日期时才做天气预判；
        # 仅有地点+天数（如"北京三天行程"）时缺乏时间维度，天气预报不准确，
        # 不强行生成（用户反馈 #4）
        travel_date_confirmed = state.get("travel_date_confirmed", False)
        weather_note = None
        if travel_date_confirmed:
            full_forecast = get_destination_weather(destination, 7)
            # 按 Query 中的具体月日（如 8.30）对齐预报起点，避免拿"今天"的预报冒充出行当天
            weather_forecast = _align_forecast_to_travel(
                full_forecast, state.get("user_input", ""), travel_days
            )
            if not weather_forecast:
                # 出行日期超出预报可覆盖范围（约7天），不给出不准确的预判
                travel_date_confirmed = False
                weather_note = "出行日期超出天气预报范围，暂未生成天气预判，建议出发前查看目的地天气"
        else:
            weather_forecast = []
            weather_note = "未提供具体出行日期，暂未生成天气预判，建议出发前查看目的地天气"
            logger.info(
                f"[旅行规划] 未提供明确出行日期，跳过 {destination} 天气预判"
            )
        
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
        
        # 未确认出行日期时：剔除规划器填充的默认天气，避免向用户展示伪造天气预报（用户反馈 #4）
        if not travel_date_confirmed:
            for day in optimized_days:
                scene_text = day.get("scene", "")
                if day.get("sub_scene"):
                    scene_text = f"{scene_text}（{day['sub_scene']}）"
                cats = [it.get("category", "") for it in day.get("items", [])]
                day["weather"] = None
                day["notes"] = (
                    f"第{day.get('day')}天，{scene_text}，暂无目的地天气预判，请出发前关注目的地天气。"
                    + (f"推荐{len(cats)}件：{'、'.join(cats)}。" if cats else "")
                )
        
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
            # 未提供明确出行日期/超出预报范围时不做天气预判，前端据此展示提示（用户反馈 #4）
            "weather_confirmed": travel_date_confirmed,
            "weather_note": weather_note,
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
    
    # 分类限制：核心服装最多2件，配饰/鞋履最多1件，饰品/文玩作为点缀
    max_per_category = {
        "上装": 2,
        "下装": 2,
        "裙装": 2,
        "外套": 2,
        "配饰": 1,
        "饰品": 2,  # 饰品/手串可作为点缀，最多2件
        "文玩": 1,  # 文玩佛珠类最多1件
        "鞋履": 1,
    }
    
    # 先遍历一次，记录配饰/饰品/文玩在排序中的位置（统称"点缀类"）
    accent_categories = {"配饰", "饰品", "文玩"}
    accessory_items = [item for item in valid_items if item.get("category") in accent_categories]
    
    # 点缀类多样性：从 top-3 点缀物品中随机选，避免同一件饰品反复出现
    if len(accessory_items) > 1:
        top_n = min(3, len(accessory_items))
        candidates = accessory_items[:top_n]
        random.shuffle(candidates)
        # 将随机化后的候选写回，确保 forced insertion 也用随机顺序
        accessory_items[:top_n] = candidates
        # 同时调整 valid_items 中点缀类的顺序，使正常遍历也受影响
        acc_idx = 0
        new_valid = []
        for item in valid_items:
            if item.get("category") in accent_categories:
                new_valid.append(accessory_items[acc_idx])
                acc_idx += 1
            else:
                new_valid.append(item)
        valid_items = new_valid
    
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
    
    # 确保至少有1件点缀类物品（如果存在且未入选）
    has_accessory = any(item.get("category") in accent_categories for item in result)
    if not has_accessory and accessory_items and len(result) >= limit:
        # 替换分数最低的非核心服装
        # P3-92 温度安全检查：不替换温度维度上必需的物品（极端温度下唯一保暖外套等）
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("category") in ["上装", "下装", "裙装", "外套", "鞋履"]:
                # 跳过温度维度上必需的物品（temp_score>=0.7 表示该物品在温度上很合适）
                if (result[i].get("temp_score") or 0) >= 0.7:
                    continue
                # 检查替换后该分类是否还有其他物品
                cat = result[i].get("category")
                same_cat_count = sum(1 for item in result if item.get("category") == cat)
                if same_cat_count > 1:  # 该分类还有其他物品，可以替换
                    result[i] = accessory_items[0]
                    break
    
    # 新增：确保饰品/文玩（手串、佛珠等传统文化饰品）至少出现1件
    # 这是产品核心差异化点，必须保证传统文化饰品在推荐中可见
    ornament_categories = {"饰品", "文玩"}
    has_ornament = any(item.get("category") in ornament_categories for item in result)
    ornament_items = [item for item in valid_items if item.get("category") in ornament_categories]
    
    if not has_ornament and ornament_items and len(result) >= limit:
        # 优先替换同属点缀类的物品（如已有一件"配饰"），避免挤占核心服装
        replaced = False
        for i in range(len(result) - 1, -1, -1):
            if result[i].get("category") in accent_categories and result[i].get("category") not in ornament_categories:
                result[i] = ornament_items[0]
                replaced = True
                break
        
        if not replaced:
            # 没有可替换的点缀类，替换分数最低且同分类有多件的服装
            for i in range(len(result) - 1, -1, -1):
                if result[i].get("category") in ["上装", "下装", "裙装", "外套"]:
                    if (result[i].get("temp_score") or 0) >= 0.7:
                        continue
                    cat = result[i].get("category")
                    same_cat_count = sum(1 for item in result if item.get("category") == cat)
                    if same_cat_count > 1:
                        result[i] = ornament_items[0]
                        break
    
    return result


def _get_versatile_items(target_elements: List[str], limit: int, user_gender: Optional[str] = None) -> List[Dict]:
    """
    获取百搭单品兜底
    
    当数据库无匹配结果时，返回中性百搭的单品
    """
    # 百搭单品特征：土属性（中性、包容）+ 基础色
    versatile_query = "百搭 中性 基础款 黑色 白色 灰色 米色 舒适"
    
    items = _vector_search(versatile_query, limit=limit, user_gender=user_gender)
    
    return items if items else []


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
    # 规则映射把"出差"归为"旅行"的子场景（main=旅行, sub=商务出差），
    # 直接取 main 会把出差行程泛化成"旅行"（用户反馈：出差两天第2天变旅行）；
    # Query 提取出的场景本身是具体旅行场景时优先采用
    if travel_main_scene == "旅行" and panel_scene in ("出差", "度假", "户外探险"):
        travel_main_scene = panel_scene
    
    scenes = []
    for day in range(travel_days):
        if day == 0 and panel_scene and panel_scene != travel_main_scene:
            # 第1天安排面板选择的场景（如商务）
            scenes.append(panel_scene)
        else:
            # 其余天使用旅行主场景
            scenes.append(travel_main_scene)
    
    return scenes


def _align_forecast_to_travel(forecast: List[Dict], user_input: str, travel_days: int) -> List[Dict]:
    """
    将天气预报对齐到实际出行日期（用户反馈：说"8.30，8.31"仍拿"今天"起的预报，日期错位）

    解析 Query 中的具体月日（如 8.30 / 8/30 / 8月30日），从预报中截取该日期起
    travel_days 天的片段：
    - 无法解析具体月日（"明天/下周"等相对表述）时维持现状，从今天起截取
    - 出行日期超出预报可覆盖范围（约7天）时返回空列表，由调用方提示出发前自查
    """
    if not forecast:
        return []

    from datetime import date, timedelta

    m = re.search(
        r"(?<![\d.])(\d{1,2})[./月](\d{1,2})[日号]?(?!\s*(?:度|℃|小时|分钟|点|折|倍|年|月))",
        user_input or "",
    )
    if not m:
        return forecast[:travel_days]
    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return forecast[:travel_days]

    today = date.today()
    try:
        start = date(today.year, month, day)
    except ValueError:
        return forecast[:travel_days]
    if start < today - timedelta(days=1):
        # 如 12 月说"1.2去出差"，按次年理解
        try:
            start = date(today.year + 1, month, day)
        except ValueError:
            return forecast[:travel_days]

    start_iso = start.isoformat()
    for i, f in enumerate(forecast):
        if f.get("date") == start_iso:
            return forecast[i:i + travel_days]

    logger.info(f"[旅行规划] 出行日期 {start_iso} 超出天气预报可覆盖范围，跳过天气预判")
    return []


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
    使用 DashScope API 生成文本向量（带 LRU 缓存 + 网络异常重试）
    
    相同文本不会重复调用 API，直接返回缓存结果。
    缓存满时自动淘汰最早插入的条目。
    
    海外链路（intl 端点）偶发连接被对端关闭（RemoteDisconnected），
    导致首次推荐失败、重试即恢复；这里对传输层异常做有限次重试。
    
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
    
    # 确保使用国内端点（ECS 同地域，避免跨境网络抖动）
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
    
    # 传输层可重试异常（连接被重置/断开/超时），API 业务错误不重试
    import http.client
    import requests.exceptions
    import urllib3.exceptions
    network_errors = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        urllib3.exceptions.ProtocolError,
        http.client.HTTPException,
        ConnectionError,
        TimeoutError,
    )
    
    max_attempts = 3
    response = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = TextEmbedding.call(
                model='text-embedding-v3',
                input=text
            )
            break
        except network_errors as e:
            if attempt >= max_attempts:
                logger.error(f"[Embedding] 网络异常重试 {max_attempts} 次后仍失败: {e}")
                raise
            wait = 1.0 * attempt
            logger.warning(f"[Embedding] 网络异常（第 {attempt}/{max_attempts} 次），{wait}s 后重试: {e}")
            time.sleep(wait)
    
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
                # 性别过滤逻辑（统一由 filters.build_gender_filter 生成，单一事实源）
                gender_filter = _build_gender_filter(user_gender)
                
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


def _search_accent_items(
    target_elements: List[str],
    user_gender: Optional[str] = None,
    limit: int = 5,
    exclude_ids: Optional[set] = None,
) -> List[Dict]:
    """
    配饰专项检索（辅路召回）

    按五行匹配从配饰/饰品/文玩品类中检索，不依赖向量语义距离。
    策略：五行命中优先 > 品类轮换（饰品>配饰>文玩）> 随机

    Args:
        target_elements: 目标五行列表
        user_gender: 用户性别
        limit: 返回数量
        exclude_ids: 需排除的物品ID集合（已在主路中出现的）

    Returns:
        配饰物品列表
    """
    items = []
    exclude_ids = exclude_ids or set()

    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                # 性别过滤（统一由 filters.build_gender_filter 生成，单一事实源）
                gender_filter = _build_gender_filter(user_gender)

                # 五行匹配排序：主五行命中 > 次五行命中 > 其他
                # 品类轮换：饰品优先（产品核心差异化）
                sql = f"""
                    SELECT 
                        item_code, name, category,
                        primary_element, secondary_element,
                        attributes_detail, gender,
                        applicable_weather, applicable_seasons,
                        temperature_range, functionality, thickness_level,
                        image_url,
                        CASE 
                            WHEN primary_element = ANY(%s) THEN 2
                            WHEN secondary_element = ANY(%s) THEN 1
                            ELSE 0
                        END AS element_match,
                        CASE category
                            WHEN '饰品' THEN 3
                            WHEN '配饰' THEN 2
                            WHEN '文玩' THEN 1
                            ELSE 0
                        END AS category_priority
                    FROM items
                    WHERE category IN ('配饰', '饰品', '文玩')
                    {gender_filter}
                    ORDER BY element_match DESC, category_priority DESC, RANDOM()
                    LIMIT %s
                """
                cur.execute(sql, (target_elements, target_elements, limit + len(exclude_ids)))
                rows = cur.fetchall()

                for row in rows:
                    item_code = row[0]
                    if item_code in exclude_ids:
                        continue
                    items.append({
                        "item_code": item_code,
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
                        "semantic_score": 0.55,  # 辅路给予中等基础分
                        "source": "public",
                    })
                    if len(items) >= limit:
                        break

    except Exception as e:
        logger.error(f"[配饰辅路] 检索失败: {e}")

    if items:
        logger.info(f"[配饰辅路] 召回{len(items)}件: {[i['name'] for i in items]}")
    return items


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

    # 显式意图指令：用户显式要求补某五行时，理由必须优先回应（最高优先级）
    explicit_intent_data = state.get("explicit_intent") or {}
    explicit_add = explicit_intent_data.get("add", [])
    explicit_ming = explicit_intent_data.get("ming", [])
    explicit_xiyong = explicit_intent_data.get("xiyong", [])
    if explicit_xiyong:
        added_instruction += (
            f' 特别说明：用户自述其喜用神为【{"、".join(explicit_xiyong)}】（以用户自述为准，优先于本账号八字推算），'
            f'这是最高优先级需求，推荐理由开头必须直接回应「喜用神是{explicit_xiyong[0]}」，'
            f'围绕【{"、".join(explicit_xiyong)}】元素的颜色/单品作主推荐，不得改用本账号八字喜用神作答，不得降级或忽略。'
        )
    elif explicit_ming:
        added_instruction += (
            f' 特别说明：用户询问的是【{"、".join(explicit_ming)}】命人的搭配，'
            f'这是最高优先级需求，必须从该命人适合的五行角度（比和元素与生它的元素）回答，'
            f'推荐理由开头必须直接回应「X命人」，不得改用本账号八字喜用神作答，不得降级或忽略。'
        )
    elif explicit_add:
        added_instruction += (
            f' 特别说明：用户明确要求补【{"、".join(explicit_add)}】元素，'
            f'这是最高优先级需求，推荐理由开头必须直接回应该需求，'
            f'并将其作为主推荐元素，不得降级为辅助加分或忽略。'
        )

    # 锚点物品指令：用户显式指定单品，叙事必须围绕它讲搭配（支持多锚点）
    anchor_specs_data = state.get("anchor_specs") or (
        [state["anchor_spec"]] if state.get("anchor_spec") else []
    )
    if anchor_specs_data:
        phrases = "、".join(s["phrase"] for s in anchor_specs_data)
        first_elem = anchor_specs_data[0].get("element")
        elem_hint = f"，其五行可参考【{first_elem}】" if first_elem else ""
        added_instruction += (
            f' 特别说明：用户已明确指定【{phrases}】为搭配锚点单品'
            f'（用户自己已拥有这些物品{elem_hint}）。'
            f'叙事必须围绕「{phrases}和什么搭配」展开：'
            f'先说明它们与哪些推荐单品组合，其余推荐单品均为衬托它们的搭配件，'
            f'不得推荐或提及与锚点单品同类冲突的其他单品。'
        )
    
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
    usage = None
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
        usage = extract_llm_usage(response)
        
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
        "llm_token_usage": merge_llm_usage(state.get("llm_token_usage"), usage),
    }


def generate_advice_stream(
    state: AgentState,
    usage_sink: Optional[Dict] = None,
) -> Generator[str, None, None]:
    """
    流式生成推荐理由（供 SSE 使用）
    
    Args:
        usage_sink: 可选，传入 dict 时将流式调用的 token 用量累加其中（成本核算）
    
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

    # 显式意图指令：用户显式要求补某五行时，理由必须优先回应（最高优先级）
    explicit_intent_data = state.get("explicit_intent") or {}
    explicit_add = explicit_intent_data.get("add", [])
    explicit_ming = explicit_intent_data.get("ming", [])
    explicit_xiyong = explicit_intent_data.get("xiyong", [])
    if explicit_xiyong:
        added_instruction += (
            f' 特别说明：用户自述其喜用神为【{"、".join(explicit_xiyong)}】（以用户自述为准，优先于本账号八字推算），'
            f'这是最高优先级需求，推荐理由开头必须直接回应「喜用神是{explicit_xiyong[0]}」，'
            f'围绕【{"、".join(explicit_xiyong)}】元素的颜色/单品作主推荐，不得改用本账号八字喜用神作答，不得降级或忽略。'
        )
    elif explicit_ming:
        added_instruction += (
            f' 特别说明：用户询问的是【{"、".join(explicit_ming)}】命人的搭配，'
            f'这是最高优先级需求，必须从该命人适合的五行角度（比和元素与生它的元素）回答，'
            f'推荐理由开头必须直接回应「X命人」，不得改用本账号八字喜用神作答，不得降级或忽略。'
        )
    elif explicit_add:
        added_instruction += (
            f' 特别说明：用户明确要求补【{"、".join(explicit_add)}】元素，'
            f'这是最高优先级需求，推荐理由开头必须直接回应该需求，'
            f'并将其作为主推荐元素，不得降级为辅助加分或忽略。'
        )

    # 锚点物品指令：用户显式指定单品，叙事必须围绕它讲搭配（支持多锚点）
    anchor_specs_data = state.get("anchor_specs") or (
        [state["anchor_spec"]] if state.get("anchor_spec") else []
    )
    if anchor_specs_data:
        phrases = "、".join(s["phrase"] for s in anchor_specs_data)
        first_elem = anchor_specs_data[0].get("element")
        elem_hint = f"，其五行可参考【{first_elem}】" if first_elem else ""
        added_instruction += (
            f' 特别说明：用户已明确指定【{phrases}】为搭配锚点单品'
            f'（用户自己已拥有这些物品{elem_hint}）。'
            f'叙事必须围绕「{phrases}和什么搭配」展开：'
            f'先说明它们与哪些推荐单品组合，其余推荐单品均为衬托它们的搭配件，'
            f'不得推荐或提及与锚点单品同类冲突的其他单品。'
        )
    
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
            max_tokens=220,  # 推荐理由压缩至100-130字（约150 token），220留足余量
            stream=True,
            include_usage=True,
        )
        
        for chunk in stream:
            # 成本核算：累加 usage（含 include_usage 末尾 chunk）
            if usage_sink is not None:
                merged = merge_llm_usage(usage_sink, extract_llm_usage(chunk))
                if merged:
                    usage_sink.clear()
                    usage_sink.update(merged)
            # include_usage 的末尾 chunk 仅有 usage 无 choices，需跳过
            if not chunk.choices:
                continue
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
            # 详情字段（用于物品详情弹窗）
            "attributes_detail": item.get("attributes_detail"),
            "thickness_level": item.get("thickness_level"),
            "applicable_weather": item.get("applicable_weather"),
            "applicable_seasons": item.get("applicable_seasons"),
            "temperature_range": item.get("temperature_range"),
            "functionality": item.get("functionality"),
            "gender": item.get("gender"),
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
