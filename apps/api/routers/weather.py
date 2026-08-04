"""
天气 API 路由
提供天气查询和天气-五行映射功能
"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
import httpx
import logging

from apps.api.core.config import settings
from apps.api.core.cache import cache
from packages.utils.city_resolver import (
    CITY_ID_MAP,
    resolve_city_id,
    search_cities,
    reverse_geocode,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class WeatherResponse(BaseModel):
    """天气响应"""
    city: str
    temperature: int  # 温度
    temperature_max: Optional[int] = None  # 当日最高温（推荐链路用于有效温度判断）
    weather: str      # 天气描述
    humidity: int     # 湿度
    wind: str         # 风向风力
    element: str      # 对应五行
    element_reason: str  # 五行映射原因


# 城市ID映射表已迁移至 packages/utils/city_resolver.py（单一数据源，
# 支持内置 120+ 城市 + 和风城市搜索 API 动态解析全国市县）


# 天气到五行的映射规则
WEATHER_ELEMENT_MAP = {
    # 水：雨、雪、潮湿
    "雨": ("水", "雨水滋润，五行属水"),
    "雪": ("水", "冰雪寒冷，五行属水"),
    "雾": ("水", "雾气湿润，五行属水"),
    "霾": ("水", "湿霾阴沉，五行属水"),
    "小雨": ("水", "细雨滋润，五行属水"),
    "中雨": ("水", "雨水充沛，五行属水"),
    "大雨": ("水", "暴雨倾盆，五行属水"),
    "雷阵雨": ("水", "雷雨交加，五行属水"),
    
    # 火：晴、热、干燥
    "晴": ("火", "阳光明媚，五行属火"),
    "热": ("火", "炎热干燥，五行属火"),
    "高温": ("火", "烈日炎炎，五行属火"),
    "干旱": ("火", "燥热干旱，五行属火"),
    
    # 木：多云、阴天、温和
    "多云": ("木", "云卷云舒，生机盎然，五行属木"),
    "阴": ("木", "阴云密布，万物生长，五行属木"),
    "微风": ("木", "和风拂面，五行属木"),
    
    # 金：凉爽、干燥、秋风
    "凉": ("金", "秋高气爽，五行属金"),
    "冷": ("金", "寒冷肃杀，五行属金"),
    "大风": ("金", "金风送爽，五行属金"),
    "台风": ("金", "狂风骤起，五行属金"),
    
    # 土：雾霾、沙尘、闷热
    "沙尘": ("土", "沙尘漫天，五行属土"),
    "浮尘": ("土", "尘土飞扬，五行属土"),
    "闷热": ("土", "湿热交蒸，五行属土"),
}


def get_element_by_weather(weather: str, temperature: int) -> tuple[str, str]:
    """
    根据天气和温度判断五行
    
    Args:
        weather: 天气描述
        temperature: 温度
        
    Returns:
        tuple: (五行, 原因)
    """
    # 先匹配天气关键词
    for key, (element, reason) in WEATHER_ELEMENT_MAP.items():
        if key in weather:
            return element, reason
    
    # 根据温度判断
    if temperature >= 30:
        return "火", f"气温{temperature}°C，炎热属火"
    elif temperature <= 10:
        return "金", f"气温{temperature}°C，寒冷属金"
    elif 20 <= temperature <= 28:
        return "木", f"气温{temperature}°C，温和舒适属木"
    elif "雨" in weather or "湿" in weather:
        return "水", "湿润多雨属水"
    else:
        return "土", f"气温{temperature}°C，天气平稳属土"


@router.get("/weather", response_model=WeatherResponse, summary="获取天气")
async def get_weather(
    city: Optional[str] = Query(default="北京", description="城市名称或城市ID")
):
    """
    获取指定城市的天气信息，并映射到五行
    
    **源码位置**: `apps/api/routers/weather.py:get_weather()` (第118行起)
    
    **核心逻辑**:
    1. 优先从缓存读取天气数据
    2. 如有配置 `WEATHER_API_KEY`，调用和风天气API
    3. 否则使用模拟数据（开发测试用）
    4. 根据天气和温度映射到五行
    
    **天气五行映射规则**:
    - 水：雨、雪、雾、潮湿
    - 火：晴、热、干燥、高温
    - 木：多云、阴天、温和
    - 金：凉爽、干燥、秋风、寒冷
    - 土：雾霾、沙尘、闷热
    
    **依赖**: `get_element_by_weather()` - 天气到五行的映射函数
    """
    # 尝试读取缓存
    cache_key = f"weather:{city}"
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"[Cache] 天气缓存命中: {city}")
        return WeatherResponse(**cached)
    
    # 检查是否有天气API配置
    weather_api_key = getattr(settings, 'weather_api_key', None)
    
    if not weather_api_key:
        # 未配置API Key，使用模拟数据
        logger.warning("[Weather] 未配置天气API Key，使用模拟数据")
        use_mock_data = True
    else:
        logger.info("[Weather] 天气API Key已配置，使用真实数据")
        use_mock_data = False
    
    if use_mock_data:
        mock_data = {
            "北京": ("晴", 22, 28, 45, "南风2级"),
            "上海": ("多云", 25, 30, 60, "东南风3级"),
            "广州": ("小雨", 28, 33, 80, "南风2级"),
            "深圳": ("雷阵雨", 30, 34, 85, "西南风3级"),
            "杭州": ("阴", 24, 29, 70, "东风2级"),
            "成都": ("多云", 23, 27, 65, "北风1级"),
        }
        
        weather, temp, temp_max, humidity, wind = mock_data.get(city, ("晴", 22, 27, 50, "微风"))
        element, reason = get_element_by_weather(weather, temp)
        
        result = WeatherResponse(
            city=city,
            temperature=temp,
            temperature_max=temp_max,
            weather=weather,
            humidity=humidity,
            wind=wind,
            element=element,
            element_reason=reason
        )
        
        # 写入缓存
        await cache.set(cache_key, result.model_dump(), ttl=1800)  # 缓存30分钟
        return result
    
    # 调用真实天气API
    try:
        logger.info(f"[API] 调用和风天气API: {city}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 使用自定义API Host和官方认证方式
            api_host = "nh6pg8qvv4.re.qweatherapi.com"
            headers = {
                "X-QW-Api-Key": weather_api_key
            }
            
            # 先查找城市ID：内置映射表 → 和风城市搜索API动态解析（全国市县）
            city_id = CITY_ID_MAP.get(city)
            if not city_id:
                logger.info(f"[API] 城市 {city} 不在预置列表中，尝试动态解析")
                city_id = await resolve_city_id(city, weather_api_key)
            if not city_id:
                # 解析失败，尝试用城市名作为location参数调用API（和风支持部分城市名/adcode）
                logger.info(f"[API] 城市 {city} 动态解析失败，直接以城市名查询")
                city_id = city
            
            weather_url = f"https://{api_host}/v7/weather/now"
            weather_params = {
                "location": city_id,  # 使用城市ID
            }
            
            weather_response = await client.get(weather_url, params=weather_params, headers=headers)
            weather_data = weather_response.json()
            
            if weather_data.get("code") != "200":
                # 如果城市名称失败，尝试使用模拟数据
                logger.warning(f"[API] 天气API返回错误: {weather_data.get('code')}, 使用模拟数据")
                raise Exception("API调用失败，使用模拟数据")
            
            now = weather_data["now"]
            temp = int(now["temp"])
            weather_desc = now["text"]
            humidity = int(now["humidity"])
            wind = f"{now['windDir']}{now['windScale']}级"
            
            # 补查当日最高温（实时接口不含，取 3 天预报首日 tempMax），失败不阻断主流程
            temp_max = None
            try:
                forecast_url = f"https://{api_host}/v7/weather/3d"
                forecast_response = await client.get(
                    forecast_url, params=weather_params, headers=headers
                )
                forecast_data = forecast_response.json()
                if forecast_data.get("code") == "200" and forecast_data.get("daily"):
                    temp_max = int(forecast_data["daily"][0]["tempMax"])
            except Exception as fe:
                logger.warning(f"[API] 获取当日最高温失败: {fe}")
            
            element, reason = get_element_by_weather(weather_desc, temp)
            
            result = WeatherResponse(
                city=city,
                temperature=temp,
                temperature_max=temp_max,
                weather=weather_desc,
                humidity=humidity,
                wind=wind,
                element=element,
                element_reason=reason
            )
            
            # 写入缓存
            await cache.set(cache_key, result.model_dump(), ttl=1800)  # 缓存30分钟
            return result
    
    except httpx.TimeoutException:
        logger.warning("[API] 天气API超时，使用模拟数据")
    except Exception as e:
        logger.warning(f"[API] 天气API异常: {e}，使用模拟数据")
    
    # API调用失败，返回模拟数据
    logger.info(f"[Mock] 使用模拟天气数据: {city}")
    mock_data = {
        "北京": ("晴", 22, 28, 45, "南风2级"),
        "上海": ("多云", 25, 30, 60, "东南风3级"),
        "广州": ("小雨", 28, 33, 80, "南风2级"),
        "深圳": ("雷阵雨", 30, 34, 85, "西南风3级"),
        "杭州": ("阴", 24, 29, 70, "东风2级"),
        "成都": ("多云", 23, 27, 65, "北风1级"),
    }
    
    weather, temp, temp_max, humidity, wind = mock_data.get(city, ("晴", 22, 27, 50, "微风"))
    element, reason = get_element_by_weather(weather, temp)
    
    result = WeatherResponse(
        city=city,
        temperature=temp,
        temperature_max=temp_max,
        weather=weather,
        humidity=humidity,
        wind=wind,
        element=element,
        element_reason=reason
    )
    
    # 写入缓存
    await cache.set(cache_key, result.model_dump(), ttl=1800)  # 缓存30分钟
    return result


@router.get("/weather/elements", summary="获取天气五行映射")
async def get_weather_elements():
    """
    获取天气到五行的映射规则
    
    **源码位置**: `apps/api/routers/weather.py:get_weather_elements()` (第260行起)
    
    **用途**: 返回天气关键词到五行的映射字典，供前端展示
    """
    return {
        "水": ["雨", "雪", "雾", "霾", "小雨", "中雨", "大雨", "雷阵雨"],
        "火": ["晴", "热", "高温", "干旱"],
        "木": ["多云", "阴", "微风"],
        "金": ["凉", "冷", "大风", "台风"],
        "土": ["沙尘", "浮尘", "闷热"],
    }


@router.get("/weather/cities", summary="获取支持的天气城市列表")
async def get_supported_cities():
    """
    返回所有预置支持的天气城市名称列表（100+城市）
    前端可用于城市选择下拉框
    """
    return {"cities": sorted(CITY_ID_MAP.keys())}


@router.get("/weather/city-search", summary="搜索天气城市")
async def search_city(
    q: str = Query(..., min_length=1, description="搜索关键词（城市名）"),
):
    """
    模糊搜索城市名，返回匹配的城市列表。
    先查内置 120+ 城市，不足时调用和风城市搜索 API 补充（覆盖全国市县）。
    用于前端城市选择输入框的实时搜索。
    """
    q = q.strip()
    weather_api_key = getattr(settings, 'weather_api_key', None)
    matches = await search_cities(q, weather_api_key, limit=20)
    return {"query": q, "matches": matches}


@router.get("/weather/reverse-geocode", summary="坐标反查城市")
async def reverse_geocode_city(
    lat: float = Query(..., ge=-90, le=90, description="纬度"),
    lng: float = Query(..., ge=-180, le=180, description="经度"),
):
    """
    根据经纬度反查城市名（和风城市搜索 API，覆盖全国市县）。
    前端浏览器定位后可直接调用，替代本地城市边界判断。
    """
    weather_api_key = getattr(settings, 'weather_api_key', None)
    city = await reverse_geocode(lat, lng, weather_api_key)
    if not city:
        raise HTTPException(status_code=404, detail="无法识别该坐标对应的城市")
    return {"city": city}


# ============================================================
# IP 定位兜底：HTTP 环境下浏览器 Geolocation 被禁用，
# 改用请求 IP 归属地解析城市（无需用户授权）
# ============================================================
IP_CITY_CACHE: dict = {}  # ip -> (timestamp, city)
IP_CITY_TTL = 3600  # 1 小时


def _get_client_ip(request: Request) -> str:
    """提取真实客户端 IP（Nginx 已转发 X-Forwarded-For / X-Real-IP）"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


def _is_private_ip(ip: str) -> bool:
    """判断是否为内网/回环地址（无法做归属地解析）"""
    if not ip or ip == "localhost":
        return True
    parts = ip.split(".")
    if len(parts) != 4:
        return True  # IPv6 或非法格式，按内网处理
    try:
        first, second = int(parts[0]), int(parts[1])
    except ValueError:
        return True
    return (
        first == 10
        or first == 127
        or (first == 172 and 16 <= second <= 31)
        or (first == 192 and second == 168)
    )


def _normalize_ip_city(city: str, region: str) -> Optional[str]:
    """
    归一化 ip-api 返回的城市名：去掉「市」后缀，
    直辖市（city 为空或与 region 相同）取 region
    """
    name = (city or "").strip()
    if not name or name == region:
        name = (region or "").strip()
    if not name:
        return None
    if name.endswith("市"):
        name = name[:-1]
    return name or None


async def _resolve_city_by_ip(ip: str) -> Optional[str]:
    """
    调用 ip-api.com 免费接口解析 IP 归属城市（中文返回，内存缓存 1 小时）。
    仅后端服务器间调用，免费层的 HTTP 限制不受影响。
    """
    cached = IP_CITY_CACHE.get(ip)
    if cached and time.time() - cached[0] < IP_CITY_TTL:
        return cached[1]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"lang": "zh-CN", "fields": "status,country,regionName,city"},
            )
            data = resp.json()
        if data.get("status") != "success":
            logger.warning(f"[IpCity] ip-api 解析失败: {ip} -> {data.get('message', 'unknown')}")
            return None
        city = _normalize_ip_city(data.get("city", ""), data.get("regionName", ""))
        if city:
            IP_CITY_CACHE[ip] = (time.time(), city)
            logger.info(f"[IpCity] IP定位成功: {ip} -> {city}")
        return city
    except Exception as e:
        logger.warning(f"[IpCity] IP归属地解析异常 ({ip}): {e}")
        return None


@router.get("/weather/ip-city", summary="IP定位城市（浏览器定位兜底）")
async def get_city_by_ip(request: Request):
    """
    根据请求 IP 解析归属城市。

    背景：浏览器 Geolocation API 仅在 HTTPS 安全上下文可用，
    备案前站点为 HTTP，前端定位会被浏览器直接拒绝；
    本接口作为无需授权的兜底定位，精度到城市级，满足天气查询需求。
    """
    ip = _get_client_ip(request)
    if _is_private_ip(ip):
        raise HTTPException(status_code=404, detail="内网地址无法定位")
    city = await _resolve_city_by_ip(ip)
    if not city:
        raise HTTPException(status_code=404, detail="无法识别IP对应的城市")
    return {"city": city, "ip": ip}
