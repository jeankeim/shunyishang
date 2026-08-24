#!/usr/bin/env python3
"""
批量同步监控：生图每满 50 张自动同步一批到生产库

职责:
1. 轮询本地 items 表 501~800 已生成图片数量
2. 每跨越 50 的整数倍里程碑 → 调用 sync_items_to_prod.py 全量幂等同步
3. 生图进程退出后：对失败项自动重试一轮（断点续跑），再做最终同步

用法:
  python -m scripts.collection.batch_sync_watcher
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg2

ROOT = Path(__file__).parent.parent.parent
SYNC_SCRIPT = ROOT / "scripts" / "sync_items_to_prod.py"
GEN_SCRIPT = ROOT / "scripts" / "collection" / "generate_transform_images.py"
BATCH_SIZE = 50
TOTAL = 300
POLL_INTERVAL = 30

LOCAL_DB = {
    "host": "localhost", "port": 5432,
    "database": "wuxing_db", "user": "wuxing_user", "password": "wuxing_password",
}


def log(msg: str):
    print(f"[watcher] {msg}", flush=True)


def local_image_count() -> int:
    conn = psycopg2.connect(**LOCAL_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM items
        WHERE image_url IS NOT NULL
          AND CAST(SUBSTRING(item_code FROM 6) AS INTEGER) BETWEEN 501 AND 800
    """)
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return n


def gen_running() -> bool:
    r = subprocess.run(["pgrep", "-f", "generate_transform_images"],
                       capture_output=True)
    return r.returncode == 0


def run_sync(tag: str):
    log(f"===== 同步生产库（{tag}）=====")
    r = subprocess.run([sys.executable, str(SYNC_SCRIPT)],
                       capture_output=True, text=True, cwd=str(ROOT))
    tail = "\n".join(r.stdout.strip().splitlines()[-6:])
    log(tail)
    if r.returncode != 0:
        log(f"同步异常 rc={r.returncode}: {r.stderr[-300:]}")
    return r.returncode == 0


def main():
    next_milestone = BATCH_SIZE
    while True:
        n = local_image_count()
        alive = gen_running()

        if n >= next_milestone:
            run_sync(f"里程碑 {next_milestone} 张，当前 {n}/300")
            next_milestone += BATCH_SIZE

        if not alive:
            # 生图进程已退出：失败项重试一轮（脚本自动跳过已有图）
            pending = TOTAL - n
            if pending > 0:
                log(f"生图结束，仍有 {pending} 件无图，自动重试一轮...")
                subprocess.run([sys.executable, str(GEN_SCRIPT)],
                               cwd=str(ROOT))
                n = local_image_count()
            run_sync(f"最终同步 {n}/300")
            log(f"全部完成：{n}/300 件已带图同步生产")
            return 0

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
