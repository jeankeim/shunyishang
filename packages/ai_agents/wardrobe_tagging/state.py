"""
批量衣物识别工作流状态定义
"""

from typing import Dict, List, Optional

from typing_extensions import TypedDict


class BatchTaggingState(TypedDict, total=False):
    """批量识别节点间传递的状态契约"""

    # 输入：与前端卡片同序的图片 URL 列表（最多 5 张）
    image_urls: List[str]

    # recognize_images 节点产出：VL 原始识别结果（与 image_urls 同序）
    raw_results: List[Dict]

    # normalize 节点产出：归一化后的最终结果
    results: List[Dict]

    # 全部失败时的错误信息（部分失败不置 error，单件自带 error 字段）
    error: Optional[str]

    # 本批 LLM token 用量汇总（供埋点折算成本）
    llm_token_usage: Dict
