"""
Upstash Redis 缓存服务
使用 REST API 而非传统连接，适合 Serverless 环境
"""

import os
import json
from typing import Optional, Any
import httpx

from apps.api.core.config import settings
from apps.api.core.logging_config import get_logger

logger = get_logger(__name__)


class UpstashRedis:
    """
    Upstash Redis REST API 客户端
    
    文档: https://upstash.com/docs/redis/sdks/rest/overview
    """
    
    def __init__(self):
        """初始化 Upstash 客户端"""
        self.rest_url = getattr(settings, 'upstash_redis_rest_url', None)
        self.rest_token = getattr(settings, 'upstash_redis_rest_token', None)
        
        if not all([self.rest_url, self.rest_token]):
            logger.warning("Upstash Redis 配置不完整，缓存功能将被禁用")
            self.enabled = False
            return
        
        self.enabled = True
        self.client = httpx.AsyncClient(
            base_url=self.rest_url,
            headers={
                'Authorization': f'Bearer {self.rest_token}',
                'Content-Type': 'application/json'
            },
            timeout=10.0
        )
        
        logger.info("Upstash Redis 客户端初始化成功")
    
    async def execute(self, command: list) -> Any:
        """
        执行 Redis 命令
        
        Args:
            command: Redis 命令列表，如 ['SET', 'key', 'value']
            
        Returns:
            命令执行结果
        """
        if not self.enabled:
            return None
        
        try:
            response = await self.client.post('/pipeline', json=[command])
            response.raise_for_status()
            result = response.json()
            
            # Upstash 返回格式: {"result": [...]}
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('result') if isinstance(result[0], dict) else result[0]
            
            return None
            
        except httpx.HTTPError as e:
            logger.error(f"Upstash Redis 请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Upstash Redis 执行异常: {e}")
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        设置键值对
        
        Args:
            key: 键
            value: 值
            ex: 过期时间（秒）
            
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        command = ['SET', key, value]
        if ex:
            command.extend(['EX', str(ex)])
        
        result = await self.execute(command)
        return result == 'OK'
    
    async def get(self, key: str) -> Optional[str]:
        """
        获取值
        
        Args:
            key: 键
            
        Returns:
            值，不存在返回 None
        """
        if not self.enabled:
            return None
        
        return await self.execute(['GET', key])
    
    async def delete(self, key: str) -> bool:
        """
        删除键
        
        Args:
            key: 键
            
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        result = await self.execute(['DEL', key])
        return result > 0 if result else False
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键
            
        Returns:
            是否存在
        """
        if not self.enabled:
            return False
        
        result = await self.execute(['EXISTS', key])
        return result > 0 if result else False
    
    async def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置 JSON 数据
        
        Args:
            key: 键
            value: Python 对象（会被序列化为 JSON）
            ex: 过期时间（秒）
            
        Returns:
            是否成功
        """
        json_str = json.dumps(value, ensure_ascii=False)
        return await self.set(key, json_str, ex)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """
        获取 JSON 数据
        
        Args:
            key: 键
            
        Returns:
            Python 对象，不存在返回 None
        """
        json_str = await self.get(key)
        if json_str:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.error(f"JSON 解析失败: {key}")
                return None
        return None
    
    async def close(self):
        """关闭 HTTP 客户端"""
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()


# 全局单例
_upstash_redis: Optional[UpstashRedis] = None


def get_upstash_redis() -> UpstashRedis:
    """获取 Upstash Redis 单例"""
    global _upstash_redis
    if _upstash_redis is None:
        _upstash_redis = UpstashRedis()
    return _upstash_redis
