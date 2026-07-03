"""
security 模块测试
测试密码哈希、JWT token 生成/验证功能
"""

import pytest
from datetime import timedelta

from apps.api.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    generate_user_code,
)


class TestPasswordHashing:
    """测试密码哈希与验证"""

    def test_hash_and_verify_success(self):
        """哈希后验证成功"""
        plain = "MyPassword123"
        hashed = get_password_hash(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        """错误密码验证失败"""
        plain = "MyPassword123"
        hashed = get_password_hash(plain)
        assert verify_password("WrongPassword", hashed) is False

    def test_hash_is_different_each_time(self):
        """每次哈希结果不同（盐值随机）"""
        plain = "SamePassword"
        hash1 = get_password_hash(plain)
        hash2 = get_password_hash(plain)
        assert hash1 != hash2
        assert verify_password(plain, hash1) is True
        assert verify_password(plain, hash2) is True

    def test_verify_empty_password(self):
        """空密码验证失败"""
        hashed = get_password_hash("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_invalid_hash_returns_false(self):
        """无效哈希返回 False"""
        assert verify_password("password", "invalid_hash") is False

    def test_long_password_truncated(self):
        """超长密码被截断（bcrypt 72字节限制）"""
        long_password = "a" * 100
        hashed = get_password_hash(long_password)
        # 截断后前72字节应能验证
        assert verify_password("a" * 72, hashed) is True


class TestCreateAccessToken:
    """测试 JWT token 生成"""

    def test_create_token_returns_string(self):
        """生成 token 返回字符串"""
        token = create_access_token(data={"user_id": 1})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_expiry(self):
        """自定义过期时间"""
        token = create_access_token(
            data={"user_id": 1},
            expires_delta=timedelta(hours=1)
        )
        assert isinstance(token, str)

    def test_token_contains_user_id(self):
        """token 包含 user_id"""
        token = create_access_token(data={"user_id": 42, "email": "test@test.com"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["email"] == "test@test.com"

    def test_token_has_expiry(self):
        """token 包含过期时间"""
        token = create_access_token(data={"user_id": 1})
        payload = decode_access_token(token)
        assert payload is not None
        assert "exp" in payload


class TestDecodeAccessToken:
    """测试 JWT token 解码"""

    def test_decode_valid_token(self):
        """解码有效 token"""
        token = create_access_token(data={"user_id": 1})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["user_id"] == 1

    def test_decode_invalid_token_returns_none(self):
        """无效 token 返回 None"""
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_empty_token_returns_none(self):
        """空 token 返回 None"""
        result = decode_access_token("")
        assert result is None


class TestGenerateUserCode:
    """测试用户码生成"""

    def test_returns_string(self):
        """返回字符串"""
        code = generate_user_code()
        assert isinstance(code, str)

    def test_unique_codes(self):
        """每次生成不同码"""
        code1 = generate_user_code()
        code2 = generate_user_code()
        assert code1 != code2

    def test_code_is_uuid_format(self):
        """码为 UUID 格式"""
        code = generate_user_code()
        # UUID 格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = code.split("-")
        assert len(parts) == 5
