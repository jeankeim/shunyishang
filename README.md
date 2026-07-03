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
**生产环境**: 🟢 运行中（Vercel + Zeabur + R2/OSS + Upstash/Redis）  
**详细进度**: 查看 [PROGRESS.md](PROGRESS.md)

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
- **VIP 会员**: 三级会员体系（免费/月度¥19.9/年度¥168）+ 推送通知
- **穿搭广场**: 社区信息流 + 点赞评论 + 关注互动 + 内容审核
- **游戏化系统**: 积分/成就/修炼等级 + 每日签到 + 穿搭行为积分联动
- **五行修炼**: 能量计算 + 等级进阶（五行初识→五行大师）+ 成就徽章
- **智能提醒**: 天气/运势/衣橱/场景四维智能推送
- **品牌合作**: 品牌商品推荐 + CPS 分销追踪
- **付费报告**: DashScope AI 深度运势报告 + 五行穿搭指导
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
│   │   ├── routers/           # API 路由
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── services/          # 业务逻辑（20+ 服务模块）
│   │   └── main.py            # 应用入口
│   └── web/                    # Next.js 前端
│       ├── app/               # 页面路由（9 个页面）
│       ├── components/        # React 组件
│       ├── hooks/             # 自定义 Hooks
│       ├── store/             # Zustand 状态管理
│       └── lib/               # API 封装/工具函数
├── packages/                   # 跨应用共享库
│   ├── ai_agents/             # LangGraph Agent（4 节点状态机）
│   ├── utils/                 # 八字/天气/场景/旅行规划
│   └── db/                    # 数据库连接池
├── data/                       # 种子数据 + 五行标准
├── scripts/                    # 数据库迁移脚本（9 个）
├── TASKS/                      # 周迭代任务文档
├── PROGRESS.md                 # 项目进度说明
├── project_spec.md             # 技术规格说明
└── MIGRATION_CHINA_PLAN.md     # 国内部署迁移计划
```

---

## 🚀 快速开始

详见 [PROGRESS.md](PROGRESS.md#-快速开始)

---

## 📄 文档索引

| 文档 | 说明 |
|------|------|
| [PROGRESS.md](PROGRESS.md) | 📄 项目进度说明（功能清单/技术亮点/后续计划） |
| [project_spec.md](project_spec.md) | 📘 技术规格说明（架构设计/技术栈/AI 协作协议） |
| [PRODUCT_V2_ROADMAP.md](TASKS/PRODUCT_V2_ROADMAP.md) | 🚀 V2 产品路线图（Phase 1-4 全部完成） |
| [MIGRATION_CHINA_PLAN.md](MIGRATION_CHINA_PLAN.md) | 🇨🇳 国内部署迁移完整计划 |

---

<p align="center">
  Made with ❤️ and ☯️
</p>
