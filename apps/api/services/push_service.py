"""
推送服务层（Week 5 增强版）
处理推送发送、历史、已读、设置、行为反馈闭环等操作
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

# 行为反馈权重映射（用于偏好学习）
_FEEDBACK_WEIGHTS = {
    "click": 1.0,    # 点击 → 正向反馈
    "ignore": 0.0,   # 忽略 → 中性
    "close": -0.5,   # 关闭 → 负向反馈
}


class PushService:
    """推送服务"""

    @staticmethod
    def send_push(user_id: int, push_type: str, title: str, body: Optional[str] = None, data: Optional[Dict] = None) -> int:
        """发送推送（记录到DB），支持每日限流 + 行为抑制检查"""
        # 行为抑制检查：用户关闭过该类型推送则跳过
        from apps.api.core.cache import cache as redis_cache
        from datetime import date
        suppress_key = f"push_type_suppress:{user_id}:{push_type}"
        if redis_cache.get(suppress_key):
            logger.info(f"[Push] 行为抑制跳过: user={user_id}, type={push_type}")
            return 0

        # 限流检查：每用户每日最多 3 条推送
        rate_key = f"push_rate:{user_id}:{date.today()}"
        count_str = redis_cache.get(rate_key)
        count = int(count_str) if count_str else 0
        if count >= 3:
            logger.info(f"[Push] 限流跳过: user={user_id}, 今日已发{count}条")
            return 0

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

        # 更新限流计数
        redis_cache.set(rate_key, str(count + 1), ex=86400)

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


    @staticmethod
    def report_push_feedback(
        user_id: int,
        notification_id: int,
        action: str,
    ) -> Dict[str, Any]:
        """
        记录推送行为反馈并更新偏好权重

        行为闭环：
        - click → 正向反馈 → 更新偏好权重（强化推送类型相关的偏好）
        - ignore → 中性 → 不调整
        - close → 负向反馈 → 降低该类推送频率

        Returns:
            {"status": "ok", "action": action, "preference_updated": bool}
        """
        if action not in _FEEDBACK_WEIGHTS:
            return {"status": "error", "message": f"无效行为: {action}"}

        weight = _FEEDBACK_WEIGHTS[action]

        # 记录行为到 user_behaviors 表
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 查询推送的 type 和 data
                    cur.execute(
                        "SELECT type, data FROM push_notifications WHERE id = %s AND user_id = %s",
                        [notification_id, user_id],
                    )
                    notif = cur.fetchone()
                    if not notif:
                        return {"status": "error", "message": "通知不存在"}

                    push_type = notif.get("type", "")
                    push_data = notif.get("data", {})
                    if isinstance(push_data, str):
                        try:
                            push_data = json.loads(push_data)
                        except (json.JSONDecodeError, TypeError):
                            push_data = {}

                    # 记录行为
                    cur.execute(
                        """
                        INSERT INTO user_behaviors (user_id, behavior_type, target_type, target_id, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT DO NOTHING
                        """,
                        [
                            user_id,
                            f"push_{action}",
                            "push_notification",
                            notification_id,
                            json.dumps(
                                {
                                    "push_type": push_type,
                                    "action": action,
                                    "weight": weight,
                                    "push_data": push_data,
                                },
                                ensure_ascii=False,
                            ),
                        ],
                    )

                    # 更新推送记录本身（标记用户行为）
                    if action == "click":
                        cur.execute(
                            "UPDATE push_notifications SET read_at = NOW() WHERE id = %s AND read_at IS NULL",
                            [notification_id],
                        )

                    conn.commit()

            # 偏好更新（仅 click 和 close 触发）
            preference_updated = False
            if weight != 0:
                preference_updated = PushService._update_preference_from_push(
                    user_id, push_type, push_data, weight
                )

            return {
                "status": "ok",
                "action": action,
                "preference_updated": preference_updated,
            }

        except Exception as e:
            logger.warning(f"[Push] 反馈记录失败: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _update_preference_from_push(
        user_id: int, push_type: str, push_data: Dict, weight: float
    ) -> bool:
        """
        根据推送反馈更新用户偏好

        - 正向反馈 (click): 从推送数据中提取五行/颜色信号，增加偏好权重
        - 负向反馈 (close): 降低该类推送的频率权重（存入 Redis）

        Returns:
            是否成功更新了偏好
        """
        from apps.api.core.cache import cache as redis_cache

        # 负向反馈：降低该类型推送频率
        if weight < 0:
            freq_key = f"push_type_suppress:{user_id}:{push_type}"
            redis_cache.set(freq_key, "1", ex=86400 * 30)  # 30天抑制
            logger.info(f"[Push] 抑制推送类型: user={user_id}, type={push_type}")
            return True

        # 正向反馈：从推送数据中提取信号更新偏好
        if weight > 0 and push_data:
            try:
                from apps.api.services.preference_service import preference_service

                # 提取幸运元素作为偏好信号
                lucky_elements = push_data.get("lucky_elements", [])
                primary_element = push_data.get("element", "")
                if not primary_element and lucky_elements:
                    primary_element = lucky_elements[0] if isinstance(lucky_elements, list) else ""

                if primary_element:
                    # 构造属性信号来更新偏好
                    signal_attrs = {
                        "primary_element": primary_element,
                        "color": push_data.get("lucky_colors", [""])[0] if push_data.get("lucky_colors") else "",
                    }
                    preference_service.update_preference(
                        user_id=user_id,
                        item_attributes=signal_attrs,
                        action="like",  # 正向
                    )
                    return True
            except Exception as e:
                logger.debug(f"[Push] 偏好更新失败: {e}")

        return False


push_service = PushService()
