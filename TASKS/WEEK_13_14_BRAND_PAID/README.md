# Week 13-14: 品牌合作推荐与付费运势解读

**周期**: Week 13-14  
**主题**: 商业化深化与变现闭环  
**状态**: ✅ 已完成（2026-07-03）  
**预估工时**: 38小时  
**依赖**: Week 9-10 已完成（VIP会员体系、命理进阶功能）

---

## 🎯 本周目标

1. **品牌合作推荐**: 接入品牌商品数据，推荐中提供可购买替代方案
2. **分销链接系统**: 商品购买链接+佣金追踪，实现 CPS 分成
3. **付费运势解读**: 深度运势报告、专家直播解读、个性化穿搭方案
4. **五行能量壁纸**: 个性化五行能量手机壁纸生成

---

## 📋 任务清单

### 模块一：品牌合作推荐（18小时）

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 |
|:---:|------|:---:|:---:|:---:|
| 01 | 品牌库 | 🔴 高 | 5h | - |
| 02 | 穿搭替代推荐 | 🔴 高 | 4h | 01 |
| 03 | 品牌联名活动 | 🟡 中 | 4h | 01 |
| 04 | 分销链接 | 🔴 高 | 5h | 01 |

### 模块二：付费运势解读（20小时）

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 |
|:---:|------|:---:|:---:|:---:|
| 05 | 深度运势报告 | 🔴 高 | 6h | - |
| 06 | 专家直播解读 | 🟡 中 | 5h | 05 |
| 07 | 穿搭方案定制 | 🔴 高 | 5h | 05 |
| 08 | 五行能量壁纸 | 🟡 中 | 4h | - |

---

## 🗄️ 数据库设计

### 品牌合作表

```sql
-- 品牌商家表
CREATE TABLE brand_merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,           -- 优衣库/ZARA/H&M等
    logo_url TEXT,
    description TEXT,
    commission_rate DECIMAL(4,2),         -- 佣金比例 0.00-100.00
    contact_info JSONB,                   -- {email, phone, wechat}
    status VARCHAR(20) DEFAULT 'active',  -- active/inactive/suspended
    partnership_level VARCHAR(20),        -- standard/premium/exclusive
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 品牌商品表
CREATE TABLE brand_products (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brand_merchants(id),
    product_code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    images JSONB NOT NULL,                -- 商品图片列表
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    category VARCHAR(50),                 -- upper/lower/outer/shoes/accessory
    primary_element VARCHAR(20),          -- 五行属性（金/木/水/火/土）
    secondary_element VARCHAR(20),        -- 次五行
    color_tags JSONB,                     -- ["红色", "白色"]
    style_tags JSONB,                     -- ["商务", "休闲"]
    season_tags JSONB,                    -- ["春", "秋"]
    attributes JSONB,                     -- {material, pattern, fit, ...}
    purchase_url TEXT NOT NULL,           -- 购买链接
    embedding vector(1024),               -- 向量嵌入（用于相似推荐）
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_brand_products_brand ON brand_products(brand_id);
CREATE INDEX idx_brand_products_element ON brand_products(primary_element, status);
CREATE INDEX idx_brand_products_category ON brand_products(category, status);

-- 分销追踪表
CREATE TABLE brand_referrals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES brand_products(id),
    click_id VARCHAR(100) UNIQUE NOT NULL,  -- 唯一追踪ID
    click_at TIMESTAMP NOT NULL DEFAULT NOW(),
    purchase_at TIMESTAMP,
    order_amount DECIMAL(10,2),
    commission DECIMAL(10,2),              -- 平台佣金
    user_rebate DECIMAL(10,2),             -- 用户返利
    status VARCHAR(20) DEFAULT 'clicked',  -- clicked/purchased/settled/expired
    settled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_referrals_user ON brand_referrals(user_id, created_at DESC);
CREATE INDEX idx_referrals_click_id ON brand_referrals(click_id);
CREATE INDEX idx_referrals_status ON brand_referrals(status);

-- 品牌联名活动表
CREATE TABLE brand_campaigns (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES brand_merchants(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    theme_element VARCHAR(20),             -- 联名五行主题
    banner_image TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_rate DECIMAL(4,2),            -- 专属折扣
    featured_products JSONB,              -- 精选商品ID列表
    status VARCHAR(20) DEFAULT 'upcoming', -- upcoming/active/ended
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 付费运势解读表

```sql
-- 付费报告表
CREATE TABLE paid_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    report_type VARCHAR(50) NOT NULL,     -- yearly_fortune/career_analysis/love_analysis/wealth_analysis/health_analysis
    title VARCHAR(200) NOT NULL,
    content JSONB NOT NULL,               -- 完整报告内容（分段存储）
    summary TEXT,                         -- 摘要
    bazi_snapshot JSONB,                 -- 生成时的八字快照
    ai_generated BOOLEAN DEFAULT TRUE,    -- 是否AI生成
    reviewed_by INTEGER,                  -- 审核人ID（专家）
    review_status VARCHAR(20) DEFAULT 'pending', -- pending/approved/rejected
    price DECIMAL(10,2) NOT NULL,
    payment_id INTEGER REFERENCES payment_records(id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending/generating/completed/failed
    expires_at TIMESTAMP,                  -- 报告有效期
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_paid_reports_user ON paid_reports(user_id, created_at DESC);
CREATE INDEX idx_paid_reports_type ON paid_reports(report_type, status);

-- 专家预约表
CREATE TABLE expert_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expert_id INTEGER NOT NULL REFERENCES users(id),
    session_type VARCHAR(50) NOT NULL,     -- voice/video/chat
    topic VARCHAR(200),                    -- 咨询主题
    description TEXT,                      -- 问题描述
    scheduled_at TIMESTAMP NOT NULL,      -- 预约时间
    duration INTEGER DEFAULT 60,           -- 时长（分钟）
    price DECIMAL(10,2) NOT NULL,
    payment_id INTEGER REFERENCES payment_records(id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending/confirmed/completed/cancelled/no_show
    meeting_url TEXT,                      -- 会议链接
    notes TEXT,                            -- 会后备注
    rating INTEGER,                        -- 用户评分 1-5
    feedback TEXT,                         -- 用户反馈
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON expert_sessions(user_id, scheduled_at);
CREATE INDEX idx_sessions_expert ON expert_sessions(expert_id, scheduled_at);

-- 定制穿搭方案表
CREATE TABLE custom_outfit_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_type VARCHAR(50) NOT NULL,        -- seasonal/event/wardrobe_optimization
    title VARCHAR(200) NOT NULL,
    description TEXT,
    plan_content JSONB NOT NULL,           -- 完整方案（衣物搭配+五行分析+购买建议）
    ai_generated BOOLEAN DEFAULT TRUE,
    expert_reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by INTEGER,
    valid_from DATE,
    valid_to DATE,
    price DECIMAL(10,2) NOT NULL,
    payment_id INTEGER REFERENCES payment_records(id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending/generating/completed/expired
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_custom_plans_user ON custom_outfit_plans(user_id, created_at DESC);
```

---

## 🔌 API 设计

### 品牌合作 API

```
# 品牌商品
GET    /api/v2/brands                       # 品牌列表
GET    /api/v2/brands/:id/products           # 品牌商品列表
GET    /api/v2/products/search               # 商品搜索（五行/风格/场景）
GET    /api/v2/products/:id                  # 商品详情

# 替代推荐
GET    /api/v2/recommend/:itemId/alternatives  # 相似商品推荐（品牌商品替代）

# 分销链接
POST   /api/v2/referrals/generate            # 生成分销链接
GET    /api/v2/referrals/click/:clickId       # 点击跳转（记录点击）
GET    /api/v2/referrals/my                   # 我的分销记录
GET    /api/v2/referrals/stats                # 分销统计

# 品牌联名活动
GET    /api/v2/campaigns                      # 活动列表
GET    /api/v2/campaigns/:id                  # 活动详情
```

### 付费运势 API

```
# 深度运势报告
GET    /api/v2/paid-reports/types             # 可购买报告类型
POST   /api/v2/paid-reports/order              # 购买报告
GET    /api/v2/paid-reports/:id                # 获取报告内容
GET    /api/v2/paid-reports/my                 # 我的报告列表

# 专家预约
GET    /api/v2/experts                        # 专家列表
GET    /api/v2/experts/:id                    # 专家详情
GET    /api/v2/experts/:id/slots              # 可预约时段
POST   /api/v2/experts/:id/book               # 预约专家
GET    /api/v2/sessions/my                    # 我的预约
POST   /api/v2/sessions/:id/cancel            # 取消预约
POST   /api/v2/sessions/:id/rate             # 评价预约

# 定制穿搭方案
GET    /api/v2/outfit-plans/types             # 方案类型
POST   /api/v2/outfit-plans/order              # 购买方案
GET    /api/v2/outfit-plans/:id                # 获取方案内容
GET    /api/v2/outfit-plans/my                # 我的方案列表

# 五行能量壁纸
POST   /api/v2/wallpaper/generate             # 生成五行壁纸
GET    /api/v2/wallpaper/my                    # 我的壁纸列表
GET    /api/v2/wallpaper/:id/download         # 下载壁纸
```

---

## 🎨 前端页面设计

### 1. 品牌商品推荐卡片

```
┌─────────────────────────────────────────┐
│ ← 推荐详情                               │
├─────────────────────────────────────────┤
│                                         │
│  ✨ 为您推荐相似单品                     │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ [你的衣物] 白衬衫  金属性        │   │
│  │                                 │   │
│  │  ↓ 相似品牌商品                  │   │
│  │                                 │   │
│  │  [图] 优衣库 白衬衫    ¥99      │   │
│  │  金属性 · 商务休闲               │   │
│  │  🔥 五行匹配度: 92%             │   │
│  │  [查看详情] [购买]              │   │
│  │                                 │   │
│  │  [图] ZARA 纯色衬衫    ¥159     │   │
│  │  金属性 · 时尚简约               │   │
│  │  🔥 五行匹配度: 87%             │   │
│  │  [查看详情] [购买]              │   │
│  └─────────────────────────────────┘   │
│                                         │
│  🎁 品牌联名活动                        │
│  ┌─────────────────────────────────┐   │
│  │ [图片] 五行联名系列 - 火之韵     │   │
│  │ ZARA x 顺衣尚 限定款             │   │
│  │ 8折优惠 · 仅剩3天               │   │
│  │ [立即查看]                      │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

### 2. 付费运势报告页

```
┌─────────────────────────────────────────┐
│ ← 运势报告                               │
├─────────────────────────────────────────┤
│                                         │
│  📖 深度运势报告                         │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 📅 年度运势详批          ¥99    │   │
│  │ 事业/财运/桃花/健康深度分析     │   │
│  │ 包含：大运流年+月度趋势+穿搭指导 │   │
│  │                          [购买]  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 🎯 事业运势专项          ¥59    │   │
│  │ 职场发展方向+贵人方位+穿搭建议   │   │
│  │                          [购买]  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 💕 桃花运势专项          ¥59    │   │
│  │ 感情趋势+桃花方位+穿搭开运      │   │
│  │                          [购买]  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  🎓 专家在线解读                        │
│  ┌─────────────────────────────────┐   │
│  │ [头像] 命理师 张老师             │   │
│  │ 从业15年 · 八字+风水             │   │
│  │ ⭐ 4.9 (238评价)                │   │
│  │ 1v1语音解读 ¥299/小时           │   │
│  │ 1v1视频解读 ¥399/小时           │   │
│  │                      [预约咨询] │   │
│  └─────────────────────────────────┘   │
│                                         │
│  🎨 五行能量壁纸                        │
│  ┌─────────────────────────────────┐   │
│  │ [预览图]                        │   │
│  │ 根据您的八字生成专属五行壁纸     │   │
│  │ 增强当日能量场                  │   │
│  │ ¥9.9/张                 [生成]  │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

---

## 💰 定价策略

### 付费报告定价

| 服务 | 价格 | 内容 |
|:---|:---:|:---|
| 年度运势详批 | ¥99 | 十年大运+流年+月度趋势+穿搭指导 |
| 事业运势专项 | ¥59 | 职场方向+贵人+穿搭建议 |
| 桃花运势专项 | ¥59 | 感情趋势+桃花方位+开运穿搭 |
| 财运专项 | ¥59 | 财富方位+投资建议+穿搭招财 |
| 完整命盘解读 | ¥199 | 完整八字+事业/感情/财运+年度指导 |

### 专家服务定价

| 服务 | 价格 | 说明 |
|:---|:---:|:---|
| 1v1语音咨询 | ¥299/小时 | 在线语音命理咨询 |
| 1v1视频咨询 | ¥399/小时 | 在线视频命理咨询 |
| 文字咨询 | ¥99/次 | 图文命理问答 |
| VIP年度服务 | ¥999 | 全年无限咨询+专属命理师 |

### 品牌分销分成

| 角色 | 分成比例 | 说明 |
|:---|:---:|:---|
| 品牌方 | 85% | 商品售价 |
| 平台 | 10% | 技术服务费 |
| 用户 | 5% | 返利积分（可兑换权益） |

---

## 🚨 风险分析

| 风险 | 影响 | 应对策略 |
|:---|:---|:---|
| 品牌对接周期长 | 高 | 先接入开放API品牌（淘宝联盟/京东联盟），再谈直签 |
| 付费转化率低 | 高 | 免费体验版引导，限时有优惠 |
| 专家资源稀缺 | 中 | 与命理师工作室合作，先签约3-5位 |
| 报告内容质量 | 高 | AI生成+专家审核双保险 |
| 分销佣金纠纷 | 中 | 清晰的分账规则+自动化结算 |
| 壁纸生成效果 | 中 | A/B测试多种风格，收集用户偏好 |

---

## ✅ 验收标准

### 品牌合作验收
- [ ] 品牌商品库可正常管理（CRUD）
- [ ] 推荐中"相似单品"正确展示品牌商品
- [ ] 分销链接生成和点击追踪正确
- [ ] 佣金分账计算准确
- [ ] 品牌联名活动页面正常

### 付费运势验收
- [ ] 深度运势报告生成时间<10秒
- [ ] 报告内容专业、准确、有穿搭指导
- [ ] 专家预约流程完整（选时段→支付→确认→咨询→评价）
- [ ] 定制穿搭方案由AI生成+专家审核
- [ ] 五行能量壁纸生成效果美观
- [ ] 付费内容权限控制正确（未购买不可查看）

---

## 📅 开发计划

| 天数 | 模块 | 任务 |
|:---:|:---|:---|
| Day 1 | 品牌 | 品牌库数据库+品牌商品管理 |
| Day 2 | 品牌 | 商品向量索引+相似推荐API |
| Day 3 | 品牌 | 分销链接系统+佣金追踪 |
| Day 4 | 品牌 | 品牌联名活动+前端商品卡片 |
| Day 5 | 付费 | 深度运势报告后端（AI生成） |
| Day 6 | 付费 | 运势报告前端+报告展示 |
| Day 7 | 付费 | 专家预约系统后端 |
| Day 8 | 付费 | 专家预约前端+时段管理 |
| Day 9 | 付费 | 定制穿搭方案（AI+专家审核） |
| Day 10 | 付费 | 五行能量壁纸生成 |

---

*创建时间: 2026-07-02*  
*状态: ⏳ 待开始*
