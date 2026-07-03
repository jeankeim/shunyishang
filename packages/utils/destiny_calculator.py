"""
大运流年计算器
基于用户八字推算十年大运周期和流年运势

大运计算规则：
- 起运年龄：阳男阴女顺排，阴男阳女逆排
- 每步大运10年
- 从月柱开始顺推或逆推天干地支
- luck_level: 旺/相/休/囚/死（基于大运五行与日主关系）
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import cnlunar

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
    WUXING_BEI_KE,
    ELEMENT_COLOR_MAP,
    ELEMENT_MATERIAL_MAP,
    WUXING_LIST,
)

logger = logging.getLogger(__name__)

# 天干列表（顺序）
TIANGAN_LIST: List[str] = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# 地支列表（顺序）
DIZHI_LIST: List[str] = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干阴阳属性
TIANGAN_YINYANG: Dict[str, str] = {
    "甲": "阳", "丙": "阳", "戊": "阳", "庚": "阳", "壬": "阳",
    "乙": "阴", "丁": "阴", "己": "阴", "辛": "阴", "癸": "阴",
}

# 60甲子序列（用于大运顺逆排）
JIAZI_60: List[str] = []
_tg_idx, _dz_idx = 0, 0
for _ in range(60):
    JIAZI_60.append(f"{TIANGAN_LIST[_tg_idx]}{DIZHI_LIST[_dz_idx]}")
    _tg_idx = (_tg_idx + 1) % 10
    _dz_idx = (_dz_idx + 1) % 12


def _jiazi_index(ganzhi: str) -> int:
    """获取干支在60甲子中的索引"""
    try:
        return JIAZI_60.index(ganzhi)
    except ValueError:
        return 0


def _jiazi_at(index: int) -> str:
    """获取60甲子序列中指定索引的干支（支持负数/超界回绕）"""
    return JIAZI_60[index % 60]


# ============================================================
# 起运年龄计算
# ============================================================

def _calculate_start_age(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    gender: str,
    year_stem: Optional[str] = None,
) -> int:
    """
    计算起运年龄（精确版）

    传统方法：3天折合1年。
    阳男阴女：从出生日顺数到下一个节气
    阴男阳女：从出生日逆数到上一个节气

    使用 cnlunar 的精确节气日期列表计算。
    """
    dt = datetime(birth_year, birth_month, birth_day, 12)
    lunar = cnlunar.Lunar(dt, godType='8char')

    # 获取年柱天干以判断阴阳（优先使用传入值，否则从 cnlunar 获取）
    if year_stem is None:
        year_gz = lunar.year8Char
        year_stem = year_gz[0]
    year_yinyang = TIANGAN_YINYANG.get(year_stem, "阳")

    # 判断顺排/逆排
    # 阳男阴女顺排，阴男阳女逆排
    if (year_yinyang == "阳" and gender == "男") or \
       (year_yinyang == "阴" and gender == "女"):
        forward = True
    else:
        forward = False

    # 获取当年精确节气日期列表 {节气名: (月, 日)}
    solar_terms = lunar.thisYearSolarTermsDic

    # 节（非中气）：立春/惊蛰/清明/立夏/芒种/小暑/立秋/白露/寒露/立冬/大雪/小寒
    jie_names = ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑',
                 '立秋', '白露', '寒露', '立冬', '大雪', '小寒']

    # 获取当年所有节的日期
    jie_dates = []
    for name in jie_names:
        if name in solar_terms:
            m, d = solar_terms[name]
            jie_dates.append(date(birth_year, m, d))
    jie_dates.sort()

    birth_date = date(birth_year, birth_month, birth_day)

    if forward:
        # 顺排：找出生日之后的下一个节气
        next_jie = None
        for jd in jie_dates:
            if jd > birth_date:
                next_jie = jd
                break
        # 如果当年没有后续节气，用次年立春
        if next_jie is None:
            next_lunar = cnlunar.Lunar(datetime(birth_year + 1, 1, 1, 12), godType='8char')
            next_terms = next_lunar.thisYearSolarTermsDic
            if '立春' in next_terms:
                m, d = next_terms['立春']
                next_jie = date(birth_year + 1, m, d)
            else:
                next_jie = date(birth_year + 1, 2, 4)
        days_diff = (next_jie - birth_date).days
    else:
        # 逆排：找出生日之前的上一个节气
        prev_jie = None
        for jd in reversed(jie_dates):
            if jd < birth_date:
                prev_jie = jd
                break
        # 如果当年没有之前的节气，用上年大雪
        if prev_jie is None:
            prev_lunar = cnlunar.Lunar(datetime(birth_year - 1, 12, 1, 12), godType='8char')
            prev_terms = prev_lunar.thisYearSolarTermsDic
            if '大雪' in prev_terms:
                m, d = prev_terms['大雪']
                prev_jie = date(birth_year - 1, m, d)
            else:
                prev_jie = date(birth_year - 1, 12, 7)
        days_diff = (birth_date - prev_jie).days

    # 3天 = 1年，有余数按1年计（传统取整法），再+1转为虚岁
    # 传统八字大运起运年龄使用虚岁，与问真八字等专业软件一致
    # 例: 21天 ÷ 3 = 7年(周岁) → 8岁起运(虚岁)
    completed_years = (days_diff + 2) // 3  # 向上取整
    start_age = completed_years + 1  # 转为虚岁
    return start_age


# ============================================================
# 大运计算
# ============================================================

def calculate_major_luck(
    bazi_result: Dict[str, Any],
    gender: str,
    birth_year: Optional[int] = None,
    birth_month: Optional[int] = None,
    birth_day: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    计算大运周期

    Args:
        bazi_result: 八字计算结果（含pillars等）
        gender: 性别 "男" 或 "女"
        birth_year: 出生年（公历，可选，优先使用）
        birth_month: 出生月
        birth_day: 出生日

    Returns:
        List of 大运周期:
        [{start_age, end_age, heavenly_stem, earthly_branch, element, luck_level}]
    """
    pillars = bazi_result.get("pillars", {})
    month_gz = pillars.get("month", "甲子")
    day_master = bazi_result.get("day_master", "土")

    # 获取月柱在60甲子中的索引
    month_idx = _jiazi_index(month_gz)

    # 判断顺逆排
    year_gz = pillars.get("year", "甲子")
    year_stem = year_gz[0]
    year_yinyang = TIANGAN_YINYANG.get(year_stem, "阳")

    if (year_yinyang == "阳" and gender == "男") or \
       (year_yinyang == "阴" and gender == "女"):
        forward = True
    else:
        forward = False

    # 使用传入的出生日期，或从 bazi_result 中提取
    by = birth_year or bazi_result.get("_birth_year") or 1995
    bm = birth_month or bazi_result.get("_birth_month") or 6
    bd = birth_day or bazi_result.get("_birth_day") or 15

    start_age = _calculate_start_age(by, bm, bd, gender, year_stem=year_stem)

    # 生成8步大运（覆盖0-100岁）
    luck_periods: List[Dict[str, Any]] = []
    for i in range(8):
        if forward:
            luck_gz = _jiazi_at(month_idx + 1 + i)
        else:
            luck_gz = _jiazi_at(month_idx - 1 - i)

        hs = luck_gz[0]
        eb = luck_gz[1]
        element = TIANGAN_WUXING.get(hs, "土")
        luck_level = _determine_luck_level(element, day_master)

        period_start = start_age + i * 10
        period_end = period_start + 10 - 1

        luck_periods.append({
            "start_age": period_start,
            "end_age": period_end,
            "heavenly_stem": hs,
            "earthly_branch": eb,
            "ganzhi": luck_gz,
            "element": element,
            "luck_level": luck_level,
        })

    return luck_periods


def _extract_birth_year(bazi_result: Dict[str, Any]) -> int:
    """从八字结果推断出生年（用于起运计算）"""
    # 尝试从eight_chars或pillars中无法直接获取，使用默认值
    return bazi_result.get("_birth_year", 1995)


def _extract_birth_month(bazi_result: Dict[str, Any]) -> int:
    """从八字结果推断出生月"""
    return bazi_result.get("_birth_month", 6)


def _extract_birth_day(bazi_result: Dict[str, Any]) -> int:
    """从八字结果推断出生日"""
    return bazi_result.get("_birth_day", 15)


def _determine_luck_level(element: str, day_master: str) -> str:
    """
    判断大运五行与日主的关系，确定旺衰等级

    旺: 大运五行 == 日主五行 (比和)
    相: 大运五行生日主 (生我)
    休: 日主生大运五行 (我生)
    囚: 日主克大运五行 (我克)
    死: 大运五行克日主 (克我)
    """
    if element == day_master:
        return "旺"
    if WUXING_SHENG.get(element) == day_master:
        return "相"
    if WUXING_SHENG.get(day_master) == element:
        return "休"
    if WUXING_KE.get(day_master) == element:
        return "囚"
    if WUXING_KE.get(element) == day_master:
        return "死"
    return "旺"


def get_current_major_luck(
    bazi_result: Dict[str, Any],
    gender: str,
    current_age: int,
    birth_year: Optional[int] = None,
    birth_month: Optional[int] = None,
    birth_day: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    获取当前所处的大运周期

    Args:
        bazi_result: 八字计算结果
        gender: 性别
        current_age: 当前年龄
        birth_year: 出生年（公历，可选）
        birth_month: 出生月
        birth_day: 出生日

    Returns:
        当前大运周期详情，若超出范围返回None
    """
    luck_periods = calculate_major_luck(bazi_result, gender, birth_year, birth_month, birth_day)

    for period in luck_periods:
        if period["start_age"] <= current_age <= period["end_age"]:
            return period

    # 边界处理
    if current_age < 0:
        return None
    if luck_periods and current_age > luck_periods[-1]["end_age"]:
        return luck_periods[-1]
    if luck_periods and current_age < luck_periods[0]["start_age"]:
        return luck_periods[0]
    return None


# ============================================================
# 流年计算
# ============================================================

def calculate_annual_luck(
    bazi_result: Dict[str, Any],
    year: int,
) -> Dict[str, Any]:
    """
    计算流年运势

    Args:
        bazi_result: 八字计算结果
        year: 目标年份（公历）

    Returns:
        {year, heavenly_stem, earthly_branch, element, relationship, advice}
    """
    day_master = bazi_result.get("day_master", "土")
    suggested_elements = bazi_result.get("suggested_elements", [])
    avoid_elements = bazi_result.get("avoid_elements", [])

    # 计算流年天干地支
    # 公元4年 = 甲子年
    stem_idx = (year - 4) % 10
    branch_idx = (year - 4) % 12
    hs = TIANGAN_LIST[stem_idx]
    eb = DIZHI_LIST[branch_idx]
    element = TIANGAN_WUXING.get(hs, "土")

    # 流年五行与日主的关系
    relationship = _get_element_relation_desc(element, day_master)

    # 生成建议
    if element == day_master:
        advice = f"流年{hs}{eb}，五行属{element}，与日主比和，运势平稳，宜守成拓展。"
    elif WUXING_SHENG.get(element) == day_master:
        advice = f"流年{hs}{eb}，五行属{element}，生扶日主{day_master}，贵人运旺，宜进取。"
    elif WUXING_SHENG.get(day_master) == element:
        advice = f"流年{hs}{eb}，五行属{element}，日主生之，精力外泄，宜蓄力。"
    elif WUXING_KE.get(day_master) == element:
        advice = f"流年{hs}{eb}，五行属{element}，日主克之，需耗费精力，宜量力而行。"
    elif WUXING_KE.get(element) == day_master:
        advice = f"流年{hs}{eb}，五行属{element}，克制日主{day_master}，压力较大，宜韬光养晦。"
    else:
        advice = f"流年{hs}{eb}，五行属{element}，运势中性。"

    # 喜用神加成
    if element in suggested_elements:
        advice += " 流年五行为喜用神，运势更佳。"
    if element in avoid_elements:
        advice += " 流年五行为忌神，需谨慎行事。"

    return {
        "year": year,
        "heavenly_stem": hs,
        "earthly_branch": eb,
        "ganzhi": f"{hs}{eb}",
        "element": element,
        "relationship": relationship,
        "advice": advice,
    }


def _get_element_relation_desc(elem_a: str, elem_b: str) -> str:
    """获取五行关系描述文字"""
    if elem_a == elem_b:
        return "比和"
    if WUXING_SHENG.get(elem_a) == elem_b:
        return "生扶"
    if WUXING_SHENG.get(elem_b) == elem_a:
        return "泄气"
    if WUXING_KE.get(elem_a) == elem_b:
        return "克制"
    if WUXING_KE.get(elem_b) == elem_a:
        return "受克"
    return "中性"


# ============================================================
# 年度运势分析
# ============================================================

def analyze_year_fortune(
    bazi_result: Dict[str, Any],
    year: int,
) -> Dict[str, Any]:
    """
    年度运势综合分析

    综合大运+流年+太岁关系，返回五维度评分和穿搭建议

    Args:
        bazi_result: 八字计算结果
        year: 目标年份

    Returns:
        {year, scores, lucky_colors, lucky_materials, lucky_directions,
         outfit_advice, annual_luck, overall_score}
    """
    day_master = bazi_result.get("day_master", "土")
    suggested_elements = bazi_result.get("suggested_elements", [])
    avoid_elements = bazi_result.get("avoid_elements", [])

    # 流年信息
    annual = calculate_annual_luck(bazi_result, year)
    year_element = annual["element"]

    # 太岁（流年地支）
    year_branch = annual["earthly_branch"]
    taishui_element = DIZHI_WUXING.get(year_branch, "土")

    # 五维度评分计算
    scores = _calculate_year_scores(
        day_master, year_element, taishui_element,
        suggested_elements, avoid_elements, year
    )

    overall_score = int(sum(scores.values()) / len(scores))

    # 幸运颜色/材质/方位
    lucky_wuxing = list(suggested_elements[:2]) if suggested_elements else [day_master]
    if year_element not in lucky_wuxing and len(lucky_wuxing) < 3:
        lucky_wuxing.append(year_element)

    lucky_colors: List[str] = []
    lucky_materials: List[str] = []
    lucky_directions: List[str] = []

    from packages.utils.wuxing_rules import ELEMENT_STYLE_MAP
    from apps.api.services.fortune_engine import ELEMENT_DIRECTION_MAP

    for elem in lucky_wuxing:
        lucky_colors.extend(ELEMENT_COLOR_MAP.get(elem, [])[:2])
        lucky_materials.extend(ELEMENT_MATERIAL_MAP.get(elem, [])[:2])
        lucky_directions.extend(ELEMENT_DIRECTION_MAP.get(elem, [])[:1])

    lucky_colors = list(dict.fromkeys(lucky_colors))[:5]
    lucky_materials = list(dict.fromkeys(lucky_materials))[:4]
    lucky_directions = list(dict.fromkeys(lucky_directions))[:3]

    # 穿搭建议
    outfit_advice = _generate_year_outfit_advice(
        scores, day_master, year_element, suggested_elements, lucky_colors
    )

    return {
        "year": year,
        "scores": scores,
        "overall_score": overall_score,
        "lucky_colors": lucky_colors,
        "lucky_materials": lucky_materials,
        "lucky_directions": lucky_directions,
        "lucky_elements": lucky_wuxing,
        "outfit_advice": outfit_advice,
        "annual_luck": annual,
    }


def _calculate_year_scores(
    day_master: str,
    year_element: str,
    taishui_element: str,
    suggested_elements: List[str],
    avoid_elements: List[str],
    year: int,
) -> Dict[str, int]:
    """计算年度五维度评分"""
    import random

    # 维度与五行亲和度（复用fortune_engine的定义）
    dimension_affinity = {
        "career": {"金": 1.2, "土": 1.1, "水": 1.0, "火": 0.9, "木": 0.8},
        "wealth": {"金": 1.3, "水": 1.1, "土": 1.0, "火": 0.9, "木": 0.7},
        "love": {"火": 1.3, "木": 1.1, "水": 1.0, "土": 0.9, "金": 0.7},
        "health": {"木": 1.2, "水": 1.1, "土": 1.0, "金": 0.9, "火": 0.8},
        "study": {"水": 1.3, "木": 1.1, "金": 1.0, "土": 0.9, "火": 0.7},
    }

    # 流年五行与日主关系系数
    relation = _get_element_relation_coef(year_element, day_master)
    taishui_relation = _get_element_relation_coef(taishui_element, day_master)

    base_score = 65
    seed_val = hash(f"{day_master}_{year}")
    rng = random.Random(seed_val)

    scores: Dict[str, int] = {}
    for dim, affinity in dimension_affinity.items():
        year_affinity = affinity.get(year_element, 1.0)
        taishui_affinity = affinity.get(taishui_element, 1.0)

        raw = base_score * (year_affinity * relation * 0.65 +
                            taishui_affinity * taishui_relation * 0.35)

        # 喜用神加成
        if year_element in suggested_elements:
            raw += 6
        if taishui_element in suggested_elements:
            raw += 4

        # 忌神减分
        if year_element in avoid_elements:
            raw -= 6
        if taishui_element in avoid_elements:
            raw -= 4

        # 小幅随机波动
        raw += rng.randint(-4, 4)

        scores[dim] = max(0, min(100, int(raw)))

    return scores


def _get_element_relation_coef(elem_a: str, elem_b: str) -> float:
    """获取五行关系系数"""
    if elem_a == elem_b:
        return 1.05
    if WUXING_SHENG.get(elem_a) == elem_b:
        return 1.15
    if WUXING_SHENG.get(elem_b) == elem_a:
        return 0.90
    if WUXING_KE.get(elem_a) == elem_b:
        return 0.85
    if WUXING_KE.get(elem_b) == elem_a:
        return 0.70
    return 1.0


def _generate_year_outfit_advice(
    scores: Dict[str, int],
    day_master: str,
    year_element: str,
    suggested_elements: List[str],
    lucky_colors: List[str],
) -> str:
    """生成年度穿搭建议"""
    dim_names = {
        "career": "事业", "wealth": "财运",
        "love": "桃花", "health": "健康", "study": "学业"
    }

    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best = sorted_dims[0]
    worst = sorted_dims[-1]

    parts: List[str] = []
    parts.append(f"本年度{dim_names[best[0]]}运最旺（{best[1]}分），"
                 f"{dim_names[worst[0]]}运需留意（{worst[1]}分）。")

    if lucky_colors:
        parts.append(f"年度宜穿{'、'.join(lucky_colors[:3])}色系。")

    if suggested_elements:
        parts.append(f"五行上宜选{'、'.join(suggested_elements[:2])}属性穿搭，"
                     f"以增强流年{year_element}运。")

    return "".join(parts)
