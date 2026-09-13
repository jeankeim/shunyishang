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
# 5a) 悬空镜像：每次构建都会多一份，留着会让 docker images 越来越难读。
#     Docker 25 的 image prune 不支持 --keep-storage，改用 until 过滤：只清 7 天前的，
#     近期部署的镜像留着，需要时 docker tag 回去就是最快的回滚路径。
#     注：这一步不是为了腾磁盘。实测清掉 50 个悬空镜像后 df -h 一格未动（reclaimed 0B）——
#     它们的 blob 同时被 5b 的构建缓存引用着，删掉镜像元数据并不释放物理空间。
# 5b) 构建缓存才是磁盘真正的大头，必须设上限。
#     dockerd 内嵌 BuildKit 与镜像层共用同一个 overlay2 store：实测 overlay2 17.28GB 里
#     有 148 个层目录只被 layerdb 注册、不被任何镜像/容器引用，物理 11.94GB 全是缓存。
#     它只增不减 —— 每部署一次就给每个 COPY 步骤新留一条记录（实测累积到
#     [runtime 7/8] COPY 38 条、runner [4/7]~[7/7] 各 16 条），20 天账面涨到 13.91GB。
#     选 --keep-storage 而不是 --filter until=：前者按最近使用保留，不涉及
#     「until 究竟看创建还是看使用时间」这个口径争议（buildx du 只给人话字符串）。
#     6GB 的依据：近两周用过的链账面约 5.76GB，被砍的是 14 天以外的历史产物副本。
#     实测 keep-storage 6GB：199 条/13.91GB -> 111 条/6.44GB，df 26G->19G（69%->49%），
#     当天构建链与基础镜像的 pulled from 记录都保留，下次部署仍命中缓存。
#     前提：python:3.11-slim 与 node:20-alpine 已 docker pull 进本地镜像库，即使缓存
#     被过度回收也不依赖镜像站重新拉取（这两个基础镜像本地镜像库里原本没有）。
# 两条清理都带 || 兜底：脚本开头是 set -euo pipefail，若不兜住，prune 一旦失败会在
# 健康检查已通过之后把整次部署误报成失败。
if [ "$NEED_API" = true ] || [ "$NEED_WEB" = true ] || [ "$NEED_COMPOSE" = true ]; then
    echo ""
    echo "[5/5] 清理 7 天前的悬空镜像 + 构建缓存收敛到 6GB 上限..."
    docker image prune -f --filter until=168h 2>&1 | tail -1 \
        || echo "      悬空镜像清理失败（忽略，不影响本次部署）"
    docker builder prune -f --keep-storage 6GB 2>&1 | tail -1 \
        || echo "      构建缓存收敛失败（忽略，磁盘仍会由下方 80% 阈值兜底）"
fi

# 兜底路径留完整清理：cleanup.sh 里的 builder prune 是无下限全清，只在磁盘真吃紧时
# 才值得付出「下次构建冷启动」的代价。有了上面 6GB 上限，正常情况下不该再走到这里。
DISK_PCT=$(df --output=pcent / 2>/dev/null | tail -1 | tr -d ' %' || df -k / | tail -1 | awk '{gsub("%","",$5); print $5}')
if [ "$DISK_PCT" -ge 80 ] 2>/dev/null; then
    echo ""
    echo "[5/5+] 磁盘占用 ${DISK_PCT}%，执行完整清理（含构建缓存）..."
    bash deploy/cleanup.sh
fi
