#!/usr/bin/env python3
"""
为 A' 转写入库的 300 件物品（ITEM_501~800）生成国风淡雅商品图

设计约束（用户指定）:
- 不出现人物/模特 —— 纯平铺或悬挂静物
- 国风淡雅 —— 宣纸质感低饱和背景，极简构图，忌花哨
- 不参考任何品牌原图 —— 纯文生图，规避版权风险

流程:
1. 从 items 表读取 501~800 且 image_url 为空的物品
2. 按「物品描述 + 五行背景色 + 国风静物风格后缀」构建中文提示词
3. wanx2.1-t2i-turbo 文生图（带 negative_prompt 排除人物）
4. 上传 OSS → 回填 items.image_url（本地库）

用法:
  python -m scripts.collection.generate_transform_images --limit 10   # 抽检
  python -m scripts.collection.generate_transform_images             # 全量补齐
"""

import argparse
import hashlib
import os
import sys
import time
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2  # noqa: E402
import oss2  # noqa: E402
from dashscope import ImageSynthesis  # noqa: E402
import dashscope  # noqa: E402

IMAGE_MODEL = "wanx2.1-t2i-turbo"
IMAGE_SIZE = "1024*1024"
OUTPUT_DIR = ROOT / "data" / "uploads" / "transform_images"
OSS_FOLDER = "uploads/transform-items"

# 五行 → 淡雅国风背景色（低饱和，宣纸质感）
WUXING_BG = {
    "木": "淡雅竹青色宣纸背景",
    "火": "浅绛红色宣纸背景",
    "土": "米白驼色宣纸背景",
    "金": "素白银灰色宣纸背景",
    "水": "淡黛蓝色宣纸背景",
}

# 品类 → 静物呈现方式（全部无人物、无衣架，纯平铺/静物）
CAT_DISPLAY = {
    "上装": "衣物平整铺放于素色布面",
    "下装": "裤装整齐折叠平铺于素色布面",
    "裙装": "裙装平铺展开呈现自然褶裥",
    "外套": "大衣平整铺放于素色布面",
    "鞋履": "鞋履端正摆放于素色台面",
    "配饰": "配饰静物特写摆放于素色台面",
    "饰品": "饰品静物特写摆放于素色台面",
    "文玩": "文玩静物特写摆放于素色台面",
}

STYLE_SUFFIX = (
    "中国传统美学静物摄影，淡雅国风风格，柔和自然光，"
    "低饱和度高级感，极简留白构图，质感细腻，无文字水印"
)

NEGATIVE_PROMPT = (
    "人物, 模特, 人脸, 人体, 手部, 衣架, 衣杆, 挂钩, "
    "动物, 鸟, 宠物, 活体, "
    "花哨图案, 复杂纹理, 高饱和颜色, 杂乱背景, 文字, 水印, logo"
)

# 易被模型误解为活体的材质词 → 显式澄清（仅饰品部件，画面无动物）
MATERIAL_CLARIFY = {
    "鸵鸟毛": "细密羽毛状丝线流苏",
    "羽毛": "羽毛状装饰部件",
    "虎眼石": "猫眼效应宝石",
}


def load_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_db_conn():
    return psycopg2.connect(os.environ.get(
        "DATABASE_URL",
        "postgresql://wuxing_user:wuxing_password@localhost:5432/wuxing_db"
    ))


def get_oss_bucket():
    auth = oss2.Auth(os.environ["OSS_ACCESS_KEY_ID"], os.environ["OSS_ACCESS_KEY_SECRET"])
    return oss2.Bucket(auth, os.environ["OSS_ENDPOINT"], os.environ["OSS_BUCKET_NAME"])


def fetch_pending_items(conn, limit):
    cur = conn.cursor()
    cur.execute("""
        SELECT item_code, name, category, primary_element,
               color, material, style, attributes_detail
        FROM items
        WHERE image_url IS NULL
          AND CAST(SUBSTRING(item_code FROM 6) AS INTEGER) >= 501
        ORDER BY item_code
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    return [dict(zip(
        ["item_code", "name", "category", "primary_element",
         "color", "material", "style", "attributes_detail"], r)) for r in rows]


def build_prompt(item: dict) -> str:
    bg = WUXING_BG.get(item["primary_element"], "米白宣纸背景")
    display = CAT_DISPLAY.get(item["category"], "静物平铺摆放")
    color = item.get("color") or ""
    material = item.get("material") or ""
    detail = item["attributes_detail"].get("款式", {}).get("细节", "")
    if isinstance(detail, list):
        detail = "，".join(detail[:2])

    prompt = f"一件{color}{material}{item['name'].replace(color, '', 1).strip()}，{display}，{bg}，{STYLE_SUFFIX}"
    if detail:
        prompt += f"，细节：{detail}"
    for k, v in MATERIAL_CLARIFY.items():
        if k in item["name"]:
            prompt += f"，其中{k}表现为{v}，画面中只有商品本身"
    return prompt


def generate_image(prompt: str) -> bytes:
    response = ImageSynthesis.call(
        model=IMAGE_MODEL,
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        n=1,
        size=IMAGE_SIZE,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ImageSynthesis {response.status_code} {response.code}: {response.message}")
    import urllib.request
    with urllib.request.urlopen(response.output.results[0].url, timeout=30) as resp:
        return resp.read()


def upload_to_oss(bucket, image_data: bytes, item_code: str) -> str:
    from PIL import Image
    img = Image.open(BytesIO(image_data))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)

    safe = hashlib.md5(item_code.encode()).hexdigest()[:8]
    key = f"{OSS_FOLDER}/{item_code}_{safe}.jpg"
    bucket.put_object(key, buf.getvalue(), headers={"Content-Type": "image/jpeg"})
    return f"{os.environ['OSS_PUBLIC_URL']}/{key}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300, help="本次处理上限")
    args = parser.parse_args()

    load_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1
    dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]

    conn = get_db_conn()
    items = fetch_pending_items(conn, args.limit)
    print(f"待生成: {len(items)} 件")
    if not items:
        return 0

    bucket = get_oss_bucket()
    ok = fail = 0
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item['item_code']} {item['name']}")
        try:
            prompt = build_prompt(item)
            data = generate_image(prompt)
            local_path = OUTPUT_DIR / f"{item['item_code']}.jpg"
            local_path.write_bytes(data)
            url = upload_to_oss(bucket, data, item["item_code"])
            cur = conn.cursor()
            cur.execute("UPDATE items SET image_url=%s WHERE item_code=%s",
                        (url, item["item_code"]))
            conn.commit()
            cur.close()
            ok += 1
            print(f"  ✓ {url}")
            time.sleep(1)
        except Exception as e:
            fail += 1
            print(f"  ✗ {e}")
            conn.rollback()
            time.sleep(2)

    conn.close()
    print(f"\n完成: {ok} 成功, {fail} 失败")
    print(f"本地备份目录: {OUTPUT_DIR}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
