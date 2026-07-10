"""
旅行穿搭规划器
支持多天行程的穿搭推荐和行李箱容量优化
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from packages.utils.scene_mapping import (
    calculate_scene_match_score,
    get_scene_rules,
    get_sub_scene_rules,
)

logger = logging.getLogger(__name__)


# ============================================================
# 行李箱容量配置
# ============================================================
LUGGAGE_CAPACITY_MAP: Dict[str, int] = {
    "小": 5,   # 登机箱 / 轻装出行
    "中": 10,  # 中型行李箱
    "大": 15,  # 大型行李箱 / 多天长途旅行
}

# 百搭功能关键词，用于识别可复用单品
REUSABLE_FUNCTIONALITY = {"百搭", "轻便", "舒适", "休闲", "抗皱"}

# 品类复用间隔（天数）：0=可全程复用，N=隔N天才能复用，-1=不复用
# 优化：上装/下装/裙装复用间隔从1天提升到2天，确保多日行程有足够多样性
CATEGORY_REUSE_INTERVAL: Dict[str, int] = {
    "外套": 0,   # 外套可全程复用
    "鞋履": 0,   # 鞋履可全程复用
    "配饰": 0,   # 配饰可全程复用
    "上装": 2,   # 上装隔2天才能复用（原为1，优化为2）
    "下装": 2,   # 下装隔2天才能复用（原为1，优化为2）
    "裙装": 2,   # 裙装隔2天才能复用（原为1，优化为2）
    "内衣": -1,  # 内衣不复用
}

# 复用惩罚强度：未用过物品 vs 已用过物品的分数差距
FRESH_ITEM_BONUS = 0.3  # 未使用过的物品获得额外加分，强制优先选新物品


# ============================================================
# 核心函数
# ============================================================

def plan_travel_outfits(
    user_bazi: Optional[Dict],
    destination_weather: List[Dict],
    days: int,
    scenes_per_day: List[str],
    luggage_capacity: str = "中",
    available_items: Optional[List[Dict]] = None,
) -> Dict:
    """
    多天穿搭规划

    根据每天的场景和天气生成穿搭建议，考虑衣物复用和行李箱容量限制。

    Args:
        user_bazi: 用户八字信息（含 suggested_elements 等喜用神）
        destination_weather: 目的地多天天气列表，每项格式:
            {date, temperature_max, temperature_min, weather_desc, humidity, wind_level}
        days: 旅行天数
        scenes_per_day: 每天的场景列表（长度应等于 days）
        luggage_capacity: 行李箱容量 ("小"/"中"/"大")
        available_items: 可选衣物列表（为空时使用模拟数据）

    Returns:
        {
            "days": [
                {
                    "day": int,
                    "scene": str,
                    "weather": dict,
                    "items": [...],
                    "notes": str,
                }
            ],
            "luggage_summary": {
                "total_items": int,
                "categories": {...},
                "reusable_items": [...],
            }
        }
    """
    if days <= 0:
        return {"days": [], "luggage_summary": _empty_luggage_summary()}

    # 如果场景数量不足，自动填充为 "日常"
    if len(scenes_per_day) < days:
        scenes_per_day = list(scenes_per_day) + ["日常"] * (days - len(scenes_per_day))
    elif len(scenes_per_day) > days:
        scenes_per_day = scenes_per_day[:days]

    # 天气列表补齐
    weather_list = _ensure_weather_list(destination_weather, days)

    # 获取喜用神
    target_elements = []
    if user_bazi and isinstance(user_bazi, dict):
        target_elements = user_bazi.get("suggested_elements", [])

    # 获取或生成可用衣物
    items_pool = available_items if available_items else _generate_default_items()

    # 行李箱容量限制
    max_items = LUGGAGE_CAPACITY_MAP.get(luggage_capacity, 10)

    # 为每一天选择衣物
    daily_outfits = []
    selected_items_per_day: List[List[Dict]] = []
    used_item_ids: set = set()
    item_last_used_day: Dict[str, int] = {}  # 物品最后使用天数（用于复用间隔计算）

    for day_idx in range(days):
        scene = scenes_per_day[day_idx]
        weather = weather_list[day_idx]

        # 提取子场景（如果场景包含子场景标记）
        sub_scene = None
        if ":" in scene:
            parts = scene.split(":", 1)
            scene, sub_scene = parts[0], parts[1]

        # 为该天选择最适合的衣物（支持跨天复用）
        day_items = _select_items_for_day(
            items_pool=items_pool,
            scene=scene,
            sub_scene=sub_scene,
            weather=weather,
            target_elements=target_elements,
            used_item_ids=used_item_ids,
            max_per_day=4,
            day_idx=day_idx,
            item_last_used_day=item_last_used_day,
        )

        # 标记已使用（更新复用记录）
        for item in day_items:
            item_id = item.get("id", item.get("name", ""))
            used_item_ids.add(item_id)
            item_last_used_day[item_id] = day_idx

        selected_items_per_day.append(day_items)

        # 生成每日笔记
        notes = _generate_day_notes(scene, sub_scene, weather, day_items, day_idx)

        daily_outfits.append({
            "day": day_idx + 1,
            "scene": scene,
            "sub_scene": sub_scene,
            "weather": weather,
            "items": day_items,
            "notes": notes,
        })

    # 行李箱优化
    optimized = optimize_luggage(daily_outfits, luggage_capacity)

    # 如果总件数超过限制，裁剪
    all_items_flat = _flatten_items(selected_items_per_day)
    if len(all_items_flat) > max_items:
        all_items_flat = _truncate_items(all_items_flat, max_items, target_elements)

    # 计算行李摘要
    luggage_summary = _calculate_luggage_summary(all_items_flat, selected_items_per_day)

    return {
        "days": daily_outfits,
        "luggage_summary": luggage_summary,
    }


def optimize_luggage(outfits_plan: List[Dict], capacity: str = "中") -> List[Dict]:
    """
    行李箱优化

    识别可复用的百搭单品，合并重复类别，优先保留五行匹配度最高的单品。

    Args:
        outfits_plan: 每日穿搭计划列表
        capacity: 行李箱容量

    Returns:
        优化后的每日穿搭计划
    """
    max_items = LUGGAGE_CAPACITY_MAP.get(capacity, 10)

    # 收集所有物品
    all_items: List[Dict] = []
    seen_ids: set = set()

    for day_plan in outfits_plan:
        for item in day_plan.get("items", []):
            item_id = item.get("id", item.get("name", ""))
            if item_id not in seen_ids:
                all_items.append(item)
                seen_ids.add(item_id)

    # 按类别分组，同类中保留五行匹配度最高的
    category_groups: Dict[str, List[Dict]] = {}
    for item in all_items:
        cat = item.get("category", "其他")
        category_groups.setdefault(cat, []).append(item)

    # 每个类别按 wuxing_score 降序排列
    for cat in category_groups:
        category_groups[cat].sort(
            key=lambda x: x.get("wuxing_score", x.get("final_score", 0.5)),
            reverse=True,
        )

    # 识别百搭单品（可复用）
    reusable_items = [
        item for item in all_items
        if _is_reusable(item)
    ]

    # 如果超出限制，保留高分物品
    if len(all_items) > max_items:
        # 优先保留百搭单品
        kept = set()
        for item in reusable_items:
            kept.add(item.get("id", item.get("name", "")))
            if len(kept) >= max_items:
                break

        # 如果还有余量，按分数补充
        remaining = [item for item in all_items if item.get("id", item.get("name", "")) not in kept]
        remaining.sort(
            key=lambda x: x.get("wuxing_score", x.get("final_score", 0.5)),
            reverse=True,
        )
        for item in remaining:
            if len(kept) >= max_items:
                break
            kept.add(item.get("id", item.get("name", "")))

        # 更新每日计划：移除未保留的物品
        for day_plan in outfits_plan:
            day_plan["items"] = [
                item for item in day_plan.get("items", [])
                if item.get("id", item.get("name", "")) in kept
            ]

    return outfits_plan


def calculate_luggage_score(
    items: List[Dict],
    capacity: str = "中",
    daily_items: Optional[List[List[Dict]]] = None,
) -> float:
    """
    行李箱评分
    
    综合评分 = 五行平衡度 30% + 场景覆盖率 20% + 行李紧凑度 20% + 天数覆盖率 30%
    
    Args:
        items: 行李箱中的所有物品列表
        capacity: 行李箱容量
        daily_items: 每天物品列表（用于计算天数覆盖率）

    Returns:
        0.0 - 1.0 的综合评分
    """
    if not items:
        return 0.0

    # 1. 五行平衡度 (30%)
    wuxing_balance = _calculate_wuxing_balance(items)

    # 2. 场景覆盖率 (20%)
    scene_coverage = _calculate_scene_coverage(items)

    # 3. 行李紧凑度 (20%)
    compactness = _calculate_compactness(items, capacity)

    # 4. 天数覆盖率 (30%)
    daily_coverage = 0.5  # 默认值
    if daily_items:
        days_with_enough = sum(1 for day_items in daily_items if len(day_items) >= 2)
        daily_coverage = days_with_enough / len(daily_items) if daily_items else 0.0

    score = (
        wuxing_balance * 0.3 +
        scene_coverage * 0.2 +
        compactness * 0.2 +
        daily_coverage * 0.3
    )
    return round(max(0.0, min(1.0, score)), 3)


# ============================================================
# 内部辅助函数
# ============================================================

def _empty_luggage_summary() -> Dict:
    return {
        "total_items": 0,
        "categories": {},
        "reusable_items": [],
    }


def _ensure_weather_list(weather_list: List[Dict], days: int) -> List[Dict]:
    """确保天气列表长度等于天数，不足时用默认值补齐"""
    if not weather_list:
        return [_default_weather(day_idx) for day_idx in range(days)]

    if len(weather_list) < days:
        last_weather = weather_list[-1]
        for _ in range(days - len(weather_list)):
            weather_list = list(weather_list) + [last_weather.copy()]
    elif len(weather_list) > days:
        weather_list = weather_list[:days]

    return weather_list


def _default_weather(day_offset: int = 0) -> Dict:
    """生成默认天气数据"""
    today = datetime.now() + timedelta(days=day_offset)
    return {
        "date": today.strftime("%Y-%m-%d"),
        "temperature_max": 25,
        "temperature_min": 15,
        "weather_desc": "多云",
        "humidity": 60,
        "wind_level": 2,
    }


def _generate_default_items() -> List[Dict]:
    """生成默认的模拟衣物列表（当未提供可用衣物时使用），覆盖五行+多品类"""
    return [
        # 原始8件
        {"id": 1, "name": "白色商务衬衫", "category": "上装",
         "primary_element": "金", "functionality": ["抗皱", "百搭", "正式"],
         "thickness_level": "适中", "wuxing_score": 0.8, "final_score": 0.85},
        {"id": 2, "name": "黑色西裤", "category": "下装",
         "primary_element": "水", "functionality": ["百搭", "正式"],
         "thickness_level": "适中", "wuxing_score": 0.7, "final_score": 0.75},
        {"id": 3, "name": "休闲T恤", "category": "上装",
         "primary_element": "木", "functionality": ["舒适", "休闲", "百搭"],
         "thickness_level": "轻薄", "wuxing_score": 0.6, "final_score": 0.7},
        {"id": 4, "name": "牛仔裤", "category": "下装",
         "primary_element": "土", "functionality": ["耐磨", "百搭"],
         "thickness_level": "适中", "wuxing_score": 0.65, "final_score": 0.72},
        {"id": 5, "name": "防风外套", "category": "外套",
         "primary_element": "金", "functionality": ["防水", "保暖"],
         "thickness_level": "中厚", "wuxing_score": 0.75, "final_score": 0.78},
        {"id": 6, "name": "速干短袖", "category": "上装",
         "primary_element": "火", "functionality": ["速干", "透气", "防晒"],
         "thickness_level": "轻薄", "wuxing_score": 0.55, "final_score": 0.65},
        {"id": 7, "name": "运动鞋", "category": "鞋履",
         "primary_element": "木", "functionality": ["舒适", "耐磨"],
         "thickness_level": "适中", "wuxing_score": 0.6, "final_score": 0.68},
        {"id": 8, "name": "连衣裙", "category": "裙装",
         "primary_element": "水", "functionality": ["优雅", "舒适"],
         "thickness_level": "轻薄", "wuxing_score": 0.7, "final_score": 0.72},
        # 新增8件（覆盖五行+品类）
        {"id": 9, "name": "针织开衫", "category": "外套",
         "primary_element": "土", "functionality": ["保暖", "百搭", "舒适"],
         "thickness_level": "适中", "wuxing_score": 0.65, "final_score": 0.70},
        {"id": 10, "name": "丝绒半裙", "category": "裙装",
         "primary_element": "火", "functionality": ["优雅", "时尚"],
         "thickness_level": "适中", "wuxing_score": 0.68, "final_score": 0.73},
        {"id": 11, "name": "棉麻衬衫", "category": "上装",
         "primary_element": "木", "functionality": ["透气", "休闲", "百搭"],
         "thickness_level": "轻薄", "wuxing_score": 0.62, "final_score": 0.68},
        {"id": 12, "name": "皮革腰带", "category": "配饰",
         "primary_element": "金", "functionality": ["百搭", "正式"],
         "thickness_level": "适中", "wuxing_score": 0.5, "final_score": 0.60},
        {"id": 13, "name": "羊毛围巾", "category": "配饰",
         "primary_element": "土", "functionality": ["保暖", "百搭"],
         "thickness_level": "适中", "wuxing_score": 0.55, "final_score": 0.62},
        {"id": 14, "name": "卡其休闲裤", "category": "下装",
         "primary_element": "土", "functionality": ["百搭", "休闲", "舒适"],
         "thickness_level": "适中", "wuxing_score": 0.6, "final_score": 0.68},
        {"id": 15, "name": "皮靴", "category": "鞋履",
         "primary_element": "金", "functionality": ["保暖", "百搭", "正式"],
         "thickness_level": "中厚", "wuxing_score": 0.65, "final_score": 0.70},
        {"id": 16, "name": "真丝丝巾", "category": "配饰",
         "primary_element": "水", "functionality": ["优雅", "百搭"],
         "thickness_level": "轻薄", "wuxing_score": 0.58, "final_score": 0.65},
    ]


def _select_items_for_day(
    items_pool: List[Dict],
    scene: str,
    sub_scene: Optional[str],
    weather: Dict,
    target_elements: List[str],
    used_item_ids: set,
    max_per_day: int = 4,
    day_idx: int = 0,
    item_last_used_day: Optional[Dict[str, int]] = None,
) -> List[Dict]:
    """为某一天选择最佳穿搭物品（支持跨天复用）"""
    if item_last_used_day is None:
        item_last_used_day = {}
    
    scored_items = []

    for item in items_pool:
        item_id = item.get("id", item.get("name", ""))
        category = item.get("category", "")

        # 场景匹配度评分
        scene_score = calculate_scene_match_score(item, scene, sub_scene)

        # 五行匹配度评分
        wuxing_score = item.get("wuxing_score", item.get("final_score", 0.5))
        if target_elements:
            item_element = item.get("primary_element", "")
            if item_element in target_elements:
                wuxing_score = min(1.0, wuxing_score + 0.15)

        # 天气适配评分
        weather_score = _weather_item_score(item, weather)

        # 跨天复用惩罚分（优化：加强惩罚 + 新品加分）
        reuse_penalty = 0.0
        fresh_bonus = 0.0
        reuse_interval = CATEGORY_REUSE_INTERVAL.get(category, 1)
        if item_id in used_item_ids:
            if reuse_interval == -1:
                # 不复用的品类，跳过
                continue
            elif reuse_interval == 0:
                # 可全程复用，无惩罚（外套/鞋履/配饰）
                pass
            else:
                last_day = item_last_used_day.get(item_id, -999)
                gap = day_idx - last_day
                if gap < reuse_interval:
                    # 未达到复用间隔，施加强惩罚（原为0.3，优化为0.6）
                    reuse_penalty = 0.6 * (reuse_interval - gap) / reuse_interval
                else:
                    # 已过复用间隔，但仍比全新物品分数低
                    reuse_penalty = 0.1
        else:
            # 全新物品，给予额外加分，强制优先选择未使用过的物品
            fresh_bonus = FRESH_ITEM_BONUS

        # 综合评分 = 场景*0.4 + 五行*0.35 + 天气*0.25 - 复用惩罚 + 新品加分
        total_score = scene_score * 0.4 + wuxing_score * 0.35 + weather_score * 0.25 - reuse_penalty + fresh_bonus

        scored_items.append({
            "item": item,
            "score": total_score,
            "scene_score": scene_score,
            "wuxing_score": wuxing_score,
            "weather_score": weather_score,
        })

    # 按综合评分降序
    scored_items.sort(key=lambda x: x["score"], reverse=True)

    # 选择不同类别的物品，优先选高分
    selected = []
    selected_categories = set()

    for scored in scored_items:
        item = scored["item"]
        category = item.get("category", "")
        item_id = item.get("id", item.get("name", ""))

        # 百搭单品可复用
        if item_id in used_item_ids and not _is_reusable(item):
            # 检查是否因复用间隔可复用
            reuse_interval = CATEGORY_REUSE_INTERVAL.get(category, 1)
            if reuse_interval == -1:
                continue
            elif reuse_interval > 0:
                last_day = item_last_used_day.get(item_id, -999)
                if day_idx - last_day < reuse_interval:
                    continue

        # 每个类别最多选1件（除非还有余量）
        if category in selected_categories:
            if len(selected) < max_per_day:
                selected.append(_format_item_output(item, scored))
            continue

        selected.append(_format_item_output(item, scored))
        selected_categories.add(category)

        if len(selected) >= max_per_day:
            break

    return selected


def _format_item_output(item: Dict, scored: Dict) -> Dict:
    """格式化输出物品"""
    return {
        "id": item.get("id"),
        "name": item.get("name", ""),
        "category": item.get("category", ""),
        "primary_element": item.get("primary_element", ""),
        "final_score": round(scored["score"], 3),
        "scene_score": round(scored["scene_score"], 3),
        "wuxing_score": round(scored["wuxing_score"], 3),
        "weather_score": round(scored["weather_score"], 3),
    }


def _weather_item_score(item: Dict, weather: Dict) -> float:
    """根据天气评估物品适配度（带强烈温度惩罚）"""
    score = 0.5
    weather_desc = weather.get("weather_desc", "")
    temp_max = weather.get("temperature_max", 25)
    temp_min = weather.get("temperature_min", 15)
    avg_temp = (temp_max + temp_min) / 2

    thickness = item.get("thickness_level", "")
    functionality = _parse_functionality(item.get("functionality", []))

    # ===== 温度适配（核心逻辑，强惩罚）=====
    # 高温场景（>=28°C）
    if avg_temp >= 28:
        if thickness in ("轻薄", "极薄"):
            score += 0.2
        elif thickness == "适中":
            score += 0.05
        elif thickness in ("中厚", "厚重"):
            score -= 0.5  # 强烈惩罚！32°C不应推荐羽绒服/厚外套
        if any(f in functionality for f in ["透气", "速干", "防晒"]):
            score += 0.15
        if any(f in functionality for f in ["保暖", "防风"]):
            score -= 0.2  # 高温天推荐保暖功能不合理

    # 低温场景（<=10°C）
    elif avg_temp <= 10:
        if thickness in ("厚重", "中厚"):
            score += 0.2
        elif thickness == "适中":
            score += 0.05
        elif thickness in ("极薄", "轻薄"):
            score -= 0.4  # 寒冷天不应推荐极薄衣物
        if "保暖" in functionality:
            score += 0.2
        if any(f in functionality for f in ["防风"]):
            score += 0.1

    # 适中温度（10-28°C）
    else:
        if thickness == "适中":
            score += 0.15
        elif thickness in ("轻薄", "中厚"):
            score += 0.05

    # ===== 天气状况加分 =====
    if any(kw in weather_desc for kw in ["雨", "雪"]):
        if "防水" in functionality:
            score += 0.15
        # 雨雪天不推荐丝绸/真丝
        if "丝绸" in str(item.get("name", "")) or "真丝" in str(item.get("name", "")):
            score -= 0.2

    return max(0.0, min(1.0, score))


def _parse_functionality(functionality) -> list:
    """解析功能性字段（兼容 list/dict/str 格式）"""
    if isinstance(functionality, str):
        import json
        try:
            functionality = json.loads(functionality)
        except Exception:
            return []
    if isinstance(functionality, dict):
        return [k for k, v in functionality.items() if v]
    if isinstance(functionality, list):
        return functionality
    return []


def _is_reusable(item: Dict) -> bool:
    """判断物品是否是百搭可复用单品"""
    functionality = item.get("functionality", [])
    if isinstance(functionality, str):
        import json
        try:
            functionality = json.loads(functionality)
        except Exception:
            functionality = []

    if isinstance(functionality, list):
        return any(f in REUSABLE_FUNCTIONALITY for f in functionality)
    elif isinstance(functionality, dict):
        return any(functionality.get(f) for f in REUSABLE_FUNCTIONALITY)
    return False


def _generate_day_notes(
    scene: str,
    sub_scene: Optional[str],
    weather: Dict,
    items: List[Dict],
    day_idx: int = 0,
) -> str:
    """生成每日穿搭建议笔记"""
    weather_desc = weather.get("weather_desc", "未知")
    temp_max = weather.get("temperature_max", "?")
    temp_min = weather.get("temperature_min", "?")

    scene_label = f"{scene}" + (f"（{sub_scene}）" if sub_scene else "")
    notes = f"第{day_idx + 1}天，{scene_label}，天气{weather_desc}，{temp_min}~{temp_max}°C。"

    if items:
        categories = [item.get("category", "") for item in items]
        notes += f"推荐{len(items)}件：{'、'.join(categories)}。"
    else:
        notes += "暂无推荐物品。"

    return notes


def _flatten_items(items_per_day: List[List[Dict]]) -> List[Dict]:
    """将多天物品列表展平为唯一物品列表"""
    seen = set()
    flat = []
    for day_items in items_per_day:
        for item in day_items:
            item_id = item.get("id", item.get("name", ""))
            if item_id not in seen:
                flat.append(item)
                seen.add(item_id)
    return flat


def _truncate_items(items: List[Dict], max_count: int, target_elements: List[str]) -> List[Dict]:
    """截断物品列表到指定数量，优先保留五行匹配度高的"""
    sorted_items = sorted(
        items,
        key=lambda x: x.get("wuxing_score", x.get("final_score", 0.5)),
        reverse=True,
    )
    return sorted_items[:max_count]


def _calculate_luggage_summary(
    all_items: List[Dict],
    items_per_day: List[List[Dict]],
) -> Dict:
    """计算行李箱摘要"""
    # 类别统计
    categories: Dict[str, int] = {}
    for item in all_items:
        cat = item.get("category", "其他")
        categories[cat] = categories.get(cat, 0) + 1

    # 可复用物品
    reusable = [item for item in all_items if _is_reusable(item)]

    return {
        "total_items": len(all_items),
        "categories": categories,
        "reusable_items": [
            {"name": item.get("name", ""), "category": item.get("category", "")}
            for item in reusable
        ],
    }


def _calculate_wuxing_balance(items: List[Dict]) -> float:
    """计算五行平衡度"""
    if not items:
        return 0.0

    element_counts: Dict[str, int] = {}
    for item in items:
        element = item.get("primary_element", "")
        if element:
            element_counts[element] = element_counts.get(element, 0) + 1

    if not element_counts:
        return 0.3

    # 五行覆盖数量
    covered = len(element_counts)
    max_balance = min(len(items), 5)

    if max_balance == 0:
        return 0.0

    # 覆盖比例
    coverage_ratio = covered / 5.0

    # 分布均匀度（方差越小越均匀）
    counts = list(element_counts.values())
    avg = sum(counts) / len(counts)
    variance = sum((c - avg) ** 2 for c in counts) / len(counts)
    uniformity = 1.0 / (1.0 + variance)

    return round(coverage_ratio * 0.6 + uniformity * 0.4, 3)


def _calculate_scene_coverage(items: List[Dict]) -> float:
    """计算场景覆盖率"""
    if not items:
        return 0.0

    covered_scenes = set()
    for item in items:
        functionality = item.get("functionality", [])
        if isinstance(functionality, list):
            for f in functionality:
                if f in ("正式", "百搭"):
                    covered_scenes.add("商务")
                if f in ("休闲", "舒适"):
                    covered_scenes.add("日常")
                if f in ("防水", "耐磨"):
                    covered_scenes.add("户外")
                if f in ("防晒", "速干"):
                    covered_scenes.add("度假")
                if f in ("时尚", "优雅"):
                    covered_scenes.add("约会")

    # 目标覆盖5大场景
    return min(1.0, len(covered_scenes) / 5.0)


def _calculate_compactness(items: List[Dict], capacity: str) -> float:
    """计算行李紧凑度"""
    max_items = LUGGAGE_CAPACITY_MAP.get(capacity, 10)
    actual = len(items)

    if actual == 0:
        return 0.0

    if actual <= max_items:
        # 使用率越高，紧凑度越高
        return round(actual / max_items, 3)
    else:
        # 超出容量，紧凑度递减
        overflow = actual - max_items
        return round(max(0.0, 1.0 - overflow * 0.1), 3)
