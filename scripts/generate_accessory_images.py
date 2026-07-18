#!/usr/bin/env python3
"""
为传统文化饰品（ITEM_151~ITEM_175）批量生成商品图片
使用 curl 调用 DashScope API（绕过 Python SSL 问题）
流程：提交任务 → 轮询结果 → 下载图片 → 上传 R2 → 更新 DB
"""

import json
import os
import sys
import time
import hashlib
import subprocess
import random
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ============================================================
# 配置
# ============================================================
SEED_PATH = ROOT / "data" / "seeds" / "seed_data_accessories.json"
IMAGE_MODEL = "wanx2.1-t2i-turbo"
IMAGE_SIZE = "1024*1024"
OUTPUT_DIR = ROOT / "data" / "uploads" / "accessory_images"
R2_FOLDER = "uploads/accessory-items"
POLL_INTERVAL = 5  # 秒
MAX_POLL = 60      # 最多轮询 60 次 (5分钟)

# 五行 → 背景色调（典雅风格）
WUXING_BG = {
    "金": ["cool platinum silk background", "soft silver mist background", "pale moonlight gray background"],
    "木": ["antique jade green background", "muted celadon background", "warm sandalwood tone background"],
    "水": ["deep obsidian black background", "ink wash gradient background", "midnight sapphire background"],
    "火": ["warm cinnabar red background", "aged vermilion background", "soft coral amber background"],
    "土": ["warm honey amber background", "antique ivory background", "muted loess earth background"],
}


def load_env():
    with open(ROOT / ".env") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def curl_json(url, headers=None, data=None, method="POST"):
    """用 curl 发 JSON 请求，返回解析后的 dict"""
    cmd = ["curl", "-s", "--connect-timeout", "15", "--max-time", "30"]
    if method != "GET":
        cmd += ["-X", method]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
    if data:
        cmd += ["-d", json.dumps(data)]
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if result.returncode != 0:
        raise Exception(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def curl_download(url, timeout=60):
    """用 curl 下载文件，返回 bytes"""
    cmd = ["curl", "-s", "--connect-timeout", "15", "--max-time", str(timeout), "-L", url]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    if result.returncode != 0:
        raise Exception(f"curl download failed: {result.stderr}")
    return result.stdout


def build_prompt(item: dict) -> str:
    """构建饰品专用 prompt：无人物、典雅、有质感"""
    name = item.get("物品名称", "")
    color_info = item.get("属性详情", {}).get("颜色", {})
    color_name = color_info.get("名称", "")
    wuxing = color_info.get("主五行", "")
    fabric_info = item.get("属性详情", {}).get("面料", {})
    fabric_name = fabric_info.get("名称", "")
    style_info = item.get("属性详情", {}).get("款式", {})
    details = style_info.get("细节", [])
    remark = color_info.get("标注备注", "")

    detail_str = ", ".join(details[:3]) if details else ""
    bg_options = WUXING_BG.get(wuxing, ["warm neutral tone background"])
    bg = random.choice(bg_options)

    prompt = (
        f"Exquisite Chinese traditional jewelry product photography: {name}. "
        f"Color: {color_name}. Material: {fabric_name}. "
    )
    if detail_str:
        prompt += f"Craft details: {detail_str}. "
    if remark:
        prompt += f"Cultural meaning: {remark}. "
    prompt += (
        f"{bg}. "
        "NO human, NO hands, NO fingers, NO body parts. "
        "Product only, centered composition, studio soft lighting. "
        "High-end e-commerce jewelry photography, sharp macro focus, "
        "8K ultra-detailed, luxurious texture, silk display surface."
    )
    return prompt


def submit_image_task(prompt: str, api_key: str) -> str:
    """提交异步图片生成任务，返回 task_id"""
    resp = curl_json(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        data={
            "model": IMAGE_MODEL,
            "input": {"prompt": prompt},
            "parameters": {"n": 1, "size": IMAGE_SIZE},
        },
    )
    task_id = resp.get("output", {}).get("task_id")
    if not task_id:
        raise Exception(f"提交任务失败: {json.dumps(resp, ensure_ascii=False)}")
    return task_id


def poll_task(task_id: str, api_key: str) -> str:
    """轮询任务状态，返回图片 URL"""
    url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    for i in range(MAX_POLL):
        resp = curl_json(url, headers=headers, method="GET")
        status = resp.get("output", {}).get("task_status", "")

        if status == "SUCCEEDED":
            results = resp.get("output", {}).get("results", [])
            if results:
                return results[0].get("url", "")
            raise Exception(f"任务成功但无结果: {json.dumps(resp, ensure_ascii=False)}")
        elif status == "FAILED":
            raise Exception(f"任务失败: {json.dumps(resp, ensure_ascii=False)}")
        else:
            time.sleep(POLL_INTERVAL)

    raise Exception(f"任务超时 ({MAX_POLL * POLL_INTERVAL}s)")


def upload_to_r2(image_data: bytes, item_code: str) -> str:
    """上传图片到 R2，返回公共 URL"""
    from PIL import Image

    safe_name = hashlib.md5(item_code.encode()).hexdigest()[:8]
    filename = f"{item_code}_{safe_name}.jpg"
    key = f"{R2_FOLDER}/{filename}"

    img = Image.open(BytesIO(image_data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92, optimize=True)
    buf.seek(0)

    import boto3
    from botocore.config import Config

    r2_client = boto3.client(
        "s3",
        endpoint_url=f'https://{os.environ["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com',
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        region_name="auto",
    )

    r2_client.put_object(
        Bucket=os.environ.get("R2_BUCKET_NAME", "wuxing-wardrobe"),
        Key=key,
        Body=buf.read(),
        ContentType="image/jpeg",
        CacheControl="public, max-age=31536000",
        Metadata={"item_code": item_code},
    )

    return f'{os.environ["R2_PUBLIC_URL"]}/{key}'


def main():
    load_env()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        all_items = json.load(f)
    print(f"待处理饰品: {len(all_items)} 件")

    import psycopg2
    db_conn = psycopg2.connect(os.environ.get("DATABASE_URL"))

    success = 0
    skipped = 0
    failed = 0

    for i, item in enumerate(all_items):
        item_code = item["物品 ID"]
        item_name = item["物品名称"]

        # 检查是否已有图片
        cur = db_conn.cursor()
        cur.execute("SELECT image_url FROM items WHERE item_code = %s", (item_code,))
        row = cur.fetchone()
        cur.close()

        if row and row[0]:
            print(f"[{i+1}/{len(all_items)}] 跳过（已有图片）: {item_code} {item_name}")
            skipped += 1
            continue

        print(f"[{i+1}/{len(all_items)}] 生成: {item_code} {item_name}")

        try:
            # 1. 构建 prompt
            prompt = build_prompt(item)

            # 2. 提交异步任务
            task_id = submit_image_task(prompt, api_key)
            print(f"  任务已提交: {task_id[:16]}...")

            # 3. 轮询等待结果
            image_url = poll_task(task_id, api_key)
            print(f"  ✓ 图片生成成功")

            # 4. 下载图片
            image_data = curl_download(image_url)
            print(f"  ✓ 下载完成 ({len(image_data)} bytes)")

            # 5. 本地备份
            local_path = OUTPUT_DIR / f"{item_code}.jpg"
            with open(local_path, "wb") as f:
                f.write(image_data)

            # 6. 上传 R2
            r2_url = upload_to_r2(image_data, item_code)
            print(f"  ✓ R2: {r2_url[:60]}...")

            # 7. 更新 DB
            cur = db_conn.cursor()
            cur.execute(
                "UPDATE items SET image_url = %s, updated_at = CURRENT_TIMESTAMP WHERE item_code = %s",
                (r2_url, item_code),
            )
            db_conn.commit()
            cur.close()
            print(f"  ✓ DB 已更新")

            success += 1
            time.sleep(1)

        except Exception as e:
            print(f"  ✗ 失败: {e}")
            failed += 1
            db_conn.rollback()
            time.sleep(2)

    db_conn.close()

    print(f"\n{'='*50}")
    print(f"完成: {success} 成功, {skipped} 跳过, {failed} 失败")
    print(f"{'='*50}")

    # 验证
    db_conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items WHERE item_code >= 'ITEM_151' AND item_code <= 'ITEM_175' AND image_url IS NOT NULL")
    cnt = cur.fetchone()[0]
    print(f"\n饰品图片统计: {cnt}/{len(all_items)} 件已有图片")
    cur.close()
    db_conn.close()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
