# Week 11-12: 穿搭广场社区与游戏化系统

**周期**: Week 11-12  
**主题**: 内容生态建设与用户激励体系  
**状态**: ✅ 已完成（2026-07-03）  
**预估工时**: 35小时  
**依赖**: Week 9-10 已完成（穿搭日记系统、VIP会员体系）

---

## 🎯 本周目标

1. **穿搭广场社区**: 构建 UGC 内容聚合平台，激发用户创作和社交互动
2. **关注系统**: 建立用户关系链，形成社区氛围
3. **话题标签**: 以五行搭配、场景穿搭等维度聚合内容
4. **游戏化激励**: 通过五行修炼、成就徽章、排行榜激励持续使用

---

## 📋 任务清单

### 模块一：穿搭广场社区（21小时）

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 |
|:---:|------|:---:|:---:|:---:|
| 01 | 广场信息流 | 🔴 高 | 6h | - |
| 02 | 关注系统 | 🟡 中 | 4h | - |
| 03 | 话题标签 | 🟡 中 | 3h | 01 |
| 04 | 搜索发现 | 🟡 中 | 4h | 03 |
| 05 | 内容审核 | 🔴 高 | 4h | 01 |

### 模块二：游戏化系统（14小时）

| 序号 | 任务 | 优先级 | 预估工时 | 依赖 |
|:---:|------|:---:|:---:|:---:|
| 06 | 五行修炼等级 | 🔴 高 | 4h | - |
| 07 | 穿搭成就 | 🟡 中 | 3h | 06 |
| 08 | 排行榜 | 🟡 中 | 3h | 06 |
| 09 | 每日任务 | 🟡 中 | 2h | 06 |
| 10 | 积分商城 | 🟡 中 | 2h | 06 |

---

## 🗄️ 数据库设计

### 穿搭广场社区表

```sql
-- 穿搭帖子表（从穿搭日记发布到广场）
CREATE TABLE community_posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    diary_id INTEGER REFERENCES outfit_diaries(id),
    title VARCHAR(200),
    description TEXT,
    images JSONB NOT NULL,              -- 帖子图片列表
    tags JSONB,                        -- 话题标签 ["今日穿搭", "五行搭配"]
    elements JSONB,                    -- 五行属性展示 {"金": 30, "木": 20, ...}
    scene VARCHAR(50),                 -- 场景标签（商务/约会/运动等）
    style VARCHAR(50),                 -- 风格标签（休闲/正式/复古等）
    is_featured BOOLEAN DEFAULT FALSE, -- 是否精选
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    collect_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',  -- pending_review/published/rejected
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_user ON community_posts(user_id, created_at DESC);
CREATE INDEX idx_posts_status ON community_posts(status, created_at DESC);
CREATE INDEX idx_posts_scene ON community_posts(scene, status);
CREATE INDEX idx_posts_featured ON community_posts(is_featured) WHERE is_featured = TRUE;

-- 点赞表
CREATE TABLE post_likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, post_id)
);

CREATE INDEX idx_likes_post ON post_likes(post_id);
CREATE INDEX idx_likes_user ON post_likes(user_id);

-- 评论表
CREATE TABLE post_comments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES post_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    like_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'published',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_comments_post ON post_comments(post_id, created_at);
CREATE INDEX idx_comments_parent ON post_comments(parent_id);

-- 用户关注表
CREATE TABLE user_follows (
    id SERIAL PRIMARY KEY,
    follower_id INTEGER NOT NULL REFERENCES users(id),
    following_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(follower_id, following_id),
    CHECK (follower_id != following_id)
);

CREATE INDEX idx_follows_follower ON user_follows(follower_id);
CREATE INDEX idx_follows_following ON user_follows(following_id);

-- 话题表
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    cover_image TEXT,
    category VARCHAR(50),              -- scene/element/style/season
    post_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_topics_category ON topics(category, sort_order);
```

### 游戏化系统表

```sql
-- 成就定义表
CREATE TABLE achievements (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    category VARCHAR(50),              -- diary/social/stylist/explorer/cultivation
    condition_type VARCHAR(50),       -- count/accumulate/special
    condition_value JSONB,
    reward_points INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- 用户成就表
CREATE TABLE user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    achievement_id INTEGER NOT NULL REFERENCES achievements(id),
    unlocked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX idx_user_ach_user ON user_achievements(user_id);

-- 排行榜表
CREATE TABLE leaderboards (
    id SERIAL PRIMARY KEY,
    leaderboard_type VARCHAR(50) NOT NULL,  -- weekly/monthly/all_time
    category VARCHAR(50) NOT NULL,           -- post_count/like_count/element_balance
    user_id INTEGER NOT NULL REFERENCES users(id),
    rank INTEGER NOT NULL,
    score NUMERIC(10,2) NOT NULL,
    period_start DATE,
    period_end DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_leaderboard_type_cat ON leaderboards(leaderboard_type, category, rank);

-- 每日任务表
CREATE TABLE daily_tasks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    task_type VARCHAR(50),             -- wear_element/post_diary/like_posts/complete_outfit
    target_value INTEGER NOT NULL,     -- 目标数量
    reward_points INTEGER DEFAULT 10,
    element_focus VARCHAR(20),         -- 关联五行（如"木"表示穿木属性衣物）
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户每日任务记录
CREATE TABLE user_daily_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    task_id INTEGER NOT NULL REFERENCES daily_tasks(id),
    task_date DATE NOT NULL,
    progress INTEGER DEFAULT 0,        -- 当前进度
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, task_id, task_date)
);

CREATE INDEX idx_user_daily_task ON user_daily_tasks(user_id, task_date);

-- 积分历史表
CREATE TABLE points_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,       -- diary_post/like_received/comment_received/sign_in/task_complete/achievement_unlock/spend
    points INTEGER NOT NULL,           -- 正数为获得，负数为消耗
    balance_after INTEGER NOT NULL,
    related_id INTEGER,                -- 关联ID（帖子ID/成就ID等）
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_points_user ON points_history(user_id, created_at DESC);
```

---

## 🔌 API 设计

### 穿搭广场 API

```
# 信息流
GET    /api/v2/community/feed              # 获取广场信息流（瀑布流）
GET    /api/v2/community/feed/hot          # 热门穿搭
GET    /api/v2/community/feed/following    # 关注用户动态
GET    /api/v2/community/feed/featured     # 精选穿搭

# 帖子操作
POST   /api/v2/community/posts             # 发布穿搭到广场
GET    /api/v2/community/posts/:id         # 获取帖子详情
DELETE /api/v2/community/posts/:id         # 删除帖子

# 互动
POST   /api/v2/community/posts/:id/like    # 点赞
DELETE /api/v2/community/posts/:id/like    # 取消点赞
POST   /api/v2/community/posts/:id/comments # 评论
GET    /api/v2/community/posts/:id/comments # 获取评论列表
POST   /api/v2/community/posts/:id/collect  # 收藏
DELETE /api/v2/community/posts/:id/collect  # 取消收藏

# 关注系统
POST   /api/v2/community/follow/:userId    # 关注用户
DELETE /api/v2/community/follow/:userId     # 取消关注
GET    /api/v2/community/followers          # 粉丝列表
GET    /api/v2/community/following          # 关注列表

# 话题
GET    /api/v2/community/topics             # 话题列表
GET    /api/v2/community/topics/:id/posts   # 话题下的帖子
GET    /api/v2/community/topics/hot         # 热门话题

# 搜索
GET    /api/v2/community/search             # 搜索穿搭
       ?keyword=&style=&scene=&element=&sort=
```

### 游戏化 API

```
# 五行修炼
GET    /api/v2/gamification/cultivation     # 获取修炼状态
GET    /api/v2/gamification/energy          # 五行能量分布

# 成就
GET    /api/v2/gamification/achievements    # 成就列表
GET    /api/v2/gamification/achievements/mine # 我的成就

# 排行榜
GET    /api/v2/gamification/leaderboard     # 排行榜
       ?type=weekly&category=post_count

# 每日任务
GET    /api/v2/gamification/daily-tasks     # 今日任务列表
POST   /api/v2/gamification/daily-tasks/:id/claim  # 领取任务奖励

# 积分
GET    /api/v2/gamification/points          # 积分余额
GET    /api/v2/gamification/points/history  # 积分记录
GET    /api/v2/gamification/shop            # 积分商城
POST   /api/v2/gamification/shop/:id/exchange  # 积分兑换
```

---

## 🎨 前端页面设计

### 1. 穿搭广场首页 (/community)

```
┌─────────────────────────────────────────┐
│ 穿搭广场                    🔍 搜索      │
├─────────────────────────────────────────┤
│ [推荐] [关注] [热门] [精选]             │
├─────────────────────────────────────────┤
│                                         │
│ #今日穿搭  #五行搭配  #职场穿搭  更多 → │
│                                         │
│ ┌──────────┐  ┌──────────┐             │
│ │ [图片]   │  │ [图片]   │             │
│ │          │  │          │             │
│ │ @用户名  │  │ @用户名  │             │
│ │ 🔥木 🌍土│  │ 💧水 🔥火│             │
│ │ ❤️ 234   │  │ ❤️ 156   │             │
│ │ 💬 45    │  │ 💬 28    │             │
│ └──────────┘  └──────────┘             │
│                                         │
│ ┌──────────┐  ┌──────────┐             │
│ │ [图片]   │  │ [图片]   │             │
│ │ ...      │  │ ...      │             │
│ └──────────┘  └──────────┘             │
│                                         │
├─────────────────────────────────────────┤
│  [首页] [推荐] [广场] [日记] [我的]    │
└─────────────────────────────────────────┘
```

### 2. 五行修炼页面 (/cultivation)

```
┌─────────────────────────────────────────┐
│ ← 五行修炼                               │
├─────────────────────────────────────────┤
│                                         │
│  🏆 当前境界：五行初识                   │
│  下一境界：五行通悟 (还需 200 经验)     │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │        五行能量分布              │   │
│  │                                  │   │
│  │    木 ████████░░ 80%            │   │
│  │    火 ██████░░░░ 60%            │   │
│  │    土 ████░░░░░░ 40%            │   │
│  │    金 ███████░░░ 70%            │   │
│  │    水 █████░░░░░ 50%            │   │
│  │                                  │   │
│  │  最旺：木  最弱：土              │   │
│  │  建议：多穿土属性衣物平衡五行     │   │
│  └──────────────────────────────────┘   │
│                                         │
│  📋 今日修炼任务                        │
│  ┌──────────────────────────────────┐   │
│  │ ☐ 穿一件木属性单品    +10 积分   │   │
│  │ ☐ 发布穿搭日记        +10 积分   │   │
│  │ ☐ 给3位穿搭点赞       +5 积分   │   │
│  │ ☑ 完成今日运势查看    +5 积分   │   │
│  └──────────────────────────────────┘   │
│                                         │
│  🏅 成就徽章                            │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐          │
│  │ ✅ │ │ ✅ │ │ 🔒 │ │ 🔒 │          │
│  │连续 │ │场景 │ │五行 │ │社交 │          │
│  │打卡 │ │达人 │ │平衡 │ │之星 │          │
│  └────┘ └────┘ └────┘ └────┘          │
│                                         │
│  📊 排行榜                              │
│  ┌──────────────────────────────────┐   │
│  │ 1. @穿搭达人    1280 积分        │   │
│  │ 2. @五行少女     980 积分        │   │
│  │ 3. @时尚先锋     850 积分        │   │
│  │ ...                              │   │
│  │ 15. 我             320 积分      │   │
│  └──────────────────────────────────┘   │
│                                         │
├─────────────────────────────────────────┤
│         [积分商城] [查看全部成就]        │
└─────────────────────────────────────────┘
```

---

## 🎮 游戏化设计详情

### 五行修炼等级体系

| 境界 | 经验要求 | 解锁权益 |
|:---|:---:|:---|
| 五行初识 | 0 | 基础功能 |
| 五行入门 | 500 | 解锁每日任务 |
| 五行通悟 | 2000 | 专属头像框 |
| 五行精通 | 5000 | 积分双倍卡 |
| 五行大师 | 10000 | 专属称号+优先曝光 |

### 成就徽章设计

| 成就 | 条件 | 奖励积分 |
|:---|:---|:---:|
| 连续打卡7天 | 连续7天发布日记 | 50 |
| 连续打卡30天 | 连续30天发布日记 | 200 |
| 场景达人 | 覆盖10种场景穿搭 | 100 |
| 五行平衡 | 单次穿搭五行全覆盖 | 80 |
| 社交之星 | 获得100个点赞 | 100 |
| 穿搭配色师 | 发布20种不同配色搭配 | 150 |
| 季节穿搭师 | 完成四季穿搭记录 | 200 |

### 积分规则

| 行为 | 积分 | 每日上限 |
|:---|:---:|:---:|
| 发布穿搭日记 | +10 | 10 |
| 发布到广场 | +5 | 5 |
| 获得点赞 | +2 | 无限 |
| 获得评论 | +3 | 无限 |
| 连续签到 | +5~20 | 20 |
| 完成每日任务 | +5~15 | 30 |
| 解锁成就 | +50~200 | 无限 |
| 邀请好友 | +50 | 无限 |

---

## 🚨 风险分析

| 风险 | 影响 | 应对策略 |
|:---|:---|:---|
| 内容质量参差不齐 | 高 | AI辅助审核+人工审核，低质量内容降权 |
| 社区冷启动困难 | 高 | 种子用户计划，官方精选内容填充 |
| 恶意刷积分 | 中 | 每日积分上限+行为频率限制+异常检测 |
| 五行修炼平衡性 | 中 | 持续监控数据，动态调整经验值 |
| 性能瓶颈 | 中 | 信息流分页加载+Redis缓存热门帖子 |

---

## ✅ 验收标准

### 穿搭广场验收
- [ ] 信息流瀑布流加载流畅（首屏<2秒）
- [ ] 发布穿搭到广场流程完整
- [ ] 点赞/评论实时更新
- [ ] 关注关系正确建立和推送
- [ ] 话题标签聚合正确
- [ ] 搜索支持多维度筛选

### 游戏化验收
- [ ] 五行修炼等级正确计算
- [ ] 成就解锁触发正确
- [ ] 排行榜实时更新
- [ ] 每日任务刷新正确
- [ ] 积分系统计算准确
- [ ] 积分商城兑换流程完整

---

## 📅 开发计划

| 天数 | 模块 | 任务 |
|:---:|:---|:---|
| Day 1 | 广场 | 数据库设计 + 信息流API |
| Day 2 | 广场 | 发布/点赞/评论 API |
| Day 3 | 广场 | 关注系统 + 话题标签 |
| Day 4 | 广场 | 搜索 + 内容审核 |
| Day 5 | 广场 | 前端广场首页 + 帖子详情 |
| Day 6 | 广场 | 前端发布流程 + 互动组件 |
| Day 7 | 游戏化 | 五行修炼等级系统 |
| Day 8 | 游戏化 | 成就徽章系统 |
| Day 9 | 游戏化 | 排行榜 + 每日任务 |
| Day 10 | 游戏化 | 积分商城 + 前端页面 |

---

*创建时间: 2026-07-02*  
*状态: ⏳ 待开始*
