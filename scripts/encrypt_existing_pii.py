"""
PIPL 存量敏感数据加密回填脚本（一次性）

前置条件：
1. 已执行迁移 17（birth_date/birth_time/birth_location 改为 TEXT）
2. 已配置 PII_ENCRYPTION_KEY（生成: .venv/bin/python -m apps.api.core.pii_crypto genkey）

用法：
    .venv/bin/python scripts/encrypt_existing_pii.py            # 实际回填
    .venv/bin/python scripts/encrypt_existing_pii.py --dry-run  # 只统计不写库

幂等：已加密（enc:v1: 前缀）的值自动跳过，可安全重复执行。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.api.core.config import settings  # noqa: E402
from apps.api.core.database import DatabasePool  # noqa: E402
from apps.api.core.pii_crypto import encrypt_pii, is_encrypted  # noqa: E402

PII_COLUMNS = ["birth_date", "birth_time", "birth_location"]


def main(dry_run: bool) -> int:
    if not settings.pii_encryption_key:
        print("❌ PII_ENCRYPTION_KEY 未配置，拒绝执行（否则回填无意义）")
        print("   生成密钥: .venv/bin/python -m apps.api.core.pii_crypto genkey")
        return 1

    cols = ", ".join(PII_COLUMNS)
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT id, {cols} FROM users ORDER BY id")
            rows = cur.fetchall()

            total = len(rows)
            updated = 0
            skipped = 0
            for row in rows:
                user_id = row[0]
                set_parts = []
                params = []
                for i, col in enumerate(PII_COLUMNS, start=1):
                    val = row[i]
                    if val is None or val == "" or is_encrypted(val):
                        continue
                    set_parts.append(f"{col} = %s")
                    params.append(encrypt_pii(val))
                if not set_parts:
                    skipped += 1
                    continue
                updated += 1
                if not dry_run:
                    params.append(user_id)
                    cur.execute(
                        f"UPDATE users SET {', '.join(set_parts)} WHERE id = %s",
                        params,
                    )
            if not dry_run:
                conn.commit()

    action = "待回填" if dry_run else "已回填"
    print(f"✅ 扫描 {total} 个用户: {action} {updated} 个, 跳过(空值/已加密) {skipped} 个")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PIPL 存量敏感数据加密回填")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写库")
    args = parser.parse_args()
    sys.exit(main(args.dry_run))
