"""
API 限流模块（固定窗口计数器）

后端优先级：
1. Redis（redis-py，INCR + EXPIRE 原子计数，多 worker 共享）
2. Upstash Redis（REST pipeline，多 worker 共享）
3. 进程内存（dict + Lock 兜底；gunicorn 多 worker 下按进程独立计数，
   实际阈值 ≈ 配置值 × worker 数，可接受）

使用方式：
- 全局限流：main.py 中间件调用 check_rate_limit()
- 端点限流：Depends(auth_rate_limit) 等依赖
"""

import logging
import threading
import time
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status

from apps.api.core.cache import cache
from apps.api.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 内存计数器（兜底）
# ---------------------------------------------------------------------------

class _MemoryCounter:
    """进程内固定窗口计数器（Redis 不可用时兜底）"""

    def __init__(self):
        self._lock = threading.Lock()
        # key -> (window_start_ts, count)
        self._buckets: Dict[str, Tuple[float, int]] = {}
        self._last_cleanup = time.time()

    def incr(self, key: str, window_seconds: int) -> Tuple[int, int]:
        """计数 +1，返回 (当前计数, 窗口剩余秒数)"""
        now = time.time()
        with self._lock:
            # 定期清理过期桶，防止内存膨胀
            if now - self._last_cleanup > 300:
                expired = [
                    k for k, (start, _) in self._buckets.items()
                    if now - start > window_seconds * 2
                ]
                for k in expired:
                    del self._buckets[k]
                self._last_cleanup = now

            start, count = self._buckets.get(key, (now, 0))
            if now - start >= window_seconds:
                # 窗口过期，重新开窗
                start, count = now, 0
            count += 1
            self._buckets[key] = (start, count)
            retry_after = max(1, int(window_seconds - (now - start)))
            return count, retry_after


_memory_counter = _MemoryCounter()


# ---------------------------------------------------------------------------
# 统一计数入口
# ---------------------------------------------------------------------------

async def incr_counter(key: str, window_seconds: int) -> Tuple[int, int]:
    """
    计数 +1（自动选择后端），返回 (当前计数, 建议重试秒数)

    Redis 异常时自动降级到内存计数，保证限流不阻断正常请求。
    """
    if cache.enabled and cache.redis_client is not None:
        try:
            pipe = cache.redis_client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            count, ttl = pipe.execute()
            if ttl < 0:
                # 新 key 或无 TTL：设置过期
                cache.redis_client.expire(key, window_seconds)
                ttl = window_seconds
            return int(count), max(1, int(ttl))
        except Exception as e:
            logger.warning(f"限流 Redis 计数失败，降级内存计数: {e}")
    elif cache.enabled and cache.use_upstash:
        try:
            client = cache._get_async_client()
            resp = await client.post(
                f"{cache.upstash_url}/pipeline",
                json=[["INCR", key], ["EXPIRE", key, str(window_seconds), "NX"]],
                headers={"Authorization": f"Bearer {cache.upstash_token}"},
                timeout=3.0,
            )
            resp.raise_for_status()
            results = resp.json()
            count = int(results[0]["result"])
            return count, window_seconds
        except Exception as e:
            logger.warning(f"限流 Upstash 计数失败，降级内存计数: {e}")

    return _memory_counter.incr(key, window_seconds)


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
    """
    检查限流：返回 (是否放行, 重试等待秒数)

    settings.rate_limit_enabled=False 时始终放行（测试环境）。
    """
    if not settings.rate_limit_enabled:
        return True, 0
    count, retry_after = await incr_counter(key, window_seconds)
    if count > limit:
        return False, retry_after
    return True, 0


# ---------------------------------------------------------------------------
# 工具与 FastAPI 依赖
# ---------------------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    """获取客户端 IP（优先 Nginx 转发头的第一跳）"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def auth_rate_limit(request: Request) -> None:
    """
    登录/注册严格限流依赖（每 IP 每分钟 settings.rate_limit_auth_per_minute 次）

    Usage:
        @router.post("/login", dependencies=[Depends(auth_rate_limit)])
    """
    ip = get_client_ip(request)
    key = f"rl:auth:{ip}"
    allowed, retry_after = await check_rate_limit(
        key, settings.rate_limit_auth_per_minute, 60
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="操作过于频繁，请稍后再试",
            headers={"Retry-After": str(retry_after)},
        )
