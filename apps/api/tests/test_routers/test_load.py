"""
负载测试
使用 asyncio 模拟并发请求，测试服务在不同并发级别下的表现
"""

import time
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from apps.api.core.cache import RedisCache


class TestConcurrentHealthCheck:
    """并发健康检查测试"""

    @pytest.mark.asyncio
    async def test_concurrent_health_10(self, async_client, mock_db_pool, mock_cache):
        """测试 10 并发健康检查"""
        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = True
            mock_main_cache.enabled = True

            async def single_request():
                start = time.perf_counter()
                response = await async_client.get("/health")
                elapsed = time.perf_counter() - start
                return response.status_code, elapsed

            start = time.perf_counter()
            tasks = [single_request() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            total_elapsed = time.perf_counter() - start

            # 所有请求都应成功
            status_codes = [r[0] for r in results]
            times = [r[1] for r in results]

            assert all(code == 200 for code in status_codes), f"有请求失败: {status_codes}"
            assert total_elapsed < 0.5, f"10 并发总耗时过长: {total_elapsed:.3f}s"
            assert max(times) < 0.2, f"单次最大响应过慢: {max(times):.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_health_50(self, async_client, mock_db_pool, mock_cache):
        """测试 50 并发健康检查"""
        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = False
            mock_main_cache.enabled = False

            async def single_request():
                response = await async_client.get("/health")
                return response.status_code

            tasks = [single_request() for _ in range(50)]
            start = time.perf_counter()
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start

            assert all(code == 200 for code in results), "50 并发有请求失败"
            assert elapsed < 1.0, f"50 并发总耗时过长: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_health_100(self, async_client, mock_db_pool, mock_cache):
        """测试 100 并发健康检查"""
        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = False
            mock_main_cache.enabled = False

            async def single_request():
                response = await async_client.get("/health")
                return response.status_code

            tasks = [single_request() for _ in range(100)]
            start = time.perf_counter()
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start

            success_count = sum(1 for code in results if code == 200)
            assert success_count == 100, f"100 并发中 {100 - success_count} 个请求失败"
            # 100 并发 mock 请求应 < 2s
            assert elapsed < 2.0, f"100 并发总耗时过长: {elapsed:.3f}s"


class TestConcurrentCacheConsistency:
    """并发缓存一致性测试"""

    @pytest.mark.asyncio
    async def test_concurrent_cache_read_write(self, mock_cache):
        """测试并发读写缓存的一致性"""
        mock_cache.enabled = True

        # 模拟缓存存储
        store = {}

        async def mock_set(key, value, ttl=None):
            store[key] = value
            return True

        async def mock_get(key):
            return store.get(key)

        mock_cache.set.side_effect = mock_set
        mock_cache.get.side_effect = mock_get

        # 并发写入
        write_tasks = []
        for i in range(50):
            write_tasks.append(mock_cache.set(f"key:{i}", {"value": i}))
        await asyncio.gather(*write_tasks)

        # 并发读取并验证
        read_tasks = []
        for i in range(50):
            read_tasks.append(mock_cache.get(f"key:{i}"))
        results = await asyncio.gather(*read_tasks)

        # 验证一致性
        for i, result in enumerate(results):
            assert result == {"value": i}, f"缓存不一致: key:{i}, expected={{'value': {i}}}, got={result}"

    @pytest.mark.asyncio
    async def test_cache_disabled_concurrent_access(self):
        """测试缓存禁用时的并发访问不会出错"""
        cache = RedisCache()
        cache.enabled = False

        async def cache_operation():
            result = await cache.get("test:key")
            assert result is None
            set_result = await cache.set("test:key", "value")
            assert set_result is False
            return True

        tasks = [cache_operation() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        assert all(r is True for r in results)


class TestMemoryLeakDetection:
    """内存泄漏检测测试"""

    @pytest.mark.asyncio
    async def test_repeated_requests_no_growth(self, async_client, mock_db_pool, mock_cache):
        """测试重复请求不会导致内存泄漏（通过对象数量验证）"""
        import gc

        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = False
            mock_main_cache.enabled = False

            # 收集初始垃圾回收状态
            gc.collect()
            initial_objects = len(gc.get_objects())

            # 执行 100 次请求
            for _ in range(100):
                response = await async_client.get("/health")
                assert response.status_code == 200

            # 再次垃圾回收
            gc.collect()
            final_objects = len(gc.get_objects())

            # 对象数量增长不应超过 10%（允许一些框架内部增长）
            growth_ratio = (final_objects - initial_objects) / max(initial_objects, 1)
            assert growth_ratio < 0.1, (
                f"可能的内存泄漏: 对象增长 {growth_ratio:.1%} "
                f"(初始: {initial_objects}, 最终: {final_objects})"
            )

    @pytest.mark.asyncio
    async def test_cache_client_reuse(self):
        """测试缓存客户端正确复用（不创建新连接）"""
        cache = RedisCache()
        cache.enabled = True
        cache.use_upstash = True
        cache.upstash_url = "https://test.upstash.io"
        cache.upstash_token = "test-token"
        cache._async_client = None  # 重置

        # 获取客户端两次，应复用同一个
        client1 = cache._get_async_client()
        client2 = cache._get_async_client()
        assert client1 is client2, "异步客户端未被复用"

        # 同步客户端也应复用
        sync_client1 = cache._get_sync_client()
        sync_client2 = cache._get_sync_client()
        assert sync_client1 is sync_client2, "同步客户端未被复用"

        # 清理
        await client1.aclose()
        sync_client1.close()


class TestConcurrentStaticEndpoints:
    """并发静态端点测试"""

    @pytest.mark.asyncio
    async def test_concurrent_root_redirect(self, async_client):
        """测试并发根路径重定向"""
        async def single_request():
            response = await async_client.get("/", follow_redirects=False)
            return response.status_code

        tasks = [single_request() for _ in range(20)]
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        assert all(code == 307 for code in results)
        assert elapsed < 0.5, f"20 并发重定向过慢: {elapsed:.3f}s"
