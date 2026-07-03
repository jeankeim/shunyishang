"""
location_utils 工具函数测试
测试坐标转城市、距离计算、中国境内判断、高德API逆地理编码等功能
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.utils.location_utils import (
    CITY_COORDINATES,
    CITY_BOUNDS,
    calculate_distance,
    get_city_bounds,
    is_location_in_china,
    reverse_geocode_simple,
    reverse_geocode_amap,
)


class TestCalculateDistance:
    """测试距离计算"""

    def test_same_point_zero_distance(self):
        """同一点距离为0"""
        dist = calculate_distance(39.9042, 116.4074, 39.9042, 116.4074)
        assert dist < 1.0  # 应该非常接近0

    def test_beijing_to_shanghai(self):
        """北京到上海距离约1000-1200公里"""
        beijing = CITY_COORDINATES['北京']
        shanghai = CITY_COORDINATES['上海']
        dist = calculate_distance(beijing['lat'], beijing['lng'], shanghai['lat'], shanghai['lng'])
        assert 900 < dist < 1300

    def test_beijing_to_tianjin(self):
        """北京到天津距离较近"""
        beijing = CITY_COORDINATES['北京']
        tianjin = CITY_COORDINATES['天津']
        dist = calculate_distance(beijing['lat'], beijing['lng'], tianjin['lat'], tianjin['lng'])
        assert 50 < dist < 200

    def test_distance_positive(self):
        """距离为正数"""
        dist = calculate_distance(30.0, 120.0, 31.0, 121.0)
        assert dist > 0


class TestGetCityBounds:
    """测试城市边界获取"""

    def test_known_city(self):
        """已知城市有边界"""
        bounds = get_city_bounds("北京")
        assert bounds is not None
        assert 'lat' in bounds
        assert 'lng' in bounds
        assert len(bounds['lat']) == 2
        assert len(bounds['lng']) == 2

    def test_unknown_city_returns_none(self):
        """未知城市返回 None"""
        assert get_city_bounds("不存在的城市") is None

    def test_bounds_around_center(self):
        """边界围绕中心坐标"""
        beijing_bounds = get_city_bounds("北京")
        beijing_coord = CITY_COORDINATES['北京']
        assert beijing_bounds['lat'][0] < beijing_coord['lat'] < beijing_bounds['lat'][1]
        assert beijing_bounds['lng'][0] < beijing_coord['lng'] < beijing_bounds['lng'][1]


class TestIsLocationInChina:
    """测试中国境内判断"""

    def test_beijing_in_china(self):
        """北京在中国境内"""
        assert is_location_in_china(39.9042, 116.4074) is True

    def test_shanghai_in_china(self):
        """上海在中国境内"""
        assert is_location_in_china(31.2304, 121.4737) is True

    def test_new_york_not_in_china(self):
        """纽约不在中国境内"""
        assert is_location_in_china(40.7128, -74.0060) is False

    def test_tokyo_not_in_china(self):
        """东京不在中国境内"""
        assert is_location_in_china(35.6762, 139.6503) is False

    def test_south_boundary(self):
        """南部边界"""
        assert is_location_in_china(18.0, 110.0) is True
        assert is_location_in_china(17.0, 110.0) is False

    def test_north_boundary(self):
        """北部边界"""
        assert is_location_in_china(53.0, 120.0) is True
        assert is_location_in_china(54.0, 120.0) is False


class TestReverseGeocodeSimple:
    """测试简化逆地理编码"""

    async def test_beijing_location(self):
        """北京坐标返回北京"""
        result = await reverse_geocode_simple(39.9042, 116.4074)
        assert result == "北京"

    async def test_shanghai_location(self):
        """上海坐标返回上海"""
        result = await reverse_geocode_simple(31.2304, 121.4737)
        assert result == "上海"

    async def test_near_beijing(self):
        """北京附近坐标返回北京"""
        result = await reverse_geocode_simple(39.85, 116.35)
        assert result == "北京"

    async def test_far_location_returns_none(self):
        """远离中国的坐标返回 None"""
        result = await reverse_geocode_simple(40.7128, -74.0060)
        assert result is None


class TestCityData:
    """测试城市数据完整性"""

    def test_all_cities_have_coordinates(self):
        """所有城市都有坐标"""
        for city, coords in CITY_COORDINATES.items():
            assert 'lat' in coords
            assert 'lng' in coords
            assert isinstance(coords['lat'], (int, float))
            assert isinstance(coords['lng'], (int, float))

    def test_all_cities_have_bounds(self):
        """所有城市都有边界"""
        for city in CITY_COORDINATES:
            assert city in CITY_BOUNDS

    def test_major_cities_exist(self):
        """主要城市存在"""
        major_cities = ["北京", "上海", "广州", "深圳", "成都", "杭州"]
        for city in major_cities:
            assert city in CITY_COORDINATES


class TestReverseGeocodeAmap:
    """测试高德地图API逆地理编码"""

    async def test_no_api_key_fallback(self):
        """未配置API Key时回退到简化版本"""
        with patch("packages.utils.location_utils.settings") as mock_settings:
            mock_settings.amap_api_key = None
            result = await reverse_geocode_amap(39.9042, 116.4074)
        assert result == "北京"

    async def test_api_success(self):
        """API调用成功"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "1",
            "regeocode": {
                "addressComponent": {
                    "city": "北京市",
                    "province": "北京市",
                }
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.location_utils.settings") as mock_settings:
            mock_settings.amap_api_key = "fake_key"
            with patch("packages.utils.location_utils.httpx.AsyncClient", return_value=mock_client):
                result = await reverse_geocode_amap(39.9042, 116.4074)

        assert result == "北京"  # 去掉"市"后缀

    async def test_api_success_direct_municipality(self):
        """直辖市处理（city为空时用province）"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "1",
            "regeocode": {
                "addressComponent": {
                    "city": [],
                    "province": "上海市",
                }
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.location_utils.settings") as mock_settings:
            mock_settings.amap_api_key = "fake_key"
            with patch("packages.utils.location_utils.httpx.AsyncClient", return_value=mock_client):
                result = await reverse_geocode_amap(31.2304, 121.4737)

        assert result == "上海"

    async def test_api_error_status(self):
        """API返回错误状态"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "0",
            "regeocode": {},
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.location_utils.settings") as mock_settings:
            mock_settings.amap_api_key = "fake_key"
            with patch("packages.utils.location_utils.httpx.AsyncClient", return_value=mock_client):
                result = await reverse_geocode_amap(39.9042, 116.4074)

        assert result is None

    async def test_api_exception_fallback(self):
        """API异常时回退到简化版本"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.location_utils.settings") as mock_settings:
            mock_settings.amap_api_key = "fake_key"
            with patch("packages.utils.location_utils.httpx.AsyncClient", return_value=mock_client):
                result = await reverse_geocode_amap(39.9042, 116.4074)

        assert result == "北京"  # 回退到简化版本

    async def test_city_without_suffix(self):
        """城市名无"市"后缀时直接返回"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "1",
            "regeocode": {
                "addressComponent": {
                    "city": "成都",
                    "province": "四川省",
                }
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.location_utils.settings") as mock_settings:
            mock_settings.amap_api_key = "fake_key"
            with patch("packages.utils.location_utils.httpx.AsyncClient", return_value=mock_client):
                result = await reverse_geocode_amap(30.5728, 104.0668)

        assert result == "成都"
