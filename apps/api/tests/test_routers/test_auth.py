"""
认证路由测试
覆盖 auth.py 所有端点
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, time, datetime

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    """模拟已认证用户"""
    return {
        "id": 1,
        "user_code": "TEST001",
        "phone": "13800138000",
        "email": "test@example.com",
        "nickname": "测试用户",
        "gender": "男",
        "birth_date": date(1990, 5, 15),
        "birth_time": time(10, 0, 0),
        "birth_location": "北京",
        "preferred_city": "北京",
        "avatar_url": None,
        "bazi": None,
        "xiyong_elements": None,
    }


class TestRegister:
    """测试期间注册已关闭，所有请求返回 503"""

    @pytest.mark.asyncio
    async def test_register_disabled(self, async_client, mock_db_pool):
        """注册接口已关闭"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"phone": "13800138000", "password": "123456", "nickname": "测试"},
        )
        assert response.status_code == 503
        assert "暂不开放注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_disabled_no_phone(self, async_client, mock_db_pool):
        """无手机号也返回503"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"password": "123456"},
        )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_register_short_password(self, async_client, mock_db_pool):
        """密码太短 - Pydantic 校验先于路由处理，仍返回 422"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"phone": "13800138000", "password": "123"},
        )
        assert response.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, async_client, mock_db_pool):
        """登录成功"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            1, "TEST001", "13800138000", "test@example.com",
            "hashed_password",  # password_hash
            "测试用户", "男",
            date(1990, 5, 15), time(10, 0, 0),
            "北京", "北京", None,
            None, None,  # bazi, xiyong
            True,  # is_active
        )

        with patch("apps.api.routers.auth.verify_password", return_value=True):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={"username": "13800138000", "password": "123456"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, async_client, mock_db_pool):
        """用户不存在"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": "13800138000", "password": "123456"},
        )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client, mock_db_pool):
        """密码错误"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            1, "TEST001", "13800138000", "test@example.com",
            "hashed_password", "测试", "男",
            None, None, None, None, None,
            None, None,
            True,
        )

        with patch("apps.api.routers.auth.verify_password", return_value=False):
            response = await async_client.post(
                "/api/v1/auth/login",
                data={"username": "13800138000", "password": "wrong"},
            )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_disabled_account(self, async_client, mock_db_pool):
        """账户已禁用"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            1, "TEST001", "13800138000", "test@example.com",
            "hashed_password", "测试", "男",
            None, None, None, None, None,
            None, None,
            False,  # is_active = False
        )

        response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": "13800138000", "password": "123456"},
        )
        assert response.status_code == 401
        assert "账户已禁用" in response.json()["detail"]


class TestGetMe:
    @pytest.mark.asyncio
    async def test_get_me_no_auth(self, async_client):
        """无认证"""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_success(self, async_client, auth_headers, test_app, mock_user):
        """获取当前用户信息"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["phone"] == "13800138000"
        finally:
            test_app.dependency_overrides.clear()


class TestUpdateBazi:
    @pytest.mark.asyncio
    async def test_update_bazi_no_auth(self, async_client):
        """无认证"""
        response = await async_client.post(
            "/api/v1/auth/bazi",
            json={"birth_year": 1990, "birth_month": 5, "birth_day": 15, "birth_hour": 10, "gender": "男"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_bazi_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """更新八字成功"""
        mock_bazi = {
            "suggested_elements": ["水", "金"],
            "reasoning": "命理分析",
            "five_elements_count": {"金": 2, "木": 1, "水": 3, "火": 1, "土": 1},
        }
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("packages.utils.bazi_calculator.calculate_bazi", return_value=mock_bazi):
                response = await async_client.post(
                    "/api/v1/auth/bazi",
                    json={"birth_year": 1990, "birth_month": 5, "birth_day": 15, "birth_hour": 10, "gender": "男",
                          "sensitive_consent": True},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert data["bazi"] is not None
            assert "水" in data["xiyong_elements"]
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_bazi_without_consent(self, async_client, auth_headers, test_app, mock_user):
        """PIPL：未勾选敏感信息同意时拒绝保存八字"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/auth/bazi",
                json={"birth_year": 1990, "birth_month": 5, "birth_day": 15, "birth_hour": 10, "gender": "男"},
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "同意" in response.json()["detail"]
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_bazi_invalid_gender(self, async_client, auth_headers, test_app, mock_user):
        """无效性别"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/auth/bazi",
                json={"birth_year": 1990, "birth_month": 5, "birth_day": 15, "birth_hour": 10, "gender": "未知"},
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_no_auth(self, async_client):
        """无认证"""
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client, auth_headers, test_app, mock_user):
        """登出成功"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
            assert response.status_code == 200
            assert "登出成功" in response.json()["message"]
        finally:
            test_app.dependency_overrides.clear()


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_get_profile_no_auth(self, async_client):
        """无认证"""
        response = await async_client.get("/api/v1/auth/profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """获取用户资料"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            "TEST001", "13800138000", "test@example.com", "测试用户", "男",
            date(1990, 5, 15), time(10, 0, 0), "北京", "北京", None,
            None, None,
            datetime(2025, 1, 1), datetime(2025, 1, 1),
            None, None, None, None,  # skin_tone, style_preference, body_type, aesthetic_tags
        )
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/auth/profile", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["user_code"] == "TEST001"
            assert data["nickname"] == "测试用户"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """用户不存在"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/auth/profile", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_profile_no_auth(self, async_client):
        """无认证"""
        response = await async_client.patch(
            "/api/v1/auth/profile",
            json={"nickname": "新昵称"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_nickname(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """更新昵称"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            "TEST001", "13800138000", "test@example.com", "新昵称", "男",
            date(1990, 5, 15), time(10, 0, 0), "北京", "北京", None,
            None, None,
            datetime(2025, 1, 1), datetime(2025, 7, 2),
            None, None, None, None,  # skin_tone, style_preference, body_type, aesthetic_tags
        )
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/auth/profile",
                json={"nickname": "新昵称"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert response.json()["nickname"] == "新昵称"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_with_bazi_calculation(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """更新出生信息触发八字计算"""
        mock_bazi = {
            "suggested_elements": ["水"],
            "reasoning": "test",
            "five_elements_count": {},
        }
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            "TEST001", "13800138000", "test@example.com", "测试", "男",
            date(1990, 5, 15), time(10, 0, 0), "北京", "北京", None,
            mock_bazi, ["水"],
            datetime(2025, 1, 1), datetime(2025, 7, 2),
            None, None, None, None,  # skin_tone, style_preference, body_type, aesthetic_tags
        )
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("packages.utils.bazi_calculator.calculate_bazi", return_value=mock_bazi):
                response = await async_client.patch(
                    "/api/v1/auth/profile",
                    json={"birth_date": "1990-05-15", "birth_time": "10:00:00", "gender": "男",
                          "sensitive_consent": True},
                    headers=auth_headers,
                )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_birth_info_without_consent(self, async_client, auth_headers, test_app, mock_user):
        """PIPL：修改出生信息未勾选同意时拒绝"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/auth/profile",
                json={"birth_date": "1990-05-15"},
                headers=auth_headers,
            )
            assert response.status_code == 400
            assert "同意" in response.json()["detail"]
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_no_fields(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """无字段更新"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            "TEST001", "13800138000", "test@example.com", "测试", "男",
            None, None, None, None, None,
            None, None,
            datetime(2025, 1, 1), datetime(2025, 1, 1),
            None, None, None, None,  # skin_tone, style_preference, body_type, aesthetic_tags
        )
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/auth/profile",
                json={},
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_avatar_url(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """更新头像"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (
            "TEST001", "13800138000", "test@example.com", "测试", "男",
            None, None, None, None, "http://img.com/avatar.jpg",
            None, None,
            datetime(2025, 1, 1), datetime(2025, 7, 2),
            None, None, None, None,  # skin_tone, style_preference, body_type, aesthetic_tags
        )
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/auth/profile",
                json={"avatar_url": "http://img.com/avatar.jpg"},
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestDeleteAccount:
    @pytest.mark.asyncio
    async def test_delete_no_auth(self, async_client):
        """无认证"""
        response = await async_client.delete("/api/v1/auth/profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """删除账户"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/auth/profile", headers=auth_headers)
            assert response.status_code == 204
        finally:
            test_app.dependency_overrides.clear()
