"""
批量衣物识别 LangGraph 工作流

编排第一阶段批量识别流程：
START → recognize_images（VL 并行识别）→ normalize（词表归一化）→ END

第二阶段（五行深度分析）为纯规则计算且需要人工确认分隔，不入此图。
"""

from packages.ai_agents.wardrobe_tagging.graph import batch_tagging_app, run_batch_tagging

__all__ = ["batch_tagging_app", "run_batch_tagging"]
