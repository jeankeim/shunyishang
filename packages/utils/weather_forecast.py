"""
目的地天气预测
获取多天天气预报用于旅行推荐
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

import httpx

from apps.api.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# 城市ID映射（复用 weather.py 中的映射，保持一致性）
# ============================================================
CITY_ID_MAP = {
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280101",
    "深圳": "101280601",
    "杭州": "101210101",
    "成都": "101270101",
    "南京": "101190101",
    "武汉": "101200101",
    "西安": "101110101",
    "重庆": "101040100",
    "天津": "101030100",
    "苏州": "101190401",
    "厦门": "101230201",
    "青岛": "101120201",
    "大连": "101070201",
    "宁波": "101210401",
    "郑州": "101180101",
    "长沙": "101250101",
    "福州": "101230101",
    "哈尔滨": "101050101",
    "三亚": "101310301",
    "拉萨": "101140101",
    "昆明": "101290101",
    "海口": "101310101",
}


# ============================================================
# 扩展天气-五行映射表（在 weather.py 的基础上新增）
# ============================================================
EXTENDED_WEATHER_ELEMENT_MAP: Dict[str, str] = {
    # 原有映射（保持与 weather.py 一致）
    "雨": "水",
    "雪": "水",
    "雾": "水",
    "霾": "水",
    "小雨": "水",
    "中雨": "水",
    "大雨": "水",
    "雷阵雨": "水",
    "晴": "火",
    "热": "火",
    "高温": "火",
    "干旱": "火",
    "多云": "木",
    "阴": "木",
    "微风": "木",
    "凉": "金",
    "冷": "金",
    "大风": "金",
    "台风": "金",
    "沙尘": "土",
    "浮尘": "土",
    "闷热": "土",
    # 新增映射
    "雾天": "金",
    "雷暴": "木",
    "沙尘暴": "土",
    "浮尘天": "土",
}


# 季节默认天气（API失败时的兜底数据）
SEASON_DEFAULT_WEATHER: Dict[str, Tuple[str, int, int]] = {
    "春": ("多云", 22, 12),
    "夏": ("晴", 32, 24),
    "秋": ("晴", 20, 10),
    "冬": ("阴", 8, -2),
}


# ============================================================
# 核心函数
# ============================================================

def get_destination_weather(city: str, days: int = 7) -> List[Dict]:
    """
    获取目的地多天天气

    使用和风天气API获取天气预报，API失败时提供基于季节的默认天气兜底。

    Args:
        city: 城市名称
        days: 预测天数

    Returns:
        天气列表，每项格式:
        {date, temperature_max, temperature_min, weather_desc, humidity, wind_level}
    """
    if days <= 0:
        return []

    # 尝试调用天气API
    weather_api_key = getattr(settings, 'weather_api_key', None)
    city_id = CITY_ID_MAP.get(city)

    if weather_api_key and city_id:
        try:
            forecast = _fetch_weather_from_api(city, city_id, weather_api_key, days)
            if forecast:
                logger.info(f"[天气预测] API成功获取 {city} {len(forecast)} 天天气")
                return forecast
        except Exception as e:
            logger.warning(f"[天气预测] API调用失败: {e}，使用兜底数据")

    # API失败或未配置，使用兜底数据
    logger.info(f"[天气预测] 使用季节兜底数据: {city}")
    return _generate_fallback_weather(city, days)


def predict_weather_element(weather_desc: str) -> str:
    """
    天气描述转五行元素

    扩展映射表，新增：雾天→金、雷暴→木、沙尘→土

    Args:
        weather_desc: 天气描述文本

    Returns:
        五行元素字符串 (金/木/水/火/土)，未匹配返回 "土"
    """
    if not weather_desc:
        return "土"

    # 按 key 长度降序匹配，确保更具体的关键词优先（如"雾天"优先于"雾"）
    for keyword in sorted(EXTENDED_WEATHER_ELEMENT_MAP.keys(), key=len, reverse=True):
        if keyword in weather_desc:
            return EXTENDED_WEATHER_ELEMENT_MAP[keyword]

    # 默认返回土
    return "土"


# ============================================================
# 内部辅助函数
# ============================================================

def _fetch_weather_from_api(
    city: str,
    city_id: str,
    api_key: str,
    days: int,
) -> List[Dict]:
    """从和风天气API获取多天天气预报"""
    import asyncio

    async def _fetch():
        api_host = "nh6pg8qvv4.re.qweatherapi.com"
        headers = {"X-QW-Api-Key": api_key}

        # 使用 7d 或 3d 预报接口
        endpoint = "/v7/weather/7d" if days > 3 else "/v7/weather/3d"

        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://{api_host}{endpoint}"
            params = {"location": city_id}
            response = await client.get(url, params=params, headers=headers)
            data = response.json()

            if data.get("code") != "200":
                logger.warning(f"[天气预测] API返回错误: {data.get('code')}")
                return []

            daily = data.get("daily", [])
            result = []

            for i, day_data in enumerate(daily[:days]):
                result.append({
                    "date": day_data.get("fxDate", ""),
                    "temperature_max": int(day_data.get("tempMax", 25)),
                    "temperature_min": int(day_data.get("tempMin", 15)),
                    "weather_desc": day_data.get("textDay", "多云"),
                    "humidity": int(day_data.get("humidity", 60)),
                    "wind_level": _parse_wind_scale(day_data.get("windScaleDay", "2")),
                })

            return result

    # 在同步上下文中运行异步函数
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 已有运行中的事件循环，创建新线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _fetch())
                return future.result()
        else:
            return loop.run_until_complete(_fetch())
    except RuntimeError:
        return asyncio.run(_fetch())


def _parse_wind_scale(scale_str: str) -> int:
    """解析风力等级（可能格式如 "2" 或 "2-3"）"""
    try:
        if "-" in scale_str:
            parts = scale_str.split("-")
            return int(parts[0])
        return int(scale_str)
    except (ValueError, IndexError):
        return 2


def _generate_fallback_weather(city: str, days: int) -> List[Dict]:
    """基于季节生成兜底天气数据"""
    now = datetime.now()
    month = now.month

    # 判断季节
    if 3 <= month <= 5:
        season = "春"
    elif 6 <= month <= 8:
        season = "夏"
    elif 9 <= month <= 11:
        season = "秋"
    else:
        season = "冬"

    base_weather, temp_max, temp_min = SEASON_DEFAULT_WEATHER.get(season, ("多云", 22, 12))

    # 城市微调
    city_adjust = _get_city_temperature_adjust(city)
    temp_max += city_adjust
    temp_min += city_adjust

    result = []
    for i in range(days):
        date = (now + timedelta(days=i)).strftime("%Y-%m-%d")

        # 模拟天气变化（每隔一天有微小变化）
        weather = base_weather
        if i > 0 and i % 3 == 0:
            if season == "夏":
                weather = "雷阵雨"
            elif season == "冬":
                weather = "阴"
            else:
                weather = "多云"

        day_temp_max = temp_max + (i % 3 - 1)
        day_temp_min = temp_min + (i % 3 - 1)

        result.append({
            "date": date,
            "temperature_max": day_temp_max,
            "temperature_min": day_temp_min,
            "weather_desc": weather,
            "humidity": 50 + (i % 3) * 10,
            "wind_level": 1 + (i % 3),
        })

    return result


def _get_city_temperature_adjust(city: str) -> int:
    """根据城市进行温度微调"""
    south_cities = {"三亚", "海口", "广州", "深圳", "厦门"}
    north_cities = {"哈尔滨", "北京", "大连", "拉萨"}

    if city in south_cities:
        return 5
    elif city in north_cities:
        return -5
    return 0
