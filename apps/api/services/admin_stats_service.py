"""
后台管理 - 运营统计服务

职责：
1. 推荐请求日志落库（recommend_logs）
2. 每日指标聚合（daily_dashboard_stats 快照表 + 当天实时计算）
3. 看板数据查询（近 N 天趋势 + 累计概况）

时区约定：
- TIMESTAMPTZ 列按 `AT TIME ZONE 'Asia/Shanghai'` 取北京自然日；
- 历史遗留 TIMESTAMP（naive）列均由 NOW()/CURRENT_TIMESTAMP 写入，
  数据库会话时区为 UTC，故按 `AT TIME ZONE 'UTC'` 解释后再转北京日期。
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn

logger = logging.getLogger(__name__)

# naive timestamp 列 → 北京自然日 表达式
_NAIVE_DAY = "(({col} AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Shanghai')::date"
# timestamptz 列 → 北京自然日 表达式
_TZ_DAY = "({col} AT TIME ZONE 'Asia/Shanghai')::date"


# ============================================================
# 推荐日志
# ============================================================

def log_recommend(
    user_id: Optional[int],
    scene: Optional[str],
    query_text: Optional[str],
    source: str,
    item_count: int,
    duration_ms: Optional[int] = None,
) -> None:
    """记录一次推荐请求（失败静默，绝不影响主流程）"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO recommend_logs
                        (user_id, scene, query_text, source, item_count, duration_ms)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        (scene or "")[:50] or None,
                        (query_text or "")[:500] or None,
                        source,
                        item_count,
                        duration_ms,
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.debug(f"[AdminStats] 推荐日志写入失败（静默）: {e}")


# ============================================================
# 每日指标聚合
# ============================================================

def compute_daily_stats(cur, stat_date: date) -> Dict[str, int]:
    """
    计算指定日期的全部看板指标（使用调用方游标，便于事务内复用）

    返回 dict: dau/new_users/recommend_count/api_requests/diary_count/
               fortune_count/like_count/dislike_count/wardrobe_added
    """
    d = stat_date

    # --- DAU：当天在任一业务表留痕的去重用户 ---
    cur.execute(
        f"""
        SELECT COUNT(DISTINCT user_id)::int FROM (
            SELECT id AS user_id FROM users
             WHERE {_NAIVE_DAY.format(col='last_login_at')} = %s
            UNION ALL
            SELECT user_id FROM user_behaviors
             WHERE user_id IS NOT NULL
               AND {_NAIVE_DAY.format(col='created_at')} = %s
            UNION ALL
            SELECT user_id FROM feedback_logs
             WHERE {_NAIVE_DAY.format(col='created_at')} = %s
            UNION ALL
            SELECT user_id FROM outfit_diaries
             WHERE {_TZ_DAY.format(col='created_at')} = %s
            UNION ALL
            SELECT user_id FROM daily_fortune
             WHERE {_TZ_DAY.format(col='created_at')} = %s
            UNION ALL
            SELECT user_id FROM recommend_logs
             WHERE user_id IS NOT NULL
               AND {_TZ_DAY.format(col='created_at')} = %s
        ) t
        """,
        (d, d, d, d, d, d),
    )
    dau = cur.fetchone()[0] or 0

    def _count_naive(table: str, extra: str = "") -> int:
        cur.execute(
            f"SELECT COUNT(*)::int FROM {table} "
            f"WHERE {_NAIVE_DAY.format(col='created_at')} = %s {extra}",
            (d,),
        )
        return cur.fetchone()[0] or 0

    def _count_tz(table: str, extra: str = "") -> int:
        cur.execute(
            f"SELECT COUNT(*)::int FROM {table} "
            f"WHERE {_TZ_DAY.format(col='created_at')} = %s {extra}",
            (d,),
        )
        return cur.fetchone()[0] or 0

    new_users = _count_naive("users")
    diary_count = _count_tz("outfit_diaries")
    fortune_count = _count_tz("daily_fortune")
    recommend_count = _count_tz("recommend_logs")
    wardrobe_added = _count_naive("user_wardrobe")

    like_count = _count_naive("feedback_logs", "AND action = 'like'")
    dislike_count = _count_naive("feedback_logs", "AND action = 'dislike'")

    # 接口调用量（daily_api_stats.stat_date 写入时即北京日期）
    cur.execute(
        "SELECT COALESCE(SUM(request_count), 0)::int FROM daily_api_stats WHERE stat_date = %s",
        (d,),
    )
    api_requests = cur.fetchone()[0] or 0

    return {
        "dau": dau,
        "new_users": new_users,
        "recommend_count": recommend_count,
        "api_requests": api_requests,
        "diary_count": diary_count,
        "fortune_count": fortune_count,
        "like_count": like_count,
        "dislike_count": dislike_count,
        "wardrobe_added": wardrobe_added,
    }


def upsert_daily_stats(stat_date: date) -> Dict[str, int]:
    """聚合并 UPSERT 指定日期的看板快照（幂等，可重复执行）"""
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            stats = compute_daily_stats(cur, stat_date)
            cur.execute(
                """
                INSERT INTO daily_dashboard_stats
                    (stat_date, dau, new_users, recommend_count, api_requests,
                     diary_count, fortune_count, like_count, dislike_count, wardrobe_added, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                ON CONFLICT (stat_date) DO UPDATE SET
                    dau = EXCLUDED.dau,
                    new_users = EXCLUDED.new_users,
                    recommend_count = EXCLUDED.recommend_count,
                    api_requests = EXCLUDED.api_requests,
                    diary_count = EXCLUDED.diary_count,
                    fortune_count = EXCLUDED.fortune_count,
                    like_count = EXCLUDED.like_count,
                    dislike_count = EXCLUDED.dislike_count,
                    wardrobe_added = EXCLUDED.wardrobe_added,
                    updated_at = NOW()
                """,
                (
                    stat_date,
                    stats["dau"], stats["new_users"], stats["recommend_count"],
                    stats["api_requests"], stats["diary_count"], stats["fortune_count"],
                    stats["like_count"], stats["dislike_count"], stats["wardrobe_added"],
                ),
            )
        conn.commit()
    logger.info(f"[AdminStats] 每日看板聚合完成 {stat_date}: {stats}")
    return stats


# ============================================================
# 看板查询
# ============================================================

def get_dashboard(days: int = 30) -> Dict[str, Any]:
    """
    看板数据：近 N 天趋势（历史取快照表，当天实时计算）+ 累计概况
    """
    days = max(1, min(days, 365))
    today = today_cn()
    start = today - timedelta(days=days - 1)

    trend: List[Dict[str, Any]] = []
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            # 历史快照（不含今天）
            cur.execute(
                """
                SELECT stat_date, dau, new_users, recommend_count, api_requests,
                       diary_count, fortune_count, like_count, dislike_count, wardrobe_added
                FROM daily_dashboard_stats
                WHERE stat_date >= %s AND stat_date < %s
                ORDER BY stat_date
                """,
                (start, today),
            )
            snapshot_map = {row[0]: row[1:] for row in cur.fetchall()}

            # 累计概况
            cur.execute("SELECT COUNT(*)::int FROM users WHERE is_active = TRUE")
            total_users = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*)::int FROM user_wardrobe WHERE is_active = TRUE")
            total_wardrobe = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*)::int FROM items")
            total_items = cur.fetchone()[0] or 0

            # 近 N 天累计
            cur.execute(
                "SELECT COUNT(*)::int FROM recommend_logs WHERE created_at >= %s",
                (start.isoformat(),),
            )
            recommend_total = cur.fetchone()[0] or 0
            cur.execute(
                "SELECT COALESCE(SUM(request_count), 0)::int FROM daily_api_stats WHERE stat_date >= %s",
                (start,),
            )
            api_total_snapshot = cur.fetchone()[0] or 0

    # 组装趋势（缺失日期补 0，保证图表连续）
    for i in range(days):
        d = start + timedelta(days=i)
        if d == today:
            # 当天实时计算（不写快照，避免和定时任务竞争）
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    metrics = compute_daily_stats(cur, d)
        else:
            row = snapshot_map.get(d)
            metrics = {
                "dau": row[0], "new_users": row[1], "recommend_count": row[2],
                "api_requests": row[3], "diary_count": row[4], "fortune_count": row[5],
                "like_count": row[6], "dislike_count": row[7], "wardrobe_added": row[8],
            } if row else {
                "dau": 0, "new_users": 0, "recommend_count": 0, "api_requests": 0,
                "diary_count": 0, "fortune_count": 0, "like_count": 0,
                "dislike_count": 0, "wardrobe_added": 0,
            }
        trend.append({"date": d.isoformat(), **metrics})

    today_metrics = trend[-1]
    return {
        "days": days,
        "today": {"date": today.isoformat(), **today_metrics},
        "totals": {
            "total_users": total_users,
            "total_wardrobe_items": total_wardrobe,
            "total_seed_items": total_items,
            "recommend_total": recommend_total,
            "api_total": api_total_snapshot + today_metrics["api_requests"],
        },
        "trend": trend,
    }
