"""
weather_api 模块测试
测试天气数据获取功能
"""

import pytest
from packages.utils.weather_api import get_weather


class TestGetWeather:
    """测试天气获取"""

    async def test_default_city(self):
        """默认城市"""
        result = await get_weather()
        assert result["city"] == "Beijing"
        assert "temperature" in result
        assert "weather" in result
        assert "humidity" in result
        assert "suggestion" in result

    async def test_custom_city(self):
        """自定义城市"""
        result = await get_weather("Shanghai")
        assert result["city"] == "Shanghai"

    async def test_chinese_city_name(self):
        """中文城市名"""
        result = await get_weather("北京")
        assert result["city"] == "北京"

    async def test_result_has_all_fields(self):
        """结果包含所有必需字段"""
        result = await get_weather()
        required_fields = ["city", "temperature", "weather", "humidity", "suggestion"]
        for field in required_fields:
            assert field in result, f"缺少字段: {field}"

    async def test_temperature_is_numeric(self):
        """温度为数字"""
        result = await get_weather()
        assert isinstance(result["temperature"], (int, float))

    async def test_humidity_is_numeric(self):
        """湿度为数字"""
        result = await get_weather()
        assert isinstance(result["humidity"], (int, float))

    async def test_suggestion_not_empty(self):
        """建议不为空"""
        result = await get_weather()
        assert len(result["suggestion"]) > 0
