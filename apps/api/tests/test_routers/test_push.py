"""
推送路由测试
"""

import pytest
from unittest.mock import patch, MagicMock


class TestPushRouter:
    """推送路由测试"""

    @pytest.mark.asyncio
    async def test_get_settings_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/push/settings")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_settings_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.put(
            "/api/v1/push/settings",
            json={"enabled": False},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_history_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/push/history")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_unread_count_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/push/unread-count")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_mark_read_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post("/api/v1/push/1/read")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_push_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post(
            "/api/v1/push/register",
            json={"endpoint": "https://example.com"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_settings_authenticated(self, async_client, auth_headers, mock_db_pool, test_app):
        """已认证获取推送设置"""
        from apps.api.routers.auth import get_current_user

        mock_cursor = mock_db_pool["cursor"]
        # 第一次fetchone返回None（触发初始化），第二次也返回None
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/push/settings",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_unread_count_authenticated(self, async_client, auth_headers, mock_db_pool, test_app):
        """已认证获取未读数量"""
        from apps.api.routers.auth import get_current_user

        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = {"cnt": 3}

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/push/unread-count",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 3
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_wechat_callback(self, async_client):
        """微信支付回调（个人备案版：支付路由已禁用，返回404）"""
        response = await async_client.post(
            "/api/v1/payments/callback/wechat",
            json={"transaction_id": "TX-001", "status": "completed"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_alipay_callback(self, async_client):
        """支付宝回调（个人备案版：支付路由已禁用，返回404）"""
        response = await async_client.post(
            "/api/v1/payments/callback/alipay",
            json={"transaction_id": "TX-002", "status": "completed"},
        )
        assert response.status_code == 404
