-- ============================================================
-- 17: PIPL 隐私合规
-- 1) birth_date/birth_time/birth_location 改为 TEXT，
--    支持应用层加密存储（密文格式 enc:v1:<token>）
-- 2) 新增 privacy_agreed_at：记录用户同意隐私政策/敏感信息处理的时间
--    （PIPL 单独同意的留痕证据）
--
-- 说明：改类型后存量数据为明文文本，读取路径透明兼容；
--       配置 PII_ENCRYPTION_KEY 后运行 scripts/encrypt_existing_pii.py
--       完成存量数据加密回填。
-- ============================================================

ALTER TABLE users ALTER COLUMN birth_date TYPE TEXT USING birth_date::text;
ALTER TABLE users ALTER COLUMN birth_time TYPE TEXT USING birth_time::text;
ALTER TABLE users ALTER COLUMN birth_location TYPE TEXT;

ALTER TABLE users ADD COLUMN IF NOT EXISTS privacy_agreed_at TIMESTAMPTZ;

COMMENT ON COLUMN users.birth_date IS '出生日期（敏感信息，应用层加密存储）';
COMMENT ON COLUMN users.birth_time IS '出生时间（敏感信息，应用层加密存储）';
COMMENT ON COLUMN users.birth_location IS '出生地点（敏感信息，应用层加密存储）';
COMMENT ON COLUMN users.privacy_agreed_at IS '隐私政策/敏感信息处理同意时间（PIPL 留痕）';
