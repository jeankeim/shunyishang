"""
月度运势穿搭建议服务
按月计算五行旺衰变化，提供穿搭策略

功能：
- calculate_monthly_fortune: 计算月度运势
- generate_monthly_outfit_strategy: 生成月度穿搭策略
- calculate_yearly_fortune: 计算年度运势汇总
"""

import logging
import random
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import cnlunar

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    MONTH_SEASON_WUXING,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
    WUXING_BEI_KE,
    ELEMENT_COLOR_MAP,
    ELEMENT_MATERIAL_MAP,
    ELEMENT_STYLE_MAP,
    WUXING_LIST,
)
from apps.api.services.fortune_engine import (
    ELEMENT_DIRECTION_MAP,
    DIMENSION_ELEMENT_AFFINITY,
    _get_element_relation,
    _calculate_relation_score,
)

logger = logging.getLogger(__name__)


def _get_month_ganzhi(year: int, month: int) -> tuple:
    """
    获取指定年月的天干地支

    使用 cnlunar 获取月柱干支

    Returns:
        (天干, 地支)
    """
    # 使用每月15日作为代表日
    dt = datetime(year, month, 15, 12)
    lunar = cnlunar.Lunar(dt, godType='8char')
    month_gz = lunar.month8Char
    return month_gz[0], month_gz[1]


def calculate_monthly_fortune(
    user_bazi: Dict[str, Any],
    year: int,
    month: int,
) -> Dict[str, Any]:
    """
    计算月度运势

    获取当月天干地支，分析当月五行与用户八字的生克关系

    Args:
        user_bazi: 用户八字信息（含day_master, suggested_elements等）
        year: 年份
        month: 月份 (1-12)

    Returns:
        {month, scores, element_analysis, outfit_strategy}
    """
    day_master = user_bazi.get("day_master", "土")
    suggested_elements = user_bazi.get("suggested_elements", [])
    avoid_elements = user_bazi.get("avoid_elements", [])

    # 获取当月天干地支
    month_tiangan, month_dizhi = _get_month_ganzhi(year, month)
    month_tg_element = TIANGAN_WUXING.get(month_tiangan, "土")
    month_dz_element = DIZHI_WUXING.get(month_dizhi, "土")

    # 当月季节五行（月令旺气）
    season_element = MONTH_SEASON_WUXING.get(month, "土")

    # 天干与日主关系
    tg_relation = _get_element_relation(month_tg_element, day_master)
    dz_relation = _get_element_relation(month_dz_element, day_master)

    # 五维度评分
    base_score = 65
    seed_val = hash(f"{user_bazi.get('pillars', {}).get('day', 'default')}_{year}_{month}")
    rng = random.Random(seed_val)

    scores: Dict[str, int] = {}
    for dimension, affinity_map in DIMENSION_ELEMENT_AFFINITY.items():
        tg_affinity = affinity_map.get(month_tg_element, 1.0)
        dz_affinity = affinity_map.get(month_dz_element, 1.0)

        tg_rel_score = _calculate_relation_score(tg_relation)
        dz_rel_score = _calculate_relation_score(dz_relation)

        raw = base_score * (tg_affinity * tg_rel_score * 0.5 +
                            dz_affinity * dz_rel_score * 0.3 +
                            affinity_map.get(season_element, 1.0) * 0.2)

        # 喜用神加成
        if month_tg_element in suggested_elements:
            raw += 6
        if month_dz_element in suggested_elements:
            raw += 4
        if season_element in suggested_elements:
            raw += 3

        # 忌神减分
        if month_tg_element in avoid_elements:
            raw -= 6
        if month_dz_element in avoid_elements:
            raw -= 4

        # 随机波动
        raw += rng.randint(-4, 4)

        scores[dimension] = max(0, min(100, int(raw)))

    # 五行分析
    element_analysis = _analyze_month_elements(
        month_tg_element, month_dz_element, season_element, day_master,
        suggested_elements, avoid_elements
    )

    # 生成穿搭策略
    outfit_strategy = generate_monthly_outfit_strategy({
        "scores": scores,
        "month_tiangan": month_tiangan,
        "month_dizhi": month_dizhi,
        "month_tg_element": month_tg_element,
        "month_dz_element": month_dz_element,
        "season_element": season_element,
        "day_master": day_master,
        "suggested_elements": suggested_elements,
        "avoid_elements": avoid_elements,
    })

    overall = int(sum(scores.values()) / len(scores))

    return {
        "year": year,
        "month": month,
        "month_ganzhi": f"{month_tiangan}{month_dizhi}",
        "scores": scores,
        "overall_score": overall,
        "element_analysis": element_analysis,
        "outfit_strategy": outfit_strategy,
    }


def _analyze_month_elements(
    tg_element: str,
    dz_element: str,
    season_element: str,
    day_master: str,
    suggested_elements: List[str],
    avoid_elements: List[str],
) -> Dict[str, Any]:
    """分析当月五行旺衰"""
    # 当月五行旺衰
    strong_elements: List[str] = []
    weak_elements: List[str] = []

    # 季节当旺五行
    strong_elements.append(season_element)

    # 天干地支五行
    if tg_element not in strong_elements:
        strong_elements.append(tg_element)
    if dz_element not in strong_elements and dz_element != tg_element:
        strong_elements.append(dz_element)

    # 弱五行 = 五行中不在旺列表中的
    for elem in WUXING_LIST:
        if elem not in strong_elements:
            weak_elements.append(elem)

    # 与日主的关系
    tg_relation = _get_element_relation(tg_element, day_master)
    dz_relation = _get_element_relation(dz_element, day_master)

    # 建议
    beneficial: List[str] = []
    for elem in suggested_elements:
        if elem in strong_elements:
            beneficial.append(f"{elem}旺（喜用神当令）")

    harmful: List[str] = []
    for elem in avoid_elements:
        if elem in strong_elements:
            harmful.append(f"{elem}旺（忌神当令）")

    return {
        "strong_elements": strong_elements,
        "weak_elements": weak_elements,
        "season_element": season_element,
        "month_tg_element": tg_element,
        "month_dz_element": dz_element,
        "tg_relation_to_master": tg_relation,
        "dz_relation_to_master": dz_relation,
        "beneficial": beneficial,
        "harmful": harmful,
    }


def generate_monthly_outfit_strategy(monthly_fortune: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成月度穿搭策略

    基于月度五行旺衰，推荐主色调和辅色调

    Args:
        monthly_fortune: 月度运势计算结果

    Returns:
        {primary_colors, secondary_colors, styles, materials, avoid_colors}
    """
    suggested_elements = monthly_fortune.get("suggested_elements", [])
    avoid_elements = monthly_fortune.get("avoid_elements", [])
    day_master = monthly_fortune.get("day_master", "土")
    season_element = monthly_fortune.get("season_element", "土")
    strong_elements = monthly_fortune.get("element_analysis", {}).get("strong_elements", [])

    # 喜用神五行列表（用于主色调）
    primary_wuxing = list(suggested_elements[:2]) if suggested_elements else [day_master]

    # 辅助五行 = 季节五行中不冲突的
    secondary_wuxing: List[str] = []
    if season_element not in primary_wuxing and season_element not in avoid_elements:
        secondary_wuxing.append(season_element)
    # 从旺五行中取不冲突的
    for elem in strong_elements:
        if elem not in primary_wuxing and elem not in avoid_elements and len(secondary_wuxing) < 2:
            secondary_wuxing.append(elem)

    # 主色调
    primary_colors: List[str] = []
    for elem in primary_wuxing:
        primary_colors.extend(ELEMENT_COLOR_MAP.get(elem, [])[:2])
    primary_colors = list(dict.fromkeys(primary_colors))[:3]

    # 辅色调
    secondary_colors: List[str] = []
    for elem in secondary_wuxing:
        secondary_colors.extend(ELEMENT_COLOR_MAP.get(elem, [])[:1])
    secondary_colors = list(dict.fromkeys(secondary_colors))[:3]

    # 风格关键词
    styles: List[str] = []
    for elem in primary_wuxing:
        styles.extend(ELEMENT_STYLE_MAP.get(elem, [])[:2])
    styles = list(dict.fromkeys(styles))[:4]

    # 材质
    materials: List[str] = []
    for elem in primary_wuxing:
        materials.extend(ELEMENT_MATERIAL_MAP.get(elem, [])[:2])
    materials = list(dict.fromkeys(materials))[:3]

    # 忌用颜色
    avoid_colors: List[str] = []
    for elem in avoid_elements:
        avoid_colors.extend(ELEMENT_COLOR_MAP.get(elem, [])[:1])
    avoid_colors = list(dict.fromkeys(avoid_colors))[:3]

    return {
        "primary_colors": primary_colors,
        "secondary_colors": secondary_colors,
        "styles": styles,
        "materials": materials,
        "avoid_colors": avoid_colors,
        "primary_elements": primary_wuxing,
        "secondary_elements": secondary_wuxing,
    }


def calculate_yearly_fortune(
    user_bazi: Dict[str, Any],
    year: int,
) -> Dict[str, Any]:
    """
    计算年度运势

    整合12个月的运势趋势，标注关键月份

    Args:
        user_bazi: 用户八字信息
        year: 年份

    Returns:
        {year, overall_score, monthly_summary, peak_months, low_months, yearly_advice}
    """
    monthly_summary: List[Dict[str, Any]] = []
    all_scores: List[int] = []

    for month in range(1, 13):
        fortune = calculate_monthly_fortune(user_bazi, year, month)
        monthly_summary.append({
            "month": month,
            "month_ganzhi": fortune["month_ganzhi"],
            "overall_score": fortune["overall_score"],
            "scores": fortune["scores"],
            "outfit_strategy": fortune["outfit_strategy"],
        })
        all_scores.append(fortune["overall_score"])

    # 年度总评
    overall_score = int(sum(all_scores) / len(all_scores)) if all_scores else 50

    # 旺月/衰月（以总评分排序）
    month_scores = [(m["month"], m["overall_score"]) for m in monthly_summary]
    sorted_months = sorted(month_scores, key=lambda x: x[1], reverse=True)

    # 旺月：前3名且分数 > overall_score
    peak_months = [m[0] for m in sorted_months[:3] if m[1] > overall_score]
    # 衰月：后3名且分数 < overall_score
    low_months = [m[0] for m in sorted_months[-3:] if m[1] < overall_score]

    # 年度建议
    yearly_advice = _generate_yearly_advice(
        overall_score, peak_months, low_months, user_bazi, year
    )

    return {
        "year": year,
        "overall_score": overall_score,
        "monthly_summary": monthly_summary,
        "peak_months": peak_months,
        "low_months": low_months,
        "yearly_advice": yearly_advice,
    }


def _generate_yearly_advice(
    overall_score: int,
    peak_months: List[int],
    low_months: List[int],
    user_bazi: Dict[str, Any],
    year: int,
) -> str:
    """生成年度运势建议"""
    day_master = user_bazi.get("day_master", "土")
    suggested = user_bazi.get("suggested_elements", [])

    parts: List[str] = []

    # 总体评价
    if overall_score >= 75:
        parts.append(f"{year}年运势大吉，综合指数{overall_score}。")
    elif overall_score >= 65:
        parts.append(f"{year}年运势良好，综合指数{overall_score}。")
    elif overall_score >= 50:
        parts.append(f"{year}年运势平稳，综合指数{overall_score}。")
    else:
        parts.append(f"{year}年运势偏弱，综合指数{overall_score}，需谨慎行事。")

    # 旺月提示
    if peak_months:
        months_str = "、".join(f"{m}月" for m in peak_months)
        parts.append(f"旺月在{months_str}，宜把握机遇、积极进取。")

    # 衰月提示
    if low_months:
        months_str = "、".join(f"{m}月" for m in low_months)
        parts.append(f"{months_str}需低调行事、注意身体和人际关系。")

    # 五行建议
    if suggested:
        parts.append(f"年度宜多穿戴{'、'.join(suggested[:2])}属性的衣物，以增强运势。")

    parts.append(f"日主{day_master}，宜顺势而为，从容应对。")

    return "".join(parts)
