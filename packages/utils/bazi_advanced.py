"""
八字高级分析
纳音五行、地支藏干、刑冲克害

纳音五行：60甲子纳音表
地支藏干：12地支藏干表（含主气/中气/余气标识）
刑冲克害：六冲、三刑、六害、三合、六合
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    WUXING_LIST,
)

logger = logging.getLogger(__name__)

# ============================================================
# 1. 60甲子纳音五行表
# ============================================================
# 每对干支对应一个纳音名称和五行
# 格式: "甲子" -> ("海中金", "金")
NAYIN_TABLE: Dict[str, Tuple[str, str]] = {}

_NAYIN_DATA: List[Tuple[str, str, str]] = [
    ("甲子", "海中金", "金"), ("乙丑", "海中金", "金"),
    ("丙寅", "炉中火", "火"), ("丁卯", "炉中火", "火"),
    ("戊辰", "大林木", "木"), ("己巳", "大林木", "木"),
    ("庚午", "路旁土", "土"), ("辛未", "路旁土", "土"),
    ("壬申", "剑锋金", "金"), ("癸酉", "剑锋金", "金"),
    ("甲戌", "山头火", "火"), ("乙亥", "山头火", "火"),
    ("丙子", "涧下水", "水"), ("丁丑", "涧下水", "水"),
    ("戊寅", "城头土", "土"), ("己卯", "城头土", "土"),
    ("庚辰", "白蜡金", "金"), ("辛巳", "白蜡金", "金"),
    ("壬午", "杨柳木", "木"), ("癸未", "杨柳木", "木"),
    ("甲申", "泉中水", "水"), ("乙酉", "泉中水", "水"),
    ("丙戌", "屋上土", "土"), ("丁亥", "屋上土", "土"),
    ("戊子", "霹雳火", "火"), ("己丑", "霹雳火", "火"),
    ("庚寅", "松柏木", "木"), ("辛卯", "松柏木", "木"),
    ("壬辰", "长流水", "水"), ("癸巳", "长流水", "水"),
    ("甲午", "砂中金", "金"), ("乙未", "砂中金", "金"),
    ("丙申", "山下火", "火"), ("丁酉", "山下火", "火"),
    ("戊戌", "平地木", "木"), ("己亥", "平地木", "木"),
    ("庚子", "壁上土", "土"), ("辛丑", "壁上土", "土"),
    ("壬寅", "金箔金", "金"), ("癸卯", "金箔金", "金"),
    ("甲辰", "覆灯火", "火"), ("乙巳", "覆灯火", "火"),
    ("丙午", "天河水", "水"), ("丁未", "天河水", "水"),
    ("戊申", "大驿土", "土"), ("己酉", "大驿土", "土"),
    ("庚戌", "钗钏金", "金"), ("辛亥", "钗钏金", "金"),
    ("壬子", "桑柘木", "木"), ("癸丑", "桑柘木", "木"),
    ("甲寅", "大溪水", "水"), ("乙卯", "大溪水", "水"),
    ("丙辰", "沙中土", "土"), ("丁巳", "沙中土", "土"),
    ("戊午", "天上火", "火"), ("己未", "天上火", "火"),
    ("庚申", "石榴木", "木"), ("辛酉", "石榴木", "木"),
    ("壬戌", "大海水", "水"), ("癸亥", "大海水", "水"),
]

for _gz, _name, _elem in _NAYIN_DATA:
    NAYIN_TABLE[_gz] = (_name, _elem)

# 纳音五行描述
NAYIN_DESCRIPTIONS: Dict[str, str] = {
    "海中金": "金沉海底，需火炼方成器，性格内敛沉稳。",
    "炉中火": "炉中之火，温暖热烈，性格热情但有节制。",
    "大林木": "森林之木，根基深厚，性格稳健有担当。",
    "路旁土": "路旁之土，承载万物，性格踏实包容。",
    "剑锋金": "剑刃之金，锋芒毕露，性格刚毅果断。",
    "山头火": "山顶之火，照亮四方，性格外向耀眼。",
    "涧下水": "山涧之水，清澈流淌，性格灵活变通。",
    "城头土": "城墙之土，坚固防护，性格稳重可靠。",
    "白蜡金": "白蜡之金，温润如玉，性格内秀文雅。",
    "杨柳木": "杨柳之木，柔韧多姿，性格温和适应力强。",
    "泉中水": "泉水之水，源源不断，性格温和持久。",
    "屋上土": "屋瓦之土，遮风挡雨，性格务实保护。",
    "霹雳火": "雷电之火，爆发力强，性格刚烈有魄力。",
    "松柏木": "松柏之木，四季常青，性格坚贞不屈。",
    "长流水": "长流之水，绵延不绝，性格持久有恒心。",
    "砂中金": "砂中之金，需淘洗方显，性格含蓄有潜力。",
    "山下火": "山下之火，温暖照人，性格温和亲和。",
    "平地木": "平地之木，平凡务实，性格低调扎实。",
    "壁上土": "墙壁之土，隔挡防护，性格谨慎有原则。",
    "金箔金": "金箔之金，华丽轻薄，性格外向善交际。",
    "覆灯火": "灯火之火，照亮一方，性格温和有奉献精神。",
    "天河水": "天河之水，雨润苍生，性格大方博爱。",
    "大驿土": "驿站之土，通达四方，性格开朗善沟通。",
    "钗钏金": "钗钏之金，精致装饰，性格优雅注重形象。",
    "桑柘木": "桑柘之木，养蚕织布，性格勤劳务实。",
    "大溪水": "大溪之水，奔流不息，性格活跃有冲劲。",
    "沙中土": "沙中之土，松散不固，性格灵活不拘束。",
    "天上火": "天上之火，普照大地，性格光明磊落。",
    "石榴木": "石榴之木，多子多福，性格丰盈有多面性。",
    "大海水": "大海之水，汪洋浩瀚，性格包容博大。",
}

# ============================================================
# 2. 地支藏干表（含主气/中气/余气标识）
# ============================================================
# is_main: True=主气, False=余气（中气也算余气的一种）
HIDDEN_STEMS_TABLE: Dict[str, List[Dict[str, Any]]] = {
    "子": [{"stem": "癸", "element": "水", "is_main": True}],
    "丑": [{"stem": "己", "element": "土", "is_main": True},
           {"stem": "癸", "element": "水", "is_main": False},
           {"stem": "辛", "element": "金", "is_main": False}],
    "寅": [{"stem": "甲", "element": "木", "is_main": True},
           {"stem": "丙", "element": "火", "is_main": False},
           {"stem": "戊", "element": "土", "is_main": False}],
    "卯": [{"stem": "乙", "element": "木", "is_main": True}],
    "辰": [{"stem": "戊", "element": "土", "is_main": True},
           {"stem": "乙", "element": "木", "is_main": False},
           {"stem": "癸", "element": "水", "is_main": False}],
    "巳": [{"stem": "丙", "element": "火", "is_main": True},
           {"stem": "庚", "element": "金", "is_main": False},
           {"stem": "戊", "element": "土", "is_main": False}],
    "午": [{"stem": "丁", "element": "火", "is_main": True},
           {"stem": "己", "element": "土", "is_main": False}],
    "未": [{"stem": "己", "element": "土", "is_main": True},
           {"stem": "丁", "element": "火", "is_main": False},
           {"stem": "乙", "element": "木", "is_main": False}],
    "申": [{"stem": "庚", "element": "金", "is_main": True},
           {"stem": "壬", "element": "水", "is_main": False},
           {"stem": "戊", "element": "土", "is_main": False}],
    "酉": [{"stem": "辛", "element": "金", "is_main": True}],
    "戌": [{"stem": "戊", "element": "土", "is_main": True},
           {"stem": "辛", "element": "金", "is_main": False},
           {"stem": "丁", "element": "火", "is_main": False}],
    "亥": [{"stem": "壬", "element": "水", "is_main": True},
           {"stem": "甲", "element": "木", "is_main": False}],
}

# ============================================================
# 3. 刑冲克害关系表
# ============================================================

# 六冲
CHONG_PAIRS: List[Tuple[str, str]] = [
    ("子", "午"), ("丑", "未"), ("寅", "申"),
    ("卯", "酉"), ("辰", "戌"), ("巳", "亥"),
]

# 三刑（三组）
XING_GROUPS: List[Tuple[str, ...]] = [
    ("寅", "巳", "申"),  # 无恩之刑
    ("丑", "戌", "未"),  # 恃势之刑
]

# 互刑（子卯相刑）
XING_MUTUAL: List[Tuple[str, str]] = [
    ("子", "卯"),  # 无礼之刑
]

# 自刑
XING_SELF: List[str] = ["辰", "午", "酉", "亥"]

# 六害
HAI_PAIRS: List[Tuple[str, str]] = [
    ("子", "未"), ("丑", "午"), ("寅", "巳"),
    ("卯", "辰"), ("申", "亥"), ("酉", "戌"),
]

# 三合局
SANHE_GROUPS: List[Tuple[str, ...]] = [
    ("申", "子", "辰"),  # 水局
    ("亥", "卯", "未"),  # 木局
    ("寅", "午", "戌"),  # 火局
    ("巳", "酉", "丑"),  # 金局
]

# 三合对应五行
SANHE_ELEMENT: Dict[Tuple[str, ...], str] = {
    ("申", "子", "辰"): "水",
    ("亥", "卯", "未"): "木",
    ("寅", "午", "戌"): "火",
    ("巳", "酉", "丑"): "金",
}

# 六合
LIUHE_PAIRS: List[Tuple[str, str]] = [
    ("子", "丑"), ("寅", "亥"), ("卯", "戌"),
    ("辰", "酉"), ("巳", "申"), ("午", "未"),
]

# 六合对应五行
LIUHE_ELEMENT: Dict[Tuple[str, str], str] = {
    ("子", "丑"): "土", ("寅", "亥"): "木", ("卯", "戌"): "火",
    ("辰", "酉"): "金", ("巳", "申"): "水", ("午", "未"): "土",
}


# ============================================================
# 纳音五行
# ============================================================

def get_nayin_element(heavenly_stem: str, earthly_branch: str) -> Dict[str, Any]:
    """
    获取纳音五行

    Args:
        heavenly_stem: 天干
        earthly_branch: 地支

    Returns:
        {nayin_name, nayin_element, nayin_description}
    """
    ganzhi = f"{heavenly_stem}{earthly_branch}"
    name, element = NAYIN_TABLE.get(ganzhi, ("未知", "土"))
    description = NAYIN_DESCRIPTIONS.get(name, "")

    return {
        "ganzhi": ganzhi,
        "nayin_name": name,
        "nayin_element": element,
        "nayin_description": description,
    }


# ============================================================
# 地支藏干
# ============================================================

def get_hidden_stems(earthly_branch: str) -> List[Dict[str, Any]]:
    """
    获取地支藏干

    Args:
        earthly_branch: 地支

    Returns:
        [{stem, element, is_main}]
    """
    return HIDDEN_STEMS_TABLE.get(earthly_branch, [])


# ============================================================
# 刑冲克害分析
# ============================================================

def analyze_chong(branches: List[str]) -> Dict[str, Any]:
    """
    分析冲（六冲）

    Args:
        branches: 地支列表

    Returns:
        {has_chong, pairs: [{branch_a, branch_b, description}]}
    """
    found_pairs: List[Dict[str, Any]] = []
    branch_set = set(branches)

    for a, b in CHONG_PAIRS:
        if a in branch_set and b in branch_set:
            found_pairs.append({
                "branch_a": a,
                "branch_b": b,
                "description": f"{a}{b}相冲，主变动、冲突",
            })

    return {
        "has_chong": len(found_pairs) > 0,
        "pairs": found_pairs,
        "count": len(found_pairs),
    }


def analyze_xing(branches: List[str]) -> Dict[str, Any]:
    """
    分析刑（三刑+互刑+自刑）

    Args:
        branches: 地支列表

    Returns:
        {has_xing, groups: [{type, branches, description}]}
    """
    found: List[Dict[str, Any]] = []
    branch_set = set(branches)

    # 三刑
    for group in XING_GROUPS:
        matched = [b for b in group if b in branch_set]
        if len(matched) >= 2:
            xing_type = "三刑" if len(matched) == 3 else "半刑"
            found.append({
                "type": xing_type,
                "branches": matched,
                "description": f"{''.join(matched)}相刑，主刑伤、是非",
            })

    # 互刑（子卯）
    for a, b in XING_MUTUAL:
        if a in branch_set and b in branch_set:
            found.append({
                "type": "互刑",
                "branches": [a, b],
                "description": f"{a}{b}相刑（无礼之刑），主口舌、无礼",
            })

    # 自刑
    from collections import Counter
    branch_counts = Counter(branches)
    for b in XING_SELF:
        if branch_counts.get(b, 0) >= 2:
            found.append({
                "type": "自刑",
                "branches": [b],
                "description": f"{b}自刑，主自寻烦恼",
            })

    return {
        "has_xing": len(found) > 0,
        "groups": found,
        "count": len(found),
    }


def analyze_hai(branches: List[str]) -> Dict[str, Any]:
    """
    分析害（六害）

    Args:
        branches: 地支列表

    Returns:
        {has_hai, pairs: [{branch_a, branch_b, description}]}
    """
    found_pairs: List[Dict[str, Any]] = []
    branch_set = set(branches)

    for a, b in HAI_PAIRS:
        if a in branch_set and b in branch_set:
            found_pairs.append({
                "branch_a": a,
                "branch_b": b,
                "description": f"{a}{b}相害，主暗害、阻碍",
            })

    return {
        "has_hai": len(found_pairs) > 0,
        "pairs": found_pairs,
        "count": len(found_pairs),
    }


def analyze_he(branches: List[str]) -> Dict[str, Any]:
    """
    分析合（三合+六合）

    Args:
        branches: 地支列表

    Returns:
        {has_he, sanhe: [...], liuhe: [...]}
    """
    sanhe_found: List[Dict[str, Any]] = []
    liuhe_found: List[Dict[str, Any]] = []
    branch_set = set(branches)

    # 三合
    for group in SANHE_GROUPS:
        matched = [b for b in group if b in branch_set]
        if len(matched) >= 2:
            element = SANHE_ELEMENT.get(group, "土")
            he_type = "三合" if len(matched) == 3 else "半合"
            sanhe_found.append({
                "type": he_type,
                "branches": matched,
                "element": element,
                "description": f"{''.join(matched)}合{element}局，主和谐、助力",
            })

    # 六合
    for a, b in LIUHE_PAIRS:
        if a in branch_set and b in branch_set:
            element = LIUHE_ELEMENT.get((a, b), "土")
            liuhe_found.append({
                "branch_a": a,
                "branch_b": b,
                "element": element,
                "description": f"{a}{b}合化为{element}，主亲近、融合",
            })

    return {
        "has_he": len(sanhe_found) > 0 or len(liuhe_found) > 0,
        "sanhe": sanhe_found,
        "liuhe": liuhe_found,
        "count": len(sanhe_found) + len(liuhe_found),
    }


# ============================================================
# 完整八字分析
# ============================================================

def full_bazi_analysis(bazi_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    完整八字分析

    整合纳音/藏干/刑冲克害，返回增强的八字分析结果

    Args:
        bazi_result: 八字计算结果（含pillars, eight_chars等）

    Returns:
        增强的八字分析结果
    """
    pillars = bazi_result.get("pillars", {})
    eight_chars = bazi_result.get("eight_chars", [])

    # 1. 四柱纳音
    nayin_results: Dict[str, Any] = {}
    for name in ["year", "month", "day", "hour"]:
        gz = pillars.get(name, "甲子")
        nayin_results[name] = get_nayin_element(gz[0], gz[1])

    # 2. 四柱地支藏干
    hidden_stems: Dict[str, Any] = {}
    for name in ["year", "month", "day", "hour"]:
        gz = pillars.get(name, "甲子")
        hidden_stems[name] = get_hidden_stems(gz[1])

    # 3. 刑冲克害分析
    branches = [pillars.get(name, "甲子")[1] for name in ["year", "month", "day", "hour"]]
    chong = analyze_chong(branches)
    xing = analyze_xing(branches)
    hai = analyze_hai(branches)
    he = analyze_he(branches)

    # 4. 综合分析文字
    analysis_parts: List[str] = []

    # 纳音概述
    nayin_names = [nayin_results[name]["nayin_name"] for name in ["year", "month", "day", "hour"]]
    analysis_parts.append(f"四柱纳音：{nayin_names[0]}、{nayin_names[1]}、{nayin_names[2]}、{nayin_names[3]}。")

    # 冲
    if chong["has_chong"]:
        descs = [p["description"] for p in chong["pairs"]]
        analysis_parts.append(f"地支有冲：{'；'.join(descs)}。")

    # 刑
    if xing["has_xing"]:
        descs = [g["description"] for g in xing["groups"]]
        analysis_parts.append(f"地支有刑：{'；'.join(descs)}。")

    # 害
    if hai["has_hai"]:
        descs = [p["description"] for p in hai["pairs"]]
        analysis_parts.append(f"地支有害：{'；'.join(descs)}。")

    # 合
    if he["has_he"]:
        all_he = [s["description"] for s in he["sanhe"]] + [l["description"] for l in he["liuhe"]]
        analysis_parts.append(f"地支有合：{'；'.join(all_he)}。")

    if not (chong["has_chong"] or xing["has_xing"] or hai["has_hai"] or he["has_he"]):
        analysis_parts.append("四柱地支无明显刑冲克害，格局较为平和。")

    return {
        "pillars": pillars,
        "nayin": nayin_results,
        "hidden_stems": hidden_stems,
        "chong": chong,
        "xing": xing,
        "hai": hai,
        "he": he,
        "analysis": "".join(analysis_parts),
    }
