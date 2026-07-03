"""
推送服务层
处理推送发送、历史、已读、设置等操作
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.schemas.membership import (
    PushSettingsResponse,
    PushSettingsUpdate,
    PushNotificationResponse,
    PushHistoryResponse,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)


class PushService:
    """推送服务"""

    @staticmethod
    def send_push(user_id: int, push_type: str, title: str, body: Optional[str] = None, data: Optional[Dict] = None) -> int:
        """发送推送（记录到DB）"""
        query = """
            INSERT INTO push_notifications (user_id, type, title, body, data, sent_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [
                    user_id,
                    push_type,
                    title,
                    body,
                    json.dumps(data or {}, ensure_ascii=False),
                ])
                row = cur.fetchone()
                conn.commit()

        logger.info(f"[Push] 发送推送: user={user_id}, type={push_type}, title={title}")
        return row["id"] if row else 0

    @staticmethod
    def get_push_history(user_id: int, page: int = 1, size: int = 20) -> PushHistoryResponse:
        """获取推送历史"""
        offset = (page - 1) * size

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 总数
                cur.execute("SELECT COUNT(*) as total FROM push_notifications WHERE user_id = %s", [user_id])
                total = cur.fetchone()["total"]

                # 分页查询
                cur.execute(
                    """
                    SELECT id, type, title, body, data, sent_at, read_at
                    FROM push_notifications
                    WHERE user_id = %s
                    ORDER BY sent_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    [user_id, size, offset],
                )
                rows = cur.fetchall()

        notifications = []
        for row in rows:
            data = row.get("data", {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    data = {}

            notifications.append(PushNotificationResponse(
                id=row["id"],
                type=row["type"],
                title=row["title"],
                body=row.get("body"),
                data=data,
                sent_at=row["sent_at"],
                read_at=row.get("read_at"),
            ))

        return PushHistoryResponse(
            notifications=notifications,
            total=total,
            page=page,
            size=size,
        )

    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """标记已读"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE push_notifications SET read_at = NOW() WHERE id = %s AND user_id = %s AND read_at IS NULL",
                    [notification_id, user_id],
                )
                affected = cur.rowcount
                conn.commit()
        return affected > 0

    @staticmethod
    def get_unread_count(user_id: int) -> UnreadCountResponse:
        """未读数量"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM push_notifications WHERE user_id = %s AND read_at IS NULL",
                    [user_id],
                )
                row = cur.fetchone()
        return UnreadCountResponse(count=row["cnt"] if row else 0)

    @staticmethod
    def get_push_settings(user_id: int) -> PushSettingsResponse:
        """获取推送设置"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM user_push_settings WHERE user_id = %s",
                    [user_id],
                )
                row = cur.fetchone()

        if not row:
            # 自动初始化
            PushService.init_push_settings(user_id)
            return PushSettingsResponse()

        return PushSettingsResponse(
            enabled=row.get("enabled", True),
            fortune_push=row.get("fortune_push", True),
            fortune_push_time=str(row.get("fortune_push_time", "08:00:00")),
            diary_reminder=row.get("diary_reminder", True),
            diary_reminder_time=str(row.get("diary_reminder_time", "21:00:00")),
            marketing=row.get("marketing", False),
            vibrate=row.get("vibrate", True),
        )

    @staticmethod
    def update_push_settings(user_id: int, settings: PushSettingsUpdate) -> PushSettingsResponse:
        """更新推送设置"""
        updates = []
        params: list = []

        if settings.enabled is not None:
            updates.append("enabled = %s")
            params.append(settings.enabled)
        if settings.fortune_push is not None:
            updates.append("fortune_push = %s")
            params.append(settings.fortune_push)
        if settings.fortune_push_time is not None:
            updates.append("fortune_push_time = %s")
            params.append(settings.fortune_push_time)
        if settings.diary_reminder is not None:
            updates.append("diary_reminder = %s")
            params.append(settings.diary_reminder)
        if settings.diary_reminder_time is not None:
            updates.append("diary_reminder_time = %s")
            params.append(settings.diary_reminder_time)
        if settings.marketing is not None:
            updates.append("marketing = %s")
            params.append(settings.marketing)
        if settings.vibrate is not None:
            updates.append("vibrate = %s")
            params.append(settings.vibrate)

        if not updates:
            return PushService.get_push_settings(user_id)

        params.append(user_id)
        query = f"""
            UPDATE user_push_settings
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE user_id = %s
        """

        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()

        return PushService.get_push_settings(user_id)

    @staticmethod
    def init_push_settings(user_id: int) -> PushSettingsResponse:
        """新用户初始化推送设置"""
        query = """
            INSERT INTO user_push_settings (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [user_id])
                conn.commit()
        return PushSettingsResponse()


push_service = PushService()
