-- =====================================================
-- 性能优化索引迁移脚本
-- Version: 05
-- Description: 为高频查询添加缺失索引、部分索引和复合索引
-- 执行方式: 在 PostgreSQL 中直接执行
-- =====================================================

-- =====================================================
-- 1. 部分索引 (Partial Index) — 减少索引大小
-- =====================================================

-- 1.1 user_wardrobe: 仅索引活跃物品的 user_id（大多数查询都带 is_active = TRUE）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wardrobe_user_active_partial
ON user_wardrobe (user_id)
WHERE is_active = TRUE;

-- 1.2 user_wardrobe: 仅索引有 embedding 的活跃物品（向量搜索前置条件）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wardrobe_embedding_partial
ON user_wardrobe (user_id)
WHERE embedding IS NOT NULL AND is_active = TRUE;

-- 1.3 items: 仅索引有 embedding 的物品（向量搜索过滤条件）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_embedding_not_null
ON items (item_code)
WHERE embedding IS NOT NULL;

-- =====================================================
-- 2. 复合索引 — 覆盖高频 WHERE + ORDER BY 组合
-- =====================================================

-- 2.1 user_wardrobe: 衣橱列表查询 (WHERE user_id = ? AND is_active = TRUE ORDER BY created_at DESC)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wardrobe_user_active_created
ON user_wardrobe (user_id, is_active, created_at DESC);

-- 2.2 items: 向量搜索带性别过滤 (WHERE gender = ? AND embedding IS NOT NULL ORDER BY embedding <=> ?)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_gender_embedding
ON items (gender)
WHERE embedding IS NOT NULL;

-- 2.3 items: 类别+五行复合查询 (WHERE category = ? AND primary_element = ?)
-- 注意: init_db.sql 已有 idx_items_category 和 idx_items_primary_element，但复合索引更优
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_category_element
ON items (category, primary_element);

-- 2.4 items: 厚度等级过滤（天气过滤常用）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_thickness_level
ON items (thickness_level)
WHERE embedding IS NOT NULL;

-- 2.5 feedback_logs: 用户反馈历史 (WHERE user_id = ? ORDER BY created_at DESC)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feedback_user_created
ON feedback_logs (user_id, created_at DESC);

-- =====================================================
-- 3. JSONB GIN 索引 — 加速 attributes_detail 查询
-- =====================================================

-- 3.1 items.attributes_detail GIN 索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_attributes_detail
ON items USING gin (attributes_detail);

-- 3.2 user_wardrobe.attributes_detail GIN 索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wardrobe_attributes_detail
ON user_wardrobe USING gin (attributes_detail);

-- 3.3 items.applicable_weather GIN 索引（补充 init_db.sql 中 items 表缺失的 GIN 索引）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_applicable_weather
ON items USING gin (applicable_weather);

-- 3.4 items.applicable_seasons GIN 索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_applicable_seasons
ON items USING gin (applicable_seasons);

-- =====================================================
-- 4. HNSW 向量索引参数优化检查
-- =====================================================
-- 注意: HNSW 索引已在 init_db.sql 中创建，参数为 m=16, ef_construction=64
-- 对于 <10K 条数据，当前参数已足够优化
-- 如果数据量 >100K，建议调整为 m=32, ef_construction=128

-- 验证 HNSW 索引是否存在:
-- SELECT indexname, indexdef FROM pg_indexes
-- WHERE tablename = 'items' AND indexdef LIKE '%hnsw%';

-- =====================================================
-- 5. 用户表补充索引
-- =====================================================

-- 5.1 users: 登录查询 (WHERE phone = ? OR email = ?)
-- PostgreSQL 对 OR 查询优化有限，但单独的索引已存在
-- 添加 is_active 的部分索引用于活跃用户查找
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_phone
ON users (phone)
WHERE is_active = TRUE;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_email
ON users (email)
WHERE is_active = TRUE;

-- =====================================================
-- 6. 更新统计信息
-- =====================================================
ANALYZE items;
ANALYZE user_wardrobe;
ANALYZE users;
ANALYZE feedback_logs;

-- =====================================================
-- 验证: 查看所有索引
-- =====================================================
-- SELECT tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename IN ('items', 'user_wardrobe', 'users', 'feedback_logs')
-- ORDER BY tablename, indexname;
