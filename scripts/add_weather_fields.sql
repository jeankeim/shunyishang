-- =====================================================
-- 为items表添加天气相关字段
-- Version: 1.1
-- Date: 2026-03-24
-- =====================================================

-- 添加适用天气字段
ALTER TABLE items ADD COLUMN IF NOT EXISTS applicable_weather JSONB;

-- 添加适用季节字段
ALTER TABLE items ADD COLUMN IF NOT EXISTS applicable_seasons JSONB;

-- 添加适用温度范围字段
ALTER TABLE items ADD COLUMN IF NOT EXISTS temperature_range JSONB;

-- 添加功能性字段
ALTER TABLE items ADD COLUMN IF NOT EXISTS functionality JSONB;

-- 添加厚度等级字段
ALTER TABLE items ADD COLUMN IF NOT EXISTS thickness_level VARCHAR(20);

-- 创建索引以支持天气过滤查询
CREATE INDEX IF NOT EXISTS idx_items_applicable_weather ON items USING GIN (applicable_weather);
CREATE INDEX IF NOT EXISTS idx_items_applicable_seasons ON items USING GIN (applicable_seasons);
CREATE INDEX IF NOT EXISTS idx_items_thickness_level ON items(thickness_level);

-- 添加注释
COMMENT ON COLUMN items.applicable_weather IS '适用天气：["晴天", "雨天", "寒冷", "炎热", "温和", "多云"]';
COMMENT ON COLUMN items.applicable_seasons IS '适用季节：["春", "夏", "秋", "冬"]';
COMMENT ON COLUMN items.temperature_range IS '适用温度范围：{"最低": int, "最高": int}';
COMMENT ON COLUMN items.functionality IS '功能性：{"防水": bool, "透气": bool, "保暖": bool, "速干": bool, "防晒": bool}';
COMMENT ON COLUMN items.thickness_level IS '厚度等级：极薄、轻薄、适中、中厚、厚重';
