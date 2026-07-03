"""
Upstash Redis 服务测试
覆盖 upstash_redis.py 所有方法
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from apps.api.services.upstash_redis import UpstashRedis, get_upstash_redis


class TestUpstashRedisInit:
    def test_disabled_when_no_config(self):
        """配置不完整时禁用"""
        with patch("apps.api.services.upstash_redis.settings") as mock_s:
            mock_s.upstash_redis_rest_url = None
            mock_s.upstash_redis_rest_token = None
            r = UpstashRedis()
            assert r.enabled is False

    def test_enabled_with_config(self):
        """配置完整时启用"""
        with patch("apps.api.services.upstash_redis.settings") as mock_s:
            mock_s.upstash_redis_rest_url = "https://test.upstash.io"
            mock_s.upstash_redis_rest_token = "test-token"
            r = UpstashRedis()
            assert r.enabled is True
            assert r.rest_url == "https://test.upstash.io"


class TestUpstashRedisExecute:
    @pytest.mark.asyncio
    async def test_disabled_returns_none(self):
        """禁用状态返回 None"""
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = False
        result = await r.execute(["SET", "key", "val"])
        assert result is None

    @pytest.mark.asyncio
    async def test_success_list_result(self):
        """成功执行，返回列表结果"""
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"result": "OK"}]
        r.client.post = AsyncMock(return_value=mock_resp)
        result = await r.execute(["SET", "key", "val"])
        assert result == "OK"

    @pytest.mark.asyncio
    async def test_success_non_dict_result(self):
        """成功执行，返回非字典列表结果"""
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = ["simple_result"]
        r.client.post = AsyncMock(return_value=mock_resp)
        result = await r.execute(["GET", "key"])
        assert result == "simple_result"

    @pytest.mark.asyncio
    async def test_empty_result(self):
        """空结果返回 None"""
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        r.client.post = AsyncMock(return_value=mock_resp)
        result = await r.execute(["GET", "key"])
        assert result is None

    @pytest.mark.asyncio
    async def test_http_error(self):
        """HTTP 错误返回 None"""
        import httpx
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.client = MagicMock()
        r.client.post = AsyncMock(side_effect=httpx.HTTPError("connection error"))
        result = await r.execute(["GET", "key"])
        assert result is None

    @pytest.mark.asyncio
    async def test_generic_error(self):
        """通用异常返回 None"""
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.client = MagicMock()
        r.client.post = AsyncMock(side_effect=ValueError("bad value"))
        result = await r.execute(["GET", "key"])
        assert result is None


class TestUpstashRedisSet:
    @pytest.mark.asyncio
    async def test_disabled(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = False
        assert await r.set("key", "val") is False

    @pytest.mark.asyncio
    async def test_success(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value="OK")
        assert await r.set("key", "val") is True
        r.execute.assert_called_once_with(["SET", "key", "val"])

    @pytest.mark.asyncio
    async def test_with_expiry(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value="OK")
        assert await r.set("key", "val", ex=3600) is True
        r.execute.assert_called_once_with(["SET", "key", "val", "EX", "3600"])

    @pytest.mark.asyncio
    async def test_failure(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value=None)
        assert await r.set("key", "val") is False


class TestUpstashRedisGet:
    @pytest.mark.asyncio
    async def test_disabled(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = False
        assert await r.get("key") is None

    @pytest.mark.asyncio
    async def test_success(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value="value")
        assert await r.get("key") == "value"


class TestUpstashRedisDelete:
    @pytest.mark.asyncio
    async def test_disabled(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = False
        assert await r.delete("key") is False

    @pytest.mark.asyncio
    async def test_deleted(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value=1)
        assert await r.delete("key") is True

    @pytest.mark.asyncio
    async def test_not_found(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value=0)
        assert await r.delete("key") is False

    @pytest.mark.asyncio
    async def test_none_result(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value=None)
        assert await r.delete("key") is False


class TestUpstashRedisExists:
    @pytest.mark.asyncio
    async def test_disabled(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = False
        assert await r.exists("key") is False

    @pytest.mark.asyncio
    async def test_exists(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value=1)
        assert await r.exists("key") is True

    @pytest.mark.asyncio
    async def test_not_exists(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.execute = AsyncMock(return_value=0)
        assert await r.exists("key") is False


class TestUpstashRedisJson:
    @pytest.mark.asyncio
    async def test_set_json(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.set = AsyncMock(return_value=True)
        data = {"key": "value", "num": 123}
        assert await r.set_json("test_key", data, ex=60) is True
        r.set.assert_called_once_with("test_key", json.dumps(data, ensure_ascii=False), 60)

    @pytest.mark.asyncio
    async def test_get_json_success(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.get = AsyncMock(return_value='{"key": "value"}')
        result = await r.get_json("test_key")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_json_none(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.get = AsyncMock(return_value=None)
        assert await r.get_json("test_key") is None

    @pytest.mark.asyncio
    async def test_get_json_decode_error(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.enabled = True
        r.get = AsyncMock(return_value="invalid json{")
        assert await r.get_json("test_key") is None


class TestUpstashRedisClose:
    @pytest.mark.asyncio
    async def test_close(self):
        r = UpstashRedis.__new__(UpstashRedis)
        r.client = MagicMock()
        r.client.aclose = AsyncMock()
        await r.close()
        r.client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_client(self):
        r = UpstashRedis.__new__(UpstashRedis)
        # No client attribute
        await r.close()  # Should not raise


class TestGetUpstashRedis:
    def test_singleton(self):
        """测试单例模式"""
        import apps.api.services.upstash_redis as mod
        mod._upstash_redis = None
        with patch("apps.api.services.upstash_redis.settings") as mock_s:
            mock_s.upstash_redis_rest_url = None
            mock_s.upstash_redis_rest_token = None
            r1 = get_upstash_redis()
            r2 = get_upstash_redis()
            assert r1 is r2
        mod._upstash_redis = None
