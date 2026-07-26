#!/usr/bin/env python3
"""
为扩充物品（ITEM_176~500，共 325 件）批量生成图片并上线:
1. DashScope ImageSynthesis (wanx2.1-t2i-turbo) 生成
2. 本地备份 data/uploads/seed_images/
3. 上传 Cloudflare R2
4. 同时回写本地 DB 和 Zeabur 生产 DB 的 image_url

特性:
- 断点续跑：本地 DB 已有 image_url 的物品自动跳过
- 颜色强调：中文色名 → 英文精确色描述（修复小件饰品色偏问题）
- 文玩/饰品 专用 prompt（微距珠宝风）

用法:
  python scripts/generate_expansion_images.py            # 全量执行
  python scripts/generate_expansion_images.py --limit 10 # 只处理前 10 件（试跑）
"""

import json
import os
import sys
import time
import random
import argparse
import hashlib
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
import boto3
from botocore.config import Config
import dashscope
from dashscope import ImageSynthesis

IMAGE_MODEL = "wanx2.1-t2i-turbo"
IMAGE_SIZE = "1024*1024"
OUTPUT_DIR = ROOT / "data" / "uploads" / "seed_images"
R2_FOLDER = "uploads/seed-items"
SEED_PATH = ROOT / "data" / "seeds" / "seed_data_expansion_500.json"

LOCAL_DB = "postgresql://wuxing_user:wuxing_password@localhost:5432/wuxing_db"

# 中文色名 → 英文精确色描述（生图模型对中文色词还原不稳，用英文强调）
COLOR_EN = {
    "丹红": "vivid vermilion red", "亮银": "bright silver", "军绿": "army olive green",
    "卡其": "khaki tan", "墨绿": "deep forest green", "墨黑": "jet black, deep pure black",
    "大地棕": "earthy brown", "姜黄": "ginger yellow", "幽绿": "deep jade green",
    "明黄": "bright amber yellow", "星空蓝": "deep midnight blue", "晶白": "crystal white",
    "曜黑": "obsidian black, glossy pure black", "月白": "moon white, pale ivory white",
    "朱红": "cinnabar red", "松石绿": "turquoise green", "柠檬黄": "soft lemon yellow",
    "棕色": "rich brown", "樱粉": "cherry blossom pink", "橄榄绿": "olive green",
    "橘红": "orange red", "檀紫褐": "dark purplish sandalwood brown", "正红": "true red, classic Chinese red",
    "浅海蓝": "light ocean blue", "浅灰": "light gray", "浅粉": "light pink",
    "海军蓝": "navy blue", "深蓝": "dark blue", "深褐": "dark chocolate brown",
    "炭灰": "charcoal gray", "焦糖": "caramel brown", "燕麦": "oatmeal beige",
    "玫红": "rose magenta", "珊瑚粉": "coral pink", "珍珠白": "pearl white",
    "珠光白": "pearlescent white", "琥珀金": "amber gold", "砖红": "brick red",
    "竹青": "bamboo green", "米黄": "cream beige", "糖白": "sugar white",
    "紫红": "burgundy purple red", "纯白": "pure white", "翠绿": "emerald green",
    "脂白": "mutton-fat white jade color", "草木绿": "greenery grass green",
    "蔷薇粉": "rose pink", "薄荷绿": "mint green", "藏蓝": "dark navy indigo",
    "褐金": "dark goldenrod", "象牙白": "ivory white", "赭褐": "ochre brown",
    "酒红": "wine red", "铂金灰": "platinum gray", "铂银": "platinum silver",
    "银灰": "silver gray", "锦红": "rich persimmon red", "雾霾蓝": "dusty haze blue",
    "青碧": "cyan jade green", "青金蓝": "lapis lazuli blue", "靛蓝": "indigo blue",
    "香槟金": "champagne gold", "驼色": "camel tan", "鸡油黄": "buttery amber yellow",
    "黑色": "black",
}

WUXING_BG = {
    "木": ["soft sage green", "muted mint", "warm olive"],
    "火": ["warm terracotta", "soft coral blush", "muted rose beige"],
    "土": ["warm sand beige", "soft cream", "light taupe"],
    "金": ["cool light gray", "silver mist", "soft platinum"],
    "水": ["deep navy blue", "soft steel blue", "muted indigo"],
}

CAT_EN = {
    "上装": "top garment", "下装": "bottom/pants", "裙装": "dress/skirt",
    "外套": "outerwear/jacket", "鞋履": "shoes/footwear", "配饰": "accessory",
    "饰品": "fine jewelry piece", "文玩": "traditional Chinese beaded artifact",
}


def load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def get_prod_url() -> str:
    for line in (ROOT / ".env.production").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(".env.production 中未找到 DATABASE_URL")


def get_r2_client():
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


def build_prompt(item: dict) -> str:
    name = item["物品名称"]
    category = item["分类"]
    color_info = item["属性详情"]["颜色"]
    color_cn = color_info["名称"]
    wuxing = color_info["主五行"]
    fabric_name = item["属性详情"]["面料"]["名称"]
    details = item["属性详情"]["款式"].get("细节", [])

    color_en = COLOR_EN.get(color_cn, color_cn)
    cat_en = CAT_EN.get(category, "clothing item")
    bg_color = random.choice(WUXING_BG.get(wuxing, ["soft neutral gray"]))
    detail_str = "，".join(details[:3]) if details else ""

    prompt = (
        f"Professional product photography of a {color_en} {cat_en}, {name}. "
        f"Material: {fabric_name}. "
        f"The main color MUST be {color_en}. "
    )
    if detail_str:
        prompt += f"Details: {detail_str}. "
    if category in ("文玩", "饰品"):
        prompt += (
            f"Studio lighting, {bg_color} gradient background, "
            "luxury jewelry e-commerce style, macro lens close-up, "
            "sharp focus, 8K quality, elegant display stand."
        )
    else:
        prompt += (
            f"Studio lighting, {bg_color} gradient background, "
            "high-end e-commerce style, "
            "sharp focus, 8K quality, no model, flat lay or mannequin display."
        )
    return prompt


def generate_image(prompt: str) -> bytes:
    resp = ImageSynthesis.call(model=IMAGE_MODEL, prompt=prompt, n=1, size=IMAGE_SIZE)
    if resp.status_code != 200:
        raise Exception(f"ImageSynthesis error: {resp.status_code} - {resp.code}: {resp.message}")
    url = resp.output.results[0].url
    import urllib.request
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def upload_to_r2(r2_client, image_data: bytes, item_code: str) -> str:
    safe_name = hashlib.md5(item_code.encode()).hexdigest()[:8]
    key = f"{R2_FOLDER}/{item_code}_{safe_name}.jpg"

    from PIL import Image
    img = Image.open(BytesIO(image_data))
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=90)
    buf.seek(0)

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 件（0=全部）")
    args = parser.parse_args()

    load_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1
    dashscope.api_key = api_key

    with open(SEED_PATH, encoding="utf-8") as f:
        items = json.load(f)
    if args.limit:
        items = items[:args.limit]

    r2_client = get_r2_client()
    local_db = psycopg2.connect(LOCAL_DB)
    remote_db = psycopg2.connect(get_prod_url(), connect_timeout=10)

    # 断点续跑：跳过本地已有图的
    cur = local_db.cursor()
    cur.execute("SELECT item_code FROM items WHERE image_url IS NOT NULL")
    has_image = {r[0] for r in cur.fetchall()}
    cur.close()

    todo = [it for it in items if it["物品 ID"] not in has_image]
    print(f"总 {len(items)} 件，已有图 {len(items) - len(todo)}，待生成 {len(todo)}", flush=True)

    success = failed = 0
    for i, item in enumerate(todo):
        code, name = item["物品 ID"], item["物品名称"]
        print(f"[{i+1}/{len(todo)}] {code} {name}", flush=True)
        try:
            image_data = generate_image(build_prompt(item))
            (OUTPUT_DIR / f"{code}.jpg").write_bytes(image_data)
            image_url = upload_to_r2(r2_client, image_data, code)

            for db in (local_db, remote_db):
                c = db.cursor()
                c.execute("UPDATE items SET image_url = %s, updated_at = CURRENT_TIMESTAMP WHERE item_code = %s",
                          (image_url, code))
                db.commit()
                c.close()

            print(f"  ✓ {image_url}", flush=True)
            success += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"  ✗ 失败: {e}", flush=True)
            failed += 1
            local_db.rollback()
            remote_db.rollback()
            time.sleep(3)

    print(f"\n{'='*50}", flush=True)
    print(f"完成: {success} 成功, {failed} 失败", flush=True)

    # 验证两库
    for label, db in (("本地", local_db), ("Zeabur", remote_db)):
        c = db.cursor()
        c.execute("SELECT count(*) FILTER (WHERE image_url IS NOT NULL), count(*) FROM items")
        with_img, total = c.fetchone()
        print(f"{label}库: {with_img}/{total} 有图", flush=True)
        c.close()

    local_db.close()
    remote_db.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
