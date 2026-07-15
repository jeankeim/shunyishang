"""
数据库自动迁移器

启动时按文件名顺序执行 scripts/migrations/*.sql，通过 schema_migrations 表
追踪已执行的迁移，确保每个迁移文件仅执行一次。

设计要点：
- 每个迁移文件在独立事务中执行，成功后写入 schema_migrations。
- 单个迁移失败时仅记录警告并跳过，不中断应用启动（避免因个别历史脚本
  在已存在的库上重复执行而导致整个服务无法启动）。
- 使用 PostgreSQL advisory lock 防止多实例/多 worker 并发执行。
"""

import logging
from pathlib import Path

from apps.api.core.database import DatabasePool

logger = logging.getLogger(__name__)

# 迁移文件目录：<project_root>/scripts/migrations
# 本文件路径：<project_root>/apps/api/core/migrations.py → parents[3] == <project_root>
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "scripts" / "migrations"

# advisory lock key（任意固定常量），防止并发执行迁移
_MIGRATION_LOCK_KEY = 8274651


def _ensure_migrations_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )


def _applied_migrations(cur) -> set[str]:
    cur.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def _list_migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        logger.warning("迁移目录不存在，跳过自动迁移: %s", MIGRATIONS_DIR)
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def run_migrations() -> None:
    """执行所有尚未应用的数据库迁移。"""
    files = _list_migration_files()
    if not files:
        return

    with DatabasePool.get_connection() as conn:
        # 获取 advisory lock，避免多个实例/worker 并发执行迁移
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK_KEY,))
        conn.commit()

        try:
            with conn.cursor() as cur:
                _ensure_migrations_table(cur)
            conn.commit()

            with conn.cursor() as cur:
                applied = _applied_migrations(cur)

            pending = [f for f in files if f.name not in applied]
            if not pending:
                logger.info("数据库迁移已是最新（已应用 %d 个）", len(applied))
                return

            logger.info("发现 %d 个待执行迁移", len(pending))
            success = 0
            for f in pending:
                sql = f.read_text(encoding="utf-8")
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        cur.execute(
                            "INSERT INTO schema_migrations (filename) VALUES (%s) "
                            "ON CONFLICT (filename) DO NOTHING",
                            (f.name,),
                        )
                    conn.commit()
                    success += 1
                    logger.info("迁移成功: %s", f.name)
                except Exception as e:  # noqa: BLE001
                    conn.rollback()
                    logger.warning("迁移跳过/失败 %s: %s", f.name, e)

            logger.info("迁移执行完成：成功 %d / 待执行 %d", success, len(pending))
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK_KEY,))
            conn.commit()
