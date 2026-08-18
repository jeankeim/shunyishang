"""
后台管理 - 每日数据更新调度器

每日 00:35（北京时间）执行：
1. 聚合昨日运营指标 → daily_dashboard_stats
2. 同步阿里云账单（回刷最近 3 天，覆盖账单延迟）

容错设计：
- 每 60 秒自检一次，以"当日是否已执行"为标记，服务在 00:35 之后
  任意时间重启都会补跑一次（幂等 UPSERT，重复执行无副作用）；
- 启动时补齐最近 7 天缺失的看板快照（覆盖停机窗口）；
- 首次接入账单（表为空）时自动回填最近 30 天。
"""

import asyncio
import logging
from datetime import date, timedelta

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import now_cn, today_cn

logger = logging.getLogger(__name__)

_DAILY_RUN_HOUR = 0
_DAILY_RUN_MINUTE = 35
_BACKFILL_DAYS = 7


class AdminScheduler:
    def __init__(self):
        self._task: asyncio.Task = None
        self._last_run_date: date = None  # 最近一次执行每日任务的北京日期
        self._bootstrapped = False

    # ------------------------------------------------------------------
    # 启动时补齐
    # ------------------------------------------------------------------

    def _bootstrap(self) -> None:
        """补齐最近 7 天缺失的看板快照；账单表为空时回填最近 30 天"""
        from apps.api.services import admin_stats_service, aliyun_billing_service

        today = today_cn()
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT stat_date FROM daily_dashboard_stats WHERE stat_date >= %s",
                        (today - timedelta(days=_BACKFILL_DAYS),),
                    )
                    existing = {row[0] for row in cur.fetchall()}
            for i in range(1, _BACKFILL_DAYS + 1):
                d = today - timedelta(days=i)
                if d not in existing:
                    admin_stats_service.upsert_daily_stats(d)
                    logger.info(f"[AdminScheduler] 补算历史看板 {d}")
        except Exception as e:
            logger.warning(f"[AdminScheduler] 看板补算失败: {e}")

        # 账单首次回填（仅在已配置 AK 且表为空时）
        if settings.billing_configured:
            try:
                with DatabasePool.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT COUNT(*) FROM aliyun_daily_bills")
                        empty = (cur.fetchone()[0] or 0) == 0
                if empty:
                    result = aliyun_billing_service.sync_bills(days=30)
                    logger.info(f"[AdminScheduler] 账单首次回填完成: {result}")
            except Exception as e:
                logger.warning(f"[AdminScheduler] 账单首次回填失败: {e}")

    # ------------------------------------------------------------------
    # 每日任务
    # ------------------------------------------------------------------

    def _run_daily_jobs(self) -> None:
        """执行每日聚合 + 账单同步（阻塞，在 to_thread 中执行）"""
        from apps.api.services import admin_stats_service, aliyun_billing_service

        yesterday = today_cn() - timedelta(days=1)
        try:
            admin_stats_service.upsert_daily_stats(yesterday)
        except Exception as e:
            logger.error(f"[AdminScheduler] 每日看板聚合失败: {e}")

        if settings.billing_configured:
            try:
                result = aliyun_billing_service.sync_bills(days=3)
                logger.info(f"[AdminScheduler] 每日账单同步完成: {result}")
            except Exception as e:
                logger.error(f"[AdminScheduler] 每日账单同步失败: {e}")
        else:
            logger.debug("[AdminScheduler] 未配置账单 AK，跳过账单同步")

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        while True:
            try:
                if not self._bootstrapped:
                    self._bootstrapped = True
                    await asyncio.to_thread(self._bootstrap)

                now = now_cn()
                due = (now.hour, now.minute) >= (_DAILY_RUN_HOUR, _DAILY_RUN_MINUTE)
                if due and self._last_run_date != today_cn():
                    self._last_run_date = today_cn()
                    logger.info("[AdminScheduler] 执行每日数据更新任务")
                    await asyncio.to_thread(self._run_daily_jobs)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"[AdminScheduler] 调度循环异常: {e}")
            await asyncio.sleep(60)

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())
            logger.info("[AdminScheduler] 后台管理每日调度器已启动")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()


admin_scheduler = AdminScheduler()
