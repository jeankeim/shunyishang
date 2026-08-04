"""
天气兜底逻辑测试

背景：前端天气面板加载失败或时序竞态时 weather 会缺失，导致温度硬过滤被整体绕过
（bad case：盛夏 33°C 推荐厚重羊毛西装）。本测试覆盖后端兜底获取天气的逻辑。
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clear_fallback_cache():
    """每个用例前清空兜底天气缓存"""
    from apps.api.routers import recommend
    recommend._WEATHER_FALLBACK_CACHE.clear()
    yield
    recommend._WEATHER_FALLBACK_CACHE.clear()


class TestWeatherFallback:
    def test_fallback_maps_keys_to_weather_info(self):
        """兜底天气字段映射为 WeatherInfo 结构"""
        from apps.api.routers import recommend

        mock_raw = {
            "city": "北京",
            "temperature": 31,
            "temperature_max": 33,
            "temperature_min": 25,
            "weather": "雷阵雨",
            "humidity": 70,
            "element": "水",
        }
        with patch(
            "apps.api.services.daily_outfit_service._get_weather_sync",
            return_value=mock_raw,
        ):
            result = recommend._get_fallback_weather("北京")

        assert result is not None
        assert result["temperature"] == 31
        assert result["temperature_max"] == 33
        assert result["weather_desc"] == "雷阵雨"
        assert result["humidity"] == 70
        assert result["wind_level"] is None

    def test_fallback_uses_cache_within_ttl(self):
        """10 分钟 TTL 内复用缓存，不重复调用天气服务"""
        from apps.api.routers import recommend

        mock_raw = {"temperature": 30, "temperature_max": 32, "weather": "晴", "humidity": 50}
        with patch(
            "apps.api.services.daily_outfit_service._get_weather_sync",
            return_value=mock_raw,
        ) as mock_sync:
            recommend._get_fallback_weather("杭州")
            recommend._get_fallback_weather("杭州")
            assert mock_sync.call_count == 1

    def test_fallback_returns_none_on_error(self):
        """天气服务异常时返回 None，不阻断推荐流程"""
        from apps.api.routers import recommend

        with patch(
            "apps.api.services.daily_outfit_service._get_weather_sync",
            side_effect=RuntimeError("network error"),
        ):
            assert recommend._get_fallback_weather("上海") is None

    def test_recommend_request_accepts_city(self):
        """RecommendRequest 支持 city 字段"""
        from apps.api.schemas.request import RecommendRequest

        req = RecommendRequest(query="夏天怎么穿凉快", city="北京")
        assert req.city == "北京"
        assert req.weather is None
