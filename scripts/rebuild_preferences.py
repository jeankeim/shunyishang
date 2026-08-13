"""
一次性修复脚本：基于 feedback_logs 重建用户偏好

背景：线上库 schema 漂移期间，反馈接口成功写入 feedback_logs，
但偏好学习（user_preferences）与不喜欢排除（user_disliked_items）
静默失败。本脚本按时间顺序重放全部反馈，重建偏好数据。

幂等：每个用户的 user_preferences 先清空再重放，可重复执行；
user_disliked_items 用 ON CONFLICT DO NOTHING 增量补齐。

用法：
    # 本地执行（使用 .env 的 DATABASE_URL）
    PYTHONPATH=. .venv/bin/python scripts/rebuild_preferences.py
    # 指定其他数据库
    DATABASE_URL=postgresql://... PYTHONPATH=. .venv/bin/python scripts/rebuild_preferences.py
"""

import logging

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ATTR_SQL = """
    SELECT name, category, primary_element, attributes_detail,
           color, style, material, thickness_level
    FROM {table} WHERE {where}
"""


def _fetch_item(cur, item_id, item_code, item_source):
    """按来源查询物品属性（wardrobe 物品在 user_wardrobe 表，公共物品在 items 表）"""
    if item_source == "wardrobe" and item_id:
        cur.execute(ATTR_SQL.format(table="user_wardrobe", where="id = %s"), [item_id])
    elif item_code:
        cur.execute(ATTR_SQL.format(table="items", where="item_code = %s"), [item_code])
    else:
        return None
    return cur.fetchone()


def _extract_keys(item) -> list[tuple[str, str]]:
    """提取可学习的 6 维属性键（与 preference_service.update_preference 对齐）"""
    if not item:
        return []
    detail = item.get("attributes_detail") or {}
    color_obj = detail.get("颜色") if isinstance(detail, dict) else None
    color = item.get("color") or (
        color_obj.get("主色") or color_obj.get("名称")
        if isinstance(color_obj, dict) else None
    )
    return [
        ("color", color),
        ("element", item.get("primary_element")),
        ("category", item.get("category")),
        ("style", item.get("style")),
        ("material", item.get("material")),
        ("thickness", item.get("thickness_level")),
    ]


def main():
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT user_id, item_id, item_code, item_source, action
                FROM feedback_logs
                WHERE action IN ('like', 'dislike')
                ORDER BY user_id, created_at, id
            """)
            feedbacks = cur.fetchall()
            logger.info("共 %d 条有效反馈待重放", len(feedbacks))
            if not feedbacks:
                return

            user_ids = sorted({f["user_id"] for f in feedbacks})
            cur.execute(
                "DELETE FROM user_preferences WHERE user_id = ANY(%s)",
                [user_ids],
            )
            logger.info("已清空 %d 个用户的旧偏好，开始重放", cur.rowcount and len(user_ids))

            applied = 0
            for fb in feedbacks:
                item = _fetch_item(cur, fb["item_id"], fb["item_code"], fb["item_source"])
                delta = 1 if fb["action"] == "like" else -1
                for pref_type, pref_key in _extract_keys(item):
                    if not pref_key:
                        continue
                    cur.execute("""
                        INSERT INTO user_preferences (user_id, pref_type, pref_key, weight, feedback_count, updated_at)
                        VALUES (%s, %s, %s, %s, 1, NOW())
                        ON CONFLICT (user_id, pref_type, pref_key) DO UPDATE SET
                            weight = user_preferences.weight + %s,
                            feedback_count = user_preferences.feedback_count + 1,
                            updated_at = NOW()
                    """, [fb["user_id"], pref_type, pref_key, delta, delta])
                    applied += 1
            logger.info("重放完成，写入 %d 条偏好记录", applied)

            # 补齐不喜欢排除列表（幂等）
            cur.execute("""
                INSERT INTO user_disliked_items (user_id, item_code, reason)
                SELECT DISTINCT ON (user_id, item_code) user_id, item_code, feedback_reason
                FROM feedback_logs
                WHERE action = 'dislike' AND item_code IS NOT NULL
                ORDER BY user_id, item_code, created_at DESC
                ON CONFLICT (user_id, item_code) DO NOTHING
            """)
            logger.info("不喜欢排除列表补齐 %d 条", cur.rowcount)

        conn.commit()

    logger.info("重建完成 ✔ 建议清理 Redis 中 user_prefs:* 缓存")


if __name__ == "__main__":
    main()
