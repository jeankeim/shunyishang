#!/bin/bash
# 生产环境向量索引检查和优化
# 用法: bash scripts/check_and_optimize_indexes.sh

set -e

echo "============================================================"
echo "🔍 生产环境向量索引诊断与优化"
echo "============================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 HNSW 索引是否存在
echo "1️⃣  检查 HNSW 索引状态"
echo "------------------------------------------------------------"

# 创建临时 SQL 文件
cat > /tmp/check_hnsw.sql << 'EOF'
-- 检查 HNSW 索引
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ HNSW 索引已存在'
        ELSE '❌ HNSW 索引不存在，需要创建'
    END as status,
    COUNT(*) as index_count
FROM pg_indexes 
WHERE tablename = 'items' 
AND indexdef LIKE '%hnsw%';

-- 检查索引大小
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE tablename = 'items'
ORDER BY indexname;

-- 测试向量搜索性能
EXPLAIN ANALYZE 
SELECT item_code, name 
FROM items 
ORDER BY embedding <-> (SELECT embedding FROM items LIMIT 1)
LIMIT 5;
EOF

echo "📋 请执行以下步骤："
echo ""
echo "1. 登录 Zeabur Dashboard"
echo "   https://zeabur.com/dashboard"
echo ""
echo "2. 找到 shunyishang-wuxing 服务"
echo ""
echo "3. 进入 Database → PostgreSQL → Query"
echo ""
echo "4. 执行以下 SQL："
echo ""
echo "------------------------------------------------------------"
cat /tmp/check_hnsw.sql
echo "------------------------------------------------------------"
echo ""

# 提供优化 SQL
echo ""
echo "2️⃣  如果索引不存在，执行优化脚本"
echo "------------------------------------------------------------"
echo ""
echo "📋 创建 HNSW 索引的 SQL："
echo ""
echo "------------------------------------------------------------"
cat << 'EOF'
-- 创建 HNSW 向量索引（如果不存在）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_items_embedding_hnsw 
ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 更新统计信息
ANALYZE items;

-- 验证索引
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE tablename = 'items'
AND indexdef LIKE '%hnsw%';
EOF
echo "------------------------------------------------------------"
echo ""

# 提供监控命令
echo ""
echo "3️⃣  监控索引创建进度"
echo "------------------------------------------------------------"
echo ""
echo "在索引创建过程中，可以监控进度："
echo ""
echo "SELECT * FROM pg_stat_progress_create_index;"
echo ""

# 预期效果
echo ""
echo "📊 预期效果"
echo "------------------------------------------------------------"
echo ""
echo "优化前（全表扫描）:"
echo "  - 向量搜索: 20-30s ❌"
echo "  - 扫描方式: Seq Scan"
echo ""
echo "优化后（HNSW 索引）:"
echo "  - 向量搜索: 0.1-0.5s ✅"
echo "  - 扫描方式: Index Scan using idx_items_embedding_hnsw"
echo ""

echo "============================================================"
echo "💡 提示"
echo "============================================================"
echo ""
echo "1. CONCURRENTLY 参数确保不锁表，可以安全在生产环境执行"
echo "2. 索引创建需要 1-3 分钟（取决于数据量）"
echo "3. 创建完成后，向量搜索性能将提升 50-100 倍"
echo "4. 建议创建后立即测试推荐接口性能"
echo ""
echo "============================================================"
