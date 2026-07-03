"""
顺衣尚后端测试共享 fixtures
提供 FastAPI TestClient、数据库 mock、认证 token 等
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

import httpx
from httpx import ASGITransport

from apps.api.core.config import settings


# ---------------------------------------------------------------------------
# 测试用 lifespan（跳过真实 DB / Cache 初始化）
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _test_lifespan(app):
    """测试环境下的空 lifespan，不连接真实数据库和缓存"""
    yield


# ---------------------------------------------------------------------------
# 创建测试专用 FastAPI app（覆盖 lifespan）
# ---------------------------------------------------------------------------

def _create_test_app():
    """创建测试用 FastAPI 应用，使用空 lifespan"""
    from apps.api.main import app as _real_app
    # 覆盖 lifespan 以避免真实 DB/Cache 连接
    _real_app.router.lifespan_context = _test_lifespan
    return _real_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_app():
    """返回测试用 FastAPI app 实例（session 级别复用）"""
    return _create_test_app()


@pytest.fixture
async def async_client(test_app):
    """
    异步 HTTP 测试客户端（基于 httpx.AsyncClient + ASGITransport）

    Usage:
        async def test_example(async_client):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sync_client(test_app):
    """
    同步 HTTP 测试客户端（基于 httpx.Client + ASGITransport）

    Usage:
        def test_example(sync_client):
            response = sync_client.get("/health")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=test_app)
    with httpx.Client(transport=transport, base_url="http://testserver") as client:
        yield client


# ---------------------------------------------------------------------------
# 数据库 mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_pool():
    """
    模拟 DatabasePool，防止测试连接真实数据库

    自动 patch:
      - DatabasePool.init_pool
      - DatabasePool.close_pool
      - DatabasePool.get_connection (返回 mock connection)
      - DatabasePool.check_health (返回 True)
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch("apps.api.core.database.DatabasePool.init_pool"),
        patch("apps.api.core.database.DatabasePool.close_pool"),
        patch("apps.api.core.database.DatabasePool.get_connection") as mock_get_conn,
        patch("apps.api.core.database.DatabasePool.check_health", return_value=True),
        patch("apps.api.core.database.check_db_health", return_value=True),
    ):
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
        yield {
            "conn": mock_conn,
            "cursor": mock_cursor,
            "get_connection": mock_get_conn,
        }


@pytest.fixture
def mock_cache():
    """
    模拟 Redis 缓存，防止测试连接真实 Redis

    自动 patch cache 实例的常用方法
    """
    with patch("apps.api.core.cache.cache") as mock_cache_instance:
        mock_cache_instance.enabled = False
        mock_cache_instance.check_health.return_value = False
        mock_cache_instance.get.return_value = None
        mock_cache_instance.set.return_value = True
        mock_cache_instance.delete.return_value = True
        yield mock_cache_instance


# ---------------------------------------------------------------------------
# 认证 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user():
    """测试用户数据"""
    return {
        "user_id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "user_code": "test-code-001",
    }


@pytest.fixture
def auth_token(test_user):
    """
    生成测试用 JWT token

    Usage:
        async def test_protected_endpoint(async_client, auth_token):
            response = await async_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
    """
    from apps.api.core.security import create_access_token
    token = create_access_token(
        data={"user_id": test_user["user_id"], "email": test_user["email"]}
    )
    return token


@pytest.fixture
def auth_headers(auth_token):
    """返回带认证的请求头"""
    return {"Authorization": f"Bearer {auth_token}"}
