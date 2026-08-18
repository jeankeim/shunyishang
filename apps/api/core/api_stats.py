"""
接口调用量采集器（后台管理-运营看板数据源）

设计：
- 中间件每个请求仅在内存计数器 +1（threading.Lock 保护），零 DB 开销；
- 后台 flush 协程每 60 秒将计数批量 UPSERT 到 daily_api_stats 表后清零；
- 按路由前缀归组为 endpoint_group，避免高基数路径爆炸。
"""

import asyncio
import logging
import threading
from typing import Dict, Tuple

from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn

logger = logging.getLogger(__name__)

# 路由前缀 → 分组名（按最长前缀优先匹配）
_GROUP_PREFIXES = [
    ("/api/v1/recommend", "recommend"),
    ("/api/v1/fortune", "fortune"),
    ("/api/v1/wardrobe", "wardrobe"),
    ("/api/v1/diary", "diary"),
    ("/api/v1/auth", "auth"),
    ("/api/v1/bazi", "bazi"),
    ("/api/v1/weather", "weather"),
    ("/api/v1/travel", "travel"),
    ("/api/v1/destiny", "destiny"),
    ("/api/v1/content", "content"),
    ("/api/v1/cultivation", "cultivation"),
    ("/api/v1/poster", "poster"),
    ("/api/v1/tasks", "tasks"),
    ("/api/v1/push", "push"),
    ("/api/v1/admin", "admin"),
]

FLUSH_INTERVAL_SECONDS = 60


def resolve_group(path: str) -> str:
    """路径归组：非 /api/v1 请求返回空串（不统计）"""
    if not path.startswith("/api/v1"):
        return ""
    for prefix, group in _GROUP_PREFIXES:
        if path.startswith(prefix):
            return group
    return "other"


class ApiStatsCollector:
    """内存计数器 + 定时落库"""

    def __init__(self):
        self._lock = threading.Lock()
        # (date_str, group) -> [request_count, success_count, error_count]
        self._counters: Dict[Tuple[str, str], list] = {}
        self._flush_task: asyncio.Task = None

    def record(self, path: str, status_code: int) -> None:
        """中间件调用：记录一次请求（仅 /api/v1）"""
        group = resolve_group(path)
        if not group:
            return
        key = (today_cn().isoformat(), group)
        with self._lock:
            counter = self._counters.setdefault(key, [0, 0, 0])
            counter[0] += 1
            if status_code < 400:
                counter[1] += 1
            else:
                counter[2] += 1

    def _pop_counters(self) -> Dict[Tuple[str, str], list]:
        with self._lock:
            if not self._counters:
                return {}
            snapshot = self._counters
            self._counters = {}
        return snapshot

    def _flush_sync(self) -> None:
        """批量 UPSERT 到 daily_api_stats（阻塞，在 to_thread 中执行）"""
        snapshot = self._pop_counters()
        if not snapshot:
            return
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    for (date_str, group), (total, success, error) in snapshot.items():
                        cur.execute(
                            """
                            INSERT INTO daily_api_stats
                                (stat_date, endpoint_group, request_count, success_count, error_count)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (stat_date, endpoint_group) DO UPDATE SET
                                request_count = daily_api_stats.request_count + EXCLUDED.request_count,
                                success_count = daily_api_stats.success_count + EXCLUDED.success_count,
                                error_count = daily_api_stats.error_count + EXCLUDED.error_count
                            """,
                            (date_str, group, total, success, error),
                        )
                conn.commit()
        except Exception as e:
            # 落库失败：计数回填，下个周期重试，避免数据丢失
            logger.warning(f"[ApiStats] flush 失败，计数回填: {e}")
            with self._lock:
                for key, val in snapshot.items():
                    cur_counter = self._counters.setdefault(key, [0, 0, 0])
                    for i in range(3):
                        cur_counter[i] += val[i]

    async def flush(self) -> None:
        await asyncio.to_thread(self._flush_sync)

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
            try:
                await self.flush()
            except Exception as e:
                logger.warning(f"[ApiStats] flush 循环异常: {e}")

    async def start(self) -> None:
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("[ApiStats] 接口调用量采集器已启动")

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
        # 关闭前兜底 flush，避免最后一分钟计数丢失
        try:
            await asyncio.to_thread(self._flush_sync)
        except Exception as e:
            logger.warning(f"[ApiStats] 关闭前 flush 失败: {e}")


api_stats = ApiStatsCollector()
