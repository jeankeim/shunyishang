# 验收标准: 推荐 Agent 状态机 (03_LANGGRAPH_AGENT)

**任务**: LangGraph 推荐 Agent  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 文件结构验证

- [ ] `packages/ai-agents/` 目录下所有文件存在
- [ ] `prompts/` 子目录及 2 个模板文件存在

**验证命令**：
```bash
find packages/ai-agents -type f | sort
```

**预期输出包含**：
```
packages/ai-agents/__init__.py
packages/ai-agents/state.py
packages/ai-agents/nodes.py
packages/ai-agents/graph.py
packages/ai-agents/prompts/__init__.py
packages/ai-agents/prompts/analyzer.txt
packages/ai-agents/prompts/generator.txt
```

---

### 2. Graph 编译验证

- [ ] LangGraph 状态机可成功编译，无 ImportError

**验证命令**：
```bash
source .venv/bin/activate
PYTHONPATH=. python3 -c "
from packages.ai_agents.graph import app
print('Graph 类型:', type(app))
print('Graph 编译 OK')
"
```

**预期输出**：不报错，打印 Graph 类型信息

---

### 3. Agent 全流程冒烟测试（无八字）

- [ ] 仅凭场景描述，能完成全流程推荐

**验证命令**：
```bash
PYTHONPATH=. python3 scripts/test_agent_flow.py --mode smoke
```

**test_agent_flow.py 测试用例 1（无八字）**：
```python
input_data = {
    "user_input": "明天要去面试，想显得专业干练",
    "scene": None,
    "bazi_input": None,
    "chat_history": []
}
```

**验收要求**：
- [ ] `final_response.analysis.target_elements` 包含 "金"
- [ ] `final_response.items` 长度 5（或数据库中不足 5 条时 ≥ 1）
- [ ] 所有返回物品的 `item_code` 在数据库中真实存在
- [ ] `final_response.reason` 字符数 > 50
- [ ] 全流程耗时 < 10 秒（不含 LLM 网络延迟则 < 2 秒）

---

### 4. Agent 全流程测试（含八字）

- [ ] 传入八字时，推荐结果体现喜用神偏向

**验证命令**：
```bash
PYTHONPATH=. python3 scripts/test_agent_flow.py --mode bazi
```

**test_agent_flow.py 测试用例 2（含八字）**：
```python
input_data = {
    "user_input": "周末想去公园散步，穿得自然随性",
    "scene": "日常",
    "bazi_input": {
        "birth_year": 1990,
        "birth_month": 7,
        "birth_day": 15,
        "birth_hour": 12,
        "gender": "女"
    },
    "chat_history": []
}
```

**验收要求**：
- [ ] `final_response.analysis.bazi_reasoning` 非空
- [ ] `final_response.analysis.target_elements` 与八字喜用神有交集
- [ ] 推荐物品与喜用五行有关联

---

### 5. 加权排序验证

- [ ] `retrieved_items` 中五行匹配的物品排在前面

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.ai_agents.nodes import retrieve_items_node
from packages.ai_agents.state import AgentState

state = AgentState(
    user_input='想穿黑色系的',
    scene=None,
    bazi_input=None,
    bazi_result=None,
    intent_result=None,
    target_elements=['水'],  # 水→黑蓝
    search_query='黑色深蓝色服装',
    retrieved_items=[],
    final_response={},
    error=None,
    chat_history=[]
)
result = retrieve_items_node(state)
items = result['retrieved_items']
print('返回物品数:', len(items))
for item in items:
    print(f\"  {item['name']} | 五行:{item['primary_element']} | 最终分:{item['final_score']:.3f}\")
# 验证五行匹配物品的分数更高
wuxing_matched = [i for i in items if i['primary_element'] == '水']
if wuxing_matched:
    max_unmatched = max((i['final_score'] for i in items if i['primary_element'] != '水'), default=0)
    min_matched = min(i['final_score'] for i in wuxing_matched)
    print(f'五行匹配最低分({min_matched:.3f}) vs 不匹配最高分({max_unmatched:.3f})')
print('加权排序验证完成')
"
```

---

### 6. 反幻觉验证

- [ ] 推荐理由中不出现数据库不存在的物品名

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.ai_agents.nodes import generate_advice_node
# 伪造一个只有2件衣服的检索结果，验证 LLM 不会编造第3件
print('反幻觉验证：仅传入2件物品，观察LLM输出...')
# （实际测试在 test_agent_flow.py 中实现）
print('请通过 test_agent_flow.py 的完整输出手动检查')
"
```

**手动检查要求**：
- [ ] `final_response.reason` 中提到的具体衣物名称，均出现在 `final_response.items` 列表中
- [ ] 无明显凭空捏造的物品（如"米白色羊绒大衣"但数据库中无此物品）

---

### 7. 错误处理验证

- [ ] 数据库查询无结果时，`state.error` 被正确设置

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.ai_agents.nodes import retrieve_items_node
from packages.ai_agents.state import AgentState

# 用一个极不可能匹配的查询
state = AgentState(
    user_input='test',
    scene=None,
    bazi_input=None,
    bazi_result=None,
    intent_result=None,
    target_elements=['金'],
    search_query='zzzzzzz极端测试用例不存在的服装',
    retrieved_items=[],
    final_response={},
    error=None,
    chat_history=[]
)
result = retrieve_items_node(state)
print('items数量:', len(result.get('retrieved_items', [])))
print('error:', result.get('error'))
# 即使无结果也不应抛出异常
print('错误处理验证 OK')
"
```

---

### 8. scripts/test_agent_flow.py 验证

- [ ] 脚本存在且可直接运行

```bash
PYTHONPATH=. python3 scripts/test_agent_flow.py
```

**预期输出格式**：
```
===== LangGraph Agent 全流程测试 =====

[测试1] 无八字 - 面试场景
  ✅ 意图推断: 金,水
  ✅ 检索到 5 件物品
  ✅ 推荐理由生成完成 (xxx字)
  ✅ 全流程耗时: 3.2s

[测试2] 含八字 - 日常场景
  ✅ 八字计算: 甲木日元，月令火旺
  ✅ 喜用神: 水,木
  ✅ 检索到 5 件物品
  ✅ 全流程耗时: 4.1s

===== 所有测试通过 =====
```

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 文件结构完整 | ⬜ | |
| Graph 编译成功 | ⬜ | |
| 无八字全流程通过 | ⬜ | |
| 含八字全流程通过 | ⬜ | |
| 加权排序生效 | ⬜ | |
| 反幻觉检验通过 | ⬜ | |
| 错误处理正常 | ⬜ | |
| 测试脚本可运行 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________
