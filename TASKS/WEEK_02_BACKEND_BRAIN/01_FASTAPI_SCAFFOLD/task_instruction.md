# 任务 1: FastAPI 骨架搭建 (01_FASTAPI_SCAFFOLD)

**优先级**: 🔴 高  
**预估时间**: 2-3 小时  
**依赖**: Week 1 数据库已运行（`wuxing-db` 容器 healthy）

---

## 📋 任务目标

搭建 FastAPI 后端项目骨架，配置 psycopg2 连接池，定义 Pydantic 请求/响应模型，暴露健康检查接口。本任务是 Week 2 所有后续任务的基础。

---

## 🔧 执行步骤

### 步骤 1: 安装新依赖

在 `requirements.txt` 中追加以下依赖（保留 Week 1 已有依赖）：

```
# Week 2 新增
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic-settings>=2.0.0
python-multipart>=0.0.9
openai>=1.0.0          # 阿里百炼兼容 OpenAI SDK
cnlunar>=0.0.4         # 八字/农历转换
langgraph>=0.1.0
langchain-core>=0.2.0
```

安装命令（使用清华镜像）：
```bash
source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir \
  fastapi uvicorn[standard] pydantic-settings python-multipart \
  openai cnlunar langgraph langchain-core
```

---

### 步骤 2: 创建目录结构

在 `apps/api/` 下创建以下结构：

```
apps/api/
├── __init__.py
├── main.py                 # 应用入口
├── core/
│   ├── __init__.py
│   ├── config.py           # 环境变量配置
│   └── database.py         # psycopg2 连接池
├── schemas/
│   ├── __init__.py
│   ├── request.py          # 请求体模型
│   └── response.py         # 响应体模型
└── routers/
    ├── __init__.py
    └── recommend.py        # 推荐路由（本任务创建占位，Task 4 实现）
```

---

### 步骤 3: `apps/api/core/config.py`

使用 `pydantic-settings` 从 `.env` 文件读取配置。

**必须包含的配置项**：

| 字段名 | 类型 | 说明 |
|:---|:---|:---|
| `DATABASE_URL` | str | `postgresql://wuxing_user:wuxing_password@localhost:5432/wuxing_db` |
| `DASHSCOPE_API_KEY` | str | 阿里百炼 API Key |
| `QWEN_MODEL` | str | 默认 `qwen-plus` |
| `APP_ENV` | str | `development` |
| `APP_DEBUG` | bool | `True` |
| `CORS_ORIGINS` | list[str] | `["*"]`（开发阶段允许所有） |

> ⚠️ 同时更新 `.env.example` 增加 `DASHSCOPE_API_KEY` 和 `QWEN_MODEL` 字段

---

### 步骤 4: `apps/api/core/database.py`

使用 `psycopg2.pool.ThreadedConnectionPool` 管理连接池（与 Week 1 保持一致，不引入 SQLAlchemy）。

**必须实现的内容**：

1. 初始化连接池：`minconn=2, maxconn=10`
2. `get_connection()` 上下文管理器：自动归还连接
3. `check_db_health()` 函数：执行 `SELECT 1` 验证连接

```python
# 接口示意（不要直接输出代码，按此规范实现）
def get_connection() -> Generator:
    """上下文管理器，自动从连接池获取和归还连接"""
    ...

def check_db_health() -> bool:
    """执行 SELECT 1 验证数据库连通性，返回 True/False"""
    ...
```

---

### 步骤 5: `apps/api/schemas/request.py`

定义推荐请求体，使用 Pydantic v2：

```python
# 接口规范（按此设计实现）
class BaziInput(BaseModel):
    birth_year: int           # 出生年（公历）
    birth_month: int          # 出生月
    birth_day: int            # 出生日
    birth_hour: int           # 出生时（0-23）
    gender: str               # "男" | "女"

class RecommendRequest(BaseModel):
    query: str                # 用户需求描述，如"明天要去面试"
    scene: str | None = None  # 场景，如"面试"、"约会"、"日常"
    bazi: BaziInput | None = None  # 八字信息（可选）
    top_k: int = 5            # 返回推荐数量
```

---

### 步骤 6: `apps/api/schemas/response.py`

定义推荐响应体（用于文档说明，SSE 实际格式见 Task 4）：

```python
class ItemRecommendation(BaseModel):
    item_code: str
    name: str
    category: str
    primary_element: str
    secondary_element: str | None
    score: float              # 加权最终分数

class RecommendResponse(BaseModel):
    analysis: dict            # 五行分析结果
    items: list[ItemRecommendation]
    reason: str               # 推荐理由
```

---

### 步骤 7: `apps/api/main.py`

**必须包含**：

1. 创建 FastAPI 应用，设置 title/version
2. 挂载 CORS 中间件（`allow_origins=settings.CORS_ORIGINS`）
3. 挂载推荐路由：`app.include_router(recommend_router, prefix="/api/v1")`
4. **健康检查接口**：

```
GET /health
响应：{"status": "ok", "db": "connected", "env": "development"}
若数据库连接失败：{"status": "error", "db": "disconnected"}，状态码 503
```

5. 根路径重定向到 `/docs`

---

### 步骤 8: `apps/api/routers/recommend.py`（占位）

本任务只创建路由占位，Task 4 实现具体逻辑：

```python
# 仅创建路由骨架，返回 501 Not Implemented
POST /api/v1/recommend/stream
```

---

### 步骤 9: 更新 `.env.example`

追加以下内容：

```bash
# === 阿里百炼 LLM 配置 ===
DASHSCOPE_API_KEY=sk-xxx
QWEN_MODEL=qwen-plus

# === FastAPI 配置 ===
APP_ENV=development
APP_DEBUG=true
APP_PORT=8000
CORS_ORIGINS=["*"]
```

---

## 📁 输出文件清单

| 文件路径 | 状态 |
|:---|:---|
| `apps/api/__init__.py` | 新建 |
| `apps/api/main.py` | 新建 |
| `apps/api/core/__init__.py` | 新建 |
| `apps/api/core/config.py` | 新建 |
| `apps/api/core/database.py` | 新建 |
| `apps/api/schemas/__init__.py` | 新建 |
| `apps/api/schemas/request.py` | 新建 |
| `apps/api/schemas/response.py` | 新建 |
| `apps/api/routers/__init__.py` | 新建 |
| `apps/api/routers/recommend.py` | 新建（占位） |
| `requirements.txt` | 更新（追加依赖） |
| `.env.example` | 更新（追加配置项） |

---

## ⚠️ 注意事项

1. **Python 路径**：从项目根目录运行 `uvicorn apps.api.main:app`，需确保 `apps/` 可被 Python 识别（可在根目录创建空 `__init__.py` 或使用 `PYTHONPATH=.`）
2. **连接池复用**：连接池在应用启动时初始化一次，通过 `lifespan` 事件管理生命周期
3. **不引入 SQLAlchemy**：保持与 Week 1 psycopg2 风格一致
4. **Type Hints**：所有函数必须有完整类型注解
