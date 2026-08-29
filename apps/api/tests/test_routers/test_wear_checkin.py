"""
穿着打卡路由测试

覆盖 wardrobe.py 穿着打卡端点：
- POST /wardrobe/items/{item_id}/wear（首次打卡建日记 / 同日追加 / 同日幂等）
- DELETE /wardrobe/items/{item_id}/wear（撤销回退 / 空日记清理）

以及 diary_service 的穿着计数联动纯逻辑：
- _wardrobe_ids_from_items 过滤
- _adjust_wardrobe_wear 对每件衣物执行 wear_count 增量 + last_worn_date 重算
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from apps.api.routers.auth import get_current_user
from apps.api.schemas.diary import (
    DiaryResponse,
    DiaryListResponse,
    DiaryOutfitItemResponse,
    DiaryItemRequest,
)
from apps.api.services.diary_service import DiaryService
from apps.api.core.time_utils import today_cn


# 打卡写入的是「北京时间今日」，测试必须与生产共用同一取日逻辑，否则跨零点即失效
TODAY = today_cn()


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def make_diary(diary_id=10, items=None, **kw):
    now = datetime(2026, 8, 29, 9, 0)
    return DiaryResponse(
        id=diary_id,
        user_id=1,
        diary_date=TODAY,
        items=items or [],
        created_at=now,
        updated_at=now,
        **kw,
    )


def make_diary_item(row_id, wardrobe_item_id, diary_id=10):
    return DiaryOutfitItemResponse(
        id=row_id,
        diary_id=diary_id,
        item_source="wardrobe",
        wardrobe_item_id=wardrobe_item_id,
        category="上装",
        created_at=datetime(2026, 8, 29, 9, 0),
    )


@pytest.fixture
def patch_db():
    """patch DatabasePool.get_connection，cursor.fetchone 按序返回指定行"""

    def _apply(fetchone_results):
        cursor = MagicMock()
        cursor.fetchone.side_effect = list(fetchone_results)
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


def empty_diary_list():
    return DiaryListResponse(diaries=[], total=0, page=1, size=1)


def diary_list_with(diary):
    return DiaryListResponse(diaries=[diary], total=1, page=1, size=1)


# ============================================================
# POST /wardrobe/items/{item_id}/wear
# ============================================================

class TestWearCheckin:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post("/api/v1/wardrobe/items/5/wear")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_item_not_found(self, async_client, auth_headers, test_app, mock_user, patch_db):
        """衣物不存在/不归属 → 404"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        patcher, _ = patch_db([None])
        patcher.start()
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items/5/wear", headers=auth_headers
            )
            assert response.status_code == 404
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_first_checkin_creates_diary(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """今日无日记 → 创建日记并关联衣物，返回最新计数"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        # fetchone 顺序：归属查询 → 穿着统计查询
        patcher, _ = patch_db([
            {"id": 5, "category": "上装"},
            {"wear_count": 1, "last_worn_date": TODAY},
        ])
        patcher.start()
        with (
            patch("apps.api.routers.wardrobe.diary_service") as svc,
            patch("apps.api.routers.wardrobe._notify_diary_written"),
        ):
            svc.get_diaries.return_value = empty_diary_list()
            svc.create_diary.return_value = make_diary(items=[make_diary_item(100, 5)])
            try:
                response = await async_client.post(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 200
                body = response.json()
                assert body["diary_id"] == 10
                assert body["already_logged"] is False
                assert body["wear_count"] == 1

                # create_diary 收到的 items 必须是衣橱来源且携带该衣物
                req = svc.create_diary.call_args[0][1]
                assert req.diary_date == TODAY
                assert len(req.items) == 1
                assert req.items[0].item_source == "wardrobe"
                assert req.items[0].wardrobe_item_id == 5
                svc.add_item_to_diary.assert_not_called()
            finally:
                patcher.stop()
                test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_same_day_different_item_appends(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """今日已有日记（不含该衣物）→ 追加关联"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        existing = make_diary(items=[make_diary_item(100, 7)])
        patcher, _ = patch_db([
            {"id": 5, "category": "下装"},
            {"wear_count": 3, "last_worn_date": TODAY},
        ])
        patcher.start()
        with (
            patch("apps.api.routers.wardrobe.diary_service") as svc,
            patch("apps.api.routers.wardrobe._notify_diary_written"),
        ):
            svc.get_diaries.return_value = diary_list_with(existing)
            try:
                response = await async_client.post(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 200
                body = response.json()
                assert body["diary_id"] == 10
                assert body["already_logged"] is False
                svc.add_item_to_diary.assert_called_once()
                svc.create_diary.assert_not_called()
            finally:
                patcher.stop()
                test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_same_day_same_item_idempotent(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """今日日记已含该衣物 → already_logged=true，不重复写入"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        existing = make_diary(items=[make_diary_item(100, 5)])
        patcher, _ = patch_db([
            {"id": 5, "category": "上装"},
            {"wear_count": 2, "last_worn_date": TODAY},
        ])
        patcher.start()
        with patch("apps.api.routers.wardrobe.diary_service") as svc:
            svc.get_diaries.return_value = diary_list_with(existing)
            try:
                response = await async_client.post(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 200
                body = response.json()
                assert body["already_logged"] is True
                assert body["wear_count"] == 2
                svc.create_diary.assert_not_called()
                svc.add_item_to_diary.assert_not_called()
            finally:
                patcher.stop()
                test_app.dependency_overrides.clear()


# ============================================================
# DELETE /wardrobe/items/{item_id}/wear
# ============================================================

class TestUnwearCheckin:
    @pytest.mark.asyncio
    async def test_no_diary_today(self, async_client, auth_headers, test_app, mock_user):
        """今日无日记 → 404"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("apps.api.routers.wardrobe.diary_service") as svc:
            svc.get_diaries.return_value = empty_diary_list()
            try:
                response = await async_client.delete(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 404
            finally:
                test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_item_not_in_diary(self, async_client, auth_headers, test_app, mock_user):
        """今日日记不含该衣物 → 404"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        existing = make_diary(items=[make_diary_item(100, 7)])
        with patch("apps.api.routers.wardrobe.diary_service") as svc:
            svc.get_diaries.return_value = diary_list_with(existing)
            try:
                response = await async_client.delete(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 404
            finally:
                test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_removes_item_and_cleans_empty_diary(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """撤销 → 移除关联；日记变空 → 删除日记；计数回退"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        existing = make_diary(items=[make_diary_item(100, 5)])
        patcher, _ = patch_db([
            {"wear_count": 0, "last_worn_date": None},
        ])
        patcher.start()
        with patch("apps.api.routers.wardrobe.diary_service") as svc:
            svc.get_diaries.return_value = diary_list_with(existing)
            # 移除后日记为空（无衣物/照片/备注）
            svc.get_diary_by_id.return_value = make_diary(items=[])
            try:
                response = await async_client.delete(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 200
                body = response.json()
                assert body["cancelled"] is True
                assert body["wear_count"] == 0
                svc.remove_item_from_diary.assert_called_once_with(10, 1, 100)
                svc.delete_diary.assert_called_once_with(10, 1)
            finally:
                patcher.stop()
                test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_keeps_diary_with_photos(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """撤销后日记仍有照片 → 不删除日记"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        existing = make_diary(items=[make_diary_item(100, 5)])
        patcher, _ = patch_db([
            {"wear_count": 1, "last_worn_date": TODAY},
        ])
        patcher.start()
        with patch("apps.api.routers.wardrobe.diary_service") as svc:
            svc.get_diaries.return_value = diary_list_with(existing)
            svc.get_diary_by_id.return_value = make_diary(
                items=[], image_urls=["http://img.com/a.jpg"]
            )
            try:
                response = await async_client.delete(
                    "/api/v1/wardrobe/items/5/wear", headers=auth_headers
                )
                assert response.status_code == 200
                svc.remove_item_from_diary.assert_called_once()
                svc.delete_diary.assert_not_called()
            finally:
                patcher.stop()
                test_app.dependency_overrides.clear()


# ============================================================
# diary_service 穿着计数联动（纯逻辑层）
# ============================================================

class TestWearCountAdjust:
    def test_wardrobe_ids_from_items_filters(self):
        items = [
            DiaryItemRequest(item_source="wardrobe", wardrobe_item_id=1, category="上装"),
            DiaryItemRequest(item_source="seed", seed_item_code="S001"),
            DiaryItemRequest(item_source="wardrobe", wardrobe_item_id=None),
            DiaryItemRequest(item_source="wardrobe", wardrobe_item_id=3, category="鞋履"),
        ]
        assert DiaryService._wardrobe_ids_from_items(items) == [1, 3]

    def test_adjust_wear_executes_increment_and_recompute(self):
        """每件衣物：1 条 wear_count 增量 UPDATE + 1 条 last_worn_date 重算 UPDATE"""
        cur = MagicMock()
        DiaryService._adjust_wardrobe_wear(cur, user_id=1, wardrobe_item_ids=[1, 2], delta=1)
        assert cur.execute.call_count == 4
        first_sql = cur.execute.call_args_list[0][0][0]
        assert "wear_count = COALESCE(wear_count, 0) + %s" in first_sql
        recompute_sql = cur.execute.call_args_list[1][0][0]
        assert "MAX(d.diary_date)" in recompute_sql

    def test_adjust_wear_decrement_floors_at_zero(self):
        cur = MagicMock()
        DiaryService._adjust_wardrobe_wear(cur, user_id=1, wardrobe_item_ids=[9], delta=-1)
        decrement_sql = cur.execute.call_args_list[0][0][0]
        assert "GREATEST(COALESCE(wear_count, 0) - %s, 0)" in decrement_sql
