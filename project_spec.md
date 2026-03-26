这是一个专为 **AI Agent (如 Cursor, Devin, Claude Code)** 设计的 **项目规范说明书 (Project Specification / Spec)**。

你可以直接将以下内容保存为项目根目录下的 `PROJECT_SPEC.md` 文件。当开启一个新的 AI 会话时，只需告诉 AI：“请读取 `PROJECT_SPEC.md` 并基于此生成完整的项目骨架”，AI 就能瞬间理解整个项目的架构、技术栈、目录职责以及当前的开发进度（MVP 阶段）。

---

# 📘 项目名称：WuXing AI Stylist (五行智能衣橱)
# 📄 文档类型：Project Master Specification (v1.0 - MVP Phase)

## 1. 🎯 项目愿景与核心目标
构建一个基于 **中国传统五行理论 (金木水火土)** 与 **现代大语言模型 (LLM)** 相结合的智能穿搭推荐系统。
- **核心功能**：用户输入生辰八字或当前心情/场景，系统通过 RAG (检索增强生成) 从向量数据库中检索符合五行喜用神的衣物，并生成个性化的穿搭建议海报。
- **技术特色**：`pgvector` 语义搜索 + `LangGraph` 状态机 Agent + `Next.js` 流式交互。
- **当前阶段**：**MVP (最小可行性产品)**，周期 6 周。
- **当前进度**：**Week 1 (数据基石)** - 正在初始化数据库与向量化种子数据。

---

## 2. 🏗️ 技术栈规范 (Tech Stack)

| 层级 | 技术选型 | 版本/备注 |
| :--- | :--- | :--- |
| **前端** | Next.js 14+ (App Router) | React, TypeScript, Tailwind CSS, Shadcn/UI |
| **可视化** | Recharts / Visx | 用于绘制“五行能量雷达图” |
| **后端** | FastAPI | Python 3.10+, Async/Await, Pydantic V2 |
| **AI 框架** | LangGraph | 构建有状态的推荐 Agent 工作流 |
| **数据库** | PostgreSQL 16 + pgvector | 核心向量存储，HNSW 索引 |
| **ORM** | SQLAlchemy (Async) | 或直接用 SQL 配合 psycopg2 |
| **Embedding** | BGE-M3 (Local) 或 OpenAI | 多语言语义向量模型 |
| **部署** | Docker & Docker Compose | 容器化编排，便于本地开发与云端迁移 |

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
│   │   ├── wuxing_elements.json         # 五行基础数据表
│   │   └── init_mappings.sql            # 初始化五行映射表 SQL
│   └── postgres/               # (Git Ignored) PG 数据持久化目录
│
├── scripts/                    # [DevOps & Tools] 一次性脚本与工具
│   ├── init_db.sql             # [W1] 数据库 DDL (建表、扩展、索引)
│   ├── import_seed.py          # [W1] ETL 脚本：JSON -> Embedding -> DB
│   └── test_semantic_search.py # [W1] 语义搜索验证脚本
│
├── TASKS/                      # [🚀 Project Command Center] 敏捷开发指挥中心
│   │                         # ⚠️ 所有开发指令和验收标准均在此目录下
│   ├── WEEK_01_DATA_FOUNDATION/
│   │   ├── 01_DB_SETUP/        # 任务：Docker & SQL Init
│   │   ├── 02_ETL_PIPELINE/    # 任务：数据向量化导入
│   │   └── 03_VECTOR_TEST/     # 任务：搜索验证
│   ├── WEEK_02_BACKEND_BRAIN/  # (待执行) FastAPI & LangGraph
│   ├── WEEK_03_FRONTEND_CORE/  # (待执行) Next.js UI
│   ├── WEEK_04_USER_WARDROBE/  # (待执行) 用户衣橱 CRUD
│   ├── WEEK_05_AI_ENHANCEMENT/ # (待执行) 图片上传 & 海报生成
│   └── WEEK_06_DEPLOY_OPTIMIZE/# (待执行) 部署优化
│
├── apps/                       # [Application Layer] 核心业务代码
│   ├── api/                    # FastAPI 后端应用
│   │   ├── main.py             # 入口文件
│   │   ├── core/               # 配置、安全、异常处理
│   │   ├── models/             # SQLAlchemy 模型定义
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── routers/            # API 路由 (recommend, wardrobe, user)
│   │   └── services/           # 业务逻辑层 (DB 操作, Agent 调用)
│   │
│   └── web/                    # Next.js 前端应用
│       ├── app/                # App Router 页面
│       ├── components/         # 通用组件 (RadarChart, ClothCard)
│       ├── features/           # 业务特性组件 (ChatInterface, WardrobeGrid)
│       └── lib/                # 工具函数 (API 客户端 hooks)
│
├── packages/                   # [Shared Libraries] 跨应用共享库
│   ├── ai-agents/              # LangGraph Agent 定义
│   │   ├── graph.py            # 状态机定义
│   │   ├── nodes.py            # 节点逻辑 (检索器、分析器、生成器)
│   │   └── prompts/            # System Prompts 模板
│   │
│   ├── utils/                  # 纯工具函数
│   │   ├── bazi_calculator.py  # 八字/五行计算逻辑
│   │   └── weather_api.py      # 天气数据获取
│   │
│   └── db/                     # 数据库连接池管理
│
└── tests/                      # [Testing] 单元测试与集成测试
    ├── test_api/
    ├── test_agents/
    └── conftest.py
```

---

## 4. 🗺️ 开发路线图 (Roadmap & Milestones)

AI 需根据当前日期 (`2026-03-17`) 和以下里程碑判断当前应聚焦的任务：

### 🟢 Phase 1: 数据基石 (Week 1) - **[CURRENT STATUS]**
- **目标**: 完成数据库搭建，导入 100 条种子数据并验证语义搜索。
- **关键产出**: `docker-compose.yml`, `init_db.sql`, `import_seed.py`, 验证通过的向量库。
- **验收标准**: 运行 `test_semantic_search.py`，搜索“神秘”能命中“深紫色丝绒”衣物。

### 🟡 Phase 2: 后端大脑 (Week 2) - **[COMPLETED]**
- **目标**: 搭建 FastAPI 后端，实现正式版八字+场景推荐逻辑，构建 LangGraph 状态机 Agent，暴露 SSE 流式 API。
- **关键产出**: `apps/api/main.py`，`packages/utils/bazi_calculator.py`，`packages/ai_agents/graph.py`，`POST /api/v1/recommend/stream`
- **验收标准**: ✅ `scripts/test_agent_flow.py` 跑通全流程；SSE 接口首字延迟 < 1.5s；推荐结果必须引用真实 `item_code`，拒绝幻觉。
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

### 🔵 Phase 3: 前端核心与可视化交互 (Week 3) - **[CURRENT STATUS]**
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

### 🟣 Phase 4: 个性化闭环 (Week 4)
- **目标**: 用户衣橱管理 (CRUD)，Agent 限制仅检索用户衣橱，反馈机制。
- **关键产出**: 衣橱管理页面，Agent 上下文过滤逻辑。
- **验收标准**: 删除衣橱物品后，推荐结果实时更新。

### 🟠 Phase 5: 多模态增强 (Week 5)
- **目标**: 图片上传与自动打标，简易试衣/Mock，分享海报生成。
- **关键产出**: 图片上传接口，Canvas 海报生成逻辑。
- **验收标准**: 上传衣服照片自动识别五行属性，生成可下载的海报。

### 🔴 Phase 6: 部署与优化 (Week 6)
- **目标**: Docker 全量编排，性能优化，生产环境部署。
- **关键产出**: 优化的 Docker Compose, Nginx 配置，CI/CD 脚本。
- **验收标准**: 公网可访问，并发测试通过。

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

> **注意**: 本项目处于 **MVP 阶段**，优先保证核心链路 (数据->Agent->展示) 的跑通，非核心功能 (如复杂的用户认证、第三方支付) 可暂时 Mock 或简化。