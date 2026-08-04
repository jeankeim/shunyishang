"""
IP 定位兜底测试

背景：浏览器 Geolocation API 仅 HTTPS 安全上下文可用，备案前站点为 HTTP，
前端定位被浏览器直接拒绝。本测试覆盖后端按请求 IP 解析归属城市的兜底逻辑。
"""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _clear_ip_cache():
    """每个用例前后清空 IP 定位缓存"""
    from apps.api.routers import weather
    weather.IP_CITY_CACHE.clear()
    yield
    weather.IP_CITY_CACHE.clear()


class TestIsPrivateIp:
    """内网/回环地址判断"""

    def test_private_ranges(self):
        from apps.api.routers.weather import _is_private_ip
        assert _is_private_ip("127.0.0.1") is True
        assert _is_private_ip("10.1.2.3") is True
        assert _is_private_ip("172.16.0.1") is True
        assert _is_private_ip("172.31.255.255") is True
        assert _is_private_ip("192.168.1.1") is True
        assert _is_private_ip("") is True
        assert _is_private_ip("localhost") is True
        assert _is_private_ip("::1") is True  # IPv6 按内网处理

    def test_public_ip(self):
        from apps.api.routers.weather import _is_private_ip
        assert _is_private_ip("121.43.60.141") is False
        assert _is_private_ip("8.8.8.8") is False
        assert _is_private_ip("172.32.0.1") is False


class TestNormalizeIpCity:
    """ip-api 城市名归一化"""

    def test_strip_shi_suffix(self):
        from apps.api.routers.weather import _normalize_ip_city
        assert _normalize_ip_city("杭州市", "浙江省") == "杭州"

    def test_municipality_city_empty(self):
        """直辖市 city 为空，取 region"""
        from apps.api.routers.weather import _normalize_ip_city
        assert _normalize_ip_city("", "北京市") == "北京"

    def test_municipality_city_equals_region(self):
        """直辖市 city 与 region 相同，取 region 并去后缀"""
        from apps.api.routers.weather import _normalize_ip_city
        assert _normalize_ip_city("北京市", "北京市") == "北京"

    def test_all_empty_returns_none(self):
        from apps.api.routers.weather import _normalize_ip_city
        assert _normalize_ip_city("", "") is None


class TestGetClientIp:
    """真实客户端 IP 提取"""

    def _mock_request(self, headers=None, host="127.0.0.1"):
        request = MagicMock()
        request.headers = headers or {}
        request.client = MagicMock(host=host)
        return request

    def test_x_forwarded_for_first(self):
        from apps.api.routers.weather import _get_client_ip
        request = self._mock_request({"X-Forwarded-For": "1.2.3.4, 10.0.0.1"})
        assert _get_client_ip(request) == "1.2.3.4"

    def test_x_real_ip(self):
        from apps.api.routers.weather import _get_client_ip
        request = self._mock_request({"X-Real-IP": "5.6.7.8"})
        assert _get_client_ip(request) == "5.6.7.8"

    def test_client_host_fallback(self):
        from apps.api.routers.weather import _get_client_ip
        request = self._mock_request({}, host="9.9.9.9")
        assert _get_client_ip(request) == "9.9.9.9"


class TestResolveCityByIp:
    """ip-api 解析与缓存"""

    @pytest.mark.asyncio
    async def test_resolve_success(self):
        from apps.api.routers import weather

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "success",
            "country": "中国",
            "regionName": "浙江省",
            "city": "杭州市",
        }
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client):
            city = await weather._resolve_city_by_ip("115.236.1.1")
        assert city == "杭州"

    @pytest.mark.asyncio
    async def test_cached_within_ttl(self):
        from apps.api.routers import weather

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "success", "country": "中国",
            "regionName": "浙江省", "city": "杭州市",
        }
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client) as mock_ctor:
            await weather._resolve_city_by_ip("115.236.1.1")
            await weather._resolve_city_by_ip("115.236.1.1")
            assert mock_ctor.call_count == 1  # 二次查询命中缓存

    @pytest.mark.asyncio
    async def test_api_failure_returns_none(self):
        from apps.api.routers import weather

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "fail", "message": "private range"}
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client):
            assert await weather._resolve_city_by_ip("1.1.1.1") is None

    @pytest.mark.asyncio
    async def test_network_exception_returns_none(self):
        from apps.api.routers import weather

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("network error")
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client):
            assert await weather._resolve_city_by_ip("1.1.1.1") is None


class TestIpCityEndpoint:
    """ip-city 接口"""

    @pytest.mark.asyncio
    async def test_private_ip_raises_404(self):
        from fastapi import HTTPException
        from apps.api.routers.weather import get_city_by_ip

        request = MagicMock()
        request.headers = {"X-Real-IP": "192.168.1.1"}
        request.client = MagicMock(host="192.168.1.1")

        with pytest.raises(HTTPException) as exc:
            await get_city_by_ip(request)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_city(self):
        from apps.api.routers import weather

        request = MagicMock()
        request.headers = {"X-Real-IP": "121.43.60.141"}
        request.client = MagicMock(host="121.43.60.141")

        with patch.object(weather, "_resolve_city_by_ip", return_value="杭州"):
            result = await weather.get_city_by_ip(request)
        assert result["city"] == "杭州"
        assert result["ip"] == "121.43.60.141"

    @pytest.mark.asyncio
    async def test_unknown_ip_raises_404(self):
        from fastapi import HTTPException
        from apps.api.routers import weather

        request = MagicMock()
        request.headers = {"X-Real-IP": "8.8.8.8"}
        request.client = MagicMock(host="8.8.8.8")

        with patch.object(weather, "_resolve_city_by_ip", return_value=None):
            with pytest.raises(HTTPException) as exc:
                await weather.get_city_by_ip(request)
        assert exc.value.status_code == 404
