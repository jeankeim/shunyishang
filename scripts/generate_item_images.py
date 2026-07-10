#!/usr/bin/env python3
"""
为新增的50条种子物品生成图片：
1. 调用 DashScope ImageSynthesis API 生成服装图片
2. 上传到 Cloudflare R2
3. 更新 items 表的 image_url 字段
"""

import json
import os
import sys
import time
import uuid
import hashlib
import random
from io import BytesIO
from pathlib import Path

# 项目路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
import boto3
from botocore.config import Config
from dashscope import ImageSynthesis
import dashscope


# ============================================================
# 配置
# ============================================================
ITEM_START = 101
ITEM_END = 150
IMAGE_MODEL = "wanx2.1-t2i-turbo"  # 快速图片生成模型
IMAGE_SIZE = "1024*1024"
OUTPUT_DIR = ROOT / "data" / "uploads" / "seed_images"
R2_FOLDER = "uploads/seed-items"


def load_env():
    """加载 .env"""
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def get_db_conn():
    return psycopg2.connect(os.environ.get(
        "DATABASE_URL",
        "postgresql://wuxing_user:wuxing_password@localhost:5432/wuxing_db"
    ))


def get_r2_client():
    """初始化 R2 客户端"""
    account_id = os.environ.get("R2_ACCOUNT_ID", "")
    access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    if not all([account_id, access_key, secret_key]):
        raise ValueError("R2 配置不完整")
    
    return boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4', retries={'max_attempts': 3, 'mode': 'standard'}),
        region_name='auto'
    )


# 五行 → 背景色调映射（相生原则）
WUXING_BG = {
    "木": ["soft sage green", "muted mint", "warm olive", "gentle forest green"],
    "火": ["warm terracotta", "soft coral blush", "warm cream", "muted rose beige"],
    "土": ["warm sand beige", "soft cream", "light taupe", "warm ivory"],
    "金": ["cool light gray", "silver mist", "pale blue-gray", "soft platinum"],
    "水": ["deep navy blue", "soft steel blue", "cool teal", "muted indigo"],
}

# 场景 → 背景色调微调
SCENE_BG_TONE = {
    "商务": "professional muted tone, sophisticated",
    "面试": "clean professional neutral, confident",
    "正式": "elegant refined tone, premium",
    "约会": "warm romantic soft tone, gentle",
    "婚礼": "elegant champagne or soft blush, celebratory",
    "派对": "vibrant yet refined, festive",
    "运动": "energetic fresh tone, dynamic",
    "户外": "natural earthy tone, organic",
    "旅行": "warm adventurous tone, relaxed",
    "居家": "cozy warm neutral, comfortable",
    "休闲": "relaxed casual tone, easygoing",
}


def build_image_prompt(item: dict) -> str:
    """
    根据物品信息构建图片生成 prompt
    生成专业的服装产品摄影风格图片，带智能色彩背景
    """
    name = item.get("物品名称", "")
    category = item.get("分类", "")
    color_info = item.get("属性详情", {}).get("颜色", {})
    color_name = color_info.get("名称", "")
    wuxing = color_info.get("主五行", "")
    fabric_info = item.get("属性详情", {}).get("面料", {})
    fabric_name = fabric_info.get("名称", "")
    style_info = item.get("属性详情", {}).get("款式", {})
    details = style_info.get("细节", [])
    thickness = item.get("厚度等级", "")
    scene_tags = item.get("适用标签", [])
    
    # 类别映射到英文
    cat_en = {
        "上装": "top garment", "下装": "bottom/pants", "裙装": "dress/skirt",
        "外套": "outerwear/jacket", "鞋履": "shoes/footwear", "配饰": "accessory"
    }.get(category, "clothing item")
    
    detail_str = "，".join(details[:3]) if details else ""
    
    # 根据五行选择背景色
    bg_colors = WUXING_BG.get(wuxing, ["soft neutral gray"])
    bg_color = random.choice(bg_colors)
    
    # 根据场景标签微调背景描述
    scene_tone = ""
    for tag in scene_tags:
        if tag in SCENE_BG_TONE:
            scene_tone = SCENE_BG_TONE[tag]
            break
    
    # 构建背景描述
    if scene_tone:
        bg_desc = f"{scene_tone}, {bg_color} gradient background"
    else:
        bg_desc = f"{bg_color} gradient background"
    
    prompt = (
        f"Professional fashion product photography of a {color_name} {cat_en}, "
        f"{name}. "
        f"Material: {fabric_name}. "
    )
    if detail_str:
        prompt += f"Details: {detail_str}. "
    if thickness:
        prompt += f"Thickness: {thickness}. "
    
    prompt += (
        f"Studio lighting, {bg_desc}, "
        "high-end e-commerce style, "
        "sharp focus, 8K quality, no model, flat lay or mannequin display."
    )
    
    return prompt


def generate_image(prompt: str, api_key: str) -> bytes:
    """
    调用 DashScope ImageSynthesis 生成图片
    返回图片二进制数据
    """
    dashscope.api_key = api_key
    
    response = ImageSynthesis.call(
        model=IMAGE_MODEL,
        prompt=prompt,
        n=1,
        size=IMAGE_SIZE,
    )
    
    if response.status_code == 200:
        # 获取图片 URL
        image_url = response.output.results[0].url
        # 下载图片
        import urllib.request
        with urllib.request.urlopen(image_url, timeout=30) as resp:
            return resp.read()
    else:
        raise Exception(f"ImageSynthesis error: {response.status_code} - {response.code}: {response.message}")


def upload_to_r2(r2_client, image_data: bytes, item_code: str, item_name: str) -> str:
    """
    上传图片到 R2，返回公共 URL
    """
    # 生成文件名
    safe_name = hashlib.md5(item_code.encode()).hexdigest()[:8]
    filename = f"{item_code}_{safe_name}.jpg"
    key = f"{R2_FOLDER}/{filename}"
    
    # 转换为 JPEG（R2 存储优化）
    from PIL import Image
    img = Image.open(BytesIO(image_data))
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)
    
    # 上传（S3 metadata 仅支持 ASCII，不传中文）
    r2_client.put_object(
        Bucket=os.environ.get("R2_BUCKET_NAME", "wuxing-wardrobe"),
        Key=key,
        Body=buf.read(),
        ContentType="image/jpeg",
        Metadata={"item_code": item_code}
    )
    
    public_url = os.environ.get("R2_PUBLIC_URL", "")
    return f"{public_url}/{key}"


def main():
    load_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1
    
    # 读取种子数据
    seed_path = ROOT / "data" / "seeds" / "seed_data_100_enhanced.json"
    with open(seed_path, "r", encoding="utf-8") as f:
        all_items = json.load(f)
    
    new_items = [
        item for item in all_items
        if ITEM_START <= int(item["物品 ID"].split("_")[1]) <= ITEM_END
    ]
    print(f"待处理: {len(new_items)} 件物品")
    
    # 初始化服务
    r2_client = get_r2_client()
    db_conn = get_db_conn()
    
    success = 0
    skipped = 0
    failed = 0
    
    for i, item in enumerate(new_items):
        item_code = item["物品 ID"]
        item_name = item["物品名称"]
        
        # 检查是否已有图片
        cur = db_conn.cursor()
        cur.execute("SELECT image_url FROM items WHERE item_code = %s", (item_code,))
        row = cur.fetchone()
        cur.close()
        
        if row and row[0]:
            print(f"[{i+1}/{len(new_items)}] 跳过（已有图片）: {item_code} {item_name}")
            skipped += 1
            continue
        
        print(f"[{i+1}/{len(new_items)}] 生成图片: {item_code} {item_name}")
        
        try:
            # 1. 构建 prompt
            prompt = build_image_prompt(item)
            
            # 2. 生成图片
            image_data = generate_image(prompt, api_key)
            print(f"  ✓ 图片生成成功 ({len(image_data)} bytes)")
            
            # 3. 本地保存备份
            local_path = OUTPUT_DIR / f"{item_code}.jpg"
            with open(local_path, "wb") as f:
                f.write(image_data)
            
            # 4. 上传到 R2
            image_url = upload_to_r2(r2_client, image_data, item_code, item_name)
            print(f"  ✓ R2 上传成功: {image_url}")
            
            # 5. 更新数据库
            cur = db_conn.cursor()
            cur.execute(
                "UPDATE items SET image_url = %s WHERE item_code = %s",
                (image_url, item_code)
            )
            db_conn.commit()
            cur.close()
            print(f"  ✓ 数据库已更新")
            
            success += 1
            
            # 避免 API 限流
            time.sleep(2)
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            failed += 1
            db_conn.rollback()
            time.sleep(3)
    
    # 清理
    db_conn.close()
    
    print(f"\n{'='*50}")
    print(f"完成: {success} 成功, {skipped} 跳过, {failed} 失败")
    print(f"{'='*50}")
    
    # 验证
    db_conn = get_db_conn()
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items WHERE image_url IS NOT NULL")
    total_with_image = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM items WHERE item_code LIKE 'ITEM_1%' AND image_url IS NOT NULL")
    new_with_image = cur.fetchone()[0]
    cur.close()
    db_conn.close()
    
    print(f"\n数据库图片统计:")
    print(f"  总物品有图片: {total_with_image}/150")
    print(f"  新增物品有图片: {new_with_image}/50")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
