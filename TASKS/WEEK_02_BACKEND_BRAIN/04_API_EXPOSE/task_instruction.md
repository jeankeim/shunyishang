# 任务 4: 暴露 SSE 流式 API (04_API_EXPOSE)

**优先级**: 🔴 高  
**预估时间**: 2-3 小时  
**依赖**: Task 1 + Task 3（Agent 全流程已通过测试）

---

## 📋 任务目标

将 LangGraph Agent 封装为 Server-Sent Events (SSE) 流式 HTTP 接口，实现 3 段式结构化输出（分析阶段 → 推荐物品 → 逐字推荐理由）。前端可分阶段渲染，提升用户体验。

---

## 🔧 执行步骤

### 步骤 1: SSE 协议规范

**SSE 数据格式**（每条消息格式严格遵守）：
```
data: {JSON}\n\n
```

**3 段式输出结构**：

#### 第 1 段：分析结果（1 条消息）
```json
{
  "type": "analysis",
  "data": {
    "target_elements": ["金", "水"],
    "bazi_reasoning": "日元甲木，午月火旺，木被火泄...",
    "intent_reasoning": "关键词'面试'→金属性",
    "scene": "面试"
  }
}
```

#### 第 2 段：推荐物品列表（1 条消息）
```json
{
  "type": "items",
  "data": [
    {
      "item_code": "ITEM_004",
      "name": "白色高领羊绒衫",
      "category": "上装",
      "primary_element": "金",
      "secondary_element": null,
      "final_score": 0.782
    }
  ]
}
```

#### 第 3 段：逐字推荐理由（N 条消息，每条 1 个 token）
```json
{"type": "token", "data": "根"}
{"type": "token", "data": "据"}
{"type": "token", "data": "您"}
...
```

#### 结束消息（1 条）
```json
{"type": "done", "data": null}
```

#### 错误消息（出错时替代所有后续消息）
```json
{"type": "error", "data": "错误描述信息"}
```

---

### 步骤 2: 实现 `apps/api/routers/recommend.py`

替换 Task 1 中的占位实现。

**接口定义**：
```
POST /api/v1/recommend/stream
Content-Type: application/json
Accept: text/event-stream

请求体：RecommendRequest（来自 apps/api/schemas/request.py）
响应：StreamingResponse，媒体类型 text/event-stream
```

**SSE 生成器函数规范**：

```python
async def generate_sse(request: RecommendRequest):
    """
    生成 SSE 事件流
    1. 构建 AgentState 初始值
    2. 运行 analyze_intent_node 和 retrieve_items_node（同步）
    3. yield 分析结果（type=analysis）
    4. yield 物品列表（type=items）
    5. 运行 generate_advice_node（流式），逐 token yield
    6. yield done
    """
```

**重要实现细节**：

1. **编码必须显式指定 UTF-8**：
   ```python
   yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
   ```

2. **StreamingResponse 设置媒体类型**：
   ```python
   return StreamingResponse(
       generate_sse(request),
       media_type="text/event-stream",
       headers={
           "Cache-Control": "no-cache",
           "X-Accel-Buffering": "no"  # 禁止 nginx 缓冲
       }
   )
   ```

3. **LangGraph 流式调用**：千问的 `stream=True` 模式在 `generate_advice_node` 中已实现，Task 4 需将其 token 流转为 SSE token 消息

4. **Agent 前两个节点非流式**：`analyze_intent` 和 `retrieve_items` 同步执行，完成后一次性发送 `analysis` 和 `items` 消息

---

### 步骤 3: 错误处理规范

| 错误情形 | HTTP 状态码 | SSE 响应 |
|:---|:---:|:---|
| 请求体 JSON 解析失败 | 422 | FastAPI 默认 ValidationError |
| 数据库连接失败 | 200 | `{"type":"error","data":"数据库连接失败，请稍后重试"}` |
| LLM API 超时（>30s）| 200 | `{"type":"error","data":"AI 服务暂时不可用，已为您提供物品列表"}` + `done` |
| Agent 内部错误 | 200 | `{"type":"error","data":"推荐服务异常：{state.error}"}` + `done` |

> ⚠️ 注意：SSE 连接建立后，状态码已固定为 200，错误只能通过 SSE 消息传递

---

### 步骤 4: `apps/api/main.py` 补充

在 `main.py` 添加请求日志中间件：

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    return response
```

---

### 步骤 5: 更新 `.env` 和 `.env.example`

确认 `.env` 中已填入真实的 `DASHSCOPE_API_KEY`（不要提交到 git）：

```bash
# 检查 .gitignore 是否包含 .env
cat .gitignore | grep ".env"
# 如果没有，添加：echo ".env" >> .gitignore
```

---

## 📁 输出文件清单

| 文件路径 | 说明 |
|:---|:---|
| `apps/api/routers/recommend.py` | 替换占位实现，实现完整 SSE 路由 |
| `apps/api/main.py` | 追加请求日志中间件 |
| `.gitignore` | 确认 `.env` 已加入忽略 |

---

## ⚠️ 注意事项

1. **UTF-8 编码**：`json.dumps()` 必须使用 `ensure_ascii=False`，否则中文变为 `\uXXXX` 转义
2. **SSE 双换行**：每条消息末尾必须是 `\n\n`（两个换行），否则浏览器不识别为完整消息
3. **生成器与 async**：SSE 生成器必须是 `async def`，内部的同步 psycopg2 调用需用 `asyncio.get_event_loop().run_in_executor()` 包裹
4. **LLM API Key 环境**：千问调用需要网络访问 `dashscope.aliyuncs.com`，开发时确保网络可达
5. **Postman 测试 SSE**：设置 `Accept: text/event-stream`，在 Response Body 查看流式输出
