"""
每日智能穿搭推荐服务

基于用户八字命理、当日运势、实时天气、季节、个人偏好和衣橱库存，
自动生成3-5件完整搭配建议，实现"打开即见"的个性化穿搭体验。
"""

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.services.user_service import get_user_bazi
from apps.api.services.fortune_engine import calculate_daily_fortune
from apps.api.services.preference_service import preference_service
from packages.utils.scene_mapping import get_scene_preferred_styles
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP, SCENE_ELEMENT_MAP

logger = logging.getLogger(__name__)

# ── 颜色 → 五行反向映射 ──────────────────────────────────────────────────────
COLOR_TO_ELEMENT: Dict[str, str] = {}
for _elem, _colors in ELEMENT_COLOR_MAP.items():
    for _c in _colors:
        COLOR_TO_ELEMENT[_c] = _elem

# ── 季节推断 ─────────────────────────────────────────────────────────────────
SEASON_MAP = {
    1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春",
    6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋", 12: "冬",
}

# ── 品类多样性上限（一套搭配中每个品类最多几件）────────────────────────────────
CATEGORY_MAX_PER_OUTFIT = {
    "上装": 1,
    "下装": 1,
    "裙装": 1,
    "外套": 1,
    "配饰": 2,  # 饰品/手串可多件
    "鞋履": 1,
}

# ── 成套槽位品类归组 ─────────────────────────────────────────────────────────
TOP_CATEGORIES = ("上装",)
BOTTOM_CATEGORIES = ("下装",)
DRESS_CATEGORIES = ("裙装",)
# 一件式品类：本身已含上下身，计入完整性判定（裙装另参与核心位比较）
ONE_PIECE_CATEGORIES = ("裙装", "套装")
SHOE_CATEGORIES = ("鞋履",)
OUTER_CATEGORIES = ("外套",)
ACCESSORY_CATEGORIES = ("配饰", "饰品", "文玩")

# ── 温度 → 厚度适配 ──────────────────────────────────────────────────────────
THICKNESS_HOT = {"轻薄", "极薄"}        # >=28°C
THICKNESS_MILD = {"轻薄", "适中"}       # 15-27°C
THICKNESS_COLD = {"适中", "中厚", "厚重"}  # <=14°C

# 低于该温度才保留外套槽位
OUTERWEAR_TEMP_THRESHOLD = 15
# 配饰槽位单套上限（与 CATEGORY_MAX_PER_OUTFIT['配饰'] 对齐）
ACCESSORY_SLOT_CAP = 2

# ── 场景加成上限 ─────────────────────────────────────────────────────────────
SCENE_BONUS_CAP = 12

# ── 一周尺度跨天复用上限 ─────────────────────────────────────────────────────
# 上装/配饰可高频复用，下装/裙装/鞋履/外套低频复用，避免「7 天同一件白 T」
WEEK_REUSE_CAP: Dict[str, int] = {
    "上装": 3,
    "配饰": 3,
    "下装": 2,
    "裙装": 2,
    "鞋履": 2,
    "外套": 2,
}
WEEK_REUSE_DEFAULT_CAP = 2
# 每复用一次该单品的降权分值（软降权，超出上限才硬约束）
REUSE_PENALTY_PER_USE = 8


# ─────────────────────────────────────────────────────────────────────────────
# 公共入口
# ─────────────────────────────────────────────────────────────────────────────

def generate_daily_outfit(
    user_id: int,
    batch_index: int = 0,
    city_override: Optional[str] = None,
    scene: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成每日智能穿搭建议

    只负责「取实时天气组装上下文」，打分与选物交给 _build_outfit，
    以便一周穿搭日历 / 场景急救等场景复用同一套选物逻辑。

    Args:
        user_id: 用户 ID
        batch_index: 换一批批次 (0-2)
        city_override: 前端定位城市（优先于用户设置）
        scene: 场景 ID（商务/面试等），命中时该场景元素单品加分

    Returns:
        {
            "outfit_items": [...],
            "reasoning": "...",
            "weather_summary": {...},
            "fortune_summary": {...},
            "style_tip": "...",
            "match_score": int,
            "completeness": {"has_top", "has_bottom_or_dress", "has_shoes",
                             "has_accessory", "missing": [...]},
        }
    """
    today = date.today()
    city = city_override or _get_user_city(user_id)
    weather = _get_weather_sync(city)
    user_bazi = get_user_bazi(user_id)

    ctx = _build_context(
        target_date=today,
        city=city,
        weather=weather,
        user_bazi=user_bazi,
        fortune=calculate_daily_fortune(user_bazi, today),
        user_prefs=_get_user_prefs(user_id),
        wardrobe_items=_query_wardrobe(user_id),
        scene=scene,
    )
    return _build_outfit(user_id, ctx, batch_index=batch_index)


def _build_context(
    target_date: date,
    city: str,
    weather: Dict[str, Any],
    user_bazi: Dict[str, Any],
    fortune: Dict[str, Any],
    user_prefs: Dict[str, Dict[str, float]],
    wardrobe_items: List[Dict[str, Any]],
    reuse_counts: Optional[Dict[int, int]] = None,
    scene: Optional[str] = None,
) -> Dict[str, Any]:
    """
    组装单日穿搭上下文

    把「依赖外部数据的部分」（八字、运势、天气、偏好、衣橱）收敛成一个纯数据字典，
    使 _build_outfit 可被连续 7 天复用而无需重复查库。
    """
    lucky_elements: List[str] = fortune.get("lucky_elements", {}).get("elements", [])
    lucky_colors: List[str] = fortune.get("lucky_elements", {}).get("colors", [])
    return {
        "date": target_date,
        "city": city,
        "weather": weather,
        "fortune": fortune,
        "temperature": weather.get("temperature", 22),
        "weather_desc": weather.get("weather", "晴"),
        "weather_element": weather.get("element", "土"),
        "season": SEASON_MAP.get(target_date.month, "秋"),
        "lucky_elements": lucky_elements,
        "lucky_colors": lucky_colors,
        "suggested_elements": user_bazi.get("suggested_elements", []),
        "avoid_elements": user_bazi.get("avoid_elements", []),
        "user_prefs": user_prefs,
        "wardrobe_items": wardrobe_items,
        "reuse_counts": reuse_counts,
        "scene": scene,
    }


def _build_outfit(
    user_id: int,
    ctx: Dict[str, Any],
    batch_index: int = 0,
) -> Dict[str, Any]:
    """
    按上下文完成打分 + 槽位式成套选择，返回与每日穿搭同构的响应

    ctx 中的 reuse_counts（若存在）会在选完后累加，用于一周尺度的跨天复用降权。
    """
    target_date: date = ctx["date"]
    weather: Dict[str, Any] = ctx["weather"]
    temperature = ctx["temperature"]
    season = ctx["season"]
    lucky_elements = ctx["lucky_elements"]
    lucky_colors = ctx["lucky_colors"]
    suggested_elements = ctx["suggested_elements"]
    avoid_elements = ctx["avoid_elements"]
    user_prefs = ctx["user_prefs"]
    scene = ctx.get("scene")
    primary_lucky = (
        lucky_elements[0] if lucky_elements
        else (suggested_elements[0] if suggested_elements else "土")
    )

    wardrobe_items = ctx["wardrobe_items"]
    if not wardrobe_items:
        return _empty_result(
            primary_lucky, lucky_colors, weather, ctx.get("fortune", {}), target_date
        )

    # ── 多维度评分 ──────────────────────────────────────────────────────────
    scored: List[Tuple[Dict[str, Any], int]] = []
    for item in wardrobe_items:
        score = _score_item(
            item=item,
            lucky_elements=lucky_elements,
            lucky_colors=lucky_colors,
            suggested_elements=suggested_elements,
            avoid_elements=avoid_elements,
            temperature=temperature,
            weather_element=ctx["weather_element"],
            season=season,
            user_prefs=user_prefs,
            scene=scene,
        )
        scored.append((item, score))

    # 按分数降序
    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 槽位式成套选择 ──────────────────────────────────────────────────────
    outfit_items, completeness = _select_complete_outfit(
        scored,
        temperature=temperature,
        target_count=5,
        batch_index=batch_index,
        reuse_counts=ctx.get("reuse_counts"),
    )

    if not outfit_items:
        return _empty_result(
            primary_lucky, lucky_colors, weather, ctx.get("fortune", {}), target_date
        )

    # 一周尺度：把本天选中的单品计入复用账本，后续天数自动降权
    reuse_counts = ctx.get("reuse_counts")
    if reuse_counts is not None:
        _bump_reuse_counts(reuse_counts, outfit_items)

    # ── 构建响应 ────────────────────────────────────────────────────────────
    # 取选中物品的平均分的整数形式
    selected_scores = []
    for item, score in scored:
        if any(o.get("id") == item.get("id") for o in outfit_items):
            selected_scores.append(score)
    avg_score = int(sum(selected_scores) / len(selected_scores)) if selected_scores else 0

    reasoning = _build_reasoning(
        lucky_elements, lucky_colors, weather, season, temperature, outfit_items
    )
    style_tip = _build_style_tip(
        lucky_colors, primary_lucky, season, temperature, outfit_items
    )

    return {
        "outfit_items": outfit_items,
        "reasoning": reasoning,
        "weather_summary": {
            "city": ctx["city"],
            "temperature": temperature,
            "weather": ctx["weather_desc"],
            "element": ctx["weather_element"],
        },
        "fortune_summary": {
            "lucky_elements": lucky_elements,
            "lucky_colors": lucky_colors,
            "overall_score": ctx.get("fortune", {}).get("overall_score", 0),
        },
        "style_tip": style_tip,
        "match_score": min(avg_score, 100),
        "completeness": completeness,
        "date": target_date.isoformat(),
    }


def _get_user_prefs(user_id: int) -> Dict[str, Dict[str, float]]:
    """获取用户偏好画像（失败降级为空偏好）"""
    try:
        return preference_service.get_user_preferences(user_id)
    except Exception as e:
        logger.warning(f"[DailyOutfit] 偏好获取失败: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# 一周穿搭日历
# ─────────────────────────────────────────────────────────────────────────────

WEEKDAY_LABELS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
WEEK_DAYS = 7


def generate_week_outfit(
    user_id: int,
    city_override: Optional[str] = None,
    start_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    生成一周（7 天）穿搭日历

    与每日穿搭共用 _build_outfit，差异在于：
    - 天气取自 7 天预报（含无 key 的季节兜底），逐天独立换算元素与温度
    - 运势逐天用 calculate_daily_fortune 重算，幸运元素按天变化
    - 八字 / 偏好 / 衣橱只查一次，7 天共享
    - 跨天复用上限：上装与配饰最多 3 次，下装/裙装/鞋履/外套最多 2 次

    Returns:
        {city, start_date, days: [{date, weekday, temp_min, temp_max, weather,
          lucky_elements, outfit_items, completeness, match_score, reasoning}],
         is_empty}
    """
    start = start_date or date.today()
    city = city_override or _get_user_city(user_id)
    forecast = _get_forecast(city, WEEK_DAYS)
    user_bazi = get_user_bazi(user_id)
    user_prefs = _get_user_prefs(user_id)
    wardrobe_items = _query_wardrobe(user_id)

    # 7 天共享一份复用账本，由 _build_outfit 逐天累加
    reuse_counts: Dict[int, int] = {}
    fallback_weather: Optional[Dict[str, Any]] = None
    days: List[Dict[str, Any]] = []

    for index in range(WEEK_DAYS):
        day = start + timedelta(days=index)
        if index < len(forecast):
            weather = _weather_from_forecast(forecast[index], city)
        else:
            # 预报缺天（如 API 只给 3 天）：用当日实时天气兜底，避免整周崩掉
            if fallback_weather is None:
                fallback_weather = _get_weather_sync(city)
            weather = dict(fallback_weather)

        ctx = _build_context(
            target_date=day,
            city=city,
            weather=weather,
            user_bazi=user_bazi,
            fortune=calculate_daily_fortune(user_bazi, day),
            user_prefs=user_prefs,
            wardrobe_items=wardrobe_items,
            reuse_counts=reuse_counts,
        )
        result = _build_outfit(user_id, ctx, batch_index=0)
        days.append({
            "date": day.isoformat(),
            "weekday": WEEKDAY_LABELS[day.weekday()],
            "temp_min": weather.get("temperature_min"),
            "temp_max": weather.get("temperature_max"),
            "weather": weather.get("weather", "晴"),
            "lucky_elements": result["fortune_summary"]["lucky_elements"],
            "lucky_colors": result["fortune_summary"]["lucky_colors"],
            "outfit_items": result["outfit_items"],
            "completeness": result["completeness"],
            "match_score": result["match_score"],
            "reasoning": result["reasoning"],
        })

    return {
        "city": city,
        "start_date": start.isoformat(),
        "days": days,
        "is_empty": not wardrobe_items,
    }


def generate_week_day_outfit(
    user_id: int,
    target_date: date,
    batch_index: int = 0,
    city_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    一周日历里某一天的「换一套」

    不接入复用账本（单日换一套只影响当天展示），天气从预报中定位该日，
    取不到时回退当日实时天气。响应结构与 /recommend/daily-outfit 完全一致。
    """
    city = city_override or _get_user_city(user_id)
    today = date.today()
    horizon = max(1, min((target_date - today).days + 1, WEEK_DAYS))
    forecast = _get_forecast(city, horizon)
    entry = next(
        (d for d in forecast if d.get("date") == target_date.isoformat()), None
    )
    if entry is None and len(forecast) >= horizon:
        # 预报日期与请求日对不上（如时区差异）时，按第 N 天位置取值
        entry = forecast[horizon - 1]
    weather = (
        _weather_from_forecast(entry, city)
        if entry else _get_weather_sync(city)
    )
    user_bazi = get_user_bazi(user_id)
    ctx = _build_context(
        target_date=target_date,
        city=city,
        weather=weather,
        user_bazi=user_bazi,
        fortune=calculate_daily_fortune(user_bazi, target_date),
        user_prefs=_get_user_prefs(user_id),
        wardrobe_items=_query_wardrobe(user_id),
    )
    return _build_outfit(user_id, ctx, batch_index=batch_index)


def generate_scene_rescue(
    user_id: int,
    scene: str,
    city_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    场景急救搭配：在当日成套穿搭基础上叠加场景加成，纯规则不调 LLM

    直接复用 generate_daily_outfit(scene=...)，因此成套结构（核心位/鞋履/外套/配饰）
    与 completeness 语义完全一致，额外返回 scene / scene_advice。
    """
    result = generate_daily_outfit(
        user_id, batch_index=0, city_override=city_override, scene=scene
    )

    mapping = SCENE_ELEMENT_MAP.get(scene, {})
    items = result["outfit_items"]
    matched = sum(
        1 for i in items
        if {i.get("primary_element"), i.get("secondary_element")}
        & set(mapping.get("primary", []) + mapping.get("secondary", []))
    )
    result["scene"] = scene
    result["scene_elements"] = {
        "primary": mapping.get("primary", []),
        "secondary": mapping.get("secondary", []),
    }
    result["scene_advice"] = _build_scene_advice(
        scene, items, matched, result["weather_summary"].get("temperature", 22)
    )
    return result


def _build_scene_advice(
    scene: str,
    items: List[Dict[str, Any]],
    matched: int,
    temperature: float,
) -> str:
    """场景急救文案：场景要点 + 命中件数 + 缺口提示（规则生成，不作吉凶断言）"""
    mapping = SCENE_ELEMENT_MAP.get(scene, {})
    desc = mapping.get("desc") or "得体舒适"
    primary = mapping.get("primary") or []

    parts = [f"{scene}讲究{desc}"]
    if primary:
        parts.append(f"优先{'、'.join(primary)}属性")
    if not items:
        parts.append("衣橱暂无适配单品，可先补一件基础款")
    else:
        parts.append(f"这套 {len(items)} 件里 {matched} 件踩中场景元素")
        if matched == 0:
            parts.append("缺的元素下次入手时可留意")
    if temperature <= OUTERWEAR_TEMP_THRESHOLD:
        parts.append("别忘了留一件外套")
    return "，".join(parts) + "。"


def _get_forecast(city: str, days: int) -> List[Dict[str, Any]]:
    """取多日天气预报（失败返回空列表，由调用方兜底）"""
    try:
        from packages.utils.weather_forecast import get_destination_weather
        forecast = get_destination_weather(city, days)
        return forecast or []
    except Exception as e:
        logger.warning(f"[WeekOutfit] 多日天气获取失败: {e}")
        return []


def _weather_from_forecast(entry: Dict[str, Any], city: str) -> Dict[str, Any]:
    """把某一日预报转成与 _get_weather_sync 同构的天气字典"""
    try:
        temp_max = int(entry.get("temperature_max", 25))
    except (TypeError, ValueError):
        temp_max = 25
    try:
        temp_min = int(entry.get("temperature_min", 15))
    except (TypeError, ValueError):
        temp_min = 15
    weather_desc = entry.get("weather_desc") or "晴"
    temperature = (temp_max + temp_min) / 2
    return {
        "city": city,
        "temperature": int(temperature),
        "temperature_max": temp_max,
        "temperature_min": temp_min,
        "weather": weather_desc,
        "humidity": entry.get("humidity", 60),
        "element": _element_by_weather(weather_desc, int(temperature)),
    }


def _element_by_weather(weather_desc: str, temperature: int) -> str:
    """天气描述 → 五行（与每日穿搭口径一致，导入异常时兜底为土）"""
    try:
        from apps.api.routers.weather import get_element_by_weather
        element, _ = get_element_by_weather(weather_desc, temperature)
        return element
    except Exception as e:
        logger.debug(f"[WeekOutfit] 天气五行映射失败: {e}")
        return "土"


# ─────────────────────────────────────────────────────────────────────────────
# 评分引擎
# ─────────────────────────────────────────────────────────────────────────────

def _score_item(
    item: Dict[str, Any],
    lucky_elements: List[str],
    lucky_colors: List[str],
    suggested_elements: List[str],
    avoid_elements: List[str],
    temperature: float,
    weather_element: str,
    season: str,
    user_prefs: Dict[str, Dict[str, float]],
    scene: Optional[str] = None,
) -> int:
    """
    多维度评分 (0-100)

    权重分配:
    - 五行匹配 30%  (喜用神 + 当日幸运元素)
    - 天气适配 25%  (温度→厚度 + 功能性)
    - 季节匹配 15%
    - 用户偏好 20%
    - 穿搭新鲜度 10% (wear_count 低的加分)
    - 场景加成 ≤12  (透传 scene 时的额外分，总量仍 clamp 100)
    """
    primary = item.get("primary_element") or ""
    secondary = item.get("secondary_element") or ""

    # ── 五行匹配 (0-30) ────────────────────────────────────────────────────
    wuxing_score = 0
    # 喜用神命中
    if primary in suggested_elements:
        wuxing_score += 15
    if secondary and secondary in suggested_elements:
        wuxing_score += 5
    # 当日幸运元素
    if primary in lucky_elements:
        wuxing_score += 10
    if secondary and secondary in lucky_elements:
        wuxing_score += 5
    # 忌神惩罚
    if primary in avoid_elements:
        wuxing_score -= 10
    wuxing_score = max(0, min(30, wuxing_score))

    # ── 天气适配 (0-25) ────────────────────────────────────────────────────
    weather_score = _calc_weather_score(item, temperature)
    weather_score = max(0, min(25, weather_score))

    # ── 季节匹配 (0-15) ────────────────────────────────────────────────────
    season_score = _calc_season_score(item, season)
    season_score = max(0, min(15, season_score))

    # ── 用户偏好 (0-20) ────────────────────────────────────────────────────
    pref_score = _calc_preference_score(item, user_prefs)
    pref_score = max(0, min(20, int(pref_score * 20)))

    # ── 穿搭新鲜度 (0-10) ──────────────────────────────────────────────────
    wear_count = item.get("wear_count") or 0
    if wear_count == 0:
        freshness = 10
    elif wear_count <= 2:
        freshness = 8
    elif wear_count <= 5:
        freshness = 5
    else:
        freshness = 2

    # 颜色匹配额外加分
    detail = item.get("attributes_detail") or {}
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            detail = {}
    color_name = ""
    if isinstance(detail, dict):
        color_info = detail.get("颜色", {})
        if isinstance(color_info, dict):
            color_name = color_info.get("名称", "") or ""
    color_bonus = 0
    if color_name and color_name in lucky_colors:
        color_bonus = 5
    color_elem = COLOR_TO_ELEMENT.get(color_name, "")
    if color_elem and color_elem in lucky_elements:
        color_bonus += 3
    color_bonus = min(8, color_bonus)

    # ── 场景加成 (0-12) ────────────────────────────────────────────────────
    scene_bonus = _calc_scene_bonus(item, detail, scene)

    total = (
        wuxing_score + weather_score + season_score
        + pref_score + freshness + color_bonus + scene_bonus
    )
    return max(0, min(100, total))


def _calc_scene_bonus(
    item: Dict[str, Any],
    detail: Any,
    scene: Optional[str],
) -> int:
    """
    场景加成 (0-12)

    命中场景主元素 +10、次元素 +5（互斥取高），单品风格属于该场景适宜风格再 +2。
    scene 为空或是未登记场景时返回 0（未知场景兜底为无加成，退化为通用打分）。
    """
    if not scene:
        return 0
    mapping = SCENE_ELEMENT_MAP.get(scene)
    if not mapping:
        return 0

    item_elements = {e for e in (item.get("primary_element"), item.get("secondary_element")) if e}
    bonus = 0
    if item_elements & set(mapping.get("primary", [])):
        bonus += 10
    elif item_elements & set(mapping.get("secondary", [])):
        bonus += 5

    preferred_styles = get_scene_preferred_styles(scene)
    if preferred_styles and isinstance(detail, dict):
        style_info = detail.get("款式")
        style = style_info.get("风格", "") if isinstance(style_info, dict) else ""
        if style and style in preferred_styles:
            bonus += 2

    return min(SCENE_BONUS_CAP, bonus)


def _calc_weather_score(item: Dict[str, Any], temperature: float) -> int:
    """温度→厚度适配评分 (0-25)"""
    thickness = item.get("thickness_level") or ""
    functionality = _parse_list(item.get("functionality"))

    if temperature >= 28:
        # 高温：偏好轻薄
        if thickness in ("轻薄", "极薄"):
            score = 20
        elif thickness == "适中":
            score = 10
        elif thickness in ("中厚", "厚重"):
            score = 0  # 强惩罚
        else:
            score = 8
        # 功能性加分
        if any(f in functionality for f in ("透气", "速干", "防晒")):
            score += 5
        if any(f in functionality for f in ("保暖", "防风")):
            score -= 3
    elif temperature <= 10:
        # 低温：偏好厚重
        if thickness in ("厚重", "中厚"):
            score = 20
        elif thickness == "适中":
            score = 12
        elif thickness in ("极薄", "轻薄"):
            score = 2
        else:
            score = 8
        if "保暖" in functionality:
            score += 5
    else:
        # 适中温度
        if thickness == "适中":
            score = 18
        elif thickness in ("轻薄", "中厚"):
            score = 12
        else:
            score = 8

    return max(0, min(25, score))


def _calc_season_score(item: Dict[str, Any], current_season: str) -> int:
    """季节适配评分 (0-15)"""
    applicable_seasons = _parse_list(item.get("applicable_seasons"))
    if not applicable_seasons:
        return 8  # 无季节信息，中性
    if current_season in applicable_seasons:
        return 15
    # 相邻季节轻微惩罚
    adjacent = {"春": {"冬", "夏"}, "夏": {"春", "秋"}, "秋": {"夏", "冬"}, "冬": {"秋", "春"}}
    if current_season in adjacent.get(current_season, set()):
        return 8
    return 3


def _calc_preference_score(
    item: Dict[str, Any],
    user_prefs: Dict[str, Dict[str, float]],
) -> float:
    """用户偏好匹配评分 (0.0-1.0)"""
    if not user_prefs:
        return 0.5

    total = 0.0
    count = 0

    # 颜色
    detail = item.get("attributes_detail") or {}
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            detail = {}
    color_name = ""
    if isinstance(detail, dict):
        color_info = detail.get("颜色", {})
        if isinstance(color_info, dict):
            color_name = color_info.get("名称", "") or ""

    if color_name and "color" in user_prefs:
        w = user_prefs["color"].get(color_name, 0)
        total += _weight_to_score(w)
        count += 1

    # 五行
    primary = item.get("primary_element") or ""
    if primary and "element" in user_prefs:
        w = user_prefs["element"].get(primary, 0)
        total += _weight_to_score(w)
        count += 1

    # 品类
    category = item.get("category") or ""
    if category and "category" in user_prefs:
        w = user_prefs["category"].get(category, 0)
        total += _weight_to_score(w)
        count += 1

    # 风格
    if isinstance(detail, dict):
        style = detail.get("款式", {}).get("风格", "") if isinstance(detail.get("款式"), dict) else ""
    else:
        style = ""
    if style and "style" in user_prefs:
        w = user_prefs["style"].get(style, 0)
        total += _weight_to_score(w)
        count += 1

    if count == 0:
        return 0.5
    return total / count


# ─────────────────────────────────────────────────────────────────────────────
# 槽位式成套选择
# ─────────────────────────────────────────────────────────────────────────────

def _select_complete_outfit(
    scored: List[tuple],
    temperature: float,
    target_count: int = 5,
    batch_index: int = 0,
    reuse_counts: Optional[Dict[int, int]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    槽位式成套选择，保证「核心位 + 鞋履 +（低温时）外套 + 配饰」结构完整

    换一批语义与旧实现一致：逐批模拟并排除前序批次已选物品，
    候选耗尽时回退复用已展示物品。

    Args:
        reuse_counts: {单品 id: 本周已用次数}，一周尺度传入以做跨天降权与上限约束，
                      由调用方持有并在选中后累加

    Returns:
        (选中的物品列表, completeness 完整性摘要)
    """
    excluded_ids: set = set()
    selected: List[Dict[str, Any]] = []
    completeness = _empty_completeness()

    for _ in range(batch_index + 1):
        selected, completeness = _pick_one_complete_batch(
            scored, temperature, target_count, excluded_ids, reuse_counts
        )
        if not selected and excluded_ids:
            # 候选耗尽：回退复用已展示物品
            excluded_ids.clear()
            selected, completeness = _pick_one_complete_batch(
                scored, temperature, target_count, excluded_ids, reuse_counts
            )
        excluded_ids.update(item["id"] for item in selected)

    return selected, completeness


def _week_reuse_cap(category: str) -> int:
    """该品类在一周内的复用次数上限"""
    if category in WEEK_REUSE_CAP:
        return WEEK_REUSE_CAP[category]
    if category in ACCESSORY_CATEGORIES:
        return WEEK_REUSE_CAP["配饰"]
    return WEEK_REUSE_DEFAULT_CAP


def _effective_score(item: Dict[str, Any], score: int, reuse_counts: Dict[int, int]) -> int:
    """跨天已用单品按次数降权后的排序用分（不污染真实 match_score）"""
    return score - REUSE_PENALTY_PER_USE * reuse_counts.get(item.get("id"), 0)


def _reuse_exhausted(item: Dict[str, Any], reuse_counts: Dict[int, int]) -> bool:
    """该单品本周已达到复用次数上限"""
    category = item.get("category") or "其他"
    return reuse_counts.get(item.get("id"), 0) >= _week_reuse_cap(category)


def _bump_reuse_counts(reuse_counts: Dict[int, int], items: List[Dict[str, Any]]) -> None:
    """选中后累计复用次数，供下一天降权"""
    for it in items:
        item_id = it.get("id")
        if item_id is not None:
            reuse_counts[item_id] = reuse_counts.get(item_id, 0) + 1


def _pick_one_complete_batch(
    scored: List[tuple],
    temperature: float,
    target_count: int,
    excluded_ids: set,
    reuse_counts: Optional[Dict[int, int]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """按槽位取物：核心位 → 鞋履 → 外套（低温）→ 配饰 → 按分数补齐"""
    # 本批可用候选（已按分数降序，scored 由调用方排序）
    pool = [(item, score) for item, score in scored if item.get("id") not in excluded_ids]
    if not pool:
        return [], _empty_completeness()
    if reuse_counts:
        # 本周已穿过的往后排，让同类候选在 7 天内轮换
        pool = sorted(
            pool,
            key=lambda x: _effective_score(x[0], x[1], reuse_counts),
            reverse=True,
        )

    used_ids: set = set()
    selected: List[Dict[str, Any]] = []
    category_count: Dict[str, int] = {}
    # 衣橱层面已有的品类：品类完全缺货时跳过槽位（记入 missing），
    # 仅因换一批被排除时才回落全局次优
    stocked_categories = {item.get("category") or "其他" for item, _ in scored}
    # 高温天禁止任何槽位（含补齐与全局回落）捡外套
    hot_blocked: Tuple[str, ...] = (
        OUTER_CATEGORIES if temperature > OUTERWEAR_TEMP_THRESHOLD else ()
    )

    def _first_available(
        categories: Tuple[str, ...] = (),
        blocked: Tuple[str, ...] = (),
        respect_reuse: bool = True,
    ) -> Optional[tuple]:
        """取分数最高、未入选、未超品类上限的物品；categories 非空时限定品类"""
        for item, score in pool:
            if item.get("id") in used_ids:
                continue
            category = item.get("category") or "其他"
            if categories and category not in categories:
                continue
            if category in blocked:
                continue
            if category_count.get(category, 0) >= CATEGORY_MAX_PER_OUTFIT.get(category, 1):
                continue
            if respect_reuse and reuse_counts and _reuse_exhausted(item, reuse_counts):
                continue
            return item, score
        return None

    def _take(
        categories: Tuple[str, ...],
        slot_cap: int = 1,
        blocked: Tuple[str, ...] = (),
    ) -> None:
        """
        占用一个槽位：品类内优先，品类本轮无候选则回落全局次优。
        回落只发生在槽位的第一件（避免配饰第二件抢走其他品类名额）。
        """
        if categories and not (set(categories) & stocked_categories):
            return
        # 高温天任何槽位都不该捡到外套（外套位本身只在低温时开启，故不会误伤）
        blocked = tuple(blocked) + hot_blocked
        for slot_index in range(slot_cap):
            if len(selected) >= target_count:
                return
            picked = _first_available(categories, blocked)
            if picked is None and slot_index == 0:
                # 回落全局次优；遵守复用上限，衣橱过小不足以凑齐一套时才打破
                picked = _first_available((), blocked) or _first_available(
                    (), blocked, respect_reuse=False
                )
            if picked is None:
                return
            item, score = picked
            category = item.get("category") or "其他"
            selected.append(_format_item(item, score))
            used_ids.add(item.get("id"))
            category_count[category] = category_count.get(category, 0) + 1

    # ── 核心位：裙装套 vs 上装+下装套 ──────────────────────────────────────
    dress = _first_available(DRESS_CATEGORIES)
    top = _first_available(TOP_CATEGORIES)
    bottom = _first_available(BOTTOM_CATEGORIES)
    if dress and (not top or not bottom or dress[1] > top[1] + bottom[1]):
        # 裙装最高分占优：走裙装套，免下装位
        _take(DRESS_CATEGORIES)
    else:
        _take(TOP_CATEGORIES)
        _take(BOTTOM_CATEGORIES)

    # ── 鞋履位：必出 ───────────────────────────────────────────────────────
    _take(SHOE_CATEGORIES)

    # ── 外套位：仅低温时保留槽 ─────────────────────────────────────────────
    if temperature <= OUTERWEAR_TEMP_THRESHOLD:
        _take(OUTER_CATEGORIES)

    # ── 配饰位：有则出 1-2 件 ──────────────────────────────────────────────
    _take(ACCESSORY_CATEGORIES, slot_cap=ACCESSORY_SLOT_CAP)

    # ── 剩余名额按分数补齐（高温时不补外套，避免热天出外套）──────────────
    _take((), slot_cap=max(0, target_count - len(selected)))

    return selected, _build_completeness(scored, selected, temperature)


def _build_completeness(
    scored: List[tuple],
    selected: List[Dict[str, Any]],
    temperature: float,
) -> Dict[str, Any]:
    """
    成套完整性摘要：missing 只登记「衣橱根本没有该品类」的缺口，
    因换一批排除导致的本轮临时缺位不算衣橱缺失。
    """
    categories = {item.get("category") or "" for item in selected}

    def _has(group: Tuple[str, ...]) -> bool:
        return bool(categories & set(group))

    def _stocked(group: Tuple[str, ...]) -> bool:
        return any((item.get("category") or "") in group for item, _ in scored)

    has_top = _has(TOP_CATEGORIES) or _has(ONE_PIECE_CATEGORIES)
    has_bottom_or_dress = _has(BOTTOM_CATEGORIES) or _has(ONE_PIECE_CATEGORIES)
    has_shoes = _has(SHOE_CATEGORIES)
    has_accessory = _has(ACCESSORY_CATEGORIES)

    missing: List[str] = []
    if not has_top and not _stocked(TOP_CATEGORIES):
        missing.append("上装")
    if not has_bottom_or_dress and not _stocked(BOTTOM_CATEGORIES + DRESS_CATEGORIES):
        missing.append("下装")
    if not has_shoes and not _stocked(SHOE_CATEGORIES):
        missing.append("鞋履")
    if temperature <= OUTERWEAR_TEMP_THRESHOLD and not _has(OUTER_CATEGORIES) and not _stocked(OUTER_CATEGORIES):
        missing.append("外套")
    if not has_accessory and not _stocked(ACCESSORY_CATEGORIES):
        missing.append("配饰")

    return {
        "has_top": has_top,
        "has_bottom_or_dress": has_bottom_or_dress,
        "has_shoes": has_shoes,
        "has_accessory": has_accessory,
        "missing": missing,
    }


def _empty_completeness() -> Dict[str, Any]:
    """无候选时的完整性摘要（全部未覆盖，无缺口清单）"""
    return {
        "has_top": False,
        "has_bottom_or_dress": False,
        "has_shoes": False,
        "has_accessory": False,
        "missing": [],
    }


def _format_item(item: Dict[str, Any], score: int) -> Dict[str, Any]:
    """格式化推荐物品输出"""
    return {
        "id": item.get("id"),
        "name": item.get("name", ""),
        "category": item.get("category"),
        "image_url": item.get("image_url"),
        "primary_element": item.get("primary_element"),
        "secondary_element": item.get("secondary_element"),
        "wear_count": item.get("wear_count", 0),
        "is_favorite": item.get("is_favorite", False),
        "match_score": score,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 文案生成
# ─────────────────────────────────────────────────────────────────────────────

def _build_reasoning(
    lucky_elements: List[str],
    lucky_colors: List[str],
    weather: Dict[str, Any],
    season: str,
    temperature: float,
    items: List[Dict[str, Any]],
) -> str:
    """生成整体推荐理由（≤80字）"""
    parts = []
    if lucky_elements:
        parts.append(f"今日运势偏{''.join(lucky_elements[:2])}")
    parts.append(f"{season}季{weather.get('weather', '')}{temperature}°C")
    if lucky_colors:
        parts.append(f"宜{lucky_colors[0]}色系")

    categories = [i.get("category", "") for i in items if i.get("category")]
    if categories:
        parts.append(f"搭配{'/'.join(categories[:3])}")

    reasoning = "，".join(parts) + "。"
    return reasoning[:80] if len(reasoning) <= 80 else reasoning[:77] + "..."


def _build_style_tip(
    lucky_colors: List[str],
    primary_lucky: str,
    season: str,
    temperature: float,
    items: List[Dict[str, Any]],
) -> str:
    """生成穿搭小贴士"""
    tips = []
    if primary_lucky:
        tips.append(f"五行属{primary_lucky}的单品可提升今日运势")
    if temperature >= 28:
        tips.append("高温天气注意选择透气轻薄面料")
    elif temperature <= 10:
        tips.append("低温天气建议搭配保暖外套")
    if lucky_colors:
        tips.append(f"今日幸运色：{lucky_colors[0]}")
    return "；".join(tips[:3])


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _get_user_city(user_id: int) -> str:
    """获取用户首选城市（优先级：用户设置 > 上次定位 > 默认杭州）"""
    try:
        query = "SELECT preferred_city FROM users WHERE id = %s"
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                row = cur.fetchone()
        if row and row.get("preferred_city"):
            return row["preferred_city"]
    except Exception as e:
        logger.debug(f"[DailyOutfit] 获取用户城市失败: {e}")
    # 默认回退杭州（而非北京），因为大多数用户在杭州
    return "杭州"


def _get_weather_sync(city: str) -> Dict[str, Any]:
    """
    同步获取天气数据（内部调用）

    优先使用真实天气API，失败时回退到季节兜底数据。
    """
    # 尝试复用 weather_forecast 的同步接口获取当天天气
    try:
        from packages.utils.weather_forecast import get_destination_weather
        forecast = get_destination_weather(city, 1)
        if forecast and len(forecast) > 0:
            day = forecast[0]
            from apps.api.routers.weather import get_element_by_weather
            weather_desc = day.get("weather_desc", "晴")
            temp = (day.get("temperature_max", 25) + day.get("temperature_min", 15)) / 2
            element, _ = get_element_by_weather(weather_desc, int(temp))
            return {
                "city": city,
                "temperature": int(temp),
                "temperature_max": day.get("temperature_max", 25),
                "temperature_min": day.get("temperature_min", 15),
                "weather": weather_desc,
                "humidity": day.get("humidity", 60),
                "element": element,
            }
    except Exception as e:
        logger.debug(f"[DailyOutfit] 天气获取失败: {e}")

    # 最终兜底
    return {
        "city": city,
        "temperature": 22,
        "temperature_max": 25,
        "temperature_min": 18,
        "weather": "晴",
        "humidity": 50,
        "element": "土",
    }


def _query_wardrobe(user_id: int) -> List[Dict[str, Any]]:
    """查询用户衣橱"""
    query = """
        SELECT id, user_id, item_code, name, category, image_url,
               primary_element, secondary_element, attributes_detail,
               wear_count, is_favorite, applicable_weather, applicable_seasons,
               temperature_range, functionality, thickness_level, energy_intensity
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 300
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"[DailyOutfit] 衣橱查询失败: {e}")
        return []


def _parse_list(val) -> list:
    """安全解析可能为 JSON 字符串或列表的字段"""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return []
    return []


def _weight_to_score(weight: float) -> float:
    """偏好权重 → 0~1 分数"""
    if weight > 0:
        return min(1.0, 0.5 + weight * 0.1)
    elif weight < 0:
        return max(0.0, 0.5 + weight * 0.1)
    return 0.5


def _empty_result(
    primary_lucky: str,
    lucky_colors: List[str],
    weather: Dict[str, Any],
    fortune: Dict[str, Any],
    today: date,
) -> Dict[str, Any]:
    """衣橱为空时的兜底响应"""
    color_hint = lucky_colors[0] if lucky_colors else "相应"
    return {
        "outfit_items": [],
        "reasoning": f"今日运势偏{primary_lucky}，建议穿着{color_hint}色系衣物增运",
        "weather_summary": {
            "city": weather.get("city", ""),
            "temperature": weather.get("temperature", 22),
            "weather": weather.get("weather", "晴"),
            "element": weather.get("element", "土"),
        },
        "fortune_summary": {
            "lucky_elements": fortune.get("lucky_elements", {}).get("elements", []),
            "lucky_colors": fortune.get("lucky_elements", {}).get("colors", []),
            "overall_score": fortune.get("overall_score", 0),
        },
        "style_tip": f"五行属{primary_lucky}的单品可提升今日运势",
        "match_score": 0,
        "completeness": {
            "has_top": False,
            "has_bottom_or_dress": False,
            "has_shoes": False,
            "has_accessory": False,
            "missing": ["上装", "下装", "鞋履", "配饰"],
        },
        "date": today.isoformat(),
    }
