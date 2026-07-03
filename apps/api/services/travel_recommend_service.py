"""
旅行穿搭推荐服务
集成天气预测、多天穿搭规划和八字五行分析
"""

import logging
from typing import Dict, List, Optional

from packages.utils.weather_forecast import (
    get_destination_weather,
    predict_weather_element,
)
from packages.utils.travel_planner import (
    plan_travel_outfits,
    optimize_luggage,
    calculate_luggage_score,
)
from packages.utils.wuxing_rules import WUXING_LIST

logger = logging.getLogger(__name__)


def generate_travel_recommendation(
    user_id: Optional[int],
    destination: str,
    days: int,
    scenes_per_day: List[str],
    luggage_size: str = "中",
    bazi: Optional[Dict] = None,
) -> Dict:
    """
    旅行推荐入口

    调用 weather_forecast 获取目的地天气，调用 travel_planner 生成多天穿搭计划，
    集成八字五行分析，返回完整的旅行穿搭方案。

    Args:
        user_id: 用户ID
        destination: 目的地城市
        days: 旅行天数
        scenes_per_day: 每天场景列表
        luggage_size: 行李箱大小 (小/中/大)
        bazi: 八字信息

    Returns:
        {
            "outfits_plan": [...],
            "luggage_summary": {...},
            "weather_forecast": [...],
            "wuxing_analysis": {...}
        }
    """
    logger.info(
        f"[旅行推荐] 用户={user_id}, 目的地={destination}, 天数={days}, "
        f"行李箱={luggage_size}"
    )

    # 1. 获取目的地多天天气
    weather_forecast = get_destination_weather(destination, days)

    # 2. 提取八字喜用神
    target_elements = []
    bazi_reasoning = None
    if bazi and isinstance(bazi, dict):
        target_elements = bazi.get("suggested_elements", [])
        bazi_reasoning = bazi.get("reasoning")
    else:
        # 无八字时使用默认平衡五行
        target_elements = WUXING_LIST[:2]

    user_bazi = {
        "suggested_elements": target_elements,
        "reasoning": bazi_reasoning,
    }

    # 3. 规划多天穿搭
    outfits_plan = plan_travel_outfits(
        user_bazi=user_bazi,
        destination_weather=weather_forecast,
        days=days,
        scenes_per_day=scenes_per_day,
        luggage_capacity=luggage_size,
    )

    # 4. 优化行李箱
    optimized_days = optimize_luggage(outfits_plan.get("days", []), luggage_size)

    # 5. 计算行李评分
    all_items = []
    seen_ids = set()
    for day in optimized_days:
        for item in day.get("items", []):
            item_id = item.get("id", item.get("name", ""))
            if item_id not in seen_ids:
                all_items.append(item)
                seen_ids.add(item_id)

    luggage_score = calculate_luggage_score(all_items, luggage_size)

    # 6. 五行分析
    wuxing_analysis = _build_wuxing_analysis(
        weather_forecast, all_items, target_elements
    )

    result = {
        "outfits_plan": optimized_days,
        "luggage_summary": {
            **outfits_plan.get("luggage_summary", {}),
            "luggage_score": luggage_score,
        },
        "weather_forecast": weather_forecast,
        "wuxing_analysis": wuxing_analysis,
    }

    logger.info(
        f"[旅行推荐] 完成，共 {len(optimized_days)} 天，"
        f"行李评分={luggage_score}"
    )

    return result


def _build_wuxing_analysis(
    weather_forecast: List[Dict],
    items: List[Dict],
    target_elements: List[str],
) -> Dict:
    """构建五行分析报告"""
    # 天气五行
    weather_elements = []
    for wf in weather_forecast:
        weather_desc = wf.get("weather_desc", "")
        element = predict_weather_element(weather_desc)
        weather_elements.append({
            "date": wf.get("date"),
            "weather": weather_desc,
            "element": element,
        })

    # 物品五行分布
    element_distribution: Dict[str, int] = {}
    for item in items:
        element = item.get("primary_element", "")
        if element:
            element_distribution[element] = element_distribution.get(element, 0) + 1

    # 五行平衡度
    covered = len(element_distribution)
    balance_score = round(covered / 5.0, 3)

    return {
        "target_elements": target_elements,
        "weather_elements": weather_elements,
        "item_element_distribution": element_distribution,
        "balance_score": balance_score,
        "balance_reasoning": _generate_balance_reasoning(
            element_distribution, target_elements
        ),
    }


def _generate_balance_reasoning(
    element_distribution: Dict[str, int],
    target_elements: List[str],
) -> str:
    """生成五行平衡建议"""
    if not element_distribution:
        return "暂无衣物数据，无法分析五行平衡。"

    covered = set(element_distribution.keys())
    missing = set(WUXING_LIST) - covered
    target_covered = set(target_elements) & covered

    parts = []
    parts.append(
        f"当前行李五行覆盖 {len(covered)}/5 行"
        f"（{', '.join(sorted(covered))}）。"
    )

    if missing:
        parts.append(f"缺失：{', '.join(sorted(missing))}。")

    if target_elements:
        if target_covered:
            parts.append(
                f"喜用神 {', '.join(target_elements)} 中已覆盖 "
                f"{', '.join(sorted(target_covered))}。"
            )
        else:
            parts.append(
                f"喜用神 {', '.join(target_elements)} 暂未覆盖，建议补充。"
            )

    return " ".join(parts)
