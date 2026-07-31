-- Migration 20: 图片 URL 全量替换 R2 -> 阿里云 OSS
--
-- 背景：
--   图片文件已从 Cloudflare R2 完整迁移至阿里云 OSS（555 个对象，key 路径不变），
--   本迁移将数据库中存量图片 URL 的域名前缀从 R2 公共域名替换为 OSS 域名。
--
-- 用法（psql 变量传入源/目标域名，便于备案后二次替换为自定义域名）：
--   psql "$DATABASE_URL" \
--     -v old_host="'https://pub-851399ad134d447ea68cd62dbadd90a4.r2.dev'" \
--     -v new_host="'https://shunyishang-image.oss-cn-hangzhou.aliyuncs.com'" \
--     -f scripts/migrations/20_rewrite_image_urls.sql
--
-- 幂等：URL 中不含 old_host 的行不受影响，可重复执行。

BEGIN;

-- 1. 用户衣橱
UPDATE user_wardrobe
SET image_url = replace(image_url, :old_host, :new_host)
WHERE image_url LIKE :old_host || '%';

-- 2. 公共库（原图 + 缩略图）
UPDATE items
SET image_url = replace(image_url, :old_host, :new_host)
WHERE image_url LIKE :old_host || '%';

UPDATE items
SET thumbnail_url = replace(thumbnail_url, :old_host, :new_host)
WHERE thumbnail_url LIKE :old_host || '%';

-- 3. 社区帖子（TEXT[] 数组，逐元素替换）
UPDATE community_posts
SET image_urls = (
    SELECT array_agg(replace(u, :old_host, :new_host) ORDER BY ord)
    FROM unnest(image_urls) WITH ORDINALITY AS t(u, ord)
)
WHERE EXISTS (
    SELECT 1 FROM unnest(image_urls) AS u WHERE u LIKE :old_host || '%'
);

-- 4. 穿搭日记（jsonb 数组，序列化替换后转回 jsonb）
UPDATE outfit_diaries
SET image_urls = replace(image_urls::text, :old_host, :new_host)::jsonb
WHERE image_urls::text LIKE '%' || :old_host || '%';

-- 5. 用户头像（当前 0 条，防御性覆盖）
UPDATE users
SET avatar_url = replace(avatar_url, :old_host, :new_host)
WHERE avatar_url LIKE :old_host || '%';

COMMIT;

-- 验证：替换后旧域名应为 0 条
SELECT 'user_wardrobe' AS tbl, count(*) AS remaining FROM user_wardrobe WHERE image_url LIKE :old_host || '%'
UNION ALL
SELECT 'items.image_url', count(*) FROM items WHERE image_url LIKE :old_host || '%'
UNION ALL
SELECT 'items.thumbnail_url', count(*) FROM items WHERE thumbnail_url LIKE :old_host || '%'
UNION ALL
SELECT 'community_posts', count(*) FROM community_posts WHERE EXISTS (SELECT 1 FROM unnest(image_urls) u WHERE u LIKE :old_host || '%')
UNION ALL
SELECT 'outfit_diaries', count(*) FROM outfit_diaries WHERE image_urls::text LIKE '%' || :old_host || '%'
UNION ALL
SELECT 'users.avatar_url', count(*) FROM users WHERE avatar_url LIKE :old_host || '%';
