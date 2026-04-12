#!/usr/bin/env python3
"""
使用 psycopg2 直接导入 SQL 文件到 Zeabur 数据库
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Zeabur 数据库连接信息
DB_CONFIG = {
    "host": "43.129.75.126",
    "port": 30216,
    "database": "zeabur",
    "user": "root",
    "password": "DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q"
}

SQL_FILE = "/Users/mingyang/Desktop/shunyishang/scripts/export_wardrobe_to_zeabur.sql"


def read_sql_file(file_path):
    """读取 SQL 文件"""
    logger.info(f"📖 读取 SQL 文件: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SQL 文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    file_size = os.path.getsize(file_path)
    logger.info(f"📊 文件大小: {file_size / 1024 / 1024:.2f} MB")
    
    return content


def split_sql_statements(sql_content):
    """分割 SQL 语句"""
    # 按分号分割，但要注意向量数据中的分号
    statements = []
    current = []
    
    for line in sql_content.split('\n'):
        # 跳过注释
        if line.strip().startswith('--'):
            continue
        
        current.append(line)
        
        # 如果行以分号结尾，这是一个完整的语句
        if line.strip().endswith(';'):
            statement = '\n'.join(current)
            if statement.strip():
                statements.append(statement)
            current = []
    
    # 处理最后可能剩余的语句
    if current:
        statement = '\n'.join(current)
        if statement.strip():
            statements.append(statement)
    
    return statements


def import_to_zeabur():
    """导入数据到 Zeabur"""
    logger.info("="*60)
    logger.info("🚀 开始导入衣橱数据到 Zeabur")
    logger.info("="*60)
    logger.info(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    logger.info(f"用户: {DB_CONFIG['user']}")
    logger.info("")
    
    # 读取 SQL 文件
    sql_content = read_sql_file(SQL_FILE)
    
    # 分割 SQL 语句
    statements = split_sql_statements(sql_content)
    total = len(statements)
    logger.info(f"📝 共 {total} 条 SQL 语句")
    logger.info("")
    
    # 连接数据库
    logger.info("🔌 连接数据库...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("✅ 数据库连接成功")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False
    
    try:
        with conn.cursor() as cur:
            start_time = time.time()
            success_count = 0
            error_count = 0
            
            for idx, statement in enumerate(statements, 1):
                try:
                    # 每 10 条输出一次进度
                    if idx % 10 == 0 or idx == total:
                        elapsed = time.time() - start_time
                        logger.info(f"进度: {idx}/{total} ({idx/total*100:.1f}%) - 耗时: {elapsed:.1f}s")
                    
                    cur.execute(statement)
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ 执行失败 (语句 {idx}): {str(e)[:200]}")
                    
                    # 如果是关键错误，停止执行
                    if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                        logger.error("❌ 表不存在，请确保数据库已初始化")
                        return False
            
            # 输出统计
            elapsed = time.time() - start_time
            logger.info("")
            logger.info("="*60)
            logger.info("✅ 导入完成！")
            logger.info(f"📊 总语句数: {total}")
            logger.info(f"✅ 成功: {success_count}")
            logger.info(f"❌ 失败: {error_count}")
            logger.info(f"⏱️  总耗时: {elapsed:.1f}s")
            logger.info("="*60)
            
            return error_count == 0
            
    except Exception as e:
        logger.error(f"❌ 导入异常: {e}")
        return False
    finally:
        conn.close()
        logger.info("🔌 数据库连接已关闭")


if __name__ == "__main__":
    success = import_to_zeabur()
    
    if success:
        logger.info("\n🎉 所有数据已成功导入 Zeabur！")
    else:
        logger.info("\n⚠️  导入过程中出现错误，请检查日志")
    
    print()
