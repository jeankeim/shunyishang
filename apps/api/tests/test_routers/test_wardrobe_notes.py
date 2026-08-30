"""
衣物故事（user_wardrobe.notes）写入通路测试（批次三 3.4）

覆盖：
- POST /wardrobe/items 携带 notes 落库、空白落 NULL、超长 422
- PATCH /wardrobe/items/{id} 写故事、空串清空为 NULL、未传字段不进 UPDATE
- 越权/不存在统一 404（UPDATE 带 user_id 与 is_active 条件）

DB 全部以 mock cursor 驱动：断言实际执行的 SQL 与参数，不连真实库。
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def make_row(**overrides):
    """衣橱 RETURNING 行（WardrobeItemResponse 必填字段齐全）"""
    row = {
        "id": 1,
        "user_id": 1,
        "item_code": None,
        "name": "白衬衫",
        "category": "上装",
        "image_url": None,
        "primary_element": "金",
        "secondary_element": None,
        "attributes_detail": {},
        "is_custom": True,
        "is_active": True,
        "wear_count": 2,
        "last_worn_date": None,
        "is_favorite": False,
        "notes": None,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
        "gender": "中性",
        "applicable_weather": [],
        "applicable_seasons": [],
        "temperature_range": None,
        "functionality": [],
        "thickness_level": None,
        "energy_intensity": None,
    }
    row.update(overrides)
    return row


@pytest.fixture
def patch_db():
    """patch DatabasePool，fetchone 固定返回衣橱行，并暴露 cursor 供断言 SQL"""

    def _apply(row):
        cursor = MagicMock()
        cursor.fetchone.return_value = row
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=conn)
        cm.__exit__ = MagicMock(return_value=False)
        patcher = patch(
            "apps.api.core.database.DatabasePool.get_connection", return_value=cm
        )
        return patcher, cursor

    return _apply


def first_statement(cursor):
    """(SQL, 参数) 元组，取第一条 execute（添加/更新端点只发一条写库语句）"""
    call = cursor.execute.call_args_list[0]
    return " ".join(call.args[0].split()), call.args[1]


# ============================================================
# PATCH /wardrobe/items/{item_id} —— 故事的写与清空
# ============================================================

class TestPatchNotes:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.patch(
            "/api/v1/wardrobe/items/1", json={"notes": "毕业旅行买的"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_write_story(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """写故事：notes 进 SET 子句，参数为原文"""
        patcher, cursor = patch_db(make_row(notes="毕业旅行买的"))
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={"notes": "毕业旅行买的"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["notes"] == "毕业旅行买的"
            sql, params = first_statement(cursor)
            assert "notes = %s" in sql
            assert "毕业旅行买的" in params
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_blank_story_clears_to_null(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """全空格视为清空，落库统一用 NULL"""
        patcher, cursor = patch_db(make_row())
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={"notes": "   "},
                headers=auth_headers,
            )
            assert response.status_code == 200
            sql, params = first_statement(cursor)
            assert "notes = %s" in sql
            assert None in params
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_over_100_chars_rejected(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """超过 100 字 422，不落库"""
        patcher, cursor = patch_db(make_row())
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={"notes": "衣" * 101},
                headers=auth_headers,
            )
            assert response.status_code == 422
            cursor.execute.assert_not_called()
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_notes_omitted_keeps_existing(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """未传 notes 时不进 SET，避免改名称误清空故事"""
        patcher, cursor = patch_db(make_row(name="新名称", notes="旧故事"))
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={"name": "新名称"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            sql, _ = first_statement(cursor)
            assert "notes = %s" not in sql
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_other_users_item_rejected(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """UPDATE 带归属与 active 条件，他人衣物（或已停用）拿不到行 → 404"""
        patcher, cursor = patch_db(None)
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/999",
                json={"notes": "不该写进去"},
                headers=auth_headers,
            )
            assert response.status_code == 404
            sql, params = first_statement(cursor)
            assert "user_id = %s" in sql
            assert "is_active = TRUE" in sql
            assert params[-2:] == [999, 1]
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_only_notes_is_a_valid_update(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """只传 notes 不算「没有需要更新的字段」"""
        patcher, _ = patch_db(make_row(notes="妈妈送的"))
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={"notes": "妈妈送的"},
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()


# ============================================================
# POST /wardrobe/items —— 添加时一并写故事
# ============================================================

class TestAddNotes:
    @pytest.mark.asyncio
    async def test_add_with_notes(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        patcher, cursor = patch_db(make_row(notes="第一次面试穿的"))
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                response = await async_client.post(
                    "/api/v1/wardrobe/items",
                    json={
                        "name": "白衬衫",
                        "category": "上装",
                        "primary_element": "金",
                        "notes": "第一次面试穿的",
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 200
            sql, params = first_statement(cursor)
            assert "notes" in sql.split("INSERT INTO user_wardrobe (")[1].split(")")[0]
            assert params[-1] == "第一次面试穿的"
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_add_blank_notes_stores_null(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        patcher, cursor = patch_db(make_row())
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                response = await async_client.post(
                    "/api/v1/wardrobe/items",
                    json={
                        "name": "白衬衫",
                        "category": "上装",
                        "primary_element": "金",
                        "notes": "  ",
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 200
            assert cursor.execute.call_args_list[0].args[1][-1] is None
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_add_over_100_chars_rejected(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        patcher, cursor = patch_db(make_row())
        patcher.start()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items",
                json={"name": "白衬衫", "primary_element": "金", "notes": "a" * 101},
                headers=auth_headers,
            )
            assert response.status_code == 422
            cursor.execute.assert_not_called()
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()
