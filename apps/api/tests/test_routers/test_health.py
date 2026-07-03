"""
健康检查端点冒烟测试
验证测试框架是否正常工作
"""

import pytest
from unittest.mock import patch


class TestHealthCheck:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client, mock_db_pool, mock_cache):
        """测试健康检查接口 - 数据库正常时返回 200"""
        with (
            patch("apps.api.main.check_db_health", return_value=True),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = False
            mock_main_cache.enabled = False

            response = await async_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["db"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_db_down(self, async_client):
        """测试健康检查接口 - 数据库异常时返回 503"""
        with (
            patch("apps.api.main.check_db_health", return_value=False),
            patch("apps.api.main.cache") as mock_main_cache,
        ):
            mock_main_cache.check_health.return_value = False
            mock_main_cache.enabled = False

            response = await async_client.get("/health")

            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_root_redirect(self, async_client):
        """测试根路径重定向到 /docs"""
        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/docs" in response.headers["location"]
