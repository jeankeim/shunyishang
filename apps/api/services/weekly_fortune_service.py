"""
流年运势周报服务
基于用户八字，聚合本周7天运势，生成趋势分析与穿搭建议
"""

import logging
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
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
    calculate_daily_fortune,
    ELEMENT_DIRECTION_MAP,
    DIMENSION_ELEMENT_AFFINITY,
    _get_element_relation,
    _calculate_relation_score,
    _get_day_ganzhi,
)
from apps.api.core.time_utils import today_cn
from apps.api.services.user_service import get_user_bazi

logger = logging.getLogger(__name__)


def _get_week_range(ref_date: Optional[date] = None) -> tuple:
    """
    获取本周的起止日期（ISO周，周一到周日）

    Returns:
        (start_date, end_date)
    """
    today = ref_date or today_cn()
    # ISO weekday: Monday=1, Sunday=7
    start = today - timedelta(days=today.isoweekday() - 1)
    end = start + timedelta(days=6)
    return start, end


def _determine_trend(scores: List[int]) -> str:
    """
    根据7天分数趋势判断整体走势

    比较前3天均值与后3天均值
    """
    if len(scores) < 4:
        return "平稳"
    first_half = sum(scores[:3]) / 3
    second_half = sum(scores[-3:]) / 3
    diff = second_half - first_half
    if diff > 5:
        return "上升"
    elif diff < -5:
        return "下降"
    return "平稳"


def _generate_weekly_style_keywords(weekly_elements: List[str]) -> List[str]:
    """基于周幸运五行生成风格关键词"""
    keywords: List[str] = []
    for elem in weekly_elements:
        styles = ELEMENT_STYLE_MAP.get(elem, [])
        keywords.extend(styles[:2])
    # 去重并限制数量
    return list(dict.fromkeys(keywords))[:4]


def _generate_weekly_outfit_suggestion(
    weekly_elements: List[str],
    day_master: str,
    overall_score: int,
    trend: str,
) -> str:
    """生成周报穿搭建议"""
    parts: List[str] = []

    # 趋势导语
    if trend == "上升":
        parts.append(f"本周运势呈上升趋势，整体指数{overall_score}，宜积极进取。")
    elif trend == "下降":
        parts.append(f"本周运势略有回落，整体指数{overall_score}，宜韬光养晦。")
    else:
        parts.append(f"本周运势平稳，整体指数{overall_score}，宜守成拓展。")

    # 五行穿搭
    if weekly_elements:
        primary_elem = weekly_elements[0]
        colors = ELEMENT_COLOR_MAP.get(primary_elem, [])
        materials = ELEMENT_MATERIAL_MAP.get(primary_elem, [])
        if colors:
            parts.append(f"本周{primary_elem}气旺盛，适合{'、'.join(colors[:3])}色系。")
        if materials:
            parts.append(f"材质推荐{'、'.join(materials[:2])}。")

    # 日主辅助建议
    if weekly_elements and day_master:
        parts.append(f"日元{day_master}，搭配{'、'.join(weekly_elements[:2])}属性饰品可增强运势。")

    return "".join(parts)


def _compute_weekly_lucky_elements(
    daily_fortunes: List[Dict[str, Any]],
    suggested_elements: List[str],
    day_master: str,
) -> List[str]:
    """聚合7天幸运五行，取出现频率最高的2-3个"""
    element_count: Dict[str, int] = {}
    for fortune in daily_fortunes:
        lucky = fortune.get("lucky_elements", {})
        elements = lucky.get("elements", [])
        for elem in elements:
            element_count[elem] = element_count.get(elem, 0) + 1

    # 按频率降序排列
    sorted_elements = sorted(element_count.items(), key=lambda x: x[1], reverse=True)

    # 优先取喜用神
    result: List[str] = []
    for elem in suggested_elements:
        if elem in element_count and elem not in result:
            result.append(elem)

    # 再按频率补充
    for elem, _ in sorted_elements:
        if elem not in result:
            result.append(elem)
        if len(result) >= 3:
            break

    return result[:3] if result else [day_master]


class WeeklyFortuneService:
    """流年运势周报服务"""

    async def calculate_weekly_fortune(self, user_id: int) -> dict:
        """
        计算本周运势周报。

        返回:
        {
            "week_number": 28,
            "year": 2026,
            "start_date": "2026-07-13",
            "end_date": "2026-07-19",
            "overall_trend": "上升",
            "overall_score": 78,
            "daily_fortunes": [
                {"date": "...", "score": 80, "lucky_element": "木", "lucky_color": "绿色"},
                ...
            ],
            "weekly_lucky_elements": ["木", "火"],
            "weekly_style_keywords": ["清新自然", "生机盎然"],
            "outfit_suggestions": "本周木气旺盛，适合绿色系、棉麻材质..."
        }
        """
        try:
            return self._calculate(user_id)
        except Exception as e:
            logger.error(f"[WeeklyFortune] 用户{user_id}周报计算失败，返回通用周报: {e}")
            return self._fallback_weekly_report()

    def _calculate(self, user_id: int) -> dict:
        """核心计算逻辑"""
        user_bazi = get_user_bazi(user_id)
        day_master = user_bazi.get("day_master", "土")
        suggested_elements = user_bazi.get("suggested_elements", [])

        now = today_cn()
        iso_cal = now.isocalendar()
        week_number = iso_cal[1]
        year = iso_cal[0]

        start_date, end_date = _get_week_range(now)

        # 计算7天每日运势
        daily_fortunes: List[Dict[str, Any]] = []
        daily_scores: List[int] = []

        for i in range(7):
            current_day = start_date + timedelta(days=i)
            fortune = calculate_daily_fortune(user_bazi, current_day, generate_ai=False)

            overall = fortune.get("overall_score", 65)
            lucky = fortune.get("lucky_elements", {})
            lucky_elements = lucky.get("elements", [])
            lucky_colors = lucky.get("colors", [])

            # 提取主幸运元素和颜色
            primary_element = lucky_elements[0] if lucky_elements else day_master
            primary_color = lucky_colors[0] if lucky_colors else "绿色"

            daily_fortunes.append({
                "date": current_day.isoformat(),
                "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][i],
                "score": overall,
                "scores": fortune.get("scores", {}),
                "lucky_element": primary_element,
                "lucky_color": primary_color,
                "lucky_colors": lucky_colors[:3],
                "outfit_suggestion": fortune.get("outfit_suggestion", ""),
            })
            daily_scores.append(overall)

        # 聚合分析
        overall_score = int(sum(daily_scores) / len(daily_scores)) if daily_scores else 65
        overall_trend = _determine_trend(daily_scores)

        # 周幸运元素
        weekly_lucky_elements = _compute_weekly_lucky_elements(
            daily_fortunes, suggested_elements, day_master
        )

        # 风格关键词
        weekly_style_keywords = _generate_weekly_style_keywords(weekly_lucky_elements)

        # 穿搭建议
        outfit_suggestions = _generate_weekly_outfit_suggestion(
            weekly_lucky_elements, day_master, overall_score, overall_trend
        )

        # 最佳/需留意日期
        sorted_days = sorted(daily_fortunes, key=lambda x: x["score"], reverse=True)
        best_day = sorted_days[0] if sorted_days else None
        low_day = sorted_days[-1] if sorted_days else None

        result = {
            "week_number": week_number,
            "year": year,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "overall_trend": overall_trend,
            "overall_score": overall_score,
            "daily_fortunes": daily_fortunes,
            "weekly_lucky_elements": weekly_lucky_elements,
            "weekly_lucky_colors": list(dict.fromkeys(
                c for df in daily_fortunes for c in df.get("lucky_colors", [])
            ))[:5],
            "weekly_style_keywords": weekly_style_keywords,
            "outfit_suggestions": outfit_suggestions,
            "best_day": {
                "date": best_day["date"],
                "weekday": best_day["weekday"],
                "score": best_day["score"],
            } if best_day else None,
            "low_day": {
                "date": low_day["date"],
                "weekday": low_day["weekday"],
                "score": low_day["score"],
            } if low_day else None,
            "day_master": day_master,
        }

        return result

    def _fallback_weekly_report(self) -> dict:
        """通用兜底周报（计算失败时使用）"""
        now = today_cn()
        iso_cal = now.isocalendar()
        start_date, end_date = _get_week_range(now)

        return {
            "week_number": iso_cal[1],
            "year": iso_cal[0],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "overall_trend": "平稳",
            "overall_score": 65,
            "daily_fortunes": [],
            "weekly_lucky_elements": ["土"],
            "weekly_lucky_colors": ["棕色", "黄色"],
            "weekly_style_keywords": ["稳重", "舒适"],
            "outfit_suggestions": "本周运势平稳，宜穿着舒适自然的衣物，保持良好心态。",
            "best_day": None,
            "low_day": None,
            "day_master": "土",
        }
