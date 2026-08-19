"""
批量衣物识别 LangGraph 状态机

流程：START → recognize_images → normalize → END
条件边：normalize 后若全部失败（error 置位）走 error 分支直达 END

两阶段交互需人工确认，故本图只编排第一阶段；第二阶段五行深度分析
为纯规则计算（wuxing_analysis_service），由路由直接调用。
"""

from typing import Literal
import logging

from langgraph.graph import StateGraph, END

from packages.ai_agents.wardrobe_tagging.state import BatchTaggingState
from packages.ai_agents.wardrobe_tagging.nodes import recognize_images_node, normalize_node

logger = logging.getLogger(__name__)


def check_all_failed(state: BatchTaggingState) -> Literal["continue", "error"]:
    """检查是否全部识别失败"""
    if state.get("error"):
        return "error"
    return "continue"


def build_batch_tagging_graph() -> StateGraph:
    """构建批量识别状态图"""
    graph = StateGraph(BatchTaggingState)

    graph.add_node("recognize_images", recognize_images_node)
    graph.add_node("normalize", normalize_node)

    graph.set_entry_point("recognize_images")
    graph.add_edge("recognize_images", "normalize")

    # 全部失败 → error 分支直达 END（error 已写入 state，由调用方读取）
    graph.add_conditional_edges(
        "normalize",
        check_all_failed,
        {
            "continue": END,
            "error": END,
        }
    )

    return graph


# 编译图
_graph = build_batch_tagging_graph()
batch_tagging_app = _graph.compile()


async def run_batch_tagging(image_urls: list) -> dict:
    """
    运行批量识别工作流（异步）

    Args:
        image_urls: 图片 URL 列表（与前端卡片同序，最多 5 张）

    Returns:
        dict: 最终状态，含 results（归一化结果，与输入同序）、
              error（全部失败时的错误信息）、llm_token_usage（用量汇总）
    """
    initial_state: BatchTaggingState = {"image_urls": list(image_urls)}
    return await batch_tagging_app.ainvoke(initial_state)
