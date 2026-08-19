"""
批量衣物识别工作流节点

- recognize_images_node: VL 模型并行识别（一图一调用，单件失败兜底默认值）
- normalize_node: 词表归一化（风格/品类/性别）+ 名称兜底 + token 用量汇总
"""

import logging

from packages.ai_agents.wardrobe_tagging.state import BatchTaggingState
from apps.api.services.ai_tagging_service import ai_tagging_service
from apps.api.services.llm_usage_service import merge_llm_usage

logger = logging.getLogger(__name__)

VALID_GENDERS = ("男", "女", "中性")


async def recognize_images_node(state: BatchTaggingState) -> dict:
    """节点1：VL 并行识别全部图片（并发上限由服务层 Semaphore 控制）"""
    image_urls = state.get("image_urls") or []
    if not image_urls:
        return {"error": "没有可识别的图片"}

    raw_results = await ai_tagging_service.batch_recognize(image_urls)
    logger.info(f"[批量识别] 完成 {len(raw_results)}/{len(image_urls)} 件")
    return {"raw_results": raw_results}


def normalize_node(state: BatchTaggingState) -> dict:
    """节点2：结果归一化，保证下游拿到的是词表内合法值

    - 风格：复用单件打标的 STYLE_VOCAB/STYLE_ALIASES 归一化，无法归一置 None 由用户选
    - 品类：越界值置 None
    - 性别：越界值置 None
    - 名称：空名称用"颜色+品类"兜底
    - 用量：汇总各件 _llm_usage 到 llm_token_usage
    """
    raw_results = state.get("raw_results") or []
    results = []
    usage_acc: dict = {}

    for r in raw_results:
        item = dict(r)

        item["style"] = ai_tagging_service._normalize_style(item.get("style"))

        if item.get("category") not in ai_tagging_service.BATCH_CATEGORY_VOCAB:
            item["category"] = None

        if item.get("gender") not in VALID_GENDERS:
            item["gender"] = None

        if not (item.get("suggested_name") or "").strip():
            item["suggested_name"] = ai_tagging_service._fallback_name(item)

        item_usage = item.pop("_llm_usage", None)
        if item_usage:
            merged = merge_llm_usage(usage_acc, item_usage)
            if merged:
                usage_acc = merged

        results.append(item)

    update: dict = {"results": results}
    if usage_acc:
        update["llm_token_usage"] = usage_acc

    # 全部失败才置 error（部分失败由单件 error 字段表达，前端引导手动填写）
    if results and all(r.get("error") for r in results):
        update["error"] = "全部衣物识别失败，请稍后重试或手动填写"

    return update
