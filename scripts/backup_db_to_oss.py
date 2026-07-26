#!/usr/bin/env python3
"""
数据库异地备份脚本：pg_dump → 阿里云 OSS

功能:
1. pg_dump 导出（custom 格式，自带压缩），本地暂存 backups/ 目录
2. 上传 OSS（路径 db_backups/YYYY/MM/wuxing_db_YYYYMMDD_HHMMSS.dump）
3. 保留策略：本地保留 7 天，OSS 保留 30 天（可用环境变量覆盖）
4. OSS 未配置/上传失败时保留本地备份并以非零退出码告警（cron 邮件可感知）

pg_dump 模式（BACKUP_PG_MODE，默认 auto）:
- auto  : 优先本机 pg_dump，不存在时回退 docker exec wuxing-db
- local : 强制本机 pg_dump（RDS 场景）
- docker: 强制 docker exec wuxing-db（自建容器场景）

Cron 示例（每天凌晨 3 点，项目根目录执行）:
    0 3 * * * cd /opt/shunyishang && .venv/bin/python scripts/backup_db_to_oss.py >> logs/backup.log 2>&1

退出码: 0=成功  1=dump 失败  2=dump 成功但上传失败
"""

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# 项目根目录加入 sys.path，复用后端配置
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.core.config import settings  # noqa: E402

BACKUP_DIR = PROJECT_ROOT / "backups"
LOCAL_RETENTION_DAYS = int(os.getenv("BACKUP_LOCAL_RETENTION_DAYS", "7"))
OSS_RETENTION_DAYS = int(os.getenv("BACKUP_OSS_RETENTION_DAYS", "30"))
OSS_PREFIX = "db_backups/"
PG_MODE = os.getenv("BACKUP_PG_MODE", "auto")
DOCKER_CONTAINER = os.getenv("BACKUP_DOCKER_CONTAINER", "wuxing-db")


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def _parse_database_url(url: str) -> dict:
    p = urlparse(url)
    return {
        "host": p.hostname or "localhost",
        "port": str(p.port or 5432),
        "user": p.username or "postgres",
        "password": p.password or "",
        "dbname": (p.path or "/postgres").lstrip("/"),
    }


def run_pg_dump(dump_path: Path) -> bool:
    """执行 pg_dump（custom 格式），返回是否成功"""
    db = _parse_database_url(settings.database_url)
    use_docker = PG_MODE == "docker" or (
        PG_MODE == "auto" and shutil.which("pg_dump") is None
    )

    if use_docker:
        # 容器内 dump 到 stdout，重定向到宿主机文件
        cmd = [
            "docker", "exec", "-i", DOCKER_CONTAINER,
            "pg_dump", "-U", db["user"], "-d", db["dbname"], "-Fc",
        ]
        env = None
        log(f"使用 docker exec {DOCKER_CONTAINER} 执行 pg_dump")
    else:
        cmd = [
            "pg_dump",
            "-h", db["host"], "-p", db["port"],
            "-U", db["user"], "-d", db["dbname"], "-Fc",
        ]
        env = {**os.environ, "PGPASSWORD": db["password"]}
        log(f"使用本机 pg_dump 连接 {db['host']}:{db['port']}/{db['dbname']}")

    try:
        with open(dump_path, "wb") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env, timeout=1800)
        if result.returncode != 0:
            log(f"❌ pg_dump 失败: {result.stderr.decode(errors='replace')[:500]}")
            dump_path.unlink(missing_ok=True)
            return False
        size_mb = dump_path.stat().st_size / 1024 / 1024
        if size_mb < 0.01:
            log("❌ dump 文件异常（<10KB），视为失败")
            return False
        log(f"✅ dump 完成: {dump_path.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        log(f"❌ pg_dump 异常: {e}")
        dump_path.unlink(missing_ok=True)
        return False


def get_oss_bucket():
    """初始化 OSS bucket，未配置返回 None"""
    if not (settings.oss_access_key_id and settings.oss_access_key_secret):
        return None
    try:
        import oss2
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        return oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
    except Exception as e:
        log(f"⚠️ OSS 初始化失败: {e}")
        return None


def upload_to_oss(bucket, dump_path: Path) -> bool:
    """上传备份到 OSS，路径按年/月归档"""
    key = f"{OSS_PREFIX}{datetime.now():%Y/%m}/{dump_path.name}"
    try:
        start = time.time()
        bucket.put_object_from_file(key, str(dump_path))
        log(f"✅ 已上传 OSS: {key} ({time.time() - start:.1f}s)")
        return True
    except Exception as e:
        log(f"❌ OSS 上传失败: {e}")
        return False


def cleanup_local() -> None:
    """清理本地过期备份"""
    cutoff = datetime.now() - timedelta(days=LOCAL_RETENTION_DAYS)
    for f in BACKUP_DIR.glob("wuxing_db_*.dump"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            log(f"🗑 清理本地过期备份: {f.name}")


def cleanup_oss(bucket) -> None:
    """清理 OSS 过期备份"""
    import oss2
    cutoff = datetime.now() - timedelta(days=OSS_RETENTION_DAYS)
    try:
        for obj in oss2.ObjectIterator(bucket, prefix=OSS_PREFIX):
            if datetime.fromtimestamp(obj.last_modified) < cutoff:
                bucket.delete_object(obj.key)
                log(f"🗑 清理 OSS 过期备份: {obj.key}")
    except Exception as e:
        log(f"⚠️ OSS 清理异常（不影响备份结果）: {e}")


def download_latest(bucket, target_dir: Path) -> Path | None:
    """下载 OSS 上最新的备份（供恢复演练使用: --download-latest）"""
    import oss2
    latest = None
    for obj in oss2.ObjectIterator(bucket, prefix=OSS_PREFIX):
        if latest is None or obj.last_modified > latest.last_modified:
            latest = obj
    if latest is None:
        log("❌ OSS 上没有任何备份")
        return None
    target = target_dir / Path(latest.key).name
    bucket.get_object_to_file(latest.key, str(target))
    log(f"✅ 已下载最新备份: {latest.key} → {target}")
    return target


def main() -> int:
    BACKUP_DIR.mkdir(exist_ok=True)

    # 恢复演练辅助模式：仅下载最新备份
    if "--download-latest" in sys.argv:
        bucket = get_oss_bucket()
        if bucket is None:
            log("❌ OSS 未配置，无法下载")
            return 1
        return 0 if download_latest(bucket, BACKUP_DIR) else 1

    dump_path = BACKUP_DIR / f"wuxing_db_{datetime.now():%Y%m%d_%H%M%S}.dump"
    if not run_pg_dump(dump_path):
        return 1

    cleanup_local()

    bucket = get_oss_bucket()
    if bucket is None:
        log("⚠️ OSS 未配置，仅保留本地备份（异地备份未生效！）")
        return 2
    if not upload_to_oss(bucket, dump_path):
        return 2
    cleanup_oss(bucket)

    log("🎉 备份完成（本地 + OSS 异地）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
