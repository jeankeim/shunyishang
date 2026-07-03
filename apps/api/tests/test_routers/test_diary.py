"""
日记路由测试
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime


class TestDiaryRouter:
    """日记路由测试"""

    @pytest.mark.asyncio
    async def test_create_diary_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post(
            "/api/v1/diary",
            json={"diary_date": "2025-01-15", "mood": "happy"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_diary(self, async_client, auth_headers, mock_db_pool, test_app):
        """测试创建日记"""
        from apps.api.routers.auth import get_current_user

        created_at = datetime(2025, 1, 15, 10, 0, 0)
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = {
            "id": 1, "user_id": 1, "diary_date": date(2025, 1, 15),
            "mood": "happy", "weather_snapshot": {}, "occasion": None,
            "notes": None, "rating": 4, "ai_review": {},
            "image_urls": [], "created_at": created_at, "updated_at": created_at,
        }
        mock_cursor.fetchall.return_value = []

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.post(
                "/api/v1/diary",
                json={
                    "diary_date": "2025-01-15",
                    "mood": "happy",
                    "rating": 4,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_diaries_no_auth(self, async_client):
        """未认证时列表返回401"""
        response = await async_client.get("/api/v1/diary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_calendar_no_auth(self, async_client):
        """未认证时日历返回401"""
        response = await async_client.get("/api/v1/diary/calendar?year=2025&month=1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stats_no_auth(self, async_client):
        """未认证时统计返回401"""
        response = await async_client.get("/api/v1/diary/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_diary_detail_no_auth(self, async_client):
        """未认证时详情返回401"""
        response = await async_client.get("/api/v1/diary/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_diary_no_auth(self, async_client):
        """未认证时更新返回401"""
        response = await async_client.put("/api/v1/diary/1", json={"mood": "sad"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_diary_no_auth(self, async_client):
        """未认证时删除返回401"""
        response = await async_client.delete("/api/v1/diary/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_item_no_auth(self, async_client):
        """未认证时添加衣物返回401"""
        response = await async_client.post(
            "/api/v1/diary/1/items",
            json={"item_source": "wardrobe", "wardrobe_item_id": 1},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_remove_item_no_auth(self, async_client):
        """未认证时移除衣物返回401"""
        response = await async_client.delete("/api/v1/diary/1/items/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_review_no_auth(self, async_client):
        """未认证时触发点评返回401"""
        response = await async_client.post("/api/v1/diary/1/review")
        assert response.status_code == 401
