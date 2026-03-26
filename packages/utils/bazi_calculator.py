"""
八字计算核心模块
使用 cnlunar 库进行四柱排盘，计算五行分布和喜用神
"""

from typing import Dict, List, Optional, TypedDict
from collections import Counter

import cnlunar

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    DIZHI_CANGAN,
    MONTH_SEASON_WUXING,
    XIYONG_RULES,
    KEYWORD_ELEMENT_MAP,
    SCENE_ELEMENT_MAP,
    WUXING_LIST,
)


class BaziResult(TypedDict):
    """八字计算结果"""
    pillars: Dict[str, str]           # 四柱: {year, month, day, hour}
    eight_chars: List[str]            # 八字: 8个字
    five_elements_count: Dict[str, int]  # 五行统计
    dominant_element: str             # 最旺五行
    lacking_element: Optional[str]    # 缺失五行
    day_master: str                   # 日元（日柱天干的五行）
    month_element: str                # 月令五行
    suggested_elements: List[str]     # 喜用神
    avoid_elements: List[str]         # 忌神
    reasoning: str                    # 推理说明


class IntentResult(TypedDict):
    """意图推断结果"""
    elements: List[str]               # 推断的五行
    confidence: float                 # 置信度
    method: str                       # "rule" 或 "llm_needed"
    matched_keywords: List[str]       # 匹配的关键词
    reasoning: str                    # 推理说明


def calculate_bazi(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    gender: str
) -> BaziResult:
    """
    计算八字及喜用神
    
    Args:
        birth_year: 出生年（公历）
        birth_month: 出生月
        birth_day: 出生日
        birth_hour: 出生时（0-23）
        gender: 性别（"男"或"女"）
    
    Returns:
        BaziResult: 八字计算结果
    """
    # 使用 cnlunar 获取农历信息和四柱
    from datetime import datetime
    dt = datetime(birth_year, birth_month, birth_day, birth_hour)
    lunar = cnlunar.Lunar(dt, godType='8char')
    
    # 获取四柱（年柱、月柱、日柱、时柱）
    year_gz = lunar.year8Char  # 年柱干支
    month_gz = lunar.month8Char  # 月柱干支
    day_gz = lunar.day8Char  # 日柱干支
    # 时柱需要根据 twohourNum 从列表中取对应索引
    hour_gz = lunar.twohour8CharList[lunar.twohourNum] if lunar.twohour8CharList else day_gz  # 时柱干支
    
    # 提取八个字
    eight_chars = [
        year_gz[0], year_gz[1],   # 年干、年支
        month_gz[0], month_gz[1], # 月干、月支
        day_gz[0], day_gz[1],     # 日干、日支
        hour_gz[0], hour_gz[1],   # 时干、时支
    ]
    
    # 统计五行分布
    five_elements_count = count_five_elements(eight_chars)
    
    # 确定日元（日柱天干的五行）
    day_master = TIANGAN_WUXING.get(day_gz[0], "土")
    
    # 确定月令五行（月支的五行）
    month_element = DIZHI_WUXING.get(month_gz[1], "土")
    
    # 查找喜用神
    suggested_elements, avoid_elements, reasoning = infer_xiyong(
        day_master, month_element
    )
    
    # 找出最旺和缺失的五行
    dominant_element = max(five_elements_count, key=five_elements_count.get)
    lacking_element = find_lacking_element(five_elements_count)
    
    return BaziResult(
        pillars={
            "year": year_gz,
            "month": month_gz,
            "day": day_gz,
            "hour": hour_gz,
        },
        eight_chars=eight_chars,
        five_elements_count=five_elements_count,
        dominant_element=dominant_element,
        lacking_element=lacking_element,
        day_master=day_master,
        month_element=month_element,
        suggested_elements=suggested_elements,
        avoid_elements=avoid_elements,
        reasoning=reasoning,
    )


def count_five_elements(eight_chars: List[str]) -> Dict[str, int]:
    """
    统计八字中五行的分布
    
    Args:
        eight_chars: 八字（8个字）
    
    Returns:
        Dict[str, int]: 五行统计 {金: x, 木: x, 水: x, 火: x, 土: x}
    """
    count = Counter()
    
    for char in eight_chars:
        # 判断是天干还是地支
        if char in TIANGAN_WUXING:
            count[TIANGAN_WUXING[char]] += 1
        elif char in DIZHI_WUXING:
            # 地支用藏干计算（主气权重1，中气权重0.5，余气权重0.3）
            cangans = DIZHI_CANGAN.get(char, [])
            for i, cangan in enumerate(cangans):
                wuxing = TIANGAN_WUXING.get(cangan, "土")
                if i == 0:  # 主气
                    count[wuxing] += 1
                elif i == 1:  # 中气
                    count[wuxing] += 0.5
                else:  # 余气
                    count[wuxing] += 0.3
    
    # 确保所有五行都有值
    result = {w: int(count.get(w, 0)) for w in WUXING_LIST}
    return result


def find_lacking_element(five_elements_count: Dict[str, int]) -> Optional[str]:
    """
    找出缺失或最弱的五行
    
    Args:
        five_elements_count: 五行统计
    
    Returns:
        Optional[str]: 缺失或最弱的五行，如果都有则返回 None
    """
    min_count = min(five_elements_count.values())
    if min_count == 0:
        for wuxing, count in five_elements_count.items():
            if count == 0:
                return wuxing
    return None


def infer_xiyong(
    day_master: str,
    month_element: str
) -> tuple[List[str], List[str], str]:
    """
    推断喜用神（增强版）
    
    优先使用规则表，无匹配时按五行旺衰原则推断
    
    Args:
        day_master: 日元五行
        month_element: 月令五行
        
    Returns:
        tuple: (喜用神列表, 忌神列表, 推理说明)
    """
    key = (day_master, month_element)
    
    # 优先使用规则表（已完整覆盖25种组合）
    if key in XIYONG_RULES:
        return XIYONG_RULES[key]
    
    # 增强的默认逻辑：考虑五行旺衰
    from packages.utils.wuxing_rules import WUXING_KE, WUXING_SHENG, WUXING_BEI_SHENG, WUXING_BEI_KE
    
    reasoning = f"日元{day_master}，生于{month_element}月，按五行平衡原则推断。"
    
    # 判断日元旺衰
    # 月令生扶日元 → 日元旺 → 喜克泄耗
    # 月令克泄日元 → 日元弱 → 喜生扶
    
    # 月令生日元（日元得生，偏旺）
    if day_master == WUXING_SHENG.get(month_element):
        # 日元得生，偏旺，喜克泄
        suggested = [WUXING_KE.get(day_master, "木"), WUXING_SHENG.get(day_master, "火")]
        avoid = [month_element, day_master]
        reasoning += f"{month_element}生{day_master}，日元偏旺，喜{WUXING_KE.get(day_master, '木')}克、{WUXING_SHENG.get(day_master, '火')}泄。"
    
    # 月令克日元（日元受克，偏弱）
    elif month_element == WUXING_KE.get(day_master):
        # 日元受克，偏弱，喜生扶
        suggested = [WUXING_BEI_SHENG.get(day_master, "土"), day_master]
        avoid = [month_element, WUXING_KE.get(day_master, "木")]
        reasoning += f"{month_element}克{day_master}，日元偏弱，喜{WUXING_BEI_SHENG.get(day_master, '土')}生、{day_master}助。"
    
    # 月令被日元所生（日元泄气，偏弱）
    elif month_element == WUXING_SHENG.get(day_master):
        # 日元泄气，偏弱，喜生扶
        suggested = [WUXING_BEI_SHENG.get(day_master, "土"), day_master]
        avoid = [month_element, WUXING_KE.get(day_master, "木")]
        reasoning += f"{day_master}生{month_element}，日元泄气，喜{WUXING_BEI_SHENG.get(day_master, '土')}生、{day_master}助。"
    
    # 月令被日元所克（日元耗气，中等）
    elif month_element == WUXING_BEI_KE.get(day_master):
        # 日元耗气，中等，喜生扶
        suggested = [WUXING_BEI_SHENG.get(day_master, "土"), day_master]
        avoid = [WUXING_KE.get(day_master, "木")]
        reasoning += f"{day_master}克{month_element}，日元耗气，喜{WUXING_BEI_SHENG.get(day_master, '土')}生扶。"
    
    else:
        # 默认：中和原则
        suggested = [day_master, WUXING_BEI_SHENG.get(day_master, "土")]
        avoid = [WUXING_KE.get(day_master, "木")]
        reasoning += "按中和原则推断。"
    
    return suggested, avoid, reasoning


def infer_elements_from_text(text: str) -> IntentResult:
    """
    从文本推断五行意图（规则优先）
    
    Args:
        text: 用户输入文本
    
    Returns:
        IntentResult: 意图推断结果
    """
    matched = []
    element_scores = {w: 0 for w in WUXING_LIST}
    
    # 遍历关键词映射表
    for element, keywords in KEYWORD_ELEMENT_MAP.items():
        for keyword in keywords:
            if keyword in text:
                matched.append(f"{keyword}→{element}")
                element_scores[element] += 1
    
    # 检查是否命中场景
    for scene, info in SCENE_ELEMENT_MAP.items():
        if scene in text:
            for elem in info["primary"]:
                element_scores[elem] += 2
                matched.append(f"{scene}→{elem}(场景)")
    
    # 统计结果
    total_matches = sum(element_scores.values())
    
    if total_matches == 0:
        return IntentResult(
            elements=[],
            confidence=0.0,
            method="llm_needed",
            matched_keywords=[],
            reasoning="未匹配到关键词，需要 LLM 兜底"
        )
    
    # 按分数排序，取前2个
    sorted_elements = sorted(
        element_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    top_elements = [e for e, s in sorted_elements if s > 0][:2]
    
    confidence = min(total_matches / 5.0, 1.0)  # 归一化置信度
    
    return IntentResult(
        elements=top_elements,
        confidence=confidence,
        method="rule",
        matched_keywords=matched,
        reasoning=f"关键词匹配: {', '.join(matched[:5])}"
    )


def merge_recommendations(
    bazi_result: Optional[BaziResult],
    intent_result: Optional[IntentResult],
    scene_result: Optional[Dict],
    weather_element: Optional[str] = None
) -> List[str]:
    """
    合并多层推荐结果
    
    优先级：八字喜用神 > 天气 > 场景 > 意图
    
    Args:
        bazi_result: 八字计算结果
        intent_result: 意图推断结果
        scene_result: 场景映射结果
        weather_element: 天气对应的五行
    
    Returns:
        List[str]: 最终推荐五行列表（去重，最多3个）
    """
    elements = []
    
    # 1. 八字喜用神（最高优先级）
    if bazi_result:
        elements.extend(bazi_result["suggested_elements"])
    
    # 2. 天气五行（次优先级，不与喜用神冲突）
    if weather_element and weather_element not in elements:
        if bazi_result and weather_element in bazi_result.get("avoid_elements", []):
            pass  # 天气五行与忌神冲突，跳过
        else:
            elements.append(weather_element)
    
    # 3. 场景五行（不与喜用神/天气冲突时叠加）
    if scene_result:
        for elem in scene_result.get("primary", []):
            if elem not in elements:
                # 检查是否与忌神冲突
                if bazi_result and elem in bazi_result.get("avoid_elements", []):
                    continue
                elements.append(elem)
    
    # 4. 意图推断（补充）
    if intent_result and intent_result["method"] == "rule":
        for elem in intent_result["elements"]:
            if elem not in elements:
                elements.append(elem)
    
    # 去重，最多3个
    return list(dict.fromkeys(elements))[:3]
