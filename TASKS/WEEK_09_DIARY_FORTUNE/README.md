# Week 9: 穿搭日记与每日运势系统

**周期**: Week 9  
**主题**: 构建用户粘性核心功能  
**状态**: ✅ 已完成（2026-07-01）  
**预估工时**: 50小时

---

## 🎯 本周目标

1. **穿搭日记系统**: 让用户每天记录穿搭，形成持续使用习惯
2. **每日运势推送**: 创造每日打开APP的理由
3. **VIP会员基础**: 建立商业化基础框架

---

## 📋 任务清单

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 | 状态 |
|:---:|------|:---:|:---:|:---:|:---|
| 01 | [数据库设计](./01_DATABASE/) | 🔴 高 | 2h | - | ✅ 已完成 |
| 02 | [穿搭日记API](./02_DIARY_API/) | 🔴 高 | 8h | 01 | ✅ 已完成 |
| 03 | [AI穿搭点评](./03_AI_COMMENT/) | 🔴 高 | 6h | 02 | ✅ 已完成 |
| 04 | [日记前端页面](./04_DIARY_FRONTEND/) | 🔴 高 | 10h | 02 | ✅ 已完成 |
| 05 | [每日运势系统](./05_FORTUNE/) | 🔴 高 | 10h | 01 | ✅ 已完成 |
| 06 | [推送通知](./06_PUSH/) | 🟡 中 | 6h | 05 | 📦 已迁移至 Week 10 |
| 07 | [VIP会员基础](./07_MEMBERSHIP/) | 🟡 中 | 8h | 01 | 📦 已迁移至 Week 10 |

> **注**: Task 06（推送通知）和 Task 07（VIP会员基础）在实现过程中整体迁移至 Week 10 统一开发，Week 10 已包含完整的推送通知系统和 VIP 会员体系。

---

## 🗄️ 核心数据模型

### 穿搭日记表 (outfit_diaries)

```sql
CREATE TABLE outfit_diaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    diary_date DATE NOT NULL,
    title VARCHAR(200),
    content TEXT,
    mood VARCHAR(50),           -- happy/sad/calm/excited/tired
    mood_score INTEGER,         -- 1-5
    weather_snapshot JSONB,     -- {temperature, weather, humidity}
    bazi_snapshot JSONB,        -- {day_master, elements}
    ai_comment TEXT,            -- AI点评
    ai_score DECIMAL(3,2),      -- AI评分 0-1
    is_public BOOLEAN DEFAULT FALSE,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, diary_date)
);

CREATE INDEX idx_diary_user_date ON outfit_diaries(user_id, diary_date DESC);
CREATE INDEX idx_diary_public ON outfit_diaries(is_public, created_at DESC);
```

### 日记关联衣物表 (diary_outfit_items)

```sql
CREATE TABLE diary_outfit_items (
    id SERIAL PRIMARY KEY,
    diary_id INTEGER NOT NULL REFERENCES outfit_diaries(id) ON DELETE CASCADE,
    item_type VARCHAR(20) NOT NULL,  -- upper/lower/outer/shoes/accessory
    wardrobe_item_id INTEGER REFERENCES user_wardrobe(id),
    public_item_code VARCHAR(50),
    custom_item_name VARCHAR(200),
    custom_item_image TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_diary_items_diary ON diary_outfit_items(diary_id);
```

### 每日运势表 (daily_fortune)

```sql
CREATE TABLE daily_fortune (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    fortune_date DATE NOT NULL,
    
    -- 运势评分 (1-5)
    overall_score INTEGER,
    career_score INTEGER,
    love_score INTEGER,
    wealth_score INTEGER,
    health_score INTEGER,
    
    -- 穿搭建议
    lucky_colors JSONB,         -- [{"color": "红色", "element": "火"}]
    lucky_elements JSONB,       -- ["火", "木"]
    avoid_colors JSONB,
    outfit_suggestions TEXT,
    
    -- 宜忌
    suitable_activities JSONB,
    avoid_activities JSONB,
    
    -- 元数据
    calculation_basis JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, fortune_date)
);

CREATE INDEX idx_fortune_user_date ON daily_fortune(user_id, fortune_date DESC);
```

---

## 🔌 API 设计

### 穿搭日记 API

```
# 日记 CRUD
POST   /api/v2/diary                    # 创建日记
GET    /api/v2/diary                    # 获取日记列表
GET    /api/v2/diary/:id                # 获取日记详情
GET    /api/v2/diary/date/:date         # 获取指定日期日记
PUT    /api/v2/diary/:id                # 更新日记
DELETE /api/v2/diary/:id                # 删除日记

# AI 功能
POST   /api/v2/diary/:id/ai-comment     # 生成AI点评
GET    /api/v2/diary/stats              # 五行能量统计

# 日历视图
GET    /api/v2/diary/calendar           # 日历数据
GET    /api/v2/diary/calendar/:year/:month  # 指定月份

# 关联衣物
POST   /api/v2/diary/:id/items          # 添加关联衣物
DELETE /api/v2/diary/:id/items/:itemId  # 移除关联衣物
```

### 每日运势 API

```
GET    /api/v2/fortune/today            # 获取今日运势
GET    /api/v2/fortune/date/:date       # 获取指定日期运势
GET    /api/v2/fortune/week             # 获取本周运势
GET    /api/v2/fortune/month            # 获取本月运势
```

### 请求/响应示例

**创建日记请求**:
```json
{
  "diary_date": "2026-04-17",
  "title": "清明节气穿搭",
  "content": "今天穿了白衬衫配黑西裤，感觉很专业",
  "mood": "happy",
  "mood_score": 4,
  "is_public": false,
  "items": [
    {
      "item_type": "upper",
      "wardrobe_item_id": 123
    },
    {
      "item_type": "lower",
      "public_item_code": "ITEM_001"
    }
  ]
}
```

**AI点评响应**:
```json
{
  "code": 0,
  "data": {
    "ai_comment": "今日穿搭金水相生，非常适合商务场合。白衬衫属金，黑西裤属水，形成金生水的良好能量流动。建议可以添加一条绿色领带（木属性），形成金生水、水生木的连续相生格局，有助于提升创造力和沟通能力。",
    "ai_score": 0.85,
    "element_analysis": {
      "金": 40,
      "水": 35,
      "木": 0,
      "火": 0,
      "土": 25
    },
    "suggestions": [
      {
        "type": "accessory",
        "suggestion": "绿色领带或丝巾",
        "element": "木",
        "reason": "补足木属性，形成连续相生"
      }
    ]
  }
}
```

---

## 🎨 前端页面设计

### 1. 日记列表页 (/diary)

```
┌─────────────────────────────────────────┐
│ ← 穿搭日记                    📅 日历   │
├─────────────────────────────────────────┤
│                                         │
│ 📅 2026年4月                            │
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 17日 · 清明                         ││
│ │ 今天穿了白衬衫配黑西裤...           ││
│ │ 😊 开心  ⭐⭐⭐⭐                    ││
│ │ [白衬衫] [黑西裤] [皮鞋]            ││
│ │ ✨ AI评分: 85分                     ││
│ └─────────────────────────────────────┘│
│                                         │
│ ┌─────────────────────────────────────┐│
│ │ 16日 · 清明                         ││
│ │ 周末约会，选了温柔风...             ││
│ │ 😊 开心  ⭐⭐⭐⭐⭐                  ││
│ │ [碎花裙] [小皮鞋]                   ││
│ │ ✨ AI评分: 92分                     ││
│ └─────────────────────────────────────┘│
│                                         │
├─────────────────────────────────────────┤
│              [＋ 写日记]                │
└─────────────────────────────────────────┘
```

### 2. 日记创建页 (/diary/new)

```
┌─────────────────────────────────────────┐
│ ← 写日记                          保存  │
├─────────────────────────────────────────┤
│                                         │
│ 📅 2026年4月17日 · 清明                │
│                                         │
│ 今日心情                                │
│ [😊 开心] [😌 平静] [😔 低落]          │
│ [🥰 幸福] [😤 疲惫]                     │
│                                         │
│ 评分 ⭐⭐⭐⭐☆                          │
│                                         │
│ 穿搭描述                                │
│ ┌─────────────────────────────────────┐│
│ │ 今天穿了...                         ││
│ └─────────────────────────────────────┘│
│                                         │
│ 添加衣物                                │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│ │ +上装│ │ +下装│ │ +外套│ │ +配饰│  │
│ └──────┘ └──────┘ └──────┘ └──────┘  │
│                                         │
│ 已添加:                                 │
│ ┌─────────────────────────────────────┐│
│ │ [图] 白衬衫    金☁️   [移除]        ││
│ │ [图] 黑西裤    水💧   [移除]        ││
│ └─────────────────────────────────────┘│
│                                         │
│ □ 公开到穿搭广场                        │
│                                         │
├─────────────────────────────────────────┤
│        [生成AI点评] [保存日记]          │
└─────────────────────────────────────────┘
```

### 3. 今日运势页 (/fortune)

```
┌─────────────────────────────────────────┐
│ ✨ 今日运势                             │
├─────────────────────────────────────────┤
│                                         │
│ 📅 2026年4月17日 · 星期五 · 清明       │
│                                         │
│ ┌─────────────────────────────────────┐│
│ │  整体运势  ⭐⭐⭐⭐☆               ││
│ │                                     ││
│ │  事业 ████████░░ 80%               ││
│ │  感情 █████████░ 90%               ││
│ │  财运 ██████░░░░ 60%               ││
│ │  健康 ████████░░ 80%               ││
│ └─────────────────────────────────────┘│
│                                         │
│ 🎨 今日穿搭建议                         │
│ ┌─────────────────────────────────────┐│
│ │ 幸运颜色: 🔴 红色 🟠 橙色           ││
│ │ 幸运五行: 🔥 火 🌍 土               ││
│ │ 忌讳颜色: ⚫ 黑色 🔵 深蓝           ││
│ └─────────────────────────────────────┘│
│                                         │
│ ✅ 今日宜                               │
│ • 面试洽谈 - 贵人运旺                  │
│ • 重要会议 - 表达能力强                │
│ • 社交活动 - 人缘极佳                  │
│                                         │
│ ⚠️ 今日忌                               │
│ • 重要决策 - 午后运势下降              │
│ • 大额投资 - 财运一般                  │
│                                         │
│ 💡 穿搭建议                             │
│ 今日火土相生，适合穿暖色系服装。        │
│ 建议选择红色/橙色上衣，搭配米色下装，   │
│ 可增强事业运势和人际魅力。              │
│                                         │
├─────────────────────────────────────────┤
│        [查看推荐穿搭] [分享运势]        │
└─────────────────────────────────────────┘
```

---

## 🧪 测试用例

### 日记功能测试

| 测试场景 | 输入 | 预期输出 |
|---------|------|---------|
| 创建日记 | 完整数据 | 成功创建，返回ID |
| 重复日期 | 同一日期再次创建 | 提示"该日期已有日记" |
| AI点评 | 请求AI点评 | 3秒内返回点评内容 |
| 关联衣物 | 关联不存在的衣物ID | 提示"衣物不存在" |
| 删除日记 | 删除有评论的日记 | 级联删除评论 |

### 运势功能测试

| 测试场景 | 输入 | 预期输出 |
|---------|------|---------|
| 首次获取运势 | 当天运势 | 自动生成并返回 |
| 二次获取运势 | 当天运势 | 返回已生成运势 |
| 无八字用户 | 当天运势 | 返回通用运势 |
| 跨日获取运势 | 新的一天 | 自动生成新运势 |

---

## ✅ 验收标准

### 功能验收

- [x] 用户可创建/编辑/删除穿搭日记
- [x] 日记可关联衣橱单品（最多10件）
- [x] AI点评生成时间<3秒，内容有意义
- [x] 日历视图正确展示历史日记
- [x] 每日运势5维度评分正确显示
- [x] 穿搭建议符合用户八字五行

### 性能验收

- [x] 日记列表加载时间<500ms
- [x] AI点评生成时间<3s
- [x] 运势计算时间<100ms
- [x] 日历视图渲染流畅

### 兼容性验收

- [x] iOS Safari 正常显示
- [x] Android Chrome 正常显示
- [x] 微信内置浏览器正常显示
- [x] 响应式布局适配手机/平板

---

## 📝 实现详情

### 后端实现

#### 数据库（3张新表）
- `outfit_diaries`：穿搭日记主表，含心情、天气快照、八字快照、AI点评
- `diary_outfit_items`：日记关联衣物表，支持衣橱单品和公共库商品
- `daily_fortune`：每日运势表，含五维度评分、幸运颜色/五行、宜忌事项

#### 后端 API
- **日记 CRUD**：10个端点（创建/列表/详情/日期查询/更新/删除/AI点评/统计/日历/关联衣物）
- **AI穿搭点评服务**：`ai_review_service.py` - 基于八字五行分析当日穿搭
- **五维度运势引擎**：`fortune_engine.py` - 综合/事业/感情/财运/健康五维度评分

### 前端实现

#### 页面
- 日记列表页（`/diary`）：瀑布流展示历史日记
- 日记创建页（`/diary/new`）：心情选择+穿搭描述+衣物关联
- 日记详情页（`/diary/:id`）：AI点评+五行能量分析
- 日历视图页（`/diary/calendar`）：月历展示穿搭记录
- 运势页（`/fortune`）：FortuneRadar 雷达图 + LuckyElements 幸运元素

#### Zustand Store
- `diary.ts`：日记列表、当前日记、创建/编辑状态
- `fortune.ts`：今日运势、运势历史、运势加载状态

---

## 🔮 命理进阶功能（已完成）

### 大运流年分析
- **文件**: `packages/utils/destiny_calculator.py`
- **功能**: 基于用户八字推算十年大运周期和流年运势
- **API**: `/api/v1/destiny/dayun` - 返回大运起运时间、各运五行属性、流年走势

### 十神关系解读
- **文件**: `packages/utils/ten_gods.py`
- **功能**: 分析日主与各天干地支的十神关系（比肩/劫财/食神/伤官/偏财/正财/七杀/正官/偏印/正印）
- **API**: `/api/v1/destiny/ten-gods` - 返回十神分布及性格/事业/感情影响解读

### 月度/年度运势
- **文件**: `packages/services/monthly_fortune_service.py`
- **功能**: 基于流月干支计算月度运势趋势，支持年度运势概览
- **API**: `/api/v1/destiny/monthly-fortune`、`/api/v1/destiny/yearly-fortune`

### 八字高级分析
- **文件**: `packages/utils/bazi_advanced.py`
- **功能**:
  - **纳音五行**：六十甲子纳音表，分析命主纳音五行属性
  - **地支藏干**：解析地支中隐藏的天干及五行
  - **刑冲克害**：分析地支间的刑、冲、克、害关系
- **API**: `/api/v1/destiny/advanced` - 返回纳音五行、藏干、刑冲克害分析

### 命理 API 端点汇总

```
GET    /api/v1/destiny/dayun               # 大运流年分析
GET    /api/v1/destiny/ten-gods            # 十神关系解读
GET    /api/v1/destiny/monthly-fortune     # 月度运势
GET    /api/v1/destiny/yearly-fortune      # 年度运势
GET    /api/v1/destiny/advanced            # 八字高级分析（纳音/藏干/刑冲克害）
GET    /api/v1/destiny/chart               # 完整命盘
```

---

## 📅 每日进度

| 日期 | 完成任务 | 备注 |
|------|---------|------|
| Day 1 | 数据库设计 + 日记API基础 | 3张新表创建完成 |
| Day 2 | 日记API完成 + AI点评 | 10个端点+AI点评服务 |
| Day 3 | 日记前端列表/创建页 | 日记列表+创建+详情页 |
| Day 4 | 日记前端详情/日历视图 | 日历组件+运势页面 |
| Day 5 | 运势系统后端 | 五维度运势引擎 |

---

*创建时间: 2026-04-17*  
*状态: ✅ 已完成（2026-07-01）*
