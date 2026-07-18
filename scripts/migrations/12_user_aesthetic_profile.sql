-- ============================================
-- Week 4: 用户审美画像 - 新增审美偏好字段
-- 版本: 1.0
-- 说明: 收集用户肤色、风格偏好、体型等审美信息，
--       使推荐更贴合个人审美特征
-- ============================================

-- 肤色：冷白皮/暖白皮/自然色/小麦色/黑皮
ALTER TABLE users ADD COLUMN IF NOT EXISTS skin_tone VARCHAR(20);

-- 风格偏好：简约/韩系/日系/国潮/复古/商务/街头/文艺
ALTER TABLE users ADD COLUMN IF NOT EXISTS style_preference VARCHAR(50);

-- 体型：偏瘦/标准/偏胖
ALTER TABLE users ADD COLUMN IF NOT EXISTS body_type VARCHAR(20);

-- 扩展审美标签（JSONB数组，支持渐进式收集）
-- 示例: ["喜欢浅色系", "偏爱宽松款", "不喜欢碎花"]
ALTER TABLE users ADD COLUMN IF NOT EXISTS aesthetic_tags JSONB DEFAULT '[]';

-- 审美信息采集时间（用于判断数据新鲜度）
ALTER TABLE users ADD COLUMN IF NOT EXISTS aesthetic_updated_at TIMESTAMPTZ;

-- 索引
CREATE INDEX IF NOT EXISTS idx_users_skin_tone ON users(skin_tone);
CREATE INDEX IF NOT EXISTS idx_users_style_pref ON users(style_preference);

-- 注释
COMMENT ON COLUMN users.skin_tone IS '肤色: 冷白皮/暖白皮/自然色/小麦色/黑皮';
COMMENT ON COLUMN users.style_preference IS '风格偏好: 简约/韩系/日系/国潮/复古/商务/街头/文艺';
COMMENT ON COLUMN users.body_type IS '体型: 偏瘦/标准/偏胖';
COMMENT ON COLUMN users.aesthetic_tags IS '扩展审美标签 JSONB 数组';
COMMENT ON COLUMN users.aesthetic_updated_at IS '审美信息最后更新时间';

-- ============================================
-- 迁移完成
-- ============================================
