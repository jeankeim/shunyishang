"""
推荐过滤逻辑

包含：温度硬过滤、场景SQL过滤、天气SQL过滤、性别过滤。
所有过滤函数均为纯函数或返回 SQL 片段。
"""

import logging
from typing import Dict, List, Optional

from packages.recommendation.config import (
    EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
    EXTREME_COLD_TEMP, MILD_COLD_TEMP,
    TEMP_SAFETY_THRESHOLD,
)
from packages.recommendation.scoring import infer_item_thickness

logger = logging.getLogger(__name__)


# ============================================================
# 温度硬过滤
# ============================================================

def apply_temperature_hard_filter(
    scored_items: List[Dict],
    weather_info: Optional[Dict],
) -> List[Dict]:
    """
    极端温度下排除不合适厚度的衣物

    分层级过滤，阈值统一自 config 常量。
    当所有候选都被排除时，回退保留温度适配分最高的一批（避免返回空）。

    Args:
        scored_items: 已评分的物品列表（含 temp_score）
        weather_info: 天气信息

    Returns:
        过滤后的物品列表
    """
    if not weather_info:
        return scored_items

    temp = weather_info.get("temperature")
    if temp is None:
        return scored_items

    temp_filtered = []
    for item in scored_items:
        thickness = infer_item_thickness(item)

        # temperature_range 硬排除
        temp_range = item.get("temperature_range")
        if temp_range and isinstance(temp_range, dict):
            # 最低温排除：当前温度低于物品适用最低温度超过10°C则排除
            range_min = temp_range.get("最低") or temp_range.get("min")
            if range_min is not None:
                try:
                    range_min_int = int(range_min)
                    if temp < range_min_int - 10:
                        continue
                except (ValueError, TypeError):
                    pass
            # 最高温排除：当前温度高于物品适用最高温度超过8°C则排除
            range_max = temp_range.get("最高") or temp_range.get("max")
            if range_max is not None:
                try:
                    range_max_int = int(range_max)
                    if temp > range_max_int + 8:
                        continue
                except (ValueError, TypeError):
                    pass

        # 温度硬过滤（分层级）
        if temp >= EXTREME_HOT_TEMP:
            if thickness in ("厚重", "中厚"):
                continue
        elif temp >= HOT_TEMP:
            if thickness in ("厚重", "中厚"):
                continue
        elif temp >= 20:
            if thickness == "厚重":
                continue
        elif temp <= EXTREME_COLD_TEMP:
            if thickness in ("极薄", "轻薄"):
                continue
        elif temp <= MILD_COLD_TEMP:
            if thickness == "极薄":
                continue

        temp_filtered.append(item)

    if temp_filtered:
        return temp_filtered

    # 所有候选都被排除：保留温度适配分最高的一批（最不坏候选）
    if scored_items:
        max_ts = max(it.get("temp_score", 0.5) for it in scored_items)
        least_bad = [it for it in scored_items if it.get("temp_score", 0.5) >= max_ts - 1e-9]
        logger.warning(
            f"[温度过滤] 温度={temp}°C 下所有候选均不合适，"
            f"回退保留温度适配分最高的 {len(least_bad)} 件"
        )
        return least_bad

    return scored_items


def apply_temperature_safety_check(
    top_items: List[Dict],
    scored_items: List[Dict],
    weather_info: Optional[Dict],
    top_k: int,
) -> List[Dict]:
    """
    温度安全检查：极端温度下替换 temp_score 过低的物品

    在多样性替换之后执行，确保最终结果中没有极端不合适的物品。
    """
    if not weather_info:
        return top_items

    temp = weather_info.get("temperature")
    if temp is None:
        return top_items

    is_extreme = temp <= EXTREME_COLD_TEMP or temp >= EXTREME_HOT_TEMP
    if not is_extreme:
        return top_items

    temp_safe_items = [i for i in top_items if (i.get("temp_score") or 1.0) >= TEMP_SAFETY_THRESHOLD]
    if len(temp_safe_items) < len(top_items) and scored_items:
        used_ids = {i.get("id") for i in temp_safe_items}
        # 统计当前品类分布，替换时遵守品类限制
        from packages.recommendation.config import CATEGORY_LIMITS, DEFAULT_CATEGORY_LIMIT
        cat_count = {}
        for i in temp_safe_items:
            cat = i.get("category", "其他")
            cat_count[cat] = cat_count.get(cat, 0) + 1
        for candidate in scored_items:
            if candidate.get("id") in used_ids:
                continue
            if (candidate.get("temp_score") or 0) < TEMP_SAFETY_THRESHOLD:
                continue
            # 遵守品类限制：不超过该品类允许的最大数量
            cat = candidate.get("category", "其他")
            max_allowed = CATEGORY_LIMITS.get(cat, DEFAULT_CATEGORY_LIMIT)
            if cat_count.get(cat, 0) >= max_allowed:
                continue
            temp_safe_items.append(candidate)
            used_ids.add(candidate.get("id"))
            cat_count[cat] = cat_count.get(cat, 0) + 1
            if len(temp_safe_items) >= top_k:
                break
        # 如果遵守品类限制后仍不足，放宽限制补充
        if len(temp_safe_items) < top_k:
            for candidate in scored_items:
                if candidate.get("id") in used_ids:
                    continue
                if (candidate.get("temp_score") or 0) < TEMP_SAFETY_THRESHOLD:
                    continue
                temp_safe_items.append(candidate)
                used_ids.add(candidate.get("id"))
                if len(temp_safe_items) >= top_k:
                    break
        return temp_safe_items[:top_k]

    return top_items


# ============================================================
# SQL 过滤条件构建
# ============================================================

def build_gender_filter(user_gender: Optional[str]) -> str:
    """构建性别过滤SQL条件"""
    if user_gender == "男":
        return "AND (gender = '中性' OR gender = '男')"
    elif user_gender == "女":
        return "AND (gender = '中性' OR gender = '女')"
    else:
        return "AND (gender = '中性' OR gender = '男' OR gender IS NULL)"


def build_weather_filter(weather_info: Optional[Dict]) -> str:
    """
    构建天气过滤SQL条件

    根据温度生成厚度过滤条件（6档与评分对齐）。
    天气状况过滤已移至评分逻辑（软过滤），不再硬性排除。
    """
    if not weather_info:
        return ""

    conditions = []
    temperature = weather_info.get("temperature")

    if temperature is not None:
        if temperature <= EXTREME_COLD_TEMP:
            conditions.append(
                f"(thickness_level IN ('厚重', '中厚') OR "
                f"temperature_range->>'最低' IS NOT NULL AND "
                f"(temperature_range->>'最低')::int <= {EXTREME_COLD_TEMP})"
            )
        elif temperature <= MILD_COLD_TEMP:
            conditions.append(
                f"(thickness_level IN ('厚重', '中厚', '适中') OR "
                f"temperature_range->>'最低' IS NOT NULL AND "
                f"(temperature_range->>'最低')::int <= {MILD_COLD_TEMP})"
            )
        elif temperature < MILD_HOT_TEMP:
            conditions.append(
                f"(thickness_level IN ('适中', '轻薄', '极薄', '中厚') OR "
                f"temperature_range->>'最低' IS NOT NULL AND "
                f"(temperature_range->>'最低')::int <= {MILD_HOT_TEMP})"
            )
        elif temperature < HOT_TEMP:
            conditions.append(
                f"(thickness_level IN ('轻薄', '极薄', '适中') OR "
                f"temperature_range->>'最高' IS NOT NULL AND "
                f"(temperature_range->>'最高')::int >= {MILD_HOT_TEMP})"
            )
        elif temperature < EXTREME_HOT_TEMP:
            conditions.append(
                f"(thickness_level IN ('轻薄', '极薄', '适中') OR "
                f"temperature_range->>'最高' IS NOT NULL AND "
                f"(temperature_range->>'最高')::int >= {HOT_TEMP})"
            )
        else:
            conditions.append(
                f"(thickness_level IN ('轻薄', '极薄') OR "
                f"temperature_range->>'最高' IS NOT NULL AND "
                f"(temperature_range->>'最高')::int >= {EXTREME_HOT_TEMP})"
            )

    return " AND ".join(conditions) if conditions else ""


def build_scene_filter(scene: Optional[str], sub_scene: Optional[str] = None) -> str:
    """
    构建场景过滤SQL条件

    统一从 scene_mapping.py 读取规则，消除硬编码不同步问题。
    注意：所有拼入 SQL 的字符串均经过单引号转义，防止配置值意外破坏 SQL 结构。
    """
    if not scene:
        return ""

    from packages.utils.scene_mapping import get_scene_rules, get_sub_scene_rules

    rules = get_scene_rules(scene)
    if not rules:
        return ""

    conditions = []

    def _escape(val: str) -> str:
        """转义 SQL 字符串中的单引号"""
        return val.replace("'", "''")

    # 排除特定类别
    excluded_cats = rules.get("excluded_categories", [])
    if excluded_cats:
        categories_str = ",".join([f"'{_escape(cat)}'" for cat in excluded_cats])
        conditions.append(f"category NOT IN ({categories_str})")

    # 排除包含特定关键词的衣物
    excluded_kws = rules.get("excluded_keywords", [])
    if excluded_kws:
        keyword_conditions = []
        for keyword in excluded_kws:
            keyword_conditions.append(f"name NOT LIKE '%%{_escape(keyword)}%%'")
        conditions.append(" AND ".join(keyword_conditions))

    # 子场景特殊排除
    if sub_scene:
        sub_rules = get_sub_scene_rules(sub_scene)
        if sub_rules and "extra_excluded_keywords" in sub_rules:
            for keyword in sub_rules["extra_excluded_keywords"]:
                conditions.append(f"name NOT LIKE '%%{_escape(keyword)}%%'")

    # 排除特定厚度（仅极端场景）
    preferred_thickness = rules.get("preferred_thickness", [])
    if preferred_thickness and scene in ("运动", "度假"):
        all_thickness = ["极薄", "轻薄", "适中", "中厚", "厚重"]
        exclude_thickness = [t for t in all_thickness if t not in preferred_thickness]
        if exclude_thickness:
            thickness_str = ",".join([f"'{_escape(t)}'" for t in exclude_thickness])
            conditions.append(f"thickness_level NOT IN ({thickness_str})")

    # 运动场景功能硬过滤
    if scene == "运动":
        preferred_funcs = rules.get("preferred_functionality", [])
        sport_funcs = [f for f in preferred_funcs if f in ("透气", "速干", "运动", "弹性")]
        if sport_funcs:
            func_conditions = []
            for func in sport_funcs:
                func_conditions.append(f"(functionality->>'{_escape(func)}')::boolean = true")
            if func_conditions:
                conditions.append(f"({' OR '.join(func_conditions)})")

    return " AND ".join(conditions) if conditions else ""


# ============================================================
# 场景分硬排除
# ============================================================

def filter_by_scene_score(scored_items: List[Dict]) -> List[Dict]:
    """过滤掉场景分为0的物品（硬排除）"""
    return [item for item in scored_items if item.get("scene_score", 0.5) > 0]
