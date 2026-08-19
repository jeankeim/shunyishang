"""
锚点物品识别与匹配工具

当用户在 query 中明确指定某件单品（如「白色衬衫和什么搭配适合我」），
该单品称为「锚点物品」：用户自己已拥有它，推荐系统应围绕它给出搭配方案，
而不是推荐其他同品类冲突单品（如别的颜色的衬衫）。

提供能力：
1. extract_anchor_spec: 从文本提取「颜色+品类」锚点描述（相邻匹配，防误命中）
2. find_anchor_item: 在物品库检索最匹配的锚点物品（颜色同族宽松匹配）
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
]

# 颜色与品类之间允许的连接词（白衬衫 / 白色衬衫 / 白的衬衫 / 白色的衬衫）
_SEPARATORS = ("", "色", "的", "色的")

# 前缀窗口长度（颜色词最长4字如「象牙白」+ 连接词最长2字）
_PREFIX_WINDOW = 7


def extract_anchor_spec(text: str) -> Optional[Dict]:
    """
    从用户文本提取锚点物品描述（颜色+品类相邻组合）

    Args:
        text: 用户输入文本

    Returns:
        命中时返回 {"color_group", "color_word", "category", "category_word",
                   "phrase", "element"}；否则 None
    """
    if not text:
        return None

    for alias, db_category in CATEGORY_ALIASES:
        pos = text.find(alias)
        if pos <= 0:
            continue
        prefix = text[max(0, pos - _PREFIX_WINDOW):pos]
        for group, synonyms in COLOR_GROUPS.items():
            for syn in synonyms:
                for sep in _SEPARATORS:
                    if prefix.endswith(syn + sep):
                        return {
                            "color_group": group,
                            "color_word": syn,
                            "category": db_category,
                            "category_word": alias,
                            "phrase": syn + sep + alias,
                            "element": COLOR_GROUP_ELEMENT.get(group),
                        }
    return None


def find_anchor_item(
    spec: Dict,
    user_gender: Optional[str] = None,
) -> Optional[Dict]:
    """
    在物品库检索与锚点描述最匹配的物品（颜色同族宽松匹配）

    匹配优先级：name 含完整 phrase > name 含「色词+品类词」> 颜色字段同族命中。
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
        for row in rows:
            name = row[1] or ""
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
