# 任务 3: 构建推荐 Agent 状态机 (03_LANGGRAPH_AGENT)

**优先级**: 🔴 极高（本周核心任务）  
**预估时间**: 4-6 小时  
**依赖**: Task 1（FastAPI 骨架）+ Task 2（八字工具库）

---

## 📋 任务目标

使用 LangGraph 构建有状态的推荐工作流，替代简单的向量搜索。Agent 能够理解用户意图（结合八字）、增强向量检索（加权排序）、调用千问生成有理有据的推荐理由。**严格禁止幻觉：推荐物品必须来自数据库真实记录。**

---

## 🔧 执行步骤

### 步骤 1: 目录结构

```
packages/ai-agents/
├── __init__.py
├── state.py            # AgentState 定义
├── graph.py            # StateGraph 编译
├── nodes.py            # 4 个节点函数
└── prompts/
    ├── __init__.py
    ├── analyzer.txt    # 意图分析 Prompt 模板
    └── generator.txt   # 推荐理由生成 Prompt 模板
```

---

### 步骤 2: `packages/ai-agents/state.py`

使用 `TypedDict` 定义 Agent 状态：

```python
# 接口规范
class AgentState(TypedDict):
    # ─── 输入层 ───
    user_input: str                     # 用户原始描述
    scene: str | None                   # 提取的场景
    bazi_input: dict | None             # 原始八字输入

    # ─── 分析层 ───
    bazi_result: dict | None            # Task 2 八字计算结果
    intent_result: dict | None          # 意图推断结果
    target_elements: list[str]          # 最终推荐五行（合并后）

    # ─── 检索层 ───
    search_query: str                   # 优化后的向量搜索文本
    retrieved_items: list[dict]         # 加权排序后的 Top5 物品

    # ─── 输出层 ───
    final_response: dict                # 格式化的最终响应
    error: str | None                   # 错误信息（有则终止流程）
    chat_history: list[dict]            # 可选：多轮对话历史
```

---

### 步骤 3: `packages/ai-agents/prompts/`

#### analyzer.txt（意图分析 Prompt 模板）

用于生成增强的向量搜索文本：

```
你是一位精通中国五行理论的时尚顾问。

用户需求：{user_input}
当前场景：{scene}

五行喜用神分析：
{bazi_reasoning}

规则推断的目标五行：{rule_elements}
对应颜色方向：{element_colors}

请根据以上信息，生成一段50字以内的衣物搜索描述文本，要求：
1. 包含五行对应的颜色词（如：黑色、深蓝、白色等）
2. 包含场景风格词（如：职业、优雅、随性等）
3. 语言自然，像是在描述一件衣服

只输出搜索描述文本，不要解释。
```

#### generator.txt（推荐理由生成 Prompt 模板）

用于生成最终推荐理由：

```
你是一位精通中国五行理论的时尚顾问，请为用户提供穿搭建议。

用户需求：{user_input}

五行分析结论：
- 喜用五行：{target_elements}
- 推理：{bazi_reasoning}

数据库中找到的推荐衣物（请必须引用这些真实物品）：
{items_list}

请生成一段个性化穿搭建议，要求：
1. 必须提及上述物品中的至少2件，使用其真实名称
2. 结合五行理论解释为什么适合
3. 给出一个完整的搭配组合建议
4. 语气亲切，200字以内

重要：只能推荐上方列表中的物品，严禁编造不存在的衣物。
```

---

### 步骤 4: `packages/ai-agents/nodes.py`

#### Node A: `analyze_intent_node`

**输入**：`state.user_input`, `state.bazi_input`, `state.scene`  
**输出**：更新 `state.bazi_result`, `state.intent_result`, `state.target_elements`, `state.search_query`

**执行逻辑**：
1. 如果有 `bazi_input`，调用 `calculate_bazi()` 计算喜用神
2. 调用 `infer_elements_from_text(user_input)` 做规则意图推断
3. 提取场景 `extract_scene_from_text(user_input)`
4. 调用 `merge_recommendations()` 合并得到 `target_elements`
5. **判断是否需要 LLM 兜底**：
   - 如果 `intent_result.method == "rule"` → 规则已足够，直接构建 `search_query`
   - 如果 `intent_result.method == "llm_needed"` → 调用千问补充意图推断
6. 调用千问，使用 `analyzer.txt` 模板生成增强的 `search_query`

**千问调用规范**（兼容 OpenAI SDK）：
```python
from openai import OpenAI

client = OpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model=settings.QWEN_MODEL,  # "qwen-plus"
    messages=[{"role": "user", "content": prompt}],
    max_tokens=100
)
```

---

#### Node B: `retrieve_items_node`（工具节点，不调用 LLM）

**输入**：`state.search_query`, `state.target_elements`  
**输出**：更新 `state.retrieved_items`

**执行逻辑**（加权排序核心）：
1. 用 `state.search_query` 对数据库做向量搜索，取 **Top 20**
2. 对每条结果计算加权分数：
   ```
   wuxing_score = 0 
   if item.primary_element in target_elements → wuxing_score += 0.6
   if item.secondary_element in target_elements → wuxing_score += 0.3
   
   final_score = semantic_similarity × 0.6 + wuxing_score × 0.4
   ```
3. 按 `final_score` 降序排序，取 **Top 5**
4. 将结果存入 `state.retrieved_items`

**边缘情况处理**：
- 如果 Top 5 全部 `wuxing_score = 0`（五行完全不匹配），**自动放宽**：只用语义相似度排序重取 Top 5
- 如果查询结果为空，在 state 设置 `error = "数据库查询无结果"` 并终止

**复用 Week 1 的向量搜索 SQL**：
```sql
SELECT item_code, name, primary_element, secondary_element, category,
       attributes_detail,
       1 - (embedding <=> %s::vector) AS semantic_score
FROM items
ORDER BY embedding <=> %s::vector
LIMIT 20
```

---

#### Node C: `generate_advice_node`

**输入**：`state.user_input`, `state.bazi_result`, `state.target_elements`, `state.retrieved_items`  
**输出**：更新 `state.final_response`（推荐理由部分）

**执行逻辑**：
1. 格式化 `retrieved_items` 为文本列表（含 item_code、name、category）
2. 填充 `generator.txt` 模板
3. 调用千问生成推荐理由（**启用流式输出**，供 Task 4 的 SSE 使用）
4. **反幻觉验证**：检查生成文本中提到的物品名是否在 `retrieved_items` 中，如不在则截断并警告

---

#### Node D: `format_output_node`

**输入**：所有 state 字段  
**输出**：更新 `state.final_response`（完整结构化响应）

**输出格式**：
```python
{
    "analysis": {
        "target_elements": ["金", "水"],
        "bazi_reasoning": "日元甲木，夏月火旺...",
        "intent_reasoning": "关键词'面试'→金属性",
        "scene": "面试"
    },
    "items": [
        {
            "item_code": "ITEM_004",
            "name": "白色高领羊绒衫",
            "category": "上装",
            "primary_element": "金",
            "secondary_element": None,
            "final_score": 0.782,
            "semantic_score": 0.523,
            "wuxing_score": 0.6
        },
        ...
    ],
    "reason": "（千问生成的推荐理由文本）"
}
```

---

### 步骤 5: `packages/ai-agents/graph.py`

**图定义**：
```
START
  → analyze_intent_node
  → retrieve_items_node
  → generate_advice_node
  → format_output_node
  → END
```

**条件边**（错误处理）：
- `analyze_intent_node` 或 `retrieve_items_node` 后：如果 `state.error` 不为 None → 直接跳到 `END`

**编译**：
```python
graph = StateGraph(AgentState)
# ... 添加节点和边
app = graph.compile()  # 编译为 Runnable
```

---

## 📁 输出文件清单

| 文件路径 | 说明 |
|:---|:---|
| `packages/ai-agents/__init__.py` | 新建 |
| `packages/ai-agents/state.py` | AgentState TypedDict |
| `packages/ai-agents/nodes.py` | 4 个节点函数 |
| `packages/ai-agents/graph.py` | StateGraph 定义与编译 |
| `packages/ai-agents/prompts/__init__.py` | 新建 |
| `packages/ai-agents/prompts/analyzer.txt` | 意图分析 Prompt |
| `packages/ai-agents/prompts/generator.txt` | 理由生成 Prompt |
| `scripts/test_agent_flow.py` | Agent 全流程测试脚本 |

---

## ⚠️ 注意事项

1. **拒绝幻觉（最高优先级）**：`generate_advice_node` 必须验证输出文本中的物品名，只允许引用 `retrieved_items` 中存在的物品
2. **流式输出**：`generate_advice_node` 调用千问时使用 `stream=True`，将 token 逐个 yield 出来，供 Task 4 的 SSE 消费
3. **DASHSCOPE_API_KEY 获取**：访问 https://bailian.console.aliyun.com/ 创建 API Key，填入 `.env`
4. **LangGraph 版本**：确保 `langgraph>=0.1.0`，API 在不同版本间有差异
5. **packages 路径**：在 `packages/ai-agents/__init__.py` 中导出 `app`（编译后的 graph），供 Task 4 调用
