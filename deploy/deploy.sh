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

# Web 单独处理，不要写成 `up -d --build web`：compose 的 --build 会连带构建 depends_on
# 声明的服务（web → api），所有层即便全 CACHED 也会导出一份新的 api 镜像，
# 镜像 ID 一变 compose 就重建 api 容器 —— 改一行前端文案却让后端冷启动一次。
# 拆成 build（只构建 web 自身）+ up --no-deps（只收敛 web 容器）即可避开。
# 代价：api 若已挂掉，本命令不会把它带起来 —— 那属于 Step 4 健康检查该报警的情况。
rebuild_web() {
    echo "  🔄 重建 Web（不连带重启 api）..."
    WEB_API_URL=http://api:8000 docker compose -f docker-compose.prod.yml build web
    WEB_API_URL=http://api:8000 docker compose -f docker-compose.prod.yml up -d --no-deps web
}

if [ "$NEED_COMPOSE" = true ]; then
    echo "  🔄 重启全部服务..."
    docker compose -f docker-compose.prod.yml up -d --build
elif [ "$NEED_API" = true ] && [ "$NEED_WEB" = true ]; then
    echo "  🔄 重建 API + Worker..."
    docker compose -f docker-compose.prod.yml up -d --build api worker
    rebuild_web
elif [ "$NEED_API" = true ]; then
    echo "  🔄 重建 API + Worker..."
    docker compose -f docker-compose.prod.yml up -d --build api worker
elif [ "$NEED_WEB" = true ]; then
    rebuild_web
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
# Nginx 这条必须探 443：80 端口现在是 `return 301 https://$host$request_uri`，
# 探 80 永远只能拿到 301，既证明不了 nginx 活着也证明不了它能代理到后端 ——
# 而把成败判定写成「等于 200」会让脚本从 HTTPS 上线起就一直报「部分服务异常」，
# 于是下次 nginx 真出事时，它看起来和这条永久噪音完全一样。用 -k 是因为回环访问
# 拿不到匹配 CN 的证书，这里只关心链路通不通，不关心证书链（公网证书另有监控）。
API_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
WEB_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ 2>/dev/null || echo "000")
NGX_OK=$(curl -sk -o /dev/null -w "%{http_code}" https://localhost/health 2>/dev/null || echo "000")
# 80 → HTTPS 的引导只作旁证打印，不参与成败判定
HTTP_TO_HTTPS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")

echo "  后端 /health:              $API_OK"
echo "  前端 /:                    $WEB_OK"
echo "  Nginx(443) → 后端:         $NGX_OK"
echo "  Nginx(80) 引导到 HTTPS:    $HTTP_TO_HTTPS"
echo ""

echo "  api 容器启动于: $(docker inspect shunyishang-api --format '{{.State.StartedAt}}' 2>/dev/null || echo '未知')"
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

# ---- Step 5: 构建后清理 ----
# 悬空镜像每次构建都会多一份（ECS 上实测积到 52 个 / 14.7GB 可回收，是磁盘最大占用项）。
# Docker 25 的 image prune 不支持 --keep-storage，改用 until 过滤：只清 7 天前的，
# 近期部署的镜像留着，需要时 docker tag 回去就是最快的回滚路径。
if [ "$NEED_API" = true ] || [ "$NEED_WEB" = true ] || [ "$NEED_COMPOSE" = true ]; then
    echo ""
    echo "[5/5] 清理 7 天前的悬空镜像..."
    docker image prune -f --filter until=168h | tail -2
fi

# 构建缓存不在常规路径里清：它是下次构建全 CACHED 的来源，也是 2GiB 内存机器上
# Next.js 构建不 OOM 的前提。只有磁盘真吃紧时才走完整 cleanup。
DISK_PCT=$(df --output=pcent / 2>/dev/null | tail -1 | tr -d ' %' || df -k / | tail -1 | awk '{gsub("%","",$5); print $5}')
if [ "$DISK_PCT" -ge 80 ] 2>/dev/null; then
    echo ""
    echo "[5/5+] 磁盘占用 ${DISK_PCT}%，执行完整清理（含构建缓存）..."
    bash deploy/cleanup.sh
fi
