# 我的个人衣橱（原「顺衣尚」）- 五行穿搭灵感推荐系统

> 基于八字命理和五行美学的 AI 穿搭灵感推荐平台 | 生产环境运行中

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0.0-blue.svg" alt="v1.0.0">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Next.js-14.2-black.svg" alt="Next.js 14.2">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-green.svg" alt="FastAPI 0.110+">
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg" alt="PostgreSQL 15">
  <img src="https://img.shields.io/badge/pgvector-0.5-orange.svg" alt="pgvector 0.5">
  <img src="https://img.shields.io/badge/LangGraph-0.2+-purple.svg" alt="LangGraph">
</p>

<p align="center">
  <b>结合传统命理学与现代 AI 技术的智能穿搭推荐平台 · 仅供娱乐参考</b>
</p>

---

## 📊 项目状态

**核心完成度**: 100%（Week 1-16 全部功能 + V2 六周改造已完成）  
**生产环境**: 🟢 阿里云 ECS 全量运行（Docker Compose：api/worker/web/redis + Nginx HTTPS 反向代理 + 阿里云 RDS PostgreSQL + OSS 图片托管；Zeabur/Vercel 已弃用）  
**合规备案**: 浙ICP备2026060847号 · 个人备案免费版 —— 无支付功能，所有功能免费开放；PIPL 隐私合规（出生信息单独同意、PII 加密、数据导出/删除）  
**商业化功能**: 🔒 支付相关（VIP会员/品牌合作/付费报告）代码已完成，暂未接入支付  
**测试覆盖**: 前端 956 用例 | 后端 1736 用例

---

## ✨ 核心功能

### MVP 基础能力（Week 1-8）
- **八字命理分析**: 生辰八字四柱计算 + 五行强弱 + 喜用神/忌用神推断（cnlunar 专业库，大运流年校准）
- **智能穿搭推荐**: LangGraph AI Agent + pgvector 语义搜索 + 六维动态权重融合评分
- **天气感知**: 和风天气 API + 浏览器 GPS 定位 + 有效温度（瞬时/当日最高取 max）分级过滤
- **用户衣橱**: 拍照批量识别入库（LangGraph 编排 qwen-vl 视觉识别 + 五行规则分析两阶段）+ 六维智能筛选 + 闲置提醒 + 物品详情
- **分享海报**: 后端 Pillow 渲染 1080×1920 + 4 种模板（简约/五行国潮/社交卡片/宋锦国风）+ 自定义编辑
- **虚拟试衣**: Canvas 画布 + 图层管理 + 拖拽交互 + 导出分享
- **出差/旅行**: 多天行程规划 + 行李箱容量优化 + 目的地天气预测
- **场景识别**: 多维度场景引擎（主场景/子场景/情感）+ 软过滤评分

### V2 用户粘性与内容体系（Week 9-16）
- **穿搭日记**: 每日穿搭记录 + AI 智能点评 + 五行能量统计 + 衣物自动入衣橱
- **每日运势**: 五维度运势引擎 + FortuneRadar 可视化 + 月度/年度报告
- **命理进阶**: 大运流年 + 十神 + 纳音五行 + 神煞
- **修炼境界**: 能量计算 + 等级进阶（五行初识→五行大师）+ 成就徽章
- **穿搭广场**: 社区信息流 + 点赞评论 + 关注互动 + 内容审核
- **游戏化系统**: 积分/成就 + 每日签到 + 穿搭行为积分联动
- **智能提醒**: 天气/运势/衣橱/场景四维智能推送
- **五行小课堂**: 五行美学知识内容体系
- **后台管理**: 数据统计 / LLM 用量分析 / 账单查询
- **用户偏好学习**: 点赞点踩反馈闭环 + 推荐权重自动优化
- 🔒 会员体系 / 品牌合作 / 付费报告（代码已完成，个人备案免费版暂未接入支付）

---

## 🏗️ 技术栈

### 后端
- **FastAPI 0.110+**: 高性能 Python Web 框架（Async/Await）
- **PostgreSQL 15 + pgvector 0.5**: 关系型数据库 + 向量语义检索（HNSW 索引），生产运行于阿里云 RDS
- **LangGraph 0.2+**: AI Agent 状态机编排（推荐链路 + 衣橱批量识别两阶段入库）
- **DashScope（阿里百炼，国内端点）**: qwen-plus（LLM）+ qwen-vl-plus（衣物视觉打标）+ text-embedding-v3（Embedding）
- **阿里云 OSS / Cloudflare R2**: 双模式对象存储（统一适配器，生产以 OSS 为主）
- **自建 Redis（ECS 容器）/ Upstash Redis**: 双模式缓存（三级缓存策略）
- **Pillow + Satori**: 服务端海报/图片渲染引擎（CJK 字体子集化）
- **cnlunar**: 专业八字/农历/节气/大运计算库
- **apps/worker**: 独立异步任务进程（推送、定时任务）

### 前端
- **Next.js 14.2**: React 全栈框架（App Router）+ PWA
- **TypeScript 5.9**: 类型安全
- **Tailwind CSS 4**: 原子化 CSS + CSS 变量设计令牌（五行/节气多皮肤主题系统）
- **Framer Motion 12.x**: 高级动效与页面转场
- **Zustand 5.x**: 轻量级状态管理 + persist 持久化
- **Recharts 3.x**: 数据可视化（五行雷达图、运势图）

### 部署
- **阿里云 ECS**: 前后端统一容器化部署（`docker-compose.prod.yml`：api/worker/web/redis）
- **Nginx**: HTTPS 反向代理（站点 + api 子域名），`deploy/setup-nginx.sh` 一键配置
- **deploy/deploy.sh**: 一键差异化部署（git diff 变更检测 → 仅重建受影响服务 → 健康检查）
- **GitHub Actions**: 推荐算法质量门禁（`recommendation-gate.yml`）
- **Docker Compose**: 本地开发环境编排（pgvector + pgAdmin）

---

## 📂 项目结构

```
shunyishang/
├── apps/
│   ├── api/                    # FastAPI 后端（17 个路由模块）
│   │   ├── core/              # 配置/安全/缓存/限流/日志/PII 加密
│   │   ├── routers/           # API 路由
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑（30+ 服务模块）
│   │   ├── tests/             # 后端测试（1736 用例）
│   │   └── main.py            # 应用入口（lifespan 启动连接池/自动迁移/调度器）
│   ├── web/                    # Next.js 前端
│   │   ├── app/               # 页面路由（13 个页面：首页/衣橱/日记/运势/命理/修炼/社区/试衣/小课堂/后台…）
│   │   ├── components/        # React 组件（ui/features 分层）
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── store/             # Zustand 状态管理
│   │   └── lib/               # API 封装/工具函数
│   └── worker/                 # 独立后台任务进程
├── packages/                   # 跨应用共享库
│   ├── ai_agents/             # LangGraph Agent（推荐链路 + 衣橱识别编排）
│   ├── ai_skills/             # AI 技能框架（Prompt 定义 + 执行器）
│   ├── recommendation/        # 推荐引擎（六维融合评分）
│   ├── utils/                 # 八字/天气/场景/旅行规划
│   └── db/                    # 数据库连接池
├── data/
│   ├── seeds/                 # 种子数据（600+ 件衣物/配饰，在线候选池 800+ 件）
│   └── standards/             # 五行映射标准（颜色/面料/风格）
├── scripts/                    # 数据库迁移（27 个）+ 工具脚本
├── deploy/                     # Nginx 配置 + ECS 一键部署脚本
├── docker-compose.yml          # 本地开发环境编排
├── docker-compose.prod.yml     # 生产 ECS 编排（api/worker/web/redis）
├── Dockerfile(.ecs)            # 后端容器镜像
└── Dockerfile.web(.ecs)        # 前端容器镜像
```

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15 + pgvector 扩展（或直接用 Docker）
- Docker & Docker Compose（推荐，用于本地数据库编排）

### 本地开发

```bash
# 1. 克隆项目
git clone https://github.com/your-username/shunyishang.git
cd shunyishang

# 2. 后端设置
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env  # 填写环境变量

# 3. 前端设置
cd apps/web
npm install
cp .env.production.example .env.local  # 填写 NEXT_PUBLIC_API_URL 等
cd ../..

# 4. 初始化数据库（pgvector 容器，自动按序执行 init_db.sql + migrations）
docker compose up -d db

# 5. 启动开发服务
.venv/bin/uvicorn apps.api.main:app --reload --port 8000   # 后端 http://localhost:8000
cd apps/web && npm run dev                                  # 前端 http://localhost:3000
```

### 运行测试

```bash
# 后端测试（1736 用例）
source .venv/bin/activate && python -m pytest apps/api/tests -q

# 前端测试（956 用例）
cd apps/web && npx vitest run
```

---

## 🔑 环境变量

复制 `.env.example` 为 `.env` 并填写以下关键配置：

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 |
| `DASHSCOPE_API_KEY` | 阿里百炼 API Key（LLM + Embedding + VL，国内端点） |
| `JWT_SECRET_KEY` | JWT 签名密钥 |
| `REDIS_URL` / `REDIS_ENABLED` | 自建 Redis 缓存（兼容 `UPSTASH_REDIS_REST_URL/TOKEN`） |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` / `OSS_BUCKET_NAME` | 阿里云 OSS 对象存储（兼容 R2 变量组） |
| `WEATHER_API_KEY` | 和风天气 API Key |
| `AMAP_API_KEY` | 高德地图 API Key（地理编码/定位） |
| `CORS_ORIGINS` / `FRONTEND_URL` | 跨域与前端地址配置 |

前端环境变量位于 `apps/web/.env.local`：`NEXT_PUBLIC_API_URL`、`NEXT_PUBLIC_APP_NAME`、图片 CDN 域名等。

---

## 📄 License

MIT License

---

<p align="center">
  Made with ❤️ and ☯️ · 浙ICP备2026060847号 · 本平台内容仅供娱乐参考
</p>
