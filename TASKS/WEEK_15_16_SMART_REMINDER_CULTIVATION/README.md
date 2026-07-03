# Week 15-16: 智能提醒系统与五行修炼系统

**周期**: Week 15-16  
**主题**: 生态完善与深度用户留存  
**状态**: ✅ 已完成（2026-07-03）  
**预估工时**: 25小时  
**依赖**: Week 9-10 已完成（穿搭日记、每日运势、推送系统）、Week 11-12 已完成（游戏化基础）

---

## 🎯 本周目标

1. **智能提醒系统**: 天气/运势/衣橱/场景四维联动提醒，创造自然回访触发点
2. **五行修炼系统**: 可视化五行能量图谱，通过穿搭行为修炼五行能量
3. **修炼境界进阶**: 从"五行初识"到"五行大师"的完整境界体系
4. **五行相生组合**: 发现并奖励符合相生原理的搭配（木生火/火生土/土生金/金生水/水生木）

---

## 📋 任务清单

### 模块一：智能提醒系统（12小时）

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 |
|:---:|------|:---:|:---:|:---:|
| 01 | 天气联动提醒 | 🔴 高 | 4h | - |
| 02 | 运势提醒 | 🔴 高 | 3h | - |
| 03 | 衣橱管理提醒 | 🟡 中 | 3h | - |
| 04 | 场景提醒 | 🟡 中 | 2h | - |

### 模块二：五行修炼系统（13小时）

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 |
|:---:|------|:---:|:---:|:---:|
| 05 | 五行能量图谱 | 🔴 高 | 3h | - |
| 06 | 修炼任务 | 🔴 高 | 3h | 05 |
| 07 | 能量加持 | 🟡 中 | 2h | 05 |
| 08 | 五行相生组合 | 🔴 高 | 3h | 05 |
| 09 | 修炼境界 | 🟡 中 | 2h | 05 |

---

## 🗄️ 数据库设计

### 智能提醒系统表

```sql
-- 提醒规则表（系统级配置）
CREATE TABLE reminder_rules (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    rule_type VARCHAR(50) NOT NULL,        -- weather/fortune/wardrobe/scene
    rule_name VARCHAR(200) NOT NULL,
    description TEXT,
    trigger_condition JSONB NOT NULL,       -- 触发条件配置
    action_type VARCHAR(50) NOT NULL,       -- push/in_app/email
    action_content JSONB,                   -- 推送内容模板
    priority INTEGER DEFAULT 5,             -- 优先级 1-10
    cooldown_hours INTEGER DEFAULT 24,      -- 冷却时间（小时）
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 天气提醒记录表
CREATE TABLE weather_reminders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    reminder_type VARCHAR(50) NOT NULL,    -- temperature_drop/rain/heatwave/cold_wave
    weather_data JSONB,                     -- 触发天气数据
    outfit_suggestion TEXT,                 -- 穿搭建议
    pushed_at TIMESTAMP DEFAULT NOW(),
    read_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',      -- sent/read/clicked
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_weather_reminder_user ON weather_reminders(user_id, pushed_at DESC);

-- 场景提醒表（日历事件关联）
CREATE TABLE scene_reminders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_name VARCHAR(200) NOT NULL,       -- 事件名称（面试/约会/婚礼等）
    event_date DATE NOT NULL,
    event_scene VARCHAR(50),                -- 关联场景
    advance_days INTEGER DEFAULT 1,         -- 提前几天提醒
    outfit_plan_id INTEGER,                 -- 关联穿搭方案
    status VARCHAR(20) DEFAULT 'pending',   -- pending/reminded/completed
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_scene_reminder_user ON scene_reminders(user_id, event_date);
```

### 五行修炼系统表

```sql
-- 五行能量记录表
CREATE TABLE energy_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    record_date DATE NOT NULL,
    element_type VARCHAR(20) NOT NULL,      -- metal/wood/water/fire/earth
    energy_value INTEGER NOT NULL,           -- 能量值
    source VARCHAR(50) NOT NULL,            -- diary/wardrobe/recommendation/cultivation_task
    source_id INTEGER,                      -- 关联ID
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_energy_user_date ON energy_records(user_id, record_date DESC);
CREATE INDEX idx_energy_element ON energy_records(user_id, element_type, record_date DESC);

-- 修炼任务定义表
CREATE TABLE cultivation_tasks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,         -- wear_element/balance_elements/combo_element/continuous
    target_element VARCHAR(20),             -- 目标五行（如穿木属性衣物）
    target_value INTEGER NOT NULL,          -- 目标数量
    energy_reward JSONB NOT NULL,           -- {"wood": 10, "fire": 5}
    points_reward INTEGER DEFAULT 10,
    difficulty VARCHAR(20) DEFAULT 'normal', -- easy/normal/hard
    duration_days INTEGER DEFAULT 1,         -- 任务持续天数
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户修炼任务记录
CREATE TABLE user_cultivation_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    task_id INTEGER NOT NULL REFERENCES cultivation_tasks(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    progress INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    energy_gained JSONB,                   -- 获得的能量
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_cultivation_user ON user_cultivation_tasks(user_id, start_date DESC);

-- 能量加持记录表
CREATE TABLE energy_bonuses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    bonus_type VARCHAR(50) NOT NULL,        -- consecutive_element/season_bonus/festival_bonus
    element_type VARCHAR(20) NOT NULL,
    bonus_value INTEGER NOT NULL,
    consecutive_count INTEGER,              -- 连续穿搭同五行的天数
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_energy_bonus_user ON energy_bonuses(user_id, created_at DESC);

-- 五行相生组合记录表
CREATE TABLE element_combos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    diary_id INTEGER REFERENCES outfit_diaries(id),
    combo_type VARCHAR(50) NOT NULL,        -- wood_fire/fire_earth/earth_metal/metal_water/water_wood
    combo_elements JSONB NOT NULL,          -- {"generating": "木", "generated": "火", "count": 2}
    balance_score DECIMAL(3,2),             -- 平衡度评分
    energy_bonus INTEGER DEFAULT 0,          -- 组合加成能量
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_element_combos_user ON element_combos(user_id, detected_at DESC);
CREATE INDEX idx_element_combos_type ON element_combos(combo_type);

-- 修炼境界表
CREATE TABLE cultivation_realms (
    id SERIAL PRIMARY KEY,
    realm_code VARCHAR(50) UNIQUE NOT NULL,
    realm_name VARCHAR(100) NOT NULL,
    description TEXT,
    min_total_energy INTEGER NOT NULL,      -- 达到该境界所需总能量
    required_elements JSONB,                -- 各五行最低能量要求 {"metal": 100, "wood": 100, ...}
    unlock_benefits JSONB,                  -- 解锁权益
    icon_url TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户修炼境界记录
CREATE TABLE user_cultivation_realms (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    realm_id INTEGER NOT NULL REFERENCES cultivation_realms(id),
    total_energy INTEGER DEFAULT 0,
    element_energies JSONB DEFAULT '{"metal": 0, "wood": 0, "water": 0, "fire": 0, "earth": 0}',
    current_realm VARCHAR(50),
    next_realm VARCHAR(50),
    progress_to_next DECIMAL(5,2),          -- 距下一境界进度百分比
    reached_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX idx_user_realm_realm ON user_cultivation_realms(current_realm);
```

---

## 🔌 API 设计

### 智能提醒 API

```
# 提醒设置
GET    /api/v2/reminders/settings            # 获取提醒设置
PUT    /api/v2/reminders/settings            # 更新提醒设置

# 天气提醒
GET    /api/v2/reminders/weather              # 获取天气提醒列表
POST   /api/v2/reminders/weather/test         # 测试天气提醒（管理员）

# 运势提醒
GET    /api/v2/reminders/fortune              # 获取运势提醒列表

# 衣橱提醒
GET    /api/v2/reminders/wardrobe             # 获取衣橱管理建议
# 返回：换季整理提醒、闲置衣物提醒、衣物轮换建议

# 场景提醒
GET    /api/v2/reminders/scene                # 获取场景提醒列表
POST   /api/v2/reminders/scene                # 创建场景提醒（关联日历事件）
DELETE /api/v2/reminders/scene/:id            # 删除场景提醒
```

### 五行修炼 API

```
# 五行能量图谱
GET    /api/v2/cultivation/energy             # 获取五行能量分布
GET    /api/v2/cultivation/energy/trend        # 获取能量趋势（按月/季/年）
GET    /api/v2/cultivation/energy/breakdown   # 获取能量来源分析

# 修炼任务
GET    /api/v2/cultivation/tasks              # 获取可领取的修炼任务
POST   /api/v2/cultivation/tasks/:id/accept    # 领取修炼任务
GET    /api/v2/cultivation/tasks/active         # 获取进行中的任务
POST   /api/v2/cultivation/tasks/:id/claim      # 领取任务奖励

# 能量加持
GET    /api/v2/cultivation/bonuses             # 获取能量加成记录
GET    /api/v2/cultivation/bonuses/streak      # 获取连续穿搭加成状态

# 五行相生组合
GET    /api/v2/cultivation/combos              # 获取相生组合记录
GET    /api/v2/cultivation/combos/stats        # 相生组合统计

# 修炼境界
GET    /api/v2/cultivation/realm               # 获取当前境界
GET    /api/v2/cultivation/realm/list           # 所有境界列表
GET    /api/v2/cultivation/realm/progress       # 境界进阶进度
```

---

## 🎨 前端页面设计

### 1. 智能提醒中心 (/reminders)

```
┌─────────────────────────────────────────┐
│ ← 智能提醒                               │
├─────────────────────────────────────────┤
│                                         │
│  🌤️ 天气穿搭提醒                         │
│  ┌──────────────────────────────────┐  │
│  │ 明日降温至 5°C                    │  │
│  │ 建议穿着：厚外套+毛衣+长裤         │  │
│  │ 您的衣橱中有3件适合的厚外套        │  │
│  │                       [查看推荐] │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ✨ 运势提醒                             │
│  ┌──────────────────────────────────┐  │
│  │ 明日运势：⭐⭐⭐⭐☆               │  │
│  │ 幸运色：红色 🟠 橙色              │  │
│  │ 忌讳色：⚫ 黑色                   │  │
│  │ 建议穿暖色系，增强火元素           │  │
│  │                       [查看详情] │  │
│  └──────────────────────────────────┘  │
│                                         │
│  👔 衣橱管理提醒                         │
│  ┌──────────────────────────────────┐  │
│  │ 🔄 换季整理提醒                   │  │
│  │ 有5件夏季衣物建议收纳             │  │
│  │                       [去整理]   │  │
│  │                                  │  │
│  │ ⏰ 闲置衣物提醒                   │  │
│  │ 有3件衣物超过30天未穿着           │  │
│  │                       [查看]     │  │
│  └──────────────────────────────────┘  │
│                                         │
│  📅 场景提醒                             │
│  ┌──────────────────────────────────┐  │
│  │ 后天 · 面试                       │  │
│  │ 建议穿搭：商务正式风               │  │
│  │ 提前1天准备穿搭方案               │  │
│  │                       [准备穿搭] │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### 2. 五行修炼详情页 (/cultivation/detail)

```
┌─────────────────────────────────────────┐
│ ← 五行修炼                               │
├─────────────────────────────────────────┤
│                                         │
│  🏆 当前境界：五行通悟                   │
│  总能量：3,250                          │
│  下一境界：五行精通 (还需 1,750)        │
│  ████████████░░░░░░░ 65%                │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │       五行能量分布图             │  │
│  │                                  │  │
│  │          🔥 火 850              │  │
│  │           /  \                   │  │
│  │     🌳木    🌍土                 │  │
│  │     720    580                   │  │
│  │        \  /                      │  │
│  │     💧水   ⚙️金                   │  │
│  │     650    450                   │  │
│  │                                  │  │
│  │  最旺：🔥 火 (850)               │  │
│  │  最弱：⚙️ 金 (450)               │  │
│  │  建议：多穿白色/金色系衣物补金    │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ⚡ 能量加成                             │
│  ┌──────────────────────────────────┐  │
│  │ 🔥 连续火属性穿搭 5天 → +50能量  │  │
│  │ 🌸 春季木属性加成 → +20%         │  │
│  └──────────────────────────────────┘  │
│                                         │
│  🔄 五行相生组合                         │
│  ┌──────────────────────────────────┐  │
│  │ 本周发现：                       │  │
│  │ ✅ 木生火 (绿色上衣+红色下装)    │  │
│  │ ✅ 火生土 (红色上衣+黄色裙装)    │  │
│  │ 🔒 土生金 (未达成)               │  │
│  │ 🔒 金生水 (未达成)               │  │
│  │ 🔒 水生木 (未达成)               │  │
│  │                                  │  │
│  │ 💡 穿搭含相生组合可获得能量加成  │  │
│  └──────────────────────────────────┘  │
│                                         │
│  📋 修炼任务                             │
│  ┌──────────────────────────────────┐  │
│  │ ☐ 补金计划                       │  │
│  │ 连续3天穿金属性衣物               │  │
│  │ 进度：1/3天  奖励：+100金能量    │  │
│  │                       [领取]     │  │
│  │                                  │  │
│  │ ☐ 五行平衡大师                    │  │
│  │ 一次穿搭包含全部五行              │  │
│  │ 奖励：+200总能量 +平衡徽章       │  │
│  │                       [领取]     │  │
│  └──────────────────────────────────┘  │
│                                         │
│  📊 能量趋势（近30天）                   │
│  ┌──────────────────────────────────┐  │
│  │ [折线图]                         │  │
│  │ 木 ████████░░░░                  │  │
│  │ 火 ██████████░░                  │  │
│  │ 土 █████░░░░░░░                  │  │
│  │ 金 ███░░░░░░░░░                  │  │
│  │ 水 ██████░░░░░░                  │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🔮 五行修炼系统设计

### 修炼境界体系

| 境界 | 总能量 | 各五行要求 | 解锁权益 |
|:---|:---:|:---|:---|
| 五行初识 | 0 | 无 | 基础功能 |
| 五行入门 | 500 | 每项≥50 | 每日任务解锁 |
| 五行通悟 | 2,000 | 每项≥200 | 专属头像框 |
| 五行精通 | 5,000 | 每项≥500 | 积分双倍卡 |
| 五行宗师 | 10,000 | 每项≥1,000 | 专属称号 |
| 五行大师 | 20,000 | 每项≥2,000 | 广场优先曝光+专属徽章 |

### 五行相生组合

五行相生是传统文化中的核心概念，系统通过检测穿搭中的五行组合来奖励用户：

| 相生关系 | 含义 | 搭配示例 | 能量加成 |
|:---|:---|:---|:---:|
| 木生火 | 木属性衣物+火属性衣物 | 绿色上衣+红色下装 | +30 |
| 火生土 | 火属性衣物+土属性衣物 | 红色上衣+黄色裙装 | +30 |
| 土生金 | 土属性衣物+金属性衣物 | 棕色外套+白色衬衫 | +30 |
| 金生水 | 金属性衣物+水属性衣物 | 白色上衣+黑色裤子 | +30 |
| 水生木 | 水属性衣物+木属性衣物 | 黑色外套+绿色围巾 | +30 |

> **全相生加成**：若一次穿搭中同时存在全部五种相生关系，额外奖励 +200 能量。

### 能量获取途径

| 行为 | 获取能量 | 说明 |
|:---|:---:|:---|
| 发布穿搭日记 | 各穿衣物对应五行 +10 | 每件衣物按其五行属性增加对应能量 |
| 完成修炼任务 | 任务指定 +50~100 | 根据任务难度和类型 |
| 五行相生组合 | +30/组 | 穿搭中包含相生关系 |
| 连续穿搭同五行 | +10~50 | 连续3天/7天/14天/30天递增 |
| 季节加成 | +20% | 春季穿木属性、夏季穿火属性等 |
| 节气加成 | +50 | 节气当日穿对应五行衣物 |

### 修炼任务示例

| 任务 | 描述 | 难度 | 奖励 |
|:---|:---|:---:|:---|
| 补金计划 | 连续3天穿金属性衣物 | normal | +100金能量 |
| 木火通明 | 穿搭同时包含木和火属性 | easy | +30总能量 |
| 五行平衡 | 一次穿搭包含全部五行 | hard | +200总能量+徽章 |
| 火土相生 | 穿搭包含火生土组合 | normal | +50总能量 |
| 连续打卡 | 连续7天发布穿搭日记 | normal | +70总能量 |
| 季节穿搭 | 完成当季四种五行穿搭 | hard | +150总能量 |

---

## 🚨 风险分析

| 风险 | 影响 | 应对策略 |
|:---|:---|:---|
| 天气API不稳定 | 高 | 多源天气数据备份，降级使用缓存数据 |
| 提醒频率过高导致用户反感 | 高 | 智能频率控制，用户可自定义提醒偏好 |
| 五行能量计算复杂 | 中 | 充分单元测试，验证各场景计算逻辑 |
| 修炼系统平衡性 | 中 | 持续监控数据，动态调整能量获取速率 |
| 用户对五行概念理解不足 | 中 | 新手引导+知识科普模块 |

---

## ✅ 验收标准

### 智能提醒验收
- [ ] 降温/降雨前正确推送穿搭建议
- [ ] 每日运势准时推送（基于用户设置的推送时间）
- [ ] 换季时自动提醒衣橱整理
- [ ] 日历事件关联穿搭提醒正确
- [ ] 提醒频率可控（用户可关闭/开启各类提醒）
- [ ] 提醒内容个性化（基于用户八字和衣橱数据）

### 五行修炼验收
- [ ] 五行能量图谱正确展示分布
- [ ] 能量趋势图按时间维度正确渲染
- [ ] 修炼任务领取/完成/奖励发放正确
- [ ] 连续穿搭同五行加成计算正确
- [ ] 五行相生组合自动检测准确
- [ ] 修炼境界升级逻辑正确
- [ ] 各境界权益正确解锁

---

## 📅 开发计划

| 天数 | 模块 | 任务 |
|:---:|:---|:---|
| Day 1 | 提醒 | 提醒规则引擎 + 天气联动提醒 |
| Day 2 | 提醒 | 运势提醒 + 衣橱管理提醒 |
| Day 3 | 提醒 | 场景提醒（日历关联）+ 提醒中心前端 |
| Day 4 | 修炼 | 五行能量记录 + 能量图谱后端 |
| Day 5 | 修炼 | 能量图谱前端 + 趋势图表 |
| Day 6 | 修炼 | 修炼任务系统 + 能量加持 |
| Day 7 | 修炼 | 五行相生组合检测 + 境界进阶 |
| Day 8 | 修炼 | 修炼详情页前端 + 集成测试 |
| Day 9 | 全部 | 联调测试 + 性能优化 |
| Day 10 | 全部 | Bug修复 + 验收 |

---

*创建时间: 2026-07-02*  
*状态: ⏳ 待开始*
