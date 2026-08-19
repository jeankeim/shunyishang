"""
后台管理路由鉴权回归测试（L3 安全审查整改）

覆盖 /api/v1/admin/* 的 ADMIN_USER_CODES 白名单强制执行：
- 未登录 → 401
- 已登录但不在白名单 → 全部路由 403
- 白名单为空 → 任何人均 403
- 白名单命中 → 200（服务层 mock，不触达真实 DB / 阿里云）
"""
import pytest
from unittest.mock import patch

from apps.api.core.config import settings
from apps.api.routers.auth import get_current_user

ADMIN_CODE = "admin-code-001"

ROUTES = [
    ("/api/v1/admin/me", "get"),
    ("/api/v1/admin/dashboard", "get"),
    ("/api/v1/admin/bills", "get"),
    ("/api/v1/admin/bills/sync", "post"),
    ("/api/v1/admin/llm-usage", "get"),
]


@pytest.fixture
def admin_user():
    """白名单内管理员"""
    return {"id": 1, "user_code": ADMIN_CODE, "nickname": "管理员"}


@pytest.fixture
def normal_user():
    """普通登录用户"""
    return {"id": 2, "user_code": "normal-code-002", "nickname": "测试用户"}


@pytest.fixture
def whitelist():
    """临时设置管理员白名单，结束恢复"""
    original = settings.admin_user_codes
    settings.admin_user_codes = ADMIN_CODE
    yield
    settings.admin_user_codes = original


class TestAdminAuthEnforcement:
    """鉴权强制执行：未登录 / 非管理员 / 空白名单"""

    @pytest.mark.asyncio
    async def test_unauthenticated_401(self, async_client):
        """未登录访问任一 admin 路由返回 401"""
        for path, method in ROUTES:
            response = await getattr(async_client, method)(path)
            assert response.status_code == 401, path

    @pytest.mark.asyncio
    async def test_non_admin_403_on_all_routes(self, async_client, test_app, normal_user, whitelist):
        """已登录但不在白名单：全部路由 403"""
        test_app.dependency_overrides[get_current_user] = lambda: normal_user
        try:
            for path, method in ROUTES:
                response = await getattr(async_client, method)(path)
                assert response.status_code == 403, path
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_empty_whitelist_denies_everyone(self, async_client, test_app, admin_user):
        """白名单为空：即使账号 code 匹配也 403（默认安全）"""
        original = settings.admin_user_codes
        settings.admin_user_codes = ""
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        try:
            for path, method in ROUTES:
                response = await getattr(async_client, method)(path)
                assert response.status_code == 403, path
        finally:
            test_app.dependency_overrides.clear()
            settings.admin_user_codes = original


class TestAdminAccess:
    """白名单命中：正常访问（服务层 mock）"""

    @pytest.mark.asyncio
    async def test_admin_me_ok(self, async_client, test_app, admin_user, whitelist):
        """管理员查询身份返回 is_admin=True"""
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        try:
            response = await async_client.get("/api/v1/admin/me")
            assert response.status_code == 200
            assert response.json()["is_admin"] is True
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_dashboard_ok(self, async_client, test_app, admin_user, whitelist):
        """管理员可访问运营看板"""
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        payload = {"today": {}, "totals": {}, "trend": []}
        try:
            with patch("apps.api.services.admin_stats_service.get_dashboard", return_value=payload):
                response = await async_client.get("/api/v1/admin/dashboard?days=7")
            assert response.status_code == 200
            assert response.json() == payload
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_bills_ok(self, async_client, test_app, admin_user, whitelist):
        """管理员可访问账单汇总"""
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        payload = {"configured": False, "total_pretax": 0, "by_product": [], "daily": [], "last_sync_at": None}
        try:
            with patch("apps.api.services.aliyun_billing_service.get_bill_summary", return_value=payload):
                response = await async_client.get("/api/v1/admin/bills")
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_bills_sync_ok(self, async_client, test_app, admin_user, whitelist):
        """管理员可手动同步账单"""
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        payload = {"synced_days": 0, "synced_rows": 0, "errors": [], "synced_at": "2026-08-19"}
        try:
            with patch("apps.api.services.aliyun_billing_service.sync_bills", return_value=payload):
                response = await async_client.post("/api/v1/admin/bills/sync")
            assert response.status_code == 200
            assert response.json()["synced_days"] == 0
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_llm_usage_ok(self, async_client, test_app, admin_user, whitelist):
        """管理员可访问大模型调用明细（按用户分组）"""
        test_app.dependency_overrides[get_current_user] = lambda: admin_user
        payload = {
            "range": {"start": "2026-08-12", "end": "2026-08-18"},
            "totals": {"call_count": 1, "user_count": 1, "image_cost": 0.0},
            "users": [
                {
                    "user_id": 1, "nickname": "管理员", "created_at": None, "city": None,
                    "call_count": 1, "image_cost": 0.0, "scenes": ["agent"],
                    "records": [
                        {"id": 1, "date": "2026-08-18", "scene": "agent",
                         "query_text": "今天穿什么", "result_summary": "推荐 3 件物品",
                         "image_cost": 0.0, "created_at": "2026-08-18T10:00:00"}
                    ],
                }
            ],
        }
        try:
            with patch("apps.api.services.llm_usage_service.get_llm_usage", return_value=payload):
                response = await async_client.get("/api/v1/admin/llm-usage?days=7&q=管理")
            assert response.status_code == 200
            body = response.json()
            assert body["totals"]["user_count"] == 1
            assert body["users"][0]["records"][0]["scene"] == "agent"
        finally:
            test_app.dependency_overrides.clear()
