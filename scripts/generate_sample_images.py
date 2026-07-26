#!/usr/bin/env python3
"""
从扩充数据（ITEM_176~500）中挑几件代表性物品生成样图，供人工评审
- 只保存到本地 data/uploads/sample_expansion/，不上传 R2、不更新数据库
- prompt 逻辑与 generate_item_images.py 一致，并补充 文玩/饰品 的类别映射
"""

import json
import os
import sys
import time
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import dashscope
from dashscope import ImageSynthesis

IMAGE_MODEL = "wanx2.1-t2i-turbo"
IMAGE_SIZE = "1024*1024"
OUTPUT_DIR = ROOT / "data" / "uploads" / "sample_expansion"
SEED_PATH = ROOT / "data" / "seeds" / "seed_data_expansion_500.json"

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


def build_prompt(item: dict) -> str:
    name = item["物品名称"]
    category = item["分类"]
    color_info = item["属性详情"]["颜色"]
    color_name = color_info["名称"]
    wuxing = color_info["主五行"]
    fabric_name = item["属性详情"]["面料"]["名称"]
    details = item["属性详情"]["款式"].get("细节", [])

    cat_en = CAT_EN.get(category, "clothing item")
    bg_color = random.choice(WUXING_BG.get(wuxing, ["soft neutral gray"]))
    detail_str = "，".join(details[:3]) if details else ""

    prompt = (
        f"Professional product photography of a {color_name} {cat_en}, {name}. "
        f"Material: {fabric_name}. "
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


def pick_samples(items: list) -> list:
    """挑 4 件代表性物品: 文玩手串 / 男装 / 裙装 / 男士饰品"""
    picked, seen = [], set()

    def first(pred, label):
        for it in items:
            if it["物品 ID"] not in seen and pred(it):
                picked.append((label, it))
                seen.add(it["物品 ID"])
                return

    first(lambda x: x["分类"] == "文玩" and "手串" in x["物品名称"], "文玩")
    first(lambda x: x["分类"] == "上装" and x["适用性别"] == "男", "男装")
    first(lambda x: x["分类"] == "裙装", "裙装")
    first(lambda x: x["分类"] == "饰品" and x["适用性别"] == "男", "男士饰品")
    return picked


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1
    dashscope.api_key = api_key

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    with open(SEED_PATH, encoding="utf-8") as f:
        items = json.load(f)

    samples = pick_samples(items)
    print(f"待生成样图: {len(samples)} 件")

    failed = 0
    for label, item in samples:
        code, name = item["物品 ID"], item["物品名称"]
        prompt = build_prompt(item)
        print(f"\n[{label}] {code} {name}")
        print(f"  prompt: {prompt}")
        try:
            resp = ImageSynthesis.call(model=IMAGE_MODEL, prompt=prompt, n=1, size=IMAGE_SIZE)
            if resp.status_code != 200:
                raise Exception(f"{resp.code}: {resp.message}")
            url = resp.output.results[0].url
            import urllib.request
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            out = OUTPUT_DIR / f"{code}_{name}.png"
            out.write_bytes(data)
            print(f"  ✓ 已保存: {out}")
            time.sleep(2)
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            failed += 1

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
