# 🚀 五行AI衣橱 - 生产部署指南

## 📐 部署架构

```
用户浏览器
    ↓ HTTPS
Vercel (前端 - Next.js 14 SSR)
    ↓ API调用
Zeabur (后端 - FastAPI + Gunicorn)
    ↓
    ├─ Zeabur PostgreSQL (数据库 + pgvector)
    ├─ Upstash Redis (缓存层)
    └─ Cloudflare R2 (图片对象存储)
```

---

## 📋 部署清单

### Phase 1: 基础设施创建（1-2 小时）

#### 1.1 Zeabur 账号注册

1. 访问 https://zeabur.com
2. 使用 GitHub 账号登录
3. 创建新项目 `wuxing-wardrobe`

---

#### 1.2 Zeabur PostgreSQL 数据库

**创建步骤**：

1. 在 Zeabur 项目页面，点击 "Add Service"
2. 选择 "Database" → "PostgreSQL"
3. 等待数据库初始化（约 1 分钟）
4. 点击数据库服务，进入 "Connection" 标签
5. 复制连接信息：
   - Host: `163.7.19.105`
   - Port: `30395`
   - Database: `zeabur`
   - Username: `root`
   - Password: `23iMH7ud61owa0bKpePLq98UCDgX45TY`

**获取完整连接字符串**：
```
postgresql://root:23iMH7ud61owa0bKpePLq98UCDgX45TY@163.7.19.105:30395/zeabur
```

**初始化数据库**：

1. 使用本地 psql 或 DBeaver 连接数据库
2. 执行初始化脚本：
```bash
psql "postgresql://root:23iMH7ud61owa0bKpePLq98UCDgX45TY@163.7.19.105:30395/zeabur" -f scripts/init_db.sql
```

或者在 Zeabur 的 "Console" 标签中直接粘贴执行 `scripts/init_db.sql` 内容。

---

#### 1.3 Cloudflare R2 对象存储

**创建步骤**：

1. 登录 https://dash.cloudflare.com
2. 左侧菜单选择 "R2 Storage"
3. 点击 "Create Bucket"
4. Bucket 名称：`wuxing-wardrobe`
5. 点击创建

**创建 API Token**：

1. 在 R2 页面，点击 "Manage R2 API Tokens"
2. 点击 "Create API Token"
3. 权限选择：
   - Object Read ✓
   - Object Write ✓
4. 设置 TTL：`Never Expires`（或自定义）
5. 点击 "Create API Token"
6. **立即保存以下信息**（只显示一次）：
   - Access Key ID: `171aa90ebdccbefcf326674d996690b5`
   - Secret Access Key: `9602c58b441ceae1ab3bab12c431f52129389b0fef47e4c6f682ca68309c6d70`

**获取 Account ID**：

1. 在 R2 页面右上角，复制 Account ID
Account ID : `e79f49e5f684d41d722a3dfe3d42a1af`
2. 格式：`32位十六进制字符串`

**配置公共访问**：

1. 在 Bucket 设置中，找到 "Public Access"
2. 启用公共访问（或通过 Workers 绑定域名）
3. 获取公共 URL：`https://pub-851399ad134d447ea68cd62dbadd90a4.r2.dev`

---

#### 1.4 Upstash Redis

**创建步骤**：

1. 访问 https://upstash.com
2. 使用 GitHub 登录
3. 点击 "Create Database"
4. 数据库名称：`wuxing-cache`
5. 区域选择：
   - 如果用户主要在亚洲：选择 `Asia Southeast (Singapore)`
   - 如果用户主要在北美：选择 `US East (Virginia)`
6. 点击 "Create"

**获取连接信息**：

1. 进入数据库详情页
2. 找到 "REST API" 部分
3. 复制以下信息：
   - UPSTASH_REDIS_REST_URL: `https://free-seagull-72571.upstash.io`
   - UPSTASH_REDIS_REST_TOKEN: `gQAAAAAAARt7AAIncDFiZWQxYTk3YzI2NWI0ZTczOTVlMTQzYWJhZTJmZjNiZHAxNzI1NzE`

---

### Phase 2: 代码准备（30 分钟）

#### 2.1 更新项目配置

项目已包含以下新文件（已为您创建）：

- ✅ `.dockerignore` - Docker 忽略规则
- ✅ `apps/api/Dockerfile` - 后端 Docker 配置
- ✅ `apps/api/services/r2_storage.py` - R2 存储服务
- ✅ `apps/api/services/upstash_redis.py` - Upstash Redis 服务
- ✅ `.env.production.example` - 生产环境变量模板
- ✅ `apps/web/.env.production.example` - 前端环境变量模板

**需要修改的文件**：

1. 复制环境变量模板：
```bash
cp .env.production.example .env.production
```

2. 编辑 `.env.production`，填入您的配置（见 Phase 3）

---

### Phase 3: 部署后端到 Zeabur（1 小时）

#### 3.1 连接 GitHub 仓库

1. 确保代码已推送到 GitHub
2. 在 Zeabur 项目页面，点击 "Add Service"
3. 选择 "Git Repository"
4. 选择您的 `shunyishang` 仓库

#### 3.2 配置环境变量

在 Zeabur 服务的 "Environment" 标签中，添加以下变量：

```bash
# === 数据库配置 ===
DATABASE_URL=postgresql://root:YOUR_PASSWORD@YOUR_HOST:5432/zeabur
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# === AI API ===
DASHSCOPE_API_KEY=sk-YOUR_KEY
QWEN_MODEL=qwen-plus

# === Embedding ===
EMBEDDING_MODEL=BGE-M3
EMBEDDING_DIMENSION=1024

# === 应用配置 ===
APP_ENV=production
APP_DEBUG=false
APP_PORT=8000
CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN.vercel.app

# === JWT (生成强随机密钥) ===
# Python 生成命令: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=YOUR_STRONG_RANDOM_KEY

# === 天气 API ===
WEATHER_API_KEY=YOUR_QWEATHER_KEY
AMAP_API_KEY=YOUR_AMAP_KEY

# === R2 对象存储 ===
R2_ACCOUNT_ID=YOUR_ACCOUNT_ID
R2_ACCESS_KEY_ID=YOUR_ACCESS_KEY
R2_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
R2_BUCKET_NAME=wuxing-wardrobe
R2_PUBLIC_URL=https://pub-XXX.r2.dev

# === Upstash Redis ===
UPSTASH_REDIS_REST_URL=https://YOUR_DB.upstash.io
UPSTASH_REDIS_REST_TOKEN=YOUR_TOKEN
```

#### 3.3 配置构建设置

在 Zeabur 服务的 "Settings" 标签中：

1. **Build Command**: 留空（自动检测 Dockerfile）
2. **Start Command**: 留空（使用 Dockerfile 中的 CMD）
3. **Root Directory**: 留空（项目根目录）
4. **Dockerfile Path**: `apps/api/Dockerfile`

#### 3.4 部署

1. 点击 "Deploy"
2. 等待构建完成（首次约 3-5 分钟）
3. 查看日志确认服务启动成功
4. 访问健康检查：`https://YOUR_ZEABUR_DOMAIN.zeabur.app/health`

应该看到：
```json
{
  "status": "ok",
  "db": "connected",
  "env": "production"
}
```

#### 3.5 配置域名（可选）

1. 在 Zeabur 服务页面，点击 "Domains"
2. 添加自定义域名（如 `api.wuxing-wardrobe.com`）
3. 按照提示配置 DNS CNAME 记录

---

### Phase 4: 部署前端到 Vercel（30 分钟）

#### 4.1 创建 Vercel 项目

1. 访问 https://vercel.com
2. 点击 "Add New..." → "Project"
3. 选择 `shunyishang` 仓库
4. 点击 "Import"

#### 4.2 配置构建设置

1. **Framework Preset**: Next.js
2. **Root Directory**: `apps/web`
3. **Build Command**: `next build`
4. **Output Directory**: `.next`

#### 4.3 配置环境变量

在 Vercel 项目设置 → "Environment Variables" 中添加：

```bash
# 生产环境
NEXT_PUBLIC_API_URL=https://YOUR_ZEABUR_DOMAIN.zeabur.app
NEXT_PUBLIC_R2_PUBLIC_URL=https://pub-XXX.r2.dev
```

**重要**：确保勾选 "Production" 和 "Preview" 环境。

#### 4.4 部署

1. 点击 "Deploy"
2. 等待构建完成（约 2-3 分钟）
3. 访问部署的 URL

#### 4.5 配置自定义域名（可选）

1. 在 Vercel 项目设置 → "Domains"
2. 添加您的域名（如 `wuxing-wardrobe.com`）
3. 按照提示配置 DNS A 记录或 CNAME

---

### Phase 5: 验证与测试（1 小时）

#### 5.1 功能验证清单

按顺序测试以下功能：

- [ ] **前端访问**
  - [ ] 可以打开 Vercel 部署的 URL
  - [ ] 页面正常渲染
  - [ ] 无控制台错误

- [ ] **用户认证**
  - [ ] 注册新用户
  - [ ] 登录成功
  - [ ] JWT Token 正常

- [ ] **八字计算**
  - [ ] 输入出生日期
  - [ ] 返回五行分析
  - [ ] Redis 缓存生效（第二次请求更快）

- [ ] **天气查询**
  - [ ] 输入城市名称
  - [ ] 返回天气数据
  - [ ] Redis 缓存生效（15 分钟内不重复请求）

- [ ] **衣物上传**
  - [ ] 上传衣物图片
  - [ ] 图片存储到 R2（非本地）
  - [ ] 返回 R2 公共 URL
  - [ ] 可以在浏览器访问该 URL

- [ ] **衣物推荐**
  - [ ] 获取推荐结果
  - [ ] 包含五行匹配
  - [ ] 图片从 R2 加载

- [ ] **海报生成**
  - [ ] 生成简约东方模板
  - [ ] 生成五行国潮模板
  - [ ] 生成社交卡片模板
  - [ ] 海报中的图片来自 R2

#### 5.2 性能验证

- [ ] 首屏加载 < 3 秒
- [ ] API 响应 < 1 秒（缓存命中）
- [ ] 图片加载使用 CDN 加速

#### 5.3 安全验证

- [ ] 所有 API 使用 HTTPS
- [ ] CORS 限制为 Vercel 域名
- [ ] JWT 密钥为强随机字符串
- [ ] 数据库连接使用 SSL
- [ ] R2 Bucket 不暴露敏感信息

---

## 🔧 故障排查

### 问题 1: 后端健康检查失败

**症状**：访问 `/health` 返回 503

**排查步骤**：
1. 查看 Zeabur 日志
2. 检查 `DATABASE_URL` 是否正确
3. 确认数据库已初始化（执行了 `init_db.sql`）
4. 测试数据库连接：
```bash
psql "YOUR_DATABASE_URL" -c "SELECT 1"
```

---

### 问题 2: 图片上传失败

**症状**：上传衣物图片报错

**排查步骤**：
1. 检查 R2 环境变量是否正确
2. 测试 R2 连接：
```python
python3 -c "
from apps.api.services.r2_storage import get_r2_service
r2 = get_r2_service()
print('R2 客户端:', r2.client is not None)
"
```
3. 查看 Zeabur 日志中的 R2 错误信息
4. 确认 Bucket 权限为 Object Read & Write

---

### 问题 3: 前端 API 调用 403/404

**症状**：前端请求后端 API 失败

**排查步骤**：
1. 检查 `NEXT_PUBLIC_API_URL` 是否正确
2. 确认 CORS_ORIGINS 包含 Vercel 域名
3. 浏览器开发者工具查看网络请求
4. 检查 Zeabur 日志中的 CORS 错误

---

### 问题 4: Redis 缓存不生效

**症状**：每次请求都查询数据库

**排查步骤**：
1. 检查 Upstash 环境变量
2. 测试 Upstash 连接：
```bash
curl -X POST https://YOUR_DB.upstash.io/pipeline \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[["SET", "test", "ok"]]'
```
3. 查看后端日志中的 Upstash 错误

---

## 📊 监控与维护

### 日志查看

- **Zeabur**: 服务页面 → "Logs" 标签
- **Vercel**: 项目页面 → "Deployments" → 点击部署 → "Logs"
- **Upstash**: 数据库页面 → "Data" 标签查看键值
- **R2**: Bucket 页面 → "Objects" 查看文件列表

### 数据库备份

Zeabur PostgreSQL 自动备份：
1. 进入数据库服务
2. 点击 "Backups" 标签
3. 可以手动创建备份或查看自动备份

### 性能监控

- **Zeabur**: 服务页面 → "Metrics" 查看 CPU/内存
- **Vercel**: 项目页面 → "Analytics" 查看访问量
- **Upstash**: 数据库页面 → "Metrics" 查看请求数

---

## 🎯 后续优化

### 短期优化（1-2 周）

1. **CDN 加速**
   - 配置 R2 Custom Domain + Cloudflare CDN
   - 启用自动图片压缩

2. **数据库优化**
   - 添加 pgvector 索引（HNSW）
   - 配置连接池（PgBouncer）

3. **缓存策略**
   - 八字结果缓存 24 小时
   - 天气数据缓存 15 分钟
   - 推荐结果缓存 1 小时

### 中期优化（1-2 月）

1. **监控告警**
   - 集成 Sentry 错误追踪
   - 配置 Zeabur 告警规则

2. **CI/CD**
   - 配置 GitHub Actions 自动部署
   - 添加自动化测试

3. **数据库扩展**
   - 读写分离
   - 分库分表（如果用户量增长）

### 长期优化（3-6 月）

1. **微服务拆分**
   - 海报生成独立服务
   - 图片处理独立服务

2. **队列系统**
   - 引入 Celery + Redis 处理异步任务
   - 海报生成异步化

3. **多区域部署**
   - 前端 Vercel 全球 CDN
   - 后端多区域部署

---

## 💰 成本估算

### 免费额度

| 服务 | 免费额度 | 超出后价格 |
|------|---------|-----------|
| Vercel | 100GB 带宽/月 | $20/月起 |
| Zeabur | $5 信用额度/月 | $5/月起 |
| Zeabur DB | 1GB 存储 | $3/月起 |
| Upstash Redis | 10,000 命令/天 | $0.20/百万命令 |
| Cloudflare R2 | 10GB 存储 + 100万次读 | $0.015/GB 存储 |

### 个人项目月费预估

- **轻度使用**（< 100 用户）：$0/月（全免费）
- **中度使用**（100-1000 用户）：$5-10/月
- **重度使用**（> 1000 用户）：$20-50/月

---

## 📞 获取帮助

- **Zeabur 文档**: https://zeabur.com/docs
- **Vercel 文档**: https://vercel.com/docs
- **Upstash 文档**: https://upstash.com/docs
- **Cloudflare R2 文档**: https://developers.cloudflare.com/r2/
- **项目问题**: 查看本项目 `logs/` 目录

---

**祝您部署顺利！** 🎉
