"""
地理位置工具模块
提供坐标转城市、距离计算等功能
"""

from typing import Optional, Tuple
import httpx
import json
from apps.api.core.config import settings

# 中国主要城市坐标数据库（扩展版）
CITY_COORDINATES = {
    # 华北地区
    '北京': {'lat': 39.9042, 'lng': 116.4074},
    '天津': {'lat': 39.3434, 'lng': 117.3616},
    '石家庄': {'lat': 38.0428, 'lng': 114.5149},
    '太原': {'lat': 37.8706, 'lng': 112.5489},
    
    # 华东地区
    '上海': {'lat': 31.2304, 'lng': 121.4737},
    '南京': {'lat': 32.0603, 'lng': 118.7969},
    '杭州': {'lat': 30.2741, 'lng': 120.1551},
    '苏州': {'lat': 31.2989, 'lng': 120.5853},
    '合肥': {'lat': 31.8206, 'lng': 117.2272},
    
    # 华南地区
    '广州': {'lat': 23.1291, 'lng': 113.2644},
    '深圳': {'lat': 22.5431, 'lng': 114.0579},
    '珠海': {'lat': 22.3964, 'lng': 113.5438},
    '厦门': {'lat': 24.4797, 'lng': 118.0894},
    
    # 西南地区
    '成都': {'lat': 30.5728, 'lng': 104.0668},
    '重庆': {'lat': 29.5630, 'lng': 106.5516},
    '昆明': {'lat': 25.0406, 'lng': 102.7123},
    
    # 西北地区
    '西安': {'lat': 34.3416, 'lng': 108.9398},
    '兰州': {'lat': 36.0611, 'lng': 103.8343},
    
    # 东北地区
    '沈阳': {'lat': 41.7969, 'lng': 123.4315},
    '大连': {'lat': 38.9140, 'lng': 121.6147},
    '哈尔滨': {'lat': 45.8038, 'lng': 126.5340},
    
    # 华中地区
    '武汉': {'lat': 30.5928, 'lng': 114.3055},
    '长沙': {'lat': 28.1941, 'lng': 112.9823},
    '郑州': {'lat': 34.7474, 'lng': 113.6249},
}

# 城市边界范围（用于粗略定位）
CITY_BOUNDS = {
    city: {
        'lat': [coord['lat'] - 0.5, coord['lat'] + 0.5],
        'lng': [coord['lng'] - 0.5, coord['lng'] + 0.5]
    }
    for city, coord in CITY_COORDINATES.items()
}


async def reverse_geocode_simple(lat: float, lng: float) -> Optional[str]:
    """
    简单逆地理编码 - 根据坐标查找最近的城市
    
    Args:
        lat: 纬度
        lng: 经度
        
    Returns:
        城市名称或None
    """
    min_distance = float('inf')
    nearest_city = None
    
    for city, coords in CITY_COORDINATES.items():
        distance = calculate_distance(lat, lng, coords['lat'], coords['lng'])
        if distance < min_distance:
            min_distance = distance
            nearest_city = city
    
    # 如果距离太远（超过200公里），认为不在中国主要城市范围内
    if min_distance > 200:
        return None
    
    return nearest_city


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    计算两点间距离（公里）
    使用简化的球面距离公式
    
    Args:
        lat1, lng1: 第一点坐标
        lat2, lng2: 第二点坐标
        
    Returns:
        距离（公里）
    """
    from math import radians, cos, sqrt
    
    # 转换为弧度
    lat1_rad = radians(lat1)
    lng1_rad = radians(lng1)
    lat2_rad = radians(lat2)
    lng2_rad = radians(lng2)
    
    # 简化计算（假设地球半径为6371公里）
    delta_lat = lat2_rad - lat1_rad
    delta_lng = lng2_rad - lng1_rad
    
    a = (sin(delta_lat/2)**2 + 
         cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = 6371 * c
    return distance


def get_city_bounds(city: str) -> Optional[dict]:
    """
    获取城市边界范围
    
    Args:
        city: 城市名称
        
    Returns:
        边界范围字典或None
    """
    return CITY_BOUNDS.get(city)


async def reverse_geocode_amap(lat: float, lng: float) -> Optional[str]:
    """
    使用高德地图API进行逆地理编码
    
    Args:
        lat: 纬度
        lng: 经度
        
    Returns:
        城市名称或None
    """
    amap_key = getattr(settings, 'amap_api_key', None)
    
    if not amap_key:
        print("[Location] 未配置高德API Key，使用简化版本")
        return await reverse_geocode_simple(lat, lng)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = "https://restapi.amap.com/v3/geocode/regeo"
            params = {
                'key': amap_key,
                'location': f'{lng},{lat}',
                'extensions': 'base'
            }
            
            response = await client.get(url, params=params)
            data = response.json()
            
            if data.get('status') == '1' and data.get('regeocode'):
                address_component = data['regeocode'].get('addressComponent', {})
                city = address_component.get('city')
                
                # 处理直辖市情况
                if not city:
                    city = address_component.get('province')
                
                # 去掉后缀（如"北京市" -> "北京"）
                if city and city.endswith('市'):
                    city = city[:-1]
                    
                return city
                
    except Exception as e:
        print(f"[Location] 高德API调用失败: {e}")
        # 回退到简化版本
        return await reverse_geocode_simple(lat, lng)
    
    return None


def is_location_in_china(lat: float, lng: float) -> bool:
    """
    判断坐标是否在中国境内
    
    Args:
        lat: 纬度
        lng: 经度
        
    Returns:
        是否在中国境内
    """
    # 中国的经纬度范围（粗略）
    china_bounds = {
        'lat': [18.0, 53.0],  # 纬度范围
        'lng': [73.0, 135.0]  # 经度范围
    }
    
    return (china_bounds['lat'][0] <= lat <= china_bounds['lat'][1] and
            china_bounds['lng'][0] <= lng <= china_bounds['lng'][1])


# 为兼容性导入数学函数
from math import sin, atan2

__all__ = [
    'reverse_geocode_simple',
    'reverse_geocode_amap',
    'calculate_distance',
    'get_city_bounds',
    'is_location_in_china',
    'CITY_COORDINATES',
    'CITY_BOUNDS'
]