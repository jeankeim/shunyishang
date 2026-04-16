-- ============================================
-- 为 items 表添加缩略图字段
-- 目的：支持渐进式图片加载（先加载缩略图，点击后加载高清图）
-- 日期：2026-04-16
-- ============================================

-- 1. 添加 thumbnail_url 字段
ALTER TABLE items 
ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500);

-- 2. 为现有图片生成缩略图 URL（仅对 R2 图片）
-- 注意：这个脚本假设 R2 的 public_url 格式
-- 如果你的 R2 配置不同，需要手动调整
UPDATE items 
SET thumbnail_url = CASE 
    -- 如果已经有缩略图 URL，保持不变
    WHEN thumbnail_url IS NOT NULL AND thumbnail_url != '' THEN thumbnail_url
    
    -- 如果是 R2 图片，生成缩略图 URL
    WHEN image_url LIKE '%.r2.cloudflarestorage.com%' OR image_url LIKE '%pub-%.r2.dev%' THEN
        -- 提取原图 key 并构建缩略图 key
        REGEXP_REPLACE(
            image_url,
            '(/uploads/[^/]+/[^/]+)\.([a-zA-Z0-9]+)$',
            '\1/thumbnails/\1_thumb.jpg'
        )
    
    -- 其他情况保持 NULL（后续上传时会自动生成）
    ELSE NULL
END
WHERE image_url IS NOT NULL 
  AND image_url != ''
  AND (thumbnail_url IS NULL OR thumbnail_url = '');

-- 3. 添加索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_items_thumbnail_url ON items(thumbnail_url);

-- 4. 添加注释
COMMENT ON COLUMN items.thumbnail_url IS '图片缩略图 URL（用于渐进式加载，宽度 400px）';

-- ============================================
-- 验证脚本
-- ============================================
-- 查看缩略图字段统计
SELECT 
    COUNT(*) as total_items,
    COUNT(thumbnail_url) as has_thumbnail,
    COUNT(image_url) as has_image,
    ROUND(COUNT(thumbnail_url)::numeric / COUNT(*) * 100, 2) as thumbnail_coverage_percent
FROM items
WHERE image_url IS NOT NULL;

-- 查看示例数据
SELECT 
    item_code,
    name,
    LEFT(image_url, 80) as image_url_preview,
    LEFT(COALESCE(thumbnail_url, 'NULL'), 80) as thumbnail_url_preview
FROM items
WHERE image_url IS NOT NULL
LIMIT 10;
