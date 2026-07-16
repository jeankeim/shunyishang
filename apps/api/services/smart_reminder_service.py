"""
智能提醒服务
- 天气变化推送（降温/降雨自动推送穿搭建议）
- 衣橱闲置提醒（30天未穿衣物提醒）
- 节气换装提醒（节气前1-2天推送换装建议）
复用已有推送系统 (push_service)
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.cache import cache as redis_cache

logger = logging.getLogger(__name__)


class SmartReminderService:
    """智能提醒服务"""

    def check_and_notify(self, user_id: int, weather_info: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        执行所有智能提醒检查，返回触发的提醒列表

        Args:
            user_id: 用户ID
            weather_info: 当前天气信息 {temperature, weather_condition, ...}

        Returns:
            触发的提醒列表 [{"type": "weather_change", "message": "..."}, ...]
        """
        triggered = []

        # 1. 天气变化提醒
        weather_alert = self._check_weather_change(user_id, weather_info)
        if weather_alert:
            triggered.append(weather_alert)

        # 2. 衣橱闲置提醒
        idle_alert = self._check_idle_wardrobe(user_id)
        if idle_alert:
            triggered.append(idle_alert)

        # 3. 节气换装提醒
        solar_term_alert = self._check_solar_term_change(user_id)
        if solar_term_alert:
            triggered.append(solar_term_alert)

        return triggered

    def _check_weather_change(
        self, user_id: int, weather_info: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """检查天气变化并生成穿搭建议推送"""
        if not weather_info:
            return None

        temp = weather_info.get("temperature")
        condition = weather_info.get("weather_condition", "")
        city = weather_info.get("city", "")

        if temp is None:
            return None

        # 检查缓存：避免同日重复推送
        cache_key = f"weather_alert:{user_id}:{date.today()}"
        if redis_cache.get(cache_key):
            return None

        # 获取昨天温度（如果缓存中有）
        yesterday_key = f"weather_snapshot:{user_id}"
        yesterday_temp_str = redis_cache.get(yesterday_key)
        yesterday_temp = float(yesterday_temp_str) if yesterday_temp_str else None

        # 保存今日温度快照
        redis_cache.set(yesterday_key, str(temp), ex=86400 * 2)  # 2天TTL

        alerts = []

        # 降温提醒（降幅 > 5°C）
        if yesterday_temp and yesterday_temp - temp >= 5:
            delta = int(yesterday_temp - temp)
            alerts.append(f"今日降温 {delta}°C，建议添加外套或保暖衣物")

        # 升温提醒（升幅 > 8°C）
        if yesterday_temp and temp - yesterday_temp >= 8:
            delta = int(temp - yesterday_temp)
            alerts.append(f"今日升温 {delta}°C，建议选择轻薄透气的穿搭")

        # 降雨提醒
        rain_keywords = ["雨", "rain", "shower", "thunderstorm", "drizzle"]
        if any(kw in condition.lower() for kw in rain_keywords):
            alerts.append("今日有降雨，建议携带雨具并选择防水穿搭")

        if not alerts:
            return None

        # 生成推送
        message = "；".join(alerts)
        if city:
            message = f"📍 {city}：{message}"

        # 发送推送
        try:
            from apps.api.services.push_service import push_service
            push_service.send_push(
                user_id=user_id,
                push_type="weather_alert",
                title="天气变化提醒",
                body=message,
                data={"temperature": temp, "condition": condition, "city": city},
            )
        except Exception as e:
            logger.warning(f"[SmartReminder] 天气推送失败: {e}")

        # 设置防重复缓存
        redis_cache.set(cache_key, "1", ex=86400)

        return {"type": "weather_change", "message": message}

    def _check_idle_wardrobe(self, user_id: int) -> Optional[Dict[str, Any]]:
        """检查衣橱闲置提醒（30天未穿的衣物）"""
        # 检查缓存：每周最多提醒一次
        cache_key = f"idle_wardrobe:{user_id}:{date.today().isocalendar()[1]}"
        if redis_cache.get(cache_key):
            return None

        threshold_date = date.today() - timedelta(days=30)

        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, name, category, primary_element, last_worn_date, created_at
                        FROM user_wardrobe
                        WHERE user_id = %s
                          AND is_active = TRUE
                          AND (last_worn_date IS NULL OR last_worn_date < %s)
                          AND created_at < %s
                        ORDER BY last_worn_date ASC NULLS FIRST
                        LIMIT 5
                        """,
                        [user_id, threshold_date, threshold_date],
                    )
                    idle_items = cur.fetchall()
        except Exception as e:
            logger.debug(f"[SmartReminder] 衣橱查询失败: {e}")
            return None

        if not idle_items:
            return None

        count = len(idle_items)
        names = "、".join(item["name"] for item in idle_items[:3])
        message = f"您有 {count} 件衣物超过30天未穿（{names}等），不妨拿出来搭配试试？"

        # 发送推送
        try:
            from apps.api.services.push_service import push_service
            push_service.send_push(
                user_id=user_id,
                push_type="idle_wardrobe",
                title="衣橱闲置提醒",
                body=message,
                data={"idle_count": count, "item_ids": [item["id"] for item in idle_items]},
            )
        except Exception as e:
            logger.warning(f"[SmartReminder] 闲置推送失败: {e}")

        redis_cache.set(cache_key, "1", ex=86400 * 7)  # 7天TTL

        return {"type": "idle_wardrobe", "message": message, "idle_items": [dict(i) for i in idle_items]}

    def _check_solar_term_change(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        检查是否有节气换装提醒。

        逻辑：
        - 未来2天内有节气 → 生成个性化换装建议
        - 防重复：缓存控制，每个节气只提醒一次（缓存键含节气名）
        """
        # 防重复：缓存键含节气名称，同一节气7天内只提醒一次
        from apps.api.services.solar_term_service import solar_term_service

        upcoming = solar_term_service.get_upcoming_solar_term(days_ahead=2)
        if not upcoming:
            return None

        term_name = upcoming["name"]
        cache_key = f"solar_term_alert:{user_id}:{term_name}:{date.today().year}"
        if redis_cache.get(cache_key):
            return None

        # 获取用户八字，生成个性化建议
        message = None
        try:
            from apps.api.services.user_service import get_user_bazi
            user_bazi = get_user_bazi(user_id)
            message = solar_term_service.get_outfit_suggestion(upcoming, user_bazi)
        except Exception as e:
            logger.warning(f"[SmartReminder] 节气建议生成失败 user={user_id}: {e}")

        if not message:
            # 兜底通用文案
            from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP
            colors = "、".join(ELEMENT_COLOR_MAP.get(upcoming["element"], [])[:2]) or "五行"
            message = (
                f"{term_name}将至，{upcoming['description']}。"
                f"建议穿{colors}色系服饰，顺应天时。"
            )

        # 发送推送
        try:
            from apps.api.services.push_service import push_service
            push_service.send_push(
                user_id=user_id,
                push_type="solar_term",
                title=f"节气换装提醒 · {term_name}",
                body=message[:100],
                data={
                    "solar_term": term_name,
                    "term_date": upcoming["date"].isoformat(),
                    "element": upcoming["element"],
                    "days_until": upcoming["days_until"],
                },
            )
        except Exception as e:
            logger.warning(f"[SmartReminder] 节气推送失败: {e}")

        # 设置防重复缓存（7天TTL，确保同一节气不重复提醒）
        redis_cache.set(cache_key, "1", ex=86400 * 7)

        return {"type": "solar_term", "message": message, "solar_term": term_name}


# 模块级单例
smart_reminder_service = SmartReminderService()
