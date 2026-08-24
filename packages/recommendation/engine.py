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
    compute_recommend_weights,
)
from packages.recommendation.scoring import (
    calculate_final_score,
    get_current_season,
    infer_item_thickness,
)
from packages.recommendation.filters import (
    apply_gender_hard_filter,
    apply_temperature_hard_filter,
    apply_temperature_safety_check,
    apply_scene_hard_filter,
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
    user_gender: Optional[str] = None,
    top_k: int = 5,
    batch_index: int = 0,
    retrieval_mode: str = "public",
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
        user_gender: 用户性别（男/女），用于评分后性别硬过滤安全网
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
        from packages.recommendation import config as rec_config
        # 有效温度 max(瞬时, 当日最高)，与硬过滤/评分口径一致
        effective_temp = rec_config.get_effective_temperature(weather_info)
        is_extreme_temp = rec_config.is_extreme_temp(effective_temp)

    weights = compute_recommend_weights(
        has_bazi=bool(bazi_result),
        has_scene=bool(scene),
        has_prefs=has_prefs,
        is_extreme_temp=is_extreme_temp,
        retrieval_mode=retrieval_mode,
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

    # ========== 4.5 场景硬过滤（安全网：拦截衣橱/配饰辅路漏过的场景错配物品） ==========
    scored_items = apply_scene_hard_filter(scored_items, scene, sub_scene, weather_info)

    # ========== 5. 温度硬过滤 ==========
    scored_items = apply_temperature_hard_filter(scored_items, weather_info)

    # ========== 5.5 性别硬过滤（安全网：拦截检索层漏过的性别错配物品） ==========
    scored_items = apply_gender_hard_filter(scored_items, user_gender)

    # ========== 6. 排序（确定性：分数 + 规范key，保证批次选择可复现） ==========
    scored_items.sort(key=lambda x: (x["final_score"], _canonical_item_key(x)), reverse=True)

    # ========== 7-10. 批次选择（换一批：批次间物品不重合） ==========
    top_items = _select_batch_items(
        scored_items=scored_items,
        top_k=top_k,
        batch_index=batch_index,
        weather_info=weather_info,
        user_style_preference=user_style_preference,
        user_body_type=user_body_type,
        target_elements=target_elements,
        scene=scene,
    )

    return {"scored_items": scored_items, "top_items": top_items}


def _select_batch_items(
    scored_items: List[Dict],
    top_k: int,
    batch_index: int,
    weather_info: Optional[Dict],
    user_style_preference: Optional[str],
    user_body_type: Optional[str],
    target_elements: List[str],
    scene: Optional[str],
) -> List[Dict]:
    """
    批次选择：确定性模拟前序批次并显式排除已展示物品，保证批次间不重合

    实现方式：
    - 整条选择链路确定性可复现（排序稳定 + 种子化随机源），
      因此 batch_index=N 时可精确重算第 0..N-1 批的展示集合并全部排除，
      下游多样性/温度安全/搭配完整性保障也只从排除后的池中补充，不会捞回前批物品
    - 新候选不足 top_k 时，已展示物品按分数序垫在池尾兜底（物理上无法完全不重合时优先保障可穿性）
    """
    # 种子仅由候选集合决定（与 batch_index 无关），保证同一候选集下各批次模拟一致
    seed_material = "|".join(_canonical_item_key(it) for it in scored_items)

    excluded_keys: set = set()
    top_items: List[Dict] = []

    for b in range(batch_index + 1):
        pool = [it for it in scored_items if _canonical_item_key(it) not in excluded_keys]
        if len(pool) < top_k and excluded_keys:
            # 新候选不足：已展示物品垫在池尾兜底（新鲜候选优先被选中）
            shown = [it for it in scored_items if _canonical_item_key(it) in excluded_keys]
            pool = pool + shown
            logger.info(
                f"[换一批] batch_index={b} 新候选不足（剩{len(pool) - len(shown)}件），复用已展示物品补足"
            )

        # 8. 多样性优化（种子化随机源：同一候选集下选择结果可复现）
        rng = random.Random(f"{seed_material}#batch{b}")
        batch_items = ensure_category_diversity(pool, top_k, rng=rng)
        batch_items = ensure_wuxing_diversity(batch_items, pool, top_k)

        # 9. 温度安全检查
        batch_items = apply_temperature_safety_check(batch_items, pool, weather_info, top_k)

        # 9.5 搭配完整性保障（在温度安全后执行，确保不被覆盖）
        batch_items = ensure_outfit_completeness(
            batch_items, pool, top_k,
            style_preference=user_style_preference,
            body_type=user_body_type,
            target_elements=target_elements,
            scene=scene,
        )

        # 10. 五行全不匹配降级
        if all(item.get("wuxing_score", 0) == 0 for item in batch_items):
            batch_items = _handle_wuxing_fallback(pool, top_k, rng=rng)

        excluded_keys.update(_canonical_item_key(it) for it in batch_items)
        top_items = batch_items
        if b > 0:
            logger.info(f"[换一批] batch_index={b}：本批{len(batch_items)}件，累计排除{len(excluded_keys)}件")

    return top_items


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


def _handle_wuxing_fallback(scored_items: List[Dict], top_k: int, rng: Optional[random.Random] = None) -> List[Dict]:
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

    result = ensure_category_diversity(scored_items, top_k, rng=rng)
    # 降级路径也保障搭配完整性（无风格/体型/五行信息，因为全不匹配）
    result = ensure_outfit_completeness(result, scored_items, top_k)
    return result
