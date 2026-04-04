#!/bin/bash

# 顺衣尚 - 服务重启脚本
# 用法: ./restart-services.sh

# set -e  # 禁用，避免非关键错误导致脚本退出

echo "🔄 正在重启顺衣尚服务..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="/Users/mingyang/Desktop/shunyishang"
cd "$PROJECT_DIR"

# ============================================
# 1. 停止现有服务并释放端口
# ============================================
echo "📍 步骤 1: 停止现有服务..."

# 停止端口 3000 (前端)
PID_3000=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$PID_3000" ]; then
    echo "  停止前端服务 (端口 3000, PID: $PID_3000)..."
    kill -9 $PID_3000 2>/dev/null || true
    sleep 1
fi

# 停止端口 8000 (后端)
PID_8000=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$PID_8000" ]; then
    echo "  停止后端服务 (端口 8000, PID: $PID_8000)..."
    kill -9 $PID_8000 2>/dev/null || true
    sleep 1
fi

echo -e "${GREEN}  ✓ 现有服务已停止${NC}"
echo ""

# ============================================
# 2. 启动数据库 (Docker)
# ============================================
echo "📍 步骤 2: 检查数据库服务..."

if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠ Docker 未运行，正在启动 Docker Desktop...${NC}"
    open -a Docker
    sleep 15
fi

# 检查数据库容器是否运行
DB_RUNNING=$(docker ps --filter "name=wuxing-db" --format "{{.Names}}" 2>/dev/null)
if [ -z "$DB_RUNNING" ]; then
    echo "  启动数据库容器..."
    docker compose up -d db
    sleep 5
else
    echo "  数据库容器已在运行"
fi

# 等待数据库健康检查
for i in {1..30}; do
    if docker ps --filter "name=wuxing-db" --filter "health=healthy" --format "{{.Names}}" | grep -q "wuxing-db"; then
        echo -e "${GREEN}  ✓ 数据库服务正常${NC}"
        break
    fi
    echo "  等待数据库就绪... ($i/30)"
    sleep 2
done
echo ""

# ============================================
# 3. 启动后端服务
# ============================================
echo "📍 步骤 3: 启动后端服务 (FastAPI)..."

# 激活虚拟环境并启动后端
cd "$PROJECT_DIR"
source .venv/bin/activate

# 确保日志目录存在
mkdir -p "$PROJECT_DIR/logs"

# 使用 nohup 在后台启动，输出到日志文件
nohup python3 -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &

# 等待后端启动
for i in {1..60}; do
    if curl -s http://localhost:8000/docs >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ 后端服务已启动: http://localhost:8000${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}  ✗ 后端服务启动超时，请检查 logs/backend.log${NC}"
        exit 1
    fi
    echo "  等待后端就绪... ($i/60)"
    sleep 2
done
echo ""

# ============================================
# 4. 启动前端服务
# ============================================
echo "📍 步骤 4: 启动前端服务 (Next.js)..."

# 确保日志目录存在
mkdir -p "$PROJECT_DIR/logs"

cd "$PROJECT_DIR/apps/web"

# 使用 nohup 在后台启动
nohup npm run dev > "$PROJECT_DIR/logs/frontend.log" 2>&1 &

# 等待前端启动
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ 前端服务已启动: http://localhost:3000${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}  ✗ 前端服务启动超时，请检查 logs/frontend.log${NC}"
        exit 1
    fi
    echo "  等待前端就绪... ($i/30)"
    sleep 2
done
echo ""

# ============================================
# 5. 显示服务状态
# ============================================
echo "=========================================="
echo -e "${GREEN}🎉 所有服务启动成功！${NC}"
echo "=========================================="
echo ""
echo "📊 服务状态:"
echo "  🗄️  数据库 (PostgreSQL):  localhost:5432"
echo "  ⚙️  后端 (FastAPI):       http://localhost:8000"
echo "  🌐 前端 (Next.js):        http://localhost:3000"
echo ""
echo "📚 常用链接:"
echo "  • API 文档 (Swagger):     http://localhost:8000/docs"
echo "  • 前端应用:               http://localhost:3000"
echo ""
echo "📝 日志文件:"
echo "  • 后端日志: $PROJECT_DIR/logs/backend.log"
echo "  • 前端日志: $PROJECT_DIR/logs/frontend.log"
echo ""
echo "🛑 停止服务:"
echo "  ./stop-services.sh"
echo ""
