-- ============================================
-- Week 4 补充: user_wardrobe 添加天气/场景字段
-- 版本: 1.1
-- 日期: 2024-03-25
-- 说明: 补充缺失的天气感知、场景匹配相关字段
-- 使 user_wardrobe 与 items 表具备相同的 AI 推荐能力
-- ============================================

-- ============================================
-- 1. 添加天气/场景相关字段
-- ============================================

-- 性别适配
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT '中性';

-- 适用天气 (JSONB数组)
-- 示例: ["晴", "多云", "阴"]
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS applicable_weather JSONB DEFAULT '[]';

-- 适用季节 (JSONB数组)
-- 示例: ["春", "夏", "秋", "冬"]
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS applicable_seasons JSONB DEFAULT '[]';

-- 温度范围 (JSONB对象)
-- 示例: {"min": 15, "max": 25}
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS temperature_range JSONB DEFAULT '{}';

-- 功能场景 (JSONB数组)
-- 示例: ["面试", "约会", "商务", "日常", "运动", "派对", "居家", "旅行"]
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS functionality JSONB DEFAULT '[]';

-- 厚度/保暖等级
-- 可选值: 轻薄/适中/加厚/厚重
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS thickness_level VARCHAR(20);

-- 能量强度 (用于八字喜用神匹配)
-- 范围: 0.0 - 1.0
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS energy_intensity DOUBLE PRECISION;

-- ============================================
-- 2. 添加索引
-- ============================================

-- 性别索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_gender 
ON user_wardrobe(gender);

-- 适用天气 GIN 索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_applicable_weather 
ON user_wardrobe USING gin(applicable_weather);

-- 适用季节 GIN 索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_applicable_seasons 
ON user_wardrobe USING gin(applicable_seasons);

-- 功能场景 GIN 索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_functionality 
ON user_wardrobe USING gin(functionality);

-- ============================================
-- 3. 添加字段注释
-- ============================================

COMMENT ON COLUMN user_wardrobe.gender IS '性别适配: 男/女/中性';
COMMENT ON COLUMN user_wardrobe.applicable_weather IS '适用天气: ["晴", "多云", "阴", "雨", "雪", "霾"]';
COMMENT ON COLUMN user_wardrobe.applicable_seasons IS '适用季节: ["春", "夏", "秋", "冬"]';
COMMENT ON COLUMN user_wardrobe.temperature_range IS '温度范围: {"min": 15, "max": 25}';
COMMENT ON COLUMN user_wardrobe.functionality IS '功能场景: ["面试", "约会", "商务", "日常", "运动", "派对", "居家", "旅行"]';
COMMENT ON COLUMN user_wardrobe.thickness_level IS '厚度等级: 轻薄/适中/加厚/厚重';
COMMENT ON COLUMN user_wardrobe.energy_intensity IS '能量强度(0.0-1.0)，用于八字喜用神匹配';

-- ============================================
-- 迁移完成
-- ============================================
-- 验证命令:
-- \d user_wardrobe
-- SELECT indexname FROM pg_indexes WHERE tablename = 'user_wardrobe';
