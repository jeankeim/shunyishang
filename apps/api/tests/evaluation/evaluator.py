"""
推荐效果评估器

评分体系（满分100分）：
1. 物品多样性 (30分)：品类/五行/颜色/风格分布 + 搭配完整性
2. 物品合理性 (25分)：八字匹配/温度适配/场景适配
3. 推荐理由质量 (15分)：个性化/逻辑性
4. 常识符合度 (15分)：温度常识/季节常识/场景常识
5. 个性化精准度 (15分)：审美匹配/偏好匹配

搭配完整性评估（10分，含在物品多样性维度内）：
- 品类覆盖度 (4分)：推荐结果覆盖的穿着部位数
- 搭配组合有效性 (4分)：是否能组成一套可穿着的穿搭
- 集中度惩罚 (2分)：避免同类物品过度集中
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

from packages.recommendation.config import (
    EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
    EXTREME_COLD_TEMP, MILD_COLD_TEMP,
    SKIN_TONE_COLOR_FIT, BODY_TYPE_FIT, STYLE_KEYWORDS,
    CATEGORY_LIMITS, TEMP_SAFETY_THRESHOLD,
    get_effective_temperature,
)
from packages.recommendation.filters import is_hot_unfit_item
from packages.utils.scene_mapping import is_style_scene_appropriate


# ============================================================
# 评分结果数据结构
# ============================================================

@dataclass
class DimensionScore:
    """单维度评分"""
    name: str
    max_score: float
    actual_score: float
    details: Dict
    
    @property
    def ratio(self) -> float:
        return self.actual_score / self.max_score if self.max_score > 0 else 0


@dataclass
class EvaluationResult:
    """单个测试用例的评估结果"""
    case_id: str
    user_id: int
    complexity: str
    total_score: float
    dimensions: List[DimensionScore]
    recommended_items: List[Dict]
    issues: List[str]


# ============================================================
# 维度1：物品多样性 (30分，含搭配完整性10分)
# ============================================================

def score_diversity(items: List[Dict], top_k: int = 5) -> DimensionScore:
    """
    评估推荐结果的多样性（含搭配完整性）
    
    子项：
    - 品类多样性 (6分)：不同品类的数量
    - 五行多样性 (5分)：不同五行属性的数量
    - 颜色多样性 (3分)：不同颜色的数量
    - 风格多样性 (3分)：不同风格的数量
    - 搭配完整性 (10分)：品类覆盖/搭配组合/集中度
    - 小计：基础多样性17分 + 搭配完整性10分 + 品类补充3分 = 30分
    """
    if not items:
        return DimensionScore("物品多样性", 30, 0, {"error": "无推荐结果"})
    
    # 品类多样性 (6分)
    categories = set(item.get("category", "") for item in items)
    category_count = len(categories)
    # 期望至少3种不同品类（5件推荐中）
    category_score = min(6.0, (category_count / min(3, len(items))) * 6)
    
    # 五行多样性 (5分)
    elements = set(item.get("primary_element", "") for item in items if item.get("primary_element"))
    element_count = len(elements)
    # 期望至少2种不同五行
    element_score = min(5.0, (element_count / 2) * 5)
    
    # 颜色多样性 (3分)
    colors = set(item.get("color", "") for item in items if item.get("color"))
    color_count = len(colors)
    color_score = min(3.0, (color_count / min(3, len(items))) * 3)
    
    # 风格多样性 (3分)
    styles = set(item.get("style", "") for item in items if item.get("style"))
    style_count = len(styles)
    style_score = min(3.0, (style_count / min(2, len(items))) * 3)
    
    # 搭配完整性 (10分)
    outfit_result = score_outfit_completeness(items)
    outfit_score = outfit_result["total"]
    
    # 品类覆盖补充 (3分)：覆盖上/下/外/鞋/饰中越多越好
    coverage_categories = {"上装", "下装", "裙装", "外套", "鞋履", "配饰", "饰品", "文玩"}
    covered = categories & coverage_categories
    coverage_bonus = min(3.0, (len(covered) / min(4, len(coverage_categories))) * 3)
    
    total = category_score + element_score + color_score + style_score + outfit_score + coverage_bonus
    total = min(30.0, total)  # 确保不超上限
    
    return DimensionScore("物品多样性", 30, round(total, 2), {
        "category_count": category_count,
        "category_score": round(category_score, 2),
        "element_count": element_count,
        "element_score": round(element_score, 2),
        "color_count": color_count,
        "color_score": round(color_score, 2),
        "style_count": style_count,
        "style_score": round(style_score, 2),
        "outfit_completeness": outfit_result,
        "coverage_bonus": round(coverage_bonus, 2),
    })


# ============================================================
# 搭配完整性评分 (10分)
# ============================================================

# 有效搭配模式定义
# 每个模式是一组必须包含的品类组合
VALID_OUTFIT_PATTERNS = [
    # 标准搭配：上装 + 下装
    {"required": {"上装", "下装"}, "name": "标准上下装"},
    # 连衣裙搭配：裙装（自带上下）
    {"required": {"裙装"}, "name": "连衣裙"},
    # 上装+裙装搭配
    {"required": {"上装", "裙装"}, "name": "上装+裙装"},
]

# 完整穿搭的加分品类
OUTFIT_ENHANCEMENT_CATEGORIES = {
    "外套": 1.0,   # 外套加分权重
    "鞋履": 1.0,   # 鞋子加分权重
    "配饰": 0.5,   # 配饰加分权重
    "饰品": 0.5,   # 饰品加分权重
    "文玩": 0.3,   # 文玩加分权重
}

# 上装类品类（覆盖上半身）
TOP_CATEGORIES = {"上装", "裙装"}
# 下装类品类（覆盖下半身）
BOTTOM_CATEGORIES = {"下装", "裙装"}


def score_outfit_completeness(items: List[Dict]) -> Dict:
    """
    评估推荐结果的搭配完整性
    
    核心逻辑：
    1. 品类覆盖度 (4分)：推荐结果是否覆盖上半身+下半身+其他部位
    2. 搭配组合有效性 (4分)：是否能组成一套可穿着的穿搭
    3. 集中度惩罚 (2分)：同类物品是否过度集中
    
    Returns:
        {
            "total": 总分(0-10),
            "coverage_score": 品类覆盖度得分,
            "combination_score": 搭配组合得分,
            "concentration_score": 集中度得分,
            "matched_pattern": 匹配的搭配模式,
            "category_distribution": 品类分布,
            "issues": 问题列表,
        }
    """
    if not items:
        return {
            "total": 0, "coverage_score": 0, "combination_score": 0,
            "concentration_score": 0, "matched_pattern": None,
            "category_distribution": {}, "issues": ["无推荐结果"],
        }
    
    issues = []
    
    # 统计品类分布
    category_dist = {}
    for item in items:
        cat = item.get("category", "其他")
        category_dist[cat] = category_dist.get(cat, 0) + 1
    
    categories_present = set(category_dist.keys())
    
    # ========== 1. 品类覆盖度 (4分) ==========
    coverage_score = 0.0
    
    # 检查上半身覆盖
    has_top = bool(categories_present & TOP_CATEGORIES)
    # 检查下半身覆盖
    has_bottom = bool(categories_present & BOTTOM_CATEGORIES)
    # 检查外层覆盖（外套）
    has_outer = "外套" in categories_present
    # 检查足部覆盖（鞋履）
    has_shoes = "鞋履" in categories_present
    # 检查点缀覆盖（配饰/饰品/文玩）
    has_accessory = bool(categories_present & {"配饰", "饰品", "文玩"})
    
    # 基础覆盖：上半身 + 下半身 = 2分
    if has_top:
        coverage_score += 1.0
    else:
        issues.append("缺少上半身衣物（上装/裙装）")
    if has_bottom:
        coverage_score += 1.0
    else:
        issues.append("缺少下半身衣物（下装/裙装）")
    
    # 扩展覆盖：外套/鞋履/点缀 各0.75分，最多2分
    enhancement_count = sum([has_outer, has_shoes, has_accessory])
    coverage_score += min(2.0, enhancement_count * 0.75)
    
    coverage_score = min(4.0, coverage_score)
    
    # ========== 2. 搭配组合有效性 (4分) ==========
    combination_score = 0.0
    matched_pattern = None
    
    # 检查是否匹配有效搭配模式
    for pattern in VALID_OUTFIT_PATTERNS:
        if pattern["required"].issubset(categories_present):
            matched_pattern = pattern["name"]
            combination_score += 2.0  # 基础搭配成立
            break
    
    if not matched_pattern:
        issues.append(f"未匹配有效搭配模式，品类分布: {category_dist}")
    
    # 搭配丰富度加分：有外套+1, 有鞋+1
    if has_outer:
        combination_score += 1.0
    if has_shoes:
        combination_score += 1.0
    
    combination_score = min(4.0, combination_score)
    
    # ========== 3. 集中度惩罚 (2分，满分=无过度集中) ==========
    concentration_score = 2.0
    
    if items:
        max_same_category = max(category_dist.values()) if category_dist else 0
        total_items = len(items)
        
        # 同一品类占比超过60% → 扣分
        if total_items >= 3 and max_same_category / total_items > 0.6:
            concentration_score -= 1.5
            dominant_cat = max(category_dist, key=category_dist.get)
            issues.append(f"品类过度集中: {dominant_cat}占{max_same_category}/{total_items}")
        # 同一品类占比超过40% → 轻微扣分
        elif total_items >= 3 and max_same_category / total_items > 0.4:
            concentration_score -= 0.5
        
        # 如果只有1-2种品类（5件物品），额外扣分
        if len(category_dist) <= 2 and total_items >= 4:
            concentration_score -= 0.5
            issues.append(f"品类种类过少: 仅{len(category_dist)}种")
    
    concentration_score = max(0.0, concentration_score)
    
    total = coverage_score + combination_score + concentration_score
    
    return {
        "total": round(total, 2),
        "coverage_score": round(coverage_score, 2),
        "combination_score": round(combination_score, 2),
        "concentration_score": round(concentration_score, 2),
        "matched_pattern": matched_pattern,
        "category_distribution": category_dist,
        "has_top": has_top,
        "has_bottom": has_bottom,
        "has_outer": has_outer,
        "has_shoes": has_shoes,
        "has_accessory": has_accessory,
        "issues": issues,
    }


# ============================================================
# 维度2：物品合理性 (25分)
# ============================================================

def score_reasonableness(
    items: List[Dict],
    target_elements: List[str],
    weather_info: Optional[Dict],
    scene: Optional[str],
    has_bazi: bool = True,
) -> DimensionScore:
    """
    评估推荐物品的合理性
    
    子项：
    - 八字匹配 (10分)：喜用神命中率
    - 温度适配 (8分)：厚度与温度的匹配
    - 场景适配 (7分)：物品与场景的匹配
    """
    if not items:
        return DimensionScore("物品合理性", 25, 0, {"error": "无推荐结果"})
    
    # 八字匹配 (10分)
    bazi_score = 0.0
    if has_bazi and target_elements:
        hit_count = 0
        for item in items:
            primary = item.get("primary_element", "")
            secondary = item.get("secondary_element", "")
            if primary in target_elements or secondary in target_elements:
                hit_count += 1
        # 3件以上匹配即满分（5件中有3件五行匹配 = 优秀）
        bazi_score = min(10.0, (hit_count / 3.0) * 10)
    else:
        bazi_score = 10.0  # 无八字时不扣分
    
    # 温度适配 (8分)
    temp_score = 8.0
    if weather_info:
        # 有效温度 max(瞬时, 当日最高)，与生产过滤/评分口径一致
        temp = get_effective_temperature(weather_info)
        if temp is not None:
            inappropriate_count = 0
            for item in items:
                thickness = item.get("thickness_level", "")
                if _is_temp_inappropriate(temp, thickness, item):
                    inappropriate_count += 1
            temp_score = max(0, 8.0 - inappropriate_count * 2.0)
    
    # 场景适配 (7分)
    scene_score = 7.0
    if scene:
        mismatch_count = 0
        for item in items:
            if not _is_scene_appropriate(item, scene):
                mismatch_count += 1
        scene_score = max(0, 7.0 - mismatch_count * 1.75)
    
    total = bazi_score + temp_score + scene_score
    
    return DimensionScore("物品合理性", 25, round(total, 2), {
        "bazi_score": round(bazi_score, 2),
        "temp_score": round(temp_score, 2),
        "scene_score": round(scene_score, 2),
    })


def _is_temp_inappropriate(temp: float, thickness: str, item: Optional[Dict] = None) -> bool:
    """判断厚度/袖长是否明显不适合温度（与生产温度硬过滤口径对齐）"""
    if temp >= EXTREME_HOT_TEMP:  # >=30°C
        if thickness in ("厚重", "中厚"):
            return True
        # 名称长袖/保暖类拦截（防晒/冰丝等功能性长袖豁免）
        return bool(item) and is_hot_unfit_item(item, temp)
    elif temp >= HOT_TEMP:  # >=28°C
        if thickness in ("厚重", "中厚"):
            return True
        return bool(item) and is_hot_unfit_item(item, temp)
    elif temp <= EXTREME_COLD_TEMP:  # <=5°C
        return thickness in ("极薄", "轻薄")
    elif temp <= MILD_COLD_TEMP:  # <=10°C
        return thickness == "极薄"
    return False


def _is_scene_appropriate(item: Dict, scene: str) -> bool:
    """判断物品是否适合场景（复用生产 scene_mapping 的风格得体度判定，避免双重标准）"""
    return is_style_scene_appropriate(item, scene)


# ============================================================
# 维度3：推荐理由质量 (15分)
# ============================================================

def score_recommendation_quality(
    items: List[Dict],
    user_info: Dict,
    scene: Optional[str],
) -> DimensionScore:
    """
    评估推荐理由的质量（基于可解释性指标）
    
    子项：
    - 五行解释 (5分)：推荐是否包含五行匹配的物品
    - 个性化解释 (5分)：推荐是否体现用户特征
    - 场景解释 (5分)：推荐是否考虑场景需求
    """
    if not items:
        return DimensionScore("推荐理由质量", 15, 0, {"error": "无推荐结果"})
    
    # 五行解释 (5分)：top物品中有多少匹配喜用神
    target_elements = user_info.get("target_elements", [])
    wuxing_explain_score = 0.0
    if target_elements:
        top_item = items[0] if items else {}
        if (top_item.get("primary_element") in target_elements or
                top_item.get("secondary_element") in target_elements):
            wuxing_explain_score = 5.0
        else:
            # 检查前3个
            for item in items[:3]:
                if (item.get("primary_element") in target_elements or
                        item.get("secondary_element") in target_elements):
                    wuxing_explain_score = 4.0
                    break
    else:
        wuxing_explain_score = 5.0  # 无八字时不要求
    
    # 个性化解释 (5分)：是否体现审美偏好
    personal_score = 3.0  # 基础分
    style_pref = user_info.get("style_preference")
    skin_tone = user_info.get("skin_tone")
    body_type = user_info.get("body_type")
    
    if style_pref:
        for item in items[:3]:
            if item.get("style") == style_pref:
                personal_score = 5.0
                break
            keywords = STYLE_KEYWORDS.get(style_pref, [])
            if any(kw in item.get("name", "") for kw in keywords):
                personal_score = 4.5
                break
    else:
        personal_score = 5.0
    
    # 场景解释 (5分)
    scene_explain_score = 5.0
    if scene:
        scene_items = sum(1 for item in items if _is_scene_appropriate(item, scene))
        # 3.5件以上场景适配即满分（点缀类天然适配不计入扣分）
        scene_explain_score = min(5.0, (scene_items / 3.5) * 5)
    
    total = wuxing_explain_score + personal_score + scene_explain_score
    
    return DimensionScore("推荐理由质量", 15, round(total, 2), {
        "wuxing_explain_score": round(wuxing_explain_score, 2),
        "personal_score": round(personal_score, 2),
        "scene_explain_score": round(scene_explain_score, 2),
    })


# ============================================================
# 维度4：常识符合度 (15分)
# ============================================================

def score_common_sense(
    items: List[Dict],
    weather_info: Optional[Dict],
    season: str,
) -> DimensionScore:
    """
    评估推荐是否符合穿衣常识
    
    子项：
    - 温度常识 (7分)：极端温度下的厚度选择
    - 季节常识 (4分)：物品适用季节
    - 功能常识 (4分)：特殊场景的功能需求
    """
    if not items:
        return DimensionScore("常识符合度", 15, 0, {"error": "无推荐结果"})
    
    # 温度常识 (7分)
    temp_sense_score = 7.0
    violations = []
    if weather_info:
        # 有效温度 max(瞬时, 当日最高)，避免早晨低温掩盖午间高温
        temp = get_effective_temperature(weather_info)
        if temp is not None:
            for item in items:
                thickness = item.get("thickness_level", "")
                violation = _check_temp_violation(temp, thickness, item.get("name", ""), item)
                if violation:
                    violations.append(violation)
                    temp_sense_score -= 1.75
                # temperature_range 超限检查（与生产过滤逻辑对齐）
                range_violation = _check_temp_range_violation(temp, item)
                if range_violation:
                    violations.append(range_violation)
                    temp_sense_score -= 1.75
    temp_sense_score = max(0, temp_sense_score)
    
    # 季节常识 (4分)
    season_sense_score = 4.0
    for item in items:
        applicable = item.get("applicable_seasons", [])
        if applicable and season not in applicable:
            season_sense_score -= 0.8
    season_sense_score = max(0, season_sense_score)
    
    # 功能常识 (4分)
    func_sense_score = 4.0
    # 检查极端温度下是否有功能性衣物
    if weather_info:
        temp = get_effective_temperature(weather_info)
        if temp is None:
            temp = 20
        if temp >= EXTREME_HOT_TEMP:
            # 高温应有透气/速干
            has_func = any(
                "透气" in item.get("functionality", []) or "速干" in item.get("functionality", [])
                for item in items
            )
            if not has_func:
                func_sense_score -= 1.5
        elif temp <= EXTREME_COLD_TEMP:
            # 低温应有保暖
            has_func = any(
                "保暖" in item.get("functionality", [])
                for item in items
            )
            if not has_func:
                func_sense_score -= 1.5
    
    total = temp_sense_score + season_sense_score + func_sense_score
    
    return DimensionScore("常识符合度", 15, round(total, 2), {
        "temp_sense_score": round(temp_sense_score, 2),
        "season_sense_score": round(season_sense_score, 2),
        "func_sense_score": round(func_sense_score, 2),
        "violations": violations,
    })


def _check_temp_violation(temp: float, thickness: str, item_name: str, item: Optional[Dict] = None) -> Optional[str]:
    """检查温度常识违反（与生产温度硬过滤阈值对齐，含高温长袖名称拦截）"""
    if temp >= 30 and thickness == "厚重":
        return f"极热({temp}°C)推荐厚重衣物: {item_name}"
    if temp >= 28 and thickness in ("厚重", "中厚"):
        return f"高温({temp}°C)推荐{thickness}衣物: {item_name}"
    if temp >= 28 and item is not None and is_hot_unfit_item(item, temp):
        return f"高温({temp}°C)推荐长袖/保暖类: {item_name}"
    if temp <= 0 and thickness in ("极薄", "轻薄"):
        return f"严寒({temp}°C)推荐{thickness}衣物: {item_name}"
    if temp <= 5 and thickness == "极薄":
        return f"低温({temp}°C)推荐极薄衣物: {item_name}"
    return None


def _check_temp_range_violation(temp: float, item: Dict) -> Optional[str]:
    """检查物品适用温度范围超限（与生产最高温硬过滤对齐）"""
    temp_range = item.get("temperature_range")
    if not temp_range or not isinstance(temp_range, dict):
        return None
    item_name = item.get("name", "")
    # 最高温超限：当前温度 > 物品最高适用温度 + 8°C
    range_max = temp_range.get("最高") or temp_range.get("max")
    if range_max is not None:
        try:
            if temp > int(range_max) + 8:
                return f"温度超限({temp}°C>最高{range_max}°C+8): {item_name}"
        except (ValueError, TypeError):
            pass
    # 最低温超限：当前温度 < 物品最低适用温度 - 10°C
    range_min = temp_range.get("最低") or temp_range.get("min")
    if range_min is not None:
        try:
            if temp < int(range_min) - 10:
                return f"温度超限({temp}°C<最低{range_min}°C-10): {item_name}"
        except (ValueError, TypeError):
            pass
    return None


# ============================================================
# 维度5：个性化精准度 (15分)
# ============================================================

def score_personalization(
    items: List[Dict],
    user_info: Dict,
) -> DimensionScore:
    """
    评估个性化精准度
    
    子项：
    - 肤色匹配 (5分)：颜色五行与肤色的适配
    - 体型匹配 (5分)：版型与体型的适配
    - 风格匹配 (5分)：物品风格与偏好的匹配
    """
    if not items:
        return DimensionScore("个性化精准度", 15, 0, {"error": "无推荐结果"})
    
    # 肤色匹配 (5分)
    skin_score = 5.0
    skin_tone = user_info.get("skin_tone")
    if skin_tone and skin_tone in SKIN_TONE_COLOR_FIT:
        color_fit = SKIN_TONE_COLOR_FIT[skin_tone]
        match_count = 0
        for item in items:
            elem = item.get("primary_element", "")
            if elem in color_fit and color_fit[elem] >= 0.03:
                match_count += 1
        skin_score = min(5.0, (match_count / max(1, len(items))) * 5 + 2)
    
    # 体型匹配 (5分)
    body_score = 5.0
    body_type = user_info.get("body_type")
    if body_type and body_type in BODY_TYPE_FIT:
        fit_map = BODY_TYPE_FIT[body_type]
        best_fit = max(fit_map.keys(), key=lambda k: fit_map[k])
        match_count = 0
        for item in items:
            detail = item.get("attributes_detail", {})
            if isinstance(detail, dict):
                fit = detail.get("款式", {}).get("版型", "")
                if fit == best_fit:
                    match_count += 1
        # 体型匹配：2件匹配即满分（搭配保障确保至少1件最佳版型）
        body_score = min(5.0, (match_count / 2.0) * 3 + 2)
    
    # 风格匹配 (5分)
    style_score = 5.0
    style_pref = user_info.get("style_preference")
    if style_pref:
        match_count = 0
        for item in items:
            if item.get("style") == style_pref:
                match_count += 1
            else:
                keywords = STYLE_KEYWORDS.get(style_pref, [])
                if any(kw in item.get("name", "") for kw in keywords):
                    match_count += 0.5
        # 2件精确匹配即满分（搭配保障确保至少2件风格匹配）
        style_score = min(5.0, (match_count / 2.0) * 5)
    
    total = skin_score + body_score + style_score
    
    return DimensionScore("个性化精准度", 15, round(total, 2), {
        "skin_score": round(skin_score, 2),
        "body_score": round(body_score, 2),
        "style_score": round(style_score, 2),
    })


# ============================================================
# 综合评估
# ============================================================

def evaluate_single_case(
    case_id: str,
    user_id: int,
    complexity: str,
    recommended_items: List[Dict],
    user_info: Dict,
    weather_info: Optional[Dict],
    scene: Optional[str],
    season: str,
) -> EvaluationResult:
    """
    对单个测试用例进行综合评估
    
    Returns:
        EvaluationResult 包含总分和各维度得分
    """
    issues = []
    
    # 维度1：物品多样性（含搭配完整性）
    dim1 = score_diversity(recommended_items)
    # 收集搭配完整性问题
    outfit_details = dim1.details.get("outfit_completeness", {})
    if outfit_details.get("issues"):
        issues.extend([f"[搭配] {iss}" for iss in outfit_details["issues"]])
    
    # 维度2：物品合理性
    dim2 = score_reasonableness(
        recommended_items,
        user_info.get("target_elements", []),
        weather_info,
        scene,
        has_bazi=bool(user_info.get("target_elements")),
    )
    
    # 维度3：推荐理由质量
    dim3 = score_recommendation_quality(recommended_items, user_info, scene)
    
    # 维度4：常识符合度
    dim4 = score_common_sense(recommended_items, weather_info, season)
    if dim4.details.get("violations"):
        issues.extend(dim4.details["violations"])
    
    # 维度5：个性化精准度
    dim5 = score_personalization(recommended_items, user_info)
    
    dimensions = [dim1, dim2, dim3, dim4, dim5]
    total_score = sum(d.actual_score for d in dimensions)
    
    return EvaluationResult(
        case_id=case_id,
        user_id=user_id,
        complexity=complexity,
        total_score=round(total_score, 2),
        dimensions=dimensions,
        recommended_items=recommended_items,
        issues=issues,
    )


def aggregate_results(results: List[EvaluationResult]) -> Dict:
    """
    汇总所有评估结果
    
    Returns:
        统计报告字典
    """
    if not results:
        return {"error": "无评估结果"}
    
    # 总分统计
    total_scores = [r.total_score for r in results]
    avg_score = sum(total_scores) / len(total_scores)
    
    # 各维度统计
    dimension_stats = {}
    for dim_name in ["物品多样性", "物品合理性", "推荐理由质量", "常识符合度", "个性化精准度"]:
        scores = []
        max_scores = []
        for r in results:
            for d in r.dimensions:
                if d.name == dim_name:
                    scores.append(d.actual_score)
                    max_scores.append(d.max_score)
        if scores:
            dimension_stats[dim_name] = {
                "avg_score": round(sum(scores) / len(scores), 2),
                "max_possible": max_scores[0] if max_scores else 0,
                "avg_ratio": round(sum(scores) / len(scores) / (max_scores[0] if max_scores else 1) * 100, 1),
                "min_score": round(min(scores), 2),
                "max_score": round(max(scores), 2),
            }
    
    # 按复杂度统计
    complexity_stats = {}
    for complexity in ["simple", "medium", "complex", "boundary"]:
        comp_results = [r for r in results if r.complexity == complexity]
        if comp_results:
            comp_scores = [r.total_score for r in comp_results]
            complexity_stats[complexity] = {
                "count": len(comp_results),
                "avg_score": round(sum(comp_scores) / len(comp_scores), 2),
                "min_score": round(min(comp_scores), 2),
                "max_score": round(max(comp_scores), 2),
            }
    
    # 问题统计
    all_issues = []
    for r in results:
        all_issues.extend(r.issues)
    
    # 搭配完整性专项统计
    outfit_stats = _aggregate_outfit_stats(results)
    
    return {
        "total_cases": len(results),
        "avg_total_score": round(avg_score, 2),
        "score_distribution": {
            "excellent_90_100": sum(1 for s in total_scores if s >= 90),
            "good_80_89": sum(1 for s in total_scores if 80 <= s < 90),
            "average_70_79": sum(1 for s in total_scores if 70 <= s < 79),
            "below_70": sum(1 for s in total_scores if s < 70),
        },
        "dimension_stats": dimension_stats,
        "complexity_stats": complexity_stats,
        "outfit_completeness_stats": outfit_stats,
        "total_issues": len(all_issues),
        "sample_issues": all_issues[:10],
    }


def _aggregate_outfit_stats(results: List[EvaluationResult]) -> Dict:
    """
    搭配完整性专项统计
    
    统计：
    - 平均搭配完整性得分
    - 成功匹配搭配模式的比例
    - 各部位覆盖率
    - 集中度问题比例
    """
    outfit_scores = []
    pattern_matched = 0
    has_top_count = 0
    has_bottom_count = 0
    has_outer_count = 0
    has_shoes_count = 0
    has_accessory_count = 0
    concentration_issues = 0
    total = len(results)
    
    for r in results:
        for d in r.dimensions:
            if d.name == "物品多样性":
                outfit_info = d.details.get("outfit_completeness", {})
                outfit_scores.append(outfit_info.get("total", 0))
                if outfit_info.get("matched_pattern"):
                    pattern_matched += 1
                if outfit_info.get("has_top"):
                    has_top_count += 1
                if outfit_info.get("has_bottom"):
                    has_bottom_count += 1
                if outfit_info.get("has_outer"):
                    has_outer_count += 1
                if outfit_info.get("has_shoes"):
                    has_shoes_count += 1
                if outfit_info.get("has_accessory"):
                    has_accessory_count += 1
                if outfit_info.get("concentration_score", 2) < 1.5:
                    concentration_issues += 1
    
    if not outfit_scores:
        return {"error": "无数据"}
    
    avg_outfit_score = sum(outfit_scores) / len(outfit_scores)
    
    return {
        "avg_outfit_score": round(avg_outfit_score, 2),
        "max_possible": 10,
        "avg_ratio": round(avg_outfit_score / 10 * 100, 1),
        "pattern_match_rate": round(pattern_matched / total * 100, 1) if total else 0,
        "coverage_rates": {
            "上半身(上装/裙装)": round(has_top_count / total * 100, 1) if total else 0,
            "下半身(下装/裙装)": round(has_bottom_count / total * 100, 1) if total else 0,
            "外套": round(has_outer_count / total * 100, 1) if total else 0,
            "鞋履": round(has_shoes_count / total * 100, 1) if total else 0,
            "点缀(配饰/饰品/文玩)": round(has_accessory_count / total * 100, 1) if total else 0,
        },
        "concentration_issue_rate": round(concentration_issues / total * 100, 1) if total else 0,
        "total_evaluated": total,
    }
