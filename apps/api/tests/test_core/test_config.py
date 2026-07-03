"""
配置管理测试
"""
import pytest
from apps.api.core.config import Settings


def _make_settings(**kwargs):
    """创建不读取 .env 文件的 Settings 实例"""
    kwargs.setdefault("_env_file", None)
    return Settings(**kwargs)


class TestSettings:
    """Settings 配置测试"""

    def test_default_settings(self):
        """默认配置值"""
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret")
        assert s.database_url.startswith("postgresql://")
        assert s.database_pool_size == 10
        assert s.embedding_dimension == 1024
        assert s.jwt_algorithm == "HS256"
        assert s.jwt_expire_minutes == 1440
        assert s.app_port == 8000
        assert s.frontend_url == "http://localhost:3000"

    def test_is_development(self):
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret")
        assert s.is_development is True
        assert s.is_production is False

    def test_is_production(self):
        s = _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789")
        assert s.is_production is True
        assert s.is_development is False

    def test_cors_origins_dev_wildcard(self):
        """开发环境且未配置 cors_origins 时应为 ['*']"""
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret", cors_origins="")
        assert s.cors_origins_list == ["*"]

    def test_cors_origins_dev_specific(self):
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret", cors_origins="http://a.com,http://b.com")
        assert "http://a.com" in s.cors_origins_list
        assert "http://b.com" in s.cors_origins_list

    def test_cors_origins_production_no_config(self):
        s = _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789", cors_origins="")
        with pytest.raises(ValueError, match="CORS"):
            _ = s.cors_origins_list

    def test_cors_origins_production_wildcard(self):
        s = _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789", cors_origins="*")
        with pytest.raises(ValueError, match="CORS"):
            _ = s.cors_origins_list

    def test_cors_origins_production_specific(self):
        s = _make_settings(
            app_env="production",
            database_url="postgresql://u:p@h:5432/db",
            jwt_secret_key="aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
            cors_origins="https://example.com",
        )
        assert s.cors_origins_list == ["https://example.com"]

    def test_jwt_secret_auto_generate_dev(self):
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db")
        assert len(s.jwt_secret_key) > 0

    def test_jwt_secret_production_missing(self):
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="")

    def test_jwt_secret_production_too_short(self):
        with pytest.raises(ValueError, match="长度不足"):
            _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="short")

    def test_jwt_secret_production_no_digits(self):
        with pytest.raises(ValueError, match="字母和数字"):
            _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="a" * 40)

    def test_jwt_secret_production_valid(self):
        s = _make_settings(app_env="production", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789")
        assert len(s.jwt_secret_key) >= 32

    def test_jwt_secret_dev_weak_warning(self):
        """开发环境弱密钥只是警告，不报错"""
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="your-super-secret-key")
        assert s.jwt_secret_key == "your-super-secret-key"

    def test_auto_enable_redis_with_upstash(self):
        s = _make_settings(
            app_env="development",
            database_url="postgresql://u:p@h:5432/db",
            jwt_secret_key="dev-secret",
            upstash_redis_rest_url="https://test.upstash.io",
            upstash_redis_rest_token="test-token",
            redis_enabled=False,
        )
        assert s.redis_enabled is True

    def test_auto_enable_redis_without_upstash(self):
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret", redis_enabled=False)
        assert s.redis_enabled is False

    def test_check_key_strength_dev_short(self):
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret")
        # Should not raise in dev
        s._check_key_strength("short")

    def test_check_key_strength_dev_weak(self):
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret")
        s._check_key_strength("your-super-secret-key")

    def test_qwen_model_default(self):
        """测试 qwen_model 默认值"""
        s = _make_settings(app_env="development", database_url="postgresql://u:p@h:5432/db", jwt_secret_key="dev-secret")
        assert s.qwen_model is not None
        assert len(s.qwen_model) > 0
