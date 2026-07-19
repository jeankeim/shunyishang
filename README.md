# 顺衣尚 - 五行智能穿搭推荐系统

> 基于八字命理和五行理论的 AI 穿搭推荐平台 | 生产环境运行中

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Next.js-14.2-black.svg" alt="Next.js 14.2">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-green.svg" alt="FastAPI 0.110+">
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg" alt="PostgreSQL 15">
  <img src="https://img.shields.io/badge/pgvector-0.5-orange.svg" alt="pgvector 0.5">
  <img src="https://img.shields.io/badge/LangGraph-0.2+-purple.svg" alt="LangGraph">
</p>

<p align="center">
  <b>结合传统命理学与现代 AI 技术的智能穿搭推荐平台</b>
</p>

---

## 📊 项目状态

**核心完成度**: 100%（Week 1-16 全部功能已完成）  
**商业化功能**: 🔒 支付相关（VIP会员/品牌合作/付费报告）代码已完成，暂未接入支付（个人备案免费版，所有功能免费开放）  
**生产环境**: 🟢 运行中（Vercel + Zeabur + R2/OSS + Upstash/Redis）  
**测试覆盖**: 前端 908 用例 100% 通过 | 后端 1400+ 用例 99.5% 通过

---

## ✨ 核心功能

### MVP 基础能力（Week 1-8）
- **八字命理分析**: 生辰八字四柱计算 + 五行强弱 + 喜用神/忌用神推断
- **智能穿搭推荐**: LangGraph 4 节点 Agent + pgvector 语义搜索 + 五行动态权重
- **天气感知**: 和风天气 API + 浏览器 GPS 定位 + 温度 4 级过滤
- **用户衣橱**: AI 智能打标 + 三种推荐模式（全局库/我的衣橱/智能混合）
- **分享海报**: 后端 Pillow 渲染 1080×1920 + 3 种模板 + 自定义编辑
- **虚拟试衣**: Canvas 画布 + 图层管理 + 拖拽交互 + 导出分享
- **出差/旅行**: 多天行程规划 + 行李箱容量优化 + 目的地天气预测
- **场景识别**: 多维度场景引擎（主场景/子场景/情感）+ 软过滤评分

### V2 用户粘性与商业化（Week 9-16）
- **穿搭日记**: 每日穿搭记录 + AI 智能点评 + 五行能量统计
- **每日运势**: 五维度运势引擎 + FortuneRadar 可视化 + 月度运势
- **命理进阶**: 大运流年 + 十神 + 纳音五行 + 修炼境界进阶
- **VIP 会员**: 三级会员体系（免费/月度¥19.9/年度¥168）+ 推送通知 🔒 暂未接入（个人备案免费版，所有功能免费开放）
- **穿搭广场**: 社区信息流 + 点赞评论 + 关注互动 + 内容审核
- **游戏化系统**: 积分/成就/修炼等级 + 每日签到 + 穿搭行为积分联动
- **五行修炼**: 能量计算 + 等级进阶（五行初识→五行大师）+ 成就徽章
- **智能提醒**: 天气/运势/衣橱/场景四维智能推送
- **品牌合作**: 品牌商品推荐 + CPS 分销追踪 🔒 暂未接入（个人备案免费版，无支付功能）
- **付费报告**: DashScope AI 深度运势报告 + 五行穿搭指导 🔒 暂未接入（个人备案免费版，所有报告免费开放）
- **用户偏好学习**: 反馈学习 + 推荐权重自动优化

---

## 🏗️ 技术栈

### 后端
- **FastAPI 0.110+**: 高性能 Python Web 框架（Async/Await）
- **PostgreSQL 15 + pgvector 0.5**: 关系型数据库 + 向量语义检索（HNSW 索引）
- **LangGraph 0.2+**: AI Agent 4 节点状态机（意图→检索→生成→格式化）
- **DashScope**: 阿里百炼千问 qwen-flash（LLM）+ text-embedding-v3（Embedding）
- **Cloudflare R2 / 阿里云 OSS**: 双模式对象存储（统一适配器）
- **Upstash Redis / 阿里云 Redis**: 双模式缓存
- **Pillow**: 后端海报图片渲染引擎
- **cnlunar**: 专业八字/农历/大运计算库

### 前端
- **Next.js 14.2**: React 全栈框架（App Router）
- **TypeScript 5.9**: 类型安全
- **Tailwind CSS 4.2**: 原子化 CSS
- **Framer Motion 12.x**: 高级动效与页面转场
- **Zustand 5.x**: 轻量级状态管理 + persist 持久化
- **Recharts 3.x**: 数据可视化（五行雷达图、运势图）

### 部署
- **Vercel**: 前端托管（自动 CI/CD）
- **Zeabur**: 后端托管（Docker 容器化 + gunicorn）
- **Docker Compose**: 本地开发环境编排

---

## 📂 项目结构

```
shunyishang/
├── apps/
│   ├── api/                    # FastAPI 后端（14 个 API 路由）
│   │   ├── core/              # 配置/安全/缓存/日志/计划中间件
│   │   ├── models/            # 预留：未来 ORM 数据模型抽象层
│   │   ├── routers/           # API 路由
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑（20+ 服务模块）
│   │   ├── tests/             # 后端测试（1400+ 用例）
│   │   └── main.py            # 应用入口
│   └── web/                    # Next.js 前端
│       ├── app/               # 页面路由（9 个页面）
│       ├── components/        # React 组件
│       ├── hooks/             # 自定义 Hooks
│       ├── store/             # Zustand 状态管理
│       ├── lib/               # API 封装/工具函数
│       └── tests/             # 前端测试（908 用例）
├── packages/                   # 跨应用共享库
│   ├── ai_agents/             # LangGraph Agent（4 节点状态机）
│   ├── recommendation/        # 推荐引擎（六维融合评分）
│   ├── utils/                 # 八字/天气/场景/旅行规划
│   └── db/                    # 数据库连接池
├── data/
│   ├── seeds/                 # 种子数据（100+ 衣物/配饰）
│   └── standards/             # 五行映射标准（颜色/面料/风格）
├── scripts/                    # 数据库迁移（15 个）+ 工具脚本
├── docker-compose.yml          # 本地开发环境编排
├── Dockerfile                  # 后端容器镜像
└── Dockerfile.web              # 前端容器镜像
```

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15 + pgvector 扩展
- Docker & Docker Compose（可选，用于本地编排）

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
cp .env.production.example .env.local  # 填写环境变量

# 4. 初始化数据库
docker compose up -d db
psql -f scripts/init_db.sql

# 5. 启动开发服务
cd apps/web && npm run dev   # 前端 http://localhost:3000
cd apps/api && uvicorn main:app --reload  # 后端 http://localhost:8000
```

### 运行测试

```bash
# 后端测试（1400+ 用例）
source .venv/bin/activate && python -m pytest apps/api/tests/ -q

# 前端测试（908 用例）
cd apps/web && npx vitest run
```

---

## 🔑 环境变量

复制 `.env.example` 为 `.env` 并填写以下关键配置：

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 |
| `DASHSCOPE_API_KEY` | 阿里百炼 API Key（LLM + Embedding） |
| `JWT_SECRET_KEY` | JWT 签名密钥 |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` | Cloudflare R2 对象存储 |
| `UPSTASH_REDIS_URL` | Redis 缓存连接 |
| `WEATHER_API_KEY` | 和风天气 API Key |

---

## 📄 License

MIT License

---

<p align="center">
  Made with ❤️ and ☯️
</p>
