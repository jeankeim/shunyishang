-- Migration 10: 偏好系统增强 + 用户行为追踪
-- 1. 扩展偏好类型注释 (新增 style/material/thickness 维度)
-- 2. 创建用户行为追踪表 (view/click/expand/image_click/dwell)
-- 3. 添加行为统计索引

-- 1. 更新偏好类型注释（代码已支持 6 维，更新注释）
COMMENT ON COLUMN user_preferences.pref_type IS '偏好类型: color/element/category/style/material/thickness';
COMMENT ON COLUMN user_preferences.weight IS '偏好权重: 正数=偏好, 负数=厌恶, 0=中性, 支持时间衰减';

-- 2. 用户行为追踪表（隐性反馈）
CREATE TABLE IF NOT EXISTS user_behaviors (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    item_id VARCHAR(100),                    -- 物品ID (wardrobe item id 或 seed item code)
    item_source VARCHAR(20) DEFAULT 'public', -- public / wardrobe
    action VARCHAR(30) NOT NULL,             -- view / click / expand / image_click / dwell
    dwell_duration INTEGER DEFAULT 0,         -- 停留时长（秒），仅 dwell 动作有值
    session_id VARCHAR(100),                  -- 推荐会话ID
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. 索引
CREATE INDEX IF NOT EXISTS idx_user_behaviors_user ON user_behaviors(user_id);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_item ON user_behaviors(item_id);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_action ON user_behaviors(user_id, action);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_created ON user_behaviors(created_at);

COMMENT ON TABLE user_behaviors IS '用户行为追踪表，记录隐性反馈用于偏好学习';
COMMENT ON COLUMN user_behaviors.action IS '行为类型: view/click/expand/image_click/dwell';
COMMENT ON COLUMN user_behaviors.dwell_duration IS '停留时长（秒），仅 dwell 动作有效';

-- 4. 为 items 表新增 color/style/material 列（从 attributes_detail JSONB 提取）
-- 颜色
ALTER TABLE items ADD COLUMN IF NOT EXISTS color VARCHAR(50);
UPDATE items SET color = attributes_detail->'颜色'->>'名称' WHERE color IS NULL AND attributes_detail->'颜色'->>'名称' IS NOT NULL;

-- 风格（从 款式.形状 提取）
ALTER TABLE items ADD COLUMN IF NOT EXISTS style VARCHAR(50);
UPDATE items SET style = attributes_detail->'款式'->>'形状' WHERE style IS NULL AND attributes_detail->'款式'->>'形状' IS NOT NULL;

-- 材质（从 面料 提取）
ALTER TABLE items ADD COLUMN IF NOT EXISTS material VARCHAR(50);
UPDATE items SET material = attributes_detail->'面料'->>'名称' WHERE material IS NULL AND attributes_detail->'面料'->>'名称' IS NOT NULL;

-- 5. 为 user_wardrobe 表也添加 color/style/material 列
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS color VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS style VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS material VARCHAR(50);

UPDATE user_wardrobe SET color = attributes_detail->'颜色'->>'名称' WHERE color IS NULL AND attributes_detail->'颜色'->>'名称' IS NOT NULL;
UPDATE user_wardrobe SET style = attributes_detail->'款式'->>'形状' WHERE style IS NULL AND attributes_detail->'款式'->>'形状' IS NOT NULL;
UPDATE user_wardrobe SET material = attributes_detail->'面料'->>'名称' WHERE material IS NULL AND attributes_detail->'面料'->>'名称' IS NOT NULL;
