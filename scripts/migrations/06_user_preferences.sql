-- Migration 06: 用户偏好学习系统
-- 记录用户对颜色、五行、风格的偏好，用于推荐权重调整

CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pref_type VARCHAR(20) NOT NULL,          -- 偏好类型: color/element/style/category
    pref_key VARCHAR(50) NOT NULL,           -- 偏好键: 如 "红色"/"火"/"休闲"/"上装"
    weight INTEGER NOT NULL DEFAULT 0,       -- 权重: 正=喜欢, 负=不喜欢, 0=中性
    feedback_count INTEGER NOT NULL DEFAULT 0, -- 反馈次数
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, pref_type, pref_key)
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_prefs_type ON user_preferences(user_id, pref_type);

COMMENT ON TABLE user_preferences IS '用户偏好学习表，基于反馈自动调整推荐权重';
COMMENT ON COLUMN user_preferences.pref_type IS '偏好类型: color/element/style/category';
COMMENT ON COLUMN user_preferences.weight IS '偏好权重: 正数=偏好, 负数=厌恶, 0=中性';
