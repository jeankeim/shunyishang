# 📘 项目名称：WuXing AI Stylist (五行智能衣橱)
# 📄 文档类型：Project Master Specification (v2.1 - Production Complete)

## 1. 🎯 项目愿景与核心目标
构建一个基于 **中国传统五行理论 (金木水火土)** 与 **现代大语言模型 (LLM)** 相结合的智能穿搭推荐系统。
- **核心功能**：用户输入生辰八字或当前心情/场景，系统通过 RAG (检索增强生成) 从向量数据库中检索符合五行喜用神的衣物，并生成个性化的穿搭建议海报。
- **技术特色**：`pgvector` 语义搜索 + `LangGraph` 状态机 Agent + `Next.js` 流式交互。
- **当前阶段**: **生产环境运行中**（Vercel + Zeabur + R2/OSS + Upstash/Redis）
- **当前进度**: **Week 16 全部已完成**（核心功能 100%，V2 全部完成）
- **生产环境**: https://shunyishang.vercel.app

---

## 2. 🛠️ 技术栈规范 (Tech Stack)

### 2.1 前端

| 技术 | 版本 | 用途 |
| :--- | :--- | :--- |
| **Next.js** | 14.2 (App Router) | React 全栈框架，支持 SSR/SSG |
| **React** | 18.3 | UI 组件库 |
| **TypeScript** | 5.9 | 类型安全 |
| **Tailwind CSS** | 4.2 | 原子化 CSS 框架 |
| **Framer Motion** | 12.x | 高级动效与页面转场 |
| **Zustand** | 5.x | 轻量状态管理 + persist 持久化 |
| **Recharts** | 3.x | 五行能量雷达图可视化 |
| **Lucide React** | 0.577 | 图标库 |
| **html-to-image** | 1.11 | 前端 DOM 转图片（分享卡片） |
| **react-datepicker** | 9.x | 日期选择器（八字输入） |
| **lunar-javascript** | 1.6 | 前端农历/节气展示 |

### 2.2 后端

| 技术 | 版本 | 用途 |
| :--- | :--- | :--- |
| **FastAPI** | 0.110+ | 异步 Web 框架 |
| **Python** | 3.11+ | 运行时（生产 3.13） |
| **Pydantic** | V2 | 请求/响应数据验证 |
| **psycopg2** | binary | PostgreSQL 连接池 |
| **LangGraph** | 0.2+ | 有状态 AI Agent 工作流（4 节点） |
| **langchain-openai** | 0.2+ | LLM SDK（兼容阿里百炼） |
| **cnlunar** | 0.2+ | 专业八字/农历/大运计算 |
| **Pillow** | 10+ | 后端海报图片渲染（1080x1920） |
| **gunicorn** | 21+ | 生产级 WSGI 服务器 |
| **tenacity** | 8+ | 重试与容错机制 |
| **numpy** | <2.0 | 数值计算 |

### 2.3 AI/ML

| 技术 | 模型/服务 | 用途 |
| :--- | :--- | :--- |
| **DashScope** | qwen-flash | LLM 大语言模型（阿里百炼） |
| **DashScope** | text-embedding-v3 | 多语言语义向量 Embedding |
| **LangGraph** | 4 节点状态机 | 意图→检索→生成→格式化 |

### 2.4 数据库与存储

| 技术 | 版本/服务 | 用途 |
| :--- | :--- | :--- |
| **PostgreSQL** | 15 | 核心数据库 |
| **pgvector** | 0.5 | 向量语义检索（HNSW 索引） |
| **Cloudflare R2** | S3 兼容 | 对象存储（海外环境） |
| **阿里云 OSS** | oss2 SDK | 对象存储（国内环境，统一适配器） |
| **Upstash Redis** | REST API | 缓存（海外环境） |
| **阿里云 Redis** | redis SDK | 缓存（国内环境） |

### 2.5 部署与基础设施

| 技术 | 用途 | 备注 |
| :--- | :--- | :--- |
| **Vercel** | 前端托管 | 自动 CI/CD |
| **Zeabur** | 后端托管 | Docker 容器化 |
| **Docker** | 本地开发环境 | docker-compose 编排 |
| **OpenAI SDK** | LLM 调用 | 兼容阿里百炼 DashScope |
| **httpx** | HTTP 客户端 | Upstash REST / 外部 API |

### 2.6 测试

| 技术 | 用途 |
| :--- | :--- |
| **pytest** + **pytest-asyncio** | 后端单元测试/异步测试 |
| **pytest-cov** | 后端测试覆盖率（目标 93%+） |
| **factory-boy** | 后端测试工厂 |
| **Vitest** | 前端单元测试框架 |
| **Testing Library** | 前端组件测试 |

### 2.7 V2 新增服务（Week 8-16）

| 服务模块 | 文件 | 功能 |
| :--- | :--- | :--- |
| **虚拟试衣** | `VirtualTryOnCanvas.tsx` + `useTryOnCanvas.ts` | Canvas 画布 + 图层交互 |
| **穿搭日记** | `diary_service.py` + `diary/` 页面 | 日记 CRUD + AI 点评 |
| **运势引擎** | `fortune_engine.py` + `monthly_fortune_service.py` | 五维度运势 + 月度运势 |
| **命理进阶** | `destiny/` 路由 + `bazi_advanced.py` | 大运流年 + 十神 + 纳音 |
| **VIP会员** | `membership_service.py` + `payment_service.py` | 三级会员 + Mock 支付 |
| **推送通知** | `push_service.py` + `push_scheduler.py` | 多渠道推送 + 定时调度 |
| **社区广场** | `community/` 路由 + `content_moderation.py` | 帖子/点赞/评论/关注 |
| **游戏化** | `gamification_service.py` + `cultivation/` | 积分/成就/修炼等级 |
| **品牌合作** | 品牌路由 + 分销追踪 | CPS 分成模式 |
| **付费报告** | `fortune_report_service.py` | DashScope AI 深度运势报告 |
| **智能提醒** | `smart_reminder_service.py` | 天气/运势/衣橱/场景四维提醒 |
| **用户偏好** | `preference_service.py` | 反馈学习与推荐权重优化 |
| **海报渲染** | `poster_service.py` (Pillow) | 后端高清海报生成 |

---

## 3. 📂 完整目录结构规范 (Directory Structure Spec)

AI 在生成文件时，必须严格遵守以下目录职责划分：

```text
wuxing-ai-stylist/
│
├── PROJECT_SPEC.md             # [本文件] 项目总规，AI 的首要阅读材料
├── README.md                   # 项目入口文档，包含快速启动指南
├── .env                        # 环境变量 (DB_URL, OPENAI_API_KEY, etc.)
├── .gitignore
├── docker-compose.yml          # [Core] 编排 DB (pgvector), PgAdmin, Backend, Frontend
│
├── data/                       # [Data Layer] 静态数据与持久化卷
│   ├── standards/              # 数据标注标准规范
│   │   ├── wuxing_color_mapping.json    # 颜色-五行映射标准
│   │   ├── wuxing_material_mapping.json # 材质-五行映射标准
│   │   ├── wuxing_style_mapping.json    # 风格-五行映射标准
│   │   └── annotation_guide.md          # 数据标注指南文档
│   ├── seeds/                  # 种子数据源
│   │   ├── seed_data_100.json           # 100 条预定义的五行衣物数据
│   │   └── wuxing_elements.json         # 五行基础数据表
│   └── postgres/               # (Git Ignored) PG 数据持久化目录
│
├── scripts/                    # [DevOps & Tools] 迁移脚本（12 个）与工具脚本
│   ├── init_db.sql             # [W1] 数据库 DDL (建表、扩展、索引)
│   ├── import_seed.py          # [W1] ETL 脚本：JSON -> Embedding -> DB
│   └── migrations/             # [W1-W16] 增量迁移脚本（12 个）
│
├── TASKS/                      # [🚀 Project Command Center] 敏捷开发指挥中心
│   │                         # ⚠️ 所有开发指令和验收标准均在此目录下
│   ├── WEEK_01_DATA_FOUNDATION/    # ✅ 已完成
│   │   ├── 01_DB_SETUP/        # 任务：Docker & SQL Init
│   │   ├── 02_ETL_PIPELINE/    # 任务：数据向量化导入
│   │   └── 03_VECTOR_TEST/     # 任务：搜索验证
│   ├── WEEK_02_BACKEND_BRAIN/  # ✅ 已完成
│   ├── WEEK_03_FRONTEND_CORE/  # ✅ 已完成
│   ├── WEEK_04_USER_WARDROBE/  # ✅ 已完成
│   ├── WEEK_05_AI_ENHANCEMENT/ # ✅ 已完成
│   ├── WEEK_06_DEPLOY_OPTIMIZE/# ✅ 已完成（Vercel + Zeabur 部署）
│   ├── WEEK_07_SCENE_MOBILE/   # ✅ 已完成（场景优化 + 移动端适配）
│   └── WEEK_08_VIRTUAL_TRYON/  # ✅ 已完成（虚拟试衣）
│   └── WEEK_09_DIARY_FORTUNE/  # ✅ 已完成（日记+运势）
│   └── WEEK_10_MEMBERSHIP_PUSH/# ✅ 已完成（会员+推送）
│   └── WEEK_11_12_COMMUNITY_GAMIFY/ # ✅ 已完成（社区+游戏化）
│   └── WEEK_13_14_BRAND_PAID/  # ✅ 已完成（品牌+付费）
│   └── WEEK_15_16_SMART_REMINDER_CULTIVATION/ # ✅ 已完成（提醒+修炼）
│
├── apps/                       # [Application Layer] 核心业务代码
│   ├── api/                    # FastAPI 后端应用
│   │   ├── main.py             # 入口文件
│   │   ├── core/               # 配置、安全、异常处理
│   │   ├── routers/            # API 路由（14 个）
│   │   └── services/           # 业务逻辑层（23 个服务模块）
│   │
│   └── web/                    # Next.js 前端应用
│       ├── app/                # App Router 页面
│       ├── components/         # 通用组件 (RadarChart, ClothCard)
│       ├── features/           # 业务特性组件 (ChatInterface, WardrobeGrid)
│       └── lib/                # 工具函数 (API 客户端 hooks)
│
├── packages/                   # [Shared Libraries] 跨应用共享库
│   ├── ai_agents/              # LangGraph Agent 定义
│   │   ├── graph.py            # 状态机定义
│   │   ├── nodes.py            # 节点逻辑 (意图/检索/生成/格式化)
│   │   ├── wardrobe_client.py  # 衣橱数据客户端
│   │   └── prompts/            # System Prompts 模板
│   │
│   ├── utils/                  # 纯工具函数
│   │   ├── bazi_calculator.py  # 八字/五行计算逻辑
│   │   ├── bazi_advanced.py    # 大运流年/十神/纳音
│   │   ├── ten_gods.py         # 十神计算
│   │   ├── wuxing_rules.py     # 五行规则引擎
│   │   ├── scene_mapping.py    # 场景五行映射
│   │   ├── weather_api.py      # 和风天气 API
│   │   ├── weather_forecast.py # 天气预报服务
│   │   └── location_utils.py   # 浏览器定位工具
│   │
│   └── db/                     # 数据库连接池管理
│
└── tests/                      # [Testing] 单元测试与集成测试
    ├── apps/api/tests/         # 后端测试（46 个测试文件）
    └── apps/web/tests/         # 前端测试（17 个测试文件）
```

---

## 4. 🗺️ 开发路线图 (Roadmap & Milestones)

AI 需根据当前日期和以下里程碑判断当前应聚焦的任务：

### ✅ Week 1: 数据基石 - **[COMPLETED]**
- **完成日期**: 2026-03-20
- **目标**: 完成数据库搭建，导入 100 条种子数据并验证语义搜索。
- **关键产出**: `docker-compose.yml`, `init_db.sql`, `import_seed.py`, 验证通过的向量库。
- **验收标准**: ✅ 向量搜索验证通过，语义检索能正确命中目标衣物。

### ✅ Week 2: 后端大脑 - **[COMPLETED]**
- **完成日期**: 2026-03-27
- **目标**: 搭建 FastAPI 后端，实现正式版八字+场景推荐逻辑，构建 LangGraph 状态机 Agent，暴露 SSE 流式 API。
- **关键产出**: `apps/api/main.py`，`packages/utils/bazi_calculator.py`，`packages/ai_agents/graph.py`，`POST /api/v1/recommend/stream`
- **验收标准**: ✅ Agent 全流程跑通；SSE 接口首字延迟 < 1.5s；推荐结果必须引用真实 `item_code`，拒绝幻觉。
- **技术决策**（已确认）:
  - LLM：阿里百炼千问（`DASHSCOPE_API_KEY`，兼容 OpenAI SDK）
  - 数据库层：保持 psycopg2 连接池，不引入 SQLAlchemy
  - 八字：方案B —— `cnlunar` 库做四柱转换，自写五行统计 + 喜用神推断；每次请求传入
  - 意图推断：规则优先（关键词→五行映射表）+ LLM 兜底，规则结果注入 Prompt 上下文
  - 搜索增强：`final_score = 语义相似度 × 0.6 + 五行匹配度 × 0.4`，Top20 语义 → 加权重排 → 返回 Top5
  - SSE 格式：3 段式结构化流 `analysis → items → token流`
- **子任务**:
  - ✅ `01_FASTAPI_SCAFFOLD`：FastAPI 骨架 + psycopg2 连接池 + Pydantic Schema + `/health`
  - ✅ `02_UTILS_BAZI`：正式版八字计算 + 场景五行映射 + 喜用神推断
  - ✅ `03_LANGGRAPH_AGENT`：4 节点状态机（意图→检索→生成→格式化）
  - ✅ `04_API_EXPOSE`：SSE 流式接口 + 错误处理

### ✅ Week 3: 前端核心与可视化交互 - **[COMPLETED]**
- **完成日期**: 2026-04-01
- **目标**: Next.js 首页，五行雷达图可视化，流式对话 UI，24 节气自适应主题。
- **关键产出**: 
  - `apps/web/` 完整前端项目
  - `FiveElementRadar` 双图层雷达图组件
  - `ChatInterface` 流式对话界面
  - 24 节气自适应主题系统
- **验收标准**: 
  - 雷达图清晰表达"现状 vs 建议"双图层
  - 24 节气主题自动切换，深色模式默认
  - 文字流式输出（打字机效果），非等待后蹦出
  - 推荐卡片随检索完成逐步展示（AnimatePresence 动画）
  - 侧边栏布局，桌面端 ≥1280px 正常显示
  - 对话历史持久化（Zustand + persist）
- **技术决策**（已确认）:
  - UI 风格: 现代简约 + 深色模式 + 24 节气自适应主题
  - 布局: 类 ChatGPT 侧边栏（260px）+ 主内容区
  - 雷达图: 双图层设计（虚线现状 + 实线建议），Recharts 实现
  - 流式 UI: AsyncGenerator 解析 SSE，TypewriterText 打字机，AnimatePresence 卡片动画
  - 八字输入: 底部输入框旁 📅 按钮，弹出表单
  - 响应式: 优先桌面端（≥1280px）
  - 状态管理: Zustand + persist（LocalStorage）
  - 图片: MVP 阶段使用 placehold.co 占位图
- **子任务**:
  - `01_NEXTJS_INIT`: Next.js 14 + TypeScript + Tailwind + Shadcn/UI + SSE 客户端
  - `02_COMPONENTS_RADAR`: FiveElementRadar 双图层组件 + 数据转换工具
  - `03_PAGE_DASHBOARD`: 侧边栏布局 + 24 节气主题系统 + Header
  - `04_STREAMING_UI`: 流式解析 + TypewriterText + AnimatePresence 卡片动画

### ✅ Week 4: 个性化闭环 - **[COMPLETED]**
- **完成日期**: 2026-03-26

### ✅ Week 5: 多模态增强 - **[COMPLETED]**
- **完成日期**: 2026-04-05

### ✅ Week 6: 部署与优化 - **[COMPLETED]**
- **完成日期**: 2026-07-01
- **实际方案**: Vercel（前端）+ Zeabur（后端）+ R2/OSS（图片）+ Upstash/Redis（缓存）
- **已完成**: 数据库索引优化、GZip 压缩、连接池健康检查、Docker Compose 生产配置

### ✅ Week 7: 场景优化 + 移动端适配 - **[COMPLETED]**
- **完成日期**: 2026-04-11
- **场景优化**: 软过滤、场景映射、多维度识别、天气过滤（100%）
- **移动端适配**: 响应式布局、手势交互、PWA 支持（100%）

### ✅ Week 8: 虚拟试衣 - **[COMPLETED]**
- **完成日期**: 2026-04-13
- **功能**: Canvas 画布组件 + 交互 Hook + 工具栏 + 图层管理 + 导出分享

---

## 5. 🤖 AI 协作协议 (AI Collaboration Protocol)

为了保持项目一致性，AI Agent 在执行任何操作时必须遵循以下规则：

1.  **上下文感知**: 每次生成代码前，必须先检查 `TASKS/WEEK_X/...` 目录下对应的 `任务说明书.md`。
2.  **文件定位**: 严禁将业务逻辑代码放入 `scripts/` (除非是 ETL 脚本) 或根目录。后端代码必须在 `apps/api`，前端在 `apps/web`，共享库在 `packages`。
3.  **类型安全**: Python 代码必须包含 Type Hints；TypeScript 代码严禁使用 `any`，必须定义 Interface。
4.  **测试驱动**: 完成任何功能模块后，必须更新或创建对应的测试文件 (`tests/`) 或验证脚本。
5.  **进度同步**: 完成一个子任务后，需在 `README.md` 或对应任务的 `完成反馈清单.md` 中标记 `[x]`。
6.  **错误处理**: 所有数据库操作和 API 调用必须包含 `try-except` 块，并返回标准的 JSON 错误格式。

---

## 6. 🚀 快速启动指令 (For AI Agent)

如果你是一个新的 AI 会话，请按以下步骤初始化项目：

1.  **读取**: 仔细阅读本 `PROJECT_SPEC.md`。
2.  **检查**: 检查当前文件系统，确认是否已存在 `TASKS/WEEK_01` 中的文件。
3.  **执行**:
    - 如果 `docker-compose.yml` 不存在 -> 执行 **Week 1 Task 1**。
    - 如果 `scripts/import_seed.py` 不存在 -> 执行 **Week 1 Task 2**。
    - 如果数据未导入 -> 指导用户运行导入脚本。
    - 如果未验证 -> 执行 **Week 1 Task 3**。
4.  **汇报**: 输出当前项目状态概览，并询问用户是否进入下一任务。

---

> **注意**: 本项目已完成 MVP 及 V2 全部功能（Week 1-16，100%），生产环境运行中。后续规划详见 [V2 路线图](TASKS/PRODUCT_V2_ROADMAP.md)，国内部署迁移详见 [迁移计划](MIGRATION_CHINA_PLAN.md) 。

---

## 7. 🚀 产品2.0 规划 (Product V2 Roadmap)

### 当前阶段过渡

**V1 MVP** → **V2 用户粘性与商业化**

| 维度 | V1 (MVP) | V2 (产品化) |
|------|---------|------------|
| **核心目标** | 功能可用 | 用户粘性与变现 |
| **用户价值** | 单次推荐价值 | 持续使用价值 |
| **商业模式** | 无 | 会员订阅+电商导流 |
| **社交属性** | 无 | 社区+互动 |
| **日活驱动** | 被动触发 | 主动打开 |

### V2 开发阶段规划

#### ✅ Week 9: 穿搭日记与运势系统 - **[COMPLETED]**
- **完成日期**: 2026-04-20
- **目标**: 创建每日打开理由
- **核心功能**:
  - 穿搭日记本（记录+AI点评）
  - 每日运势推送
  - 五行能量统计
  - 命理进阶：大运流年 + 十神 + 纳音五行
- **详细文档**: [TASKS/WEEK_09_DIARY_FORTUNE/README.md](TASKS/WEEK_09_DIARY_FORTUNE/README.md)

#### ✅ Week 10: VIP会员与推送系统 - **[COMPLETED]**
- **完成日期**: 2026-04-27
- **目标**: 商业化基础设施
- **核心功能**:
  - VIP会员体系（免费/月度/年度）
  - Mock 支付服务 + 权限中间件
  - 多渠道推送通知（webpush/sms/email）
- **详细文档**: [TASKS/WEEK_10_MEMBERSHIP_PUSH/README.md](TASKS/WEEK_10_MEMBERSHIP_PUSH/README.md)

#### ✅ Week 11-12: 穿搭广场社区 + 游戏化 - **[COMPLETED]**
- **完成日期**: 2026-05-11
- **目标**: 内容生态 + 用户激励
- **核心功能**:
  - 穿搭广场信息流 + 点赞评论 + 关注系统
  - 积分系统 + 成就徽章 + 等级成长体系
  - 每日签到 + 穿搭行为积分联动

#### ✅ Week 13-14: 商业化深化 - **[COMPLETED]**
- **完成日期**: 2026-05-25
- **目标**: 变现能力提升
- **核心功能**:
  - 品牌合作推荐（CPS）
  - 付费运势报告（DashScope AI）
  - 深度运势解读 + 五行穿搭指导

#### ✅ Week 15-16: 生态完善 - **[COMPLETED]**
- **完成日期**: 2026-06-08
- **目标**: 产品生态闭环
- **核心功能**:
  - 五行修炼系统（能量/等级/成就）
  - 智能提醒服务（天气/运势/衣橱/场景）
  - 修炼境界进阶（五行初识→五行大师）

### V2 核心目标 (OKR)

| 目标 | 关键结果 | 衡量指标 |
|------|---------|---------|
| **提升用户粘性** | DAU增长300% | DAU: 300 → 900 |
| | 7日留存率提升 | 留存: 15% → 40% |
| | 日均停留时长翻倍 | 时长: 3min → 6min |
| **构建内容生态** | 月度日记发布量 | 1000+ 篇/月 |
| | 穿搭广场浏览量 | 5000+ 次/日 |
| | 用户互动率 | 15%+ |
| **实现商业化** | 付费转化率 | 5%+ |
| | 月度ARPU | ¥30+ |
| | 商业化收入占比 | 30%+ |

### V2 技术扩展（已实现）

| 层级 | 新增技术 | 用途 | 状态 |
|------|---------|------|:---:|
| 前端 | Framer Motion 12.x | 高级动效与页面转场 | ✅ 已实现 |
| | PWA + Web Push | 推送通知 | ✅ 已实现 |
| 后端 | push_scheduler.py | 定时推送调度（替代 Celery） | ✅ 已实现 |
| | payment_service.py | 支付服务（当前 Mock，待接真实 SDK） | ✅ Mock |
| | Pillow | 后端海报渲染（替代前端方案） | ✅ 已实现 |
| 数据库 | 21 张表（5 基础 + 16 V2） | V2 功能数据 | ✅ 已实现 |
| 缓存 | Upstash Redis + httpx | 缓存 + 推送队列 | ✅ 已实现 |
| 存储 | 统一适配器（R2/OSS 双模式） | 国内/海外存储自动切换 | ✅ 已实现 |

### 数据库表清单（21 张）

| 分类 | 表名 | 用途 |
|------|------|------|
| **基础（5）** | `items` | 公共衣物库 |
| | `users` | 用户账户 |
| | `user_wardrobe` | 个人衣橱 |
| | `five_element_configs` | 五行配置 |
| | `feedback_logs` | 反馈日志 |
| **日记/运势（3）** | `outfit_diaries` | 穿搭日记 |
| | `diary_outfit_items` | 日记关联衣物 |
| | `daily_fortune` | 每日运势 |
| **会员/推送（4）** | `subscriptions` | 会员订阅 |
| | `payment_records` | 支付记录 |
| | `push_notifications` | 推送通知 |
| | `user_push_settings` | 推送偏好 |
| **社区（3）** | `community_posts` | 社区帖子 |
| | `post_likes` | 点赞 |
| | `post_comments` | 评论 |
| **游戏化（4）** | `user_points` | 用户积分 |
| | `points_history` | 积分流水 |
| | `achievements` | 成就定义 |
| | `user_achievements` | 用户成就 |
| **商业化（2）** | `paid_reports` | 付费运势报告 |
| | `user_preferences` | 用户偏好学习 |

### 完整路线图文档

详见: [TASKS/PRODUCT_V2_ROADMAP.md](TASKS/PRODUCT_V2_ROADMAP.md)