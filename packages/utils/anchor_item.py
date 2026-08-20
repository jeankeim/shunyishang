"""
锚点物品识别与匹配工具

当用户在 query 中明确指定某件单品（如「白色衬衫和什么搭配适合我」
「牛仔裤配什么鞋」），该单品称为「锚点物品」：用户自己已拥有它，
推荐系统应围绕它给出搭配方案，而不是推荐其他同品类冲突单品
（如别的颜色的衬衫、别的裤子）。颜色可选：有色按「颜色+品类」
相邻匹配，无色仅凭品类点名（如「牛仔裤」）同样构成锚点。

提供能力：
1. extract_anchor_spec: 从文本提取锚点描述（颜色+品类相邻，或无色品类点名）
2. find_anchor_item: 在物品库检索最匹配的锚点物品（有色同族宽松 / 无色按品类词）
3. COLOR_GROUP_ELEMENT: 色系→五行映射，供叙事上下文使用
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 色系（规范色 → 同族近义词，长词在前避免子串误判）
COLOR_GROUPS: Dict[str, List[str]] = {
    "白": ["象牙白", "米白", "乳白", "雪白", "纯白", "银白", "珍珠白", "白"],
    "黑": ["墨黑", "炭黑", "漆黑", "纯黑", "黑"],
    "红": ["酒红", "正红", "橘红", "玫红", "枣红", "绯红", "砖红", "红"],
    "蓝": ["浅蓝", "天蓝", "藏蓝", "深蓝", "靛蓝", "湖蓝", "蔚蓝", "蓝"],
    "绿": ["薄荷绿", "橄榄绿", "翠竹绿", "墨绿", "军绿", "青绿", "绿"],
    "黄": ["姜黄", "焦糖", "棕色", "卡其", "杏色", "燕麦", "黄"],
    "灰": ["铂金灰", "银灰", "烟灰", "灰"],
    "紫": ["紫罗", "葡萄紫", "紫"],
    "粉": ["玫瑰粉", "桃粉", "粉"],
}

# 色系→五行（颜色五行归属，供叙事解释锚点物品五行）
COLOR_GROUP_ELEMENT: Dict[str, str] = {
    "白": "金", "黑": "水", "红": "火", "蓝": "水", "绿": "木",
    "黄": "土", "灰": "金", "紫": "火", "粉": "火",
}

# 品类别名 → items 表主分类（长别名在前，避免「衬衫」误吞「衬衫裙」）
# 内衣/袜子映射到虚拟分类「内衣」（库内无该类物品时排除为 no-op，叙事仍生效）
CATEGORY_ALIASES: List[tuple] = [
    ("防晒衣", "外套"), ("羽绒服", "外套"), ("风衣", "外套"), ("大衣", "外套"),
    ("外套", "外套"), ("夹克", "外套"),
    ("Polo衫", "上装"), ("衬衫裙", "裙装"), ("连衣裙", "裙装"), ("裙装", "裙装"),
    ("半身裙", "裙装"), ("长裙", "裙装"), ("裙子", "裙装"),
    ("衬衫", "上装"), ("T恤", "上装"), ("针织衫", "上装"), ("卫衣", "上装"),
    ("毛衣", "上装"), ("打底衫", "上装"), ("上装", "上装"),
    ("牛仔裤", "下装"), ("西装裤", "下装"), ("休闲裤", "下装"), ("短裤", "下装"),
    ("阔腿裤", "下装"), ("裤子", "下装"), ("下装", "下装"),
    ("帆布鞋", "鞋履"), ("运动鞋", "鞋履"), ("乐福鞋", "鞋履"), ("皮鞋", "鞋履"),
    ("凉鞋", "鞋履"), ("靴子", "鞋履"), ("鞋子", "鞋履"),
    ("内衣", "内衣"), ("内裤", "内衣"), ("打底内衣", "内衣"), ("文胸", "内衣"),
    ("袜子", "内衣"), ("丝袜", "内衣"),
    ("棒球帽", "配饰"), ("渔夫帽", "配饰"), ("帽子", "配饰"),
    ("围巾", "配饰"), ("披肩", "配饰"), ("腰带", "配饰"),
    ("背包", "配饰"), ("手提包", "配饰"), ("包包", "配饰"),
    ("耳环", "饰品"), ("项链", "饰品"), ("手链", "饰品"),
]

# 细粒度分类：库内粗分类（配饰/饰品等）下含多种不冲突小类，
# 冲突排除按「名称含同一品类词」判定（帽子锚点只排除其他帽子，不排除包包）；
# 粗分类（上装/下装等）则整类排除（衬衫锚点排除所有上装）
FINE_GRAINED_CATEGORIES = {"配饰", "饰品", "文玩", "内衣"}

# 按别名长度降序稳定排序，保证长别名优先命中（衬衫裙 先于 衬衫、打底内衣 先于 内衣）
CATEGORY_ALIASES.sort(key=lambda t: -len(t[0]))

# 细分类同义组：同组别名互为冲突（帽子锚点排除棒球帽/渔夫帽）
CATEGORY_SYNONYM_GROUPS: List[set] = [
    {"帽子", "棒球帽", "渔夫帽"},
    {"围巾", "披肩"},
    {"背包", "手提包", "包包"},
    {"内衣", "打底内衣", "文胸", "内裤"},
    {"袜子", "丝袜"},
    {"耳环", "耳钉"},
]

# 颜色与品类之间允许的连接词（白衬衫 / 白色衬衫 / 白的衬衫 / 白色的衬衫）
_SEPARATORS = ("", "色", "的", "色的")

# 前缀窗口长度（颜色词最长4字如「象牙白」+ 连接词最长2字）
_PREFIX_WINDOW = 7

# 提问标记：前缀窗口内出现这些词时，品类词是提问对象（「配什么外套」），
# 而非用户自有单品，不构成锚点
_QUESTION_MARKERS = ("什么", "啥", "哪")


def extract_anchor_specs(text: str) -> List[Dict]:
    """
    从用户文本提取全部锚点物品描述（支持多锚点）

    有色锚点：颜色+品类相邻组合，如「白色衬衫和黑色裤子搭配什么」→ [白/上装, 黑/下装]；
    无色锚点：仅品类点名，如「牛仔裤配什么鞋」→ [None/下装]（用户点名即视为自有）。
    提问对象保护：「配什么外套」「哪条裤子」中品类词是诉求而非自有单品，不提取。
    重叠区间去重（「白色衬衫裙」只命中衬衫裙，不再重复命中衬衫），
    结果按文本位置排序。

    Returns:
        锚点描述列表，每项含 {"color_group", "color_word", "category",
        "category_word", "phrase", "element"}（无色锚点颜色字段为 None）；
        无命中时为空列表
    """
    if not text:
        return []

    hits: List[tuple] = []  # (pos, span, spec)
    spans: List[tuple] = []
    for alias, db_category in CATEGORY_ALIASES:
        start = 0
        while True:
            pos = text.find(alias, start)
            if pos < 0:
                break
            start = pos + 1
            span = (pos, pos + len(alias))
            # 与已命中的更长别名重叠则跳过（长别名优先）
            if any(not (span[1] <= s[0] or span[0] >= s[1]) for s in spans):
                continue
            prefix = text[max(0, pos - _PREFIX_WINDOW):pos]
            # 品类词是提问对象（「配什么外套」「哪条裤子」）而非自有单品 → 不作锚点
            if any(m in prefix for m in _QUESTION_MARKERS):
                continue
            spec = None
            for group, synonyms in COLOR_GROUPS.items():
                if spec:
                    break
                for syn in synonyms:
                    for sep in _SEPARATORS:
                        if prefix.endswith(syn + sep):
                            spec = {
                                "color_group": group,
                                "color_word": syn,
                                "category": db_category,
                                "category_word": alias,
                                "phrase": syn + sep + alias,
                                "element": COLOR_GROUP_ELEMENT.get(group),
                            }
                            break
                    if spec:
                        break
            if spec is None:
                # 无色锚点：用户点名品类单品（「牛仔裤配什么鞋」），同样视为自有，
                # 颜色字段为 None（排除/库内匹配仅按品类词判定）
                spec = {
                    "color_group": None,
                    "color_word": None,
                    "category": db_category,
                    "category_word": alias,
                    "phrase": alias,
                    "element": None,
                }
            spans.append(span)
            hits.append((pos, span, spec))

    hits.sort(key=lambda t: t[0])
    return [spec for _, _, spec in hits]


def extract_anchor_spec(text: str) -> Optional[Dict]:
    """兼容接口：返回首个锚点描述，无命中时 None"""
    specs = extract_anchor_specs(text)
    return specs[0] if specs else None


def item_conflicts_with_anchor(item: Dict, spec: Dict) -> bool:
    """
    判定物品是否与锚点冲突（应被排除）

    - 分类不同 → 不冲突
    - 粗分类（上装/下装/外套/裙装/鞋履）→ 同分类即冲突
    - 细分类（配饰/饰品/文玩/内衣）→ 名称含同一品类词才冲突
      （帽子锚点排除其他帽子，但不排除包包/围巾）
    """
    if item.get("category") != spec["category"]:
        return False
    if spec["category"] in FINE_GRAINED_CATEGORIES:
        name = item.get("name") or ""
        group = next(
            (g for g in CATEGORY_SYNONYM_GROUPS if spec["category_word"] in g),
            None,
        )
        aliases = group if group else {spec["category_word"]}
        return any(a in name for a in aliases)
    return True


def find_anchor_item(
    spec: Dict,
    user_gender: Optional[str] = None,
) -> Optional[Dict]:
    """
    在物品库检索与锚点描述最匹配的物品

    有色锚点匹配优先级：name 含完整 phrase > name 含「色词+品类词」> 颜色字段同族命中；
    无色锚点：name 含品类词（如「牛仔裤」）即命中。
    库中无匹配时返回 None（调用方仅做同品类排除，不置顶）。
    """
    try:
        from apps.api.core.database import DatabasePool
        from packages.recommendation.filters import build_gender_filter

        gender_filter = build_gender_filter(user_gender)
        sql = f"""
            SELECT item_code, name, category, primary_element,
                   attributes_detail, image_url
            FROM items
            WHERE category = %s {gender_filter}
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (spec["category"],))
                rows = cur.fetchall()

        synonyms = COLOR_GROUPS.get(spec["color_group"], [])

        def _color_name(row) -> str:
            detail = row[4] or {}
            if isinstance(detail, dict):
                color = detail.get("颜色") or {}
                if isinstance(color, dict):
                    return str(color.get("名称") or "")
            return ""

        candidates = []
        colorless = spec.get("color_word") is None
        for row in rows:
            name = row[1] or ""
            if colorless:
                # 无色锚点：name 含品类词即视为锚点物品（牛仔裤 → 「xx牛仔裤」）
                if spec["category_word"] in name:
                    candidates.append((0, row[0], row))
                continue
            color_name = _color_name(row)
            haystack = name + color_name
            if not any(syn in haystack for syn in synonyms):
                continue
            # 仅接受名称级命中：完整 phrase=0，色词+品类词=1；
            # 仅同族颜色命中（如白毛衣≠白衬衫）不视为锚点，避免「指定」标记语义失真
            if spec["phrase"] in name or (spec["color_word"] + spec["category_word"]) in name:
                rank = 0
            elif spec["color_word"] in name and spec["category_word"] in name:
                rank = 1
            else:
                continue
            candidates.append((rank, row[0], row))

        if not candidates:
            return None
        candidates.sort(key=lambda t: (t[0], t[1]))
        best = candidates[0][2]
        logger.info(
            f"[锚点匹配] {spec['phrase']} → {best[0]} {best[1]} "
            f"(候选{len(candidates)}件)"
        )
        return {
            "item_code": best[0],
            "name": best[1],
            "category": best[2],
            "primary_element": best[3],
            "attributes_detail": best[4],
            "image_url": best[5],
            # 用户指定单品即最高匹配，补全评分字段供前端展示
            "final_score": 0.99,
            "source": "public",
            "source_label": "🎯 指定",
            "is_anchor": True,
        }
    except Exception as e:
        logger.warning(f"[锚点匹配] 检索失败（降级为仅排除同品类）: {e}")
        return None
