"""
推送调度器
使用 asyncio 定时任务实现每日运势推送和日记提醒
- N+1查询消除（NOT EXISTS子查询合并）
- 推送内容个性化（调用 fortune_engine）
- 运势预计算写入 daily_fortune + Redis缓存
"""

import asyncio
import json
import logging
from datetime import date, datetime, time, timedelta

from apps.api.core.cache import cache
from apps.api.core.database import DatabasePool
from apps.api.services.fortune_engine import calculate_daily_fortune
from apps.api.services.push_service import push_service
from apps.api.services.solar_term_service import solar_term_service
from apps.api.services.user_service import get_user_bazi
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

logger = logging.getLogger(__name__)

# 运势等级映射（用于推送文案）
_FORTUNE_LEVEL_MAP = [
    (80, "大吉"),
    (65, "良好"),
    (50, "平稳"),
    (0, "偏弱"),
]


def _fortune_level(score: int) -> str:
    """运势分数 -> 等级文案"""
    for threshold, label in _FORTUNE_LEVEL_MAP:
        if score >= threshold:
            return label
    return "平稳"


def _build_fortune_push_body(fortune: dict) -> str:
    """
    基于运势数据生成个性化推送文案（控制在100字以内）。
    格式示例：'今日运势大吉，宜穿青绿色系单品，查看你的五行穿搭指南'
    """
    overall = fortune.get("overall_score", 65)
    level = _fortune_level(overall)
    lucky = fortune.get("lucky_elements", {})
    colors = lucky.get("colors", [])
    color_text = "、".join(colors[:2]) if colors else "五行"
    body = f"今日运势{level}（{overall}分），宜穿{color_text}色系单品，查看你的五行穿搭指南"
    return body[:100]


DEFAULT_FORTUNE_BODY = "点击查看您的专属五行运势和穿搭建议"


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
        cls._tasks.append(asyncio.create_task(cls._solar_term_reminder_loop()))
        cls._tasks.append(asyncio.create_task(cls._weekly_outfit_preview_loop()))

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

    # ------------------------------------------------------------------
    # 运势推送（N+1已消除 + 个性化内容 + 预计算）
    # ------------------------------------------------------------------

    @classmethod
    async def schedule_daily_fortune_push(cls):
        """每日运势推送（遍历启用的用户，单条SQL消除N+1）"""
        now = datetime.now()
        current_hour = now.hour

        # 只在 7-9 点之间推送
        if not (7 <= current_hour <= 9):
            return

        today = now.date()

        try:
            # 单条SQL：合并"已启用" + "今日未推送"判断，消除N+1
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ups.user_id
                        FROM user_push_settings ups
                        WHERE ups.enabled = TRUE
                          AND ups.fortune_push = TRUE
                          AND EXTRACT(HOUR FROM ups.fortune_push_time) = %s
                          AND NOT EXISTS (
                              SELECT 1 FROM push_notifications pn
                              WHERE pn.user_id = ups.user_id
                                AND pn.type = 'fortune_daily'
                                AND pn.sent_at >= CURRENT_DATE
                          )
                        """,
                        [current_hour],
                    )
                    rows = cur.fetchall()

            for (user_id,) in rows:
                try:
                    await cls._push_fortune_for_user(user_id, today, now)
                except Exception as e:
                    logger.error(
                        f"[PushScheduler] 发送运势推送失败 user={user_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"[PushScheduler] 查询运势推送用户失败: {e}")

    @classmethod
    async def _push_fortune_for_user(
        cls, user_id: int, today: date, now: datetime
    ):
        """对单个用户：预计算运势 -> 写入DB/缓存 -> 发送个性化推送"""

        # --- Step 1: 预计算运势（失败不阻塞推送） ---
        fortune = None
        body = DEFAULT_FORTUNE_BODY
        try:
            fortune = await cls._precompute_fortune(user_id, today)
            if fortune:
                body = _build_fortune_push_body(fortune)
        except Exception as e:
            logger.warning(
                f"[PushScheduler] 运势预计算失败 user={user_id}: {e}，回退通用文案"
            )

        # --- Step 2: 发送推送 ---
        push_service.send_push(
            user_id=user_id,
            push_type="fortune_daily",
            title="今日运势已更新",
            body=body,
            data={"date": now.strftime("%Y-%m-%d")},
        )

    # ------------------------------------------------------------------
    # 运势预计算：写入 daily_fortune 表 + Redis 缓存
    # ------------------------------------------------------------------

    @classmethod
    async def _precompute_fortune(
        cls, user_id: int, today: date
    ) -> dict | None:
        """
        预算用户当日运势，写入 daily_fortune（UPSERT）+ Redis缓存。
        返回运势 dict，失败返回 None。
        """
        user_bazi = get_user_bazi(user_id)
        result = calculate_daily_fortune(user_bazi, today)

        # --- 写入 daily_fortune 表（UPSERT，当天无记录则插入） ---
        upsert_sql = """
            INSERT INTO daily_fortune (
                user_id, fortune_date, scores, overall_score,
                advice_text, lucky_elements, outfit_suggestion, bazi_snapshot
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, fortune_date) DO UPDATE SET
                scores = EXCLUDED.scores,
                overall_score = EXCLUDED.overall_score,
                advice_text = EXCLUDED.advice_text,
                lucky_elements = EXCLUDED.lucky_elements,
                outfit_suggestion = EXCLUDED.outfit_suggestion,
                bazi_snapshot = EXCLUDED.bazi_snapshot
        """
        params = [
            user_id,
            today,
            json.dumps(result["scores"]),
            result["overall_score"],
            result["advice_text"],
            json.dumps(result["lucky_elements"]),
            result["outfit_suggestion"],
            json.dumps(result["bazi_snapshot"]),
        ]
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(upsert_sql, params)
                conn.commit()

        # --- 写入 Redis 缓存，TTL 86400s ---
        cache_key = f"fortune_today:{user_id}:{today.isoformat()}"
        await cache.set(cache_key, result, ttl=86400)

        logger.info(
            f"[PushScheduler] 运势预计算完成 user={user_id} date={today}"
        )
        return result

    # ------------------------------------------------------------------
    # 日记提醒（N+1已消除）
    # ------------------------------------------------------------------

    @classmethod
    async def schedule_diary_reminder(cls):
        """日记提醒（遍历启用的用户，单条SQL消除N+1）"""
        now = datetime.now()
        current_hour = now.hour

        # 只在 20-22 点之间推送
        if not (20 <= current_hour <= 22):
            return

        try:
            # 单条SQL：合并"已启用" + "今日未记日记"判断，消除N+1
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ups.user_id
                        FROM user_push_settings ups
                        WHERE ups.enabled = TRUE
                          AND ups.diary_reminder = TRUE
                          AND EXTRACT(HOUR FROM ups.diary_reminder_time) = %s
                          AND NOT EXISTS (
                              SELECT 1 FROM outfit_diaries od
                              WHERE od.user_id = ups.user_id
                                AND od.diary_date = CURRENT_DATE
                          )
                        """,
                        [current_hour],
                    )
                    rows = cur.fetchall()

            for (user_id,) in rows:
                try:
                    push_service.send_push(
                        user_id=user_id,
                        push_type="diary_reminder",
                        title="记录今日穿搭",
                        body="今天的穿搭记录了吗？快来记录一下吧！",
                        data={"date": now.strftime("%Y-%m-%d")},
                    )
                except Exception as e:
                    logger.error(
                        f"[PushScheduler] 发送日记提醒失败 user={user_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"[PushScheduler] 查询日记提醒用户失败: {e}")

    # ------------------------------------------------------------------
    # 节气换装提醒（每日检查一次）
    # ------------------------------------------------------------------

    @classmethod
    async def _solar_term_reminder_loop(cls):
        """节气换装提醒循环 - 每天早上9点检查"""
        while cls._running:
            try:
                await cls.schedule_solar_term_reminder()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PushScheduler] 节气提醒异常: {e}")
            # 每天检查一次（86400秒）
            await asyncio.sleep(86400)

    @classmethod
    async def schedule_solar_term_reminder(cls):
        """节气换装提醒：检查未来2天内是否有节气，对启用用户发送推送"""
        now = datetime.now()

        # 只在 8-10 点之间推送，避免太早或太晚
        if not (8 <= now.hour <= 10):
            return

        # 检查未来2天内是否有节气
        upcoming = solar_term_service.get_upcoming_solar_term(days_ahead=2)
        if not upcoming:
            return

        term_name = upcoming["name"]

        # 防重复：检查今天是否已经为该节气发送过推送（全局维度）
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM push_notifications
                        WHERE type = 'solar_term'
                          AND data::text LIKE %s
                          AND sent_at >= CURRENT_DATE
                        """,
                        [f'%{term_name}%'],
                    )
                    count = cur.fetchone()[0]

            # 如果今天已为该节气发过推送（至少有用户收到了），不再重复
            # 但需要按用户粒度控制，所以下面每个用户单独检查
        except Exception as e:
            logger.warning(f"[PushScheduler] 节气全局去重查询失败: {e}")

        # 查询所有启用推送的用户
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ups.user_id
                        FROM user_push_settings ups
                        WHERE ups.enabled = TRUE
                          AND NOT EXISTS (
                              SELECT 1 FROM push_notifications pn
                              WHERE pn.user_id = ups.user_id
                                AND pn.type = 'solar_term'
                                AND pn.data::text LIKE %s
                                AND pn.sent_at >= CURRENT_DATE - INTERVAL '3 days'
                          )
                        """,
                        [f'%{term_name}%'],
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.error(f"[PushScheduler] 查询节气提醒用户失败: {e}")
            return

        for (user_id,) in rows:
            try:
                # 获取用户八字，生成个性化换装建议
                body = None
                try:
                    user_bazi = get_user_bazi(user_id)
                    body = solar_term_service.get_outfit_suggestion(
                        upcoming, user_bazi
                    )
                except Exception as e:
                    logger.warning(
                        f"[PushScheduler] 节气建议生成失败 user={user_id}: {e}"
                    )

                # 兜底通用文案
                if not body:
                    colors = "、".join(
                        ELEMENT_COLOR_MAP.get(upcoming["element"], [])[:2]
                    ) or "五行"
                    body = (
                        f"{term_name}将至，{upcoming['description']}。"
                        f"建议穿{colors}色系服饰，顺应天时。"
                    )

                push_service.send_push(
                    user_id=user_id,
                    push_type="solar_term",
                    title=f"换季开柜仪式 · {term_name}",
                    body=body[:100],
                    data={
                        "solar_term": term_name,
                        "term_date": upcoming["date"].isoformat(),
                        "element": upcoming["element"],
                        "days_until": upcoming["days_until"],
                        "target": "#wardrobe",
                    },
                )
            except Exception as e:
                logger.error(
                    f"[PushScheduler] 发送节气提醒失败 user={user_id}: {e}"
                )

    # ------------------------------------------------------------------
    # 一周穿搭预告（周日晚上提醒下周方案已就绪）
    # ------------------------------------------------------------------

    @classmethod
    async def _weekly_outfit_preview_loop(cls):
        """一周穿搭预告循环（每小时检查一次）"""
        while cls._running:
            try:
                await cls.schedule_weekly_outfit_preview()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PushScheduler] 一周穿搭预告异常: {e}")
            await asyncio.sleep(3600)

    @classmethod
    async def schedule_weekly_outfit_preview(cls):
        """
        周日 20-21 点推送「下周穿搭已排好」

        单条 SQL 完成「已启用 + 本周未推送」判定以消除 N+1，
        去重靠 data 里写入的本周一日期（同一周只推一次）。
        """
        now = datetime.now()
        if now.weekday() != 6 or not (20 <= now.hour <= 21):
            return

        monday = (now.date() - timedelta(days=now.weekday())).isoformat()

        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT ups.user_id
                        FROM user_push_settings ups
                        WHERE ups.enabled = TRUE
                          AND NOT EXISTS (
                              SELECT 1 FROM push_notifications pn
                              WHERE pn.user_id = ups.user_id
                                AND pn.type = 'weekly_outfit_preview'
                                AND pn.data::text LIKE %s
                          )
                        """,
                        [f'%{monday}%'],
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.error(f"[PushScheduler] 查询一周穿搭预告用户失败: {e}")
            return

        for (user_id,) in rows:
            try:
                push_service.send_push(
                    user_id=user_id,
                    push_type="weekly_outfit_preview",
                    title="下周穿搭已经排好了",
                    body="7 天成套方案已按天气与运势备好，打开首页即可查看，也能一键记日记",
                    data={"week_start": monday, "target": "#chat"},
                )
            except Exception as e:
                logger.error(
                    f"[PushScheduler] 发送一周穿搭预告失败 user={user_id}: {e}"
                )


push_scheduler = PushScheduler()
