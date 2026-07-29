-- Migration 19: 修复并回填 user_wardrobe.style（真实风格值）
--
-- 背景：
--   Migration 10 曾将 style 列从 attributes_detail->'款式'->>'形状' 回填，
--   写入的是"形状/品名"值（长方/圆形/直筒牛仔裤等），并非风格词表，
--   会导致场景风格判断（is_style_scene_appropriate）误判为风格不匹配。
--   同时上传链路此前从未写入 style 列，AI 识别的真实风格只存在于
--   attributes_detail->'款式'->>'风格' 中。
--   生产库 user_wardrobe 可能从未执行过 migration 10（无 color/style/material 列）。
--
-- 本迁移（幂等）：
--   0. 补建 user_wardrobe 缺失的 color/style/material 列
--   1. 用 attributes_detail->'款式'->>'风格' 覆盖回填 user_wardrobe.style，
--      并归一化到统一风格词表；词表外值（含形状污染值）置空
--   2. items 表清理所有词表外的 style 值（形状/品名污染，置空即无惩罚）

-- 0. 补建缺失列（与 migration 10 对齐，生产库可能未执行过）
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS color VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS style VARCHAR(50);
ALTER TABLE user_wardrobe ADD COLUMN IF NOT EXISTS material VARCHAR(50);

UPDATE user_wardrobe SET color = attributes_detail->'颜色'->>'名称'
WHERE color IS NULL AND attributes_detail->'颜色'->>'名称' IS NOT NULL;
UPDATE user_wardrobe SET material = attributes_detail->'面料'->>'名称'
WHERE material IS NULL AND attributes_detail->'面料'->>'名称' IS NOT NULL;

-- 1. 衣橱：用真实风格覆盖回填（旧词表值同时归一化到统一词表）
UPDATE user_wardrobe
SET style = CASE attributes_detail->'款式'->>'风格'
    WHEN '正式' THEN '商务'
    WHEN '职业' THEN '商务'
    WHEN '时尚' THEN '街头'
    WHEN '潮流' THEN '街头'
    WHEN '传统' THEN '国潮'
    WHEN '中式' THEN '国潮'
    WHEN '禅意' THEN '文艺'
    WHEN '复古' THEN '文艺'
    WHEN '极简' THEN '简约'
    WHEN '日常' THEN '休闲'
    ELSE attributes_detail->'款式'->>'风格'
END
WHERE attributes_detail->'款式'->>'风格' IS NOT NULL
  AND attributes_detail->'款式'->>'风格' <> '';

-- 1b. 归一化后仍不在统一词表内的值置空（空 style 不参与风格惩罚）
UPDATE user_wardrobe
SET style = NULL
WHERE style IS NOT NULL
  AND style NOT IN ('商务', '知性', '简约', '优雅', '甜美', '性感',
                    '休闲', '运动', '街头', '森系', '文艺', '国潮');

-- 2. 公共库：清理词表外污染值（migration 10 从"形状"回填的形状/品名值）
UPDATE items
SET style = NULL
WHERE style IS NOT NULL
  AND style NOT IN ('商务', '知性', '简约', '优雅', '甜美', '性感',
                    '休闲', '运动', '街头', '森系', '文艺', '国潮');

COMMENT ON COLUMN user_wardrobe.style IS '风格（AI打标，与场景偏好词表对齐）: 商务/休闲/运动/优雅/知性/简约/文艺 等';
