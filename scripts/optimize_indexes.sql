-- =====================================================
-- 数据库索引优化脚本
-- 目标: 提升查询性能,优化向量搜索
-- 执行时间: 2026-04-12
-- =====================================================

-- 1. 向量搜索 HNSW 索引 (最重要)
-- 说明: HNSW 索引大幅提升向量搜索速度,从线性搜索 O(n) 到近似搜索 O(log n)
-- 参数: m=16 (连接数), ef_construction=64 (构建时搜索深度)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_embedding_hnsw 
ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 2. 常用查询字段索引
-- 说明: 加速场景过滤、类别筛选等常用查询
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_primary_element ON items(primary_element);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_source ON items(source);

-- 3. 衣橱表索引
-- 说明: 加速用户衣橱查询
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_wardrobe_user_id ON user_wardrobe(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_wardrobe_item_id ON user_wardrobe(item_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_wardrobe_composite ON user_wardrobe(user_id, item_id);

-- 4. 复合索引 (场景过滤常用组合)
-- 说明: 加速 WHERE category = ? AND primary_element = ? 类型查询
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_category_element ON items(category, primary_element);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_source_category ON items(source, category);

-- 5. JSONB 字段索引 (functionality 查询)
-- 说明: 加速 functionality->>'透气' = true 类型查询
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_functionality ON items USING gin (functionality);

-- 6. 用户表索引
-- 说明: 加速用户查询
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_user_code ON users(user_code);

-- =====================================================
-- 索引创建后分析
-- =====================================================

-- 更新统计信息,让查询优化器使用最新的索引统计
ANALYZE items;
ANALYZE user_wardrobe;
ANALYZE users;

-- =====================================================
-- 验证索引创建结果
-- =====================================================

-- 查看所有索引
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('items', 'user_wardrobe', 'users')
ORDER BY tablename, indexname;

-- 查看索引大小
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE tablename = 'items'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- =====================================================
-- 性能测试查询 (验证索引效果)
-- =====================================================

-- 测试1: 向量搜索 (应该使用 idx_items_embedding_hnsw)
EXPLAIN ANALYZE 
SELECT id, name, category 
FROM items 
ORDER BY embedding <-> (SELECT embedding FROM items WHERE id = 'ITEM_001' LIMIT 1)
LIMIT 10;

-- 测试2: 场景过滤 (应该使用 idx_items_category)
EXPLAIN ANALYZE 
SELECT id, name, category 
FROM items 
WHERE category = '上装' 
LIMIT 10;

-- 测试3: 复合查询 (应该使用 idx_items_category_element)
EXPLAIN ANALYZE 
SELECT id, name, category, primary_element 
FROM items 
WHERE category = '上装' AND primary_element = '木' 
LIMIT 10;

-- 测试4: 功能过滤 (应该使用 idx_items_functionality)
EXPLAIN ANALYZE 
SELECT id, name, functionality 
FROM items 
WHERE functionality->>'透气' = 'true' 
LIMIT 10;

-- 测试5: 用户衣橱查询 (应该使用 idx_user_wardrobe_user_id)
EXPLAIN ANALYZE 
SELECT uw.*, i.name, i.category 
FROM user_wardrobe uw
JOIN items i ON uw.item_id = i.id
WHERE uw.user_id = 1
LIMIT 10;

-- =====================================================
-- 说明
-- =====================================================
-- 1. CONCURRENTLY: 不锁表,可以在生产环境安全执行
-- 2. IF NOT EXISTS: 幂等操作,可重复执行
-- 3. 执行时间: 根据数据量,预计 1-5 分钟
-- 4. 监控进度: SELECT * FROM pg_stat_progress_create_index;
