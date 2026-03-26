"""
Redis 缓存管理模块
提供统一的缓存接口，支持内存回退
"""

import json
import hashlib
import logging
from typing import Optional, Any, Union
from datetime import datetime, timedelta

from apps.api.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器"""
    
    _instance = None
    _redis_client = None
    _memory_cache = {}  # 内存缓存回退
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._enabled = settings.redis_enabled
            if self._enabled:
                self._init_redis()
    
    def _init_redis(self):
        """初始化 Redis 连接"""
        try:
            import redis
            self._redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30
            )
            # 测试连接
            self._redis_client.ping()
            logger.info("Redis 缓存已连接")
        except Exception as e:
            logger.warning(f"Redis 连接失败，使用内存缓存: {e}")
            self._redis_client = None
            self._enabled = False
    
    def _make_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        content = ":".join(str(arg) for arg in args)
        hash_part = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"wuxing:{prefix}:{hash_part}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._enabled or not self._redis_client:
            # 使用内存缓存
            item = self._memory_cache.get(key)
            if item and item['expire'] > datetime.now():
                return item['value']
            return None
        
        try:
            value = self._redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"读取失败: {e}")
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        if not self._enabled or not self._redis_client:
            # 使用内存缓存
            self._memory_cache[key] = {
                'value': value,
                'expire': datetime.now() + timedelta(seconds=ttl or 3600)
            }
            # 清理过期缓存
            self._cleanup_memory_cache()
            return True
        
        try:
            serialized = json.dumps(value, default=str)
            self._redis_client.setex(key, ttl or 3600, serialized)
            return True
        except Exception as e:
            logger.error(f"写入失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._enabled or not self._redis_client:
            self._memory_cache.pop(key, None)
            return True
        
        try:
            self._redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """清理过期内存缓存"""
        now = datetime.now()
        expired = [k for k, v in self._memory_cache.items() if v['expire'] <= now]
        for k in expired:
            del self._memory_cache[k]
    
    # ========== 业务封装方法 ==========
    
    def get_bazi(self, birth_key: str) -> Optional[dict]:
        """获取八字缓存"""
        key = self._make_key("bazi", birth_key)
        return self.get(key)
    
    def set_bazi(self, birth_key: str, value: dict) -> bool:
        """设置八字缓存"""
        key = self._make_key("bazi", birth_key)
        return self.set(key, value, settings.cache_ttl_bazi)
    
    def get_weather(self, city: str) -> Optional[dict]:
        """获取天气缓存"""
        key = self._make_key("weather", city, datetime.now().strftime("%Y%m%d%H"))
        return self.get(key)
    
    def set_weather(self, city: str, value: dict) -> bool:
        """设置天气缓存"""
        key = self._make_key("weather", city, datetime.now().strftime("%Y%m%d%H"))
        return self.set(key, value, settings.cache_ttl_weather)
    
    def get_search(self, query: str, gender: Optional[str] = None) -> Optional[list]:
        """获取搜索结果缓存"""
        key = self._make_key("search", query, gender or "all")
        return self.get(key)
    
    def set_search(
        self, 
        query: str, 
        value: list, 
        gender: Optional[str] = None
    ) -> bool:
        """设置搜索结果缓存"""
        key = self._make_key("search", query, gender or "all")
        return self.set(key, value, settings.cache_ttl_search)
    
    def get_llm_response(self, prompt_hash: str) -> Optional[str]:
        """获取 LLM 响应缓存"""
        key = self._make_key("llm", prompt_hash)
        return self.get(key)
    
    def set_llm_response(self, prompt_hash: str, value: str, ttl: int = 86400) -> bool:
        """设置 LLM 响应缓存"""
        key = self._make_key("llm", prompt_hash)
        return self.set(key, value, ttl)


# 全局缓存实例
cache = CacheManager()


def cached_bazi(func):
    """八字计算缓存装饰器"""
    def wrapper(birth_year: int, birth_month: int, birth_day: int, birth_hour: int, gender: str, *args, **kwargs):
        birth_key = f"{birth_year}-{birth_month}-{birth_day}-{birth_hour}-{gender}"
        
        # 尝试读取缓存
        cached = cache.get_bazi(birth_key)
        if cached:
            logger.debug(f"八字缓存命中: {birth_key}")
            return cached
        
        # 执行计算
        result = func(birth_year, birth_month, birth_day, birth_hour, gender, *args, **kwargs)
        
        # 写入缓存
        cache.set_bazi(birth_key, result)
        return result
    
    return wrapper


def cached_weather(func):
    """天气查询缓存装饰器"""
    def wrapper(city: str, *args, **kwargs):
        # 尝试读取缓存
        cached = cache.get_weather(city)
        if cached:
            logger.debug(f"天气缓存命中: {city}")
            return cached
        
        # 执行查询
        result = func(city, *args, **kwargs)
        
        # 写入缓存
        cache.set_weather(city, result)
        return result
    
    return wrapper
