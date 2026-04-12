#!/usr/bin/env python3
"""
修复 user_wardrobe 表中的图片 URL
将本地路径更新为 R2 URL
"""

import psycopg2
import boto3
from botocore.config import Config
from pathlib import Path
import logging
import os
import re

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

# R2 配置
R2_CONFIG = {
    "account_id": os.getenv("R2_ACCOUNT_ID", "e79f49e5f684d41d722a3dfe3d42a1af"),
    "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "171aa90ebdccbefcf326674d996690b5"),
    "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "9602c58b441ceae1ab3bab12c431f52129389b0fef47e4c6f682ca68309c6d70"),
    "bucket_name": os.getenv("R2_BUCKET_NAME", "wuxing-wardrobe"),
    "public_url": os.getenv("R2_PUBLIC_URL", "https://pub-851399ad134d447ea68cd62dbadd90a4.r2.dev")
}


def init_r2_client():
    """初始化 R2 客户端"""
    endpoint_url = f"https://{R2_CONFIG['account_id']}.r2.cloudflarestorage.com"
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_CONFIG['access_key_id'],
        aws_secret_access_key=R2_CONFIG['secret_access_key'],
        config=Config(signature_version='s3v4')
    )
    
    return s3_client


def upload_to_r2(s3_client, local_path: str, user_id: int, item_id: int) -> str:
    """上传图片到 R2"""
    if not local_path or not Path(local_path).exists():
        logger.warning(f"  ⚠️  文件不存在: {local_path[-60:]}")
        return None
    
    # 生成 R2 对象键
    file_ext = Path(local_path).suffix or '.png'
    object_key = f"wardrobe/{user_id}/{item_id}{file_ext}"
    
    try:
        s3_client.upload_file(
            local_path,
            R2_CONFIG['bucket_name'],
            object_key,
            ExtraArgs={
                'ContentType': 'image/jpeg' if file_ext.lower() in ['.jpg', '.jpeg'] else 'image/png',
                'CacheControl': 'public, max-age=31536000'
            }
        )
        
        public_url = f"{R2_CONFIG['public_url']}/{object_key}"
        logger.info(f"  ✅ 上传成功: {object_key}")
        return public_url
        
    except Exception as e:
        logger.error(f"  ❌ 上传失败: {e}")
        return None


def find_local_file(image_url: str, user_id: int, item_id: int) -> str:
    """
    查找本地文件
    处理长文件名问题
    """
    if not image_url or not image_url.startswith('/uploads/'):
        return None
    
    # 尝试直接路径
    local_path = Path("/Users/mingyang/Desktop/shunyishang/data") / image_url.lstrip('/')
    
    try:
        if local_path.exists():
            return str(local_path)
    except OSError:
        pass
    
    # 尝试在用户目录下查找 item_id 开头的文件
    user_dir = Path("/Users/mingyang/Desktop/shunyishang/data/uploads/wardrobe") / str(user_id)
    if user_dir.exists():
        for file in user_dir.glob(f"{item_id}_*"):
            if file.is_file():
                return str(file)
    
    return None


def fix_image_urls():
    """修复图片 URL"""
    logger.info("="*70)
    logger.info("🔧 开始修复 user_wardrobe 图片 URL")
    logger.info("="*70)
    
    # 连接数据库
    conn = psycopg2.connect(**DB_CONFIG)
    s3_client = init_r2_client()
    
    try:
        with conn.cursor() as cur:
            # 查询所有需要修复的记录
            cur.execute('''
                SELECT id, user_id, name, image_url
                FROM user_wardrobe
                WHERE image_url LIKE '/uploads/%'
                ORDER BY user_id, id
            ''')
            
            records = cur.fetchall()
            total = len(records)
            
            logger.info(f"📊 找到 {total} 条需要修复的记录")
            logger.info("")
            
            if total == 0:
                logger.info("✅ 所有图片 URL 已经是 R2 格式")
                return
            
            uploaded = 0
            skipped = 0
            failed = 0
            updated = 0
            
            for idx, (item_id, user_id, name, old_url) in enumerate(records, 1):
                logger.info(f"[{idx}/{total}] 处理: 用户{user_id}, ID{item_id} - {name[:30]}")
                
                # 查找本地文件
                local_file = find_local_file(old_url, user_id, item_id)
                
                if not local_file:
                    logger.warning(f"  ⚠️  找不到本地文件，跳过")
                    skipped += 1
                    continue
                
                # 上传到 R2
                new_url = upload_to_r2(s3_client, local_file, user_id, item_id)
                
                if new_url:
                    # 更新数据库
                    cur.execute('''
                        UPDATE user_wardrobe
                        SET image_url = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (new_url, item_id))
                    conn.commit()
                    
                    uploaded += 1
                    updated += 1
                    logger.info(f"  ✅ 已更新: {new_url[-50:]}")
                else:
                    failed += 1
                    logger.warning(f"  ⚠️  上传失败，保留原 URL")
                
                logger.info("")
            
            # 统计结果
            logger.info("="*70)
            logger.info("✅ 修复完成！")
            logger.info(f"📊 总记录数: {total}")
            logger.info(f"📤 上传成功: {uploaded}")
            logger.info(f"⏭️  跳过: {skipped}")
            logger.info(f"❌ 失败: {failed}")
            logger.info(f"💾 数据库更新: {updated}")
            logger.info("="*70)
            
    finally:
        conn.close()


if __name__ == "__main__":
    fix_image_urls()
