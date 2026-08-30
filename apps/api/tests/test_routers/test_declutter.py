"""
断舍离三态路由测试（批次三 3.1）

覆盖 wardrobe.py 断舍离端点：
- POST   /wardrobe/items/{item_id}/declutter（首次处理 / 改判幂等 / 动作校验 / 越权）
- DELETE /wardrobe/items/{item_id}/declutter（撤销恢复 active / 无记录 404）
- GET    /wardrobe/declutter-report（入参透传与登录校验）

DB 全部以 mock cursor 驱动：断言实际执行的 SQL 与参数，不连真实库。
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


@pytest.fixture
def patch_db():
    """patch DatabasePool，fetchone 按序返回指定行，并暴露 cursor 供断言 SQL"""

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


def executed_sql(cursor):
    """cursor.execute 实际收到的 SQL 列表（去空白便于断言）"""
    return [" ".join(call.args[0].split()) for call in cursor.execute.call_args_list]


# ============================================================
# POST /wardrobe/items/{item_id}/declutter
# ============================================================

class TestDeclutterItem:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/wardrobe/items/5/declutter", json={"action": "donate"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_action_rejected(self, async_client, auth_headers, test_app, mock_user):
        """非法动作直接 400，不碰数据库"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items/5/declutter",
                json={"action": "burn"},
                headers=auth_headers,
            )
            assert response.status_code == 400
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_note_too_long_rejected(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items/5/declutter",
                json={"action": "sell", "note": "很长" * 60},
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_item_not_found_or_not_owned(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """归属查询无行 → 404（他人衣物与不存在衣物同一语义）"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        patcher, cursor = patch_db([None])
        patcher.start()
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items/999/declutter",
                json={"action": "donate"},
                headers=auth_headers,
            )
            assert response.status_code == 404
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()
        # 归属不通过时不得写入处理记录
        assert not any("wardrobe_item_actions" in sql for sql in executed_sql(cursor))

    @pytest.mark.asyncio
    async def test_first_declutter_inserts_and_deactivates(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """首次处理：upsert 三态 + 置 is_active = FALSE，updated=false"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        # fetchone 顺序：归属 → 既有处理记录（无）
        patcher, cursor = patch_db([{"id": 5}, None])
        patcher.start()
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items/5/declutter",
                json={"action": "donate", "note": "小区捐赠箱"},
                headers=auth_headers,
            )
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["action"] == "donate"
        assert body["action_label"] == "捐赠"
        assert body["is_active"] is False
        assert body["updated"] is False

        sqls = executed_sql(cursor)
        assert any("INSERT INTO wardrobe_item_actions" in s for s in sqls)
        assert any("ON CONFLICT (user_id, wardrobe_item_id) DO UPDATE" in s for s in sqls)
        assert any("SET is_active = FALSE" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_repeat_declutter_is_idempotent_update(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """重复提交只改判动作（走 DO UPDATE 分支），updated=true，不产生第二条记录"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        patcher, cursor = patch_db([{"id": 5}, {"action": "donate"}])
        patcher.start()
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items/5/declutter",
                json={"action": "discard"},
                headers=auth_headers,
            )
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

        body = response.json()
        assert body["action"] == "discard"
        assert body["action_label"] == "舍弃"
        assert body["updated"] is True
        # 仍是一条 upsert，而不是第二次 INSERT 新行
        assert sum("INSERT INTO wardrobe_item_actions" in s for s in executed_sql(cursor)) == 1

    @pytest.mark.asyncio
    async def test_declutter_invalidates_insight_cache(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """处理衣物会改变衣橱构成，需清五行平衡仪表盘缓存"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        patcher, _ = patch_db([{"id": 5}, None])
        patcher.start()
        try:
            with patch("apps.api.core.config.settings.redis_enabled", True), \
                    patch("apps.api.core.cache.cache.delete_sync") as mock_delete:
                response = await async_client.post(
                    "/api/v1/wardrobe/items/5/declutter",
                    json={"action": "sell"},
                    headers=auth_headers,
                )
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

        assert response.status_code == 200
        mock_delete.assert_called_once_with("wardrobe_element_balance:1")


# ============================================================
# DELETE /wardrobe/items/{item_id}/declutter
# ============================================================

class TestUndoDeclutter:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.delete("/api/v1/wardrobe/items/5/declutter")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_undo_without_record(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """未标记处理的衣物无可撤销 → 404"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        patcher, cursor = patch_db([None])
        patcher.start()
        try:
            response = await async_client.delete(
                "/api/v1/wardrobe/items/5/declutter", headers=auth_headers
            )
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

        assert response.status_code == 404
        assert not any("SET is_active = TRUE" in s for s in executed_sql(cursor))

    @pytest.mark.asyncio
    async def test_undo_restores_active(
        self, async_client, auth_headers, test_app, mock_user, patch_db
    ):
        """撤销：删除处理记录并把衣物放回活跃衣橱"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        patcher, cursor = patch_db([{"id": 7}])
        patcher.start()
        try:
            response = await async_client.delete(
                "/api/v1/wardrobe/items/7/declutter", headers=auth_headers
            )
        finally:
            patcher.stop()
            test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == {"item_id": 7, "is_active": True}
        sqls = executed_sql(cursor)
        assert any("DELETE FROM wardrobe_item_actions" in s for s in sqls)
        assert any("SET is_active = TRUE" in s for s in sqls)


# ============================================================
# GET /wardrobe/declutter-report
# ============================================================

class TestDeclutterReportApi:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/declutter-report")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_default_year_is_none(self, async_client, auth_headers, test_app, mock_user):
        """不传 year 时由 service 兜底为当年"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch(
            "apps.api.services.wardrobe_analytics_service.get_declutter_report",
            return_value={"year": 2026, "total_processed": 0},
        ) as mock_report:
            response = await async_client.get(
                "/api/v1/wardrobe/declutter-report", headers=auth_headers
            )
        test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["total_processed"] == 0
        mock_report.assert_called_once_with(1, None)

    @pytest.mark.asyncio
    async def test_year_passed_through(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch(
            "apps.api.services.wardrobe_analytics_service.get_declutter_report",
            return_value={"year": 2025, "total_processed": 3},
        ) as mock_report:
            response = await async_client.get(
                "/api/v1/wardrobe/declutter-report?year=2025", headers=auth_headers
            )
        test_app.dependency_overrides.clear()

        assert response.status_code == 200
        mock_report.assert_called_once_with(1, 2025)

    @pytest.mark.asyncio
    async def test_year_out_of_range(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get(
                "/api/v1/wardrobe/declutter-report?year=1999", headers=auth_headers
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()
