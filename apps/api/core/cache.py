"""
Redis 缓存服务
支持 Upstash Redis (REST API) 和传统 Redis
"""

import json
import logging
from typing import Optional, Any
from datetime import datetime

import httpx

from apps.api.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 缓存服务"""
    
    def __init__(self):
        self.enabled = settings.redis_enabled
        self.default_ttl = 3600  # 默认 1 小时
        
        # Upstash Redis 配置
        self.upstash_url = settings.upstash_redis_rest_url
        self.upstash_token = settings.upstash_redis_rest_token
        self.use_upstash = bool(self.upstash_url and self.upstash_token)
        
        # 传统 Redis 配置
        self.redis_url = settings.redis_url
        self.redis_client = None
        
        # 复用的 httpx 客户端（避免每次请求都新建连接）
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
        
        # 初始化客户端
        if self.enabled:
            self._init_client()
    
    def _init_client(self):
        """初始化 Redis 客户端"""
        if self.use_upstash:
            logger.info(f"✅ Upstash Redis 已启用: {self.upstash_url}")
        else:
            # 传统 Redis (需要 redis-py)
            try:
                import redis
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
                logger.info(f"✅ Redis 已启用: {self.redis_url}")
            except ImportError:
                logger.warning("⚠️  redis-py 未安装，Redis 缓存不可用")
                self.enabled = False
            except Exception as e:
                logger.warning(f"⚠️  Redis 连接失败: {e}")
                self.enabled = False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        try:
            if self.use_upstash:
                return await self._upstash_get(key)
            else:
                return await self._redis_get(key)
        except Exception as e:
            logger.error(f"❌ Redis GET 失败: {key}, 错误: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if not self.enabled:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            
            if self.use_upstash:
                return await self._upstash_set(key, serialized, ttl)
            else:
                return await self._redis_set(key, serialized, ttl)
        except Exception as e:
            logger.error(f"❌ Redis SET 失败: {key}, 错误: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return False
        
        try:
            if self.use_upstash:
                return await self._upstash_delete(key)
            else:
                return await self._redis_delete(key)
        except Exception as e:
            logger.error(f"❌ Redis DELETE 失败: {key}, 错误: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.enabled:
            return False
        
        try:
            if self.use_upstash:
                return await self._upstash_exists(key)
            else:
                return await self._redis_exists(key)
        except Exception as e:
            logger.error(f"❌ Redis EXISTS 失败: {key}, 错误: {e}")
            return False
    
    # === 同步方法（用于非 async 上下文，如 LangGraph 节点） ===

    def get_sync(self, key: str) -> Optional[Any]:
        """同步获取缓存（用于非 async 上下文）"""
        if not self.enabled:
            return None
        try:
            if self.use_upstash:
                client = self._get_sync_client()
                response = client.post(f"{self.upstash_url}/get/{key}")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result") is not None:
                        return json.loads(data["result"])
                return None
            else:
                if self.redis_client:
                    value = self.redis_client.get(key)
                    if value:
                        return json.loads(value)
                return None
        except Exception as e:
            logger.error(f"Redis GET (sync) 失败: {key}, 错误: {e}")
            return None

    def set_sync(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """同步设置缓存（用于非 async 上下文）"""
        if not self.enabled:
            return False
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            if self.use_upstash:
                client = self._get_sync_client()
                response = client.post(f"{self.upstash_url}/set/{key}/{serialized}")
                if response.status_code == 200:
                    client.post(f"{self.upstash_url}/expire/{key}/{ttl}")
                    return True
                return False
            else:
                if self.redis_client:
                    return self.redis_client.setex(key, ttl, serialized)
                return False
        except Exception as e:
            logger.error(f"Redis SET (sync) 失败: {key}, 错误: {e}")
            return False

    def check_health(self) -> bool:
        """检查缓存连接健康状态"""
        if not self.enabled:
            return False
        try:
            if self.use_upstash:
                client = self._get_sync_client()
                response = client.post(f"{self.upstash_url}/ping")
                return response.status_code == 200
            else:
                if self.redis_client:
                    return self.redis_client.ping()
                return False
        except Exception as e:
            logger.error(f"Redis 健康检查失败: {e}")
            return False

    # === Upstash Redis (REST API) ===
    
    def _get_async_client(self) -> httpx.AsyncClient:
        """获取复用的异步 HTTP 客户端"""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self.upstash_token}"},
                timeout=5.0,
            )
        return self._async_client
    
    def _get_sync_client(self) -> httpx.Client:
        """获取复用的同步 HTTP 客户端"""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                headers={"Authorization": f"Bearer {self.upstash_token}"},
                timeout=3.0,
            )
        return self._sync_client
    
    async def _upstash_get(self, key: str) -> Optional[Any]:
        """Upstash GET"""
        client = self._get_async_client()
        response = await client.post(f"{self.upstash_url}/get/{key}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("result") is not None:
                return json.loads(data["result"])
        return None
    
    async def _upstash_set(self, key: str, value: str, ttl: int) -> bool:
        """Upstash SET"""
        client = self._get_async_client()
        # 使用 SET + EXPIRE
        response = await client.post(f"{self.upstash_url}/set/{key}/{value}")
        
        if response.status_code == 200:
            # 设置过期时间
            await client.post(f"{self.upstash_url}/expire/{key}/{ttl}")
            return True
        return False
    
    async def _upstash_delete(self, key: str) -> bool:
        """Upstash DELETE"""
        client = self._get_async_client()
        response = await client.post(f"{self.upstash_url}/del/{key}")
        return response.status_code == 200
    
    async def _upstash_exists(self, key: str) -> bool:
        """Upstash EXISTS"""
        client = self._get_async_client()
        response = await client.post(f"{self.upstash_url}/exists/{key}")
        
        if response.status_code == 200:
            data = response.json()
            return data.get("result", 0) > 0
        return False
    
    # === 传统 Redis ===
    
    async def _redis_get(self, key: str) -> Optional[Any]:
        """传统 Redis GET"""
        if self.redis_client:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        return None
    
    async def _redis_set(self, key: str, value: str, ttl: int) -> bool:
        """传统 Redis SET"""
        if self.redis_client:
            return self.redis_client.setex(key, ttl, value)
        return False
    
    async def _redis_delete(self, key: str) -> bool:
        """传统 Redis DELETE"""
        if self.redis_client:
            return self.redis_client.delete(key) > 0
        return False
    
    async def _redis_exists(self, key: str) -> bool:
        """传统 Redis EXISTS"""
        if self.redis_client:
            return self.redis_client.exists(key) > 0
        return False


# 全局缓存实例
cache = RedisCache()


# === 便捷函数 ===

async def get_cached(key: str) -> Optional[Any]:
    """获取缓存的便捷函数"""
    return await cache.get(key)


async def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存的便捷函数"""
    return await cache.set(key, value, ttl)


async def delete_cached(key: str) -> bool:
    """删除缓存的便捷函数"""
    return await cache.delete(key)
