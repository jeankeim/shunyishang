"""
天气 API 路由
提供天气查询和天气-五行映射功能
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx
import logging

from apps.api.core.config import settings
from apps.api.core.cache import cache

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


# 常用城市ID映射表（覆盖全国省会/直辖市/主要城市，共100+）
CITY_ID_MAP = {
    # ---- 直辖市 ----
    "北京": "101010100",
    "上海": "101020100",
    "天津": "101030100",
    "重庆": "101040100",
    # ---- 省会 / 首府 ----
    "哈尔滨": "101050101",
    "长春": "101060101",
    "沈阳": "101070101",
    "呼和浩特": "101080101",
    "石家庄": "101090101",
    "太原": "101100101",
    "济南": "101120101",
    "郑州": "101180101",
    "西安": "101110101",
    "兰州": "101160101",
    "银川": "101170101",
    "西宁": "101150101",
    "乌鲁木齐": "101130101",
    "合肥": "101220101",
    "南京": "101190101",
    "杭州": "101210101",
    "福州": "101230101",
    "南昌": "101240101",
    "武汉": "101200101",
    "长沙": "101250101",
    "广州": "101280101",
    "南宁": "101300101",
    "海口": "101310101",
    "成都": "101270101",
    "贵阳": "101260101",
    "昆明": "101290101",
    "拉萨": "101140101",
    "台北": "101340101",
    # ---- 计划单列市 / 经济特区 ----
    "深圳": "101280601",
    "厦门": "101230201",
    "宁波": "101210401",
    "青岛": "101120201",
    "大连": "101070201",
    # ---- 其他主要城市 ----
    "苏州": "101190401",
    "无锡": "101190201",
    "常州": "101191101",
    "佛山": "101280800",
    "东莞": "101281600",
    "珠海": "101280701",
    "温州": "101210701",
    "嘉兴": "101210301",
    "绍兴": "101210501",
    "金华": "101210901",
    "台州": "101211001",
    "泉州": "101230501",
    "烟台": "101120501",
    "潍坊": "101120601",
    "威海": "101121301",
    "日照": "101121501",
    "洛阳": "101180901",
    "开封": "101180801",
    "宜昌": "101201001",
    "襄阳": "101200201",
    "株洲": "101250301",
    "岳阳": "101251001",
    "桂林": "101300501",
    "柳州": "101300301",
    "三亚": "101310201",
    "绵阳": "101270401",
    "德阳": "101271401",
    "遵义": "101260201",
    "大理": "101290801",
    "丽江": "101291401",
    "唐山": "101090501",
    "保定": "101090201",
    "廊坊": "101090601",
    "秦皇岛": "101090301",
    "邯郸": "101091001",
    "吉林": "101060201",
    "延吉": "101060901",
    "鞍山": "101070301",
    "锦州": "101070701",
    "营口": "101070801",
    "泰安": "101120801",
    "临沂": "101120901",
    "淄博": "101120301",
    "徐州": "101190801",
    "连云港": "101191001",
    "盐城": "101190701",
    "南通": "101190501",
    "扬州": "101190601",
    "镇江": "101190301",
    "泰州": "101191201",
    "漳州": "101231001",
    "龙岩": "101230701",
    "莆田": "101230401",
    "九江": "101240201",
    "赣州": "101240701",
    "上饶": "101240301",
    "蚌埠": "101220201",
    "芜湖": "101220301",
    "黄山": "101221001",
    "安庆": "101220601",
    "马鞍山": "101220501",
    "许昌": "101180401",
    "新乡": "101180301",
    "南阳": "101180701",
    "信阳": "101180601",
    "焦作": "101181101",
    "湘潭": "101250201",
    "衡阳": "101250401",
    "常德": "101250601",
    "韶关": "101280201",
    "惠州": "101280301",
    "汕头": "101281501",
    "湛江": "101281001",
    "江门": "101281101",
    "肇庆": "101280901",
    "梅州": "101280401",
    "潮州": "101281502",
    "百色": "101300901",
    "梧州": "101300401",
    "北海": "101300201",
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
            
            # 直接使用城市ID获取天气
            # 先查找城市ID
            city_id = CITY_ID_MAP.get(city)
            if not city_id:
                # 城市不在映射表中，尝试用城市名作为location参数调用API
                logger.info(f"[API] 城市 {city} 不在预置列表中，尝试直接以城市名查询")
                city_id = city  # 和风天气API也支持直接传城市名/adcode
            
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
    用于前端城市选择输入框的实时搜索。
    """
    q = q.strip()
    matches = [city for city in CITY_ID_MAP.keys() if q in city]
    return {"query": q, "matches": matches[:20]}
