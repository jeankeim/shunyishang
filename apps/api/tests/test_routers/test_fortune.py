"""
运势路由测试
"""

import pytest
from unittest.mock import patch


class TestFortuneRouter:
    """运势路由测试"""

    @pytest.mark.asyncio
    async def test_today_fortune_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/fortune/today")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_fortune_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/fortune?date=2025-07-01")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_fortune_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post("/api/v1/fortune/generate")
        assert response.status_code == 401
