#!/bin/bash
# ============================================================
# 顺衣尚 ECS 磁盘清理脚本
# 用法: bash deploy/cleanup.sh [--deep]
#
# 背景:
#   ECS 为 2核/2GiB/小磁盘规格，每次 docker compose up -d --build
#   都会产生大量悬空镜像与构建缓存（尤其 Next.js build + 字体子集化
#   阶段），磁盘极易被打满（>95% 后下次构建直接失败）。
#
# 默认清理（安全）:
#   1. 悬空镜像（dangling）——重建后旧版 shunyishang-* 镜像
#   2. 构建缓存（builder cache）——构建过程中最大的占用来源
#   3. 已停止的容器
# --deep 额外清理:
#   4. 所有未被任何容器引用的镜像（含历史 tag 版本）
# ============================================================

set -uo pipefail

DEEP=false
if [ "${1:-}" = "--deep" ]; then
    DEEP=true
fi

echo "========================================="
echo "  顺衣尚 · ECS 磁盘清理"
echo "========================================="

disk_pct() {
    df --output=pcent / 2>/dev/null | tail -1 | tr -d ' %' || df -k / | tail -1 | awk '{gsub("%","",$5); print $5}'
}

echo ""
echo "[清理前] 磁盘占用: $(disk_pct)%"
df -h / | tail -1 | awk '{printf "  总量 %s | 已用 %s | 可用 %s\n", $2, $3, $4}'
echo ""
echo "[清理前] Docker 占用:"
docker system df

echo ""
echo "[1/3] 清理悬空镜像（重建后被替换的旧镜像）..."
docker image prune -f

echo ""
echo "[2/3] 清理构建缓存（Next.js build / 字体阶段产物）..."
docker builder prune -f

echo ""
echo "[3/3] 清理已停止的容器..."
docker container prune -f

if [ "$DEEP" = true ]; then
    echo ""
    echo "[deep] 清理所有未使用的镜像..."
    docker image prune -af
fi

echo ""
echo "========================================="
echo "  ✅ 清理完成，磁盘占用: $(disk_pct)%"
df -h / | tail -1 | awk '{printf "     总量 %s | 已用 %s | 可用 %s\n", $2, $3, $4}'
echo "========================================="

PCT=$(disk_pct)
if [ "$PCT" -ge 85 ] 2>/dev/null; then
    echo ""
    echo "  ⚠️  磁盘占用仍达 ${PCT}%，建议:"
    if [ "$DEEP" = false ]; then
        echo "     1. 执行 bash deploy/cleanup.sh --deep 清理所有未使用镜像"
    fi
    echo "     2. 检查大目录: du -xh --max-depth=1 / | sort -rh | head"
    echo "     3. 评估云盘扩容（构建镜像建议至少预留 20G）"
fi
