"""
缓存服务测试 - RedisCache (Upstash REST API + 传统 Redis)
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from apps.api.core.cache import RedisCache, get_cached, set_cached, delete_cached


class TestRedisCacheDisabled:
    """缓存未启用时的行为"""

    def test_get_disabled(self):
        c = RedisCache()
        c.enabled = False
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(c.get("key"))
        assert result is None

    def test_set_disabled(self):
        c = RedisCache()
        c.enabled = False
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(c.set("key", "val"))
        assert result is False

    def test_delete_disabled(self):
        c = RedisCache()
        c.enabled = False
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(c.delete("key"))
        assert result is False

    def test_exists_disabled(self):
        c = RedisCache()
        c.enabled = False
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(c.exists("key"))
        assert result is False

    def test_get_sync_disabled(self):
        c = RedisCache()
        c.enabled = False
        assert c.get_sync("key") is None

    def test_set_sync_disabled(self):
        c = RedisCache()
        c.enabled = False
        assert c.set_sync("key", "val") is False

    def test_check_health_disabled(self):
        c = RedisCache()
        c.enabled = False
        assert c.check_health() is False


class TestRedisCacheUpstash:
    """Upstash Redis (REST API) 测试"""

    @pytest.fixture
    def upstash_cache(self):
        c = RedisCache()
        c.enabled = True
        c.use_upstash = True
        c.upstash_url = "https://test.upstash.io"
        c.upstash_token = "test-token"
        c.redis_client = None
        c._async_client = None
        c._sync_client = None
        return c

    @pytest.mark.asyncio
    async def test_upstash_get_hit(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": json.dumps({"data": "hello"})}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.get("test_key")
        assert result == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_upstash_get_miss(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": None}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_upstash_get_error(self, upstash_cache):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection error"))
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_upstash_set_success(self, upstash_cache):
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_resp1, mock_resp2])
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.set("test_key", {"v": 1}, ttl=60)
        assert result is True

    @pytest.mark.asyncio
    async def test_upstash_set_fail(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.set("test_key", "val")
        assert result is False

    @pytest.mark.asyncio
    async def test_upstash_delete(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.delete("test_key")
        assert result is True

    @pytest.mark.asyncio
    async def test_upstash_exists_true(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": 1}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.exists("test_key")
        assert result is True

    @pytest.mark.asyncio
    async def test_upstash_exists_false(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": 0}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        upstash_cache._get_async_client = MagicMock(return_value=mock_client)

        result = await upstash_cache.exists("test_key")
        assert result is False

    def test_upstash_get_sync_hit(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": json.dumps("sync_val")}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.get_sync("k") == "sync_val"

    def test_upstash_get_sync_miss(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": None}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.get_sync("k") is None

    def test_upstash_set_sync(self, upstash_cache):
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_client = MagicMock()
        mock_client.post.side_effect = [mock_resp1, mock_resp2]
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.set_sync("k", "v", ttl=30) is True

    def test_upstash_set_sync_fail(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.set_sync("k", "v") is False

    def test_upstash_check_health_ok(self, upstash_cache):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.check_health() is True

    def test_upstash_check_health_fail(self, upstash_cache):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("fail")
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.check_health() is False

    def test_upstash_get_sync_error(self, upstash_cache):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("err")
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.get_sync("k") is None

    def test_upstash_set_sync_error(self, upstash_cache):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("err")
        upstash_cache._get_sync_client = MagicMock(return_value=mock_client)

        assert upstash_cache.set_sync("k", "v") is False


class TestRedisCacheTraditional:
    """传统 Redis 测试"""

    @pytest.fixture
    def trad_cache(self):
        c = RedisCache()
        c.enabled = True
        c.use_upstash = False
        c.redis_client = MagicMock()
        return c

    @pytest.mark.asyncio
    async def test_redis_get_hit(self, trad_cache):
        trad_cache.redis_client.get.return_value = json.dumps({"v": 1})
        result = await trad_cache.get("k")
        assert result == {"v": 1}

    @pytest.mark.asyncio
    async def test_redis_get_miss(self, trad_cache):
        trad_cache.redis_client.get.return_value = None
        result = await trad_cache.get("k")
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_set(self, trad_cache):
        trad_cache.redis_client.setex.return_value = True
        result = await trad_cache.set("k", "v", ttl=60)
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_delete(self, trad_cache):
        trad_cache.redis_client.delete.return_value = 1
        assert await trad_cache.delete("k") is True

    @pytest.mark.asyncio
    async def test_redis_delete_miss(self, trad_cache):
        trad_cache.redis_client.delete.return_value = 0
        assert await trad_cache.delete("k") is False

    @pytest.mark.asyncio
    async def test_redis_exists(self, trad_cache):
        trad_cache.redis_client.exists.return_value = 1
        assert await trad_cache.exists("k") is True

    @pytest.mark.asyncio
    async def test_redis_get_error(self, trad_cache):
        trad_cache.redis_client.get.side_effect = Exception("err")
        assert await trad_cache.get("k") is None

    @pytest.mark.asyncio
    async def test_redis_set_error(self, trad_cache):
        trad_cache.redis_client.setex.side_effect = Exception("err")
        assert await trad_cache.set("k", "v") is False

    @pytest.mark.asyncio
    async def test_redis_delete_error(self, trad_cache):
        trad_cache.redis_client.delete.side_effect = Exception("err")
        assert await trad_cache.delete("k") is False

    @pytest.mark.asyncio
    async def test_redis_exists_error(self, trad_cache):
        trad_cache.redis_client.exists.side_effect = Exception("err")
        assert await trad_cache.exists("k") is False

    @pytest.mark.asyncio
    async def test_redis_get_no_client(self):
        c = RedisCache()
        c.enabled = True
        c.use_upstash = False
        c.redis_client = None
        assert await c.get("k") is None

    @pytest.mark.asyncio
    async def test_redis_set_no_client(self):
        c = RedisCache()
        c.enabled = True
        c.use_upstash = False
        c.redis_client = None
        assert await c.set("k", "v") is False

    @pytest.mark.asyncio
    async def test_redis_delete_no_client(self):
        c = RedisCache()
        c.enabled = True
        c.use_upstash = False
        c.redis_client = None
        assert await c.delete("k") is False

    def test_redis_check_health_ok(self, trad_cache):
        trad_cache.redis_client.ping.return_value = True
        assert trad_cache.check_health() is True

    def test_redis_check_health_no_client(self):
        c = RedisCache()
        c.enabled = True
        c.use_upstash = False
        c.redis_client = None
        assert c.check_health() is False


class TestRedisCacheInit:
    """初始化测试"""

    def test_init_client_upstash(self):
        c = RedisCache()
        c.use_upstash = True
        c.upstash_url = "https://test"
        # _init_client just logs
        c._init_client()

    def test_init_client_redis_import_error(self):
        c = RedisCache()
        c.use_upstash = False
        c.redis_url = "redis://localhost:6379/0"
        with patch("builtins.__import__", side_effect=ImportError("no redis")):
            c._init_client()
        assert c.enabled is False

    def test_init_client_redis_connection_error(self):
        c = RedisCache()
        c.use_upstash = False
        c.redis_url = "redis://localhost:6379/0"
        with patch.dict("sys.modules", {"redis": MagicMock(from_url=MagicMock(side_effect=Exception("conn fail")))}):
            c._init_client()
        assert c.enabled is False


class TestCacheHelperFunctions:
    """便捷函数测试"""

    @pytest.mark.asyncio
    async def test_get_cached(self):
        with patch("apps.api.core.cache.cache") as mock_c:
            mock_c.get = AsyncMock(return_value="val")
            result = await get_cached("k")
            assert result == "val"

    @pytest.mark.asyncio
    async def test_set_cached(self):
        with patch("apps.api.core.cache.cache") as mock_c:
            mock_c.set = AsyncMock(return_value=True)
            result = await set_cached("k", "v", ttl=60)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_cached(self):
        with patch("apps.api.core.cache.cache") as mock_c:
            mock_c.delete = AsyncMock(return_value=True)
            result = await delete_cached("k")
            assert result is True
