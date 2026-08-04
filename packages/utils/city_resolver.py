"""
城市解析模块（全国城市覆盖）

统一维护城市名 → 和风天气 LocationID 的解析逻辑：
1. 优先命中内置映射表（120+ 常用城市，免 API 调用）
2. 未命中时调用和风天气「城市搜索 API」(/geo/v2/city/lookup) 动态解析，
   支持全国任意地级市/区县（如「昆山」「义乌」），结果进程内缓存
3. 支持坐标反查城市（替代前端本地边界判断）

供 weather.py（实时天气）、weather_forecast.py（旅行预报）等模块复用，
避免各处维护重复的城市映射表。
"""

import logging
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

# 和风天气专属 API Host（与 weather.py / weather_forecast.py 保持一致）
QWEATHER_API_HOST = "nh6pg8qvv4.re.qweatherapi.com"
GEO_LOOKUP_PATH = "/geo/v2/city/lookup"
GEO_LOOKUP_TIMEOUT = 5.0

# ============================================================
# 内置城市ID映射表（覆盖全国省会/直辖市/主要城市，共120+）
# ============================================================
CITY_ID_MAP: Dict[str, str] = {
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

# 动态解析结果缓存（城市名 -> LocationID）。
# 城市ID永久有效，无需 TTL；仅缓存正向结果，避免错误拼写被长期记住。
_RESOLVED_CACHE: Dict[str, str] = {}


def clear_resolved_cache() -> None:
    """清空动态解析缓存（测试用）"""
    _RESOLVED_CACHE.clear()


def _geo_lookup_sync(location: str, api_key: str, number: int = 5) -> List[Dict[str, Any]]:
    """
    同步调用和风天气城市搜索 API（/geo/v2/city/lookup）

    Args:
        location: 城市名 / 区县名 / "经度,纬度" 坐标
        api_key: 和风天气 API Key
        number: 返回结果数量上限

    Returns:
        匹配的城市列表（name/id/adm1/adm2/lat/lon），失败返回空列表
    """
    try:
        response = httpx.get(
            f"https://{QWEATHER_API_HOST}{GEO_LOOKUP_PATH}",
            params={"location": location, "number": number},
            headers={"X-QW-Api-Key": api_key},
            timeout=GEO_LOOKUP_TIMEOUT,
        )
        data = response.json()
        if data.get("code") != "200":
            logger.warning(f"[CityResolver] 城市搜索API返回错误: {data.get('code')} ({location})")
            return []
        return data.get("location") or []
    except Exception as e:
        logger.warning(f"[CityResolver] 城市搜索API调用失败 ({location}): {e}")
        return []


async def _geo_lookup_async(location: str, api_key: str, number: int = 5) -> List[Dict[str, Any]]:
    """异步版城市搜索 API 调用，参数与返回同 _geo_lookup_sync"""
    try:
        async with httpx.AsyncClient(timeout=GEO_LOOKUP_TIMEOUT) as client:
            response = await client.get(
                f"https://{QWEATHER_API_HOST}{GEO_LOOKUP_PATH}",
                params={"location": location, "number": number},
                headers={"X-QW-Api-Key": api_key},
            )
            data = response.json()
            if data.get("code") != "200":
                logger.warning(f"[CityResolver] 城市搜索API返回错误: {data.get('code')} ({location})")
                return []
            return data.get("location") or []
    except Exception as e:
        logger.warning(f"[CityResolver] 城市搜索API调用失败 ({location}): {e}")
        return []


def _pick_best_match(candidates: List[Dict[str, Any]], expected_name: str) -> Optional[Dict[str, Any]]:
    """
    从搜索结果中挑选最匹配的城市：
    优先 name 完全一致，其次取第一条（API 已按相关度排序），仅保留中国境内结果
    """
    china = [c for c in candidates if c.get("country", "中国") == "中国"]
    if not china:
        return None
    for c in china:
        if c.get("name") == expected_name:
            return c
    return china[0]


def resolve_city_id_sync(city: str, api_key: Optional[str]) -> Optional[str]:
    """
    同步解析城市名为和风 LocationID（内置映射表 → 城市搜索API → 缓存）

    Args:
        city: 城市名或区县名
        api_key: 和风天气 API Key（未配置时仅查内置映射表）

    Returns:
        LocationID，无法解析返回 None
    """
    if not city:
        return None
    city = city.strip()

    city_id = CITY_ID_MAP.get(city) or _RESOLVED_CACHE.get(city)
    if city_id:
        return city_id

    if not api_key:
        return None

    candidates = _geo_lookup_sync(city, api_key, number=5)
    best = _pick_best_match(candidates, city)
    if best and best.get("id"):
        _RESOLVED_CACHE[city] = best["id"]
        logger.info(f"[CityResolver] 动态解析成功: {city} -> {best['id']} ({best.get('adm1', '')}{best.get('adm2', '')})")
        return best["id"]
    return None


async def resolve_city_id(city: str, api_key: Optional[str]) -> Optional[str]:
    """异步版城市解析，逻辑同 resolve_city_id_sync"""
    if not city:
        return None
    city = city.strip()

    city_id = CITY_ID_MAP.get(city) or _RESOLVED_CACHE.get(city)
    if city_id:
        return city_id

    if not api_key:
        return None

    candidates = await _geo_lookup_async(city, api_key, number=5)
    best = _pick_best_match(candidates, city)
    if best and best.get("id"):
        _RESOLVED_CACHE[city] = best["id"]
        logger.info(f"[CityResolver] 动态解析成功: {city} -> {best['id']} ({best.get('adm1', '')}{best.get('adm2', '')})")
        return best["id"]
    return None


async def search_cities(query: str, api_key: Optional[str], limit: int = 10) -> List[str]:
    """
    全国城市模糊搜索：先查内置映射表，不足时用城市搜索 API 补充

    Returns:
        城市名列表（去重、最多 limit 条）
    """
    query = (query or "").strip()
    if not query:
        return []

    # 1. 本地映射表匹配（零延迟）
    matches = [c for c in CITY_ID_MAP.keys() if query in c]

    # 2. 本地结果不足时调用和风城市搜索 API 补充（覆盖全国市县）
    if len(matches) < limit and api_key:
        candidates = await _geo_lookup_async(query, api_key, number=limit)
        for c in candidates:
            if c.get("country", "中国") != "中国":
                continue
            name = c.get("name")
            if name and name not in matches:
                matches.append(name)

    return matches[:limit]


async def reverse_geocode(lat: float, lng: float, api_key: Optional[str]) -> Optional[str]:
    """
    坐标反查城市名（和风城市搜索 API 支持 "经度,纬度" 格式）

    优先返回地级市名（与天气查询粒度一致）：区县结果（如「西湖」）
    会尝试用其上级行政区（adm2，如「杭州市」）二次解析；失败时返回区县名。

    Returns:
        城市名，失败返回 None
    """
    if not api_key:
        return None
    candidates = await _geo_lookup_async(f"{lng},{lat}", api_key, number=1)
    if not candidates or candidates[0].get("country", "中国") != "中国":
        return None

    best = candidates[0]
    name = best.get("name")
    adm2 = best.get("adm2", "")  # 上级行政区（地级市），如「杭州市」
    if adm2:
        # 区县结果上提到地级市（去掉「市」后缀后精确匹配）
        parent = adm2[:-1] if adm2.endswith("市") else adm2
        parent_id = await resolve_city_id(parent, api_key)
        if parent_id:
            return parent
    return name
