-- 迁移13: 用户不喜欢物品记录
-- 用于记录用户明确不喜欢的物品，推荐时排除

CREATE TABLE IF NOT EXISTS user_disliked_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    item_code VARCHAR(50) NOT NULL,
    reason VARCHAR(100),  -- 可选原因: '不感兴趣', '风格不符', '已有类似', '其他'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_code)
);

CREATE INDEX IF NOT EXISTS idx_disliked_user ON user_disliked_items(user_id);
CREATE INDEX IF NOT EXISTS idx_disliked_item ON user_disliked_items(item_code);
