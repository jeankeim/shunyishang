"""
LangGraph 状态机定义
构建推荐 Agent 的工作流图
"""

from typing import Literal
import logging

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

from packages.ai_agents.state import AgentState, create_initial_state
from packages.ai_agents.nodes import (
    analyze_intent_node,
    retrieve_items_node,
    generate_advice_node,
    format_output_node,
)
from apps.api.services.llm_usage_service import merge_llm_usage


def check_error(state: AgentState) -> Literal["continue", "error"]:
    """
    检查是否有错误
    
    Returns:
        "continue": 继续执行
        "error": 跳转到结束
    """
    if state.get("error"):
        return "error"
    return "continue"


def check_retrieved_items(state: AgentState) -> Literal["continue", "error"]:
    """
    检查是否有检索结果
    
    Returns:
        "continue": 继续执行
        "error": 跳转到结束
    """
    if not state.get("retrieved_items"):
        return "error"
    return "continue"


def build_graph() -> StateGraph:
    """
    构建 LangGraph 状态机
    
    流程：
    START → analyze_intent → retrieve_items → generate_advice → format_output → END
    
    条件边：
    - analyze_intent 后：如果 error → END
    - retrieve_items 后：如果无结果 → END
    """
    # 创建状态图
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("analyze_intent", analyze_intent_node)
    graph.add_node("retrieve_items", retrieve_items_node)
    graph.add_node("generate_advice", generate_advice_node)
    graph.add_node("format_output", format_output_node)
    
    # 设置入口
    graph.set_entry_point("analyze_intent")
    
    # 添加边
    # analyze_intent → retrieve_items（条件）
    graph.add_conditional_edges(
        "analyze_intent",
        check_error,
        {
            "continue": "retrieve_items",
            "error": END,
        }
    )
    
    # retrieve_items → generate_advice（条件）
    graph.add_conditional_edges(
        "retrieve_items",
        check_retrieved_items,
        {
            "continue": "generate_advice",
            "error": END,
        }
    )
    
    # generate_advice → format_output
    graph.add_edge("generate_advice", "format_output")
    
    # format_output → END
    graph.add_edge("format_output", END)
    
    return graph


# 编译图
_graph = build_graph()
app = _graph.compile()


# 上下文提取已迁移到 packages/recommendation/context_extraction.py
from packages.recommendation.context_extraction import (
    extract_context_from_query as _extract_context_from_query,
    extract_context_by_rules as _extract_context_by_rules,
)


def run_agent(
    user_input: str,
    scene: str = None,
    weather_element: str = None,
    weather_info: dict = None,
    bazi_input: dict = None,
    top_k: int = 5,
) -> dict:
    """
    运行 Agent（同步方式）
    
    Args:
        user_input: 用户输入
        scene: 场景（可选）
        weather_element: 天气五行（可选）
        weather_info: 天气详情（可选）
        bazi_input: 八字输入（可选）
        top_k: 返回数量
    
    Returns:
        dict: 最终响应
    """
    # 从八字输入中提取性别
    user_gender = bazi_input.get("gender") if bazi_input else None
    
    # 优化：从用户输入中提取场景/天气/旅行参数（与 run_agent_stream 保持一致）
    extracted = _extract_context_from_query(user_input)
    final_scene = extracted.get("scene") or scene
    final_weather_info = extracted.get("weather_info") or weather_info
    final_weather_element = extracted.get("weather_element") or weather_element
    final_travel_days = extracted.get("travel_days")
    final_destination = extracted.get("destination")
    
    # 判断是否为旅行/出差场景
    is_travel_scene = (
        final_scene in ("旅行", "出差", "度假", "户外探险")
        and final_travel_days is not None
        and final_travel_days >= 2
    )
    
    if is_travel_scene:
        logger.info(f"[推荐-sync] 旅行场景: 目的地={final_destination}, 天数={final_travel_days}")
    
    initial_state = create_initial_state(
        user_input=user_input,
        scene=final_scene,
        weather_element=final_weather_element,
        weather_info=final_weather_info,
        bazi_input=bazi_input,
        user_gender=user_gender,
        top_k=top_k,
        travel_days=final_travel_days if is_travel_scene else None,
        destination=final_destination if is_travel_scene else None,
        luggage_size="中" if is_travel_scene else None,
    )
    
    result = app.invoke(initial_state)
    return result.get("final_response", {})


def run_agent_stream(
    user_input: str,
    scene: str = None,
    weather_element: str = None,
    weather_info: dict = None,
    bazi_input: dict = None,
    user_gender: str = None,
    user_id: int = None,
    retrieval_mode: str = "public",
    top_k: int = 5,
    travel_days: int = None,
    destination: str = None,
    luggage_size: str = None,
    batch_index: int = 0,
):
    """
    运行 Agent（流式方式，供 SSE 使用）
    
    Args:
        user_input: 用户输入
        scene: 场景（可选）
        weather_element: 天气五行（可选）
        weather_info: 天气详情（可选）
        bazi_input: 八字输入（可选）
        user_id: 用户ID（衣橱模式必需）
        retrieval_mode: 检索模式（默认 public）
        top_k: 返回数量
        travel_days: 旅行天数（可选，优先于用户输入提取）
        destination: 目的地城市（可选，优先于用户输入提取）
        luggage_size: 行李箱大小（可选，小/中/大）
    
    Yields:
        dict: 状态更新
    """
    from packages.ai_agents.nodes import generate_advice_stream
    
    # 新增：从用户输入中提取场景和天气信息（优先级：用户提问 > 外部设置）
    extracted = _extract_context_from_query(user_input)

    # 成本核算：累加本次请求所有 LLM 调用的 token 用量
    usage_acc: dict = {}
    ctx_usage = extracted.get("llm_usage") if isinstance(extracted, dict) else None
    if ctx_usage:
        usage_acc.update(ctx_usage)
    
    # 使用用户提问中提取的信息，如果未提取到则使用外部传入的参数
    final_scene = extracted.get("scene") or scene
    final_weather_info = extracted.get("weather_info") or weather_info
    final_weather_element = extracted.get("weather_element") or weather_element
    
    # 旅行参数：外部传入优先，其次从用户输入提取
    final_travel_days = travel_days or extracted.get("travel_days")
    final_destination = destination or extracted.get("destination")
    final_luggage_size = luggage_size or "中"  # 默认中号行李箱
    
    # 判断是否为旅行/出差场景（有天数 + 目的地，或场景为旅行/出差）
    is_travel_scene = (
        final_scene in ("旅行", "出差", "度假", "户外探险")
        and final_travel_days is not None
        and final_travel_days >= 2
    )
    
    if extracted.get("scene"):
        logger.info(f"[推荐] 从用户提问中提取到场景: {extracted['scene']}")
    if extracted.get("weather_info"):
        logger.info(f"[推荐] 从用户提问中提取到天气: {extracted['weather_info']}")
    if is_travel_scene:
        logger.info(f"[推荐] 旅行场景: 目的地={final_destination}, 天数={final_travel_days}, 行李箱={final_luggage_size}")
    
    # 使用传入的 user_gender，如果没有则从八字输入中提取
    if user_gender is None and bazi_input:
        user_gender = bazi_input.get("gender")
    
    # 调试日志：打印 gender 信息
    logger.info(f"[推荐] user_gender={user_gender}, bazi_input.gender={bazi_input.get('gender') if bazi_input else None}")
    
    initial_state = create_initial_state(
        user_input=user_input,
        scene=final_scene,  # 使用提取后的场景
        weather_element=final_weather_element,  # 使用提取后的天气五行
        weather_info=final_weather_info,  # 使用提取后的天气信息
        bazi_input=bazi_input,
        user_gender=user_gender,
        user_id=user_id,
        retrieval_mode=retrieval_mode,
        top_k=top_k,
        travel_days=final_travel_days if is_travel_scene else None,
        destination=final_destination if is_travel_scene else None,
        luggage_size=final_luggage_size if is_travel_scene else None,
        batch_index=batch_index,
    )
    
    # 执行前三个节点（同步）
    state = analyze_intent_node(initial_state)
    initial_state.update(state)

    # 合并意图节点（查询增强 LLM）的 token 用量
    node_usage = initial_state.get("llm_token_usage")
    if node_usage:
        merged = merge_llm_usage(usage_acc, node_usage)
        if merged:
            usage_acc = merged
    
    if initial_state.get("error"):
        yield {"type": "error", "data": initial_state["error"]}
        return
    
    state = retrieve_items_node(initial_state)
    initial_state.update(state)
    
    # 检查是否有错误信息
    if initial_state.get("error"):
        yield {"type": "error", "data": initial_state["error"]}
        return
    
    if not initial_state.get("retrieved_items"):
        yield {"type": "error", "data": "没有找到合适的衣物"}
        return
    
    # 软降级通知：衣橱模式因向量 API 抖动重试后仍失败，已自动降级公共库，
    # 向前端发一条 notice 事件（不中断推荐结果），保障用户知情而非静默切换。
    if initial_state.get("retrieval_fallback") == "wardrobe_to_public":
        yield {
            "type": "notice",
            "data": "衣橱推荐暂时不可用，已临时为您使用公共库推荐。稍后可再试「我的衣橱」。",
        }
    
    # 输出分析结果
    bazi_result = initial_state.get("bazi_result")
    bazi_reasoning = bazi_result.get("reasoning") if bazi_result else None
    
    # 注入流年/大运信息
    if bazi_reasoning:
        annual_luck = initial_state.get("annual_luck")
        major_luck = initial_state.get("major_luck")
        if annual_luck:
            annual_info = annual_luck.get("annual_luck", {})
            annual_score = annual_luck.get("overall_score", 0)
            bazi_reasoning += f" 流年{annual_info.get('ganzhi', '')}({annual_info.get('element', '')})运势{annual_score}分。"
        if major_luck:
            bazi_reasoning += f" 当前大运{major_luck.get('ganzhi', '')}({major_luck.get('element', '')})，旺衰{major_luck.get('luck_level', '')}。"
    
    yield {
        "type": "analysis",
        "data": {
            "target_elements": initial_state["target_elements"],
            "bazi_reasoning": bazi_reasoning,
            "intent_reasoning": initial_state["intent_result"].get("reasoning") if initial_state.get("intent_result") else None,
            "scene": initial_state.get("scene"),
            # 八字五行分布（用于雷达图当前层）
            "element_scores": bazi_result.get("five_elements_count") if bazi_result else None,
            # 喜用神（用于雷达图建议层）
            "suggested_elements": bazi_result.get("suggested_elements") if bazi_result else initial_state["target_elements"],
            # 旅行场景标识
            "is_travel": is_travel_scene,
            "destination": final_destination if is_travel_scene else None,
            "travel_days": final_travel_days if is_travel_scene else None,
        }
    }
    
    # 输出多天行程规划（如果是旅行场景）
    travel_plan = initial_state.get("travel_plan")
    if travel_plan and is_travel_scene:
        yield {"type": "travel_plan", "data": travel_plan}
    
    # 输出物品列表（包含 source 字段）
    items = []
    logger.debug(f"[调试] retrieved_items 总数: {len(initial_state['retrieved_items'])}")
    logger.debug(f"[调试] retrieved_items 类型: {type(initial_state['retrieved_items'])}")
    
    for idx, item in enumerate(initial_state["retrieved_items"]):
        # 调试：检查 item 的类型
        if not isinstance(item, dict):
            logger.error(f"[错误] retrieved_items[{idx}] 不是字典，类型: {type(item)}, 值: {item}")
            continue
        
        # 额外调试：打印 item 的所有键
        if idx == 0:
            logger.debug(f"[调试] 第一个 item 的键: {list(item.keys())}")
        
        items.append({
            "item_code": item.get("item_code", ""),
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "primary_element": item.get("primary_element", ""),
            "secondary_element": item.get("secondary_element"),
            "final_score": round(item.get("final_score", 0), 3),
            "semantic_score": round(item.get("semantic_score", 0.5), 3),  # Task 05
            "wuxing_score": round(item.get("wuxing_score", 0), 3),  # Task 05
            "scene_score": round(item.get("scene_score", 0.5), 3),  # Task 05
            "source": item.get("source") or "public",
            "item_id": item.get("id"),
            "image_url": item.get("image_url"),
        })
    
    logger.debug(f"[调试] 成功构建 items 数量: {len(items)}")
    yield {"type": "items", "data": items}
    
    # 流式输出推荐理由
    reasoning_parts = []
    for token in generate_advice_stream(initial_state, usage_sink=usage_acc):
        reasoning_parts.append(token)
        yield {"type": "token", "data": token}

    # 成本核算内部事件：路由层拦截落库，不转发前端
    if usage_acc:
        yield {"type": "_llm_usage", "data": usage_acc}

    # 完成
    yield {"type": "done", "data": None}
