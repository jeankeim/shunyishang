"""
PII 加密工具单元测试（PIPL 合规）

覆盖：密钥加解密闭环、明文历史数据透明兼容、无密钥降级、date/time 解析
"""

from datetime import date, time

import pytest
from cryptography.fernet import Fernet

from apps.api.core import pii_crypto
from apps.api.core.config import settings
from apps.api.core.pii_crypto import (
    ENC_PREFIX,
    decrypt_date,
    decrypt_pii,
    decrypt_time,
    encrypt_pii,
    is_encrypted,
    reset_fernet_cache,
)


@pytest.fixture
def with_key(monkeypatch):
    """配置有效密钥，测试结束后还原"""
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "pii_encryption_key", key)
    reset_fernet_cache()
    yield key
    reset_fernet_cache()


@pytest.fixture
def without_key(monkeypatch):
    """清空密钥（降级模式），测试结束后还原"""
    monkeypatch.setattr(settings, "pii_encryption_key", "")
    monkeypatch.setattr(pii_crypto, "_warned_no_key", False)
    reset_fernet_cache()
    yield
    reset_fernet_cache()


class TestEncryptDecryptRoundtrip:
    def test_str_roundtrip(self, with_key):
        cipher = encrypt_pii("马鞍山")
        assert is_encrypted(cipher)
        assert cipher.startswith(ENC_PREFIX)
        assert decrypt_pii(cipher) == "马鞍山"

    def test_date_roundtrip(self, with_key):
        cipher = encrypt_pii(date(1990, 5, 15))
        assert is_encrypted(cipher)
        assert decrypt_date(cipher) == date(1990, 5, 15)

    def test_time_roundtrip(self, with_key):
        cipher = encrypt_pii(time(10, 30, 0))
        assert is_encrypted(cipher)
        assert decrypt_time(cipher) == time(10, 30, 0)

    def test_none_passthrough(self, with_key):
        assert encrypt_pii(None) is None
        assert decrypt_pii(None) is None
        assert decrypt_date(None) is None
        assert decrypt_time(None) is None

    def test_wrong_key_returns_none(self, with_key):
        """密钥更换后旧密文解密失败返回 None（不泄露密文）"""
        cipher = encrypt_pii("secret")
        other_key = Fernet.generate_key().decode("ascii")
        settings.pii_encryption_key = other_key
        reset_fernet_cache()
        assert decrypt_pii(cipher) is None


class TestPlaintextCompat:
    """明文历史数据（迁移 17 后未回填）透明兼容"""

    def test_plaintext_str(self, with_key):
        assert decrypt_pii("北京") == "北京"

    def test_plaintext_iso_date(self, with_key):
        assert decrypt_date("1990-05-15") == date(1990, 5, 15)

    def test_plaintext_iso_time(self, with_key):
        assert decrypt_time("10:30:00") == time(10, 30, 0)

    def test_date_object_passthrough(self, with_key):
        """兼容旧列类型返回的 date/time 对象"""
        assert decrypt_date(date(1990, 5, 15)) == date(1990, 5, 15)
        assert decrypt_time(time(10, 30)) == time(10, 30)

    def test_invalid_date_returns_none(self, with_key):
        assert decrypt_date("not-a-date") is None


class TestNoKeyDegradation:
    def test_encrypt_falls_back_to_plaintext(self, without_key):
        assert encrypt_pii("马鞍山") == "马鞍山"
        assert encrypt_pii(date(1990, 5, 15)) == "1990-05-15"

    def test_decrypt_cipher_without_key_returns_none(self, without_key):
        assert decrypt_pii(ENC_PREFIX + "abcdef") is None
