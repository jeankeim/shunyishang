"""
游戏化服务 - 积分、成就、五行修炼等级
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool

logger = logging.getLogger(__name__)

# 修炼等级配置
CULTIVATION_LEVELS = [
    {"level": 1, "name": "初识", "min_points": 0, "icon": "🌱"},
    {"level": 2, "name": "入门", "min_points": 100, "icon": "🌿"},
    {"level": 3, "name": "通悟", "min_points": 500, "icon": "🌳"},
    {"level": 4, "name": "精通", "min_points": 2000, "icon": "🏔️"},
    {"level": 5, "name": "大师", "min_points": 5000, "icon": "⭐"},
]

# 积分获取规则
POINTS_RULES = {
    "diary_create": 10,
    "community_like": 2,
    "daily_streak": 5,       # 基础签到
    "streak_bonus_7": 20,    # 连续7天额外奖励
    "streak_bonus_30": 50,   # 连续30天额外奖励
}


class GamificationService:
    """游戏化服务"""

    def get_or_create_user_points(self, user_id: int) -> Dict[str, Any]:
        """获取或初始化用户积分"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM user_points WHERE user_id = %s",
                    [user_id],
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

                # 初始化
                cur.execute(
                    "INSERT INTO user_points (user_id) VALUES (%s) RETURNING *",
                    [user_id],
                )
                row = cur.fetchone()
                conn.commit()
                return dict(row)

    def add_points(
        self,
        user_id: int,
        points: int,
        reason: str,
        reference_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """增加积分并记录历史"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # UPSERT user_points
                cur.execute(
                    """
                    INSERT INTO user_points (user_id, total_points, current_points, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        total_points = user_points.total_points + %s,
                        current_points = user_points.current_points + %s,
                        updated_at = NOW()
                    RETURNING *
                    """,
                    [user_id, points, points, points, points],
                )
                user_pts = cur.fetchone()

                # 记录历史
                cur.execute(
                    """
                    INSERT INTO points_history (user_id, points, reason, reference_id, balance_after)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [user_id, points, reason, reference_id, user_pts["current_points"]],
                )

                # 检查升级
                new_level = self._calculate_level(user_pts["total_points"])
                if new_level > user_pts["cultivation_level"]:
                    cur.execute(
                        "UPDATE user_points SET cultivation_level = %s WHERE user_id = %s",
                        [new_level, user_id],
                    )
                    user_pts["cultivation_level"] = new_level

                conn.commit()
                return dict(user_pts)

    def check_daily_streak(self, user_id: int) -> Dict[str, Any]:
        """检查并更新每日连续签到"""
        today = date.today()
        result = {"streak_updated": False, "points_earned": 0, "streak_days": 0}

        user_pts = self.get_or_create_user_points(user_id)
        last_date = user_pts.get("last_checkin_date")

        if last_date == today:
            # 今日已签到
            result["streak_days"] = user_pts.get("streak_days", 0)
            return result

        streak = user_pts.get("streak_days", 0)
        if last_date and last_date == today - timedelta(days=1):
            streak += 1
        else:
            streak = 1  # 重置

        # 更新签到
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_points
                    SET streak_days = %s, last_checkin_date = %s, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    [streak, today, user_id],
                )
                conn.commit()

        # 基础签到积分
        base_points = POINTS_RULES["daily_streak"]
        self.add_points(user_id, base_points, "daily_streak")
        result["points_earned"] = base_points
        result["streak_days"] = streak
        result["streak_updated"] = True

        # 连续签到额外奖励
        if streak > 0 and streak % 7 == 0:
            bonus = POINTS_RULES.get("streak_bonus_7", 20)
            self.add_points(user_id, bonus, "streak_bonus_7")
            result["points_earned"] += bonus

        if streak > 0 and streak % 30 == 0:
            bonus = POINTS_RULES.get("streak_bonus_30", 50)
            self.add_points(user_id, bonus, "streak_bonus_30")
            result["points_earned"] += bonus

        return result

    def check_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """检查并解锁成就"""
        newly_unlocked = []

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取所有成就定义
                cur.execute("SELECT * FROM achievements")
                all_achievements = cur.fetchall()

                # 获取已解锁成就
                cur.execute(
                    "SELECT achievement_id FROM user_achievements WHERE user_id = %s",
                    [user_id],
                )
                unlocked_ids = {r["achievement_id"] for r in cur.fetchall()}

                # 计算用户各维度数据
                stats = self._get_user_stats(user_id)

                for ach in all_achievements:
                    if ach["id"] in unlocked_ids:
                        continue

                    req_type = ach["requirement_type"]
                    req_val = ach["requirement_value"]
                    current = stats.get(req_type, 0)

                    if current >= req_val:
                        # 解锁成就
                        try:
                            cur.execute(
                                "INSERT INTO user_achievements (user_id, achievement_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [user_id, ach["id"]],
                            )
                            # 奖励积分
                            self.add_points(user_id, ach["points_reward"], "achievement_unlock", ach["id"])
                            newly_unlocked.append(dict(ach))
                        except Exception as e:
                            logger.warning(f"[Gamify] 解锁成就失败: {e}")

                conn.commit()

        return newly_unlocked

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """获取用户游戏化完整数据"""
        user_pts = self.get_or_create_user_points(user_id)
        level_info = CULTIVATION_LEVELS[min(user_pts["cultivation_level"] - 1, len(CULTIVATION_LEVELS) - 1)]
        next_level = CULTIVATION_LEVELS[min(user_pts["cultivation_level"], len(CULTIVATION_LEVELS) - 1)]

        # 获取已解锁成就
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT a.*, ua.unlocked_at
                    FROM user_achievements ua
                    JOIN achievements a ON a.id = ua.achievement_id
                    WHERE ua.user_id = %s
                    ORDER BY ua.unlocked_at DESC
                    """,
                    [user_id],
                )
                unlocked = [dict(r) for r in cur.fetchall()]

                # 获取全部成就（标记是否解锁）
                cur.execute("SELECT * FROM achievements ORDER BY category, requirement_value")
                all_achievements = []
                for r in cur.fetchall():
                    r_dict = dict(r)
                    r_dict["is_unlocked"] = any(u["id"] == r_dict["id"] for u in unlocked)
                    all_achievements.append(r_dict)

        return {
            "total_points": user_pts["total_points"],
            "current_points": user_pts["current_points"],
            "cultivation_level": user_pts["cultivation_level"],
            "level_name": level_info["name"],
            "level_icon": level_info["icon"],
            "next_level_name": next_level["name"],
            "next_level_min_points": next_level["min_points"],
            "level_progress": self._calc_progress(user_pts["total_points"], level_info, next_level),
            "streak_days": user_pts["streak_days"],
            "last_checkin_date": str(user_pts.get("last_checkin_date", "")),
            "unlocked_achievements": unlocked,
            "all_achievements": all_achievements,
        }

    def get_points_history(self, user_id: int, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取积分变动历史"""
        offset = (page - 1) * size
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM points_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    [user_id, size, offset],
                )
                rows = [dict(r) for r in cur.fetchall()]

                cur.execute("SELECT COUNT(*) as total FROM points_history WHERE user_id = %s", [user_id])
                total = cur.fetchone()["total"]

        return {"history": rows, "total": total, "page": page, "size": size}

    # ========== 内部方法 ==========

    def _calculate_level(self, total_points: int) -> int:
        """根据累计积分计算等级"""
        for lvl in reversed(CULTIVATION_LEVELS):
            if total_points >= lvl["min_points"]:
                return lvl["level"]
        return 1

    def _calc_progress(self, total: int, current: dict, next_lvl: dict) -> float:
        """计算当前等级进度 (0~1)"""
        if current["level"] == next_lvl["level"]:
            return 1.0  # 满级
        range_pts = next_lvl["min_points"] - current["min_points"]
        if range_pts <= 0:
            return 1.0
        progress = (total - current["min_points"]) / range_pts
        return min(1.0, max(0.0, progress))

    def _get_user_stats(self, user_id: int) -> Dict[str, int]:
        """计算用户各维度统计数据（用于成就检查）"""
        stats: Dict[str, int] = {}

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 连续打卡天数 (from user_points)
                cur.execute("SELECT streak_days FROM user_points WHERE user_id = %s", [user_id])
                row = cur.fetchone()
                stats["diary_streak"] = row["streak_days"] if row else 0

                # 总日记数
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM outfit_diaries WHERE user_id = %s",
                    [user_id],
                )
                stats["total_diaries"] = cur.fetchone()["cnt"]

                # 社区获赞总数
                cur.execute(
                    """
                    SELECT COALESCE(SUM(like_count), 0) as total_likes
                    FROM community_posts WHERE user_id = %s AND status = 'active'
                    """,
                    [user_id],
                )
                stats["community_likes"] = cur.fetchone()["total_likes"]

                # 社区发帖数
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM community_posts WHERE user_id = %s AND status = 'active'",
                    [user_id],
                )
                stats["community_posts"] = cur.fetchone()["cnt"]

                # 五行均衡度（衣橱五行覆盖数）
                cur.execute(
                    "SELECT COUNT(DISTINCT primary_element) as cnt FROM user_wardrobe WHERE user_id = %s AND is_active = TRUE",
                    [user_id],
                )
                stats["element_balance"] = cur.fetchone()["cnt"]

        return stats


# 模块级单例
gamification_service = GamificationService()
