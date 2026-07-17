"""
社区路由测试
覆盖: apps/api/routers/community.py (149行未覆盖, 18%)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com",
            "nickname": "测试用户", "username": "testuser", "avatar_url": None}


def _post_row(**overrides):
    base = {
        "id": 1, "user_id": 1, "diary_id": None, "content": "今日穿搭分享",
        "image_urls": [], "tags": ["穿搭"], "element": "火",
        "view_count": 10, "like_count": 5, "comment_count": 2,
        "is_featured": False, "published_at": datetime.now(), "created_at": datetime.now(),
        "is_liked": False, "author_name": "测试用户", "author_avatar": None,
    }
    base.update(overrides)
    return base


def _comment_row(**overrides):
    base = {
        "id": 1, "post_id": 1, "user_id": 1, "content": "好看！",
        "parent_id": None, "created_at": datetime.now(),
        "author_name": "测试用户", "author_avatar": None,
    }
    base.update(overrides)
    return base


class TestHelperFunctions:
    def test_get_user_id(self):
        from apps.api.routers.community import _get_user_id
        assert _get_user_id({"id": 1}) == 1
        assert _get_user_id({"user_id": 2}) == 2

    def test_get_user_id_missing(self):
        from apps.api.routers.community import _get_user_id
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _get_user_id({})

    def test_row_to_post(self):
        from apps.api.routers.community import _row_to_post
        row = _post_row()
        result = _row_to_post(row, 1)
        assert result.id == 1
        assert result.content == "今日穿搭分享"


class TestCreatePost:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post("/api/v1/community/posts", json={"content": "test"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _post_row()

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.community.check_content", return_value=(True, "")):
                response = await async_client.post(
                    "/api/v1/community/posts",
                    json={"content": "今日穿搭分享", "element": "火"},
                    headers=auth_headers,
                )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_content_blocked(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.community.check_content", return_value=(False, "内容违规")):
                response = await async_client.post(
                    "/api/v1/community/posts",
                    json={"content": "违规内容"},
                    headers=auth_headers,
                )
            assert response.status_code == 400
        finally:
            test_app.dependency_overrides.clear()


class TestListPosts:
    @pytest.mark.asyncio
    async def test_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = [_post_row()]
        mock_cursor.fetchone.return_value = {"total": 1}

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/community/posts", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_with_filters(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = {"total": 0}

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get(
                "/api/v1/community/posts?element=火&featured=true", headers=auth_headers
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestGetPost:
    @pytest.mark.asyncio
    async def test_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _post_row()

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/community/posts/1", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/community/posts/999", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestDeletePost:
    @pytest.mark.asyncio
    async def test_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.rowcount = 1

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/community/posts/1", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_not_author(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.rowcount = 0

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/community/posts/999", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestPostByDiary:
    @pytest.mark.asyncio
    async def test_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _post_row(diary_id=1)

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/community/posts/by-diary/1", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/community/posts/by-diary/999", headers=auth_headers)
            assert response.status_code == 200
            assert response.json() is None
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_by_diary(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.rowcount = 1

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/community/posts/by-diary/1", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestToggleLike:
    @pytest.mark.asyncio
    async def test_like(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.side_effect = [
            None,  # not yet liked
            {"element": "火", "tags": ["穿搭"]},  # post info for preference
        ]

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.community.preference_service"):
                response = await async_client.post(
                    "/api/v1/community/posts/1/like", headers=auth_headers
                )
            assert response.status_code == 200
            assert response.json()["action"] == "liked"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unlike(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.side_effect = [
            {"id": 1},  # already liked
            {"element": "火", "tags": []},  # post info
        ]

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.community.preference_service"):
                response = await async_client.post(
                    "/api/v1/community/posts/1/like", headers=auth_headers
                )
            assert response.status_code == 200
            assert response.json()["action"] == "unliked"
        finally:
            test_app.dependency_overrides.clear()


class TestComments:
    @pytest.mark.asyncio
    async def test_list_comments(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = [_comment_row()]
        mock_cursor.fetchone.return_value = {"total": 1}

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/community/posts/1/comments", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_comment(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.side_effect = [
            (1,),  # post exists check
            _comment_row(),  # INSERT RETURNING
        ]

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.community.check_content", return_value=(True, "")):
                response = await async_client.post(
                    "/api/v1/community/posts/1/comments",
                    json={"content": "好看！"},
                    headers=auth_headers,
                )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_comment_post_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.community.check_content", return_value=(True, "")):
                response = await async_client.post(
                    "/api/v1/community/posts/999/comments",
                    json={"content": "评论"},
                    headers=auth_headers,
                )
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_comment(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = {"post_id": 1}

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/community/comments/1", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_comment_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/community/comments/999", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()
