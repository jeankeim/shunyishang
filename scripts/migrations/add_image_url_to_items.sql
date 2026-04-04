-- =====================================================
-- 给 items 表添加 image_url 字段
-- 用于存储公共种子库物品的图片URL
-- =====================================================

-- 添加 image_url 字段
ALTER TABLE items ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);

-- 添加字段注释
COMMENT ON COLUMN items.image_url IS '物品图片URL，用于前端展示';

-- 创建索引（可选，如果需要按图片URL查询）
-- CREATE INDEX idx_items_image_url ON items(image_url) WHERE image_url IS NOT NULL;
