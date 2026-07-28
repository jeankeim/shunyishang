"""
异步任务服务
基于 PostgreSQL tasks 表 + FOR UPDATE SKIP LOCKED 实现轻量任务队列
"""

import json
import logging
from typing import Any, Dict, Optional

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _row_to_dict(row) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    task = dict(row)
    task["id"] = str(task["id"])
    for key in ("created_at", "started_at", "finished_at"):
        if task.get(key) is not None:
            task[key] = str(task[key])
    return task


def create_task(user_id: int, task_type: str, payload: Dict[str, Any]) -> str:
    """创建任务，返回 task_id"""
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO tasks (user_id, task_type, payload)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                [user_id, task_type, json.dumps(payload, ensure_ascii=False)],
            )
            row = cur.fetchone()
            conn.commit()
    task_id = str(row["id"])
    logger.info(f"[Task] 创建任务 {task_type} id={task_id} user={user_id}")
    return task_id


def get_task(task_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    """查询任务状态与结果（限本人）"""
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, task_type, status, result, error, created_at, started_at, finished_at
                FROM tasks
                WHERE id = %s AND user_id = %s
                """,
                [task_id, user_id],
            )
            row = cur.fetchone()
    return _row_to_dict(row)


def claim_task() -> Optional[Dict[str, Any]]:
    """worker 认领一个待处理任务（SKIP LOCKED 保证多 worker 不重复认领）"""
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = 'running', started_at = now()
                WHERE id = (
                    SELECT id FROM tasks
                    WHERE status = 'pending'
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id, user_id, task_type, payload, retries
                """
            )
            row = cur.fetchone()
            conn.commit()
    return _row_to_dict(row)


def mark_done(task_id: str, result: Dict[str, Any]) -> None:
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tasks
                SET status = 'done', result = %s, finished_at = now()
                WHERE id = %s
                """,
                [json.dumps(result, ensure_ascii=False), task_id],
            )
            conn.commit()
    logger.info(f"[Task] 任务完成 id={task_id}")


def mark_failed(task_id: str, error: str, retries: int) -> None:
    """失败处理：未超重试上限则重新排队，否则标记失败"""
    if retries < MAX_RETRIES:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tasks
                    SET status = 'pending', retries = retries + 1,
                        error = %s, started_at = NULL
                    WHERE id = %s
                    """,
                    [error[:2000], task_id],
                )
                conn.commit()
        logger.warning(f"[Task] 任务失败重排 id={task_id} retries={retries + 1}: {error}")
    else:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tasks
                    SET status = 'failed', error = %s, finished_at = now()
                    WHERE id = %s
                    """,
                    [error[:2000], task_id],
                )
                conn.commit()
        logger.error(f"[Task] 任务最终失败 id={task_id}: {error}")
