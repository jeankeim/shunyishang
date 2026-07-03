"""
存储服务工厂
根据配置自动选择 R2（海外）或 OSS（国内阿里云）存储服务
保持接口统一，调用方无需关心底层实现
"""

from typing import Optional, BinaryIO, Tuple
from apps.api.core.config import settings
from apps.api.core.logging_config import get_logger

logger = get_logger(__name__)


class StorageServiceAdapter:
    """
    统一存储服务适配器
    自动检测配置并代理到 R2 或 OSS 实现
    """

    def __init__(self):
        self._backend = None
        self._backend_type = None
        self._init_backend()

    def _init_backend(self):
        """根据配置初始化后端存储"""
        # 优先检测 OSS 配置（国内生产环境）
        oss_key_id = getattr(settings, 'oss_access_key_id', '')
        oss_key_secret = getattr(settings, 'oss_access_key_secret', '')
        if oss_key_id and oss_key_secret:
            try:
                from apps.api.services.oss_storage import OSSStorageService
                self._backend = OSSStorageService()
                self._backend_type = 'oss'
                logger.info("存储服务: 使用阿里云 OSS")
                return
            except Exception as e:
                logger.warning(f"OSS 初始化失败，回退到 R2: {e}")

        # 回退到 R2 配置（海外/当前生产环境）
        r2_account = getattr(settings, 'r2_account_id', '')
        r2_key_id = getattr(settings, 'r2_access_key_id', '')
        r2_key_secret = getattr(settings, 'r2_secret_access_key', '')
        if r2_account and r2_key_id and r2_key_secret:
            try:
                from apps.api.services.r2_storage import R2StorageService
                self._backend = R2StorageService()
                self._backend_type = 'r2'
                logger.info("存储服务: 使用 Cloudflare R2")
                return
            except Exception as e:
                logger.warning(f"R2 初始化失败: {e}")

        logger.warning("未检测到有效的存储服务配置，文件上传功能不可用")

    @property
    def backend_type(self) -> str:
        """当前使用的存储后端类型: 'oss' | 'r2' | 'none'"""
        return self._backend_type or 'none'

    @property
    def available(self) -> bool:
        """存储服务是否可用"""
        return self._backend is not None

    def upload_file_with_thumbnail(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Tuple[Optional[str], Optional[str]]:
        """上传文件并生成缩略图，返回 (原图URL, 缩略图URL)"""
        if not self._backend:
            logger.error("存储服务不可用")
            return None, None
        return self._backend.upload_file_with_thumbnail(file_data, file_name, folder, content_type)

    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """上传文件，返回文件 URL"""
        if not self._backend:
            logger.error("存储服务不可用")
            return None
        return self._backend.upload_file(file_data, file_name, folder, content_type)

    def upload_file_from_path(
        self,
        file_path: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """从本地路径上传文件，返回文件 URL"""
        if not self._backend:
            logger.error("存储服务不可用")
            return None
        return self._backend.upload_file_from_path(file_path, folder, content_type)

    def delete_file(self, file_url: str) -> bool:
        """删除文件"""
        if not self._backend:
            return False
        return self._backend.delete_file(file_url)

    def file_exists(self, file_url: str) -> bool:
        """检查文件是否存在"""
        if not self._backend:
            return False
        return self._backend.file_exists(file_url)

    def get_thumbnail_url(self, original_url: str) -> Optional[str]:
        """获取缩略图 URL"""
        if not self._backend:
            return None
        return self._backend.get_thumbnail_url(original_url)


# 全局单例
_storage_service: Optional[StorageServiceAdapter] = None


def get_storage_service() -> StorageServiceAdapter:
    """获取统一存储服务单例"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageServiceAdapter()
    return _storage_service
