# 顺衣尚 - 五行智能穿搭推荐系统

> 基于八字命理和五行理论的 AI 穿搭推荐平台 | 生产环境运行中

---

## 📊 项目概况

**项目状态**: 🟢 生产环境运行中（Vercel + Zeabur）  
**核心完成度**: 90%（Week 1-4 核心功能 + Week 5 海报生成 + Week 7 场景优化）  
**技术栈**: Next.js 14 + FastAPI + PostgreSQL + pgvector + LangGraph  
**部署架构**: Vercel（前端）+ Zeabur（后端）+ R2（图片）+ Upstash（缓存）

---

## ✅ 已完成功能

### Week 1: 数据基础设施 ✅
- ✅ PostgreSQL + pgvector 向量数据库
- ✅ 100+ 条种子数据 + 五行配置标准
- ✅ HNSW 向量索引优化
- ✅ ETL 数据管道

### Week 2: 后端智能大脑 ✅
- ✅ FastAPI 框架 + JWT 认证
- ✅ 八字计算 API（cnlunar 库）
- ✅ LangGraph 4 节点 AI Agent
- ✅ SSE 流式推荐接口
- ✅ Redis 缓存（Upstash）

### Week 3: 前端核心界面 ✅
- ✅ Next.js 14 + TypeScript + Tailwind
- ✅ 五行雷达图可视化（Recharts）
- ✅ 流式聊天界面（打字机效果）
- ✅ 浏览器 GPS 自动定位
- ✅ 和风天气 API 集成

### Week 4: 用户衣橱系统 ✅
- ✅ 衣橱 CRUD + AI 智能打标
- ✅ 三种推荐模式（全局库/我的衣橱/智能混合）
- ✅ 自动八字分析 + 资料优先模式
- ✅ 简化输入流程（描述+可选图片）

### Week 5: AI 多模态增强 ✅
- ✅ 图片上传（R2 对象存储）
- ✅ 分享海报生成（3 种模板：简约/五行/卡片）
- ✅ 海报编辑器（标题/文案/签名自定义）
- ✅ 五行配色主题切换

### Week 7: 场景推荐优化 ✅
- ✅ 软过滤机制（场景适配评分）
- ✅ 多维度场景识别（主场景+子场景+情感）
- ✅ 前端场景标签展示（适配度进度条）
- ✅ 天气温度过滤（4 级：极冷/较冷/温和/炎热）
- ✅ 泳装性别修正

### 移动端适配 ✅
- ✅ 下拉刷新（衣橱页面）
- ✅ 手势左滑删除
- ✅ 响应式布局优化
- ✅ PWA 支持

---

## 🎯 核心特性

### 1. 智能推荐引擎
```
用户输入 → 意图识别 → 向量检索 → 五行匹配 → AI 生成 → 流式输出
```
- 动态权重：语义相似度 60% + 五行匹配度 40%
- 分类多样性：确保上装/下装/外套/配饰均衡
- 天气适配：温度过滤 + 天气状况过滤

### 2. 三种推荐模式
| 模式 | 数据源 | 登录要求 | 适用场景 |
|------|--------|---------|---------|
| 全局库 | items 表 | 不需要 | 快速体验 |
| 我的衣橱 | user_wardrobe | 必需 | 个性化推荐 |
| 智能混合 | 衣橱 + 公共库 | 必需 | 平衡丰富度 |

### 3. 八字命理分析
- 自动生成四柱（年柱/月柱/日柱/时柱）
- 计算五行强弱 + 喜用神/忌用神
- 动态首页布局（有八字显示卡片，无八字显示输入）

### 4. 海报生成
- 3 种模板风格
- 1080x1920 高清输出
- 支持自定义编辑
- 后端 Pillow 生成（生产环境）

---

## 🏗️ 项目结构

```
shunyishang/
├── apps/
│   ├── api/                    # FastAPI 后端
│   │   ├── core/              # 配置/安全/日志
│   │   ├── routers/           # API 路由（7 个）
│   │   ├── services/          # 业务逻辑（R2/Upstash/AI）
│   │   └── main.py            # 应用入口
│   └── web/                    # Next.js 前端
│       ├── app/               # 页面路由
│       ├── components/        # React 组件
│       ├── hooks/             # 自定义 Hooks
│       ├── store/             # Zustand 状态管理
│       └── lib/               # API 封装/工具函数
├── packages/
│   ├── ai_agents/             # LangGraph Agent
│   │   ├── graph.py          # 状态机定义
│   │   ├── nodes.py          # 4 个节点逻辑
│   │   └── prompts/          # AI Prompt 模板
│   ├── utils/                 # 通用工具（八字/五行规则）
│   └── db/                    # 数据库连接
├── data/
│   ├── seeds/                 # 种子数据（100 条）
│   └── standards/             # 五行映射标准
├── scripts/                   # 一次性脚本
├── TASKS/                     # 任务文档（历史参考）
├── PROGRESS.md                # 📄 本文件：项目进度说明
├── README.md                  # 项目入口文档
├── project_spec.md            # 技术规格说明
└── docker-compose.yml         # 本地开发环境
```

---

## 🚀 快速开始

### 本地开发

```bash
# 1. 克隆项目
git clone https://github.com/jeankeim/shunyishang.git
cd shunyishang

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥

# 3. 启动数据库
docker-compose up -d postgres pgadmin

# 4. 初始化数据库
psql -h localhost -U wuxing_user -d wuxing_db -f scripts/init_db.sql

# 5. 启动后端
cd apps/api
uvicorn main:app --reload --port 8000

# 6. 启动前端
cd apps/web
npm install
npm run dev
```

### 生产环境

- **前端**: https://shunyishang.vercel.app
- **后端**: https://shunyishang-api.zeabur.app
- **API 文档**: https://shunyishang-api.zeabur.app/docs

---

## 📈 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| API P95 响应时间 | < 200ms | ~150ms |
| 向量搜索 | < 100ms | ~80ms |
| 缓存命中率 | > 80% | ~85% |
| 并发用户 | 100+ | 已验证 |
| 首屏加载 | < 3s | ~2.5s |

---

## 🔧 技术亮点

1. **LangGraph 状态机**: 4 节点推荐流程（意图→检索→生成→格式化）
2. **pgvector 向量搜索**: HNSW 索引，余弦相似度检索
3. **SSE 流式响应**: 3 段式结构化流（分析→物品→推荐理由）
4. **R2 对象存储**: Cloudflare CDN 加速图片分发
5. **Upstash Redis**: Serverless 缓存，按量计费
6. **动态权重算法**: 根据八字/场景自动调整语义/五行权重比例

---

## 📋 后续计划

### P0 - 高优先级
- [ ] 生产环境性能优化（慢查询分析、压力测试）- 6-8 小时

### P1 - 中优先级
- [ ] 虚拟试衣功能（Canvas 图片叠加）- 8-10 小时
- [ ] 用户反馈学习系统（点赞/点踩数据收集）- 6-8 小时

### P2 - 低优先级
- [ ] 出差/旅行场景规则增强 - 3-4 小时
- [ ] 命理进阶功能（大运流年/十神分析）- 15-20 小时
- [ ] 社交功能（搭配分享社区）- 20-30 小时
- [ ] 移动端深度优化（PWA 离线缓存）- 10-15 小时
- [ ] 国际化支持 - 10-15 小时

---

## 📞 联系方式

- **GitHub**: https://github.com/jeankeim/shunyishang
- **作者**: Ming Yang
- **License**: MIT

---

*最后更新: 2026-04-11*  
*项目阶段: 生产环境运行，核心功能 90% 完成*
