#!/usr/bin/env python3
"""
导出 user_wardrobe 表数据到 Zeabur 数据库
同时上传图片到 Cloudflare R2 并更新 image_url
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import boto3
from botocore.config import Config
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 本地数据库配置
LOCAL_DB_CONFIG = {
    "host": "localhost",
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}

# Cloudflare R2 配置
R2_CONFIG = {
    "account_id": os.getenv("R2_ACCOUNT_ID", "e79f49e5f684d41d722a3dfe3d42a1af"),
    "access_key_id": os.getenv("R2_ACCESS_KEY_ID", "171aa90ebdccbefcf326674d996690b5"),
    "secret_access_key": os.getenv("R2_SECRET_ACCESS_KEY", "9602c58b441ceae1ab3bab12c431f52129389b0fef47e4c6f682ca68309c6d70"),
    "bucket_name": os.getenv("R2_BUCKET_NAME", "wuxing-wardrobe"),
    "public_url": os.getenv("R2_PUBLIC_URL", "https://pub-851399ad134d447ea68cd62dbadd90a4.r2.dev")
}

# 输出文件
OUTPUT_FILE = "/Users/mingyang/Desktop/shunyishang/scripts/export_wardrobe_to_zeabur.sql"

# 本地图片目录
LOCAL_IMAGE_DIR = Path("/Users/mingyang/Desktop/shunyishang/data/uploads/wardrobe")


def init_r2_client():
    """初始化 Cloudflare R2 客户端"""
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
    """
    上传图片到 R2
    返回 R2 公开 URL
    """
    if not local_path or not Path(local_path).exists():
        logger.warning(f"图片文件不存在: {local_path}")
        return None
    
    # 生成 R2 对象键
    file_ext = Path(local_path).suffix
    object_key = f"wardrobe/{user_id}/{item_id}{file_ext}"
    
    try:
        # 上传图片
        s3_client.upload_file(
            local_path,
            R2_CONFIG['bucket_name'],
            object_key,
            ExtraArgs={
                'ContentType': 'image/jpeg',
                'CacheControl': 'public, max-age=31536000'  # 缓存1年
            }
        )
        
        # 生成公开 URL
        public_url = f"{R2_CONFIG['public_url']}/{object_key}"
        logger.info(f"✅ 上传成功: {public_url}")
        
        return public_url
        
    except Exception as e:
        logger.error(f"❌ 上传失败 {local_path}: {e}")
        return None


def escape_sql(s):
    """转义 SQL 字符串"""
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"


def convert_local_path_to_absolute(image_url: str, user_id: int, item_id: int) -> str:
    """
    将相对路径转换为本地绝对路径
    处理长文件名问题：如果路径太长，尝试查找 item_id 开头的文件
    """
    if not image_url:
        return None
    
    # 如果已经是 R2 URL，直接返回
    if image_url.startswith('http'):
        return image_url
    
    # 如果是相对路径，转换为绝对路径
    if image_url.startswith('/uploads/'):
        # 从 URL 中提取路径
        relative_path = image_url.replace('/uploads/', '')
        local_path = Path("/Users/mingyang/Desktop/shunyishang/data/uploads") / relative_path
        
        # 检查文件是否存在（捕获长文件名异常）
        try:
            if local_path.exists():
                return str(local_path)
        except OSError as e:
            logger.warning(f"  ⚠️  路径检查失败: {e}")
        
        # 如果文件不存在（可能文件名太长），尝试查找 item_id 开头的文件
        user_dir = Path("/Users/mingyang/Desktop/shunyishang/data/uploads/wardrobe") / str(user_id)
        if user_dir.exists():
            # 查找以 item_id_ 开头的文件
            for file in user_dir.glob(f"{item_id}_*"):
                if file.is_file():
                    logger.info(f"  🔍 找到匹配文件: {file.name[:50]}...")
                    return str(file)
        
        return str(local_path)  # 返回原路径，让调用方处理
    
    return None


def export_wardrobe():
    """导出 user_wardrobe 数据"""
    logger.info("=== 开始导出 user_wardrobe 数据 ===")
    
    # 连接本地数据库
    conn = psycopg2.connect(**LOCAL_DB_CONFIG)
    s3_client = init_r2_client()
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 查询所有衣橱数据
            cur.execute("""
                SELECT 
                    id, user_id, item_code, name, category, image_url,
                    primary_element, secondary_element, energy_intensity,
                    attributes_detail, embedding,
                    gender, applicable_weather, applicable_seasons, 
                    temperature_range, functionality, thickness_level,
                    is_custom, is_active,
                    purchase_date, wear_count, last_worn_date, 
                    is_favorite, notes
                FROM user_wardrobe
                WHERE is_active = TRUE
                ORDER BY user_id, id
            """)
            
            items = cur.fetchall()
            total = len(items)
            
            logger.info(f"查询到 {total} 条衣橱记录")
            
            if total == 0:
                logger.warning("没有找到任何衣橱数据，退出")
                return
            
            # 统计信息
            uploaded_count = 0
            failed_count = 0
            skipped_count = 0
            
            # 写入 SQL 文件
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write("-- =====================================================\n")
                f.write("-- WuXing AI Stylist - User Wardrobe 数据导入脚本\n")
                f.write(f"-- 记录数: {total}\n")
                f.write("-- 用于导入 Zeabur 数据库\n")
                f.write("-- =====================================================\n\n")
                
                for idx, item in enumerate(items, 1):
                    logger.info(f"处理进度: {idx}/{total} (用户{item['user_id']}, 物品{item['id']})")
                    
                    item_id = item['id']
                    user_id = item['user_id']
                    original_image_url = item['image_url']
                    new_image_url = original_image_url
                    
                    # 处理图片上传
                    if original_image_url:
                        local_path = None
                        
                        try:
                            local_path = convert_local_path_to_absolute(original_image_url, user_id, item_id)
                        except OSError as e:
                            logger.warning(f"  ⚠️  路径转换失败: {e}")
                            local_path = None
                        
                        if local_path:
                            try:
                                path_exists = Path(local_path).exists()
                            except OSError as e:
                                logger.warning(f"  ⚠️  路径检查失败: {e}")
                                path_exists = False
                            
                            if path_exists:
                                # 检查是否已经是 R2 URL
                                if original_image_url.startswith('http'):
                                    logger.info(f"  ⏭️  已是 R2 URL，跳过上传")
                                    skipped_count += 1
                                else:
                                    # 上传到 R2
                                    logger.info(f"  📤 上传图片: {local_path[-80:]}")
                                    new_image_url = upload_to_r2(s3_client, local_path, user_id, item_id)
                                    
                                    if new_image_url:
                                        uploaded_count += 1
                                    else:
                                        failed_count += 1
                                        new_image_url = original_image_url  # 失败则保留原 URL
                            else:
                                logger.warning(f"  ⚠️  图片文件不存在: {local_path[-80:]}")
                                skipped_count += 1
                    
                    # 处理 JSONB 字段
                    attr = escape_sql(json.dumps(item['attributes_detail'], ensure_ascii=False) if item['attributes_detail'] else '{}')
                    weather = escape_sql(json.dumps(item['applicable_weather'], ensure_ascii=False) if item['applicable_weather'] else '[]')
                    seasons = escape_sql(json.dumps(item['applicable_seasons'], ensure_ascii=False) if item['applicable_seasons'] else '[]')
                    temp = escape_sql(json.dumps(item['temperature_range'], ensure_ascii=False) if item['temperature_range'] else '{}')
                    func = escape_sql(json.dumps(item['functionality'], ensure_ascii=False) if item['functionality'] else '[]')
                    
                    # 处理 embedding 向量
                    if item['embedding']:
                        emb_data = item['embedding']
                        if isinstance(emb_data, str):
                            try:
                                emb_list = json.loads(emb_data)
                            except:
                                emb_list = [float(x) for x in emb_data.strip('[]').split(',') if x.strip()]
                        elif isinstance(emb_data, (list, tuple)):
                            emb_list = emb_data
                        else:
                            emb_list = list(emb_data)
                        
                        emb = "[" + ",".join(str(float(x)) for x in emb_list) + "]"
                        embedding = f"'{emb}'::vector"
                    else:
                        embedding = "NULL"
                    
                    # 处理可能为 NULL 的字段
                    energy = item['energy_intensity'] if item['energy_intensity'] is not None else 'NULL'
                    purchase_date = escape_sql(item['purchase_date']) if item['purchase_date'] else 'NULL'
                    last_worn_date = escape_sql(item['last_worn_date']) if item['last_worn_date'] else 'NULL'
                    notes = escape_sql(item['notes']) if item['notes'] else 'NULL'
                    
                    # 生成 INSERT SQL（使用 ON CONFLICT 实现幂等）
                    sql = f"""INSERT INTO user_wardrobe (id, user_id, item_code, name, category, image_url, primary_element, secondary_element, energy_intensity, attributes_detail, embedding, gender, applicable_weather, applicable_seasons, temperature_range, functionality, thickness_level, is_custom, is_active, purchase_date, wear_count, last_worn_date, is_favorite, notes, created_at, updated_at) VALUES ({item_id}, {user_id}, {escape_sql(item['item_code'])}, {escape_sql(item['name'])}, {escape_sql(item['category'])}, {escape_sql(new_image_url)}, {escape_sql(item['primary_element'])}, {escape_sql(item['secondary_element'])}, {energy}, {attr}, {embedding}, {escape_sql(item['gender'])}, {weather}, {seasons}, {temp}, {func}, {escape_sql(item['thickness_level'])}, {item['is_custom']}, {item['is_active']}, {purchase_date}, {item['wear_count']}, {last_worn_date}, {item['is_favorite']}, {notes}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) ON CONFLICT (id) DO UPDATE SET user_id = EXCLUDED.user_id, item_code = EXCLUDED.item_code, name = EXCLUDED.name, category = EXCLUDED.category, image_url = EXCLUDED.image_url, primary_element = EXCLUDED.primary_element, secondary_element = EXCLUDED.secondary_element, energy_intensity = EXCLUDED.energy_intensity, attributes_detail = EXCLUDED.attributes_detail, embedding = EXCLUDED.embedding, gender = EXCLUDED.gender, applicable_weather = EXCLUDED.applicable_weather, applicable_seasons = EXCLUDED.applicable_seasons, temperature_range = EXCLUDED.temperature_range, functionality = EXCLUDED.functionality, thickness_level = EXCLUDED.thickness_level, is_custom = EXCLUDED.is_custom, is_active = EXCLUDED.is_active, purchase_date = EXCLUDED.purchase_date, wear_count = EXCLUDED.wear_count, last_worn_date = EXCLUDED.last_worn_date, is_favorite = EXCLUDED.is_favorite, notes = EXCLUDED.notes, updated_at = CURRENT_TIMESTAMP;
"""
                    f.write(sql)
            
            # 输出统计信息
            logger.info(f"\n{'='*50}")
            logger.info(f"✅ 导出完成！")
            logger.info(f"📁 SQL 文件: {OUTPUT_FILE}")
            logger.info(f"📊 总记录数: {total}")
            logger.info(f"📤 上传成功: {uploaded_count}")
            logger.info(f"⏭️  跳过（已是R2）: {skipped_count}")
            logger.info(f"❌ 上传失败: {failed_count}")
            logger.info(f"{'='*50}")
            logger.info(f"\n📝 下一步:")
            logger.info(f"1. 检查 SQL 文件: {OUTPUT_FILE}")
            logger.info(f"2. 导入到 Zeabur 数据库:")
            logger.info(f"   PGPASSWORD=<password> psql -h <zeabur-host> -U <user> -d <database> -f {OUTPUT_FILE}")
            
    finally:
        conn.close()


if __name__ == "__main__":
    export_wardrobe()
