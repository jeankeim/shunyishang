"""
阿里云 OSS 对象存储服务
用于国内生产环境的图片上传和存储
替代 Cloudflare R2，提供更低的国内访问延迟
支持自动缩略图生成
"""

import uuid
from typing import Optional, BinaryIO, Tuple
from pathlib import Path
from io import BytesIO
from PIL import Image

from apps.api.core.config import settings
from apps.api.core.logging_config import get_logger

logger = get_logger(__name__)


class OSSStorageService:
    """阿里云 OSS 对象存储服务"""

    def __init__(self):
        """初始化 OSS 客户端"""
        self.access_key_id = getattr(settings, 'oss_access_key_id', None)
        self.access_key_secret = getattr(settings, 'oss_access_key_secret', None)
        self.bucket_name = getattr(settings, 'oss_bucket_name', 'shunyishang-images')
        self.endpoint = getattr(settings, 'oss_endpoint', 'https://oss-cn-hangzhou.aliyuncs.com')
        self.public_url = getattr(settings, 'oss_public_url', '')

        # 缩略图配置
        self.thumbnail_width = 400  # 缩略图宽度
        self.thumbnail_quality = 80  # JPEG 质量

        if not all([self.access_key_id, self.access_key_secret]):
            logger.warning("OSS 配置不完整，文件上传将不可用")
            self.bucket = None
            return

        try:
            import oss2
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            logger.info(f"OSS 存储服务初始化成功: bucket={self.bucket_name}, endpoint={self.endpoint}")
        except ImportError:
            logger.error("oss2 库未安装，请执行: pip install oss2")
            self.bucket = None
        except Exception as e:
            logger.error(f"OSS 初始化失败: {e}")
            self.bucket = None

    def _generate_thumbnail(self, image_data: bytes, max_width: int = None) -> bytes:
        """
        生成图片缩略图

        Args:
            image_data: 原始图片二进制数据
            max_width: 最大宽度（默认使用配置值）

        Returns:
            缩略图二进制数据
        """
        try:
            width = max_width or self.thumbnail_width

            img = Image.open(BytesIO(image_data))

            # 转换为 RGB（处理 PNG 透明通道）
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # 计算缩放比例
            ratio = width / float(img.width)
            height = int(float(img.height) * ratio)

            img = img.resize((width, height), Image.Resampling.LANCZOS)

            output = BytesIO()
            img.save(output, format='JPEG', quality=self.thumbnail_quality, optimize=True)

            return output.getvalue()

        except Exception as e:
            logger.error(f"生成缩略图失败: {e}")
            return image_data  # 失败时返回原图

    def upload_file_with_thumbnail(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        上传文件到 OSS 并自动生成缩略图

        Args:
            file_data: 文件二进制数据
            file_name: 文件名
            folder: 文件夹路径
            content_type: MIME 类型

        Returns:
            (原图URL, 缩略图URL)，失败返回 (None, None)
        """
        if not self.bucket:
            logger.error("OSS 客户端未初始化")
            return None, None

        try:
            # 生成唯一文件名
            unique_id = uuid.uuid4().hex[:8]
            base_name = Path(file_name).stem
            extension = Path(file_name).suffix.lstrip('.') or 'jpg'

            # 原图 key
            original_key = f"{folder}/{unique_id}_{base_name}.{extension}"

            # 缩略图 key
            thumbnail_key = f"{folder}/thumbnails/{unique_id}_{base_name}_thumb.jpg"

            # 读取文件数据
            file_data.seek(0)
            original_data = file_data.read()

            # 上传原图
            self.bucket.put_object(
                original_key,
                original_data,
                headers={
                    'Content-Type': content_type,
                    'Cache-Control': 'public, max-age=31536000'
                }
            )

            # 生成并上传缩略图（仅对图片生成）
            thumbnail_url = None
            if content_type.startswith('image/'):
                thumbnail_data = self._generate_thumbnail(original_data)
                self.bucket.put_object(
                    thumbnail_key,
                    thumbnail_data,
                    headers={
                        'Content-Type': 'image/jpeg',
                        'Cache-Control': 'public, max-age=31536000'
                    }
                )
                thumbnail_url = self._build_url(thumbnail_key)

            original_url = self._build_url(original_key)

            logger.info(f"文件上传成功: {original_key}, 缩略图: {thumbnail_key}")
            return original_url, thumbnail_url

        except Exception as e:
            logger.error(f"OSS 上传失败: {e}")
            return None, None

    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """
        上传文件到 OSS（保持与 R2 版本相同的接口）

        Args:
            file_data: 文件二进制数据
            file_name: 文件名
            folder: 文件夹路径
            content_type: MIME 类型

        Returns:
            文件的公共 URL，失败返回 None
        """
        original_url, _ = self.upload_file_with_thumbnail(
            file_data, file_name, folder, content_type
        )
        return original_url

    def upload_file_from_path(
        self,
        file_path: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """
        从本地路径上传文件到 OSS

        Args:
            file_path: 本地文件路径
            folder: 文件夹路径
            content_type: MIME 类型

        Returns:
            文件的公共 URL，失败返回 None
        """
        if not self.bucket:
            logger.error("OSS 客户端未初始化")
            return None

        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None

            with open(path, 'rb') as f:
                return self.upload_file(
                    file_data=f,
                    file_name=path.name,
                    folder=folder,
                    content_type=content_type
                )

        except Exception as e:
            logger.error(f"OSS 上传异常: {e}")
            return None

    def delete_file(self, file_url: str) -> bool:
        """
        删除 OSS 中的文件

        Args:
            file_url: 文件的公共 URL

        Returns:
            是否删除成功
        """
        if not self.bucket:
            logger.error("OSS 客户端未初始化")
            return False

        try:
            key = self._extract_key(file_url)
            self.bucket.delete_object(key)
            logger.info(f"文件删除成功: {key}")
            return True

        except Exception as e:
            logger.error(f"OSS 删除失败: {e}")
            return False

    def file_exists(self, file_url: str) -> bool:
        """
        检查文件是否存在

        Args:
            file_url: 文件的公共 URL

        Returns:
            文件是否存在
        """
        if not self.bucket:
            return False

        try:
            key = self._extract_key(file_url)
            return self.bucket.object_exists(key)

        except Exception as e:
            logger.error(f"OSS 检查文件异常: {e}")
            return False

    def get_thumbnail_url(self, original_url: str) -> Optional[str]:
        """
        根据原图 URL 生成缩略图 URL

        Args:
            original_url: 原图 URL

        Returns:
            缩略图 URL
        """
        if not original_url:
            return None

        try:
            key = self._extract_key(original_url)
            path = Path(key)
            folder = path.parent
            stem = path.stem.replace('_thumb', '')
            thumbnail_key = f"{folder}/thumbnails/{stem}_thumb.jpg"
            return self._build_url(thumbnail_key)

        except Exception as e:
            logger.error(f"生成缩略图 URL 失败: {e}")
            return original_url

    def _build_url(self, key: str) -> str:
        """根据 key 构建完整的访问 URL"""
        if self.public_url:
            return f"{self.public_url}/{key}"
        else:
            # 使用 OSS 默认域名
            endpoint_host = self.endpoint.replace('https://', '').replace('http://', '')
            return f"https://{self.bucket_name}.{endpoint_host}/{key}"

    def _extract_key(self, url: str) -> str:
        """从 URL 中提取 OSS key"""
        if self.public_url and url.startswith(self.public_url):
            return url.replace(f"{self.public_url}/", "", 1)
        else:
            # 尝试从 URL 中提取 bucket 后面的路径
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path.lstrip('/')
                return path
            except Exception:
                return url.split('/')[-1]


# 全局单例
_oss_service: Optional[OSSStorageService] = None


def get_oss_service() -> OSSStorageService:
    """获取 OSS 服务单例"""
    global _oss_service
    if _oss_service is None:
        _oss_service = OSSStorageService()
    return _oss_service
