"""
缓存性能测试
测试缓存 get/set 性能、序列化/反序列化性能、大批量操作
"""

import time
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from apps.api.core.cache import RedisCache


class TestCacheGetSetPerformance:
    """缓存 get/set 性能测试"""

    @pytest.mark.asyncio
    async def test_cache_disabled_get_performance(self):
        """测试缓存禁用时的 get 性能（应极快返回 None）"""
        cache = RedisCache()
        cache.enabled = False

        start = time.perf_counter()
        for _ in range(10000):
            result = await cache.get("test:key")
        elapsed = time.perf_counter() - start

        assert result is None
        # 10000 次禁用缓存 get 应 < 50ms
        assert elapsed < 0.05, f"禁用缓存 get 过慢: {elapsed:.3f}s / 10000次"

    @pytest.mark.asyncio
    async def test_cache_disabled_set_performance(self):
        """测试缓存禁用时的 set 性能"""
        cache = RedisCache()
        cache.enabled = False

        start = time.perf_counter()
        for _ in range(10000):
            result = await cache.set("test:key", {"data": "value"})
        elapsed = time.perf_counter() - start

        assert result is False
        assert elapsed < 0.05, f"禁用缓存 set 过慢: {elapsed:.3f}s / 10000次"

    @pytest.mark.asyncio
    async def test_mock_cache_get_set_cycle(self, mock_cache):
        """测试 mock 缓存的 get/set 循环性能"""
        mock_cache.enabled = True
        # 使用 AsyncMock 使方法可 await
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)

        start = time.perf_counter()
        for i in range(1000):
            await mock_cache.set(f"key:{i}", {"value": i})
            result = await mock_cache.get(f"key:{i}")
        elapsed = time.perf_counter() - start

        # 2000 次 get/set 应 < 500ms
        assert elapsed < 0.5, f"Mock 缓存 get/set 循环过慢: {elapsed:.3f}s"


class TestCacheSerializationPerformance:
    """缓存序列化/反序列化性能测试"""

    def test_json_serialization_small(self):
        """测试小对象 JSON 序列化性能"""
        small_data = {
            "analysis": {"target_elements": ["金", "木"], "scene": "商务"},
            "items": [{"name": "白衬衫", "category": "上装"}] * 5,
            "reason": "推荐白色衬衫搭配。",
        }

        start = time.perf_counter()
        for _ in range(10000):
            serialized = json.dumps(small_data, ensure_ascii=False, default=str)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"小对象序列化过慢: {elapsed:.3f}s / 10000次"

    def test_json_deserialization_small(self):
        """测试小对象 JSON 反序列化性能"""
        serialized = json.dumps({
            "analysis": {"target_elements": ["金", "木"], "scene": "商务"},
            "items": [{"name": "白衬衫", "category": "上装"}] * 5,
            "reason": "推荐白色衬衫搭配。",
        }, ensure_ascii=False)

        start = time.perf_counter()
        for _ in range(10000):
            data = json.loads(serialized)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"小对象反序列化过慢: {elapsed:.3f}s / 10000次"

    def test_json_serialization_large(self):
        """测试大对象 JSON 序列化性能（模拟完整推荐结果）"""
        large_data = {
            "analysis": {
                "target_elements": ["金", "木", "水"],
                "bazi_reasoning": "八字分析结果" * 50,
                "scene": "商务",
            },
            "items": [
                {
                    "item_code": f"ITEM_{i:03d}",
                    "name": f"测试物品_{i}" * 5,
                    "category": "上装",
                    "primary_element": "金",
                    "final_score": 0.85,
                    "semantic_score": 0.78,
                    "wuxing_score": 0.6,
                    "source": "public",
                    "image_url": f"https://example.com/img_{i}.png",
                }
                for i in range(20)
            ],
            "reason": "这是一段较长的推荐理由文本" * 20,
        }

        start = time.perf_counter()
        for _ in range(1000):
            serialized = json.dumps(large_data, ensure_ascii=False, default=str)
            data = json.loads(serialized)
        elapsed = time.perf_counter() - start

        # 1000 次序列化+反序列化应 < 500ms
        assert elapsed < 0.5, f"大对象序列化/反序列化过慢: {elapsed:.3f}s / 1000次"


class TestBulkCacheOperations:
    """批量缓存操作测试"""

    @pytest.mark.asyncio
    async def test_bulk_cache_key_generation(self):
        """测试批量缓存 key 生成的性能"""
        import hashlib

        keys = []
        start = time.perf_counter()
        for i in range(10000):
            cache_key_raw = f"query_{i}|scene_商务|weather_金|user_1|vector|10"
            cache_key = f"recommend:{hashlib.md5(cache_key_raw.encode()).hexdigest()}"
            keys.append(cache_key)
        elapsed = time.perf_counter() - start

        assert len(keys) == 10000
        assert len(set(keys)) == 10000  # 所有 key 唯一
        # 10000 次 key 生成应 < 100ms
        assert elapsed < 0.1, f"缓存 key 生成过慢: {elapsed:.3f}s / 10000次"

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self):
        """测试缓存 TTL 配置合理性"""
        from apps.api.core.config import settings

        # 验证 TTL 配置合理
        assert settings.cache_ttl_bazi >= 3600, "八字缓存 TTL 应 >= 1小时"
        assert settings.cache_ttl_weather >= 300, "天气缓存 TTL 应 >= 5分钟"
        assert settings.cache_ttl_search >= 600, "搜索缓存 TTL 应 >= 10分钟"

    @pytest.mark.asyncio
    async def test_mock_cache_delete_performance(self, mock_cache):
        """测试缓存删除性能"""
        mock_cache.enabled = True
        mock_cache.delete = AsyncMock(return_value=True)

        start = time.perf_counter()
        for i in range(1000):
            await mock_cache.delete(f"key:{i}")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, f"缓存删除过慢: {elapsed:.3f}s / 1000次"
