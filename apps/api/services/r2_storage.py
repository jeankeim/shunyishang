"""
Cloudflare R2 对象存储服务
用于生产环境的图片上传和存储
支持自动缩略图生成
"""

import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO, Tuple
from pathlib import Path
import uuid
from io import BytesIO
from PIL import Image

from apps.api.core.config import settings
from apps.api.core.logging_config import get_logger

logger = get_logger(__name__)


class R2StorageService:
    """Cloudflare R2 对象存储服务"""
    
    def __init__(self):
        """初始化 R2 客户端"""
        self.account_id = getattr(settings, 'r2_account_id', None)
        self.access_key_id = getattr(settings, 'r2_access_key_id', None)
        self.secret_access_key = getattr(settings, 'r2_secret_access_key', None)
        self.bucket_name = getattr(settings, 'r2_bucket_name', 'wuxing-wardrobe')
        self.public_url = getattr(settings, 'r2_public_url', '')
        
        # 缩略图配置
        self.thumbnail_width = 400  # 缩略图宽度
        self.thumbnail_quality = 80  # JPEG 质量
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key]):
            logger.warning("R2 配置不完整，文件上传将使用本地存储")
            self.client = None
            return
        
        # 初始化 S3 兼容客户端
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(
                signature_version='s3v4',
                retries={'max_attempts': 3, 'mode': 'standard'}
            ),
            region_name='auto'  # R2 使用 auto
        )
        
        logger.info(f"R2 存储服务初始化成功: bucket={self.bucket_name}")
    
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
            
            # 打开图片
            img = Image.open(BytesIO(image_data))
            
            # 转换为 RGB（处理 PNG 透明通道）
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 计算缩放比例
            ratio = width / float(img.width)
            height = int(float(img.height) * ratio)
            
            # 缩放图片
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # 保存到内存
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
        上传文件到 R2 并自动生成缩略图
        
        Args:
            file_data: 文件二进制数据
            file_name: 文件名
            folder: 文件夹路径
            content_type: MIME 类型
            
        Returns:
            (原图URL, 缩略图URL)，失败返回 (None, None)
        """
        if not self.client:
            logger.error("R2 客户端未初始化")
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
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=original_key,
                Body=original_data,
                ContentType=content_type,
                CacheControl='public, max-age=31536000'  # 1年缓存
            )
            
            # 生成并上传缩略图（仅对图片生成）
            thumbnail_url = None
            if content_type.startswith('image/'):
                thumbnail_data = self._generate_thumbnail(original_data)
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=thumbnail_key,
                    Body=thumbnail_data,
                    ContentType='image/jpeg',
                    CacheControl='public, max-age=31536000'
                )
                
                # 生成缩略图 URL
                if self.public_url:
                    thumbnail_url = f"{self.public_url}/{thumbnail_key}"
                else:
                    thumbnail_url = f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{thumbnail_key}"
            
            # 生成原图 URL
            if self.public_url:
                original_url = f"{self.public_url}/{original_key}"
            else:
                original_url = f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{original_key}"
            
            logger.info(f"文件上传成功: {original_key}, 缩略图: {thumbnail_key}")
            return original_url, thumbnail_url
            
        except ClientError as e:
            logger.error(f"R2 上传失败: {e}")
            return None, None
        except Exception as e:
            logger.error(f"R2 上传异常: {e}")
            return None, None
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """
        上传文件到 R2（保持向后兼容）
        
        Args:
            file_data: 文件二进制数据
            file_name: 文件名（会被添加 UUID 前缀避免冲突）
            folder: 文件夹路径
            content_type: MIME 类型
            
        Returns:
            文件的公共 URL，失败返回 None
        """
        original_url, _ = self.upload_file_with_thumbnail(
            file_data, file_name, folder, content_type
        )
        return original_url
    
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
            # 从原图 URL 提取 key
            if self.public_url and original_url.startswith(self.public_url):
                key = original_url.replace(f"{self.public_url}/", "")
            else:
                key = original_url.split('/')[-1]
            
            # 生成缩略图 key
            path = Path(key)
            folder = path.parent
            stem = path.stem.replace('_thumb', '')  # 移除可能已有的 _thumb
            thumbnail_key = f"{folder}/thumbnails/{stem}_thumb.jpg"
            
            # 生成缩略图 URL
            if self.public_url:
                return f"{self.public_url}/{thumbnail_key}"
            else:
                return f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{thumbnail_key}"
                
        except Exception as e:
            logger.error(f"生成缩略图 URL 失败: {e}")
            return original_url  # 失败时返回原图
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """
        上传文件到 R2
        
        Args:
            file_data: 文件二进制数据
            file_name: 文件名（会被添加 UUID 前缀避免冲突）
            folder: 文件夹路径
            content_type: MIME 类型
            
        Returns:
            文件的公共 URL，失败返回 None
        """
        if not self.client:
            logger.error("R2 客户端未初始化")
            return None
        
        try:
            # 生成唯一文件名
            unique_name = f"{folder}/{uuid.uuid4().hex[:8]}_{file_name}"
            
            # 上传文件
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=unique_name,
                Body=file_data,
                ContentType=content_type,
                CacheControl='public, max-age=31536000'  # 1年缓存
            )
            
            # 生成公共 URL
            if self.public_url:
                public_url = f"{self.public_url}/{unique_name}"
            else:
                # 如果没有配置公共 URL，使用默认格式
                public_url = f"https://{self.bucket_name}.{self.account_id}.r2.cloudflarestorage.com/{unique_name}"
            
            logger.info(f"文件上传成功: {unique_name}")
            return public_url
            
        except ClientError as e:
            logger.error(f"R2 上传失败: {e}")
            return None
        except Exception as e:
            logger.error(f"R2 上传异常: {e}")
            return None
    
    def upload_file_from_path(
        self,
        file_path: str,
        folder: str = "uploads",
        content_type: str = "image/png"
    ) -> Optional[str]:
        """
        从本地路径上传文件到 R2
        
        Args:
            file_path: 本地文件路径
            folder: 文件夹路径
            content_type: MIME 类型
            
        Returns:
            文件的公共 URL，失败返回 None
        """
        if not self.client:
            logger.error("R2 客户端未初始化")
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
            logger.error(f"R2 上传异常: {e}")
            return None
    
    def delete_file(self, file_url: str) -> bool:
        """
        删除 R2 中的文件
        
        Args:
            file_url: 文件的公共 URL
            
        Returns:
            是否删除成功
        """
        if not self.client:
            logger.error("R2 客户端未初始化")
            return False
        
        try:
            # 从 URL 提取 key
            if self.public_url and file_url.startswith(self.public_url):
                key = file_url.replace(f"{self.public_url}/", "")
            else:
                # 尝试从 URL 最后部分提取
                key = file_url.split('/')[-1]
            
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"文件删除成功: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"R2 删除失败: {e}")
            return False
        except Exception as e:
            logger.error(f"R2 删除异常: {e}")
            return False
    
    def file_exists(self, file_url: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_url: 文件的公共 URL
            
        Returns:
            文件是否存在
        """
        if not self.client:
            return False
        
        try:
            # 从 URL 提取 key
            if self.public_url and file_url.startswith(self.public_url):
                key = file_url.replace(f"{self.public_url}/", "")
            else:
                key = file_url.split('/')[-1]
            
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except ClientError:
            return False
        except Exception as e:
            logger.error(f"R2 检查文件异常: {e}")
            return False


# 全局单例
_r2_service: Optional[R2StorageService] = None


def get_r2_service() -> R2StorageService:
    """获取 R2 服务单例"""
    global _r2_service
    if _r2_service is None:
        _r2_service = R2StorageService()
    return _r2_service
