"""
神煞查表系统（命局神煞）

按出生八字干支组合查表，输出命带神煞列表。
与十神体系（五行生克关系角色）互补：十神描述命局结构，神煞提供标签化星曜。

v1 收录 11 项共识度高、流派争议小的神煞：
- 吉星：天乙贵人 / 文昌贵人 / 禄神 / 将星
- 中性：驿马 / 桃花 / 华盖
- 凶煞：羊刃 / 空亡 / 孤辰 / 寡宿

查表依据（主流通行口诀）：
- 天乙贵人：甲戊见丑未，乙己见子申，丙丁见亥酉，壬癸见卯巳，庚辛见寅午（日干/年干查支）
- 文昌贵人：甲乙巳午报，丙戊申宫求，丁己酉上走，庚亥辛子寻，壬寅癸逢卯（日干查支）
- 禄神：甲禄在寅，乙禄在卯，丙戊禄在巳，丁己禄在午，庚禄在申，辛禄在酉，壬禄在亥，癸禄在子（日干查支）
- 羊刃：甲刃在卯，丙戊刃在午，庚刃在酉，壬刃在子（仅阳干，阴干流派不一不收录）
- 驿马/桃花/华盖/将星：三合局查支（年支/日支查其余支）
  申子辰→马寅桃花酉华盖辰将星子；寅午戌→马申桃花卯华盖戌将星午
  亥卯未→马巳桃花子华盖未将星卯；巳酉丑→马亥桃花午华盖丑将星酉
- 孤辰/寡宿：亥子丑见寅/戌，寅卯辰见巳/丑，巳午未见申/辰，申酉戌见亥/未（年支查支）
- 空亡：日柱所在旬中未出现的两个地支（查年/月/时支）

断语采用文化中性表述，配合合规角标「传统命理参考，仅供文化欣赏」。
"""

import logging
from typing import Dict, List, TypedDict

logger = logging.getLogger(__name__)

# 合规角标文案（前端展示于神煞区块底部）
SHEN_SHA_COMPLIANCE_NOTE = "神煞为传统命理文化参考，仅供文化欣赏。"

PILLAR_NAMES = ["年柱", "月柱", "日柱", "时柱"]

DIZHI_LIST = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
TIANGAN_LIST = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]


class ShenShaHit(TypedDict):
    """命带神煞结果项"""
    name: str              # 神煞名
    category: str          # 吉 / 中性 / 煞
    positions: List[str]   # 出现柱位，如 ["年柱", "时柱"]
    duanyu: str            # 传统断语（文化中性表述）


# ============================================================
# 查表定义（顺序即展示顺序：吉 → 中性 → 煞）
# ============================================================

# 天乙贵人：日干/年干 → 贵人之支
_TIANYI_GUIREN: Dict[str, List[str]] = {
    "甲": ["丑", "未"], "戊": ["丑", "未"],
    "乙": ["子", "申"], "己": ["子", "申"],
    "丙": ["亥", "酉"], "丁": ["亥", "酉"],
    "壬": ["卯", "巳"], "癸": ["卯", "巳"],
    "庚": ["寅", "午"], "辛": ["寅", "午"],
}

# 文昌贵人 / 禄神：日干 → 支
_WENCHANG: Dict[str, str] = {
    "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
    "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
}
_LUSHEN: Dict[str, str] = {
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
}

# 羊刃：仅阳干（阴干流派不一，v1 不收录）
_YANGREN: Dict[str, str] = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}

# 三合局分组：支 → 局
_BRANCH_GROUP: Dict[str, str] = {
    "申": "申子辰", "子": "申子辰", "辰": "申子辰",
    "寅": "寅午戌", "午": "寅午戌", "戌": "寅午戌",
    "亥": "亥卯未", "卯": "亥卯未", "未": "亥卯未",
    "巳": "巳酉丑", "酉": "巳酉丑", "丑": "巳酉丑",
}

# 三合局 → 四类星曜目标支
_GROUP_STARS: Dict[str, Dict[str, str]] = {
    "申子辰": {"驿马": "寅", "桃花": "酉", "华盖": "辰", "将星": "子"},
    "寅午戌": {"驿马": "申", "桃花": "卯", "华盖": "戌", "将星": "午"},
    "亥卯未": {"驿马": "巳", "桃花": "子", "华盖": "未", "将星": "卯"},
    "巳酉丑": {"驿马": "亥", "桃花": "午", "华盖": "丑", "将星": "酉"},
}

# 孤辰 / 寡宿：年支 → 支
_GUCHEN: Dict[str, str] = {
    "亥": "寅", "子": "寅", "丑": "寅",
    "寅": "巳", "卯": "巳", "辰": "巳",
    "巳": "申", "午": "申", "未": "申",
    "申": "亥", "酉": "亥", "戌": "亥",
}
_GUASU: Dict[str, str] = {
    "亥": "戌", "子": "戌", "丑": "戌",
    "寅": "丑", "卯": "丑", "辰": "丑",
    "巳": "辰", "午": "辰", "未": "辰",
    "申": "未", "酉": "未", "戌": "未",
}

# 断语库（文化中性表述，禁止确定性断言句式）
_DUANYU: Dict[str, str] = {
    "天乙贵人": "传统认为逢凶化吉之星，主人缘佳、易得助力。",
    "文昌贵人": "传统主文运聪慧，象征好学上进、思维敏捷。",
    "禄神": "传统主福禄俸禄，象征衣食无忧、稳步积累。",
    "将星": "传统主领导力与执行力，象征能担重任。",
    "驿马": "传统主奔波变动，象征生活活跃、动中发展。",
    "桃花": "传统主人缘魅力，象征受欢迎、异性缘佳。",
    "华盖": "传统主才华清高，象征好学悟性强、与艺术哲学有缘。",
    "羊刃": "传统主性情刚烈果决、竞争意识强，现代多解读为执行力与冲劲。",
    "空亡": "传统谓「落空」，象征性情超脱、与哲学精神文化有缘。",
    "孤辰": "传统主性情安静独立，象征享受独处、内心世界丰富。",
    "寡宿": "传统主性情清寡，象征独立自强、不轻易依赖他人。",
}

# 分类
_CATEGORY: Dict[str, str] = {
    "天乙贵人": "吉", "文昌贵人": "吉", "禄神": "吉", "将星": "吉",
    "驿马": "中性", "桃花": "中性", "华盖": "中性",
    "羊刃": "煞", "空亡": "煞", "孤辰": "煞", "寡宿": "煞",
}

# 展示顺序
_ORDER = ["天乙贵人", "文昌贵人", "禄神", "将星", "驿马", "桃花", "华盖",
          "羊刃", "空亡", "孤辰", "寡宿"]


def _kongwang_branches(day_gan: str, day_zhi: str) -> List[str]:
    """
    计算日柱所在旬的空亡两支

    旬首地支 = (日支序 - 日干序) mod 12；空亡为旬首后第 10、11 位地支。
    """
    if day_gan not in TIANGAN_LIST or day_zhi not in DIZHI_LIST:
        return []
    head = (DIZHI_LIST.index(day_zhi) - TIANGAN_LIST.index(day_gan)) % 12
    return [DIZHI_LIST[(head + 10) % 12], DIZHI_LIST[(head + 11) % 12]]


def calculate_shen_sha(eight_chars: List[str]) -> List[ShenShaHit]:
    """
    计算命带神煞

    Args:
        eight_chars: 八字 [年干,年支,月干,月支,日干,日支,时干,时支]

    Returns:
        命带神煞列表（按 吉→中性→煞 固定顺序），无命中时为空列表
    """
    if not eight_chars or len(eight_chars) != 8:
        return []

    year_gan, year_zhi, _, _, day_gan, day_zhi, _, _ = eight_chars
    branches = [eight_chars[1], eight_chars[3], eight_chars[5], eight_chars[7]]

    def positions_of(zhi: str) -> List[str]:
        return [PILLAR_NAMES[i] for i, b in enumerate(branches) if b == zhi]

    hits: Dict[str, List[str]] = {}

    def add(name: str, zhi: str) -> None:
        pos = positions_of(zhi)
        if pos:
            hits.setdefault(name, [])
            for p in pos:
                if p not in hits[name]:
                    hits[name].append(p)

    # —— 日干/年干查支类（日干优先，遍历顺序确定以保证柱位顺序稳定） ——
    for gan in dict.fromkeys([day_gan, year_gan]):
        for zhi in _TIANYI_GUIREN.get(gan, []):
            add("天乙贵人", zhi)
    add("文昌贵人", _WENCHANG.get(day_gan, ""))
    add("禄神", _LUSHEN.get(day_gan, ""))
    add("羊刃", _YANGREN.get(day_gan, ""))

    # —— 三合局查支类（日支优先、年支补充取并集） ——
    for base in dict.fromkeys([day_zhi, year_zhi]):
        stars = _GROUP_STARS.get(_BRANCH_GROUP.get(base, ""), {})
        for name, zhi in stars.items():
            add(name, zhi)

    # —— 年支查孤辰寡宿 ——
    add("孤辰", _GUCHEN.get(year_zhi, ""))
    add("寡宿", _GUASU.get(year_zhi, ""))

    # —— 日柱旬空亡（查年/月/时支） ——
    kw = _kongwang_branches(day_gan, day_zhi)
    for zhi in kw:
        pos = [PILLAR_NAMES[i] for i in (0, 1, 3) if branches[i] == zhi]
        if pos:
            hits.setdefault("空亡", [])
            for p in pos:
                if p not in hits["空亡"]:
                    hits["空亡"].append(p)

    result: List[ShenShaHit] = [
        ShenShaHit(
            name=name,
            category=_CATEGORY[name],
            positions=sorted(hits[name], key=PILLAR_NAMES.index),
            duanyu=_DUANYU[name],
        )
        for name in _ORDER
        if name in hits
    ]
    return result


def shen_sha_context(eight_chars: List[str]) -> str:
    """
    生成供 LLM 叙事注入的神煞上下文文本（无命中返回空串）
    """
    hits = calculate_shen_sha(eight_chars)
    if not hits:
        return ""
    lines = [f"- {h['name']}（{'、'.join(h['positions'])}）：{h['duanyu']}" for h in hits]
    return "\n".join(lines)
