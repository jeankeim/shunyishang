-- Migration 08: 游戏化系统 - 积分、成就、五行修炼等级
-- 参考: WEEK_11_12_COMMUNITY_GAMIFY/README.md 模块二

-- ========== 成就定义表 ==========
CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,             -- 成就编码: daily_7, daily_30, wuxing_balance, scene_master
    name VARCHAR(100) NOT NULL,                    -- 成就名称
    description TEXT,                              -- 成就描述
    icon VARCHAR(10) DEFAULT '🏆',                 -- 图标 emoji
    category VARCHAR(30) NOT NULL,                 -- 分类: streak / wuxing / social / special
    requirement_type VARCHAR(30) NOT NULL,         -- 条件类型: diary_streak / total_diaries / community_likes / element_balance
    requirement_value INTEGER NOT NULL DEFAULT 1,  -- 达标数值
    points_reward INTEGER NOT NULL DEFAULT 50,     -- 积分奖励
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE achievements IS '成就定义表（系统预设）';

-- ========== 用户成就关联表 ==========
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, achievement_id)
);

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

COMMENT ON TABLE user_achievements IS '用户已解锁成就';

-- ========== 积分历史表 ==========
CREATE TABLE IF NOT EXISTS points_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    points INTEGER NOT NULL,                       -- 正=获得, 负=消耗
    reason VARCHAR(50) NOT NULL,                   -- 原因编码: diary_create / community_like / daily_streak / achievement_unlock
    reference_id INTEGER,                          -- 关联记录ID（日记ID/帖子ID等）
    balance_after INTEGER NOT NULL DEFAULT 0,      -- 操作后余额
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_points_user ON points_history(user_id, created_at DESC);

COMMENT ON TABLE points_history IS '积分变动历史';

-- ========== 用户积分总览表 ==========
CREATE TABLE IF NOT EXISTS user_points (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    total_points INTEGER NOT NULL DEFAULT 0,       -- 累计获得积分
    current_points INTEGER NOT NULL DEFAULT 0,     -- 当前可用积分
    cultivation_level INTEGER NOT NULL DEFAULT 1,  -- 修炼等级 1-5
    streak_days INTEGER NOT NULL DEFAULT 0,        -- 连续签到天数
    last_checkin_date DATE,                        -- 最近签到日期
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE user_points IS '用户积分与修炼等级总览';

-- ========== 预设成就数据 ==========
INSERT INTO achievements (code, name, description, icon, category, requirement_type, requirement_value, points_reward) VALUES
    ('daily_7', '连续打卡7天', '连续7天记录穿搭日记', '🔥', 'streak', 'diary_streak', 7, 50),
    ('daily_30', '月度达人', '连续30天记录穿搭日记', '🌟', 'streak', 'diary_streak', 30, 200),
    ('daily_100', '百日修行', '累计记录100天穿搭日记', '💎', 'streak', 'total_diaries', 100, 500),
    ('wuxing_balance', '五行平衡', '衣橱五行分布均衡', '☯️', 'wuxing', 'element_balance', 5, 100),
    ('community_liked_10', '人气穿搭', '获得10次点赞', '❤️', 'social', 'community_likes', 10, 30),
    ('community_liked_50', '穿搭达人', '获得50次点赞', '👑', 'social', 'community_likes', 50, 100),
    ('first_diary', '初识穿搭', '创建第一篇穿搭日记', '📝', 'special', 'total_diaries', 1, 10),
    ('first_post', '广场新星', '在穿搭广场发布第一篇帖子', '✨', 'social', 'community_posts', 1, 15)
ON CONFLICT (code) DO NOTHING;

COMMENT ON COLUMN achievements.requirement_type IS 'diary_streak=连续打卡天数, total_diaries=总日记数, community_likes=获赞数, element_balance=五行均衡度, community_posts=发帖数';
