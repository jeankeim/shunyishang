# 🚀 部署快速开始检查清单

## 前置准备

- [ ] 已有 GitHub 账号并推送代码
- [ ] 已有 Cloudflare 账号
- [ ] 已有和风天气 API Key
- [ ] 已有高德地图 API Key（可选）
- [ ] 已有 DashScope API Key

---

## Phase 1: 创建基础设施（预计 1-2 小时）

### 1. Zeabur 注册
- [ ] 访问 https://zeabur.com
- [ ] 使用 GitHub 登录
- [ ] 创建项目 `wuxing-wardrobe`

### 2. Zeabur PostgreSQL
- [ ] 在项目中添加 PostgreSQL 服务
- [ ] 等待初始化完成
- [ ] 复制数据库连接信息：
  - [ ] Host: `_______________________`
  - [ ] Password: `_______________________`
- [ ] 完整连接字符串：
  ```
  DATABASE_URL=postgresql://root:PASSWORD@HOST:5432/zeabur
  ```
- [ ] 执行数据库初始化：
  ```bash
  psql "YOUR_DATABASE_URL" -f scripts/init_db.sql
  ```

### 3. Cloudflare R2
- [ ] 登录 https://dash.cloudflare.com
- [ ] 创建 Bucket：`wuxing-wardrobe`
- [ ] 创建 API Token（Object Read + Write）
- [ ] 保存以下信息：
  - [ ] Account ID: `_______________________`
  - [ ] Access Key ID: `_______________________`
  - [ ] Secret Access Key: `_______________________`
- [ ] 启用公共访问，获取 Public URL：
  - [ ] R2_PUBLIC_URL: `https://pub-_______.r2.dev`

### 4. Upstash Redis
- [ ] 访问 https://upstash.com
- [ ] 使用 GitHub 登录
- [ ] 创建数据库 `wuxing-cache`
- [ ] 选择区域：Asia Southeast (Singapore)
- [ ] 保存以下信息：
  - [ ] UPSTASH_REDIS_REST_URL: `https://_______.upstash.io`
  - [ ] UPSTASH_REDIS_REST_TOKEN: `_______________________`

---

## Phase 2: 配置环境变量（预计 15 分钟）

### 1. 生成 JWT 密钥
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
- [ ] JWT_SECRET_KEY: `_______________________`

### 2. 填写后端环境变量（Zeabur）

复制以下内容到 Zeabur Environment 标签：

```bash
# 数据库
DATABASE_URL=postgresql://root:________@________:5432/zeabur
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# AI API
DASHSCOPE_API_KEY=sk-________
QWEN_MODEL=qwen-plus

# Embedding
EMBEDDING_MODEL=BGE-M3
EMBEDDING_DIMENSION=1024

# 应用
APP_ENV=production
APP_DEBUG=false
APP_PORT=8000
CORS_ORIGINS=https://________.vercel.app

# JWT
JWT_SECRET_KEY=________

# 天气 API
WEATHER_API_KEY=________
AMAP_API_KEY=

# R2 存储
R2_ACCOUNT_ID=________
R2_ACCESS_KEY_ID=________
R2_SECRET_ACCESS_KEY=________
R2_BUCKET_NAME=wuxing-wardrobe
R2_PUBLIC_URL=https://pub-________.r2.dev

# Upstash Redis
UPSTASH_REDIS_REST_URL=https://________.upstash.io
UPSTASH_REDIS_REST_TOKEN=________
```

### 3. 填写前端环境变量（Vercel）

稍后在 Vercel 部署时填写：

```bash
NEXT_PUBLIC_API_URL=https://________.zeabur.app
NEXT_PUBLIC_R2_PUBLIC_URL=https://pub-________.r2.dev
```

---

## Phase 3: 部署后端（预计 30 分钟）

### 1. 连接 GitHub
- [ ] 在 Zeabur 添加 Git Repository
- [ ] 选择 `shunyishang` 仓库

### 2. 配置构建设置
- [ ] Dockerfile Path: `apps/api/Dockerfile`
- [ ] Root Directory: 留空

### 3. 部署
- [ ] 点击 Deploy
- [ ] 等待构建完成（3-5 分钟）
- [ ] 记录 Zeabur 域名：
  - [ ] API_URL: `https://________.zeabur.app`

### 4. 健康检查
- [ ] 访问 `https://YOUR_DOMAIN.zeabur.app/health`
- [ ] 确认返回：
  ```json
  {
    "status": "ok",
    "db": "connected",
    "env": "production"
  }
  ```

---

## Phase 4: 部署前端（预计 20 分钟）

### 1. 创建 Vercel 项目
- [ ] 访问 https://vercel.com
- [ ] Import `shunyishang` 仓库
- [ ] Root Directory: `apps/web`

### 2. 配置环境变量
- [ ] 添加 `NEXT_PUBLIC_API_URL`
- [ ] 添加 `NEXT_PUBLIC_R2_PUBLIC_URL`

### 3. 部署
- [ ] 点击 Deploy
- [ ] 等待构建完成（2-3 分钟）
- [ ] 记录 Vercel 域名：
  - [ ] FRONTEND_URL: `https://________.vercel.app`

---

## Phase 5: 更新 CORS 配置（预计 5 分钟）

### 1. 更新后端 CORS
- [ ] 回到 Zeabur Environment
- [ ] 更新 `CORS_ORIGINS` 为 Vercel 域名：
  ```
  CORS_ORIGINS=https://________.vercel.app
  ```
- [ ] 保存后自动重新部署

---

## Phase 6: 功能测试（预计 1 小时）

### 基础功能
- [ ] 打开前端 URL，页面正常显示
- [ ] 注册新用户
- [ ] 登录成功

### 核心功能
- [ ] 八字计算正常
- [ ] 天气查询正常
- [ ] 上传衣物图片（确认存储到 R2）
- [ ] 查看衣物列表（图片从 R2 加载）
- [ ] 获取推荐结果

### 高级功能
- [ ] 生成简约东方海报
- [ ] 生成五行国潮海报
- [ ] 生成社交卡片海报
- [ ] 下载海报正常

### 性能验证
- [ ] 首屏加载 < 3 秒
- [ ] 八字计算第二次请求更快（Redis 缓存）
- [ ] 天气查询 15 分钟内不重复请求（Redis 缓存）
- [ ] 图片加载快速（R2 CDN）

---

## Phase 7: 自定义域名（可选）

### 1. Vercel 域名
- [ ] 在 Vercel 添加自定义域名
- [ ] 配置 DNS CNAME 记录
- [ ] 等待 SSL 证书签发

### 2. Zeabur 域名
- [ ] 在 Zeabur 添加自定义域名
- [ ] 配置 DNS CNAME 记录
- [ ] 更新前端 `NEXT_PUBLIC_API_URL`

### 3. R2 域名
- [ ] 在 Cloudflare 配置 R2 Custom Domain
- [ ] 更新后端 `R2_PUBLIC_URL`

---

## 常见问题

### Q: 后端健康检查失败？
1. 检查 Zeabur Logs
2. 确认 `DATABASE_URL` 正确
3. 确认已执行 `init_db.sql`

### Q: 图片上传失败？
1. 检查 R2 环境变量
2. 确认 Bucket 权限
3. 查看 Zeabur Logs 中的 R2 错误

### Q: 前端 API 调用 403？
1. 确认 `NEXT_PUBLIC_API_URL` 正确
2. 确认 `CORS_ORIGINS` 包含 Vercel 域名

### Q: Redis 缓存不生效？
1. 检查 Upstash 环境变量
2. 测试 Upstash REST API 连接
3. 查看后端日志

---

## 部署完成 ✅

恭喜！您的五行AI衣橱已成功部署到生产环境！

- 前端：`https://________.vercel.app`
- 后端：`https://________.zeabur.app`
- 数据库：Zeabur PostgreSQL
- 缓存：Upstash Redis
- 存储：Cloudflare R2

**下一步**：
1. 配置监控和告警
2. 设置自动备份
3. 邀请用户测试
4. 收集反馈并迭代
