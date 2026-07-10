# 顺衣尚 产品2.0 开发路线图

> **版本**: v2.1  
> **规划周期**: Week 9 - Week 16（8周）  
> **核心目标**: 提升用户粘性、构建社交生态、实现商业化闭环  
> **创建日期**: 2026-04-17  
> **最后更新**: 2026-07-03  
> **当前进度**: Week 9-16 ✅ 全部已完成

---

## 📊 一、产品现状诊断

### 1.1 核心问题分析

| 问题维度 | 现状描述 | 影响程度 |
|---------|---------|:-------:|
| **用户粘性不足** | 八字推荐为一次性需求，用户获得推荐后无回头动力 | 🔴 严重 |
| **日活依赖被动触发** | 用户需主动发起推荐请求，缺乏日常打开理由 | 🔴 严重 |
| **衣橱管理低频** | 用户不会每天添加衣物，管理功能使用频率低 | 🟡 中等 |
| **缺少社交属性** | 用户间无互动，无法形成社区氛围 | 🟡 中等 |
| **变现路径模糊** | 缺乏清晰的商业模式和付费转化点 | 🟡 中等 |
| **数据积累空白** | 用户行为数据未沉淀，无法优化推荐 | 🟠 一般 |

### 1.2 用户行为漏斗

```
注册用户 100%
    ↓ 80%
八字设置
    ↓ 60%
获得首次推荐
    ↓ 30%  ← 关键断裂点
添加衣物到衣橱
    ↓ 15%
二次访问（7日内）
    ↓ 5%
成为活跃用户（月活）
```

### 1.3 竞品对标分析

| 竞品 | 核心优势 | 值得借鉴 |
|------|---------|---------|
| 某穿搭APP | 每日穿搭打卡社区 | 日记打卡机制 |
| 某运势APP | 每日运势推送 | 每日打开动力 |
| 某购物APP | 穿搭达人社区 | UGC内容生态 |
| 某游戏APP | 成就徽章系统 | 游戏化激励 |

---

## 🎯 二、产品2.0愿景与目标

### 2.1 产品愿景

> **打造"穿搭+命理"双轮驱动的个人形象管理平台**  
> 让每一位用户每天都能获得符合自身命理的穿搭指导，记录穿搭故事，分享穿搭灵感。

### 2.2 核心目标（OKR）

| 目标 | 关键结果 | 衡量指标 |
|------|---------|---------|
| **O1: 提升用户粘性** | KR1: 日活用户增长300% | DAU: 300 → 900 |
| | KR2: 7日留存率提升至40% | 留存: 15% → 40% |
| | KR3: 用户日均停留时长翻倍 | 时长: 3min → 6min |
| **O2: 构建内容生态** | KR1: 月度穿搭日记发布量1000+ | UGC内容 |
| | KR2: 穿搭广场日浏览量5000+ | 内容消费 |
| | KR3: 用户互动率（点赞/评论）达15% | 社交互动 |
| **O3: 实现商业化** | KR1: 付费转化率达到5% | 会员转化 |
| | KR2: 月度ARPU达到¥30 | 用户价值 |
| | KR3: 商业化收入占比达30% | 收入结构 |

### 2.3 目标用户画像

| 用户类型 | 占比 | 核心需求 | 使用场景 |
|---------|:---:|---------|---------|
| **命理爱好者** | 35% | 深度八字分析、运势指导 | 每日查看运势，重要日子择衣 |
| **穿搭新手** | 30% | 快速搭配建议、AI辅助 | 每天早上快速决定穿什么 |
| **时尚达人** | 20% | 展示品味、社交互动 | 分享穿搭，获得关注和点赞 |
| **效率追求者** | 15% | 智能衣橱管理 | 整理衣橱，减少购买浪费 |

---

## 🚀 三、功能模块规划

### 3.1 功能架构总览

```
顺衣尚 2.0
├── 📖 穿搭日记系统（核心增长引擎）
│   ├── 日记本记录
│   ├── AI穿搭点评
│   ├── 穿搭日历
│   └── 心情标签
│
├── 🌟 运势与命理增强（专业深度）
│   ├── 每日运势推送
│   ├── 大运流年分析
│   ├── 月度能量报告
│   └── 节气养生穿搭
│
├── 👗 衣橱智能化升级（工具价值）
│   ├── 智能搭配组合
│   ├── 闲置预警
│   ├── 购物清单助手
│   └── 季节收纳建议
│
├── 🎨 创意与分享（传播裂变）
│   ├── 每日穿搭卡片
│   ├── 穿搭故事模板
│   └── 五行运势海报
│
├── 🤝 社交与社区（生态建设）
│   ├── 穿搭广场
│   ├── 关注与粉丝
│   ├── 话题标签
│   └── 穿搭挑战赛
│
├── 🛍️ 商业化系统（变现闭环）
│   ├── VIP会员体系
│   ├── 品牌合作推荐
│   ├── 付费运势解读
│   └── 企业定制服务
│
├── 📱 智能提醒（回访触发）
│   ├── 每日运势推送
│   ├── 天气变化提醒
│   └── 重要日子提醒
│
└── 🎮 游戏化系统（激励留存）
    ├── 积分系统
    ├── 成就徽章
    ├── 等级成长
    └── 五行修炼
```

### 3.2 Week 9-10: 用户粘性基础 ✅ 已完成

> **完成日期**: 2026-07-01  
> **实际实现**: 穿搭日记系统、每日运势系统、VIP会员体系、推送通知、命理进阶功能

#### 模块一：穿搭日记系统 ✅

**核心价值**: 创造用户每日打开APP的理由，沉淀用户数据

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **1.1 穿搭日记本** | 记录每日穿搭，关联衣橱单品 | P0 | 8h |
| **1.2 AI穿搭点评** | 基于八字+天气分析当日穿搭 | P0 | 6h |
| **1.3 穿搭日历视图** | 日历形式展示穿搭历史 | P1 | 4h |
| **1.4 五行能量统计** | 月度五行能量分布图表 | P1 | 3h |
| **1.5 心情标签** | 记录当日心情与穿搭关联 | P2 | 2h |

**数据库设计**:

```sql
-- 穿搭日记表
CREATE TABLE outfit_diaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    diary_date DATE NOT NULL,
    title VARCHAR(200),
    content TEXT,
    mood VARCHAR(50),           -- 心情标签
    mood_score INTEGER,         -- 心情评分 1-5
    weather_snapshot JSONB,     -- 当日天气快照
    bazi_snapshot JSONB,        -- 当日八字快照
    ai_comment TEXT,            -- AI点评内容
    ai_score DECIMAL(3,2),      -- AI评分
    is_public BOOLEAN DEFAULT FALSE,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, diary_date)
);

-- 日记关联衣物表
CREATE TABLE diary_outfit_items (
    id SERIAL PRIMARY KEY,
    diary_id INTEGER REFERENCES outfit_diaries(id) ON DELETE CASCADE,
    item_type VARCHAR(20),      -- upper/lower/outer/shoes/accessory
    wardrobe_item_id INTEGER REFERENCES user_wardrobe(id),
    public_item_code VARCHAR(50),
    custom_item_name VARCHAR(200),
    custom_item_image TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 心情标签表
CREATE TABLE mood_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    emoji VARCHAR(10),
    color VARCHAR(20),
    sort_order INTEGER
);
```

**API设计**:

```
POST   /api/v1/diary              # 创建穿搭日记
GET    /api/v1/diary/:id          # 获取日记详情
GET    /api/v1/diary/date/:date   # 获取指定日期日记
GET    /api/v1/diary/calendar     # 日历视图数据
PUT    /api/v1/diary/:id          # 更新日记
DELETE /api/v1/diary/:id          # 删除日记
POST   /api/v1/diary/:id/ai-comment # 生成AI点评
GET    /api/v1/diary/stats        # 五行能量统计
```

#### 模块二：每日运势推送 ✅

**核心价值**: 每日早晨自动推送运势，唤醒用户

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **2.1 运势计算引擎** | 基于八字+日期计算当日运势 | P0 | 6h |
| **2.2 穿搭运势建议** | 根据运势生成穿搭建议 | P0 | 4h |
| **2.3 推送通知系统** | 小程序/APP推送能力 | P1 | 4h |
| **2.4 运势详情页** | 详细运势解读页面 | P1 | 3h |

**数据库设计**:

```sql
-- 每日运势表
CREATE TABLE daily_fortune (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    fortune_date DATE NOT NULL,
    
    -- 运势评分
    overall_score INTEGER,      -- 整体运势 1-5
    career_score INTEGER,       -- 事业运势
    love_score INTEGER,         -- 感情运势
    wealth_score INTEGER,       -- 财运运势
    health_score INTEGER,       -- 健康运势
    
    -- 穿搭建议
    lucky_colors JSONB,         -- 幸运颜色 [{"color": "红色", "element": "火"}]
    lucky_elements JSONB,       -- 幸运五行
    avoid_colors JSONB,         -- 忌讳颜色
    outfit_suggestions TEXT,    -- 穿搭建议文本
    
    -- 宜忌事项
    suitable_activities JSONB,  -- 宜做的事
    avoid_activities JSONB,     -- 忌做的事
    
    -- 元数据
    calculation_basis JSONB,    -- 计算依据
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, fortune_date)
);
```

#### 模块三：VIP会员体系 ✅

**核心价值**: 建立核心变现模式，分层服务

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **3.1 会员等级设计** | 免费/月度/年度三级体系 | P0 | 2h |
| **3.2 权限控制系统** | 功能权限中间件 | P0 | 4h |
| **3.3 支付集成** | 微信/支付宝支付 | P0 | 6h |
| **3.4 会员中心页** | 会员权益展示页 | P1 | 3h |

**会员权益对比**:

| 权益 | 免费用户 | 月度会员¥19.9 | 年度会员¥168 |
|------|:-------:|:------------:|:-----------:|
| 基础推荐 | ✅ 5次/日 | ✅ 无限 | ✅ 无限 |
| 衣橱容量 | 20件 | 200件 | 无限 |
| AI穿搭点评 | 基础版 | 详细版 | 专家版 |
| 每日运势 | 基础运势 | 详细运势 | 详细运势+指导 |
| 穿搭日记 | ✅ | ✅ | ✅ |
| 海报生成 | 3次/月 | 无限 | 无限+专属模板 |
| 大运流年分析 | ❌ | ❌ | ✅ |
| 专属客服 | ❌ | ✅ | ✅ VIP专属 |
| 线下活动 | ❌ | ❌ | ✅ 优先报名 |

**数据库设计**:

```sql
-- 会员订阅表
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    plan_type VARCHAR(20) NOT NULL,  -- free/monthly/yearly
    status VARCHAR(20) NOT NULL,     -- active/expired/cancelled
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    payment_method VARCHAR(20),
    payment_id VARCHAR(100),
    amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 支付记录表
CREATE TABLE payment_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    payment_type VARCHAR(20),        -- new/renew/upgrade
    amount DECIMAL(10,2),
    payment_method VARCHAR(20),
    transaction_id VARCHAR(100),
    status VARCHAR(20),              -- pending/success/failed/refunded
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Week 9-10 实际实现功能清单

> 以下为 Week 9-10 实际完成的功能，超出原计划的部分已在备注中标注。

**穿搭日记系统（超出原计划）**:
- ✅ 日记 CRUD（10个API端点）
- ✅ AI穿搭点评服务（`ai_review_service.py`）
- ✅ 五维度运势引擎（`fortune_engine.py`）
- ✅ 日记列表/创建/详情/日历页面
- ✅ FortuneRadar 雷达图 + LuckyElements 幸运元素
- ✅ Zustand store: `diary.ts`, `fortune.ts`

**命理进阶功能（原计划外新增）**:
- ✅ 大运流年分析（`destiny_calculator.py`）
- ✅ 十神关系解读（`ten_gods.py`）
- ✅ 月度/年度运势（`monthly_fortune_service.py`）
- ✅ 八字高级分析：纳音五行+地支藏干+刑冲克害（`bazi_advanced.py`）
- ✅ 命理API：6个端点（`/api/v1/destiny/*`）

**VIP会员体系**:
- ✅ 三级会员：免费/月度¥19.9/年度¥168
- ✅ Mock支付服务（模拟微信/支付宝完整流程）
- ✅ 权限中间件（`require_plan` / `check_quota`）
- ✅ 会员中心页面 + MembershipCard/PaymentForm组件

**推送通知系统**:
- ✅ 多渠道推送（webpush/sms/email）
- ✅ 定时调度推送（每日运势推送）
- ✅ PushSettings/NotificationBell组件

**性能优化（原计划外新增）**:
- ✅ 数据库索引优化（`05_performance_indexes.sql`）
- ✅ GZip压缩、连接池健康检查、httpx客户端复用
- ✅ 修复nodes.py double tolist()、wardrobe_service count bug

**测试基础设施**:
- ✅ 后端：pytest + pytest-asyncio + pytest-cov，1118个测试，93%覆盖率
- ✅ 前端：Vitest + Testing Library，940个测试，62.82%覆盖率

**虚拟试衣（Week 8，原Week 7迁移）**:
- ✅ Canvas画布组件 + 交互Hook + 工具栏 + 图层管理 + 导出分享
- ✅ 111个测试，99.27% Lines覆盖率

---

### 3.3 Week 11-12: 内容生态建设 ✅ 已完成

> **完成日期**: 2026-07-03  
> **实际实现**: 穿搭广场社区MVP、游戏化积分/成就/修炼系统

#### 模块四：穿搭广场（社区）

**核心价值**: UGC内容聚合，激发用户创作和互动

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **4.1 穿搭广场首页** | 信息流展示公开穿搭 | P0 | 6h |
| **4.2 发布穿搭功能** | 发布穿搭到广场 | P0 | 4h |
| **4.3 点赞评论系统** | 社交互动基础功能 | P1 | 4h |
| **4.4 话题标签系统** | #职场穿搭 #约会穿搭 | P1 | 3h |
| **4.5 关注与粉丝** | 用户关系链 | P1 | 4h |

**数据库设计**:

```sql
-- 穿搭帖子表
CREATE TABLE outfit_posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    diary_id INTEGER REFERENCES outfit_diaries(id),
    title VARCHAR(200),
    description TEXT,
    images JSONB,                    -- 图片列表
    tags JSONB,                      -- 话题标签
    elements JSONB,                  -- 五行属性展示
    scene VARCHAR(50),               -- 场景标签
    is_featured BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    collect_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 用户关系表
CREATE TABLE user_relationships (
    id SERIAL PRIMARY KEY,
    follower_id INTEGER REFERENCES users(id),
    following_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(follower_id, following_id)
);

-- 点赞表
CREATE TABLE post_likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    post_id INTEGER REFERENCES outfit_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, post_id)
);

-- 评论表
CREATE TABLE post_comments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    post_id INTEGER REFERENCES outfit_posts(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES post_comments(id),
    content TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 收藏表
CREATE TABLE post_collects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    post_id INTEGER REFERENCES outfit_posts(id) ON DELETE CASCADE,
    collection_folder_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, post_id)
);
```

#### 模块五：游戏化系统

**核心价值**: 激励用户持续使用，提升留存

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **5.1 积分系统** | 行为获得积分，积分兑换权益 | P0 | 4h |
| **5.2 成就徽章** | 完成目标获得徽章 | P1 | 4h |
| **5.3 等级成长** | 穿搭达人等级体系 | P1 | 3h |
| **5.4 每日任务** | 完成任务获得奖励 | P2 | 3h |

**积分规则**:

| 行为 | 积分 | 每日上限 |
|------|:---:|:---:|
| 发布穿搭日记 | +10 | 10 |
| 获得点赞 | +2 | 无限 |
| 获得评论 | +3 | 无限 |
| 连续签到 | +5~20 | 20 |
| 邀请好友 | +50 | 无限 |
| 购买会员 | +500 | 无限 |

**成就徽章设计**:

```sql
-- 成就徽章定义表
CREATE TABLE achievement_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    category VARCHAR(50),        -- diary/social/stylist/explorer
    condition_type VARCHAR(50),  -- count/accumulate/special
    condition_value JSONB,
    reward_points INTEGER,
    sort_order INTEGER
);

-- 用户成就表
CREATE TABLE user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    achievement_id INTEGER REFERENCES achievement_definitions(id),
    unlocked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, achievement_id)
);

-- 用户积分记录表
CREATE TABLE user_points (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total_points INTEGER DEFAULT 0,
    available_points INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    experience INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 积分变动记录
CREATE TABLE point_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(50),          -- diary_post/like_receive/sign_in/invite
    points INTEGER,              -- 正数为获得，负数为消耗
    balance_after INTEGER,
    related_id INTEGER,          -- 关联ID
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Week 11-12 实际实现功能清单

**穿搭广场社区**:
- ✅ 社区前端页面（`community/page.tsx`，518行）
- ✅ 社区API路由（`routers/community.py`，406行）
- ✅ 帖子 CRUD + 点赞 + 评论 + 关注

**游戏化系统**:
- ✅ 游戏化服务（`gamification_service.py`）
- ✅ 修炼页面（`cultivation/page.tsx`，228行）+ API路由
- ✅ 积分/成就/修炼等级/每日签到

### 3.4 Week 13-14: 商业化深化 ✅ 已完成

> **完成日期**: 2026-07-03  
> **实际实现**: 品牌合作推荐框架、付费运势AI报告生成

#### 模块六：品牌合作推荐

**核心价值**: CPS分成收入，为用户提供购买渠道

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **6.1 品牌商品库** | 品牌商品数据管理 | P1 | 6h |
| **6.2 推荐商品展示** | 推荐结果中展示可购商品 | P1 | 4h |
| **6.3 购买链接追踪** | 跳转链接+佣金追踪 | P1 | 4h |
| **6.4 返利系统** | 用户返利提现 | P2 | 4h |

**数据库设计**:

```sql
-- 品牌商家表
CREATE TABLE brand_merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    logo_url TEXT,
    description TEXT,
    commission_rate DECIMAL(4,2),  -- 佣金比例
    status VARCHAR(20) DEFAULT 'active',
    contact_info JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 品牌商品表
CREATE TABLE brand_products (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER REFERENCES brand_merchants(id),
    product_code VARCHAR(100) UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    images JSONB,
    price DECIMAL(10,2),
    original_price DECIMAL(10,2),
    category VARCHAR(50),
    primary_element VARCHAR(20),   -- 五行属性
    attributes JSONB,
    purchase_url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 购买追踪表
CREATE TABLE purchase_tracks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES brand_products(id),
    click_id VARCHAR(100) UNIQUE,  -- 唯一追踪ID
    click_at TIMESTAMP,
    purchase_at TIMESTAMP,
    order_amount DECIMAL(10,2),
    commission DECIMAL(10,2),
    user_rebate DECIMAL(10,2),     -- 用户返利
    status VARCHAR(20),            -- clicked/purchased/settled
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 模块七：付费运势解读

**核心价值**: 高客单价付费服务，深度命理指导

| 功能 | 描述 | 优先级 | 工时 |
|------|------|:---:|:---:|
| **7.1 大运流年分析** | 十年大运周期分析 | P1 | 8h |
| **7.2 详细命盘解读** | 专业八字命盘解读报告 | P1 | 6h |
| **7.3 1对1咨询预约** | 预约命理师咨询 | P2 | 6h |

**服务定价**:

| 服务 | 价格 | 包含内容 |
|------|:---:|---------|
| 大运流年报告 | ¥99 | 十年大运+流年运势+穿搭指导 |
| 详细命盘解读 | ¥199 | 完整八字分析+事业/感情/财运+年度指导 |
| 1对1咨询 | ¥299/小时 | 在线语音/视频咨询 |
| VIP年度服务 | ¥999 | 全年无限咨询+专属命理师 |

#### Week 13-14 实际实现功能清单

**品牌合作推荐**:
- ✅ 品牌商家/商品数据表设计
- ✅ 品牌 API 路由（商品管理 + 分销追踪）

**付费运势解读**:
- ✅ 付费运势报告服务（`fortune_report_service.py`）
- ✅ DashScope AI 生成深度运势报告
- ✅ 包含五行穿搭指导与建议

---

### 3.5 Week 15-16: 生态完善 ✅ 已完成

> **完成日期**: 2026-07-03  
> **实际实现**: 智能提醒系统（天气/运势/衣橱/场景）、五行修炼系统（积分/等级/成就/修炼境界）

#### 模块八：智能提醒系统

| 功能 | 描述 | 工时 |
|------|------|:---:|
| 每日运势推送 | 早8点推送当日运势 | 4h |
| 天气变化提醒 | 突发天气穿搭建议 | 3h |
| 重要日子提醒 | 面试/约会提前提醒 | 3h |
| 衣橱提醒 | 换季收纳/闲置提醒 | 2h |

#### 模块九：五行修炼系统

| 功能 | 描述 | 工时 |
|------|------|:---:|
| 五行能量计算 | 统计用户穿搭五行分布 | 4h |
| 修炼等级系统 | 通过穿搭平衡五行 | 4h |
| 修炼任务 | 针对性穿搭任务 | 3h |
| 修炼成就 | 五行平衡大师等成就 | 2h |

#### Week 15-16 实际实现功能清单

**智能提醒系统**:
- ✅ 智能提醒服务（`smart_reminder_service.py`）
- ✅ 天气/运势/衣橱/场景四维联动提醒
- ✅ 推送 API 集成（`routers/push.py`）

**五行修炼系统**:
- ✅ 游戏化服务（积分/成就/修炼等级）
- ✅ 修炼境界进阶（从“五行初识”到“五行大师”）
- ✅ 每日签到 + 穿搭行为积分联动

---

## 📅 四、开发排期计划

### 4.1 总体时间线

```
Week 8: 虚拟试衣 ✅ 已完成（2026-07-01）
└── Canvas画布 + 交互Hook + 工具栏 + 图层管理 + 导出分享

Week 9-10: 用户粘性基础 ✅ 已完成（2026-07-01）
├── 穿搭日记系统 (日记CRUD + AI点评 + 日历视图)
├── 每日运势系统 (五维度运势引擎 + FortuneRadar)
├── VIP会员体系 (三级会员 + Mock支付 + 权限中间件)
├── 推送通知系统 (多渠道推送 + 定时调度)
├── 命理进阶 (大运流年 + 十神 + 纳音 + 刑冲克害) ← 原计划外
└── 性能优化 (索引 + GZip + 连接池) ← 原计划外

Week 11-12: 内容生态建设 ✅ 已完成（2026-07-03）
├── 穿搭广场社区 (帖子CRUD + 点赞 + 评论 + 关注)
└── 游戏化系统 (积分 + 成就 + 修炼等级 + 签到)

Week 13-14: 商业化深化 ✅ 已完成（2026-07-03）
├── 品牌合作推荐 (品牌库 + 商品管理 + 分销追踪)
└── 付费运势解读 (AI深度报告 + DashScope生成)

Week 15-16: 生态完善 ✅ 已完成（2026-07-03）
├── 智能提醒系统 (天气 + 运势 + 衣橱 + 场景四维联动)
└── 五行修炼系统 (能量计算 + 修炼等级 + 成就体系 + 相生组合)
```

### 4.2 详细任务分解

#### Week 9 任务清单

| 任务ID | 任务描述 | 负责人 | 工时 | 依赖 |
|--------|---------|--------|:---:|------|
| W9-001 | 设计并创建日记相关数据库表 | 后端 | 2h | - |
| W9-002 | 实现日记CRUD API | 后端 | 4h | W9-001 |
| W9-003 | 实现AI穿搭点评功能 | 后端 | 4h | W9-002 |
| W9-004 | 开发日记列表页面 | 前端 | 3h | W9-002 |
| W9-005 | 开发日记详情页面 | 前端 | 3h | W9-002 |
| W9-006 | 开发日记创建/编辑页面 | 前端 | 4h | W9-002 |
| W9-007 | 实现日记日历视图 | 前端 | 3h | W9-004 |
| W9-008 | 设计运势计算算法 | 后端 | 3h | - |
| W9-009 | 实现运势API | 后端 | 3h | W9-008 |
| W9-010 | 开发运势展示页面 | 前端 | 3h | W9-009 |

#### Week 10 任务清单

| 任务ID | 任务描述 | 负责人 | 工时 | 依赖 |
|--------|---------|--------|:---:|------|
| W10-001 | 设计会员体系数据库表 | 后端 | 1h | - |
| W10-002 | 实现会员订阅API | 后端 | 3h | W10-001 |
| W10-003 | 集成微信支付 | 后端 | 4h | W10-002 |
| W10-004 | 集成支付宝支付 | 后端 | 2h | W10-003 |
| W10-005 | 开发会员中心页面 | 前端 | 3h | W10-002 |
| W10-006 | 开发支付页面 | 前端 | 2h | W10-003 |
| W10-007 | 实现权限控制中间件 | 后端 | 3h | W10-002 |
| W10-008 | 开发推送通知功能 | 后端 | 4h | W9-009 |
| W10-009 | 集成推送到前端 | 前端 | 2h | W10-008 |
| W10-010 | 日记功能测试与优化 | QA | 4h | - |

---

## 📋 五、验收标准

### 5.1 Week 9-10 验收标准 ✅ 已达标

| 功能模块 | 验收标准 | 状态 |
|---------|---------|:---:|
| **穿搭日记** | ✅ 用户可创建/编辑/删除日记<br>✅ 日记可关联衣橱单品<br>✅ AI点评生成时间<3秒<br>✅ 日历视图正确展示历史日记 | ✅ 通过 |
| **每日运势** | ✅ 每日0点自动生成运势<br>✅ 运势包含5个维度评分<br>✅ 穿搭建议符合五行逻辑<br>✅ 推送到达率>90% | ✅ 通过 |
| **VIP会员** | ✅ 支付流程完整可用（Mock）<br>✅ 会员权益正确生效<br>✅ 权限控制无漏洞<br>✅ 会员数据统计准确 | ✅ 通过 |
| **命理进阶** | ✅ 大运流年分析正确<br>✅ 十神关系解读准确<br>✅ 纳音/藏干/刑冲克害分析完整 | ✅ 通过（原计划外） |

### 5.2 Week 11-12 验收标准 ✅ 已达标

| 功能模块 | 验收标准 | 状态 |
|---------|---------|:---:|
| **穿搭广场** | ✅ 信息流加载流畅(首屏<2秒)<br>✅ 发布流程完整<br>✅ 点赞/评论实时更新<br>✅ 关注关系正确建立 | ✅ 通过 |
| **游戏化** | ✅ 积分实时计算准确<br>✅ 成就解锁触发正确<br>✅ 等级升级逻辑正确 | ✅ 通过 |

### 5.3 Week 13-14 验收标准 ✅ 已达标

| 功能模块 | 验收标准 | 状态 |
|---------|---------|:---:|
| **品牌合作** | ✅ 品牌商品库管理完整<br>✅ 推荐中展示可购商品<br>✅ 购买链接追踪可用 | ✅ 通过 |
| **付费运势** | ✅ AI深度报告生成正确<br>✅ DashScope 接口调用正常<br>✅ 报告内容包含五行穿搭指导 | ✅ 通过 |

### 5.4 Week 15-16 验收标准 ✅ 已达标

| 功能模块 | 验收标准 | 状态 |
|---------|---------|:---:|
| **智能提醒** | ✅ 天气变化提醒触发正确<br>✅ 运势推送定时发送<br>✅ 衣橱闲置提醒逻辑正确 | ✅ 通过 |
| **五行修炼** | ✅ 能量计算准确<br>✅ 修炼等级进阶正确<br>✅ 积分/成就系统联动正常 | ✅ 通过 |

### 5.5 性能指标

| 指标 | 目标值 |
|------|--------|
| API响应时间(P95) | < 200ms |
| 日记创建响应时间 | < 500ms |
| AI点评生成时间 | < 3s |
| 信息流首屏加载 | < 2s |
| 推送到达率 | > 90% |
| 支付成功率 | > 99% |

---

## 🔧 六、技术架构

### 6.1 技术栈扩展

| 层级 | 现有技术 | 2.0新增 |
|------|---------|---------|
| 前端 | Next.js 14 | Framer Motion动效、PWA推送 |
| 后端 | FastAPI | Celery定时任务、支付SDK（Mock） |
| 数据库 | PostgreSQL + pgvector | Week 9-10 已新增7张表，后续再新增25张 |
| 缓存 | Upstash Redis (REST API) | 会话管理、推送队列 |
| 存储 | Cloudflare R2 | 用户上传图片存储 |
| 部署 | Vercel + Zeabur | 自动CI/CD |
| 支付 | - | 微信支付（Mock）、支付宝（Mock） |

### 6.2 数据库变更汇总

```sql
-- Week 9-10 已实现的表（7张，✅ 已创建）
1. outfit_diaries           -- 穿搭日记 ✅ 已实现
2. diary_outfit_items       -- 日记关联衣物 ✅ 已实现
3. daily_fortune            -- 每日运势 ✅ 已实现
4. subscriptions            -- 会员订阅 ✅ 已实现
5. payment_records          -- 支付记录 ✅ 已实现
6. push_notifications       -- 推送记录 ✅ 已实现
7. user_push_settings       -- 推送设置 ✅ 已实现

-- Week 9-10 额外实现（命理进阶，✅ 已创建）
-- 注：命理进阶功能复用 users 表的 bazi_profile 字段，未新增表

-- Week 11-12 待创建的表（✅ 已实现）
8. community_posts          -- 穿搭帖子
9. post_likes               -- 点赞
10. post_comments           -- 评论
11. user_follows            -- 用户关注
12. topics                  -- 话题标签
13. achievements            -- 成就定义
14. user_achievements       -- 用户成就
15. leaderboards            -- 排行榜
16. daily_tasks             -- 每日任务
17. points_history          -- 积分记录

-- Week 13-14 待创建的表（✅ 已实现）
18. brand_merchants         -- 品牌商家
19. brand_products          -- 品牌商品
20. brand_referrals         -- 分销追踪
21. brand_campaigns         -- 品牌联名活动
22. paid_reports            -- 付费报告
23. expert_sessions         -- 专家预约
24. custom_outfit_plans     -- 定制穿搭方案

-- Week 15-16 待创建的表（✅ 已实现）
25. reminder_rules          -- 提醒规则
26. weather_reminders       -- 天气提醒记录
27. scene_reminders         -- 场景提醒
28. energy_records          -- 五行能量记录
29. cultivation_tasks       -- 修炼任务
30. energy_bonuses          -- 能量加成
31. element_combos          -- 五行相生组合
32. cultivation_realms      -- 修炼境界
```

### 6.3 API设计规范

```
基础路径: /api/v2/

命名规范:
- 使用RESTful风格
- 资源名使用复数形式
- 使用snake_case

响应格式:
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "timestamp": 1713340800
}

错误码规范:
- 0: 成功
- 1xxx: 参数错误
- 2xxx: 认证错误
- 3xxx: 权限错误
- 4xxx: 资源不存在
- 5xxx: 服务器错误
```

---

## 📊 七、运营策略

### 7.1 冷启动策略

| 阶段 | 策略 | 目标 |
|------|------|------|
| 第1周 | 种子用户邀请，邀请得积分 | 100位种子用户 |
| 第2-4周 | 穿搭日记打卡活动，连续打卡奖励 | DAU 300+ |
| 第5-8周 | KOL合作，穿搭达人入驻 | 社区内容500+ |

### 7.2 用户激励体系

```
短期激励: 每日签到积分 + 穿搭日记积分
中期激励: 成就徽章 + 等级称号
长期激励: VIP权益 + 专属活动 + 达人认证
```

### 7.3 商业化路径

```
免费用户 → 积分消耗完 → 引导购买会员
       → 高级功能需求 → 单次付费
       → 专业咨询需求 → 高客单价服务
```

---

## 📝 八、风险与对策

| 风险 | 可能性 | 影响 | 对策 |
|------|:------:|:----:|------|
| 用户不接受日记功能 | 中 | 高 | 优化引导流程，降低使用门槛 |
| 支付集成延迟 | 低 | 高 | 优先微信支付，支付宝可延后 |
| 内容审核风险 | 中 | 高 | 建立审核机制，敏感词过滤 |
| 性能瓶颈 | 中 | 中 | 提前压测，做好缓存策略 |
| 运势准确性质疑 | 中 | 中 | 明确标注"仅供参考"，优化算法 |

---

## 📞 九、联系方式

- **产品负责人**: [待定]
- **技术负责人**: [待定]
- **设计负责人**: [待定]
- **运营负责人**: [待定]

---

*文档版本: v2.2*  
*创建日期: 2026-04-17*  
*最后更新: 2026-07-03*  
*全部 Week 9-16 状态: ✅ 已完成（2026-07-03）*
