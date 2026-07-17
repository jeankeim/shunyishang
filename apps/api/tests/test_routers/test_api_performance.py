"""
API 端点性能测试
测试健康检查、推荐接口（缓存命中）、衣橱列表接口的响应时间
使用 mock 基础设施，不连接真实数据库或外部服务
"""

import time
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from apps.api.core.config import settings


class TestHealthCheckPerformance:
    """健康检查端点性能测试"""

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, async_client, mock_db_pool, mock_cache):
        """测试健康检查接口响应时间 < 500ms"""
        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = True
            mock_main_cache.enabled = True

            start = time.perf_counter()
            response = await async_client.get("/health")
            elapsed = time.perf_counter() - start

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            # 健康检查应 < 500ms（含测试客户端开销）
            assert elapsed < 0.5, f"健康检查响应过慢: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_health_check_repeated(self, async_client, mock_db_pool, mock_cache):
        """测试连续健康检查的稳定性"""
        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = False
            mock_main_cache.enabled = False

            times = []
            for _ in range(20):
                start = time.perf_counter()
                response = await async_client.get("/health")
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                assert response.status_code == 200

            avg_time = sum(times) / len(times)
            max_time = max(times)
            assert avg_time < 0.05, f"平均响应过慢: {avg_time:.3f}s"
            assert max_time < 0.2, f"最大响应过慢: {max_time:.3f}s"


class TestRecommendPerformance:
    """推荐接口性能测试"""

    @pytest.mark.asyncio
    async def test_recommend_cache_hit_performance(self, async_client, mock_cache):
        """测试推荐接口在缓存命中时的响应时间 < 500ms"""
        # 构造缓存命中场景
        cached_result = {
            "analysis": {
                "target_elements": ["金", "木"],
                "bazi_reasoning": None,
                "intent_reasoning": "用户需要商务穿搭",
                "scene": "商务",
            },
            "items": [
                {
                    "item_code": f"ITEM_{i:03d}",
                    "name": f"测试物品_{i}",
                    "category": "上装",
                    "primary_element": "金",
                    "final_score": 0.85,
                    "semantic_score": 0.78,
                    "wuxing_score": 0.6,
                    "source": "public",
                    "item_id": None,
                    "image_url": None,
                }
                for i in range(5)
            ],
            "reason": "根据您的商务场景，推荐金系和木系的衣物搭配。",
        }

        with (
            patch("apps.api.routers.recommend.settings") as mock_settings,
            patch("apps.api.routers.recommend.cache") as mock_rec_cache,
        ):
            mock_settings.redis_enabled = True
            mock_rec_cache.get = AsyncMock(return_value=cached_result)
            mock_rec_cache.set = AsyncMock(return_value=True)

            request_data = {
                "query": "明天面试穿什么",
                "scene": "面试",
                "retrieval_mode": "public",
                "top_k": 5,
            }

            start = time.perf_counter()
            response = await async_client.post(
                "/api/v1/recommend/stream",
                json=request_data,
            )
            elapsed = time.perf_counter() - start

            assert response.status_code == 200

            # 收集 SSE 事件
            content = response.text
            events = [line for line in content.split("\n") if line.startswith("data:")]
            assert len(events) >= 3  # analysis + items + token/done

            # 缓存命中时应 < 500ms
            assert elapsed < 0.5, f"缓存命中推荐过慢: {elapsed:.3f}s"


class TestWardrobeListPerformance:
    """衣橱列表接口性能测试"""

    @pytest.mark.asyncio
    async def test_wardrobe_list_response_time(self, async_client, mock_db_pool, auth_token):
        """测试衣橱列表接口响应时间 < 200ms"""
        mock_cursor = mock_db_pool["cursor"]

        # 模拟衣橱数据
        mock_rows = [
            {
                "id": i,
                "user_id": 1,
                "item_code": f"ITEM_{i:03d}",
                "name": f"测试衣物_{i}",
                "category": "上装",
                "image_url": "https://test.com/img.png",
                "primary_element": "金",
                "secondary_element": None,
                "attributes_detail": {},
                "is_custom": False,
                "is_active": True,
                "wear_count": 0,
                "last_worn_date": None,
                "is_favorite": False,
                "notes": None,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "gender": "中性",
                "applicable_weather": [],
                "applicable_seasons": [],
                "temperature_range": {},
                "functionality": [],
                "thickness_level": "适中",
                "energy_intensity": 0.5,
            }
            for i in range(1, 6)
        ]

        call_count = {"n": 0}

        def side_effect_fetchall():
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_rows  # 列表查询
            elif call_count["n"] == 2:
                return [{"primary_element": "金", "count": 5}]  # 统计
            return []

        def side_effect_fetchone():
            return {"total": 5}

        mock_cursor.fetchall.side_effect = side_effect_fetchall
        mock_cursor.fetchone.side_effect = side_effect_fetchone

        # Mock get_current_user 以返回测试用户
        with patch("apps.api.routers.wardrobe.get_current_user") as mock_get_user:
            mock_get_user.return_value = {"id": 1, "user_code": "test-001"}

            # 需要先绕过 Depends
            from apps.api.routers.auth import get_current_user
            async def override_get_user():
                return {"id": 1, "user_code": "test-001"}

            from apps.api.main import app
            app.dependency_overrides[get_current_user] = override_get_user

            try:
                start = time.perf_counter()
                response = await async_client.get("/api/v1/wardrobe/items?page=1&limit=20")
                elapsed = time.perf_counter() - start

                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert "total" in data

                # 衣橱列表应 < 200ms
                assert elapsed < 0.2, f"衣橱列表响应过慢: {elapsed:.3f}s"
            finally:
                app.dependency_overrides.clear()


class TestStaticEndpointPerformance:
    """静态端点性能测试"""

    @pytest.mark.asyncio
    async def test_root_redirect_performance(self, async_client):
        """测试根路径重定向性能"""
        start = time.perf_counter()
        response = await async_client.get("/", follow_redirects=False)
        elapsed = time.perf_counter() - start

        assert response.status_code == 307
        assert elapsed < 0.05, f"根路径重定向过慢: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_docs_endpoint_performance(self, async_client):
        """测试 API 文档端点性能"""
        start = time.perf_counter()
        response = await async_client.get("/docs")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        # API 文档加载应 < 200ms
        assert elapsed < 0.2, f"API 文档加载过慢: {elapsed:.3f}s"
