"""
十神关系解读系统
比肩/劫财/食神/伤官/偏财/正财/七杀/正官/偏印/正印

十神计算规则：
- 同我（同五行）：同阴阳=比肩，异阴阳=劫财
- 我生（我生之五行）：同阴阳=食神，异阴阳=伤官
- 我克（我克之五行）：同阴阳=偏财，异阴阳=正财
- 克我（克我之五行）：同阴阳=七杀，异阴阳=正官
- 生我（生我之五行）：同阴阳=偏印，异阴阳=正印
"""

import logging
from collections import Counter
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
)

logger = logging.getLogger(__name__)

# 天干阴阳属性
TIANGAN_YINYANG: Dict[str, str] = {
    "甲": "阳", "丙": "阳", "戊": "阳", "庚": "阳", "壬": "阳",
    "乙": "阴", "丁": "阴", "己": "阴", "辛": "阴", "癸": "阴",
}

# 天干列表
TIANGAN_LIST: List[str] = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

# ============================================================
# 十神定义
# ============================================================

TEN_GODS: Dict[str, Dict[str, Any]] = {
    "比肩": {
        "element_relation": "同我",
        "description": "独立自主，竞争合作",
        "style_keywords": ["简约", "干练", "中性"],
    },
    "劫财": {
        "element_relation": "同我",
        "description": "行动力强，宜稳健理财",
        "style_keywords": ["活力", "运动", "明快"],
    },
    "食神": {
        "element_relation": "我生",
        "description": "才华横溢，福禄之兆",
        "style_keywords": ["优雅", "文艺", "柔和"],
    },
    "伤官": {
        "element_relation": "我生",
        "description": "聪明叛逆，创新之兆",
        "style_keywords": ["个性", "时尚", "前卫"],
    },
    "偏财": {
        "element_relation": "我克",
        "description": "意外之财，投资之兆",
        "style_keywords": ["奢华", "高端", "精致"],
    },
    "正财": {
        "element_relation": "我克",
        "description": "正当收入，稳定之兆",
        "style_keywords": ["稳重", "正式", "经典"],
    },
    "七杀": {
        "element_relation": "克我",
        "description": "权威压力，挑战之兆",
        "style_keywords": ["强势", "硬朗", "深色"],
    },
    "正官": {
        "element_relation": "克我",
        "description": "事业地位，名声之兆",
        "style_keywords": ["正式", "得体", "端庄"],
    },
    "偏印": {
        "element_relation": "生我",
        "description": "学习深造，偏门之兆",
        "style_keywords": ["知性", "独特", "深沉"],
    },
    "正印": {
        "element_relation": "生我",
        "description": "贵人相助，学业之兆",
        "style_keywords": ["温和", "典雅", "柔和"],
    },
}

# 十神对应五行（用于穿搭颜色推导）
TEN_GOD_ELEMENT: Dict[str, str] = {
    "比肩": "木",  # 与日主同，用木作为通用代表
    "劫财": "木",
    "食神": "火",  # 我生
    "伤官": "火",
    "偏财": "土",  # 我克
    "正财": "土",
    "七杀": "金",  # 克我
    "正官": "金",
    "偏印": "水",  # 生我
    "正印": "水",
}

# 十神风格颜色映射
TEN_GOD_COLOR_MAP: Dict[str, List[str]] = {
    "比肩": ["白色", "灰色", "米白", "浅蓝"],
    "劫财": ["橙色", "红色", "明黄", "珊瑚"],
    "食神": ["绿色", "薄荷", "浅绿", "乳白"],
    "伤官": ["紫色", "黑色", "玫红", "深蓝"],
    "偏财": ["金色", "香槟", "银色", "白色"],
    "正财": ["棕色", "卡其", "驼色", "米色"],
    "七杀": ["黑色", "深灰", "藏青", "酒红"],
    "正官": ["藏青", "深蓝", "黑色", "白色"],
    "偏印": ["深紫", "墨绿", "深蓝", "深灰"],
    "正印": ["浅粉", "米白", "浅蓝", "薄荷"],
}

# 十神风格材质映射
TEN_GOD_MATERIAL_MAP: Dict[str, List[str]] = {
    "比肩": ["棉麻", "亚麻", "棉", "针织"],
    "劫财": ["运动面料", "棉", "网眼", "弹力"],
    "食神": ["真丝", "丝绸", "雪纺", "蕾丝"],
    "伤官": ["皮革", "亮片", "金属", "缎面"],
    "偏财": ["缎面", "天鹅绒", "丝绸", "皮草"],
    "正财": ["羊毛", "呢料", "棉", "羊绒"],
    "七杀": ["皮革", "牛仔", "金属", "粗纺"],
    "正官": ["西装面料", "呢料", "丝绸", "棉"],
    "偏印": ["天鹅绒", "丝绒", "针织", "羊毛"],
    "正印": ["棉", "丝绸", "针织", "雪纺"],
}


# ============================================================
# 十神计算
# ============================================================

def calculate_ten_gods(day_master_stem: str, other_stem: str) -> Dict[str, Any]:
    """
    计算日主天干与其他天干的十神关系

    Args:
        day_master_stem: 日主天干（如 "甲"）
        other_stem: 其他天干（如 "丙"）

    Returns:
        {ten_god, element_relation, description, style_keywords}
    """
    dm_element = TIANGAN_WUXING.get(day_master_stem, "土")
    other_element = TIANGAN_WUXING.get(other_stem, "土")
    dm_yinyang = TIANGAN_YINYANG.get(day_master_stem, "阳")
    other_yinyang = TIANGAN_YINYANG.get(other_stem, "阳")

    same_polarity = (dm_yinyang == other_yinyang)
    ten_god_name = _determine_ten_god(dm_element, other_element, same_polarity)

    info = TEN_GODS.get(ten_god_name, TEN_GODS["比肩"])
    return {
        "ten_god": ten_god_name,
        "element_relation": info["element_relation"],
        "description": info["description"],
        "style_keywords": info["style_keywords"],
        "day_master_stem": day_master_stem,
        "other_stem": other_stem,
        "day_master_element": dm_element,
        "other_element": other_element,
        "same_polarity": same_polarity,
    }


def _determine_ten_god(
    dm_element: str,
    other_element: str,
    same_polarity: bool,
) -> str:
    """
    根据五行关系和阴阳同异确定十神名称

    Args:
        dm_element: 日主五行
        other_element: 其他天干五行
        same_polarity: 是否同阴阳

    Returns:
        十神名称
    """
    # 同我（同五行）
    if dm_element == other_element:
        return "比肩" if same_polarity else "劫财"

    # 我生
    if WUXING_SHENG.get(dm_element) == other_element:
        return "食神" if same_polarity else "伤官"

    # 我克
    if WUXING_KE.get(dm_element) == other_element:
        return "偏财" if same_polarity else "正财"

    # 克我
    if WUXING_KE.get(other_element) == dm_element:
        return "七杀" if same_polarity else "正官"

    # 生我
    if WUXING_SHENG.get(other_element) == dm_element:
        return "偏印" if same_polarity else "正印"

    return "比肩"


# ============================================================
# 八字十神格局分析
# ============================================================

def analyze_ten_gods_chart(bazi_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析八字十神格局

    计算年柱/月柱/日柱/时柱的十神，分析十神旺衰

    Args:
        bazi_result: 八字计算结果（含pillars, eight_chars等）

    Returns:
        {pillars: {year: {stem, ten_god}, ...},
         dominant_gods: [],
         weak_gods: [],
         analysis: str}
    """
    pillars = bazi_result.get("pillars", {})
    eight_chars = bazi_result.get("eight_chars", [])

    # 日主天干（日柱天干）
    day_gz = pillars.get("day", "甲子")
    day_master_stem = day_gz[0]

    # 计算四柱天干的十神
    pillar_gods: Dict[str, Dict[str, Any]] = {}
    god_counter: Counter = Counter()

    for pillar_name in ["year", "month", "day", "hour"]:
        gz = pillars.get(pillar_name, "甲子")
        # 时辰未知时时柱为"未知"，无法计算十神，直接标记跳过
        if gz and gz[0] not in TIANGAN_WUXING:
            pillar_gods[pillar_name] = {
                "stem": None,
                "ganzhi": gz,
                "ten_god": "未知",
            }
            continue
        stem = gz[0]
        if pillar_name == "day":
            ten_god = "日主"
        else:
            result = calculate_ten_gods(day_master_stem, stem)
            ten_god = result["ten_god"]
            god_counter[ten_god] += 1
        pillar_gods[pillar_name] = {
            "stem": stem,
            "ganzhi": gz,
            "ten_god": ten_god,
        }

    # 分析地支藏干的十神
    from packages.utils.wuxing_rules import DIZHI_CANGAN
    hidden_gods: List[Dict[str, Any]] = []
    for pillar_name in ["year", "month", "day", "hour"]:
        gz = pillars.get(pillar_name, "甲子")
        branch = gz[1]
        cangans = DIZHI_CANGAN.get(branch, [])
        for cg in cangans:
            result = calculate_ten_gods(day_master_stem, cg)
            hidden_gods.append({
                "pillar": pillar_name,
                "hidden_stem": cg,
                "ten_god": result["ten_god"],
            })
            god_counter[result["ten_god"]] += 0.5

    # 旺神和衰神
    sorted_gods = god_counter.most_common()
    dominant_gods = [g[0] for g in sorted_gods if g[1] >= 1.5][:3]
    weak_gods = [g[0] for g in sorted_gods if g[1] < 0.5][:3]

    # 生成分析文字
    analysis = _generate_chart_analysis(pillar_gods, dominant_gods, weak_gods, god_counter)

    return {
        "pillars": pillar_gods,
        "hidden_gods": hidden_gods,
        "dominant_gods": dominant_gods,
        "weak_gods": weak_gods,
        "god_distribution": dict(god_counter),
        "analysis": analysis,
    }


def _generate_chart_analysis(
    pillar_gods: Dict[str, Dict[str, Any]],
    dominant_gods: List[str],
    weak_gods: List[str],
    god_counter: Counter,
) -> str:
    """生成十神格局分析文字"""
    parts: List[str] = []

    # 四柱十神概述
    for name, info in pillar_gods.items():
        pillar_names = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
        if info["ten_god"] == "日主":
            parts.append(f"{pillar_names[name]}为日主{info['stem']}，")
        else:
            parts.append(f"{pillar_names[name]}天干{info['stem']}为{info['ten_god']}，")

    # 旺神分析
    if dominant_gods:
        dom_descs = []
        for g in dominant_gods:
            desc = TEN_GODS.get(g, {}).get("description", "")
            dom_descs.append(f"{g}（{desc}）")
        parts.append(f"命中以{'、'.join(dom_descs)}为主，性格倾向明显。")

    # 衰神分析
    if weak_gods:
        parts.append(f"{'、'.join(weak_gods)}较弱，相关方面需注意补充。")

    # 整体格局
    if "正官" in dominant_gods or "七杀" in dominant_gods:
        parts.append("官杀旺，事业心强，适合管理或技术路线。")
    if "正财" in dominant_gods or "偏财" in dominant_gods:
        parts.append("财星旺，重视物质，理财能力强。")
    if "食神" in dominant_gods or "伤官" in dominant_gods:
        parts.append("食伤旺，才华出众，适合创意或表达类工作。")
    if "正印" in dominant_gods or "偏印" in dominant_gods:
        parts.append("印星旺，学习力强，适合学术或研究。")
    if "比肩" in dominant_gods or "劫财" in dominant_gods:
        parts.append("比劫旺，独立自主，竞争意识强。")

    return "".join(parts)


# ============================================================
# 穿搭风格建议
# ============================================================

def get_style_suggestion(ten_god_name: str) -> Dict[str, Any]:
    """
    获取十神对应的穿搭风格建议

    Args:
        ten_god_name: 十神名称

    Returns:
        {style_keywords, color_suggestion, material_suggestion}
    """
    info = TEN_GODS.get(ten_god_name, TEN_GODS["比肩"])
    colors = TEN_GOD_COLOR_MAP.get(ten_god_name, [])
    materials = TEN_GOD_MATERIAL_MAP.get(ten_god_name, [])

    return {
        "ten_god": ten_god_name,
        "style_keywords": info["style_keywords"],
        "color_suggestion": colors,
        "material_suggestion": materials,
        "description": info["description"],
    }


def get_multi_god_style_suggestion(ten_god_names: List[str]) -> Dict[str, Any]:
    """
    获取多个十神综合穿搭风格建议

    Args:
        ten_god_names: 十神名称列表

    Returns:
        {style_keywords, colors, materials, advice}
    """
    all_keywords: List[str] = []
    all_colors: List[str] = []
    all_materials: List[str] = []

    for name in ten_god_names:
        suggestion = get_style_suggestion(name)
        all_keywords.extend(suggestion["style_keywords"])
        all_colors.extend(suggestion["color_suggestion"])
        all_materials.extend(suggestion["material_suggestion"])

    # 去重保留顺序
    all_keywords = list(dict.fromkeys(all_keywords))[:6]
    all_colors = list(dict.fromkeys(all_colors))[:5]
    all_materials = list(dict.fromkeys(all_materials))[:4]

    advice_parts: List[str] = []
    if all_colors:
        advice_parts.append(f"推荐色系：{'、'.join(all_colors[:3])}。")
    if all_materials:
        advice_parts.append(f"推荐材质：{'、'.join(all_materials[:2])}。")
    if all_keywords:
        advice_parts.append(f"风格关键词：{'、'.join(all_keywords[:3])}。")

    return {
        "style_keywords": all_keywords,
        "colors": all_colors,
        "materials": all_materials,
        "advice": "".join(advice_parts),
    }
