#!/usr/bin/env python3
"""
将本地 items 表（500 件，含 embedding）全量同步到 Zeabur 生产库

流程:
1. 远端补齐 color/style/material 三列（迁移 10 的结构变更）
2. 本地读取全部 items → 分批 upsert 到远端
   - image_url 用 COALESCE 保护：远端已有图片不被本地空值覆盖
3. 删除远端旧 demo 数据（DRESS_001 等 5 条，已确认零引用）
4. 验证：总量 / 空向量 / 性别分布 / 品类×五行 ≥10

用法:
  python scripts/sync_items_to_prod.py            # 执行同步
  python scripts/sync_items_to_prod.py --dry-run  # 只对比不写入
"""

import argparse
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).parent.parent

LOCAL_DB = {
    "host": "localhost", "port": 5432,
    "database": "wuxing_db", "user": "wuxing_user", "password": "wuxing_password",
}

# 同步列（不含 created_at/updated_at，远端自行维护）
SYNC_COLS = [
    "item_code", "name", "category", "primary_element", "secondary_element",
    "energy_intensity", "gender", "attributes_detail", "embedding",
    "applicable_weather", "applicable_seasons", "temperature_range",
    "functionality", "thickness_level", "color", "style", "material",
    "image_url",
]

OLD_DEMO_CODES = ("DRESS_001", "JACKET_001", "PANTS_001", "SHIRT_001", "SHOES_001")

# 以 text 传输、写入时 cast 回原类型的列
JSONB_COLS = {"attributes_detail", "applicable_weather", "applicable_seasons",
              "temperature_range", "functionality"}

BATCH_SIZE = 50


def log(level: str, message: str):
    print(f"[{level}] {message}")


def get_prod_url() -> str:
    env_path = ROOT / ".env.production"
    for line in env_path.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(".env.production 中未找到 DATABASE_URL")


def ensure_remote_columns(remote):
    """远端补齐迁移 10 的三列（幂等）"""
    cur = remote.cursor()
    cur.execute("""
        ALTER TABLE items
            ADD COLUMN IF NOT EXISTS color VARCHAR(50),
            ADD COLUMN IF NOT EXISTS style VARCHAR(50),
            ADD COLUMN IF NOT EXISTS material VARCHAR(50)
    """)
    remote.commit()
    cur.close()
    log("INFO", "远端表结构已补齐 color/style/material")


def fetch_local_items(local):
    cur = local.cursor()
    cols = ", ".join(
        f"{c}::text" if (c == "embedding" or c in JSONB_COLS) else c
        for c in SYNC_COLS
    )
    cur.execute(f"SELECT {cols} FROM items ORDER BY item_code")
    rows = cur.fetchall()
    cur.close()
    log("INFO", f"本地读取 {len(rows)} 条")
    return rows


def upsert_remote(remote, rows):
    cur = remote.cursor()
    col_list = ", ".join(SYNC_COLS)
    # embedding 以 text 传输，插入时 cast 回 vector
    template = "(" + ", ".join(
        "%s::vector" if c == "embedding" else ("%s::jsonb" if c in JSONB_COLS else "%s")
        for c in SYNC_COLS
    ) + ")"
    update_sets = []
    for c in SYNC_COLS:
        if c == "item_code":
            continue
        if c == "image_url":
            # 保护远端已有图片：本地为 NULL 时不覆盖
            update_sets.append("image_url = COALESCE(EXCLUDED.image_url, items.image_url)")
        else:
            update_sets.append(f"{c} = EXCLUDED.{c}")
    update_sets.append("updated_at = CURRENT_TIMESTAMP")
    sql = f"""
        INSERT INTO items ({col_list})
        VALUES %s
        ON CONFLICT (item_code) DO UPDATE SET {", ".join(update_sets)}
    """
    total = len(rows)
    done = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        execute_values(cur, sql, batch, template=template)
        remote.commit()
        done += len(batch)
        log("INFO", f"已同步 {done}/{total} 条")
    cur.close()


def delete_old_demo(remote):
    cur = remote.cursor()
    cur.execute("DELETE FROM items WHERE item_code IN %s", (OLD_DEMO_CODES,))
    deleted = cur.rowcount
    remote.commit()
    cur.close()
    log("INFO", f"删除旧 demo 数据 {deleted} 条")


def verify(remote, expected_total: int):
    cur = remote.cursor()
    cur.execute("""
        SELECT count(*),
               count(*) FILTER (WHERE embedding IS NULL),
               count(*) FILTER (WHERE image_url IS NOT NULL),
               count(*) FILTER (WHERE color IS NULL)
        FROM items
    """)
    total, null_emb, has_img, null_color = cur.fetchone()
    log("INFO", f"远端总量: {total} | 空向量: {null_emb} | 有图: {has_img} | color 缺失: {null_color}")

    cur.execute("SELECT gender, count(*) FROM items GROUP BY gender ORDER BY gender")
    log("INFO", f"性别分布: {cur.fetchall()}")

    cur.execute("""
        SELECT category, primary_element, count(*)
        FROM items GROUP BY category, primary_element
        HAVING count(*) < 10 ORDER BY 1, 2
    """)
    short = cur.fetchall()
    if short:
        log("WARN", f"未达标格子（<10）: {short}")
    else:
        log("SUCCESS", "所有品类×五行格子 ≥ 10")
    cur.close()

    ok = (total == expected_total and null_emb == 0 and not short)
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只对比不写入")
    args = parser.parse_args()

    local = psycopg2.connect(**LOCAL_DB)
    remote = psycopg2.connect(get_prod_url(), connect_timeout=10)

    rows = fetch_local_items(local)

    if args.dry_run:
        cur = remote.cursor()
        cur.execute("SELECT count(*) FROM items")
        log("INFO", f"[dry-run] 远端当前 {cur.fetchone()[0]} 条，同步后预期 {len(rows)} 条")
        cur.close()
        local.close()
        remote.close()
        return 0

    ensure_remote_columns(remote)
    upsert_remote(remote, rows)
    delete_old_demo(remote)

    log("INFO", "-" * 50)
    ok = verify(remote, expected_total=len(rows))

    local.close()
    remote.close()

    if ok:
        log("SUCCESS", "生产库同步完成，目标全部达成！")
        return 0
    log("ERROR", "同步完成但验证未全部通过，请检查上方输出")
    return 1


if __name__ == "__main__":
    sys.exit(main())
