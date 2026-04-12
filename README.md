# 五行穿搭推荐系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue.svg" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Next.js-14-black.svg" alt="Next.js 14">
  <img src="https://img.shields.io/badge/FastAPI-0.104-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-15-blue.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/pgvector-0.5-orange.svg" alt="pgvector">
</p>

<p align="center">
  <b>基于八字命理和五行理论的智能穿搭推荐系统</b>
</p>

---

## 项目简介

五行穿搭推荐系统是一个结合传统中国命理学与现代AI技术的智能穿搭推荐平台。系统通过分析用户的生辰八字，计算五行喜用神，结合天气、场景等因素，为用户推荐最适合的穿搭方案。

### 核心功能

- **八字命理分析**: 根据生辰八字计算五行强弱、喜用神
- **智能穿搭推荐**: 基于五行理论推荐适合的衣物颜色和材质
- **天气感知**: 结合实时天气数据，推荐适合当前天气的穿搭
- **用户衣橱**: 管理个人衣物，支持AI自动识别衣物属性
- **多模态交互**: 支持图片上传、虚拟试衣、分享海报

---

## 技术栈

### 后端
- **FastAPI**: 高性能Python Web框架
- **PostgreSQL + pgvector**: 关系型数据库 + 向量扩展
- **Redis**: 缓存与会话存储
- **LangGraph**: AI Agent 状态机框架
- **OpenAI API**: 大语言模型接口
- **Sentence Transformers**: 文本Embedding生成 (BGE-M3)

### 前端
- **Next.js 14**: React 全栈框架
- **TypeScript**: 类型安全的JavaScript
- **Tailwind CSS**: 原子化CSS框架
- **Zustand**: 轻量级状态管理
- **Recharts**: 数据可视化（五行雷达图）

### AI/ML
- **CLIP**: 图片Embedding模型
- **RAG**: 检索增强生成
- **向量搜索**: 基于余弦相似度的语义搜索

### 运维
- **Docker**: 容器化部署
- **Docker Compose**: 多服务编排
- **Prometheus + Grafana**: 监控告警
- **Nginx**: 反向代理

---

## 项目结构

```
wuxing-fashion/
├── apps/
│   ├── api/                    # FastAPI 后端
│   │   ├── core/              # 核心配置（数据库、缓存、安全）
│   │   ├── models/            # 数据模型
│   │   ├── routers/           # API 路由
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── services/          # 业务逻辑
│   │   └── main.py            # 应用入口
│   └── web/                    # Next.js 前端
│       ├── app/               # 页面路由
│       ├── components/        # React 组件
│       ├── lib/               # 工具函数
│       ├── store/             # 状态管理
│       └── types/             # TypeScript 类型
├── packages/
│   ├── ai_agents/             # LangGraph AI Agent
│   │   ├── nodes.py          # 推荐流程节点
│   │   ├── prompts/          # AI Prompt模板
│   │   └── utils.py          # 工具函数
│   ├── db/                    # 数据库工具
│   └── utils/                 # 通用工具
├── data/
│   ├── seeds/                 # 种子数据
│   └── standards/             # 五行配置标准
├── scripts/                   # 脚本工具
├── tests/                     # 测试文件
├── TASKS/                     # 任务文档
│   ├── WEEK_01_DATA_FOUNDATION/
│   ├── WEEK_02_BACKEND_BRAIN/
│   ├── WEEK_03_FRONTEND_CORE/
│   ├── WEEK_04_USER_WARDROBE/
│   ├── WEEK_05_AI_ENHANCEMENT/
│   ├── WEEK_06_DEPLOY_OPTIMIZE/
│   ├── WEEK_07_SCENE_OPTIMIZATION/
│   └── WEEK_07_5_MOBILE_RESPONSIVE/  # 🔴 紧急: 移动端适配
├── docker-compose.yml         # 开发环境配置
├── docker-compose.prod.yml    # 生产环境配置
└── README.md                  # 项目说明
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (with pgvector)
- Redis 7+
- Docker & Docker Compose (推荐)

### 方式一：Docker Compose（推荐）

1. **克隆项目**
```bash
git clone https://github.com/yourusername/wuxing-fashion.git
cd wuxing-fashion
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填写必要的API密钥
```

3. **启动服务**
```bash
docker-compose up -d
```

4. **访问服务**
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 方式二：本地开发

#### 后端启动

1. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动服务**
```bash
cd apps/api
uvicorn main:app --reload --port 8000
```

#### 前端启动

1. **安装依赖**
```bash
cd apps/web
npm install
```

2. **启动开发服务器**
```bash
npm run dev
```

3. **访问**
打开浏览器访问 http://localhost:3000
![alt text](image.png)
![alt text](image-3.png)
![alt text](image-2.png)

---

## 已完成功能

### Week 1: 数据基础设施 ✅
- [x] Docker Compose 环境搭建
- [x] PostgreSQL + pgvector 数据库
- [x] 完整表结构设计
- [x] 100+条种子数据
- [x] 向量索引配置
- [x] ETL数据管道

### Week 2: 后端智能大脑 ✅
- [x] FastAPI 框架搭建
- [x] JWT 用户认证
- [x] 八字计算API
- [x] 天气查询API
- [x] LangGraph AI Agent
- [x] 向量检索与五行匹配
- [x] SSE 流式响应

### Week 3: 前端核心界面 ✅
- [x] Next.js 项目搭建
- [x] 五行雷达图可视化
- [x] 八字输入与农历转换
- [x] 天气场景选择器
- [x] 流式聊天界面
- [x] 浏览器自动定位
- [x] 和风天气API集成

### Week 4: 用户衣橱系统 ✅
- [x] 衣橱CRUD管理
- [x] AI智能打标
- [x] 简化输入流程
- [x] 三种推荐模式
- [x] 用户资料管理
- [x] 自动八字分析
- [x] 资料优先模式

---

## 开发计划

### Week 5: AI 多模态增强 ⏳
- [ ] 图片上传与Embedding（CLIP模型）
- [ ] 虚拟试衣Mock（Canvas合成）
- [ ] 分享海报生成（html2canvas）

### Week 6: 部署与优化 ⏳
- [ ] 性能调优（数据库、缓存、查询）
- [ ] Docker Compose 生产配置
- [ ] 生产环境部署

---

## API 文档

启动后端服务后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

主要接口：
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/bazi/calculate` - 八字计算
- `POST /api/v1/recommend` - 穿搭推荐
- `POST /api/v1/recommend/stream` - 流式推荐
- `GET /api/v1/weather` - 天气查询
- `GET /api/v1/wardrobe` - 获取衣橱

---

## 配置说明

### 环境变量

创建 `.env` 文件，配置以下变量：

```bash
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/wuxing

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key

# OpenAI
OPENAI_API_KEY=sk-xxx

# 和风天气
QWEATHER_API_KEY=xxx

# 高德地图
AMAP_API_KEY=xxx
```

---

## 测试

### 运行测试

```bash
# 后端测试
pytest tests/ -v

# 前端测试
cd apps/web
npm test
```

### 性能测试

```bash
# 使用 k6 进行负载测试
k6 run scripts/load_test.js
```

---

## 部署

### 生产环境部署

1. **配置生产环境变量**
```bash
cp .env.prod.example .env.prod
# 编辑 .env.prod
```

2. **构建并启动**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **查看日志**
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

详细部署文档请参考 [DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 监控

系统集成了 Prometheus + Grafana 监控：

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

监控指标包括：
- API 响应时间
- 数据库查询性能
- 缓存命中率
- 系统资源使用

---

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 联系方式

- 项目主页: https://github.com/yourusername/wuxing-fashion
- 问题反馈: https://github.com/yourusername/wuxing-fashion/issues
- 邮箱: your.email@example.com

---

<p align="center">
  Made with ❤️ and ☯️
</p>
