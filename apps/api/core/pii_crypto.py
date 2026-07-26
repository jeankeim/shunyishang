"""
PII 敏感字段加密工具（PIPL 合规）

对出生日期/时辰/出生地等敏感个人信息做应用层加密后落库：
- 算法: Fernet (AES-128-CBC + HMAC-SHA256)，密文格式 "enc:v1:<token>"
- 密钥: settings.pii_encryption_key（生成: python -m apps.api.core.pii_crypto genkey）
- 兼容性: 解密函数对明文历史数据透明放行（存量数据用
  scripts/encrypt_existing_pii.py 一次性回填加密）
- 未配置密钥时降级明文存储并告警（开发环境），生产环境必须配置

设计约定：数据库中 birth_date/birth_time 列为 TEXT（迁移 17），
应用层读取时解密并解析回 date/time 对象，对上层代码透明。
"""

import logging
import sys
from datetime import date, time
from typing import Optional

from apps.api.core.config import settings

logger = logging.getLogger(__name__)

ENC_PREFIX = "enc:v1:"

_fernet = None
_fernet_loaded = False
_warned_no_key = False


def _get_fernet():
    """懒加载 Fernet 实例（密钥未配置返回 None）"""
    global _fernet, _fernet_loaded
    if _fernet_loaded:
        return _fernet
    _fernet_loaded = True
    key = settings.pii_encryption_key
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error(f"❌ PII_ENCRYPTION_KEY 无效，加密不可用: {e}")
        _fernet = None
    return _fernet


def reset_fernet_cache() -> None:
    """重置密钥缓存（测试用）"""
    global _fernet, _fernet_loaded
    _fernet = None
    _fernet_loaded = False


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def encrypt_pii(value) -> Optional[str]:
    """
    加密敏感值（接受 str/date/time，统一转 str 后加密）

    密钥未配置时降级返回明文（仅开发环境可接受，只告警一次）。
    """
    global _warned_no_key
    if value is None:
        return None
    plain = str(value)
    if not plain:
        return plain
    f = _get_fernet()
    if f is None:
        if not _warned_no_key:
            logger.warning("⚠️ PII_ENCRYPTION_KEY 未配置，敏感字段将以明文存储（生产环境必须配置！）")
            _warned_no_key = True
        return plain
    return ENC_PREFIX + f.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_pii(value) -> Optional[str]:
    """
    解密敏感值为字符串

    - 非加密格式（明文历史数据 / date/time 对象）透明放行
    - 密文但密钥缺失/错误时返回 None（宁可显示为空，不泄露密文）
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    if not value.startswith(ENC_PREFIX):
        return value
    f = _get_fernet()
    if f is None:
        logger.error("❌ 存在加密数据但 PII_ENCRYPTION_KEY 未配置，无法解密")
        return None
    try:
        return f.decrypt(value[len(ENC_PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as e:
        logger.error(f"❌ PII 解密失败（密钥是否被更换？）: {e}")
        return None


def decrypt_date(value) -> Optional[date]:
    """解密并解析为 date（兼容 date 对象 / 明文 ISO 字符串 / 密文）"""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = decrypt_pii(value)
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        logger.warning(f"birth_date 解析失败: {s[:20]}")
        return None


def decrypt_time(value) -> Optional[time]:
    """解密并解析为 time（兼容 time 对象 / 明文字符串 / 密文）"""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    s = decrypt_pii(value)
    if not s:
        return None
    try:
        return time.fromisoformat(s)
    except ValueError:
        logger.warning(f"birth_time 解析失败: {s[:20]}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "genkey":
        from cryptography.fernet import Fernet
        print(Fernet.generate_key().decode("ascii"))
    else:
        print("用法: python -m apps.api.core.pii_crypto genkey")
