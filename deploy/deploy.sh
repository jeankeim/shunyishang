#!/bin/bash
# ============================================================
# 顺衣尚 ECS 一键部署脚本
# 用法: bash deploy/deploy.sh
#
# 功能:
#   1. git pull 拉取最新代码
#   2. 检测本次变更涉及哪些模块
#   3. 仅重建/重启受影响的服务（差异化部署）
#   4. 输出最终容器状态
#
# 适用场景: 本地改完代码 push 到 GitHub 后，SSH 到 ECS 执行本脚本
# ============================================================

set -euo pipefail

cd /opt/shunyishang

echo "========================================="
echo "  顺衣尚 · ECS 一键部署"
echo "========================================="
echo ""

# ---- Step 1: 拉取代码 ----
echo "[1/4] 拉取最新代码..."
git fetch origin main
OLD_HEAD=$(git rev-parse HEAD)
git reset --hard origin/main
NEW_HEAD=$(git rev-parse HEAD)

CHANGED=""
if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
    echo "  ⏭  代码无更新，已是最新"
else
    CHANGED=$(git diff --name-only "$OLD_HEAD" "$NEW_HEAD")
    echo "  ✅ 已更新: $OLD_HEAD → $NEW_HEAD"
    echo "  变更文件:"
    echo "$CHANGED" | sed 's/^/    /'
fi
echo ""

# ---- Step 2: 检测变更模块 ----
echo "[2/4] 检测变更模块..."

NEED_API=false
NEED_WEB=false
NEED_NGINX=false
NEED_COMPOSE=false

if echo "$CHANGED" | grep -qE "^(apps/api/|packages/|requirements\.txt|Dockerfile\.ecs)"; then
    NEED_API=true
    echo "  📦 后端代码变更 → 需重建 API + Worker"
fi

if echo "$CHANGED" | grep -qE "^(apps/web/|Dockerfile\.web\.ecs)"; then
    NEED_WEB=true
    echo "  📦 前端代码变更 → 需重建 Web"
fi

if echo "$CHANGED" | grep -qE "^deploy/nginx/"; then
    NEED_NGINX=true
    echo "  📦 Nginx 配置变更 → 需重载 Nginx"
fi

if echo "$CHANGED" | grep -qE "^(docker-compose\.prod\.yml|\.env\.ecs)"; then
    NEED_COMPOSE=true
    echo "  📦 Compose/环境变量变更 → 需重启全部服务"
fi

if [ "$NEED_API" = false ] && [ "$NEED_WEB" = false ] && [ "$NEED_NGINX" = false ] && [ "$NEED_COMPOSE" = false ]; then
    echo "  ⏭  无需重建任何服务（变更仅涉及文档/脚本/测试等）"
    echo ""
    echo "========================================="
    echo "  ✅ 部署完成（无服务变更）"
    echo "========================================="
    exit 0
fi
echo ""

# ---- Step 2.5: 磁盘/内存预检（防止构建打满磁盘或 OOM） ----
DISK_PCT=$(df --output=pcent / 2>/dev/null | tail -1 | tr -d ' %' || df -k / | tail -1 | awk '{gsub("%","",$5); print $5}')
if [ "$DISK_PCT" -ge 80 ] 2>/dev/null; then
    echo "[2.5/4] ⚠️  磁盘占用已达 ${DISK_PCT}%，构建前先清理..."
    bash deploy/cleanup.sh
    echo ""
fi

if { [ "$NEED_WEB" = true ] || [ "$NEED_API" = true ]; } && command -v free >/dev/null 2>&1; then
    SWAP_MB=$(free -m | awk '/^Swap:/{print $2}')
    if [ "${SWAP_MB:-0}" -lt 1024 ] 2>/dev/null; then
        echo "  ⚠️  2GiB 内存且 swap 不足，Next.js/字体子集化构建可能 OOM，建议先执行:"
        echo "     sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
        echo ""
    fi
fi

# ---- Step 3: 执行重建 ----
echo "[3/4] 执行重建..."

if [ "$NEED_COMPOSE" = true ]; then
    echo "  🔄 重启全部服务..."
    docker compose -f docker-compose.prod.yml up -d --build
elif [ "$NEED_API" = true ] && [ "$NEED_WEB" = true ]; then
    echo "  🔄 重建 API + Worker + Web..."
    docker compose -f docker-compose.prod.yml up -d --build api worker
    WEB_API_URL=http://api:8000 docker compose -f docker-compose.prod.yml up -d --build web
elif [ "$NEED_API" = true ]; then
    echo "  🔄 重建 API + Worker..."
    docker compose -f docker-compose.prod.yml up -d --build api worker
elif [ "$NEED_WEB" = true ]; then
    echo "  🔄 重建 Web..."
    WEB_API_URL=http://api:8000 docker compose -f docker-compose.prod.yml up -d --build web
fi

if [ "$NEED_NGINX" = true ]; then
    echo "  🔄 重载 Nginx..."
    bash deploy/setup-nginx.sh ip
fi
echo ""

# ---- Step 4: 验证 ----
echo "[4/4] 验证服务状态..."
sleep 2

echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "shunyishang|NAMES"

echo ""
# 健康检查
API_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
WEB_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null || echo "000")
NGX_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")

echo "  后端 /health:       $API_OK"
echo "  前端 /:             $WEB_OK"
echo "  Nginx → 后端:       $NGX_OK"
echo ""

if [ "$API_OK" = "200" ] && [ "$NGX_OK" = "200" ]; then
    echo "========================================="
    echo "  ✅ 部署完成，所有服务正常"
    echo "========================================="
else
    echo "========================================="
    echo "  ⚠️  部署完成，但部分服务异常，请检查日志:"
    echo "      docker logs shunyishang-api --tail 20"
    echo "      docker logs shunyishang-web --tail 20"
    echo "========================================="
fi

# ---- Step 5: 构建后清理（--build 会产生悬空镜像与构建缓存） ----
DISK_PCT=$(df --output=pcent / 2>/dev/null | tail -1 | tr -d ' %' || df -k / | tail -1 | awk '{gsub("%","",$5); print $5}')
if [ "$DISK_PCT" -ge 80 ] 2>/dev/null; then
    echo ""
    echo "[5/5] 磁盘占用 ${DISK_PCT}%，执行构建后清理..."
    bash deploy/cleanup.sh
fi
