"""
异步任务服务 + 任务路由 + worker 测试
覆盖: task_service.py, routers/tasks.py, apps/worker/main.py
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def _mock_db_context():
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.get_connection.return_value = mock_conn
    return mock_db, mock_cursor


# ======================== task_service ========================

class TestTaskService:

    def test_create_task(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {"id": "abc-123"}
        with patch("apps.api.services.task_service.DatabasePool", mock_db):
            from apps.api.services import task_service
            task_id = task_service.create_task(1, "annual_report", {"year": 2026})
        assert task_id == "abc-123"
        sql, params = mock_cursor.execute.call_args.args
        assert "INSERT INTO tasks" in sql
        assert params[0] == 1
        assert params[1] == "annual_report"
        assert json.loads(params[2]) == {"year": 2026}

    def test_get_task_found(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {
            "id": "abc-123", "task_type": "annual_report", "status": "done",
            "result": {"id": 1}, "error": None,
            "created_at": "2026-01-01", "started_at": None, "finished_at": None,
        }
        with patch("apps.api.services.task_service.DatabasePool", mock_db):
            from apps.api.services import task_service
            task = task_service.get_task("abc-123", 1)
        assert task["status"] == "done"
        assert task["result"] == {"id": 1}

    def test_get_task_not_found(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = None
        with patch("apps.api.services.task_service.DatabasePool", mock_db):
            from apps.api.services import task_service
            assert task_service.get_task("nope", 1) is None

    def test_claim_task_uses_skip_locked(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {
            "id": "abc-123", "user_id": 1, "task_type": "annual_report",
            "payload": {"year": 2026}, "retries": 0,
        }
        with patch("apps.api.services.task_service.DatabasePool", mock_db):
            from apps.api.services import task_service
            task = task_service.claim_task()
        assert task["id"] == "abc-123"
        sql = mock_cursor.execute.call_args.args[0]
        assert "FOR UPDATE SKIP LOCKED" in sql

    def test_mark_failed_requeues_below_max_retries(self):
        mock_db, mock_cursor = _mock_db_context()
        with patch("apps.api.services.task_service.DatabasePool", mock_db):
            from apps.api.services import task_service
            task_service.mark_failed("abc-123", "boom", retries=0)
        sql = mock_cursor.execute.call_args.args[0]
        assert "retries + 1" in sql
        assert "'pending'" in sql

    def test_mark_failed_final_at_max_retries(self):
        mock_db, mock_cursor = _mock_db_context()
        with patch("apps.api.services.task_service.DatabasePool", mock_db):
            from apps.api.services import task_service
            task_service.mark_failed("abc-123", "boom", retries=task_service.MAX_RETRIES)
        sql = mock_cursor.execute.call_args.args[0]
        assert "'failed'" in sql


# ======================== routers/tasks ========================

class TestTasksRouter:

    @pytest.mark.asyncio
    async def test_get_task_status(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.services.task_service.get_task") as mock_get:
                mock_get.return_value = {"id": "abc-123", "status": "done", "result": {"id": 1}}
                response = await async_client.get("/api/v1/tasks/abc-123", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["status"] == "done"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.services.task_service.get_task", return_value=None):
                response = await async_client.get("/api/v1/tasks/nope", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_task_no_auth(self, async_client):
        response = await async_client.get("/api/v1/tasks/abc-123")
        assert response.status_code == 401


# ======================== worker ========================

class TestWorker:

    def test_run_once_no_task(self):
        from apps.worker import main as worker_main
        with patch.object(worker_main.task_service, "claim_task", return_value=None):
            assert worker_main.run_once() is False

    def test_run_once_success(self):
        from apps.worker import main as worker_main
        task = {"id": "abc-123", "user_id": 1, "task_type": "annual_report",
                "payload": {"year": 2026}, "retries": 0}
        with patch.object(worker_main.task_service, "claim_task", return_value=task), \
             patch.object(worker_main.task_service, "mark_done") as mock_done, \
             patch.dict(worker_main.HANDLERS, {"annual_report": lambda uid, p: {"id": 9}}):
            assert worker_main.run_once() is True
        mock_done.assert_called_once_with("abc-123", {"id": 9})

    def test_run_once_handler_failure(self):
        from apps.worker import main as worker_main

        def boom(uid, p):
            raise RuntimeError("AI down")

        task = {"id": "abc-123", "user_id": 1, "task_type": "annual_report",
                "payload": {"year": 2026}, "retries": 0}
        with patch.object(worker_main.task_service, "claim_task", return_value=task), \
             patch.object(worker_main.task_service, "mark_failed") as mock_failed, \
             patch.dict(worker_main.HANDLERS, {"annual_report": boom}):
            assert worker_main.run_once() is True
        mock_failed.assert_called_once_with("abc-123", "AI down", retries=0)

    def test_run_once_unknown_task_type(self):
        from apps.worker import main as worker_main
        task = {"id": "abc-123", "user_id": 1, "task_type": "whatever",
                "payload": {}, "retries": 0}
        with patch.object(worker_main.task_service, "claim_task", return_value=task), \
             patch.object(worker_main.task_service, "mark_failed") as mock_failed:
            assert worker_main.run_once() is True
        assert mock_failed.called
