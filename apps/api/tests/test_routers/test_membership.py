"""
会员路由测试
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestMembershipRouter:
    """会员路由测试"""

    @pytest.mark.asyncio
    async def test_get_status_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/membership/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_plans_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/membership/plans")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_subscribe_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post(
            "/api/v1/membership/subscribe",
            json={"plan": "monthly", "payment_method": "mock"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cancel_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post("/api/v1/membership/cancel?subscription_id=1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upgrade_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post(
            "/api/v1/membership/upgrade",
            json={"new_plan": "yearly"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_renew_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post(
            "/api/v1/membership/renew",
            json={"payment_method": "mock"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_status_authenticated(self, async_client, auth_headers, mock_db_pool, test_app):
        """已认证获取会员状态"""
        from apps.api.routers.auth import get_current_user

        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/membership/status",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["plan"] == "free"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_plans_authenticated(self, async_client, auth_headers, test_app):
        """已认证获取套餐列表"""
        from apps.api.routers.auth import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/membership/plans",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["plans"]) == 3
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_quota_no_auth(self, async_client):
        """未认证配额检查返回401"""
        response = await async_client.get("/api/v1/membership/quota/daily_recommendations")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_quota_check(self, async_client, auth_headers, mock_db_pool, test_app):
        """配额检查"""
        from apps.api.routers.auth import get_current_user

        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/membership/quota/ai_review",
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()
