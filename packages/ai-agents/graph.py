"""
LangGraph 推荐工作流状态机定义
"""
from typing import TypedDict, Dict, List, Optional
from langgraph.graph import StateGraph, END


class AgentState(TypedDict):
    """Agent 状态定义"""
    # 输入
    user_id: str
    input_type: str  # bazi | mood | scene
    input_data: Dict
    
    # 分析阶段
    wuxing_analysis: Optional[Dict]
    search_query: Optional[str]
    
    # 检索阶段
    candidate_items: Optional[List[Dict]]
    selected_items: Optional[List[Dict]]
    
    # 生成阶段
    recommendation_reason: Optional[str]
    styling_tips: Optional[str]
    
    # 输出
    radar_data: Optional[Dict]
    final_output: Optional[Dict]
    
    # 控制
    messages: List[str]
    errors: List[str]


def create_recommend_graph():
    """
    创建推荐工作流图
    
    Returns:
        编译后的 LangGraph
    """
    # TODO: 实现完整的工作流
    # 当前返回占位实现
    workflow = StateGraph(AgentState)
    
    # 添加节点（待实现）
    # workflow.add_node("analyze", analyze_node)
    # workflow.add_node("search", search_node)
    # workflow.add_node("rank", rank_node)
    # workflow.add_node("generate", generate_node)
    
    # 设置入口
    # workflow.set_entry_point("analyze")
    
    return workflow.compile()
