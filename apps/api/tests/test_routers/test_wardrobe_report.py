"""
衣橱年度报告路由测试（批次三 3.2）

覆盖 wardrobe.py 年度报告端点：
- POST /wardrobe/report（提交异步任务 / 额度用尽 429 / 入队失败回退额度）
- GET  /wardrobe/report（report + quota 结构、年份默认值、入参校验）

DB 与 LLM 全部 mock，不连真实库。
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def _report_service_stub(**overrides):
    """构造一个只带必要方法的 service 替身"""
    stub = MagicMock()
    stub.acquire_quota.return_value = overrides.get("acquire_quota", 42)
    stub.get_report.return_value = overrides.get("get_report")
    stub.get_quota.return_value = overrides.get(
        "get_quota", {"year": 2026, "used": 1, "limit": 3, "remaining": 2}
    )
    return stub


# ============================================================
# POST /wardrobe/report
# ============================================================

class TestGenerateWardrobeReport:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post("/api/v1/wardrobe/report")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_task_id(self, async_client, auth_headers, test_app, mock_user):
        """额度可用时提交异步任务，返回 202 + task_id"""
        stub = _report_service_stub()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
            ), patch(
                "apps.api.services.task_service.create_task", return_value="uuid-77"
            ) as mock_create:
                response = await async_client.post(
                    "/api/v1/wardrobe/report", headers=auth_headers
                )
            assert response.status_code == 202
            body = response.json()
            assert body["task_id"] == "uuid-77"
            assert body["status"] == "pending"
            assert stub.acquire_quota.call_args.args == (1, body["year"])
            assert mock_create.call_args.kwargs["task_type"] == "wardrobe_report"
            assert mock_create.call_args.kwargs["payload"] == {"year": body["year"]}
            assert mock_create.call_args.kwargs["user_id"] == 1
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_year_passed_through(self, async_client, auth_headers, test_app, mock_user):
        stub = _report_service_stub()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
            ), patch(
                "apps.api.services.task_service.create_task", return_value="uuid-78"
            ) as mock_create:
                response = await async_client.post(
                    "/api/v1/wardrobe/report?year=2025", headers=auth_headers
                )
            assert response.status_code == 202
            assert stub.acquire_quota.call_args.args == (1, 2025)
            assert mock_create.call_args.kwargs["payload"] == {"year": 2025}
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_quota_exhausted_returns_429(
        self, async_client, auth_headers, test_app, mock_user
    ):
        """额度用尽：429 且不入队"""
        stub = _report_service_stub(acquire_quota=None)
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
            ), patch("apps.api.services.task_service.create_task") as mock_create:
                response = await async_client.post(
                    "/api/v1/wardrobe/report?year=2026", headers=auth_headers
                )
            assert response.status_code == 429
            assert "最多生成 3 次" in response.json()["detail"]
            mock_create.assert_not_called()
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_enqueue_failure_releases_quota(
        self, async_client, auth_headers, test_app, mock_user
    ):
        """入队失败要把已占的额度还回去"""
        stub = _report_service_stub()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
            ), patch(
                "apps.api.services.task_service.create_task",
                side_effect=RuntimeError("redis down"),
            ):
                response = await async_client.post(
                    "/api/v1/wardrobe/report?year=2026", headers=auth_headers
                )
            assert response.status_code == 503
            stub.release_quota.assert_called_once_with(1, 2026)
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_invalid_year_rejected(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/report?year=1999", headers=auth_headers
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()


# ============================================================
# GET /wardrobe/report
# ============================================================

class TestGetWardrobeReport:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/report")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_report_and_quota(self, async_client, auth_headers, test_app, mock_user):
        stub = _report_service_stub(
            get_report={"id": 7, "year": 2025, "status": "ready", "content": {}, "summary": "s"}
        )
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
            ):
                response = await async_client.get(
                    "/api/v1/wardrobe/report?year=2025", headers=auth_headers
                )
            assert response.status_code == 200
            body = response.json()
            assert body["year"] == 2025
            assert body["report"]["id"] == 7
            assert body["quota"]["remaining"] == 2
            stub.get_report.assert_called_once_with(1, 2025)
            stub.get_quota.assert_called_once_with(1, 2025)
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_defaults_to_current_year(self, async_client, auth_headers, test_app, mock_user):
        from apps.api.core.time_utils import today_cn

        stub = _report_service_stub()
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
            ):
                response = await async_client.get(
                    "/api/v1/wardrobe/report", headers=auth_headers
                )
            assert response.status_code == 200
            assert response.json()["year"] == today_cn().year
            assert response.json()["report"] is None
        finally:
            test_app.dependency_overrides.clear()


# ============================================================
# worker handler
# ============================================================

class TestWardrobeReportHandler:
    def test_handler_registered(self):
        from apps.worker.main import HANDLERS

        assert "wardrobe_report" in HANDLERS

    def test_handler_calls_service(self):
        from apps.worker import main as worker_main

        stub = MagicMock()
        stub.generate_report.return_value = {"id": 3, "status": "ready"}
        with patch(
            "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
        ):
            result = worker_main.HANDLERS["wardrobe_report"](1, {"year": 2026})
        assert result == {"id": 3, "status": "ready"}
        stub.generate_report.assert_called_once_with(1, 2026)
        stub.mark_failed.assert_not_called()

    def test_handler_marks_failed_on_error(self):
        from apps.worker import main as worker_main

        stub = MagicMock()
        stub.generate_report.side_effect = RuntimeError("llm down")
        with patch(
            "apps.api.services.wardrobe_report_service.wardrobe_report_service", stub
        ):
            with pytest.raises(RuntimeError, match="llm down"):
                worker_main.HANDLERS["wardrobe_report"](1, {"year": 2026})
        stub.mark_failed.assert_called_once_with(1, 2026)
