#!/usr/bin/env python3
"""
为缺失图片的衣橱记录设置默认占位图
"""

import psycopg2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': '43.129.75.126',
    'port': 30216,
    'database': 'zeabur',
    'user': 'root',
    'password': 'DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q'
}

# 默认占位图 URL（使用 R2 上已有的图片）
DEFAULT_IMAGE_URL = "https://pub-851399ad134d447ea68cd62dbadd90a4.r2.dev/wardrobe/1/101.png"


def fix_missing_images():
    """修复缺失图片的记录"""
    logger.info("="*70)
    logger.info("🔧 开始修复缺失图片的衣橱记录")
    logger.info("="*70)
    logger.info(f"默认占位图: {DEFAULT_IMAGE_URL}")
    logger.info("")
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cur:
            # 更新所有本地路径的记录
            cur.execute('''
                UPDATE user_wardrobe
                SET image_url = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE image_url LIKE '/uploads/%%'
                RETURNING id, user_id, name
            ''', (DEFAULT_IMAGE_URL,))
            
            updated_records = cur.fetchall()
            conn.commit()
            
            total = len(updated_records)
            
            logger.info(f"✅ 修复完成！")
            logger.info(f"📊 更新记录数: {total}")
            logger.info("")
            
            if total > 0:
                logger.info("更新的记录示例（前10条）:")
                logger.info("-" * 70)
                for id, user_id, name in updated_records[:10]:
                    logger.info(f"  ID {id}, 用户 {user_id}: {name}")
                
                if total > 10:
                    logger.info(f"  ... 还有 {total - 10} 条记录")
            
            # 验证结果
            cur.execute('''
                SELECT 
                    CASE 
                        WHEN image_url LIKE '%r2.dev%' THEN 'R2 URL'
                        ELSE '其他'
                    END as url_type,
                    COUNT(*) as count
                FROM user_wardrobe
                GROUP BY url_type
            ''')
            
            logger.info("")
            logger.info("📊 当前 image_url 分布:")
            for url_type, count in cur.fetchall():
                logger.info(f"  {url_type}: {count} 条")
            
    except Exception as e:
        logger.error(f"❌ 修复失败: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    fix_missing_images()
