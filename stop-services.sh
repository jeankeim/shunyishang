#!/bin/bash

# 顺衣尚 - 服务停止脚本
# 用法: ./stop-services.sh

echo "🛑 正在停止顺衣尚服务..."
echo ""

# 停止前端 (端口 3000)
PID_3000=$(lsof -ti:3000 2>/dev/null)
if [ -n "$PID_3000" ]; then
    echo "  停止前端服务 (端口 3000, PID: $PID_3000)..."
    kill -9 $PID_3000 2>/dev/null
    echo "  ✓ 前端已停止"
else
    echo "  ℹ 前端服务未运行"
fi

# 停止后端 (端口 8000)
PID_8000=$(lsof -ti:8000 2>/dev/null)
if [ -n "$PID_8000" ]; then
    echo "  停止后端服务 (端口 8000, PID: $PID_8000)..."
    kill -9 $PID_8000 2>/dev/null
    echo "  ✓ 后端已停止"
else
    echo "  ℹ 后端服务未运行"
fi

echo ""
echo "✅ 所有服务已停止"
