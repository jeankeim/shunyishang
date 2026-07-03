"""
每日运势计算引擎
基于八字五行计算五维度运势和穿搭建议
"""

import logging
import random
from datetime import date, datetime
from typing import Dict, List, Optional, Any

import cnlunar

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
    WUXING_BEI_KE,
    WUXING_LIST,
    ELEMENT_COLOR_MAP,
    ELEMENT_MATERIAL_MAP,
)

logger = logging.getLogger(__name__)

# 方位映射
ELEMENT_DIRECTION_MAP: Dict[str, List[str]] = {
    "金": ["西", "西北"],
    "木": ["东", "东南"],
    "水": ["北", "西北"],
    "火": ["南", "西南"],
    "土": ["中", "东北", "西南"],
}

# 五维度与五行的关联权重
# 每个维度有不同的五行偏好
DIMENSION_ELEMENT_AFFINITY: Dict[str, Dict[str, float]] = {
    "career": {"金": 1.2, "土": 1.1, "水": 1.0, "火": 0.9, "木": 0.8},
    "wealth": {"金": 1.3, "水": 1.1, "土": 1.0, "火": 0.9, "木": 0.7},
    "love": {"火": 1.3, "木": 1.1, "水": 1.0, "土": 0.9, "金": 0.7},
    "health": {"木": 1.2, "水": 1.1, "土": 1.0, "金": 0.9, "火": 0.8},
    "study": {"水": 1.3, "木": 1.1, "金": 1.0, "土": 0.9, "火": 0.7},
}


def _get_day_ganzhi(target_date: date) -> tuple:
    """获取目标日期的天干地支"""
    dt = datetime(target_date.year, target_date.month, target_date.day, 12)
    lunar = cnlunar.Lunar(dt, godType='8char')
    day_gz = lunar.day8Char
    return day_gz[0], day_gz[1]  # 天干, 地支


def _get_element_relation(elem_a: str, elem_b: str) -> str:
    """
    判断 elem_a 对 elem_b 的关系
    返回: sheng(生), ke(克), bi(比), xie(泄), hao(耗)
    """
    if elem_a == elem_b:
        return "bi"  # 比（同）
    if WUXING_SHENG.get(elem_a) == elem_b:
        return "xie"  # 泄（我生之）
    if WUXING_KE.get(elem_a) == elem_b:
        return "hao"  # 耗（我克之）
    if WUXING_BEI_SHENG.get(elem_a) == elem_b:
        return "sheng"  # 生（生我者）
    if WUXING_BEI_KE.get(elem_a) == elem_b:
        return "ke"  # 克（克我者）
    return "bi"


def _calculate_relation_score(relation: str) -> float:
    """关系 -> 分数系数"""
    return {
        "sheng": 1.15,   # 被生：好运
        "bi": 1.05,      # 比和：平稳偏好
        "xie": 0.90,     # 泄气：稍弱
        "hao": 0.85,     # 耗气：消耗
        "ke": 0.70,      # 被克：不利
    }.get(relation, 1.0)


def calculate_daily_fortune(
    user_bazi: Dict[str, Any],
    target_date: date,
) -> Dict[str, Any]:
    """
    计算五维度运势

    Args:
        user_bazi: 用户的八字信息 (dict with day_master, suggested_elements, etc.)
        target_date: 目标日期

    Returns:
        {scores: {career, wealth, love, health, study},
         overall_score: int,
         advice_text: str,
         lucky_elements: {colors, materials, directions, elements},
         outfit_suggestion: str}
    """
    day_master = user_bazi.get("day_master", "土")
    suggested_elements = user_bazi.get("suggested_elements", [])
    avoid_elements = user_bazi.get("avoid_elements", [])

    # 获取目标日期的天干地支
    day_tiangan, day_dizhi = _get_day_ganzhi(target_date)
    day_element = TIANGAN_WUXING.get(day_tiangan, "土")
    dizhi_element = DIZHI_WUXING.get(day_dizhi, "土")

    # 计算日干与用户日干的五行关系
    tiangan_relation = _get_element_relation(day_element, day_master)
    dizhi_relation = _get_element_relation(dizhi_element, day_master)

    # 基础分数
    base_score = 65

    # 使用日期作为确定性随机种子（同一天同一用户结果一致）
    seed_val = hash(f"{user_bazi.get('pillars', {}).get('day', 'default')}_{target_date.isoformat()}")
    rng = random.Random(seed_val)

    scores: Dict[str, int] = {}
    for dimension, affinity_map in DIMENSION_ELEMENT_AFFINITY.items():
        # 天干影响(60%) + 地支影响(40%)
        tg_affinity = affinity_map.get(day_element, 1.0)
        dz_affinity = affinity_map.get(dizhi_element, 1.0)

        tg_relation_score = _calculate_relation_score(tiangan_relation)
        dz_relation_score = _calculate_relation_score(dizhi_relation)

        raw = base_score * (tg_affinity * tg_relation_score * 0.6 +
                            dz_affinity * dz_relation_score * 0.4)

        # 喜用神加成
        if day_element in suggested_elements:
            raw += 8
        if dizhi_element in suggested_elements:
            raw += 5

        # 忌神减分
        if day_element in avoid_elements:
            raw -= 8
        if dizhi_element in avoid_elements:
            raw -= 5

        # 小幅随机波动(±5)
        raw += rng.randint(-5, 5)

        scores[dimension] = max(0, min(100, int(raw)))

    overall = int(sum(scores.values()) / len(scores))

    # 幸运元素
    lucky_elements = _generate_lucky_elements(day_element, suggested_elements, day_master)

    # 穿搭建议
    outfit_suggestion = generate_outfit_suggestion(scores, user_bazi, lucky_elements)

    # 运势建议文本
    advice_text = _generate_advice(scores, day_element, day_master, suggested_elements)

    return {
        "scores": scores,
        "overall_score": overall,
        "advice_text": advice_text,
        "lucky_elements": lucky_elements,
        "outfit_suggestion": outfit_suggestion,
        "bazi_snapshot": {
            "day_master": day_master,
            "target_day_ganzhi": f"{day_tiangan}{day_dizhi}",
            "target_day_element": day_element,
            "pillars": user_bazi.get("pillars", {}),
        },
    }


def _generate_lucky_elements(
    day_element: str,
    suggested_elements: List[str],
    day_master: str,
) -> Dict[str, List[str]]:
    """生成幸运元素"""
    # 幸运五行 = 喜用神优先 + 当日五行辅助
    lucky_wuxing = list(suggested_elements[:2]) if suggested_elements else [day_master]
    if day_element not in lucky_wuxing and len(lucky_wuxing) < 3:
        lucky_wuxing.append(day_element)
    lucky_wuxing = lucky_wuxing[:3]

    # 从幸运五行推导颜色
    colors: List[str] = []
    for elem in lucky_wuxing:
        elem_colors = ELEMENT_COLOR_MAP.get(elem, [])
        colors.extend(elem_colors[:2])
    colors = list(dict.fromkeys(colors))[:5]

    # 材质
    materials: List[str] = []
    for elem in lucky_wuxing:
        elem_materials = ELEMENT_MATERIAL_MAP.get(elem, [])
        materials.extend(elem_materials[:2])
    materials = list(dict.fromkeys(materials))[:4]

    # 方位
    directions: List[str] = []
    for elem in lucky_wuxing:
        dirs = ELEMENT_DIRECTION_MAP.get(elem, [])
        directions.extend(dirs)
    directions = list(dict.fromkeys(directions))[:3]

    return {
        "colors": colors,
        "materials": materials,
        "directions": directions,
        "elements": lucky_wuxing,
    }


def generate_outfit_suggestion(
    fortune_scores: Dict[str, int],
    user_bazi: Dict[str, Any],
    lucky_elements: Optional[Dict] = None,
) -> str:
    """基于运势生成穿搭建议文本"""
    suggested = user_bazi.get("suggested_elements", [])
    day_master = user_bazi.get("day_master", "土")

    # 找出最高和最低维度
    sorted_dims = sorted(fortune_scores.items(), key=lambda x: x[1], reverse=True)
    best_dim = sorted_dims[0]
    worst_dim = sorted_dims[-1]

    dim_names = {
        "career": "事业", "wealth": "财运",
        "love": "桃花", "health": "健康", "study": "学业"
    }

    parts = []
    parts.append(f"今日{dim_names[best_dim[0]]}运最旺（{best_dim[1]}分），"
                 f"{dim_names[worst_dim[0]]}运需留意（{worst_dim[1]}分）。")

    if lucky_elements:
        le = lucky_elements
        if le.get("colors"):
            parts.append(f"建议穿着{'、'.join(le['colors'][:3])}色系衣物。")
        if le.get("materials"):
            parts.append(f"材质上推荐{'、'.join(le['materials'][:2])}。")

    if suggested:
        parts.append(f"五行上宜选{'、'.join(suggested[:2])}属性的穿搭，"
                     f"以增强整体运势。")

    return "".join(parts)


def _generate_advice(
    scores: Dict[str, int],
    day_element: str,
    day_master: str,
    suggested_elements: List[str],
) -> str:
    """生成运势建议文本"""
    overall = int(sum(scores.values()) / len(scores))

    if overall >= 80:
        tone = "今日运势大吉"
    elif overall >= 65:
        tone = "今日运势良好"
    elif overall >= 50:
        tone = "今日运势平稳"
    else:
        tone = "今日运势偏弱"

    parts = [f"{tone}，综合指数 {overall}。"]
    parts.append(f"今日天干属{day_element}，您的日元属{day_master}。")

    relation = _get_element_relation(day_element, day_master)
    relation_text = {
        "sheng": "天干生扶日元，贵人相助，诸事顺遂。",
        "bi": "天干与日元比和，平稳安宁，宜守不宜急。",
        "xie": "日元生天干，精力外泄，注意休息。",
        "hao": "日元克天干，耗气劳神，宜量力而行。",
        "ke": "天干克日元，压力较大，宜韬光养晦。",
    }
    parts.append(relation_text.get(relation, ""))

    if suggested_elements:
        parts.append(f"今日宜穿戴{'、'.join(suggested_elements[:2])}五行属性的衣物饰品，以增强运势。")

    return "".join(parts)
