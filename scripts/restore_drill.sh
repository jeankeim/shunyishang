#!/bin/bash
# ============================================================
# 数据库恢复演练脚本（每月执行一次，验证备份真实可恢复）
#
# 流程:
#   1. 取备份文件（参数指定，或自动从 OSS 拉最新一份）
#   2. 启动临时 pgvector 容器（端口 55432，不影响生产库）
#   3. pg_restore 恢复
#   4. 完整性抽查：核心表行数 > 0、users 表可查询
#   5. 打印结果并销毁临时容器
#
# 用法:
#   ./scripts/restore_drill.sh                     # 自动下载 OSS 最新备份
#   ./scripts/restore_drill.sh backups/xxx.dump    # 指定本地备份文件
#
# Cron 示例（每月 1 号凌晨 4 点）:
#   0 4 1 * * cd /opt/shunyishang && ./scripts/restore_drill.sh >> logs/restore_drill.log 2>&1
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."

DRILL_CONTAINER="wuxing-restore-drill"
DRILL_PORT=55432
DB_USER="drill_user"
DB_NAME="drill_db"
PYTHON=".venv/bin/python"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cleanup() {
    docker rm -f "$DRILL_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# ---------- 1. 确定备份文件 ----------
DUMP_FILE="${1:-}"
if [ -z "$DUMP_FILE" ]; then
    log "未指定备份文件，从 OSS 下载最新备份..."
    $PYTHON scripts/backup_db_to_oss.py --download-latest
    DUMP_FILE=$(ls -t backups/wuxing_db_*.dump 2>/dev/null | head -1)
fi
if [ ! -f "$DUMP_FILE" ]; then
    log "❌ 备份文件不存在: $DUMP_FILE"
    exit 1
fi
log "使用备份文件: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"

# ---------- 2. 启动临时容器 ----------
cleanup
log "启动临时恢复容器 $DRILL_CONTAINER (端口 $DRILL_PORT)..."
docker run -d --name "$DRILL_CONTAINER" \
    -e POSTGRES_USER="$DB_USER" \
    -e POSTGRES_PASSWORD=drill_pass \
    -e POSTGRES_DB="$DB_NAME" \
    -p "$DRILL_PORT":5432 \
    ankane/pgvector:latest >/dev/null

# 等待 PG 就绪
for i in $(seq 1 30); do
    if docker exec "$DRILL_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        break
    fi
    [ "$i" -eq 30 ] && { log "❌ 临时容器 30 秒内未就绪"; exit 1; }
    sleep 1
done
log "临时容器就绪"

# ---------- 3. 恢复 ----------
log "开始 pg_restore..."
# --no-owner/--no-acl: 忽略原库属主；恢复告警不中断（个别扩展对象属正常现象）
docker exec -i "$DRILL_CONTAINER" pg_restore \
    -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl < "$DUMP_FILE" || true
log "pg_restore 执行完毕"

# ---------- 4. 完整性抽查 ----------
check_table() {
    local table=$1 min_rows=$2
    local count
    count=$(docker exec "$DRILL_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -A \
        -c "SELECT COUNT(*) FROM $table" 2>/dev/null || echo "-1")
    if [ "$count" -ge "$min_rows" ] 2>/dev/null; then
        log "  ✅ $table: $count 行"
        return 0
    else
        log "  ❌ $table: 查询失败或行数异常 ($count)"
        return 1
    fi
}

log "完整性抽查:"
FAILED=0
check_table "users" 0 || FAILED=1
check_table "items" 1 || FAILED=1
check_table "user_wardrobe" 0 || FAILED=1
check_table "schema_migrations" 1 || FAILED=1

# ---------- 5. 结果 ----------
if [ "$FAILED" -eq 0 ]; then
    log "🎉 恢复演练通过：备份可用"
    exit 0
else
    log "❌ 恢复演练失败：请立即检查备份链路！"
    exit 1
fi
