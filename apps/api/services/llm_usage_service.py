"""
后台管理 - 用户大模型调用明细服务

职责：
1. 大模型调用日志落库（user_daily_llm_usage，usage_date 按北京自然日）
2. 明细查询：按用户分组聚合，支持近 N 天 / 单日 / 昵称·ID 关键词过滤

埋点原则：仅在真实发起大模型调用的路径记录（缓存命中不记录）。
图片生成成本：当前在线链路无付费图片生成（海报为 Pillow 本地渲染，
wanx 文生图仅离线脚本使用），image_cost 为预留字段，单价常量见下。
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# DashScope wanx2.1-t2i-turbo 文生图单价（元/张，参考官网定价，调整时同步更新）
IMAGE_COST_PER_WANX_IMAGE = 0.14


def log_llm_usage(
    user_id: Optional[int],
    scene: str,
    query_text: Optional[str] = None,
    result_summary: Optional[str] = None,
    image_cost: float = 0.0,
) -> None:
    """记录一次大模型调用（失败静默，绝不影响主流程）"""
    if not user_id:
        return
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_daily_llm_usage
                        (user_id, usage_date, scene, query_text, result_summary, image_cost)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        today_cn(),
                        (scene or "")[:50] or None,
                        (query_text or "")[:500] or None,
                        (result_summary or "")[:500] or None,
                        image_cost or 0,
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.debug(f"[LLMUsage] 调用日志写入失败（静默）: {e}")


def get_llm_usage(
    days: int = 7,
    date_str: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    查询大模型调用明细（按用户分组）

    Args:
        days: 默认近 N 天（含今天）
        date_str: 单日筛选 YYYY-MM-DD（优先于 days）
        keyword: 按昵称模糊 / 用户ID精确 过滤

    Returns:
        {range, totals{call_count,user_count,image_cost}, users[{...用户信息, records[]}]}
    """
    today = today_cn()
    if date_str:
        try:
            start = end = date.fromisoformat(date_str)
        except ValueError:
            start = end = today
    else:
        end = today
        start = today - timedelta(days=max(1, min(days, 90)) - 1)

    params: List[Any] = [start, end]
    user_filter = ""
    kw = (keyword or "").strip()
    if kw:
        user_filter = " AND (u.nickname ILIKE %s OR u.id::text = %s)"
        params.extend([f"%{kw}%", kw])

    query = f"""
        SELECT l.id, l.user_id, l.usage_date, l.scene, l.query_text,
               l.result_summary, l.image_cost, l.created_at,
               u.nickname, u.created_at AS user_created_at, u.preferred_city
        FROM user_daily_llm_usage l
        JOIN users u ON u.id = l.user_id
        WHERE l.usage_date BETWEEN %s AND %s{user_filter}
        ORDER BY l.created_at DESC, l.id DESC
    """

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    # 按用户分组聚合
    groups: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        uid = row["user_id"]
        g = groups.get(uid)
        if g is None:
            g = groups[uid] = {
                "user_id": uid,
                "nickname": row["nickname"] or f"用户{uid}",
                "created_at": row["user_created_at"].isoformat() if row["user_created_at"] else None,
                "city": row["preferred_city"] or None,
                "call_count": 0,
                "image_cost": 0.0,
                "scenes": set(),
                "records": [],
            }
        g["call_count"] += 1
        g["image_cost"] += float(row["image_cost"] or 0)
        g["scenes"].add(row["scene"])
        g["records"].append({
            "id": row["id"],
            "date": row["usage_date"].isoformat(),
            "scene": row["scene"],
            "query_text": row["query_text"],
            "result_summary": row["result_summary"],
            "image_cost": float(row["image_cost"] or 0),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    users = sorted(groups.values(), key=lambda g: (-g["call_count"], g["user_id"]))
    for g in users:
        g["image_cost"] = round(g["image_cost"], 4)
        g["scenes"] = sorted(g["scenes"])

    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "totals": {
            "call_count": len(rows),
            "user_count": len(users),
            "image_cost": round(sum(g["image_cost"] for g in users), 4),
        },
        "users": users,
    }
