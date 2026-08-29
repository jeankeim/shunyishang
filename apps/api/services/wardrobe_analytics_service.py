"""
衣橱智能分析服务

提供穿着频率分析、季节穿着模式、天气适应性、长期闲置识别等洞察，
帮助用户更好地管理衣橱，减少浪费。
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

logger = logging.getLogger(__name__)

# ── 常量 ────────────────────────────────────────────────────────────────────────
IDLE_DAYS_THRESHOLD = 180          # 180天未穿视为闲置
LOW_FREQ_DAYS_THRESHOLD = 90      # 90天未穿且次数少视为低频
LOW_FREQ_WEAR_COUNT_MAX = 3       # 低频次上限
REDUNDANCY_MIN_ITEMS = 3          # 同品类同五行冗余阈值
HIGH_FREQ_MULTIPLIER = 1.5       # 高频：wear_count >= 品类均值 * 1.5

# 月份 → 季节（与每日成套推荐保持同一口径）
SEASON_MAP_BY_MONTH = {
    1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
    6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋", 12: "冬",
}



# ─────────────────────────────────────────────────────────────────────────────────
# 公共入口
# ─────────────────────────────────────────────────────────────────────────────────

def get_wardrobe_analytics(user_id: int) -> Dict[str, Any]:
    """
    获取衣橱综合分析数据

    返回结构:
    {
        "frequency_analysis": {
            "high_freq_items": [...],   # 高频穿着物品
            "low_freq_items": [...],    # 低频穿着物品
            "redundant_items": [...],   # 冗余物品（同品类同五行多件且低频）
            "category_avg_wear": {...}, # 各品类平均穿着次数
            "summary": {...}            # 汇总统计
        },
        "seasonal_patterns": {
            "spring": {...},
            "summer": {...},
            "autumn": {...},
            "winter": {...}
        },
        "weather_adaptability": {
            "cold": {...},    # <=10°C
            "mild": {...},    # 11-22°C
            "warm": {...},    # 23-28°C
            "hot": {...}      # >=29°C
        },
        "overall_stats": {
            "total_items": int,
            "active_items": int,
            "avg_wear_count": float,
            "most_worn_category": str,
            "most_worn_element": str
        }
    }
    """
    wardrobe = _query_wardrobe(user_id)
    if not wardrobe:
        return _empty_analytics()

    # 1. 穿着频率分析
    freq_analysis = _analyze_frequency(wardrobe)

    # 2. 季节穿着模式（关联日记）
    seasonal = _analyze_seasonal_patterns(user_id, wardrobe)

    # 3. 天气适应性（关联日记天气快照）
    weather_adapt = _analyze_weather_adaptability(user_id, wardrobe)

    # 4. 总体统计
    overall = _compute_overall_stats(wardrobe)

    return {
        "frequency_analysis": freq_analysis,
        "seasonal_patterns": seasonal,
        "weather_adaptability": weather_adapt,
        "overall_stats": overall,
    }


def get_idle_items(user_id: int) -> List[Dict[str, Any]]:
    """
    获取长期闲置物品列表 + 公益建议文案

    闲置条件（满足任一）:
    - last_worn_date 距今 > 180天
    - wear_count = 0 且 created_at 距今 > 90天

    返回每个物品包含:
    {
        "id": int,
        "name": str,
        "category": str,
        "image_url": str,
        "primary_element": str,
        "wear_count": int,
        "last_worn_date": str | null,
        "days_since_worn": int | null,
        "created_at": str,
        "days_owned": int,
        "donation_suggestion": str  # 公益建议文案
    }
    """
    wardrobe = _query_wardrobe(user_id)
    today = date.today()
    idle_items = []

    for item in wardrobe:
        last_worn_str = item.get("last_worn_date")
        wear_count = item.get("wear_count") or 0
        created_at = item.get("created_at")

        # 计算天数
        days_since_worn = None
        days_owned = None

        if last_worn_str:
            last_worn = _parse_date(last_worn_str)
            if last_worn:
                days_since_worn = (today - last_worn).days

        if created_at:
            created = _parse_date(created_at)
            if created:
                days_owned = (today - created).days

        # 闲置判断
        is_idle = False
        if days_since_worn is not None and days_since_worn > IDLE_DAYS_THRESHOLD:
            is_idle = True
        elif wear_count == 0 and days_owned is not None and days_owned > LOW_FREQ_DAYS_THRESHOLD:
            is_idle = True

        if is_idle:
            idle_items.append({
                "id": item.get("id"),
                "name": item.get("name", ""),
                "category": item.get("category", ""),
                "image_url": item.get("image_url"),
                "primary_element": item.get("primary_element"),
                "wear_count": wear_count,
                "last_worn_date": str(last_worn_str) if last_worn_str else None,
                "days_since_worn": days_since_worn,
                "created_at": str(created_at)[:10] if created_at else None,
                "days_owned": days_owned,
                "donation_suggestion": _generate_donation_suggestion(
                    item, days_since_worn, days_owned, wear_count
                ),
            })

    # 按天数降序（最久未穿的排前面）
    idle_items.sort(
        key=lambda x: x.get("days_since_worn") or x.get("days_owned") or 0,
        reverse=True,
    )
    return idle_items


# ─────────────────────────────────────────────────────────────────────────────────
# 五行衣橱平衡（占比 vs 命理目标参考口径）
# ─────────────────────────────────────────────────────────────────────────────────

ELEMENTS = ("金", "木", "水", "火", "土")

# 参考口径：第一喜用 40%、第二喜用 25%、其余三行均分 35%；忌神单品占比上限 10%
LUCKY_TARGET_TIERS = (40.0, 25.0)
LUCKY_REMAINING_PCT = 35.0
AVOID_TARGET_CAP = 10.0
# 缺口小于该值视为已平衡，不出补运建议
GAP_MIN_PCT = 3.0
# 建议单品取件数
ADVICE_ITEM_LIMIT = 3


def get_element_balance(
    user_id: int,
    city: Optional[str] = None,
    gender: Optional[str] = None,
) -> Dict[str, Any]:
    """
    五行衣橱平衡仪表盘

    实际占比：primary_element 计 1.0、secondary_element 计 0.5，归一化为百分比。
    目标占比：用户八字喜用神第一 40% / 第二 25% / 其余三行均分 35%，
             忌神行以 10% 为目标上限（超出即 surplus）。
    无八字时目标为五行均分 20%（兜底参考口径）。

    返回:
    {
        "elements": [{element, count, actual_pct, target_pct, gap_pct, status}],
        "lucky_elements": [...], "avoid_elements": [...],
        "advice": [{element, headline, want: {category, colors, seasons}, items: [...]}],
        "total_items": int, "is_empty": bool,
    }

    注：目标占比是自定义参考口径，文案表述为传统文化参考与搭配建议，不作吉凶断言。
    """
    wardrobe = _query_wardrobe(user_id)
    bazi = _get_bazi_safe(user_id)
    lucky_elements = [e for e in (bazi.get("suggested_elements") or []) if e in ELEMENTS]
    avoid_elements = [e for e in (bazi.get("avoid_elements") or []) if e in ELEMENTS]

    targets = _compute_target_pcts(lucky_elements, avoid_elements)
    weights, counts = _accumulate_element_weights(wardrobe)
    total_weight = sum(weights.values())

    elements: List[Dict[str, Any]] = []
    for elem in ELEMENTS:
        actual_pct = round(weights[elem] / total_weight * 100, 1) if total_weight else 0.0
        target_pct = targets[elem]
        gap_pct = round(target_pct - actual_pct, 1)
        elements.append({
            "element": elem,
            "count": counts[elem],
            "actual_pct": actual_pct,
            "target_pct": target_pct,
            "gap_pct": gap_pct,
            "status": _element_status(elem, actual_pct, target_pct, gap_pct, avoid_elements),
        })

    season = SEASON_MAP_BY_MONTH[date.today().month]
    temperature = _current_temperature(city)

    advice: List[Dict[str, Any]] = []
    if wardrobe:
        deficient = [e for e in elements if e["gap_pct"] >= GAP_MIN_PCT]
        deficient.sort(key=lambda e: e["gap_pct"], reverse=True)
        for entry in deficient[:2]:
            elem = entry["element"]
            want_category = _pick_want_category(wardrobe, elem)
            want = {
                "category": want_category,
                "colors": ELEMENT_COLOR_MAP.get(elem, [])[:3],
                "seasons": [season],
            }
            advice.append({
                "element": elem,
                "headline": (
                    f"{elem}属性单品偏少（参考缺口 {entry['gap_pct']:.0f}%）· "
                    f"可补 1-2 件{want_category}"
                ),
                "gap_pct": entry["gap_pct"],
                "want": want,
                "items": _query_suggestion_items(
                    elem, season, temperature, wardrobe, gender, want_category
                ),
            })

    return {
        "elements": elements,
        "lucky_elements": lucky_elements,
        "avoid_elements": avoid_elements,
        "advice": advice,
        "total_items": len(wardrobe),
        "is_empty": not wardrobe,
        "temperature": temperature,
        "season": season,
    }


def _get_bazi_safe(user_id: int) -> Dict[str, Any]:
    """读取八字喜用/忌神，失败按未录入处理（目标回落均分）"""
    try:
        from apps.api.services.user_service import get_user_bazi
        return get_user_bazi(user_id) or {}
    except Exception as e:
        logger.debug(f"[ElementBalance] 八字获取失败: {e}")
        return {}


def _compute_target_pcts(
    lucky_elements: List[str],
    avoid_elements: List[str],
) -> Dict[str, float]:
    """目标占比：第一喜用 40% / 第二喜用 25% / 其余三行均分 35%；忌神压到 10% 上限

    喜用神多于两个时，第三及以后按「其余行」档参与均分（参考口径只看前两档）。
    """
    if not lucky_elements:
        targets = {e: 20.0 for e in ELEMENTS}
    else:
        top_two = lucky_elements[:2]
        others = [e for e in ELEMENTS if e not in top_two]
        targets = {e: 0.0 for e in ELEMENTS}
        for idx, elem in enumerate(top_two):
            targets[elem] = LUCKY_TARGET_TIERS[idx]
        if others:
            share = round(LUCKY_REMAINING_PCT / len(others), 1)
            for elem in others:
                targets[elem] = share
    for elem in avoid_elements:
        targets[elem] = min(targets[elem], AVOID_TARGET_CAP)
    return targets


def _accumulate_element_weights(
    wardrobe: List[Dict],
) -> Tuple[Dict[str, float], Dict[str, int]]:
    """主五行计 1.0、次五行计 0.5；count 为命中该五行的件数"""
    weights = {e: 0.0 for e in ELEMENTS}
    counts = {e: 0 for e in ELEMENTS}
    for item in wardrobe:
        primary = item.get("primary_element")
        secondary = item.get("secondary_element")
        hit = False
        if primary in weights:
            weights[primary] += 1.0
            hit = True
        if secondary in weights:
            weights[secondary] += 0.5
            hit = True
        if hit:
            if primary in weights:
                counts[primary] += 1
            if secondary in weights and secondary != primary:
                counts[secondary] += 1
    return weights, counts


def _element_status(
    elem: str,
    actual_pct: float,
    target_pct: float,
    gap_pct: float,
    avoid_elements: List[str],
) -> str:
    """缺口/超出/适中判定；忌神行只看是否超过上限"""
    if elem in avoid_elements:
        return "surplus" if actual_pct > AVOID_TARGET_CAP else "balanced"
    if gap_pct >= GAP_MIN_PCT:
        return "deficient"
    if gap_pct <= -GAP_MIN_PCT:
        return "surplus"
    return "balanced"


def _pick_want_category(wardrobe: List[Dict], elem: str) -> str:
    """在该行件数最少的核心品类上给建议（并列时按品类顺序取第一个）"""
    key_categories = ("上装", "下装", "外套", "鞋履", "配饰")
    elem_count: Dict[str, int] = {c: 0 for c in key_categories}
    for item in wardrobe:
        cat = item.get("category") or ""
        if cat not in elem_count:
            continue
        if item.get("primary_element") == elem or item.get("secondary_element") == elem:
            elem_count[cat] += 1
    return min(elem_count, key=lambda c: (elem_count[c], key_categories.index(c)))


def _current_temperature(city: Optional[str]) -> Optional[int]:
    """当日气温均值（天气源失败返回 None，调用方按不限温度处理）"""
    try:
        from packages.utils.weather_forecast import get_destination_weather
        forecast = get_destination_weather(city or "杭州", 1)
        if forecast:
            day = forecast[0]
            hi = day.get("temperature_max")
            lo = day.get("temperature_min")
            if hi is not None and lo is not None:
                return int((int(hi) + int(lo)) / 2)
    except Exception as e:
        logger.debug(f"[ElementBalance] 天气获取失败: {e}")
    return None


def _query_suggestion_items(
    elem: str,
    season: str,
    temperature: Optional[int],
    wardrobe: List[Dict],
    gender: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    从公共库 items 取该五行、当季、厚度匹配的单品（站内商品，无外链）

    五行命中为硬条件（主/次皆可），品类与季节、厚度均为软优先：
    优先主五行命中 + 缺口品类，不足 3 件时再放开季节限制补齐。
    """
    owned_codes = [i.get("item_code") for i in wardrobe if i.get("item_code")]
    preferred_thickness: List[str] = []
    if temperature is not None:
        if temperature >= 24:
            preferred_thickness = ["轻薄", "极薄"]
        elif temperature <= 12:
            preferred_thickness = ["适中", "中厚", "厚重"]

    # 条件与参数严格按拼接顺序成对构造，避免占位符错位
    where = ["(primary_element = %s OR secondary_element = %s)"]
    where_params: List[Any] = [elem, elem]
    if gender:
        where.append("(gender = %s OR gender = '中性' OR gender IS NULL OR gender = '')")
        where_params.append(gender)
    where.append("item_code <> ALL(%s)")
    where_params.append(owned_codes)

    # 季节条件始终放在 WHERE 末尾：补齐查询时整段去掉即可，参数同步截断
    season_param = json.dumps([season], ensure_ascii=False)
    order_params: List[Any] = [elem, category or "", preferred_thickness, ADVICE_ITEM_LIMIT * 2]

    def _build_sql(with_season: bool) -> str:
        conditions = list(where)
        if with_season:
            conditions.append("COALESCE(applicable_seasons, '[]'::jsonb) @> %s::jsonb")
        return f"""
            SELECT item_code, name, category, primary_element, secondary_element,
                   color, thickness_level, image_url, thumbnail_url
            FROM items
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE WHEN primary_element = %s THEN 0 ELSE 1 END,
                CASE WHEN category = %s THEN 0 ELSE 1 END,
                CASE WHEN thickness_level = ANY(%s) THEN 0 ELSE 1 END,
                energy_intensity DESC NULLS LAST,
                item_code
            LIMIT %s
        """

    rows = _fetch_items(_build_sql(True), where_params + [season_param] + order_params)

    # 当季不足则放开季节补齐（衣橱建议宁缺毋滥，但不希望面板出现空列表）
    if len(rows) < ADVICE_ITEM_LIMIT:
        seen = {r.get("item_code") for r in rows}
        fill_params = where_params + order_params
        for r in _fetch_items(_build_sql(False), fill_params):
            if r.get("item_code") not in seen:
                rows.append(r)
                seen.add(r.get("item_code"))

    return [
        {
            "item_code": r.get("item_code"),
            "name": r.get("name", ""),
            "category": r.get("category", ""),
            "primary_element": r.get("primary_element"),
            "color": r.get("color"),
            "image_url": r.get("image_url") or r.get("thumbnail_url"),
            "element_role": "primary" if r.get("primary_element") == elem else "secondary",
        }
        for r in rows[:ADVICE_ITEM_LIMIT]
    ]


def _fetch_items(sql: str, params: List[Any]) -> List[Dict[str, Any]]:
    """公共库单品查询（失败返回空列表，不影响主面板）"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.warning(f"[ElementBalance] 公共库单品查询失败: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────────
# 穿着频率分析
# ─────────────────────────────────────────────────────────────────────────────────

def _analyze_frequency(wardrobe: List[Dict]) -> Dict[str, Any]:
    """分析穿着频率：高频/低频/冗余"""
    today = date.today()

    # 各品类平均穿着次数
    category_wear_counts: Dict[str, List[int]] = {}
    for item in wardrobe:
        cat = item.get("category") or "其他"
        wc = item.get("wear_count") or 0
        category_wear_counts.setdefault(cat, []).append(wc)

    category_avg: Dict[str, float] = {}
    for cat, counts in category_wear_counts.items():
        category_avg[cat] = sum(counts) / len(counts) if counts else 0

    high_freq = []
    low_freq = []

    for item in wardrobe:
        cat = item.get("category") or "其他"
        wc = item.get("wear_count") or 0
        avg = category_avg.get(cat, 0)

        # 高频：wear_count >= 品类均值 * 1.5 且至少穿过2次
        if wc >= avg * HIGH_FREQ_MULTIPLIER and wc >= 2:
            high_freq.append(_format_freq_item(item, "high"))

        # 低频：last_worn > 90天 且 wear_count < 3
        last_worn = _parse_date(item.get("last_worn_date"))
        if last_worn:
            days = (today - last_worn).days
            if days > LOW_FREQ_DAYS_THRESHOLD and wc < LOW_FREQ_WEAR_COUNT_MAX:
                low_freq.append(_format_freq_item(item, "low", days))

    # 冗余检测：同品类+同五行 >= 3件 且整体低频
    redundant = _detect_redundancy(wardrobe, low_freq)

    # 汇总统计
    total = len(wardrobe)
    summary = {
        "total_items": total,
        "high_freq_count": len(high_freq),
        "low_freq_count": len(low_freq),
        "redundant_count": len(redundant),
        "high_freq_ratio": round(len(high_freq) / total * 100, 1) if total else 0,
        "low_freq_ratio": round(len(low_freq) / total * 100, 1) if total else 0,
    }

    return {
        "high_freq_items": high_freq[:20],
        "low_freq_items": low_freq[:20],
        "redundant_items": redundant[:20],
        "category_avg_wear": {k: round(v, 1) for k, v in category_avg.items()},
        "summary": summary,
    }


def _detect_redundancy(
    wardrobe: List[Dict],
    low_freq_items: List[Dict],
) -> List[Dict[str, Any]]:
    """检测冗余物品：同品类+同五行 >= 3件 且其中多数为低频"""
    low_freq_ids = {i.get("id") for i in low_freq_items}

    # 分组：key = (category, primary_element)
    groups: Dict[Tuple[str, str], List[Dict]] = {}
    for item in wardrobe:
        cat = item.get("category") or "其他"
        elem = item.get("primary_element") or ""
        if elem:
            groups.setdefault((cat, elem), []).append(item)

    redundant = []
    seen_ids = set()
    for (cat, elem), items in groups.items():
        if len(items) >= REDUNDANCY_MIN_ITEMS:
            # 该组中低频物品数量
            low_in_group = [i for i in items if i.get("id") in low_freq_ids]
            if len(low_in_group) >= 2:
                for item in low_in_group:
                    if item.get("id") not in seen_ids:
                        seen_ids.add(item.get("id"))
                        redundant.append(_format_freq_item(
                            item, "redundant",
                            extra_info=f"同品类同五行({cat}/{elem})共{len(items)}件"
                        ))

    return redundant


def _format_freq_item(
    item: Dict,
    freq_type: str,
    days_since_worn: Optional[int] = None,
    extra_info: str = "",
) -> Dict[str, Any]:
    """格式化频率分析物品"""
    return {
        "id": item.get("id"),
        "name": item.get("name", ""),
        "category": item.get("category", ""),
        "image_url": item.get("image_url"),
        "primary_element": item.get("primary_element"),
        "wear_count": item.get("wear_count") or 0,
        "last_worn_date": str(item.get("last_worn_date")) if item.get("last_worn_date") else None,
        "days_since_worn": days_since_worn,
        "freq_type": freq_type,  # high / low / redundant
        "extra_info": extra_info,
    }


# ─────────────────────────────────────────────────────────────────────────────────
# 季节穿着模式
# ─────────────────────────────────────────────────────────────────────────────────

def _analyze_seasonal_patterns(
    user_id: int,
    wardrobe: List[Dict],
) -> Dict[str, Any]:
    """
    分析各季节穿着偏好

    数据来源：
    1. outfit_diaries 打卡记录关联 diary_outfit_items
    2. user_wardrobe.applicable_seasons 字段
    """
    season_map = {"春": "spring", "夏": "summer", "秋": "autumn", "冬": "winter"}
    patterns = {
        "spring": {"top_categories": {}, "top_elements": {}, "top_colors": {}, "total_records": 0},
        "summer": {"top_categories": {}, "top_elements": {}, "top_colors": {}, "total_records": 0},
        "autumn": {"top_categories": {}, "top_elements": {}, "top_colors": {}, "total_records": 0},
        "winter": {"top_categories": {}, "top_elements": {}, "top_colors": {}, "total_records": 0},
    }

    # 从日记关联物品中统计
    diary_items = _query_diary_outfit_items(user_id)

    for di in diary_items:
        diary_month = di.get("diary_month")
        if not diary_month:
            continue
        # 推断季节
        season_cn = _month_to_season(diary_month)
        season_key = season_map.get(season_cn)
        if not season_key:
            continue

        bucket = patterns[season_key]
        bucket["total_records"] += 1

        # 品类
        cat = di.get("category") or ""
        if cat:
            bucket["top_categories"][cat] = bucket["top_categories"].get(cat, 0) + 1

        # 五行
        elem = di.get("primary_element") or ""
        if elem:
            bucket["top_elements"][elem] = bucket["top_elements"].get(elem, 0) + 1

        # 颜色（从 attributes_detail 提取）
        color = _extract_color(di.get("attributes_detail"))
        if color:
            bucket["top_colors"][color] = bucket["top_colors"].get(color, 0) + 1

    # 排序并取 Top3
    result = {}
    for season_key, data in patterns.items():
        result[season_key] = {
            "top_categories": _top_n(data["top_categories"], 3),
            "top_elements": _top_n(data["top_elements"], 3),
            "top_colors": _top_n(data["top_colors"], 3),
            "total_records": data["total_records"],
        }

    return result


def _month_to_season(month: int) -> str:
    """月份 → 季节"""
    if month in (3, 4, 5):
        return "春"
    elif month in (6, 7, 8):
        return "夏"
    elif month in (9, 10, 11):
        return "秋"
    else:
        return "冬"


# ─────────────────────────────────────────────────────────────────────────────────
# 天气适应性
# ─────────────────────────────────────────────────────────────────────────────────

def _analyze_weather_adaptability(
    user_id: int,
    wardrobe: List[Dict],
) -> Dict[str, Any]:
    """
    分析不同温度区间的穿着偏好

    温度区间：cold(<=10°C) / mild(11-22°C) / warm(23-28°C) / hot(>=29°C)
    """
    temp_ranges = {
        "cold":  {"label": "≤10°C", "items": {}},
        "mild":  {"label": "11-22°C", "items": {}},
        "warm":  {"label": "23-28°C", "items": {}},
        "hot":   {"label": "≥29°C", "items": {}},
    }

    # 从日记天气快照中获取温度信息
    diary_weather = _query_diary_weather_snapshots(user_id)

    for dw in diary_weather:
        temp = dw.get("temperature")
        if temp is None:
            continue

        # 确定温度区间
        if temp <= 10:
            bucket = "cold"
        elif temp <= 22:
            bucket = "mild"
        elif temp <= 28:
            bucket = "warm"
        else:
            bucket = "hot"

        # 统计该温度下的穿着
        items_worn = dw.get("items", [])
        for wi in items_worn:
            cat = wi.get("category") or ""
            thickness = wi.get("thickness_level") or ""
            key = f"{cat}|{thickness}" if cat else thickness
            if key:
                temp_ranges[bucket]["items"][key] = temp_ranges[bucket]["items"].get(key, 0) + 1

    # 整理输出
    result = {}
    for bucket, data in temp_ranges.items():
        top_items = _top_n(data["items"], 5)
        result[bucket] = {
            "label": data["label"],
            "preferred_items": top_items,
            "total_records": sum(data["items"].values()),
        }

    return result


# ─────────────────────────────────────────────────────────────────────────────────
# 总体统计
# ─────────────────────────────────────────────────────────────────────────────────

def _compute_overall_stats(wardrobe: List[Dict]) -> Dict[str, Any]:
    """计算衣橱总体统计"""
    total = len(wardrobe)
    total_wear = sum(i.get("wear_count") or 0 for i in wardrobe)
    avg_wear = round(total_wear / total, 1) if total else 0

    # 最穿的品类
    cat_counts: Dict[str, int] = {}
    elem_counts: Dict[str, int] = {}
    for item in wardrobe:
        cat = item.get("category") or ""
        elem = item.get("primary_element") or ""
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + (item.get("wear_count") or 0)
        if elem:
            elem_counts[elem] = elem_counts.get(elem, 0) + (item.get("wear_count") or 0)

    most_worn_cat = max(cat_counts, key=cat_counts.get) if cat_counts else ""
    most_worn_elem = max(elem_counts, key=elem_counts.get) if elem_counts else ""

    # 活跃物品数（wear_count > 0）
    active = sum(1 for i in wardrobe if (i.get("wear_count") or 0) > 0)

    return {
        "total_items": total,
        "active_items": active,
        "inactive_items": total - active,
        "avg_wear_count": avg_wear,
        "total_wear_count": total_wear,
        "most_worn_category": most_worn_cat,
        "most_worn_element": most_worn_elem,
    }


# ─────────────────────────────────────────────────────────────────────────────────
# 公益建议文案
# ─────────────────────────────────────────────────────────────────────────────────

def _generate_donation_suggestion(
    item: Dict,
    days_since_worn: Optional[int],
    days_owned: Optional[int],
    wear_count: int,
) -> str:
    """
    生成温和的公益建议文案

    风格：友好、非指责性、鼓励循环利用
    """
    name = item.get("name", "这件衣物")
    category = item.get("category", "单品")

    if wear_count == 0:
        # 从未穿过
        if days_owned and days_owned > 365:
            return (
                f"「{name}」已经陪伴你{days_owned}天了，但似乎还没有被穿过。"
                f"如果不再需要，可以考虑转赠给有需要的人，让{category}继续发光发热 ✨"
            )
        return (
            f"「{name}」还没有被穿过，如果不打算穿的话，"
            f"不如让它找到更适合的主人 🌱"
        )

    if days_since_worn and days_since_worn > 365:
        return (
            f"「{name}」已经{days_since_worn}天没有穿过了。"
            f"它曾经陪伴你{wear_count}次，如果已经完成了使命，"
            f"可以考虑捐赠给公益机构，让{category}延续它的故事 💚"
        )

    if days_since_worn and days_since_worn > IDLE_DAYS_THRESHOLD:
        return (
            f"「{name}」已经{days_since_worn}天没有穿过了。"
            f"有些{category}适合在特定季节或场合穿着，"
            f"如果确定不再需要，让它帮助更多的人也是很好的选择 🌿"
        )

    return f"「{name}」似乎有一段时间没穿了，可以考虑整理一下衣橱 🍃"


# ─────────────────────────────────────────────────────────────────────────────────
# 数据库查询
# ─────────────────────────────────────────────────────────────────────────────────

def _query_wardrobe(user_id: int) -> List[Dict[str, Any]]:
    """查询用户衣橱所有活跃物品"""
    query = """
        SELECT id, user_id, item_code, name, category, image_url,
               primary_element, secondary_element, attributes_detail,
               wear_count, last_worn_date, is_favorite,
               applicable_weather, applicable_seasons,
               temperature_range, functionality, thickness_level,
               created_at
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 500
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"[WardrobeAnalytics] 衣橱查询失败: {e}")
        return []


def _query_diary_outfit_items(user_id: int) -> List[Dict[str, Any]]:
    """
    查询用户日记关联的穿着物品（用于季节分析）

    关联: outfit_diaries → diary_outfit_items → user_wardrobe
    """
    query = """
        SELECT
            EXTRACT(MONTH FROM od.diary_date)::INT AS diary_month,
            COALESCE(doi.category, uw.category) AS category,
            uw.primary_element,
            uw.attributes_detail,
            uw.name
        FROM outfit_diaries od
        INNER JOIN diary_outfit_items doi ON doi.diary_id = od.id
        LEFT JOIN user_wardrobe uw ON uw.id = doi.wardrobe_item_id
        WHERE od.user_id = %s
          AND od.diary_date >= CURRENT_DATE - INTERVAL '1 year'
        ORDER BY od.diary_date DESC
        LIMIT 2000
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.debug(f"[WardrobeAnalytics] 日记物品查询失败: {e}")
        return []


def _query_diary_weather_snapshots(user_id: int) -> List[Dict[str, Any]]:
    """
    查询用户日记中的天气快照和关联穿着

    返回每个打卡日的温度 + 穿着物品信息
    """
    query = """
        SELECT
            od.id AS diary_id,
            od.weather_snapshot,
            od.diary_date
        FROM outfit_diaries od
        WHERE od.user_id = %s
          AND od.weather_snapshot IS NOT NULL
          AND od.weather_snapshot != '{}'::jsonb
          AND od.diary_date >= CURRENT_DATE - INTERVAL '1 year'
        ORDER BY od.diary_date DESC
        LIMIT 500
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                rows = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.debug(f"[WardrobeAnalytics] 天气快照查询失败: {e}")
        return []

    result = []
    for row in rows:
        snapshot = row.get("weather_snapshot") or {}
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except Exception:
                snapshot = {}

        temp = snapshot.get("temperature") or snapshot.get("temp")
        if temp is None:
            continue

        # 获取该日记关联的物品
        items = _query_diary_items_detail(row["diary_id"])
        result.append({
            "temperature": int(temp) if isinstance(temp, (int, float)) else None,
            "items": items,
        })

    return result


def _query_diary_items_detail(diary_id: int) -> List[Dict[str, Any]]:
    """获取某篇日记关联的物品详情"""
    query = """
        SELECT
            COALESCE(doi.category, uw.category) AS category,
            uw.thickness_level,
            uw.primary_element,
            uw.name
        FROM diary_outfit_items doi
        LEFT JOIN user_wardrobe uw ON uw.id = doi.wardrobe_item_id
        WHERE doi.diary_id = %s
        LIMIT 20
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [diary_id])
                return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────────────────────────

def _parse_date(val) -> Optional[date]:
    """安全解析日期

    注意：datetime 是 date 的子类，isinstance(datetime_obj, date) 为 True，
    因此必须先判断 datetime 并转为 date，否则后续 (date - datetime) 会抛 TypeError。
    """
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def _extract_color(attributes_detail) -> Optional[str]:
    """从 attributes_detail 中提取颜色名称"""
    if not attributes_detail:
        return None
    detail = attributes_detail
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            return None
    if isinstance(detail, dict):
        color_info = detail.get("颜色", {})
        if isinstance(color_info, dict):
            return color_info.get("名称") or None
        if isinstance(color_info, str):
            return color_info
    return None


def _top_n(counter: Dict[str, int], n: int) -> List[Dict[str, Any]]:
    """从计数器中取 Top N"""
    sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    return [{"name": k, "count": v} for k, v in sorted_items[:n]]


def _empty_analytics() -> Dict[str, Any]:
    """衣橱为空时的兜底响应"""
    return {
        "frequency_analysis": {
            "high_freq_items": [],
            "low_freq_items": [],
            "redundant_items": [],
            "category_avg_wear": {},
            "summary": {
                "total_items": 0,
                "high_freq_count": 0,
                "low_freq_count": 0,
                "redundant_count": 0,
                "high_freq_ratio": 0,
                "low_freq_ratio": 0,
            },
        },
        "seasonal_patterns": {
            "spring": {"top_categories": [], "top_elements": [], "top_colors": [], "total_records": 0},
            "summer": {"top_categories": [], "top_elements": [], "top_colors": [], "total_records": 0},
            "autumn": {"top_categories": [], "top_elements": [], "top_colors": [], "total_records": 0},
            "winter": {"top_categories": [], "top_elements": [], "top_colors": [], "total_records": 0},
        },
        "weather_adaptability": {
            "cold": {"label": "≤10°C", "preferred_items": [], "total_records": 0},
            "mild": {"label": "11-22°C", "preferred_items": [], "total_records": 0},
            "warm": {"label": "23-28°C", "preferred_items": [], "total_records": 0},
            "hot": {"label": "≥29°C", "preferred_items": [], "total_records": 0},
        },
        "overall_stats": {
            "total_items": 0,
            "active_items": 0,
            "inactive_items": 0,
            "avg_wear_count": 0,
            "total_wear_count": 0,
            "most_worn_category": "",
            "most_worn_element": "",
        },
    }
