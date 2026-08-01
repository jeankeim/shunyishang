#!/bin/bash
# ============================================================
# Nginx 一键部署脚本
# 用法: bash deploy/setup-nginx.sh [ip|domain]
#   ip     - 备案前 IP 模式（默认）
#   domain - 备案后域名模式（需先执行 cutover.sh）
#
# 功能:
#   1. 注释掉 /etc/nginx/nginx.conf 中的默认 server 块（避免 default_server 冲突）
#   2. 复制对应的 conf 到 /etc/nginx/conf.d/
#   3. nginx -t 验证 + reload
# ============================================================

set -euo pipefail

MODE="${1:-ip}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NGINX_CONF="/etc/nginx/nginx.conf"
CONF_D="/etc/nginx/conf.d"

echo "=== Nginx 部署脚本 (模式: $MODE) ==="

# ---- Step 1: 注释掉 nginx.conf 中的默认 server 块 ----
echo "[1/3] 检查 nginx.conf 默认 server 块..."

if grep -q '^\s*server\s*{' "$NGINX_CONF" 2>/dev/null; then
    # 用 sed 把 http {} 块内的 server {} 整段注释掉
    # 策略：在 server { 到对应的 } 之间每行加 #
    # 简单做法：备份后用 awk 处理
    cp "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%s)"

    awk '
    /^(\s*)server\s*\{/ { in_server=1; brace_count=0 }
    in_server {
        gsub(/^{/, "{")
        for(i=1; i<=length($0); i++) {
            c = substr($0,i,1)
            if(c == "{") brace_count++
            if(c == "}") brace_count--
        }
        print "# [setup-nginx.sh 已注释] " $0
        if(brace_count <= 0 && index($0, "}") > 0) { in_server=0 }
        next
    }
    { print }
    ' "$NGINX_CONF" > "${NGINX_CONF}.tmp" && mv "${NGINX_CONF}.tmp" "$NGINX_CONF"

    echo "  ✅ 已注释 nginx.conf 中的默认 server 块（原文件备份为 .bak.*）"
else
    echo "  ⏭  nginx.conf 中无 server 块，跳过"
fi

# ---- Step 2: 复制配置文件 ----
echo "[2/3] 部署 Nginx 配置..."

# 先清理旧的
rm -f "$CONF_D"/shunyishang-ip.conf "$CONF_D"/shunyishang.conf 2>/dev/null || true

if [ "$MODE" = "ip" ]; then
    cp "$SCRIPT_DIR/nginx/shunyishang-ip.conf" "$CONF_D/shunyishang-ip.conf"
    echo "  ✅ 已部署 IP 模式配置: $CONF_D/shunyishang-ip.conf"
elif [ "$MODE" = "domain" ]; then
    if [ ! -f "$CONF_D/shunyishang.conf" ]; then
        echo "  ❌ 域名模式需先执行 cutover.sh 生成配置"
        exit 1
    fi
    echo "  ✅ 域名模式配置已存在"
else
    echo "  ❌ 未知模式: $MODE (可选: ip, domain)"
    exit 1
fi

# ---- Step 3: 验证并重载 ----
echo "[3/3] 验证并重载 Nginx..."
if nginx -t 2>&1; then
    systemctl reload nginx
    echo "  ✅ Nginx 重载成功"
else
    echo "  ❌ nginx -t 失败，请检查配置"
    exit 1
fi

# ---- 验证 ----
echo ""
echo "=== 验证 ==="
sleep 1
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ /health → 200 (Nginx → 后端 通路正常)"
else
    echo "⚠️  /health → $HTTP_CODE (后端可能未启动，但 Nginx 配置已生效)"
fi

echo ""
echo "=== 完成 ==="
