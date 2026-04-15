"""
检查 PostgreSQL 向量索引状态
诊断向量搜索慢的问题
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('.env.production')

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL 未设置")
    exit(1)

print("=" * 70)
print("🔍 PostgreSQL 向量索引诊断")
print("=" * 70)
print()

# 连接数据库
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. 检查 HNSW 索引是否存在
    print("1️⃣  检查 HNSW 索引")
    print("-" * 70)
    
    result = conn.execute(text("""
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes 
        WHERE tablename = 'items' 
        AND indexdef LIKE '%hnsw%'
    """))
    
    hnsw_indexes = result.fetchall()
    
    if hnsw_indexes:
        print(f"✅ 找到 {len(hnsw_indexes)} 个 HNSW 索引:")
        for idx_name, idx_def in hnsw_indexes:
            print(f"   - {idx_name}")
            # 只显示索引定义的前 100 字符
            print(f"     {idx_def[:100]}...")
    else:
        print("❌ 未找到 HNSW 索引！")
        print("   这可能是向量搜索慢的原因")
    
    print()
    
    # 2. 检查 items 表大小
    print("2️⃣  检查 items 表大小")
    print("-" * 70)
    
    result = conn.execute(text("""
        SELECT 
            pg_size_pretty(pg_total_relation_size('items')) as total_size,
            pg_size_pretty(pg_relation_size('items')) as table_size,
            (SELECT count(*) FROM items) as row_count
    """))
    
    row = result.fetchone()
    print(f"   总大小: {row[0]}")
    print(f"   表大小: {row[1]}")
    print(f"   行数: {row[2]}")
    
    print()
    
    # 3. 检查 embedding 字段类型
    print("3️⃣  检查 embedding 字段")
    print("-" * 70)
    
    result = conn.execute(text("""
        SELECT 
            column_name,
            data_type,
            udt_name
        FROM information_schema.columns 
        WHERE table_name = 'items' 
        AND column_name = 'embedding'
    """))
    
    row = result.fetchone()
    if row:
        print(f"   字段: {row[0]}")
        print(f"   类型: {row[1]} ({row[2]})")
    else:
        print("   ❌ embedding 字段不存在")
    
    print()
    
    # 4. 测试向量搜索性能
    print("4️⃣  测试向量搜索性能")
    print("-" * 70)
    
    # 生成一个随机向量（1024 维）
    import random
    random_vector = [random.uniform(-1, 1) for _ in range(1024)]
    vector_str = f"[{','.join(map(str, random_vector))}]"
    
    # 测试查询
    import time
    start = time.time()
    
    result = conn.execute(text("""
        EXPLAIN ANALYZE
        SELECT item_code, name, embedding <-> :query_vector as distance
        FROM items
        ORDER BY embedding <-> :query_vector
        LIMIT 5
    """), {"query_vector": vector_str})
    
    explain_output = result.fetchall()
    elapsed = time.time() - start
    
    print(f"   查询耗时: {elapsed:.3f}s")
    print()
    print("   执行计划:")
    for row in explain_output:
        print(f"   {row[0]}")
    
    # 检查是否使用了索引
    full_plan = "\n".join([row[0] for row in explain_output])
    if "Index Scan" in full_plan or "Bitmap Index Scan" in full_plan:
        print("\n   ✅ 使用了索引扫描")
    elif "Seq Scan" in full_plan:
        print("\n   ❌ 使用了全表扫描（慢！）")
    else:
        print("\n   ⚠️  无法判断扫描方式")
    
    print()
    
    # 5. 检查 pgvector 扩展
    print("5️⃣  检查 pgvector 扩展")
    print("-" * 70)
    
    result = conn.execute(text("""
        SELECT extname, extversion
        FROM pg_extension
        WHERE extname = 'vector'
    """))
    
    row = result.fetchone()
    if row:
        print(f"   ✅ pgvector 已安装")
        print(f"   版本: {row[1]}")
    else:
        print("   ❌ pgvector 未安装")
    
    print()

print("=" * 70)
print("💡 建议:")
print("   1. 如果没有 HNSW 索引，需要创建")
print("   2. 如果使用全表扫描，需要调整 HNSW 参数")
print("   3. 如果查询 > 5s，考虑增加内存或优化参数")
print("=" * 70)
