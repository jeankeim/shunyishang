"""
天气 API 路由
提供天气查询和天气-五行映射功能
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx

from apps.api.core.config import settings
from apps.api.core.cache import cache

router = APIRouter()


class WeatherResponse(BaseModel):
    """天气响应"""
    city: str
    temperature: int  # 温度
    weather: str      # 天气描述
    humidity: int     # 湿度
    wind: str         # 风向风力
    element: str      # 对应五行
    element_reason: str  # 五行映射原因


# 常用城市ID映射表
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
}


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
        print(f"[Cache] 天气缓存命中: {city}")
        return WeatherResponse(**cached)
    
    # 检查是否有天气API配置
    weather_api_key = getattr(settings, 'weather_api_key', None)
    
    if not weather_api_key:
        # 未配置API Key，使用模拟数据
        print("[Weather] 未配置天气API Key，使用模拟数据")
        use_mock_data = True
    else:
        print(f"[Weather] 尝试使用API Key: {weather_api_key[:8]}...")
        use_mock_data = False
    
    if use_mock_data:
        mock_data = {
            "北京": ("晴", 22, 45, "南风2级"),
            "上海": ("多云", 25, 60, "东南风3级"),
            "广州": ("小雨", 28, 80, "南风2级"),
            "深圳": ("雷阵雨", 30, 85, "西南风3级"),
            "杭州": ("阴", 24, 70, "东风2级"),
            "成都": ("多云", 23, 65, "北风1级"),
        }
        
        weather, temp, humidity, wind = mock_data.get(city, ("晴", 22, 50, "微风"))
        element, reason = get_element_by_weather(weather, temp)
        
        result = WeatherResponse(
            city=city,
            temperature=temp,
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
        print(f"[API] 调用和风天气API: {city}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 使用自定义API Host和官方认证方式
            api_host = "nh6pg8qvv4.re.qweatherapi.com"
            headers = {
                "X-QW-Api-Key": weather_api_key
            }
            
            # 直接使用城市ID获取天气
            # 先查找城市ID
            city_id = CITY_ID_MAP.get(city)
            if not city_id:
                # 如果城市不在映射表中，使用模拟数据
                print(f"[API] 城市 {city} 不在支持列表中，使用模拟数据")
                raise Exception("城市不在支持列表中")
            
            weather_url = f"https://{api_host}/v7/weather/now"
            weather_params = {
                "location": city_id,  # 使用城市ID
            }
            
            weather_response = await client.get(weather_url, params=weather_params, headers=headers)
            weather_data = weather_response.json()
            
            if weather_data.get("code") != "200":
                # 如果城市名称失败，尝试使用模拟数据
                print(f"[API] 天气API返回错误: {weather_data.get('code')}, 使用模拟数据")
                raise Exception("API调用失败，使用模拟数据")
            
            now = weather_data["now"]
            temp = int(now["temp"])
            weather_desc = now["text"]
            humidity = int(now["humidity"])
            wind = f"{now['windDir']}{now['windScale']}级"
            
            element, reason = get_element_by_weather(weather_desc, temp)
            
            result = WeatherResponse(
                city=city,
                temperature=temp,
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
        print(f"[API] 天气API超时，使用模拟数据")
    except Exception as e:
        print(f"[API] 天气API异常: {e}，使用模拟数据")
    
    # API调用失败，返回模拟数据
    print(f"[Mock] 使用模拟天气数据: {city}")
    mock_data = {
        "北京": ("晴", 22, 45, "南风2级"),
        "上海": ("多云", 25, 60, "东南风3级"),
        "广州": ("小雨", 28, 80, "南风2级"),
        "深圳": ("雷阵雨", 30, 85, "西南风3级"),
        "杭州": ("阴", 24, 70, "东风2级"),
        "成都": ("多云", 23, 65, "北风1级"),
    }
    
    weather, temp, humidity, wind = mock_data.get(city, ("晴", 22, 50, "微风"))
    element, reason = get_element_by_weather(weather, temp)
    
    result = WeatherResponse(
        city=city,
        temperature=temp,
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
