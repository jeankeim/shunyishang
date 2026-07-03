"""
天气预测测试
测试目的地天气获取、天气五行映射、API失败兜底、内部辅助函数
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from packages.utils.weather_forecast import (
    get_destination_weather,
    predict_weather_element,
    _fetch_weather_from_api,
    _parse_wind_scale,
    _generate_fallback_weather,
    _get_city_temperature_adjust,
    EXTENDED_WEATHER_ELEMENT_MAP,
    CITY_ID_MAP,
    SEASON_DEFAULT_WEATHER,
)


class TestGetDestinationWeather:
    """测试目的地天气获取"""

    def test_fallback_weather_basic(self):
        """未配置API时使用兜底数据"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = None
            result = get_destination_weather("北京", 3)

        assert len(result) == 3
        for day in result:
            assert "date" in day
            assert "temperature_max" in day
            assert "temperature_min" in day
            assert "weather_desc" in day
            assert "humidity" in day
            assert "wind_level" in day

    def test_fallback_weather_multiple_days(self):
        """多天天气预测"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = None
            result = get_destination_weather("上海", 7)

        assert len(result) == 7
        # 日期应该递增
        for i, day in enumerate(result):
            assert day["date"] is not None

    def test_fallback_weather_zero_days(self):
        """0天返回空列表"""
        result = get_destination_weather("北京", 0)
        assert result == []

    def test_fallback_weather_unknown_city(self):
        """未知城市也返回兜底数据"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = None
            result = get_destination_weather("未知城市", 2)

        assert len(result) == 2

    def test_south_city_temperature_adjust(self):
        """南方城市温度微调"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = None
            south = get_destination_weather("三亚", 1)
            north = get_destination_weather("哈尔滨", 1)

        # 三亚温度应该高于哈尔滨
        assert south[0]["temperature_max"] > north[0]["temperature_max"]

    def test_api_failure_fallback(self):
        """API调用失败时兜底"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = "fake_key"
            with patch("packages.utils.weather_forecast._fetch_weather_from_api", return_value=[]):
                result = get_destination_weather("北京", 3)

        assert len(result) == 3  # 应回退到兜底数据

    def test_api_success(self):
        """API调用成功"""
        mock_weather = [
            {
                "date": "2026-07-01",
                "temperature_max": 30,
                "temperature_min": 22,
                "weather_desc": "晴",
                "humidity": 55,
                "wind_level": 2,
            },
        ]
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = "fake_key"
            with patch("packages.utils.weather_forecast._fetch_weather_from_api", return_value=mock_weather):
                result = get_destination_weather("北京", 1)

        assert len(result) == 1
        assert result[0]["weather_desc"] == "晴"
        assert result[0]["temperature_max"] == 30

    def test_weather_has_valid_fields(self):
        """天气数据字段完整性"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = None
            result = get_destination_weather("杭州", 5)

        for day in result:
            assert isinstance(day["temperature_max"], int)
            assert isinstance(day["temperature_min"], int)
            assert isinstance(day["humidity"], int)
            assert isinstance(day["wind_level"], int)
            assert isinstance(day["weather_desc"], str)
            assert isinstance(day["date"], str)


class TestPredictWeatherElement:
    """测试天气五行映射"""

    def test_rain_maps_to_water(self):
        """雨天映射为水"""
        assert predict_weather_element("雨天") == "水"
        assert predict_weather_element("小雨") == "水"
        assert predict_weather_element("大雨") == "水"
        assert predict_weather_element("雷阵雨") == "水"

    def test_sunny_maps_to_fire(self):
        """晴天映射为火"""
        assert predict_weather_element("晴") == "火"
        assert predict_weather_element("高温") == "火"

    def test_cloudy_maps_to_wood(self):
        """多云映射为木"""
        assert predict_weather_element("多云") == "木"
        assert predict_weather_element("阴") == "木"

    def test_cold_maps_to_metal(self):
        """寒冷映射为金"""
        assert predict_weather_element("凉") == "金"
        assert predict_weather_element("冷") == "金"
        assert predict_weather_element("大风") == "金"

    def test_dust_maps_to_earth(self):
        """沙尘映射为土"""
        assert predict_weather_element("沙尘") == "土"
        assert predict_weather_element("闷热") == "土"

    def test_fog_maps_to_metal(self):
        """雾天映射为金（新增）"""
        assert predict_weather_element("雾天") == "金"

    def test_thunderstorm_maps_to_wood(self):
        """雷暴映射为木（新增）"""
        assert predict_weather_element("雷暴") == "木"

    def test_sandstorm_maps_to_earth(self):
        """沙尘暴映射为土（新增）"""
        assert predict_weather_element("沙尘暴") == "土"

    def test_unknown_weather_default_earth(self):
        """未知天气默认返回土"""
        assert predict_weather_element("未知天气类型") == "土"

    def test_empty_weather(self):
        """空天气描述"""
        assert predict_weather_element("") == "土"
        assert predict_weather_element(None) == "土"

    def test_extended_map_has_new_entries(self):
        """扩展映射表包含新增条目"""
        assert "雾天" in EXTENDED_WEATHER_ELEMENT_MAP
        assert "雷暴" in EXTENDED_WEATHER_ELEMENT_MAP
        assert "沙尘暴" in EXTENDED_WEATHER_ELEMENT_MAP

    def test_extended_map_consistency(self):
        """扩展映射表与原有映射一致"""
        # 原有映射应该保持一致
        assert EXTENDED_WEATHER_ELEMENT_MAP["雨"] == "水"
        assert EXTENDED_WEATHER_ELEMENT_MAP["晴"] == "火"
        assert EXTENDED_WEATHER_ELEMENT_MAP["多云"] == "木"
        assert EXTENDED_WEATHER_ELEMENT_MAP["凉"] == "金"
        assert EXTENDED_WEATHER_ELEMENT_MAP["沙尘"] == "土"


class TestCityIdMap:
    """测试城市ID映射"""

    def test_common_cities_exist(self):
        """常见城市在映射表中"""
        assert "北京" in CITY_ID_MAP
        assert "上海" in CITY_ID_MAP
        assert "广州" in CITY_ID_MAP
        assert "深圳" in CITY_ID_MAP
        assert "杭州" in CITY_ID_MAP

    def test_travel_cities_exist(self):
        """旅游城市在映射表中"""
        assert "三亚" in CITY_ID_MAP
        assert "厦门" in CITY_ID_MAP
        assert "昆明" in CITY_ID_MAP
        assert "拉萨" in CITY_ID_MAP


# ============================================================
# _parse_wind_scale 测试
# ============================================================

class TestParseWindScale:
    """测试风力等级解析"""

    def test_simple_number(self):
        """纯数字"""
        assert _parse_wind_scale("2") == 2
        assert _parse_wind_scale("5") == 5

    def test_range(self):
        """范围格式 2-3"""
        assert _parse_wind_scale("2-3") == 2
        assert _parse_wind_scale("3-4") == 3

    def test_invalid_string(self):
        """无效字符串返回默认值2"""
        assert _parse_wind_scale("abc") == 2

    def test_empty_string(self):
        """空字符串返回默认值2"""
        assert _parse_wind_scale("") == 2


# ============================================================
# _get_city_temperature_adjust 测试
# ============================================================

class TestGetCityTemperatureAdjust:
    """测试城市温度微调"""

    def test_south_cities(self):
        """南方城市+5度"""
        assert _get_city_temperature_adjust("三亚") == 5
        assert _get_city_temperature_adjust("海口") == 5
        assert _get_city_temperature_adjust("广州") == 5
        assert _get_city_temperature_adjust("深圳") == 5
        assert _get_city_temperature_adjust("厦门") == 5

    def test_north_cities(self):
        """北方城市-5度"""
        assert _get_city_temperature_adjust("哈尔滨") == -5
        assert _get_city_temperature_adjust("北京") == -5
        assert _get_city_temperature_adjust("大连") == -5
        assert _get_city_temperature_adjust("拉萨") == -5

    def test_other_cities(self):
        """其他城市0度"""
        assert _get_city_temperature_adjust("上海") == 0
        assert _get_city_temperature_adjust("成都") == 0
        assert _get_city_temperature_adjust("未知城市") == 0


# ============================================================
# _generate_fallback_weather 测试
# ============================================================

class TestGenerateFallbackWeather:
    """测试兜底天气生成"""

    def test_basic_generation(self):
        """基本生成"""
        result = _generate_fallback_weather("北京", 3)
        assert len(result) == 3
        for day in result:
            assert "date" in day
            assert "temperature_max" in day
            assert "temperature_min" in day
            assert "weather_desc" in day
            assert "humidity" in day
            assert "wind_level" in day

    def test_temperature_adjustment_south(self):
        """南方城市温度调高"""
        south = _generate_fallback_weather("三亚", 1)
        normal = _generate_fallback_weather("上海", 1)
        assert south[0]["temperature_max"] > normal[0]["temperature_max"]

    def test_temperature_adjustment_north(self):
        """北方城市温度调低"""
        north = _generate_fallback_weather("哈尔滨", 1)
        normal = _generate_fallback_weather("上海", 1)
        assert north[0]["temperature_max"] < normal[0]["temperature_max"]

    def test_dates_increment(self):
        """日期递增"""
        result = _generate_fallback_weather("北京", 5)
        for i in range(1, len(result)):
            assert result[i]["date"] != result[i - 1]["date"]

    def test_weather_variation(self):
        """天气有变化（第3天可能有变化）"""
        result = _generate_fallback_weather("北京", 7)
        # 至少检查不报错且返回正确数量
        assert len(result) == 7

    def test_humidity_and_wind_range(self):
        """湿度和风力在合理范围"""
        result = _generate_fallback_weather("北京", 5)
        for day in result:
            assert 0 <= day["humidity"] <= 100
            assert day["wind_level"] >= 0


# ============================================================
# _fetch_weather_from_api 测试
# ============================================================

class TestFetchWeatherFromApi:
    """测试天气API调用"""

    def test_success_with_mock(self):
        """API成功调用"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "200",
            "daily": [
                {
                    "fxDate": "2026-07-01",
                    "tempMax": "30",
                    "tempMin": "22",
                    "textDay": "晴",
                    "humidity": "55",
                    "windScaleDay": "2",
                },
                {
                    "fxDate": "2026-07-02",
                    "tempMax": "28",
                    "tempMin": "20",
                    "textDay": "多云",
                    "humidity": "60",
                    "windScaleDay": "2-3",
                },
            ],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.weather_forecast.httpx.AsyncClient", return_value=mock_client):
            result = _fetch_weather_from_api("北京", "101010100", "fake_key", 2)

        assert len(result) == 2
        assert result[0]["date"] == "2026-07-01"
        assert result[0]["temperature_max"] == 30
        assert result[0]["weather_desc"] == "晴"
        assert result[0]["wind_level"] == 2

    def test_api_error_code(self):
        """API返回错误码"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": "401", "daily": []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.weather_forecast.httpx.AsyncClient", return_value=mock_client):
            result = _fetch_weather_from_api("北京", "101010100", "fake_key", 3)

        assert result == []

    def test_api_exception(self):
        """API调用异常时异常传播（由调用方捕获）"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.weather_forecast.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                _fetch_weather_from_api("北京", "101010100", "fake_key", 3)

    def test_wind_scale_range_parsing(self):
        """风力等级范围解析"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "200",
            "daily": [
                {
                    "fxDate": "2026-07-01",
                    "tempMax": "30",
                    "tempMin": "22",
                    "textDay": "晴",
                    "humidity": "55",
                    "windScaleDay": "3-4",
                },
            ],
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.weather_forecast.httpx.AsyncClient", return_value=mock_client):
            result = _fetch_weather_from_api("北京", "101010100", "fake_key", 1)

        assert result[0]["wind_level"] == 3  # "3-4" → 3

    def test_days_truncation(self):
        """API返回天数截断"""
        daily_data = [
            {"fxDate": f"2026-07-{i:02d}", "tempMax": "30", "tempMin": "22",
             "textDay": "晴", "humidity": "55", "windScaleDay": "2"}
            for i in range(1, 8)
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": "200", "daily": daily_data}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("packages.utils.weather_forecast.httpx.AsyncClient", return_value=mock_client):
            result = _fetch_weather_from_api("北京", "101010100", "fake_key", 3)

        assert len(result) == 3  # 截断为3天


# ============================================================
# 季节相关测试（mock datetime）
# ============================================================

class TestFallbackWeatherSeasons:
    """测试不同季节的兜底天气生成"""

    def _mock_datetime(self, month):
        """创建mock datetime对象"""
        mock_dt = MagicMock(wraps=datetime)
        mock_dt.now.return_value = datetime(2026, month, 15)
        return mock_dt

    def test_spring_season(self):
        """春季兜底天气"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(4)):
            result = _generate_fallback_weather("上海", 5)
        assert len(result) == 5
        # 春季基础天气为多云
        assert result[0]["weather_desc"] == "多云"

    def test_summer_season(self):
        """夏季兜底天气"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(7)):
            result = _generate_fallback_weather("上海", 5)
        assert len(result) == 5
        # 夏季基础天气为晴
        assert result[0]["weather_desc"] == "晴"

    def test_autumn_season(self):
        """秋季兜底天气"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(10)):
            result = _generate_fallback_weather("上海", 5)
        assert len(result) == 5
        # 秋季基础天气为晴
        assert result[0]["weather_desc"] == "晴"

    def test_winter_season(self):
        """冬季兜底天气"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(1)):
            result = _generate_fallback_weather("上海", 5)
        assert len(result) == 5
        # 冬季基础天气为阴
        assert result[0]["weather_desc"] == "阴"

    def test_summer_weather_variation(self):
        """夏季天气变化（第3天雷阵雨）"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(7)):
            result = _generate_fallback_weather("上海", 7)
        # 第3天(i=3, i%3==0)夏季应该变为雷阵雨
        assert result[3]["weather_desc"] == "雷阵雨"

    def test_winter_weather_variation(self):
        """冬季天气变化（第3天阴）"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(1)):
            result = _generate_fallback_weather("上海", 7)
        # 第3天(i=3, i%3==0)冬季应该变为阴
        assert result[3]["weather_desc"] == "阴"

    def test_spring_weather_variation(self):
        """春秋天气变化（第3天多云）"""
        with patch("packages.utils.weather_forecast.datetime", self._mock_datetime(4)):
            result = _generate_fallback_weather("上海", 7)
        # 第3天(i=3, i%3==0)春秋应该变为多云
        assert result[3]["weather_desc"] == "多云"


# ============================================================
# API 异常路径测试
# ============================================================

class TestGetDestinationWeatherApiException:
    """测试 get_destination_weather 的API异常处理"""

    def test_api_exception_fallback(self):
        """API异常时使用兜底数据"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = "fake_key"
            with patch("packages.utils.weather_forecast._fetch_weather_from_api", side_effect=Exception("API error")):
                result = get_destination_weather("北京", 3)
        assert len(result) == 3  # 应回退到兜底数据

    def test_unknown_city_with_api_key(self):
        """有API Key但城市不在CITY_ID_MAP中"""
        with patch("packages.utils.weather_forecast.settings") as mock_settings:
            mock_settings.weather_api_key = "fake_key"
            result = get_destination_weather("未知城市", 2)
        assert len(result) == 2  # 使用兜底数据
