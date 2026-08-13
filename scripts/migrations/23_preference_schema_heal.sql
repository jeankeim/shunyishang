-- Migration 23: 偏好系统 schema 自愈
-- 背景: 线上库可能是旧版本建表，06/10/13 迁移中的 CREATE TABLE IF NOT EXISTS
-- 对已存在的旧表是 no-op，不会补齐缺失的 UNIQUE 约束/列，导致：
--   * preference_service.update_preference 的 ON CONFLICT (user_id, pref_type, pref_key)
--     因缺少唯一索引而报错，偏好学习静默失败（反馈成功但画像永远为空）
--   * _get_item_attributes 查询缺失列报错
-- 本迁移全部使用 IF NOT EXISTS / 防御性去重，可安全重复执行（幂等）。

-- 0. 极早期遗留的旧版 user_preferences（user_id varchar + preferred_* JSONB 结构）
-- 与现行代码完全不兼容且无任何引用，重命名为备份表后重建新结构
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'preferred_elements'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_preferences' AND column_name = 'pref_type'
    ) THEN
        ALTER TABLE user_preferences RENAME TO user_preferences_legacy_bak;
        RAISE NOTICE '旧版 user_preferences 已备份为 user_preferences_legacy_bak';
    END IF;
END $$;


-- 1. 确保 user_preferences 表存在（含 UNIQUE 约束）
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pref_type VARCHAR(20) NOT NULL,
    pref_key VARCHAR(50) NOT NULL,
    weight INTEGER NOT NULL DEFAULT 0,
    feedback_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, pref_type, pref_key)
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_prefs_type ON user_preferences(user_id, pref_type);

-- 2. 旧表可能缺 UNIQUE 约束：先防御性去重（保留最新一条），再补唯一索引
-- ON CONFLICT (user_id, pref_type, pref_key) 依赖此唯一索引
DELETE FROM user_preferences a
USING user_preferences b
WHERE a.user_id = b.user_id
  AND a.pref_type = b.pref_type
  AND a.pref_key = b.pref_key
  AND a.id < b.id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_preferences_user_type_key
    ON user_preferences(user_id, pref_type, pref_key);

-- 3. items 表补齐偏好维度列（缺列会导致属性查询报错）
ALTER TABLE items ADD COLUMN IF NOT EXISTS color VARCHAR(50);
ALTER TABLE items ADD COLUMN IF NOT EXISTS style VARCHAR(50);
ALTER TABLE items ADD COLUMN IF NOT EXISTS material VARCHAR(50);

UPDATE items SET color = attributes_detail->'颜色'->>'名称'
WHERE color IS NULL AND attributes_detail->'颜色'->>'名称' IS NOT NULL;
UPDATE items SET style = attributes_detail->'款式'->>'形状'
WHERE style IS NULL AND attributes_detail->'款式'->>'形状' IS NOT NULL;
UPDATE items SET material = attributes_detail->'面料'->>'名称'
WHERE material IS NULL AND attributes_detail->'面料'->>'名称' IS NOT NULL;

-- 4. user_wardrobe 表补齐偏好维度列
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS color VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS style VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS material VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS thickness_level VARCHAR(20);

UPDATE user_wardrobe SET color = attributes_detail->'颜色'->>'名称'
WHERE color IS NULL AND attributes_detail->'颜色'->>'名称' IS NOT NULL;
UPDATE user_wardrobe SET style = attributes_detail->'款式'->>'形状'
WHERE style IS NULL AND attributes_detail->'款式'->>'形状' IS NOT NULL;
UPDATE user_wardrobe SET material = attributes_detail->'面料'->>'名称'
WHERE material IS NULL AND attributes_detail->'面料'->>'名称' IS NOT NULL;

-- 5. 确保 user_disliked_items 表存在（dislike 排除列表）
CREATE TABLE IF NOT EXISTS user_disliked_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    item_code VARCHAR(50) NOT NULL,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_code)
);

CREATE INDEX IF NOT EXISTS idx_disliked_user ON user_disliked_items(user_id);
CREATE INDEX IF NOT EXISTS idx_disliked_item ON user_disliked_items(item_code);
