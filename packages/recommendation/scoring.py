"""
推荐评分引擎

所有评分函数均为纯函数（输入 item + context，输出 float），便于单元测试。
包含：五行评分、温度评分、季节评分、审美加分（肤色/风格/体型）、轮换奖励。
"""

import json
import logging
from typing import Dict, List, Optional

from packages.recommendation.config import (
    EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
    EXTREME_COLD_TEMP, MILD_COLD_TEMP,
    WUXING_PRIMARY_SCORE, WUXING_SECONDARY_SCORE,
    WUXING_BOOST_PRIMARY, WUXING_BOOST_SECONDARY, WUXING_BOOST_MIN_CAP,
    ORNAMENT_BONUS, ORNAMENT_CATEGORIES,
    ROTATION_MAX_BONUS, ROTATION_DECAY_PER_WEAR,
    SKIN_TONE_COLOR_FIT, SKIN_TONE_MAX_BONUS,
    STYLE_KEYWORDS, STYLE_NAME_BONUS, STYLE_DETAIL_BONUS, STYLE_FIELD_BONUS, STYLE_MAX_BONUS,
    BODY_TYPE_FIT, BODY_TYPE_MAX_BONUS,
    SEASON_MATCH_SCORE, SEASON_MISMATCH_SCORE, SEASON_UNKNOWN_SCORE,
)

logger = logging.getLogger(__name__)


# ============================================================
# 五行评分
# ============================================================

def calculate_wuxing_score(
    item: Dict,
    target_elements: List[str],
    boost_elements: Optional[List[str]] = None,
) -> float:
    """
    计算物品五行匹配分（归一化到 [0, 1.0]）

    评分规则：
    - primary_element 命中 target: +0.6
    - secondary_element 命中 target: +0.3
    - boost 元素（相生辅助）: +0.08/+0.04，但 cap 不超过 base 命中分
    - 最终 min(1.0, score) 确保不超 1

    Args:
        item: 物品字典（含 primary_element, secondary_element）
        target_elements: 目标五行列表
        boost_elements: 相生辅助五行列表（忌神但生喜用神）

    Returns:
        [0.0, 1.0] 之间的五行匹配分
    """
    if not target_elements:
        return 0.0

    primary = item.get("primary_element", "")
    secondary = item.get("secondary_element") or ""

    score = 0.0
    base_target_score = 0.0

    if primary in target_elements:
        score += WUXING_PRIMARY_SCORE
        base_target_score += WUXING_PRIMARY_SCORE
    if secondary and secondary in target_elements:
        score += WUXING_SECONDARY_SCORE
        base_target_score += WUXING_SECONDARY_SCORE

    # 相生加分（P2-62 上限约束：不超过 base 命中分）
    if boost_elements:
        boost_raw = 0.0
        if primary in boost_elements:
            boost_raw += WUXING_BOOST_PRIMARY
        if secondary and secondary in boost_elements:
            boost_raw += WUXING_BOOST_SECONDARY
        boost_capped = min(boost_raw, max(base_target_score, WUXING_BOOST_MIN_CAP))
        score += boost_capped

    return min(1.0, score)


def calculate_ornament_bonus(item: Dict, target_elements: List[str]) -> float:
    """
    饰品/文玩五行补救加分

    当物品属于饰品/文玩类别且五行命中 target 时，给予小幅加分。
    """
    category = item.get("category", "")
    primary = item.get("primary_element", "")
    if category in ORNAMENT_CATEGORIES and primary in target_elements:
        return ORNAMENT_BONUS
    return 0.0


# ============================================================
# 温度评分
# ============================================================

def infer_item_thickness(item: Dict) -> str:
    """
    统一推断物品厚度

    优先级：名称暗示厚重 > DB thickness_level > 名称暗示中厚/轻薄 > 空串
    解决硬过滤与温度评分依据不同源的割裂问题。
    """
    item_name = item.get("name", "")
    db_thickness = item.get("thickness_level", "") or ""

    heavy_keywords = ["羽绒", "棉袄", "棉衣", "大衣", "毛呢", "羊毛大衣", "皮草"]
    if any(k in item_name for k in heavy_keywords):
        return "厚重"

    if db_thickness:
        return db_thickness

    medium_keywords = ["毛衣", "卫衣", "针织", "西装", "风衣", "夹克", "外套"]
    if any(k in item_name for k in medium_keywords):
        return "中厚"

    thin_keywords = ["衬衫", "T恤", "Polo", "polo", "短裤", "薄", "背心", "吊带", "雪纺", "丝"]
    if any(k in item_name for k in thin_keywords):
        return "轻薄"

    return ""


def calculate_temp_score(item: Dict, weather_info: Optional[Dict]) -> float:
    """
    计算物品温度适配分（0.0-1.0）

    同时考虑 thickness_level 和 temperature_range（物品适用温度范围）。
    6档温度分层与 config 中的阈值常量完全对齐。
    """
    if not weather_info:
        return 0.5

    temp = weather_info.get("temperature")
    if temp is None:
        return 0.5

    score = 0.5
    thickness = infer_item_thickness(item)
    functionality = item.get("functionality", [])
    if isinstance(functionality, str):
        try:
            functionality = json.loads(functionality)
        except Exception:
            functionality = []
    if not isinstance(functionality, list):
        functionality = []

    # temperature_range 检查
    temp_range = item.get("temperature_range")
    if temp_range and isinstance(temp_range, dict):
        range_min = temp_range.get("最低") or temp_range.get("min")
        range_max = temp_range.get("最高") or temp_range.get("max")
        if range_min is not None:
            try:
                range_min = int(range_min)
                if temp < range_min:
                    deficit = range_min - temp
                    score -= min(0.4, deficit * 0.05)
            except (ValueError, TypeError):
                pass
        if range_max is not None:
            try:
                range_max = int(range_max)
                if temp > range_max + 5:
                    score -= 0.15
            except (ValueError, TypeError):
                pass

    # 6档温度评分
    if temp >= EXTREME_HOT_TEMP:
        if thickness in ("极薄", "轻薄"):
            score += 0.3
        elif thickness == "适中":
            score += 0.1
        elif thickness in ("中厚", "厚重"):
            score -= 0.3
        if any(f in functionality for f in ["透气", "速干", "防晒"]):
            score += 0.2
    elif temp >= HOT_TEMP:
        if thickness in ("极薄", "轻薄"):
            score += 0.3
        elif thickness == "适中":
            score += 0.1
        elif thickness in ("中厚", "厚重"):
            score -= 0.3
        if any(f in functionality for f in ["透气", "速干"]):
            score += 0.2
    elif temp >= MILD_HOT_TEMP:
        if thickness in ("极薄", "轻薄"):
            score += 0.2
        elif thickness == "适中":
            score += 0.1
        elif thickness == "厚重":
            score -= 0.2
    elif temp <= EXTREME_COLD_TEMP:
        if thickness in ("厚重", "中厚"):
            score += 0.3
        elif thickness == "适中":
            score += 0.1
        elif thickness in ("极薄", "轻薄"):
            score -= 0.3
        if any(f in functionality for f in ["保暖", "防风"]):
            score += 0.2
    elif temp <= MILD_COLD_TEMP:
        if thickness in ("厚重", "中厚"):
            score += 0.2
        elif thickness == "适中":
            score += 0.1
        elif thickness == "极薄":
            score -= 0.2
    else:
        # 适中温度（11-24°C）
        if temp >= 20:
            if thickness == "适中":
                score += 0.2
            elif thickness in ("轻薄", "极薄"):
                score += 0.1
            elif thickness == "厚重":
                score -= 0.3
            elif thickness == "中厚":
                score -= 0.1
        else:
            if thickness == "适中":
                score += 0.2
            elif thickness == "中厚":
                score += 0.1

    return max(0.0, min(1.0, score))


# ============================================================
# 季节评分
# ============================================================

def get_current_season() -> Optional[str]:
    """推断当前季节（基于月份）"""
    from datetime import datetime
    month = datetime.now().month
    if month in (3, 4, 5):
        return "春"
    elif month in (6, 7, 8):
        return "夏"
    elif month in (9, 10, 11):
        return "秋"
    else:
        return "冬"


def calculate_season_score(item: Dict, current_season: Optional[str]) -> float:
    """
    计算物品季节适配分

    Returns:
        1.0 = 完全适配 / 0.7 = 不适配 / 0.5 = 无季节信息
    """
    if not current_season:
        return SEASON_UNKNOWN_SCORE

    applicable_seasons = item.get("applicable_seasons")
    if not applicable_seasons:
        return SEASON_UNKNOWN_SCORE

    if isinstance(applicable_seasons, str):
        try:
            applicable_seasons = json.loads(applicable_seasons)
        except Exception:
            return SEASON_UNKNOWN_SCORE

    if not isinstance(applicable_seasons, list) or len(applicable_seasons) == 0:
        return SEASON_UNKNOWN_SCORE

    if current_season in applicable_seasons:
        return SEASON_MATCH_SCORE

    return SEASON_MISMATCH_SCORE


# ============================================================
# 审美画像加分
# ============================================================

def calculate_skin_tone_bonus(item: Dict, skin_tone: Optional[str]) -> float:
    """
    计算肤色适配加分（0.0 ~ SKIN_TONE_MAX_BONUS）
    """
    if not skin_tone:
        return 0.0

    color_fit = SKIN_TONE_COLOR_FIT.get(skin_tone)
    if not color_fit:
        return 0.0

    primary = item.get("primary_element", "")
    secondary = item.get("secondary_element") or ""

    bonus = color_fit.get(primary, 0.0)
    if secondary:
        bonus += color_fit.get(secondary, 0.0) * 0.5

    return min(SKIN_TONE_MAX_BONUS, bonus)


def calculate_style_preference_bonus(item: Dict, style_preference: Optional[str]) -> float:
    """
    计算风格偏好加分（0.0 ~ STYLE_MAX_BONUS）

    加分策略：
    - style 字段精确匹配: +STYLE_FIELD_BONUS (0.15)
    - 名称关键词匹配: +STYLE_NAME_BONUS (0.10)
    - 属性详情匹配: +STYLE_DETAIL_BONUS (0.10)
    - 上限: STYLE_MAX_BONUS (0.25)
    """
    if not style_preference:
        return 0.0

    bonus = 0.0

    # 1. style 字段精确匹配（最高优先级）
    if item.get("style") == style_preference:
        bonus += STYLE_FIELD_BONUS

    # 2. 名称关键词匹配
    keywords = STYLE_KEYWORDS.get(style_preference, [])
    if keywords:
        item_name = item.get("name", "")
        for kw in keywords:
            if kw in item_name:
                bonus += STYLE_NAME_BONUS
                break

    # 3. 属性详情匹配
    detail = item.get("attributes_detail") or {}
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            detail = {}
    if isinstance(detail, dict):
        style_info = detail.get("款式", {})
        if isinstance(style_info, dict):
            style_text = style_info.get("风格", "")
            if keywords:
                for kw in keywords:
                    if kw in style_text:
                        bonus += STYLE_DETAIL_BONUS
                        break

    return min(STYLE_MAX_BONUS, bonus)


def calculate_body_type_bonus(item: Dict, body_type: Optional[str]) -> float:
    """
    计算体型适配加分（0.0 ~ BODY_TYPE_MAX_BONUS）
    """
    if not body_type:
        return 0.0

    fit_map = BODY_TYPE_FIT.get(body_type)
    if not fit_map:
        return 0.0

    # 从属性推断版型
    detail = item.get("attributes_detail") or {}
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            detail = {}

    fit_type = ""
    if isinstance(detail, dict):
        style_info = detail.get("款式", {})
        if isinstance(style_info, dict):
            fit_type = style_info.get("版型", "")
            if not fit_type and style_info.get("细节"):
                details = style_info.get("细节")
                if isinstance(details, list) and details:
                    fit_type = details[0]

    # 从名称推断
    item_name = item.get("name", "")
    if not fit_type:
        if any(k in item_name for k in ["修身", "紧身"]):
            fit_type = "修身"
        elif any(k in item_name for k in ["宽松", "oversize", "廓形"]):
            fit_type = "宽松"
        elif any(k in item_name for k in ["常规", "标准"]):
            fit_type = "适中"

    if fit_type:
        return fit_map.get(fit_type, 0.0)
    return 0.0


# ============================================================
# 轮换奖励
# ============================================================

def calculate_rotation_bonus(item: Dict) -> float:
    """
    计算衣物轮换奖励（独立于五行分的微调项）

    穿着次数少的自有衣物给予小幅加分鼓励轮换。
    公共库物品无 wear_count，返回 0。
    """
    wear_count = item.get("wear_count")
    if wear_count is None or not isinstance(wear_count, (int, float)) or wear_count < 0:
        return 0.0
    return max(0.0, ROTATION_MAX_BONUS - wear_count * ROTATION_DECAY_PER_WEAR)


# ============================================================
# 综合评分
# ============================================================

def calculate_final_score(
    item: Dict,
    weights: Dict[str, float],
    target_elements: List[str],
    boost_elements: Optional[List[str]] = None,
    weather_info: Optional[Dict] = None,
    current_season: Optional[str] = None,
    scene: Optional[str] = None,
    sub_scene: Optional[str] = None,
    scene_weight: float = 0.0,
    user_prefs: Optional[Dict] = None,
    pref_weight: float = 0.0,
    skin_tone: Optional[str] = None,
    style_preference: Optional[str] = None,
    body_type: Optional[str] = None,
    behavior_score: float = 0.0,
) -> Dict[str, float]:
    """
    计算物品的综合推荐分数

    各维度均为 [0,1]，加权和为 [0,1]。
    轮换奖励和审美加分作为独立微调项叠加。
    季节分作为乘性因子（0.7~1.0）。

    Returns:
        包含各维度分数和 final_score 的字典
    """
    from packages.utils.scene_mapping import calculate_scene_match_score

    semantic_score = item.get("semantic_score", 0.5)

    # 五行分
    wuxing_score = calculate_wuxing_score(item, target_elements, boost_elements)

    # 温度分
    temp_score = calculate_temp_score(item, weather_info)

    # 季节分（乘性因子）
    season_score = calculate_season_score(item, current_season)

    # 场景分
    scene_score = 0.5
    if scene and scene_weight > 0:
        scene_score = calculate_scene_match_score(item, scene, sub_scene)

    # 偏好分
    preference_score = 0.5
    if user_prefs and pref_weight > 0:
        try:
            from apps.api.services.preference_service import preference_service
            preference_score = preference_service.calculate_preference_score(item, user_prefs)
        except Exception:
            preference_score = 0.5

    # 加权求和
    final_score = (
        semantic_score * weights.get("semantic", 0.5) +
        wuxing_score * weights.get("wuxing", 0.3) +
        scene_score * weights.get("scene", 0.0) +
        preference_score * weights.get("pref", 0.0) +
        temp_score * weights.get("temp", 0.0)
    ) * season_score

    # 独立微调项
    rotation_bonus = calculate_rotation_bonus(item)
    final_score += rotation_bonus

    # 饰品五行补救
    final_score += calculate_ornament_bonus(item, target_elements)

    # 审美画像加分
    final_score += calculate_skin_tone_bonus(item, skin_tone)
    final_score += calculate_style_preference_bonus(item, style_preference)
    final_score += calculate_body_type_bonus(item, body_type)

    # 行为反馈加分
    final_score += behavior_score

    return {
        "semantic_score": semantic_score,
        "wuxing_score": wuxing_score,
        "scene_score": scene_score,
        "preference_score": preference_score,
        "temp_score": temp_score,
        "season_score": season_score,
        "final_score": final_score,
    }
