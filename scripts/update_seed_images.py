#!/usr/bin/env python3
"""
更新公共种子库图片URL
将生成的图片关联到 items 表

使用方式: python scripts/update_seed_images.py
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# 数据库配置
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "wuxing_db"),
    "user": os.getenv("DB_USER", "wuxing_user"),
    "password": os.getenv("DB_PASSWORD", "wuxing_password")
}

# 图片目录配置
IMAGE_DIRS = [
    "data/generated_images/seed_data_100/20260401/20260401",
]

# 图片基础 URL（前端访问路径）
# 图片放在 public/images/seed/ 目录下，前端可通过 /images/seed/ITEM_001.png 访问
IMAGE_BASE_URL = "/images/seed"


def log(level: str, message: str):
    """打印日志"""
    print(f"[{level}] {message}")


def run_migration():
    """执行数据库迁移：添加 image_url 字段"""
    log("INFO", "执行数据库迁移...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'items' AND column_name = 'image_url'
        """)
        
        if cur.fetchone():
            log("INFO", "image_url 字段已存在，跳过迁移")
        else:
            # 添加字段
            cur.execute("ALTER TABLE items ADD COLUMN image_url VARCHAR(500)")
            conn.commit()
            log("SUCCESS", "已添加 image_url 字段到 items 表")
    
    except Exception as e:
        conn.rollback()
        log("ERROR", f"数据库迁移失败: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def extract_item_code(filename: str) -> str:
    """
    从文件名提取物品编码
    
    例如: image_001_正红色真丝衬衫...png -> ITEM_001
    """
    match = re.match(r'image_(\d+)_', filename)
    if match:
        num = int(match.group(1))
        return f"ITEM_{num:03d}"
    return None


def get_image_mapping() -> Dict[str, str]:
    """
    扫描图片目录，建立 item_code -> 图片URL 的映射
    
    Returns:
        Dict[item_code, image_url]
    """
    base_path = Path(__file__).parent.parent
    mapping = {}
    
    for dir_path in IMAGE_DIRS:
        full_path = base_path / dir_path
        if not full_path.exists():
            log("WARN", f"目录不存在: {full_path}")
            continue
        
        # 获取所有 png 文件
        for png_file in sorted(full_path.glob("*.png")):
            item_code = extract_item_code(png_file.name)
            if item_code:
                # 优先选择"极简主义风格"或"日式极简"的图片
                # 这些风格更符合优衣库风格
                if "极简主义" in png_file.name or "日式极简" in png_file.name:
                    # 构建图片 URL
                    # 使用相对路径，前端会处理
                    image_url = f"{IMAGE_BASE_URL}/{item_code}.png"
                    mapping[item_code] = image_url
                elif item_code not in mapping:
                    # 如果没有找到极简风格的图片，使用第一张
                    image_url = f"{IMAGE_BASE_URL}/{item_code}.png"
                    mapping[item_code] = image_url
    
    log("INFO", f"找到 {len(mapping)} 个图片映射")
    return mapping


def copy_images_to_public(mapping: Dict[str, str]):
    """
    将图片复制到 Next.js public 目录，并重命名为 item_code.png
    
    这样前端可以通过 /images/seed/ITEM_001.png 访问
    """
    base_path = Path(__file__).parent.parent
    public_dir = base_path / "apps" / "web" / "public" / "images" / "seed"
    public_dir.mkdir(parents=True, exist_ok=True)
    
    # 记录已复制的 item_code，避免重复
    copied_items = set()
    
    for dir_path in IMAGE_DIRS:
        full_path = base_path / dir_path
        if not full_path.exists():
            continue
        
        for png_file in sorted(full_path.glob("*.png")):
            item_code = extract_item_code(png_file.name)
            if item_code and item_code in mapping and item_code not in copied_items:
                # 优先复制极简风格的图片
                if "极简主义" in png_file.name or "日式极简" in png_file.name:
                    dest = public_dir / f"{item_code}.png"
                    shutil.copy2(png_file, dest)
                    copied_items.add(item_code)
                elif item_code not in copied_items:
                    # 如果目标目录还没有这个物品的图片，复制第一张
                    dest = public_dir / f"{item_code}.png"
                    shutil.copy2(png_file, dest)
                    copied_items.add(item_code)
    
    log("INFO", f"复制了 {len(copied_items)} 张图片到 {public_dir}")


def update_database(mapping: Dict[str, str]):
    """
    更新数据库中的 image_url 字段
    
    Args:
        mapping: item_code -> image_url 映射
    """
    if not mapping:
        log("ERROR", "没有图片映射需要更新")
        return
    
    log("INFO", "连接数据库...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # 更新每个物品的 image_url
        updated_count = 0
        for item_code, image_url in mapping.items():
            cur.execute(
                "UPDATE items SET image_url = %s WHERE item_code = %s",
                (image_url, item_code)
            )
            if cur.rowcount > 0:
                updated_count += 1
        
        conn.commit()
        log("SUCCESS", f"更新了 {updated_count} 条记录")
        
        # 验证更新结果
        cur.execute("SELECT COUNT(*) FROM items WHERE image_url IS NOT NULL")
        count = cur.fetchone()[0]
        log("INFO", f"数据库中共有 {count} 条记录有图片URL")
        
    except Exception as e:
        conn.rollback()
        log("ERROR", f"更新数据库失败: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def main():
    """主函数"""
    log("INFO", "=" * 60)
    log("INFO", "更新公共种子库图片URL")
    log("INFO", "=" * 60)
    
    # 1. 执行数据库迁移
    log("INFO", "步骤1: 执行数据库迁移（添加 image_url 字段）...")
    run_migration()
    
    # 2. 获取图片映射
    log("INFO", "步骤2: 扫描图片目录...")
    mapping = get_image_mapping()
    
    if not mapping:
        log("ERROR", "没有找到任何图片映射")
        return 1
    
    # 显示前5个映射
    log("INFO", "示例映射:")
    for i, (code, url) in enumerate(list(mapping.items())[:5]):
        log("INFO", f"  {code} -> {url}")
    
    # 3. 复制图片到 public 目录
    log("INFO", "步骤3: 复制图片到 public 目录...")
    copy_images_to_public(mapping)
    
    # 4. 更新数据库
    log("INFO", "步骤4: 更新数据库...")
    update_database(mapping)
    
    log("INFO", "=" * 60)
    log("SUCCESS", "图片URL更新完成！")
    log("INFO", "前端可通过 /images/seed/ITEM_XXX.png 访问图片")
    log("INFO", "=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
