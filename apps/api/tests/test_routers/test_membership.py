"""
会员路由测试

个人备案版：会员路由已禁用（main.py 中注释掉），所有功能免费开放。
测试验证路由确实返回 404（未注册）。
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestMembershipRouter:
    """会员路由测试（个人备案版已禁用）"""

    @pytest.mark.asyncio
    async def test_get_status_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.get("/api/v1/membership/status")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_plans_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.get("/api/v1/membership/plans")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_subscribe_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.post(
            "/api/v1/membership/subscribe",
            json={"plan": "monthly", "payment_method": "mock"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.post("/api/v1/membership/cancel?subscription_id=1")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upgrade_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.post(
            "/api/v1/membership/upgrade",
            json={"new_plan": "yearly"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_renew_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.post(
            "/api/v1/membership/renew",
            json={"payment_method": "mock"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_quota_disabled(self, async_client):
        """个人备案版：会员路由未注册，返回404"""
        response = await async_client.get("/api/v1/membership/quota/daily_recommendations")
        assert response.status_code == 404
