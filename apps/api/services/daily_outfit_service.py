"""
每日智能穿搭推荐服务

基于用户八字命理、当日运势、实时天气、季节、个人偏好和衣橱库存，
自动生成3-5件完整搭配建议，实现"打开即见"的个性化穿搭体验。
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.services.user_service import get_user_bazi
from apps.api.services.fortune_engine import calculate_daily_fortune
from apps.api.services.preference_service import preference_service
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

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

# ── 温度 → 厚度适配 ──────────────────────────────────────────────────────────
THICKNESS_HOT = {"轻薄", "极薄"}        # >=28°C
THICKNESS_MILD = {"轻薄", "适中"}       # 15-27°C
THICKNESS_COLD = {"适中", "中厚", "厚重"}  # <=14°C


# ─────────────────────────────────────────────────────────────────────────────
# 公共入口
# ─────────────────────────────────────────────────────────────────────────────

def generate_daily_outfit(
    user_id: int,
    batch_index: int = 0,
    city_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成每日智能穿搭建议

    Args:
        user_id: 用户 ID
        batch_index: 换一批批次 (0-2)
        city_override: 前端定位城市（优先于用户设置）

    Returns:
        {
            "outfit_items": [...],
            "reasoning": "...",
            "weather_summary": {...},
            "fortune_summary": {...},
            "style_tip": "...",
            "match_score": int,
        }
    """
    today = date.today()
    season = SEASON_MAP.get(today.month, "秋")

    # ── 1. 用户八字 + 运势 ────────────────────────────────────────────────
    user_bazi = get_user_bazi(user_id)
    fortune = calculate_daily_fortune(user_bazi, today)

    lucky_elements: List[str] = fortune.get("lucky_elements", {}).get("elements", [])
    lucky_colors: List[str] = fortune.get("lucky_elements", {}).get("colors", [])
    suggested_elements: List[str] = user_bazi.get("suggested_elements", [])
    avoid_elements: List[str] = user_bazi.get("avoid_elements", [])
    primary_lucky = lucky_elements[0] if lucky_elements else (suggested_elements[0] if suggested_elements else "土")

    # ── 2. 天气（优先使用前端定位城市，确保与首页天气显示一致）───────────────
    city = city_override or _get_user_city(user_id)
    weather = _get_weather_sync(city)
    temperature = weather.get("temperature", 22)
    weather_desc = weather.get("weather", "晴")
    weather_element = weather.get("element", "土")

    # ── 3. 用户偏好 ────────────────────────────────────────────────────────
    user_prefs = {}
    try:
        user_prefs = preference_service.get_user_preferences(user_id)
    except Exception as e:
        logger.warning(f"[DailyOutfit] 偏好获取失败: {e}")

    # ── 4. 查询衣橱 ────────────────────────────────────────────────────────
    wardrobe_items = _query_wardrobe(user_id)
    if not wardrobe_items:
        return _empty_result(primary_lucky, lucky_colors, weather, fortune, today)

    # ── 5. 多维度评分 ──────────────────────────────────────────────────────
    scored = []
    for item in wardrobe_items:
        score = _score_item(
            item=item,
            lucky_elements=lucky_elements,
            lucky_colors=lucky_colors,
            suggested_elements=suggested_elements,
            avoid_elements=avoid_elements,
            temperature=temperature,
            weather_element=weather_element,
            season=season,
            user_prefs=user_prefs,
        )
        scored.append((item, score))

    # 按分数降序
    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 6. 品类多样性选择 ──────────────────────────────────────────────────
    outfit_items = _select_diverse_items(scored, target_count=5, batch_index=batch_index)

    # ── 7. 构建响应 ────────────────────────────────────────────────────────
    if not outfit_items:
        return _empty_result(primary_lucky, lucky_colors, weather, fortune, today)

    total_score = sum(s for _, s in scored if any(
        o.get("id") == _["id"] for o in outfit_items for _ in [o]
    ))
    # 简化：取选中物品的平均分的整数形式
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
            "city": city,
            "temperature": temperature,
            "weather": weather_desc,
            "element": weather_element,
        },
        "fortune_summary": {
            "lucky_elements": lucky_elements,
            "lucky_colors": lucky_colors,
            "overall_score": fortune.get("overall_score", 0),
        },
        "style_tip": style_tip,
        "match_score": min(avg_score, 100),
        "date": today.isoformat(),
    }


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
) -> int:
    """
    多维度评分 (0-100)

    权重分配:
    - 五行匹配 30%  (喜用神 + 当日幸运元素)
    - 天气适配 25%  (温度→厚度 + 功能性)
    - 季节匹配 15%
    - 用户偏好 20%
    - 穿搭新鲜度 10% (wear_count 低的加分)
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

    total = wuxing_score + weather_score + season_score + pref_score + freshness + color_bonus
    return max(0, min(100, total))


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
# 品类多样性选择
# ─────────────────────────────────────────────────────────────────────────────

def _select_diverse_items(
    scored: List[tuple],
    target_count: int = 5,
    batch_index: int = 0,
) -> List[Dict[str, Any]]:
    """
    从评分结果中选择品类多样化的物品

    策略：
    - 每个品类不超过 CATEGORY_MAX_PER_OUTFIT 限制
    - 优先确保 上装+下装 或 裙装 的核心搭配
    - 配饰/鞋履作为补充
    - 换一批：逐批模拟并排除前序批次已选物品，保证批次间不重合；
      候选耗尽时回退复用已展示物品
    """
    excluded_ids: set = set()
    selected: List[Dict[str, Any]] = []

    for _ in range(batch_index + 1):
        selected = _pick_one_batch(scored, target_count, excluded_ids)
        if not selected and excluded_ids:
            # 候选耗尽：回退复用已展示物品
            excluded_ids.clear()
            selected = _pick_one_batch(scored, target_count, excluded_ids)
        excluded_ids.update(item["id"] for item in selected)

    return selected


def _pick_one_batch(
    scored: List[tuple],
    target_count: int,
    excluded_ids: set,
) -> List[Dict[str, Any]]:
    """从评分结果中选出一批物品（跳过已排除 id，遵守品类限制）"""
    selected: List[Dict[str, Any]] = []
    category_count: Dict[str, int] = {}

    for item, score in scored:
        if item.get("id") in excluded_ids:
            continue

        category = item.get("category") or "其他"
        current = category_count.get(category, 0)
        max_allowed = CATEGORY_MAX_PER_OUTFIT.get(category, 1)

        if current >= max_allowed:
            continue

        payload = _format_item(item, score)
        selected.append(payload)
        category_count[category] = current + 1

        if len(selected) >= target_count:
            break

    return selected


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
        "date": today.isoformat(),
    }
