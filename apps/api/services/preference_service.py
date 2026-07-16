"""
用户偏好学习服务
基于用户反馈（喜欢/不喜欢）自动学习偏好，影响推荐排序
"""

import logging
from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.config import settings

logger = logging.getLogger(__name__)


class PreferenceService:
    """用户偏好学习服务"""

    def update_preference(
        self,
        user_id: int,
        item_attributes: Dict[str, Any],
        action: str,  # 'like' or 'dislike'
    ) -> None:
        """
        根据用户反馈更新偏好

        Args:
            user_id: 用户ID
            item_attributes: 物品属性 {color, primary_element, category, style}
            action: 'like' 或 'dislike'
        """
        delta = 1 if action == 'like' else -1

        # 提取可学习的属性维度（3→6维）
        mappings = [
            ('color', item_attributes.get('color', '')),
            ('element', item_attributes.get('primary_element', '')),
            ('category', item_attributes.get('category', '')),
            ('style', item_attributes.get('style', '')),
            ('material', item_attributes.get('material', '')),
            ('thickness', item_attributes.get('thickness_level', '')),
        ]

        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                for pref_type, pref_key in mappings:
                    if not pref_key:
                        continue
                    cur.execute("""
                        INSERT INTO user_preferences (user_id, pref_type, pref_key, weight, feedback_count, updated_at)
                        VALUES (%s, %s, %s, %s, 1, NOW())
                        ON CONFLICT (user_id, pref_type, pref_key) DO UPDATE SET
                            weight = user_preferences.weight + %s,
                            feedback_count = user_preferences.feedback_count + 1,
                            updated_at = NOW()
                    """, [user_id, pref_type, pref_key, delta, delta])
                conn.commit()

        # 失效偏好缓存
        if settings.redis_enabled:
            try:
                from apps.api.core.cache import cache as redis_cache
                redis_cache.delete_sync(f"user_prefs:{user_id}")
            except Exception as e:
                logger.debug(f"[Preference] Redis 失效失败: {e}")

        logger.debug(f"[Preference] user={user_id}, action={action}, attrs={item_attributes}")

    def get_user_preferences(self, user_id: int) -> Dict[str, Dict[str, int]]:
        """
        获取用户偏好

        Returns:
            {
                "color": {"红色": 3, "蓝色": -1, ...},
                "element": {"火": 2, "水": -2, ...},
                "category": {"上装": 1, ...},
            }
        """
        # Redis 缓存（10分钟 TTL）
        cache_key = f"user_prefs:{user_id}"
        if settings.redis_enabled:
            try:
                from apps.api.core.cache import cache as redis_cache
                cached = redis_cache.get_sync(cache_key)
                if cached is not None:
                    return cached
            except Exception as e:
                logger.debug(f"[Preference] Redis 读取失败: {e}")

        query = """
            SELECT pref_type, pref_key, weight,
                   EXTRACT(EPOCH FROM (NOW() - updated_at)) / 86400 AS days_old
            FROM user_preferences
            WHERE user_id = %s AND weight != 0
            ORDER BY pref_type, ABS(weight) DESC
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                rows = cur.fetchall()

        prefs: Dict[str, Dict[str, float]] = {}
        for row in rows:
            pt = row['pref_type']
            if pt not in prefs:
                prefs[pt] = {}
            # 时间衰减：每日衰减 2%，最低保留 10%
            days_old = row.get('days_old', 0)
            decay_factor = max(0.1, 1.0 - days_old * 0.02)
            prefs[pt][row['pref_key']] = row['weight'] * decay_factor

        # 写入 Redis 缓存
        if settings.redis_enabled:
            try:
                from apps.api.core.cache import cache as redis_cache
                redis_cache.set_sync(cache_key, prefs, ttl=600)
            except Exception as e:
                logger.debug(f"[Preference] Redis 写入失败: {e}")

        return prefs

    def calculate_preference_score(
        self,
        item: Dict[str, Any],
        user_prefs: Dict[str, Dict[str, int]],
    ) -> float:
        """
        计算物品与用户偏好的匹配分数

        Args:
            item: 物品数据 {color, primary_element, category, ...}
            user_prefs: 用户偏好（from get_user_preferences）

        Returns:
            0.0 ~ 1.0 之间的偏好分数（0.5 = 中性，> 0.5 = 偏好，< 0.5 = 不偏好）
        """
        if not user_prefs:
            return 0.5  # 无偏好数据，返回中性分

        total_score = 0.0
        count = 0

        # 检查颜色偏好
        color = item.get('color', '')
        if color and 'color' in user_prefs:
            weight = user_prefs['color'].get(color, 0)
            total_score += self._weight_to_score(weight)
            count += 1

        # 检查五行偏好
        element = item.get('primary_element', '')
        if element and 'element' in user_prefs:
            weight = user_prefs['element'].get(element, 0)
            total_score += self._weight_to_score(weight)
            count += 1

        # 检查分类偏好
        category = item.get('category', '')
        if category and 'category' in user_prefs:
            weight = user_prefs['category'].get(category, 0)
            total_score += self._weight_to_score(weight)
            count += 1

        # 检查风格偏好
        style = item.get('style', '')
        if style and 'style' in user_prefs:
            weight = user_prefs['style'].get(style, 0)
            total_score += self._weight_to_score(weight)
            count += 1

        # 检查材质偏好
        material = item.get('material', '')
        if material and 'material' in user_prefs:
            weight = user_prefs['material'].get(material, 0)
            total_score += self._weight_to_score(weight)
            count += 1

        # 检查厚度偏好
        thickness = item.get('thickness_level', '')
        if thickness and 'thickness' in user_prefs:
            weight = user_prefs['thickness'].get(thickness, 0)
            total_score += self._weight_to_score(weight)
            count += 1

        if count == 0:
            return 0.5  # 没有匹配的偏好维度

        return total_score / count

    @staticmethod
    def _weight_to_score(weight: int) -> float:
        """
        将偏好权重转换为 0~1 分数

        weight > 0 -> 0.6 ~ 1.0（喜欢）
        weight == 0 -> 0.5（中性）
        weight < 0 -> 0.0 ~ 0.4（不喜欢）
        """
        if weight > 0:
            return min(1.0, 0.5 + weight * 0.1)
        elif weight < 0:
            return max(0.0, 0.5 + weight * 0.1)
        return 0.5


# 模块级单例
preference_service = PreferenceService()
