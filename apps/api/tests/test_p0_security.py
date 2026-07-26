"""
P0 安全能力测试：API 限流 / LLM 日配额 / 账号注销

覆盖:
1. 内存计数器语义（计数、窗口重置）
2. check_rate_limit 开关与超限行为
3. 登录/注册端点限流（429 + Retry-After）
4. 全局限流中间件（豁免路径、超限拒绝）
5. LLM 日配额（身份解析、配额耗尽 429）
6. 账号注销（级联删除 SQL + 对象存储清理）
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from apps.api.core.config import settings
from apps.api.core.rate_limit import _MemoryCounter, check_rate_limit
from apps.api.core.quota import _resolve_identity, llm_daily_quota


def _unique_ip() -> str:
    """每个测试用唯一伪 IP，避免计数器串扰"""
    tail = uuid.uuid4().int
    return f"10.{(tail >> 16) % 256}.{(tail >> 8) % 256}.{tail % 256}"


def make_request(headers: dict = None, client_ip: str = "127.0.0.1") -> Request:
    """构造 starlette Request（用于直接测试依赖函数）"""
    raw_headers = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/recommend/stream",
        "headers": raw_headers,
        "client": (client_ip, 12345),
        "query_string": b"",
    }
    return Request(scope)


@pytest.fixture
def rate_limit_on():
    """临时打开限流开关（conftest 默认全局关闭）"""
    old = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    yield
    settings.rate_limit_enabled = old


@pytest.fixture
def quota_on():
    """临时打开 LLM 配额开关"""
    old_enabled = settings.llm_quota_enabled
    old_quota = settings.llm_daily_quota
    settings.llm_quota_enabled = True
    settings.llm_daily_quota = 3
    yield
    settings.llm_quota_enabled = old_enabled
    settings.llm_daily_quota = old_quota


# ---------------------------------------------------------------------------
# 1. 内存计数器
# ---------------------------------------------------------------------------

class TestMemoryCounter:
    def test_incr_counts_up(self):
        counter = _MemoryCounter()
        assert counter.incr("k1", 60)[0] == 1
        assert counter.incr("k1", 60)[0] == 2
        assert counter.incr("k1", 60)[0] == 3

    def test_keys_are_independent(self):
        counter = _MemoryCounter()
        counter.incr("a", 60)
        counter.incr("a", 60)
        assert counter.incr("b", 60)[0] == 1

    def test_window_reset(self, monkeypatch):
        counter = _MemoryCounter()
        fake_now = [1000.0]
        monkeypatch.setattr("apps.api.core.rate_limit.time.time", lambda: fake_now[0])
        counter.incr("k", 60)
        counter.incr("k", 60)
        # 窗口过期后重新计数
        fake_now[0] = 1061.0
        count, _ = counter.incr("k", 60)
        assert count == 1

    def test_retry_after_within_window(self, monkeypatch):
        counter = _MemoryCounter()
        fake_now = [2000.0]
        monkeypatch.setattr("apps.api.core.rate_limit.time.time", lambda: fake_now[0])
        counter.incr("k", 60)
        fake_now[0] = 2030.0
        _, retry_after = counter.incr("k", 60)
        assert retry_after == 30


# ---------------------------------------------------------------------------
# 2. check_rate_limit
# ---------------------------------------------------------------------------

class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_disabled_always_allows(self):
        assert settings.rate_limit_enabled is False
        key = f"test:{uuid.uuid4()}"
        for _ in range(100):
            allowed, _ = await check_rate_limit(key, 1, 60)
            assert allowed

    @pytest.mark.asyncio
    async def test_enabled_blocks_over_limit(self, rate_limit_on):
        key = f"test:{uuid.uuid4()}"
        for i in range(3):
            allowed, _ = await check_rate_limit(key, 3, 60)
            assert allowed, f"第 {i+1} 次应放行"
        allowed, retry_after = await check_rate_limit(key, 3, 60)
        assert not allowed
        assert retry_after >= 1


# ---------------------------------------------------------------------------
# 3. 登录端点限流
# ---------------------------------------------------------------------------

class TestAuthEndpointRateLimit:
    @pytest.mark.asyncio
    async def test_login_rate_limited(self, async_client, mock_db_pool, rate_limit_on):
        """同 IP 第 6 次登录尝试返回 429"""
        mock_db_pool["cursor"].fetchone.return_value = None  # 用户不存在 → 401
        headers = {"X-Forwarded-For": _unique_ip()}
        data = {"username": "13800000000", "password": "wrong"}

        for i in range(settings.rate_limit_auth_per_minute):
            resp = await async_client.post("/api/v1/auth/login", data=data, headers=headers)
            assert resp.status_code != 429, f"第 {i+1} 次不应被限流"

        resp = await async_client.post("/api/v1/auth/login", data=data, headers=headers)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    @pytest.mark.asyncio
    async def test_different_ips_not_affected(self, async_client, mock_db_pool, rate_limit_on):
        """不同 IP 独立计数"""
        mock_db_pool["cursor"].fetchone.return_value = None
        data = {"username": "13800000000", "password": "wrong"}

        ip1 = {"X-Forwarded-For": _unique_ip()}
        for _ in range(settings.rate_limit_auth_per_minute + 1):
            resp = await async_client.post("/api/v1/auth/login", data=data, headers=ip1)
        assert resp.status_code == 429

        ip2 = {"X-Forwarded-For": _unique_ip()}
        resp = await async_client.post("/api/v1/auth/login", data=data, headers=ip2)
        assert resp.status_code != 429


# ---------------------------------------------------------------------------
# 4. 全局限流中间件
# ---------------------------------------------------------------------------

class TestGlobalRateLimit:
    @pytest.mark.asyncio
    async def test_global_limit_blocks(self, async_client, rate_limit_on):
        old = settings.rate_limit_global_per_minute
        settings.rate_limit_global_per_minute = 3
        try:
            headers = {"X-Forwarded-For": _unique_ip()}
            for i in range(3):
                resp = await async_client.get("/api/v1/nonexistent", headers=headers)
                assert resp.status_code == 404, f"第 {i+1} 次应正常到达路由"
            resp = await async_client.get("/api/v1/nonexistent", headers=headers)
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
        finally:
            settings.rate_limit_global_per_minute = old

    @pytest.mark.asyncio
    async def test_health_exempt(self, async_client, rate_limit_on, mock_db_pool, mock_cache):
        """健康检查路径豁免全局限流"""
        old = settings.rate_limit_global_per_minute
        settings.rate_limit_global_per_minute = 2
        try:
            headers = {"X-Forwarded-For": _unique_ip()}
            for _ in range(5):
                resp = await async_client.get("/health", headers=headers)
                assert resp.status_code != 429
        finally:
            settings.rate_limit_global_per_minute = old


# ---------------------------------------------------------------------------
# 5. LLM 日配额
# ---------------------------------------------------------------------------

class TestLLMQuota:
    def test_identity_guest_by_ip(self):
        req = make_request(headers={"X-Forwarded-For": "1.2.3.4"})
        assert _resolve_identity(req) == "ip:1.2.3.4"

    def test_identity_user_by_token(self):
        from apps.api.core.security import create_access_token
        token = create_access_token(data={"sub": "42"})
        req = make_request(headers={"Authorization": f"Bearer {token}"})
        assert _resolve_identity(req) == "u:42"

    def test_identity_invalid_token_falls_back_to_ip(self):
        req = make_request(
            headers={"Authorization": "Bearer invalid.token.xxx", "X-Forwarded-For": "5.6.7.8"}
        )
        assert _resolve_identity(req) == "ip:5.6.7.8"

    @pytest.mark.asyncio
    async def test_quota_disabled_unlimited(self):
        assert settings.llm_quota_enabled is False
        req = make_request(headers={"X-Forwarded-For": _unique_ip()})
        for _ in range(50):
            await llm_daily_quota(req)  # 不应抛异常

    @pytest.mark.asyncio
    async def test_quota_exhausted_raises_429(self, quota_on):
        ip = _unique_ip()
        req = make_request(headers={"X-Forwarded-For": ip})
        for _ in range(settings.llm_daily_quota):
            await llm_daily_quota(req)
        with pytest.raises(HTTPException) as exc_info:
            await llm_daily_quota(req)
        assert exc_info.value.status_code == 429
        assert "配额" in exc_info.value.detail or "次数" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_quota_isolated_between_identities(self, quota_on):
        """不同身份的配额互不影响"""
        req_a = make_request(headers={"X-Forwarded-For": _unique_ip()})
        req_b = make_request(headers={"X-Forwarded-For": _unique_ip()})
        for _ in range(settings.llm_daily_quota):
            await llm_daily_quota(req_a)
        with pytest.raises(HTTPException):
            await llm_daily_quota(req_a)
        # B 仍可用
        await llm_daily_quota(req_b)


# ---------------------------------------------------------------------------
# 6. 账号注销
# ---------------------------------------------------------------------------

def _make_user_row(user_id=1, avatar_url=None):
    """构造 get_current_user 查询返回的 14 列用户行"""
    return (
        user_id, "test-code-001", "13800000000", "test@example.com",
        "测试用户", "男", None, None, None, None,
        avatar_url, None, None, True,  # is_active
    )


@pytest.fixture
def deregister_token():
    from apps.api.core.security import create_access_token
    return create_access_token(data={"sub": "1"})


class TestAccountDeregister:
    @pytest.mark.asyncio
    async def test_deregister_deletes_user_and_images(
        self, async_client, mock_db_pool, deregister_token
    ):
        cursor = mock_db_pool["cursor"]
        cursor.fetchone.return_value = _make_user_row(avatar_url="https://cdn.test/avatar.png")
        cursor.fetchall.return_value = [("https://cdn.test/item1.png",), (None,)]

        mock_storage = MagicMock()
        mock_storage.available = True
        mock_storage.get_thumbnail_url.return_value = None

        with patch(
            "apps.api.services.storage.get_storage_service", return_value=mock_storage
        ):
            resp = await async_client.delete(
                "/api/v1/auth/account",
                headers={"Authorization": f"Bearer {deregister_token}"},
            )

        assert resp.status_code == 204

        executed_sql = [str(call.args[0]) for call in cursor.execute.call_args_list]
        assert any("DELETE FROM user_disliked_items" in sql for sql in executed_sql)
        assert any("DELETE FROM users" in sql for sql in executed_sql)
        mock_db_pool["conn"].commit.assert_called()

        # 图片清理：衣橱物品图 + 头像（None 已被过滤）
        deleted_urls = [call.args[0] for call in mock_storage.delete_file.call_args_list]
        assert "https://cdn.test/item1.png" in deleted_urls
        assert "https://cdn.test/avatar.png" in deleted_urls

    @pytest.mark.asyncio
    async def test_deregister_requires_auth(self, async_client):
        resp = await async_client.delete("/api/v1/auth/account")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_deregister_storage_failure_does_not_block(
        self, async_client, mock_db_pool, deregister_token
    ):
        """存储清理失败不影响注销成功（best-effort）"""
        cursor = mock_db_pool["cursor"]
        cursor.fetchone.return_value = _make_user_row()
        cursor.fetchall.return_value = [("https://cdn.test/item1.png",)]

        mock_storage = MagicMock()
        mock_storage.available = True
        mock_storage.delete_file.side_effect = RuntimeError("OSS 不可用")

        with patch(
            "apps.api.services.storage.get_storage_service", return_value=mock_storage
        ):
            resp = await async_client.delete(
                "/api/v1/auth/account",
                headers={"Authorization": f"Bearer {deregister_token}"},
            )

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_soft_delete_profile_still_works(
        self, async_client, mock_db_pool, deregister_token
    ):
        """原软删除接口保持可用"""
        cursor = mock_db_pool["cursor"]
        cursor.fetchone.return_value = _make_user_row()

        resp = await async_client.delete(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {deregister_token}"},
        )
        assert resp.status_code == 204
        executed_sql = [str(call.args[0]) for call in cursor.execute.call_args_list]
        assert any("is_active = FALSE" in sql for sql in executed_sql)
