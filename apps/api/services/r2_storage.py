"""
Cloudflare R2 对象存储服务
用于生产环境的图片上传和存储
"""

import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
from pathlib import Path
import uuid

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
