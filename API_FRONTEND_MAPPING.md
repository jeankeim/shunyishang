# 后端接口 → 前端调用对照表

> 路径均相对项目根目录 `/Users/mingyang/Desktop/shunyishang`

---

## 1. 推荐相关 API

| 后端接口 | 前端封装函数（`apps/web/lib/api.ts`） | 前端调用位置 |
|---------|----------------------------------------|--------------|
| `POST /api/v1/recommend/stream` | `async function* streamRecommendation(request)` | `apps/web/components/features/ChatInterface.tsx` 中：<br>– 第 5–7 行：`import { streamRecommendation } from '@/lib/api'`<br>– 第 72 行附近：`for await (const event of streamRecommendation({ ... }))` |

---

## 2. 八字 / 用户八字 API

| 后端接口 | 前端封装函数 | 前端调用位置 |
|---------|--------------|--------------|
| `POST /api/v1/bazi/calculate` | `calculateBazi(request: BaziCalculateRequest)` | 1. `apps/web/components/features/BaziInputSection.tsx`：用户在首页左侧"生辰八字"输入时调用，用于实时预览雷达图。<br>2. `apps/web/components/features/UserProfile.tsx`：在 `autoAnalyzeBazi` 中，资料保存后自动调用计算八字。 |
| `POST /api/v1/auth/bazi` | `updateUserBazi(request: BaziCalculateRequest)` | 1. `apps/web/store/user.ts`：`updateBazi` 方法中封装，供全局使用。<br>2. `apps/web/components/features/UserProfile.tsx`：`autoAnalyzeBazi` 中直接调用，用于将计算结果写回用户资料。 |

---

## 3. 认证 / 用户资料 API

| 后端接口 | 前端封装函数 | 前端调用位置 |
|---------|--------------|--------------|
| `POST /api/v1/auth/register` | `register(request: RegisterRequest)` | `apps/web/store/user.ts`：`register` 方法中使用（`apiRegister`），供登录弹窗等调用。<br>`apps/web/components/features/AuthModal.tsx`：通过 `useUserStore().register` 触发。 |
| `POST /api/v1/auth/login` | `login(request: LoginRequest)` | `apps/web/store/user.ts`：`login` / `loginWithEmail` 方法中使用（`apiLogin`）。<br>`apps/web/components/features/AuthModal.tsx`：调用 `useUserStore().login` / `loginWithEmail`。 |
| `GET /api/v1/auth/me` | `getCurrentUser()` | `apps/web/store/user.ts`：`fetchUserInfo` 中调用，用于初始化/刷新登录状态，首页、其它页面通过 `useUserStore()` 间接使用。 |
| `POST /api/v1/auth/logout` | `logout()` | `apps/web/store/user.ts`：`logout` 方法中使用（`apiLogout`），供头部或用户菜单的登出操作使用。 |
| `GET /api/v1/auth/profile` | `getUserProfile()` | `apps/web/components/features/UserProfile.tsx`：<br>– 初次打开个人资料页时拉取完整资料（第 65–77 行附近）。<br>– 更新资料成功后再调一次刷新 `fullProfile`（`refreshedProfile = await getUserProfile()`）。 |
| `PATCH /api/v1/auth/profile` | `updateProfile(request: UpdateProfileRequest)` | 1. `apps/web/store/user.ts`：`updateProfile` 方法中使用，更新全局 `user`。<br>2. `apps/web/components/features/UserProfile.tsx`：表单提交 `handleSubmit` 中直接 `await updateProfile(updateData)`，然后再自动触发八字分析。 |

---

## 4. 衣橱 / 衣物管理 API

这些接口主要通过 `apps/web/store/wardrobe.ts` 这一层被前端页面使用。

| 后端接口 | 前端封装函数 | 前端调用位置 |
|---------|--------------|--------------|
| `GET /api/v1/wardrobe/items` | `getWardrobeItems(params)` | `apps/web/store/wardrobe.ts`：`fetchItems` 中调用 `getWardrobeItems({ ...filters, limit: 100 })`，Wardrobe 页面通过 store（如 `useWardrobeStore`）间接使用。 |
| `POST /api/v1/wardrobe/items` | `addWardrobeItem(data)` | `apps/web/store/wardrobe.ts`：`addItem` 中调用，然后把新 item 插入到 `items` 列表头部。前端"添加衣物"弹窗组件通过 store 调用。 |
| `PATCH /api/v1/wardrobe/items/{item_id}` | `updateWardrobeItem(itemId, data)` | `apps/web/store/wardrobe.ts`：`updateItem` 中调用，更新本地 `items` 列表中的对应 item。 |
| `DELETE /api/v1/wardrobe/items/{item_id}` | `deleteWardrobeItem(itemId)` | `apps/web/store/wardrobe.ts`：`deleteItem` 中调用，删除后从 `items` 列表中过滤掉该 item。 |
| `POST /api/v1/wardrobe/items/preview-tagging` | `previewTagging(description, image_url?)` | `apps/web/store/wardrobe.ts`：`previewTagging` 中调用，用于"AI 预览打标"功能；添加衣物弹窗里通过 store 展示 AI 建议的五行、颜色等。 |
| `POST /api/v1/wardrobe/feedback` | `submitFeedback(data)` | `apps/web/components/features/RecommendCard.tsx`：点击"喜欢/不喜欢"按钮时调用 `submitFeedback({...})`，给推荐结果打反馈。 |

（`/api/v1/wardrobe/stats` 目前在 `lib/api.ts` 不存在封装，前端也暂无直接调用。）

---

## 5. 天气 / 五行映射 API

> 这些接口目前在前端 **没有专门的封装函数**，也没在 TS/TSX 中搜索到直接调用，逻辑主要由后端用于计算天气五行，前端只使用处理后的 `weatherElement` 结果。

| 后端接口 | 前端使用情况 |
|---------|--------------|
| `GET /api/v1/weather/weather` | 前端没有在 `apps/web/lib/api.ts` 中封装，也没有在 TS/TSX 中看到直接 fetch 调用，当前逻辑是：后端提供天气 → 五行映射能力，前端通过 `WeatherSceneSection` 这类组件传入场景与天气的五行元素，用于推荐。 |
| `GET /api/v1/weather/weather/elements` | 同上，目前未在前端直接调用，多作为后端配置/说明用。 |

---

## 6. 健康检查 API

| 后端接口 | 前端封装函数 | 前端调用位置 |
|---------|--------------|--------------|
| `GET /health` | `checkHealth()` | `apps/web/lib/api.ts` 中有封装，但在 `apps/web` 下未搜到 TS/TSX 直接调用。可以在将来用于"后端服务状态"指示灯或调试页面。 |

---

## 7. 如何使用这张表查代码

当你在 `http://localhost:8000/docs` 里看到某个接口时，可以按下面步骤快速定位前端逻辑：

1. **看接口路径 & 方法**  
   比如 `POST /api/v1/auth/profile`
2. **在表中查这一行**  
   看到对应封装函数：`updateProfile()`，位置 `apps/web/lib/api.ts`
3. **顺着看调用链**  
   - 用户资料相关 → `UserProfile.tsx` + `store/user.ts`
   - 推荐相关 → `ChatInterface.tsx` + `store/chat.ts`
   - 衣橱相关 → `store/wardrobe.ts` + `wardrobe 页面 / AddWardrobeModal`

---

# 完整调用链示例

## 示例 1: 用户资料更新 + 自动八字分析

```
用户操作
    ↓
点击"保存更改"按钮
    ↓
apps/web/components/features/UserProfile.tsx
    handleSubmit()
        ↓
    await updateProfile(updateData)  ← 调用 lib/api.ts
        ↓
    POST /api/v1/auth/profile  ← 后端接口
        ↓
    后端: apps/api/routers/auth.py:update_profile()
        ↓
    如果更新了出生信息:
        自动调用 calculate_bazi() 计算八字
        更新数据库 bazi, xiyong_elements 字段
        ↓
    返回更新后的用户资料
        ↓
    前端: UserProfile.tsx 继续执行
        ↓
    如果出生信息有变更:
        await autoAnalyzeBazi()  (内部调用 calculateBazi + updateUserBazi)
            ↓
        POST /api/v1/auth/bazi  ← 后端接口
            ↓
        后端: apps/api/routers/auth.py:update_bazi()
            ↓
        返回带八字的用户信息
            ↓
    await fetchUserInfo()  (通过 user store)
        ↓
    GET /api/v1/auth/me
        ↓
    更新全局 user 状态
        ↓
    首页 page.tsx 检测到 user.bazi 变化
        ↓
    UI 自动切换: 显示 BaziCard, 隐藏 BaziInputSection 和 FiveElementRadar
```

## 示例 2: 流式推荐（三种模式详解）

### 2.1 全局库模式（public）

```
用户操作
    ↓
在 ChatInterface 选择"全局库"模式，输入问题并发送
    ↓
apps/web/components/features/ChatInterface.tsx
    handleSendMessage()
        ↓
    构建请求参数:
        - retrieval_mode: "public"
        - user_id: undefined（不传）
        - query: 用户输入内容
        - bazi/gender/scene/weather_element: 上下文信息
        ↓
    for await (const event of streamRecommendation({...}))
        ↓
    POST /api/v1/recommend/stream  (SSE 流)
        ↓
    后端: apps/api/routers/recommend.py:recommend_stream()
        ↓
    调用 packages/ai_agents/graph.py:run_agent_stream()
        ↓
    创建初始状态: create_initial_state(retrieval_mode="public")
        ↓
    执行 retrieve_items_node(state)
        ↓
    进入 nodes.py 第 384-397 行（else 分支 - 默认公共库模式）
        ↓
    调用 _vector_search() 从公共库检索
        SQL: SELECT ... FROM items WHERE embedding IS NOT NULL ...
        条件: 性别过滤（男/女/中性）+ 天气过滤
        排序: ORDER BY embedding <=> query_vector
        返回: 标记 source="public", source_label="🛒 建议"
        ↓
    动态权重计算（语义分 + 五行匹配分）
        ↓
    分类多样性优化 _ensure_category_diversity()
        ↓
    返回检索结果到 graph.py
        ↓
    流式返回事件:
        - type: "analysis"  → 显示五行分析
        - type: "items"     → 显示推荐物品列表（全部来自公共库）
        - type: "token"    → 逐字显示推荐理由
        - type: "done"     → 结束标记
        ↓
    前端 ChatInterface 实时渲染各类型事件
```

**全局库模式特点：**
- 数据源：`items` 表（公共种子库）
- 权限：无需登录即可使用
- 过滤条件：性别匹配、天气适配
- 结果标记：🛒 建议
- 兜底策略：百搭单品 fallback

---

### 2.2 我的衣橱模式（wardrobe）

```
用户操作
    ↓
在 ChatInterface 选择"我的衣橱"模式，输入问题并发送
    ↓
apps/web/components/features/ChatInterface.tsx
    handleSendMessage()
        ↓
    检查登录状态: isAuthenticated = true
        ↓
    构建请求参数:
        - retrieval_mode: "wardrobe"
        - user_id: user.id（必需，从 useUserStore 获取）
        - query/scene/bazi/gender/weather_element: 上下文信息
        ↓
    for await (const event of streamRecommendation({...}))
        ↓
    POST /api/v1/recommend/stream  (SSE 流)
        ↓
    后端: apps/api/routers/recommend.py:recommend_stream()
        验证: request.user_id 必须存在
        ↓
    调用 packages/ai_agents/graph.py:run_agent_stream(user_id=1, retrieval_mode="wardrobe")
        ↓
    创建初始状态: create_initial_state(user_id=1, retrieval_mode="wardrobe")
        ↓
    执行 retrieve_items_node(state)
        ↓
    进入 nodes.py 第 303-337 行（wardrobe 分支）
        ↓
    【权限检查】
        if not user_id: return error("衣橱模式需要登录用户")
        ↓
    【衣橱空检查】
        wardrobe_client.check_wardrobe_empty(user_id)
        SQL: SELECT COUNT(*) FROM user_wardrobe WHERE user_id = %s AND is_active = TRUE
        如果 count == 0: return error("您的衣橱还没有添加衣物...")
        ↓
    【向量检索】
        wardrobe_client.vector_search_wardrobe(
            user_id=1,
            query_embedding=...,
            target_elements=["土", "木"],
            weather_info={...},
            limit=50
        )
        ↓
    SQL 查询（wardrobe_client.py 第 140-150 行）:
        SELECT id, name, category, primary_element, secondary_element,
               attributes_detail, gender, applicable_weather, ...,
               1 - (embedding <=> %(query_vector)s::vector) AS semantic_score
        FROM user_wardrobe
        WHERE user_id = %(user_id)s
          AND is_active = TRUE
          AND embedding IS NOT NULL
          -- 可选: 天气过滤条件
        ORDER BY embedding <=> %(query_vector)s::vector
        LIMIT %(limit)s
        ↓
    【标记来源】
        for item in items:
            item["source"] = "wardrobe"
            item["source_label"] = "🏠 自有"
            item_sources[str(item["id"])] = "wardrobe"
        ↓
    【空结果处理】（nodes.py 第 400-420 行）
        if not items and retrieval_mode == "wardrobe":
            return error("您的衣橱中没有符合当前五行需求的衣物...")
        -- 注意：衣橱模式不 fallback 到公共库
        ↓
    【动态权重计算】
        semantic_weight = 0.6, wuxing_weight = 0.4
        根据 bazi/scene 动态调整权重
        计算 final_score = semantic_score * semantic_weight + wuxing_score * wuxing_weight
        ↓
    【分类多样性优化】
        _ensure_category_diversity(scored_items, top_k)
        确保上装/下装/外套/配饰各类别均衡
        ↓
    返回检索结果到 graph.py
        ↓
    流式返回事件:
        - type: "analysis"  → 显示五行分析
        - type: "items"     → 显示推荐物品列表（全部来自用户衣橱，标记 🏠 自有）
        - type: "token"    → 逐字显示推荐理由
        - type: "done"     → 结束标记
        ↓
    前端 ChatInterface 实时渲染各类型事件
```

**我的衣橱模式特点：**
- 数据源：`user_wardrobe` 表（用户私有衣橱）
- 权限：必须登录，必须传递 user_id
- 过滤条件：user_id 匹配、is_active=TRUE、embedding IS NOT NULL、可选天气过滤
- 结果标记：🏠 自有
- 兜底策略：无（如果衣橱为空或五行不匹配，返回错误提示，不 fallback）
- SQL 参数：使用命名参数 `%(name)s` 避免类型错位

---

### 2.3 智能混合模式（hybrid）

```
用户操作
    ↓
在 ChatInterface 选择"智能混合"模式，输入问题并发送
    ↓
apps/web/components/features/ChatInterface.tsx
    handleSendMessage()
        ↓
    检查登录状态: isAuthenticated = true
        ↓
    构建请求参数:
        - retrieval_mode: "hybrid"
        - user_id: user.id（必需）
        - query/scene/bazi/gender/weather_element: 上下文信息
        ↓
    for await (const event of streamRecommendation({...}))
        ↓
    POST /api/v1/recommend/stream  (SSE 流)
        ↓
    后端: apps/api/routers/recommend.py:recommend_stream()
        ↓
    调用 packages/ai_agents/graph.py:run_agent_stream(user_id=1, retrieval_mode="hybrid")
        ↓
    创建初始状态: create_initial_state(user_id=1, retrieval_mode="hybrid")
        ↓
    执行 retrieve_items_node(state)
        ↓
    进入 nodes.py 第 339-382 行（hybrid 分支）
        ↓
    【第一步：优先从衣橱检索】
        if user_id and not wardrobe_client.check_wardrobe_empty(user_id):
            wardrobe_client.vector_search_wardrobe(
                user_id=1,
                query_embedding=...,
                target_elements=["土", "木"],
                limit=top_k  -- 注意：这里 limit=top_k（默认5）
            )
            ↓
            SQL: 同 wardrobe 模式，但 limit 较小
            ↓
            for item in wardrobe_items:
                item["source"] = "wardrobe"
                item["source_label"] = "🏠 自有"
                item_sources[str(item["id"])] = "wardrobe"
            ↓
            items.extend(wardrobe_items)
        ↓
    【第二步：从公共库补充】
        if len(items) < top_k:
            need_count = top_k - len(items)
            public_items = _vector_search(
                search_query,
                limit=top_k * 2,  -- 多查一些用于去重
                user_gender=user_gender,
                weather_info=weather_info
            )
            ↓
            SQL: SELECT ... FROM items WHERE embedding IS NOT NULL ...
            ↓
            for item in public_items:
                item["source"] = "public"
                item["source_label"] = "🛒 建议"
                item_sources[item["item_code"]] = "public"
            ↓
            【去重合并】
            existing_ids = {str(i.get("id")) for i in items}
            for item in public_items:
                if str(item.get("id")) not in existing_ids:
                    items.append(item)
                    if len(items) >= top_k * 2:
                        break
        ↓
    【后续处理同其他模式】
        动态权重计算 → 分类多样性优化 → 返回结果
        ↓
    流式返回事件:
        - type: "analysis"  → 显示五行分析
        - type: "items"     → 显示混合推荐列表
                            （优先展示衣橱物品 🏠 自有，
                             不足时补充公共库 🛒 建议）
        - type: "token"    → 逐字显示推荐理由
        - type: "done"     → 结束标记
        ↓
    前端 ChatInterface 实时渲染各类型事件
```

**智能混合模式特点：**
- 数据源：`user_wardrobe` + `items`（优先衣橱，不足补充）
- 权限：必须登录，必须传递 user_id
- 检索策略：
  1. 先从衣橱检索 top_k 件
  2. 如果不足，从公共库补充到 top_k * 2
  3. 去重合并（避免同一物品重复）
- 结果标记：🏠 自有（衣橱）+ 🛒 建议（公共库）
- 适用场景：用户有衣橱但物品不够丰富时，保证推荐数量和质量

---

### 三种模式对比表

| 特性 | 全局库模式 (public) | 我的衣橱模式 (wardrobe) | 智能混合模式 (hybrid) |
|------|---------------------|-------------------------|----------------------|
| **数据源** | `items` 表 | `user_wardrobe` 表 | `user_wardrobe` + `items` |
| **登录要求** | 不需要 | 必需 | 必需 |
| **user_id** | 不传 | 必需 | 必需 |
| **主要过滤** | 性别、天气 | user_id、天气 | user_id、性别、天气 |
| **结果标记** | 🛒 建议 | 🏠 自有 | 🏠 自有 / 🛒 建议 |
| **空结果处理** | 百搭单品兜底 | 返回错误提示 | 公共库补充 |
| **适用场景** | 未登录/快速体验 | 忠实用户/个性化 | 平衡个性化与丰富度 |
| **代码位置** | nodes.py:384-397 | nodes.py:303-337 | nodes.py:339-382 |

---

### 前端模式切换逻辑

```
apps/web/components/features/ChatInterface.tsx
    ↓
const { retrievalMode } = useChatStore()  -- 当前选择的模式
const { user, isAuthenticated } = useUserStore()  -- 用户状态
    ↓
// 未登录时强制使用 public 模式
const effectiveRetrievalMode = isAuthenticated ? retrievalMode : 'public'
    ↓
// 获取用户ID（衣橱模式需要）
const userId = user?.id
    ↓
// 构建请求
streamRecommendation({
    query: content,
    retrieval_mode: effectiveRetrievalMode,  -- "public" | "wardrobe" | "hybrid"
    user_id: userId,  -- 衣橱/混合模式必需
    ...其他参数
})
```

**登录状态控制：**
- 未登录：自动锁定为 `public` 模式，禁用模式切换 UI
- 已登录：可自由切换三种模式，根据选择传递对应参数

## 示例 3: 添加衣物到衣橱

```
用户操作
    ↓
在 AddWardrobeModal 填写衣物信息
    ↓
点击"AI 分析"按钮
    ↓
调用 wardrobe store 的 previewTagging()
    ↓
POST /api/v1/wardrobe/items/preview-tagging
    ↓
后端: apps/api/routers/wardrobe.py:preview_tagging()
    ↓
调用 apps/api/services/ai_tagging_service.py:analyze_item()
    ↓
返回 AI 分析结果 (五行、颜色、材质等)
    ↓
前端显示 AI 建议，用户可修改
    ↓
点击"确认添加"
    ↓
调用 wardrobe store 的 addItem()
    ↓
POST /api/v1/wardrobe/items
    ↓
后端: apps/api/routers/wardrobe.py:add_wardrobe_item()
    ↓
1. AI 打标 (如未指定五行)
2. 生成 Embedding 向量
3. 存入数据库
    ↓
返回新创建的衣物 item
    ↓
前端 wardrobe store 将新 item 添加到列表头部
    ↓
UI 更新显示新添加的衣物
```

## 示例 4: 用户登录

```
用户操作
    ↓
在 AuthModal 输入手机号/邮箱和密码
    ↓
点击"登录"
    ↓
apps/web/components/features/AuthModal.tsx
    调用 useUserStore().login(phone, password)
        ↓
    apps/web/store/user.ts
        login() 方法
            ↓
        await apiLogin({ phone, password })
            ↓
        POST /api/v1/auth/login  (form-data)
            ↓
        后端: apps/api/routers/auth.py:login()
            ↓
        验证用户名密码
        生成 JWT token
            ↓
        返回 { access_token, user }
            ↓
        前端: setAuthToken(data.access_token) 保存到 localStorage
            ↓
        更新 store: set({ user, isAuthenticated: true })
            ↓
        登录成功，关闭弹窗
            ↓
        如有需要，自动调用 fetchUserInfo() 获取完整信息
```

---

## 文件层级总结

```
┌─────────────────────────────────────────────────────────┐
│  前端页面 / 组件 (Page / Component)                        │
│  - app/page.tsx                                          │
│  - app/wardrobe/page.tsx                                 │
│  - components/features/UserProfile.tsx                   │
│  - components/features/ChatInterface.tsx                 │
│  - components/features/AuthModal.tsx                     │
│  - components/features/AddWardrobeModal.tsx              │
├─────────────────────────────────────────────────────────┤
│  状态管理 (Zustand Store)                                │
│  - store/user.ts      (用户认证、资料)                    │
│  - store/chat.ts      (聊天、推荐)                        │
│  - store/wardrobe.ts  (衣橱管理)                          │
├─────────────────────────────────────────────────────────┤
│  API 封装层 (lib/api.ts)                                 │
│  - streamRecommendation()                                │
│  - calculateBazi() / updateUserBazi()                    │
│  - login() / register() / logout()                       │
│  - getCurrentUser() / getUserProfile() / updateProfile() │
│  - getWardrobeItems() / addWardrobeItem() / ...          │
│  - previewTagging() / submitFeedback()                   │
├─────────────────────────────────────────────────────────┤
│  HTTP 请求 → 后端 FastAPI                                │
└─────────────────────────────────────────────────────────┘
```
