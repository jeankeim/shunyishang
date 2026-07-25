"""
推荐引擎主入口

编排完整的推荐流程：
1. 评分（scoring）→ 2. 过滤（filters）→ 3. 多样性（diversity）→ 4. 输出

本模块是 nodes.py 中 retrieve_items_node 评分/过滤/多样性部分的重构提取，
nodes.py 保留为 LangGraph 节点的薄包装层。
"""

import random
import logging
from typing import Dict, List, Optional

from packages.recommendation.config import (
    MAX_TARGET_ELEMENTS,
    BATCH_JITTER_RANGE,
    compute_recommend_weights,
)
from packages.recommendation.scoring import (
    calculate_final_score,
    get_current_season,
    infer_item_thickness,
)
from packages.recommendation.filters import (
    apply_temperature_hard_filter,
    apply_temperature_safety_check,
    filter_by_scene_score,
)
from packages.recommendation.diversity import (
    ensure_category_diversity,
    ensure_wuxing_diversity,
    ensure_outfit_completeness,
)
from packages.recommendation.behavior import (
    get_user_behavior_preferences,
    calculate_behavior_score,
)

logger = logging.getLogger(__name__)


def _canonical_item_key(item: Dict) -> str:
    """
    生成物品统一 key（优先 item_code，缺失时回退 str(id)）
    """
    return item.get("item_code") or str(item.get("id"))


def score_and_rank_items(
    items: List[Dict],
    target_elements: List[str],
    boost_elements: Optional[List[str]] = None,
    bazi_result: Optional[Dict] = None,
    scene: Optional[str] = None,
    sub_scene: Optional[str] = None,
    weather_info: Optional[Dict] = None,
    user_id: Optional[int] = None,
    user_prefs: Optional[Dict] = None,
    user_skin_tone: Optional[str] = None,
    user_style_preference: Optional[str] = None,
    user_body_type: Optional[str] = None,
    top_k: int = 5,
    batch_index: int = 0,
) -> Dict:
    """
    推荐引擎核心：评分 → 过滤 → 排序 → 多样性 → 温度安全

    这是从 nodes.py retrieve_items_node 中提取的纯评分/排序逻辑，
    不包含数据检索（向量搜索）部分。

    Args:
        items: 已检索的候选物品列表
        target_elements: 目标五行
        boost_elements: 相生辅助五行
        bazi_result: 八字结果
        scene: 场景
        sub_scene: 子场景
        weather_info: 天气信息
        user_id: 用户ID
        user_prefs: 用户显性偏好
        user_skin_tone: 肤色
        user_style_preference: 风格偏好
        user_body_type: 体型
        top_k: 返回数量
        batch_index: 批次索引（换一批）

    Returns:
        {
            "scored_items": 全量评分列表,
            "top_items": 最终 top-k 列表,
        }
    """
    if not items:
        return {"scored_items": [], "top_items": []}

    # ========== 1. 计算权重 ==========
    # 偏好有效性校验（P2-74）
    has_prefs = bool(user_prefs)
    if has_prefs and items:
        pref_hit = _check_pref_relevance(user_prefs, items)
        if not pref_hit:
            logger.info("[引擎] 用户偏好与当前候选物品无交集，回退到无偏好权重方案")
            has_prefs = False

    is_extreme_temp = False
    if weather_info:
        temp_val = weather_info.get("temperature")
        if temp_val is not None:
            from packages.recommendation.config import EXTREME_COLD_TEMP, EXTREME_HOT_TEMP
            is_extreme_temp = temp_val <= EXTREME_COLD_TEMP or temp_val >= EXTREME_HOT_TEMP

    weights = compute_recommend_weights(
        has_bazi=bool(bazi_result),
        has_scene=bool(scene),
        has_prefs=has_prefs,
        is_extreme_temp=is_extreme_temp,
    )
    scene_weight = weights["scene"]
    pref_weight = weights["pref"]

    # ========== 2. 获取行为偏好（隐性反馈） ==========
    behavior_prefs = {}
    if user_id:
        behavior_prefs = get_user_behavior_preferences(user_id)

    # ========== 3. 逐物品评分 ==========
    current_season = get_current_season()
    scored_items = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            logger.error(f"[引擎] items[{idx}] 不是字典类型，跳过")
            continue

        # 行为加分
        behavior_score = calculate_behavior_score(item, behavior_prefs) if behavior_prefs else 0.0

        # 综合评分
        scores = calculate_final_score(
            item=item,
            weights=weights,
            target_elements=target_elements,
            boost_elements=boost_elements,
            weather_info=weather_info,
            current_season=current_season,
            scene=scene,
            sub_scene=sub_scene,
            scene_weight=scene_weight,
            user_prefs=user_prefs,
            pref_weight=pref_weight,
            skin_tone=user_skin_tone,
            style_preference=user_style_preference,
            body_type=user_body_type,
            behavior_score=behavior_score,
        )

        scored_items.append({**item, **scores})

    # ========== 4. 场景分硬排除 ==========
    scored_items = filter_by_scene_score(scored_items)

    # ========== 5. 温度硬过滤 ==========
    scored_items = apply_temperature_hard_filter(scored_items, weather_info)

    # ========== 6. 排序 ==========
    if batch_index > 0:
        for item in scored_items:
            item["_jittered_score"] = item["final_score"] + random.uniform(-BATCH_JITTER_RANGE, BATCH_JITTER_RANGE)
        scored_items.sort(key=lambda x: (x["_jittered_score"], _canonical_item_key(x)), reverse=True)
        for item in scored_items:
            del item["_jittered_score"]
    else:
        scored_items.sort(key=lambda x: (x["final_score"], _canonical_item_key(x)), reverse=True)

    # ========== 7. 批次偏移 ==========
    start_idx = batch_index * top_k
    if start_idx < len(scored_items):
        diversity_pool = scored_items[start_idx:]
        if batch_index > 0:
            logger.info(f"[换一批] batch_index={batch_index}，跳过前{start_idx}件")
    else:
        diversity_pool = scored_items
        logger.info(f"[换一批] 候选不足（{len(scored_items)}件），回退到第1批")

    # ========== 8. 多样性优化 ==========
    # 传入批次起点之后的完整候选池：品类/点缀去重后仍能用普通服装回填到 top_k，避免因去重导致数量不足
    top_items = ensure_category_diversity(diversity_pool, top_k)
    top_items = ensure_wuxing_diversity(top_items, scored_items, top_k)

    # ========== 9. 温度安全检查 ==========
    top_items = apply_temperature_safety_check(top_items, scored_items, weather_info, top_k)

    # ========== 9.5 搭配完整性保障（在温度安全后执行，确保不被覆盖） ==========
    top_items = ensure_outfit_completeness(
        top_items, scored_items, top_k,
        style_preference=user_style_preference,
        body_type=user_body_type,
        target_elements=target_elements,
        scene=scene,
    )

    # ========== 10. 五行全不匹配降级 ==========
    if all(item.get("wuxing_score", 0) == 0 for item in top_items):
        top_items = _handle_wuxing_fallback(scored_items, top_k)

    return {"scored_items": scored_items, "top_items": top_items}


def _check_pref_relevance(user_prefs: Dict, items: List[Dict]) -> bool:
    """检查用户偏好是否与当前候选物品有交集"""
    pref_dimension_map = {
        "color": "color",
        "primary_element": "element",
        "category": "category",
        "style": "style",
        "material": "material",
        "thickness_level": "thickness",
    }
    for it in items:
        for attr, dim in pref_dimension_map.items():
            if dim in user_prefs and it.get(attr) and it.get(attr) in user_prefs[dim]:
                return True
    return False


def _handle_wuxing_fallback(scored_items: List[Dict], top_k: int) -> List[Dict]:
    """五行全不匹配时的降级策略"""
    semantic_values = {item.get("semantic_score", 0.5) for item in scored_items}
    if len(semantic_values) <= 1:
        # semantic 无区分度，改用 temp+scene 组合
        scored_items.sort(
            key=lambda x: (
                (x.get("temp_score") or 0.5) + (x.get("scene_score") or 0.5),
                _canonical_item_key(x),
            ),
            reverse=True,
        )
        logger.info("[引擎] 五行全0且semantic无区分度，降级为 temp+scene 排序")
    else:
        scored_items.sort(key=lambda x: (x["semantic_score"], _canonical_item_key(x)), reverse=True)

    result = ensure_category_diversity(scored_items, top_k)
    # 降级路径也保障搭配完整性（无风格/体型/五行信息，因为全不匹配）
    result = ensure_outfit_completeness(result, scored_items, top_k)
    return result
