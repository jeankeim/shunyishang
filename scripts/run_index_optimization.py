"""
执行数据库索引优化脚本
"""

import psycopg2
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://wuxing_user:wuxing_password@localhost:5432/wuxing_db"

def execute_index_optimization():
    """执行索引优化"""
    
    sql_file = Path(__file__).parent / "optimize_indexes.sql"
    
    if not sql_file.exists():
        logger.error(f"SQL文件不存在: {sql_file}")
        return
    
    sql_content = sql_file.read_text(encoding='utf-8')
    
    logger.info("开始执行索引优化...")
    start_time = time.time()
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # CREATE INDEX CONCURRENTLY 需要在 autocommit 模式下执行
        
        with conn.cursor() as cur:
            # 分割 SQL 语句并逐条执行
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
            
            total = len(statements)
            for i, stmt in enumerate(statements, 1):
                # 跳过 SELECT 查询（仅用于验证）
                if stmt.upper().startswith('SELECT') or stmt.upper().startswith('EXPLAIN'):
                    continue
                
                try:
                    logger.info(f"[{i}/{total}] 执行: {stmt[:80]}...")
                    cur.execute(stmt)
                    logger.info(f"  ✅ 成功")
                except Exception as e:
                    logger.warning(f"  ⚠️  跳过: {e}")
        
        elapsed = time.time() - start_time
        logger.info(f"\n✅ 索引优化完成! 耗时: {elapsed:.2f}s")
        
        # 验证索引
        logger.info("\n📊 验证索引创建结果...")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename, indexname 
                FROM pg_indexes 
                WHERE tablename IN ('items', 'user_wardrobe', 'users')
                AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname
            """)
            
            indexes = cur.fetchall()
            logger.info(f"\n已创建 {len(indexes)} 个索引:")
            for tablename, indexname in indexes:
                logger.info(f"  - {tablename}.{indexname}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ 索引优化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    execute_index_optimization()
