"""
推送调度器
使用 asyncio 定时任务实现每日运势推送和日记提醒
"""

import asyncio
import logging
from datetime import datetime, time

from apps.api.core.database import DatabasePool
from apps.api.services.push_service import push_service

logger = logging.getLogger(__name__)


class PushScheduler:
    """推送调度器"""

    _tasks: list = []
    _running = False

    @classmethod
    async def start(cls):
        """启动调度器"""
        if cls._running:
            return
        cls._running = True
        logger.info("[PushScheduler] 启动推送调度器")

        # 注册定时任务
        cls._tasks.append(asyncio.create_task(cls._fortune_push_loop()))
        cls._tasks.append(asyncio.create_task(cls._diary_reminder_loop()))

    @classmethod
    async def stop(cls):
        """停止调度器"""
        cls._running = False
        for task in cls._tasks:
            task.cancel()
        cls._tasks.clear()
        logger.info("[PushScheduler] 推送调度器已停止")

    @classmethod
    async def _fortune_push_loop(cls):
        """每日运势推送循环（每小时检查一次）"""
        while cls._running:
            try:
                await cls.schedule_daily_fortune_push()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PushScheduler] 运势推送异常: {e}")
            # 每小时检查一次
            await asyncio.sleep(3600)

    @classmethod
    async def _diary_reminder_loop(cls):
        """日记提醒循环（每小时检查一次）"""
        while cls._running:
            try:
                await cls.schedule_diary_reminder()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PushScheduler] 日记提醒异常: {e}")
            await asyncio.sleep(3600)

    @classmethod
    async def schedule_daily_fortune_push(cls):
        """每日运势推送（遍历启用的用户）"""
        now = datetime.now()
        current_hour = now.hour

        # 只在 7-9 点之间推送
        if not (7 <= current_hour <= 9):
            return

        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ups.user_id
                        FROM user_push_settings ups
                        WHERE ups.enabled = TRUE
                          AND ups.fortune_push = TRUE
                          AND EXTRACT(HOUR FROM ups.fortune_push_time) = %s
                        """,
                        [current_hour],
                    )
                    rows = cur.fetchall()

            for (user_id,) in rows:
                try:
                    # 检查今天是否已推送
                    with DatabasePool.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                SELECT COUNT(*) FROM push_notifications
                                WHERE user_id = %s AND type = 'fortune_daily'
                                  AND sent_at >= CURRENT_DATE
                                """,
                                [user_id],
                            )
                            count = cur.fetchone()[0]

                    if count > 0:
                        continue

                    push_service.send_push(
                        user_id=user_id,
                        push_type="fortune_daily",
                        title="今日运势已更新",
                        body="点击查看您的专属五行运势和穿搭建议",
                        data={"date": now.strftime("%Y-%m-%d")},
                    )
                except Exception as e:
                    logger.error(f"[PushScheduler] 发送运势推送失败 user={user_id}: {e}")

        except Exception as e:
            logger.error(f"[PushScheduler] 查询运势推送用户失败: {e}")

    @classmethod
    async def schedule_diary_reminder(cls):
        """日记提醒（遍历启用的用户）"""
        now = datetime.now()
        current_hour = now.hour

        # 只在 20-22 点之间推送
        if not (20 <= current_hour <= 22):
            return

        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ups.user_id
                        FROM user_push_settings ups
                        WHERE ups.enabled = TRUE
                          AND ups.diary_reminder = TRUE
                          AND EXTRACT(HOUR FROM ups.diary_reminder_time) = %s
                        """,
                        [current_hour],
                    )
                    rows = cur.fetchall()

            for (user_id,) in rows:
                try:
                    # 检查今天是否已记日记
                    with DatabasePool.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                SELECT COUNT(*) FROM outfit_diaries
                                WHERE user_id = %s AND diary_date = CURRENT_DATE
                                """,
                                [user_id],
                            )
                            count = cur.fetchone()[0]

                    if count > 0:
                        continue

                    push_service.send_push(
                        user_id=user_id,
                        push_type="diary_reminder",
                        title="记录今日穿搭",
                        body="今天的穿搭记录了吗？快来记录一下吧！",
                        data={"date": now.strftime("%Y-%m-%d")},
                    )
                except Exception as e:
                    logger.error(f"[PushScheduler] 发送日记提醒失败 user={user_id}: {e}")

        except Exception as e:
            logger.error(f"[PushScheduler] 查询日记提醒用户失败: {e}")


push_scheduler = PushScheduler()
