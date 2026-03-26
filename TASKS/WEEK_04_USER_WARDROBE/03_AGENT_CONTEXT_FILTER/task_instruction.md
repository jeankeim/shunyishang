# 任务 3: Agent 上下文过滤 (03_AGENT_CONTEXT_FILTER)

**优先级**: 🔴 高  
**预估时间**: 3-4 小时  
**依赖**: Task 1-2 完成

---

## 📋 任务目标

改造推荐 Agent，支持三种检索模式：
- **模式 A（公有库）**: 从公共种子库检索，标记"🛒 建议购入"
- **模式 B（私有衣橱）**: 仅从用户衣橱检索，标记"🏠 自有"
- **模式 C（混合推荐）**: 优先用户衣橱，不足时补充公有库建议

---

## 🔧 执行步骤

### 步骤 1: 扩展 Agent State

修改 `packages/ai_agents/state.py`：

```python
class AgentState(TypedDict):
    user_input: str
    scene: Optional[str]
    top_k: int
    user_id: Optional[str]
    retrieval_mode: str  # 'public' | 'wardrobe' | 'hybrid'
    wardrobe_item_ids: Optional[List[str]]
    target_elements: Optional[List[str]]
    retrieved_items: Optional[List[Dict]]
    item_sources: Optional[Dict[str, str]]  # {'item_id': 'wardrobe'/'public'}
    final_response: Optional[str]
    error: Optional[str]
```

---

### 步骤 2: 获取用户衣橱数据

创建 `packages/ai_agents/wardrobe_client.py`：

```python
class WardrobeClient:
    async def get_wardrobe_items(self, user_id: str) -> List[Dict]:
        """获取用户衣橱物品列表"""
        # 查询 user_wardrobe 表
        
    async def get_wardrobe_item_ids(self, user_id: str) -> List[str]:
        """获取用户衣橱物品ID列表"""
```

---

### 步骤 3: 修改检索节点

修改 `packages/ai_agents/nodes.py`：

```python
async def _vector_search_wardrobe(
    user_id: str,
    query_embedding: List[float],
    target_elements: List[str],
    limit: int = 20
) -> List[Dict]:
    """从用户衣橱检索
    
    ⚠️ 必须在 WHERE 子句中强制加上 user_id 过滤！
    """
    query = """
        SELECT item_id, name, category, primary_element,
               1 - (embedding <=> $2) as similarity
        FROM user_wardrobe
        WHERE user_id = $1  -- 权限控制！
          AND is_active = TRUE
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $2
        LIMIT $3
    """


async def retrieve_items_node(state: AgentState) -> Dict:
    """物品检索节点 - 支持三种模式"""
    retrieval_mode = state.get('retrieval_mode', 'public')
    
    if retrieval_mode == 'wardrobe':
        # 仅从用户衣橱检索
        items = await _vector_search_wardrobe(user_id, ...)
    elif retrieval_mode == 'hybrid':
        # 先查衣橱，不足补充公共库
        items = await _vector_search_wardrobe(user_id, ...)
        if len(items) < top_k:
            public_items = await _vector_search_public(...)
            items.extend(public_items)
    else:  # public
        items = await _vector_search_public(...)
```

---

### 步骤 4: 更新生成节点

根据物品来源使用不同语气：

```python
# 用户拥有的衣物 -> "您可以穿您拥有的XXX"
# 建议购入的衣物 -> "您可以考虑购入XXX"
```

### 步骤 5: 前端模式切换组件 ✅ 已完成 (2026-03-26)

创建 `apps/web/components/features/ChatInterface.tsx` 中的 `RetrievalModeToggle` 组件：

```typescript
// 推荐模式切换组件
function RetrievalModeToggle() {
  const { retrievalMode, setRetrievalMode } = useChatStore()
  
  return (
    <div className="flex items-center gap-2">
      <span>推荐范围</span>
      <div className="flex gap-1">
        {['public', 'wardrobe', 'hybrid'].map((mode) => (
          <button
            key={mode}
            onClick={() => setRetrievalMode(mode)}
            className={isActive ? 'active' : ''}
          >
            {mode === 'public' && '🛒 全局库'}
            {mode === 'wardrobe' && '🏠 我的衣橱'}
            {mode === 'hybrid' && '✨ 智能混合'}
          </button>
        ))}
      </div>
    </div>
  )
}
```

**状态管理**: `apps/web/store/chat.ts`
- 添加 `retrievalMode: RetrievalMode` 状态
- 添加 `setRetrievalMode` 方法
- 持久化到 localStorage

**API 对接**: `apps/web/lib/api.ts`
- `RecommendRequest` 接口添加 `retrieval_mode` 字段
- `ChatInterface` 组件发送请求时传入当前模式

---

## 📁 输出文件清单

| 文件路径 | 操作 | 状态 |
|:---|:---|:---:|
| `packages/ai_agents/state.py` | 更新 | ✅ |
| `packages/ai_agents/wardrobe_client.py` | 新建 | ✅ |
| `packages/ai_agents/nodes.py` | 更新 | ✅ |
| `apps/api/routers/recommend.py` | 更新 | ✅ |
| `apps/web/store/chat.ts` | 更新（添加模式状态） | ✅ 2026-03-26 |
| `apps/web/components/features/ChatInterface.tsx` | 添加模式切换 UI | ✅ 2026-03-26 |

---

## ✅ 实现验证

- [x] 后端 API 支持 `retrieval_mode` 参数
- [x] 前端 Store 管理模式状态
- [x] 模式切换 UI 组件
- [x] 模式状态持久化
- [x] 推荐请求携带模式参数

---

## ⚠️ 注意事项

1. **权限控制**: 向量搜索必须加 `WHERE user_id = ?`，防止数据越权
2. **冷启动处理**: 新用户衣橱为空时，给出友好提示
3. **混合模式阈值**: 相似度低于 0.6 时才补充公共库
4. **来源标记**: 每个 item 必须标记 source
5. **模式持久化**: 用户选择的模式保存在 localStorage，刷新后保留
