# Week 6 - Task 02: Docker Compose 生产配置

## 任务概述
创建生产级 Docker Compose 配置，包括多阶段构建、镜像优化、安全加固，确保系统可以在生产环境稳定运行。

## 背景与目标
当前项目使用开发环境的 Docker 配置，需要为生产环境创建专门的配置，包括更小的镜像体积、更高的安全性、更好的性能。

## 技术要求

### Docker 多阶段构建
- 构建阶段与运行阶段分离
- 最小化最终镜像体积
- 移除构建依赖

### 安全加固
- 非 root 用户运行
- 只读文件系统
- 安全扫描
- 密钥管理

### 生产优化
- 健康检查
- 资源限制
- 日志管理
- 重启策略

## 实现步骤

### 1. 后端 Dockerfile

#### 1.1 多阶段构建
文件: `apps/api/Dockerfile.prod`

```dockerfile
# 构建阶段
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 运行阶段
FROM python:3.11-slim as runtime

# 创建非 root 用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# 从构建阶段复制依赖
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1.2 镜像优化
- 使用 python:3.11-slim 基础镜像
- 多阶段构建分离构建依赖
- 清理 apt 缓存
- 使用 .dockerignore 排除无关文件

### 2. 前端 Dockerfile

#### 2.1 多阶段构建
文件: `apps/web/Dockerfile.prod`

```dockerfile
# 构建阶段
FROM node:18-alpine as builder

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制源码并构建
COPY . .
RUN npm run build

# 运行阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

#### 2.2 Nginx 配置
文件: `apps/web/nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # 缓存静态资源
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Docker Compose 生产配置

文件: `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: ankane/pgvector:v0.5.1
    container_name: wuxing_postgres_prod
    environment:
      POSTGRES_USER: ${DB_USER:-wuxing}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      POSTGRES_DB: ${DB_NAME:-wuxing}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-wuxing}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: wuxing_redis_prod
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  # 后端 API
  api:
    build:
      context: .
      dockerfile: apps/api/Dockerfile.prod
    container_name: wuxing_api_prod
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${DB_USER:-wuxing}:${DB_PASSWORD:-changeme}@postgres:5432/${DB_NAME:-wuxing}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QWEATHER_API_KEY=${QWEATHER_API_KEY}
    volumes:
      - ./data/uploads:/app/data/uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 3G
        reservations:
          cpus: '1'
          memory: 1G

  # 前端 Web
  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile.prod
    container_name: wuxing_web_prod
    ports:
      - "80:80"
    depends_on:
      - api
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

volumes:
  postgres_data:
  redis_data:
```

### 4. 环境变量配置

文件: `.env.prod.example`

```bash
# 数据库配置
DB_USER=wuxing
DB_PASSWORD=your_secure_password_here
DB_NAME=wuxing

# JWT 密钥
SECRET_KEY=your_jwt_secret_key_here

# AI API 密钥
OPENAI_API_KEY=your_openai_api_key

# 天气 API 密钥
QWEATHER_API_KEY=your_qweather_api_key

# 高德地图 API 密钥
AMAP_API_KEY=your_amap_api_key
```

### 5. 部署脚本

文件: `scripts/deploy.sh`

```bash
#!/bin/bash
set -e

echo "🚀 开始部署五行穿搭推荐系统..."

# 检查环境变量
if [ ! -f .env.prod ]; then
    echo "❌ 错误: .env.prod 文件不存在"
    exit 1
fi

# 加载环境变量
export $(cat .env.prod | grep -v '^#' | xargs)

# 拉取最新代码
git pull origin main

# 构建镜像
echo "📦 构建 Docker 镜像..."
docker-compose -f docker-compose.prod.yml build

# 停止旧服务
echo "🛑 停止旧服务..."
docker-compose -f docker-compose.prod.yml down

# 启动新服务
echo "▶️ 启动新服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 健康检查
echo "🏥 健康检查..."
docker-compose -f docker-compose.prod.yml ps

echo "✅ 部署完成！"
echo "🌐 访问地址: http://localhost"
```

## 验收标准

### 镜像标准
```
后端镜像大小: < 500MB
前端镜像大小: < 100MB
构建时间: < 5分钟
```

### 安全标准
- [ ] 非 root 用户运行
- [ ] 无构建依赖残留
- [ ] 敏感信息通过环境变量注入
- [ ] 镜像安全扫描通过

### 功能标准
- [ ] 服务正常启动
- [ ] 健康检查通过
- [ ] 日志正常输出
- [ ] 重启策略生效

## 交付物

### Docker 文件
- `apps/api/Dockerfile.prod` - 后端生产镜像
- `apps/web/Dockerfile.prod` - 前端生产镜像
- `apps/web/nginx.conf` - Nginx 配置
- `docker-compose.prod.yml` - 生产编排
- `.env.prod.example` - 环境变量示例
- `.dockerignore` - Docker 忽略文件

### 脚本文件
- `scripts/deploy.sh` - 部署脚本
- `scripts/backup.sh` - 备份脚本
- `scripts/health_check.sh` - 健康检查脚本

### 文档
- `docs/DEPLOYMENT.md` - 部署文档
- `docs/DOCKER_GUIDE.md` - Docker 使用指南

## 预估工时
- Dockerfile 编写: 3小时
- Docker Compose 配置: 2小时
- Nginx 配置: 2小时
- 部署脚本: 2小时
- 测试验证: 2小时
- **总计: 11小时**

## 依赖任务
- Week 1-5: 所有功能开发完成
- Week 6-01: 性能调优（优化后构建）

## 注意事项
1. 生产环境密钥必须强密码
2. 定期更新基础镜像版本
3. 配置日志轮转防止磁盘满
4. 数据库数据需要定期备份
