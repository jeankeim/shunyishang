"""
LangGraph 状态机定义
构建推荐 Agent 的工作流图
"""

from typing import Literal

from langgraph.graph import StateGraph, END

from packages.ai_agents.state import AgentState, create_initial_state
from packages.ai_agents.nodes import (
    analyze_intent_node,
    retrieve_items_node,
    generate_advice_node,
    format_output_node,
)


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
    
    initial_state = create_initial_state(
        user_input=user_input,
        scene=scene,
        weather_element=weather_element,
        weather_info=weather_info,
        bazi_input=bazi_input,
        user_gender=user_gender,
        top_k=top_k,
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
    
    Yields:
        dict: 状态更新
    """
    from packages.ai_agents.nodes import generate_advice_stream
    
    # 使用传入的 user_gender，如果没有则从八字输入中提取
    if user_gender is None and bazi_input:
        user_gender = bazi_input.get("gender")
    
    initial_state = create_initial_state(
        user_input=user_input,
        scene=scene,
        weather_element=weather_element,
        weather_info=weather_info,
        bazi_input=bazi_input,
        user_gender=user_gender,
        user_id=user_id,
        retrieval_mode=retrieval_mode,
        top_k=top_k,
    )
    
    # 执行前三个节点（同步）
    state = analyze_intent_node(initial_state)
    initial_state.update(state)
    
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
    
    # 输出分析结果
    bazi_result = initial_state.get("bazi_result")
    yield {
        "type": "analysis",
        "data": {
            "target_elements": initial_state["target_elements"],
            "bazi_reasoning": bazi_result.get("reasoning") if bazi_result else None,
            "intent_reasoning": initial_state["intent_result"].get("reasoning") if initial_state.get("intent_result") else None,
            "scene": initial_state.get("scene"),
            # 八字五行分布（用于雷达图当前层）
            "element_scores": bazi_result.get("five_elements_count") if bazi_result else None,
            # 喜用神（用于雷达图建议层）
            "suggested_elements": bazi_result.get("suggested_elements") if bazi_result else initial_state["target_elements"],
        }
    }
    
    # 输出物品列表
    items = []
    for item in initial_state["retrieved_items"]:
        items.append({
            "item_code": item.get("item_code", ""),
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "primary_element": item.get("primary_element", ""),
            "secondary_element": item.get("secondary_element"),
            "final_score": round(item.get("final_score", 0), 3),
        })
    yield {"type": "items", "data": items}
    
    # 流式输出推荐理由
    reasoning_parts = []
    for token in generate_advice_stream(initial_state):
        reasoning_parts.append(token)
        yield {"type": "token", "data": token}
    
    # 完成
    yield {"type": "done", "data": None}
