-- =====================================================
-- Week 9: 穿搭日记 & 每日运势 数据库迁移
-- =====================================================

-- outfit_diaries: 穿搭日记主表
CREATE TABLE IF NOT EXISTS outfit_diaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    diary_date DATE NOT NULL,
    mood VARCHAR(20),  -- happy/neutral/sad/excited/calm
    weather_snapshot JSONB DEFAULT '{}',
    occasion VARCHAR(50),
    notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    ai_review JSONB DEFAULT '{}',  -- AI点评结果 {score, comment, suggestions}
    image_urls JSONB DEFAULT '[]',  -- 穿搭照片URL列表
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, diary_date)
);

-- diary_outfit_items: 日记关联衣物
CREATE TABLE IF NOT EXISTS diary_outfit_items (
    id SERIAL PRIMARY KEY,
    diary_id INTEGER NOT NULL REFERENCES outfit_diaries(id) ON DELETE CASCADE,
    item_source VARCHAR(20) DEFAULT 'wardrobe',  -- wardrobe/seed
    wardrobe_item_id INTEGER REFERENCES user_wardrobe(id) ON DELETE SET NULL,
    seed_item_code VARCHAR(50) REFERENCES items(item_code) ON DELETE SET NULL,
    category VARCHAR(50),
    notes VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- daily_fortune: 每日运势
CREATE TABLE IF NOT EXISTS daily_fortune (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fortune_date DATE NOT NULL,
    scores JSONB NOT NULL,  -- {career: 85, wealth: 70, love: 90, health: 75, study: 80}
    overall_score INTEGER,
    advice_text TEXT,
    lucky_elements JSONB DEFAULT '{}',  -- {colors: [...], materials: [...], directions: [...]}
    outfit_suggestion TEXT,
    bazi_snapshot JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, fortune_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_outfit_diaries_user_date ON outfit_diaries(user_id, diary_date DESC);
CREATE INDEX IF NOT EXISTS idx_outfit_diaries_mood ON outfit_diaries(mood);
CREATE INDEX IF NOT EXISTS idx_diary_outfit_items_diary ON diary_outfit_items(diary_id);
CREATE INDEX IF NOT EXISTS idx_daily_fortune_user_date ON daily_fortune(user_id, fortune_date DESC);

-- updated_at 触发器
DROP TRIGGER IF EXISTS update_outfit_diaries_updated_at ON outfit_diaries;
CREATE TRIGGER update_outfit_diaries_updated_at BEFORE UPDATE ON outfit_diaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
