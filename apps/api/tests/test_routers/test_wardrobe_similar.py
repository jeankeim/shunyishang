"""
衣橱相似款端点测试
覆盖: GET /api/v1/recommend/wardrobe-similar
"""

import pytest

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def _src_row(**overrides):
    base = {
        "item_code": "TC001",
        "name": "白色衬衫",
        "category": "上装",
        "embedding": "[0.1,0.2,0.3]",
    }
    base.update(overrides)
    return base


class TestWardrobeSimilar:
    @pytest.mark.asyncio
    async def test_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _src_row()
        mock_cursor.fetchall.return_value = [
            {
                "id": 101, "name": "米白衬衫", "category": "上装",
                "image_url": "/uploads/x.jpg", "primary_element": "金",
                "secondary_element": None, "similarity": 0.87,
            },
            {
                "id": 102, "name": "浅蓝衬衣", "category": "上装",
                "image_url": None, "primary_element": "水",
                "secondary_element": "木", "similarity": 0.7432,
            },
        ]
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = await async_client.get(
            "/api/v1/recommend/wardrobe-similar?item_code=TC001", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_item"] == {"item_code": "TC001", "name": "白色衬衫", "category": "上装"}
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == 101
        assert data["items"][0]["similarity"] == 0.87
        # 相似度保留3位小数
        assert data["items"][1]["similarity"] == 0.743
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_item_not_found_404(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = await async_client.get(
            "/api/v1/recommend/wardrobe-similar?item_code=NOPE", headers=auth_headers
        )
        assert response.status_code == 404
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_source_without_embedding_returns_empty(
        self, async_client, auth_headers, test_app, mock_db_pool, mock_user
    ):
        """源单品无向量时不报错，返回空列表由前端展示空态"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _src_row(embedding=None)
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = await async_client.get(
            "/api/v1/recommend/wardrobe-similar?item_code=TC001", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        # 不应执行第二次衣橱检索
        assert mock_cursor.execute.call_count == 1
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_no_similar_items(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _src_row()
        mock_cursor.fetchall.return_value = []
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = await async_client.get(
            "/api/v1/recommend/wardrobe-similar?item_code=TC001", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["items"] == []
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        response = await async_client.get("/api/v1/recommend/wardrobe-similar?item_code=TC001")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_limit_param(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _src_row()
        mock_cursor.fetchall.return_value = []
        test_app.dependency_overrides[get_current_user] = lambda: mock_user

        response = await async_client.get(
            "/api/v1/recommend/wardrobe-similar?item_code=TC001&limit=5", headers=auth_headers
        )
        assert response.status_code == 200
        # limit 透传到 SQL 参数
        sql_params = mock_cursor.execute.call_args_list[-1].args[1]
        assert sql_params["limit"] == 5
        assert sql_params["category"] == "上装"
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_limit_rejected(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        response = await async_client.get(
            "/api/v1/recommend/wardrobe-similar?item_code=TC001&limit=99", headers=auth_headers
        )
        assert response.status_code == 422
        test_app.dependency_overrides.clear()
