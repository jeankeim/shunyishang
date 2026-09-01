"""
八字计算核心模块
使用 cnlunar 库进行四柱排盘，计算五行分布和喜用神
"""

from typing import Dict, List, Optional, Tuple, TypedDict
import logging

import cnlunar

logger = logging.getLogger(__name__)

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    TIANGAN_YINYANG,
    DIZHI_WUXING,
    DIZHI_CANGAN,
    MONTH_SEASON_WUXING,
    XIYONG_RULES,
    KEYWORD_ELEMENT_MAP,
    SCENE_ELEMENT_MAP,
    WUXING_LIST,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
    WUXING_BEI_KE,
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
    birth_hour: Optional[int],
    gender: str
) -> BaziResult:
    """
    计算八字及喜用神
    
    Args:
        birth_year: 出生年（公历）
        birth_month: 出生月
        birth_day: 出生日
        birth_hour: 出生时（0-23），传 None 表示时辰未知，按三柱（年/月/日）推演
        gender: 性别（"男"或"女"）
    
    Returns:
        BaziResult: 八字计算结果
    """
    # 时辰未知标记：后续仅按年/月/日三柱推演喜用神
    hour_unknown = birth_hour is None

    # 使用 cnlunar 获取农历信息和四柱
    from datetime import datetime
    # 时辰未知时用正午12点占位排盘：年/月/日柱与具体时辰无关，
    # 且避开子时（23:00-00:59）跨日逻辑，保证日柱稳定
    dt = datetime(birth_year, birth_month, birth_day, birth_hour if not hour_unknown else 12)
    lunar = cnlunar.Lunar(dt, godType='8char')
    
    # 获取四柱（年柱、月柱、日柱、时柱）
    year_gz = lunar.year8Char  # 年柱干支
    month_gz = lunar.month8Char  # 月柱干支
    # cnlunar 已正确处理子时跨日：23:00-00:59 自动使用次日日柱
    day_gz = lunar.day8Char  # 日柱干支
    
    if hour_unknown:
        # 三柱模式：不含时柱，仅 6 字（喜用神切片逻辑对 6 字列表天然兼容）
        eight_chars = [
            year_gz[0], year_gz[1],   # 年干、年支
            month_gz[0], month_gz[1], # 月干、月支
            day_gz[0], day_gz[1],     # 日干、日支
        ]
    else:
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
    
    # 查找喜用神（传入完整八字，启用从格/旺衰三分支判定）
    suggested_elements, avoid_elements, reasoning = infer_xiyong(
        day_master, month_element, eight_chars=eight_chars, day_gan=day_gz[0]
    )
    if hour_unknown:
        reasoning = f"时辰未知，按年/月/日三柱推演（不含时柱）。{reasoning}"
    
    # 找出最旺和缺失的五行
    dominant_element = max(five_elements_count, key=five_elements_count.get)
    lacking_element = find_lacking_element(five_elements_count)
    
    return BaziResult(
        pillars={
            "year": year_gz,
            "month": month_gz,
            "day": day_gz,
            "hour": "未知" if hour_unknown else hour_gz,
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


def _weighted_element_scores(eight_chars: List[str]) -> Dict[str, float]:
    """
    计算八字五行加权得分（不做取整）

    天干权重1；地支按藏干计（主气1、中气0.5、余气0.3），
    供 count_five_elements 展示与喜用神旺衰/从格判定共用。
    """
    scores = {w: 0.0 for w in WUXING_LIST}
    for char in eight_chars:
        if char in TIANGAN_WUXING:
            scores[TIANGAN_WUXING[char]] += 1.0
        elif char in DIZHI_WUXING:
            for i, cangan in enumerate(DIZHI_CANGAN.get(char, [])):
                scores[TIANGAN_WUXING.get(cangan, "土")] += (1.0, 0.5, 0.3)[min(i, 2)]
    return scores


def count_five_elements(eight_chars: List[str]) -> Dict[str, int]:
    """
    统计八字中五行的分布
    
    Args:
        eight_chars: 八字（8个字）
    
    Returns:
        Dict[str, int]: 五行统计 {金: x, 木: x, 水: x, 火: x, 土: x}
    """
    scores = _weighted_element_scores(eight_chars)
    # 确保所有五行都有值（使用 round 避免 int 截断导致小数权重丢失）
    return {w: round(scores[w]) for w in WUXING_LIST}


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


# ============================================================
# 喜用神三分支判定阈值（从格 / 正格旺衰）
# ============================================================
CONG_STRONG_SAME_RATIO = 0.75   # 从强：同党（印+比劫）加权占比阈值
CONG_STRONG_OPPOSE_MAX = 0.5    # 从强：财官杀加权上限（财官必须无气）
CONG_WEAK_DOM_RATIO = 0.5       # 从弱：异党主导势力加权占比阈值
CONG_WEAK_YIN_ROOT_MAX = 0.3    # 阴日主允许余气弱根（阴从势，从宽）
CONG_WEAK_YANG_ROOT_MAX = 0.0   # 阳日主须完全无根（阳从气，从严）
BALANCED_GAP = 1.0              # 同异党差值在此范围内视为中和，参考月令规则表


def _ten_role_elements(day_master: str) -> Dict[str, str]:
    """返回日元视角下各十神势力的五行归属"""
    return {
        "比劫": day_master,                            # 同我
        "印": WUXING_BEI_SHENG.get(day_master, "土"),   # 生我
        "食伤": WUXING_SHENG.get(day_master, "火"),     # 我生
        "财": WUXING_KE.get(day_master, "木"),          # 我克
        "官杀": WUXING_BEI_KE.get(day_master, "金"),    # 克我
    }


def infer_xiyong(
    day_master: str,
    month_element: str,
    eight_chars: Optional[List[str]] = None,
    day_gan: Optional[str] = None,
) -> tuple[List[str], List[str], str]:
    """
    推断喜用神（三分支增强版）

    提供 eight_chars 时按「从强 → 从弱 → 正格旺衰」顺序做全局判定，
    reasoning 中给出格局名称、加权得分与流派说明（阳从气/阴从势）；
    未提供时保留旧版 (日元, 月令) 二维逻辑，向后兼容。

    Args:
        day_master: 日元五行
        month_element: 月令五行
        eight_chars: 完整八字（8字列表，可选）
        day_gan: 日柱天干（用于阴阳流派判定，可选）

    Returns:
        tuple: (喜用神列表, 忌神列表, 推理说明)
    """
    if not eight_chars:
        return _infer_xiyong_legacy(day_master, month_element)
    return _infer_xiyong_by_chart(day_master, month_element, eight_chars, day_gan)


def _infer_xiyong_legacy(day_master: str, month_element: str) -> tuple[List[str], List[str], str]:
    """旧版二维逻辑：规则表优先，无匹配按月令旺衰默认推断"""
    key = (day_master, month_element)
    
    # 优先使用规则表（已完整覆盖25种组合）
    if key in XIYONG_RULES:
        return XIYONG_RULES[key]
    
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


def _infer_xiyong_by_chart(
    day_master: str,
    month_element: str,
    eight_chars: List[str],
    day_gan: Optional[str],
) -> tuple[List[str], List[str], str]:
    """全局三分支判定：从强 → 从弱 → 正格旺衰"""
    scores = _weighted_element_scores(eight_chars)
    roles = _ten_role_elements(day_master)

    same_party = scores[roles["比劫"]] + scores[roles["印"]]
    diff_party = scores[roles["财"]] + scores[roles["官杀"]] + scores[roles["食伤"]]
    total = same_party + diff_party

    # 根气与透干帮扶：从弱判定的核心证据
    root_score = 0.0
    for branch in eight_chars[1::2]:
        for i, cangan in enumerate(DIZHI_CANGAN.get(branch, [])):
            if TIANGAN_WUXING.get(cangan, "土") in (roles["比劫"], roles["印"]):
                root_score += (1.0, 0.5, 0.3)[min(i, 2)]
    stems = eight_chars[0::2]
    stem_support = sum(
        1 for idx, gan in enumerate(stems)
        if idx != 2 and TIANGAN_WUXING.get(gan, "土") in (roles["比劫"], roles["印"])
    )

    # —— 分支1：从强（专旺，同党独旺、财官无气且当令）——
    oppose = scores[roles["财"]] + scores[roles["官杀"]]
    if (
        total > 0
        and same_party / total >= CONG_STRONG_SAME_RATIO
        and oppose <= CONG_STRONG_OPPOSE_MAX
        and month_element in (roles["比劫"], roles["印"])
    ):
        suggested = [roles["印"], roles["比劫"]]
        avoid = [roles["官杀"], roles["财"]]
        reasoning = (
            f"同党(印+比劫)加权{same_party:.1f}/{total:.1f}独旺，财官杀仅{oppose:.1f}且不当令，"
            f"判为从强格：顺其旺势，喜{'、'.join(suggested)}（食伤泄秀亦宜），忌{'、'.join(avoid)}逆势。"
        )
        return suggested, avoid, reasoning

    # —— 分支2：从弱（从财/从杀/从儿）——
    dominant_role = max(["财", "官杀", "食伤"], key=lambda r: scores[roles[r]])
    dominant_elem = roles[dominant_role]
    dominant_score = scores[dominant_elem]
    yinyang = TIANGAN_YINYANG.get(day_gan or "", "阴")
    root_max = CONG_WEAK_YIN_ROOT_MAX if yinyang == "阴" else CONG_WEAK_YANG_ROOT_MAX
    in_command = month_element == dominant_elem
    cong_weak_base = (
        root_score <= root_max
        and stem_support == 0
        and total > 0
        and dominant_score / total >= CONG_WEAK_DOM_RATIO
    )
    # 阳从气不从势：异党独旺但所从之势不当令，阳日主不入从格
    yang_blocked = cong_weak_base and yinyang == "阳" and not in_command
    if cong_weak_base and (yinyang == "阴" or in_command):
        if dominant_role == "食伤":
            suggested, avoid = [dominant_elem, roles["财"]], [roles["印"]]
            ge_name = "从儿"
        elif dominant_role == "官杀":
            suggested, avoid = [dominant_elem, roles["财"]], [roles["印"], roles["比劫"]]
            ge_name = "从杀"
        else:
            suggested, avoid = [dominant_elem, roles["食伤"]], [roles["印"], roles["比劫"]]
            ge_name = "从财"
        school_note = ""
        if yinyang == "阴" and not in_command:
            school_note = "阴从势：阴日主气柔，所从之势虽不当令仍入从格。"
        elif yinyang == "阳":
            school_note = "阳从气：阳日主所从之势当令，方入从格。"
        reasoning = (
            f"日元无根(根气{root_score:.1f})、天干无生扶，{dominant_role}{dominant_elem}"
            f"加权{dominant_score:.1f}/{total:.1f}主导，判为{ge_name}格：顺{dominant_role}势，"
            f"喜{'、'.join(suggested)}，忌{'、'.join(avoid)}破格。{school_note}"
        )
        return suggested, avoid, reasoning

    # —— 分支3：正格旺衰（月令当令方加权+1）——
    month_same = month_element in (roles["比劫"], roles["印"])
    same_adj = same_party + (1.0 if month_same else 0.0)
    diff_adj = diff_party + (0.0 if month_same else 1.0)

    if abs(same_adj - diff_adj) <= BALANCED_GAP:
        suggested, avoid, legacy_reasoning = _infer_xiyong_legacy(day_master, month_element)
        reasoning = (
            f"同党{same_adj:.1f} vs 异党{diff_adj:.1f}，旺衰中和，参考月令规则表：{legacy_reasoning}"
        )
        return suggested, avoid, reasoning

    if same_adj > diff_adj:
        suggested = [roles["官杀"], roles["财"]]
        avoid = [roles["印"], roles["比劫"]]
        reasoning = (
            f"同党(印+比劫){same_adj:.1f} vs 异党(财官食伤){diff_adj:.1f}，日元身强，"
            f"喜{suggested[0]}克、{suggested[1]}耗（食伤泄秀为辅），忌{avoid[0]}、{avoid[1]}生扶。"
        )
    else:
        suggested = [roles["印"], roles["比劫"]]
        avoid = [roles["官杀"], roles["财"]]
        reasoning = (
            f"同党(印+比劫){same_adj:.1f} vs 异党(财官食伤){diff_adj:.1f}，日元身弱，"
            f"喜{suggested[0]}生、{suggested[1]}助，忌{avoid[0]}、{avoid[1]}。"
        )

    if yang_blocked:
        reasoning += (
            f"注：异党{dominant_elem}虽独旺，但阳日主「从气不从势」，"
            f"所从之势不当令，不入从格，按正格论。"
        )
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


# ============================================================
# 显式五行修正意图检测（用户实时意图，最高优先级）
# ============================================================

# 显式「补/加」指令模板：用户主动要求加强某五行
# 注意：模板必须足够特异，避免日常词汇误命中（如「重要」含「要」）
EXPLICIT_ADD_PATTERNS: List[str] = [
    "缺{e}", "补{e}", "旺{e}", "想要{e}", "需要{e}", "要穿{e}", "想穿{e}",
    "多穿{e}", "来点{e}", "多点{e}", "{e}弱", "{e}太弱",
    "{e}属性", "{e}元素",  # 新增：用户说"火属性/木元素"等
]

# 显式「避/忌」指令模板：用户主动要求回避某五行
EXPLICIT_AVOID_PATTERNS: List[str] = [
    "忌{e}", "不要{e}", "别穿{e}", "少穿{e}", "不想穿{e}", "避开{e}",
    "{e}太多", "{e}太旺",
]

# 显式「命主身份」表述模板：用户以某五行命人身份提问（如「金命人适合什么颜色」）
# 语义等价于「补 X + 生X者」（比和 + 生我），同属实时意图，优先于八字预设
EXPLICIT_MING_PATTERNS: List[str] = [
    "{e}命人", "{e}命的", "日主{e}", "日主属{e}", "日干{e}", "属{e}命",
]

# 显式「喜用神自述」表述模板：用户直接声明喜用神为某五行（如「喜用神是火应该穿什么颜色」）
# 语义等价于「补 X」，以用户自述为准，优先于本账号八字推算预设
EXPLICIT_XIYONG_PATTERNS: List[str] = [
    "喜用神是{e}", "喜用神为{e}", "喜用神属{e}",
    "用神是{e}", "用神为{e}", "用神属{e}",
    "喜神是{e}", "喜神为{e}", "喜用{e}",
]


def extract_explicit_element_intent(text: str) -> Dict[str, List[str]]:
    """
    检测用户 query 中的显式五行修正指令（实时意图）

    与 infer_elements_from_text 的隐式推断（场景/气质关键词）不同，
    这里只识别用户主动说出的「补X / 缺X / 不要X / X命人」等明确指令，
    例如「五行缺金」「想补金」「不要水」「金命人适合什么颜色」。
    命主身份表述（X命人/日主X）语义映射为 add=[X, 生X者]（比和+生我）；
    喜用神自述（喜用神是X/用神为X）语义映射为 add=[X]（用户自述优先）。
    结果供 merge_recommendations 作为最高优先级五行目标，
    可覆盖八字喜用神预设（用户实时意图 > 预设条件）。

    Args:
        text: 用户输入文本

    Returns:
        {"add": [用户显式要补的五行],
         "avoid": [用户显式要避的五行],
         "ming": [用户提问的命主五行],
         "xiyong": [用户自述的喜用神五行],
         "matched": [命中指令描述]}
    """
    result: Dict[str, List[str]] = {"add": [], "avoid": [], "ming": [], "xiyong": [], "matched": []}
    if not text:
        return result

    for element in WUXING_LIST:
        # 同一五行同时出现补/避指令时，以避为准（否定意图更明确）
        avoid_hit = next(
            (p for p in EXPLICIT_AVOID_PATTERNS if p.format(e=element) in text), None
        )
        if avoid_hit:
            result["avoid"].append(element)
            result["matched"].append(f"{avoid_hit.format(e=element)}→避{element}")
            continue
        add_hit = next(
            (p for p in EXPLICIT_ADD_PATTERNS if p.format(e=element) in text), None
        )
        if add_hit:
            result["add"].append(element)
            result["matched"].append(f"{add_hit.format(e=element)}→补{element}")
            continue
        # 喜用神自述：如「喜用神是火」「用神为金」，语义=补 X（用户自述优先于八字推算）
        xiyong_hit = next(
            (p for p in EXPLICIT_XIYONG_PATTERNS if p.format(e=element) in text), None
        )
        if xiyong_hit:
            result["xiyong"].append(element)
            if element not in result["add"]:
                result["add"].append(element)
            result["matched"].append(f"{xiyong_hit.format(e=element)}→喜用{element}")
            continue
        # 命主身份表述：如「金命人」「日主金」，语义=补 X + 生X者（比和+生我）
        ming_hit = next(
            (p for p in EXPLICIT_MING_PATTERNS if p.format(e=element) in text), None
        )
        if ming_hit:
            result["ming"].append(element)
            for e2 in (element, GENERATED_BY.get(element)):
                if e2 and e2 not in result["add"]:
                    result["add"].append(e2)
            result["matched"].append(
                f"{ming_hit.format(e=element)}→{element}命(补{element}+{GENERATED_BY.get(element)})"
            )

    return result


# 五行相生关系：A生B
GENERATING_CYCLE: Dict[str, str] = {
    "金": "水",  # 金生水
    "水": "木",  # 水生木
    "木": "火",  # 木生火
    "火": "土",  # 火生土
    "土": "金",  # 土生金
}

# 相生逆查：生我者（土生金 → GENERATED_BY[金]=土），供命主身份语义映射使用
GENERATED_BY: Dict[str, str] = {v: k for k, v in GENERATING_CYCLE.items()}


def _check_generates_xiyong(elem: str, xiyong_elements: List[str]) -> bool:
    """检查 elem 是否通过相生关系生成某个喜用神"""
    generated = GENERATING_CYCLE.get(elem, "")
    return generated in xiyong_elements


def merge_recommendations(
    bazi_result: Optional[BaziResult],
    intent_result: Optional[IntentResult],
    scene_result: Optional[Dict],
    weather_element: Optional[str] = None,
    explicit_intent: Optional[Dict[str, List[str]]] = None,
) -> Tuple[List[str], List[str], Dict]:
    """
    合并多层推荐结果

    优先级（高→低）：
    1. 用户显式五行指令（缺X/补X/忌X 等实时意图，可覆盖八字预设）
    2. 八字喜用神（预设）
    3. 天气五行
    4. 场景五行
    5. 隐式关键词意图

    冲突策略：
    - 显式「补X」：X 置于 target 最前，即使 X 为忌神也提升（用户意图优先）
    - 显式「避X」：X 从喜用神中剔除并全局阻断（不进 target / boost）
    - 场景/天气/隐式意图五行与忌神冲突时，检查相生关系：
      - 若该五行生某个喜用神 → 加入 boost_elements（评分加分但不进 target）
      - 若无相生关系 → 跳过

    Args:
        bazi_result: 八字计算结果
        intent_result: 意图推断结果
        scene_result: 场景映射结果
        weather_element: 天气对应的五行
        explicit_intent: 显式五行修正意图（extract_explicit_element_intent 输出）

    Returns:
        Tuple[List[str], List[str], Dict]: (target_elements, boost_elements, avoid_info)
            - target_elements: 最终推荐五行列表（去重，最多3个）
            - boost_elements: 相生辅助五行（忌神但生喜用神，评分加分）
            - avoid_info: 忌神信息（供评分引擎和 SQL 层使用）
                - explicit_avoid: 用户显式回避（硬禁忌，SQL 层直接排除）
                - bazi_avoid: 八字忌神（软禁忌，评分惩罚但不硬过滤）
    """
    elements = []
    boost_elements = []

    xiyong_elements = list(bazi_result["suggested_elements"]) if bazi_result else []
    avoid_elements = list(bazi_result.get("avoid_elements", [])) if bazi_result else []

    explicit_add = (explicit_intent or {}).get("add", [])
    explicit_avoid = (explicit_intent or {}).get("avoid", [])

    # P3-58 防御：数据异常时喜用神与忌神可能出现交集（同一元素既在 suggested 又在 avoid）。
    # 此时以喜用神为准（推荐优先级更高），从忌神列表中剔除冲突元素，避免后续相生判断自相矛盾。
    if xiyong_elements and avoid_elements:
        conflict = set(xiyong_elements) & set(avoid_elements)
        if conflict:
            logger.warning(f"[merge_recommendations] P3-58 触发: 喜忌神交集 {conflict}，以喜用神为准，从忌神列表剔除")
            avoid_elements = [e for e in avoid_elements if e not in set(xiyong_elements)]

    # 0. 用户显式「避X」：实时意图覆盖预设，从喜用神剔除并并入全局忌神
    if explicit_avoid:
        xiyong_elements = [e for e in xiyong_elements if e not in explicit_avoid]
        avoid_elements = list(dict.fromkeys(avoid_elements + explicit_avoid))
        logger.info(
            f"[merge_recommendations] 用户显式避 {explicit_avoid}，"
            f"剔除后喜用神={xiyong_elements}"
        )

    # 1. 用户显式「补 X」（最高优先级，可覆盖忌神）
    # 关键：当用户有显式五行指令时，完全覆盖八字喜用神，不合并
    if explicit_add:
        for elem in explicit_add:
            if elem not in elements:
                elements.append(elem)
                if elem in avoid_elements:
                    logger.warning(
                        f"[merge_recommendations] 用户显式意图覆盖忌神：{elem} 提升进 target_elements"
                    )
        # 显式指令存在时，跳过八字喜用神（完全覆盖，不合并）
        logger.info(
            f"[merge_recommendations] 用户显式指令 {explicit_add} 覆盖八字喜用神 {xiyong_elements}，"
            f"仅使用显式指令"
        )
    else:
        # 2. 八字喜用神（预设，次优先级）- 仅在无显式指令时使用
        for elem in xiyong_elements:
            if elem not in elements:
                elements.append(elem)

    # 3. 天气五行（不与喜用神冲突）
    if weather_element and weather_element not in elements:
        if weather_element in explicit_avoid:
            logger.info(f"[merge_recommendations] 天气五行 {weather_element} 被用户显式回避，跳过")
        elif weather_element in avoid_elements:
            # 忌神但可能相生喜用神
            if _check_generates_xiyong(weather_element, xiyong_elements):
                boost_elements.append(weather_element)
                logger.info(f"[五行相生] 天气五行 {weather_element} 虽为忌神，但生 {GENERATING_CYCLE[weather_element]}（喜用神），加入加分列表")
        else:
            elements.append(weather_element)

    # 4. 场景五行（不与喜用神/天气冲突时叠加）
    if scene_result:
        for elem in scene_result.get("primary", []):
            if elem not in elements:
                if elem in explicit_avoid:
                    continue
                if elem in avoid_elements:
                    # 忌神但可能相生喜用神
                    if _check_generates_xiyong(elem, xiyong_elements):
                        if elem not in boost_elements:
                            boost_elements.append(elem)
                            logger.info(f"[五行相生] 场景五行 {elem} 虽为忌神，但生 {GENERATING_CYCLE[elem]}（喜用神），加入加分列表")
                    continue
                elements.append(elem)

    # 5. 意图推断（补充，需检查忌神与显式回避）
    if intent_result and intent_result["method"] == "rule":
        for elem in intent_result["elements"]:
            if elem not in elements:
                if elem in explicit_avoid:
                    continue
                if elem in avoid_elements:
                    # 忌神元素：检查是否相生喜用神，若是则加入 boost，否则跳过
                    if _check_generates_xiyong(elem, xiyong_elements):
                        if elem not in boost_elements:
                            boost_elements.append(elem)
                            logger.info(f"[五行相生] 意图五行 {elem} 虽为忌神，但生 {GENERATING_CYCLE[elem]}（喜用神），加入加分列表")
                    continue
                elements.append(elem)

    # 去重，最多3个
    target = list(dict.fromkeys(elements))[:3]
    boost = list(dict.fromkeys(boost_elements))

    # 构建 avoid_info（供评分引擎和 SQL 层使用）
    avoid_info = {
        "explicit_avoid": list(dict.fromkeys(explicit_avoid)),  # 硬禁忌（用户说的）
        "bazi_avoid": list(dict.fromkeys(avoid_elements)),      # 软禁忌（八字忌神）
    }

    return target, boost, avoid_info
