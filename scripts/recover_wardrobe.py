#!/usr/bin/env python3
"""
衣橱数据恢复脚本 — 从 R2 下载图片，用 Qwen 多模态 AI 识别，重建数据库记录
"""

import json
import time
import sys
import os
import tempfile
import base64
import asyncio
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
import boto3
import dashscope
from dashscope import TextEmbedding
from openai import OpenAI

# 配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}
R2_PUBLIC_URL_BASE = "https://pub-851399ad134d447ea68cd62dbadd90a4.r2.dev"
USER_ID = 1  # 用户 ID

ANALYZE_PROMPT = """你是一个专业的五行穿搭顾问。请分析图片中的衣物，返回五行属性。

请根据以下规则分析：

1. 颜色五行对照：
   - 红、橙、紫、粉色 → 火
   - 黄、棕、土色、卡其 → 土
   - 白、金、银、米色 → 金
   - 黑、蓝、灰、藏青 → 水
   - 绿、青、墨绿 → 木

2. 材质五行对照：
   - 丝绸、棉麻、棉布 → 木
   - 皮革、毛呢、灯芯绒 → 土
   - 羽绒、羊毛、针织 → 水或火（视颜色而定）
   - 金属装饰、亮片 → 金
   - 化纤、混纺 → 根据主要成分判断

3. 款式五行对照：
   - 正装、西装、职业装 → 金
   - 运动休闲、宽松舒适 → 木
   - 华丽礼服、时尚前卫 → 火
   - 简约基础、经典款 → 水
   - 自然田园、森系 → 土

4. 厚度等级判断：
   - 轻薄：T恤、衬衫、薄裙
   - 适中：卫衣、针织衫、风衣
   - 加厚：毛衣、厚外套
   - 厚重：羽绒服、棉服、厚大衣

请以 JSON 格式输出分析结果：
{
    "primary_element": "主五行（金/木/水/火/土之一）",
    "secondary_element": "次五行（可选，或null）",
    "color": "主色调名称",
    "color_element": "颜色对应的五行",
    "material": "材质名称",
    "material_element": "材质对应的五行",
    "style": "风格（正式/休闲/运动/商务/时尚）",
    "shape": "款式形状（长方/正方/圆形/三角/不规则）",
    "details": ["款式细节1", "款式细节2"],
    "energy_intensity": 0.8,
    "category": "分类（上装/下装/外套/鞋履/配饰/裙装/套装/其他）",
    "season": ["适合季节"],
    "tags": ["标签1", "标签2"],
    "applicable_weather": ["晴", "多云"],
    "applicable_seasons": ["春", "秋"],
    "temperature_range": {"min": 10, "max": 25},
    "functionality": ["日常", "商务"],
    "thickness_level": "适中",
    "suggested_name": "物品名称（如：红色羊毛大衣）"
}"""


def log(level, msg):
    print(f"[{level}] {msg}")


def get_r2_client(env):
    """创建 R2/S3 客户端"""
    return boto3.client(
        's3',
        endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=env['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=env['R2_SECRET_ACCESS_KEY'],
        region_name='auto'
    )


def list_wardrobe_images(r2_client, bucket='wuxing-wardrobe'):
    """列出 R2 中的衣橱图片"""
    paginator = r2_client.get_paginator('list_objects_v2')
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix='wardrobe/1/'):
        if 'Contents' in page:
            for obj in page['Contents']:
                keys.append(obj['Key'])
    return sorted(keys)


def download_image(r2_client, key, bucket='wuxing-wardrobe'):
    """从 R2 下载图片，返回 base64 编码"""
    import io
    buf = io.BytesIO()
    r2_client.download_fileobj(bucket, key, buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def analyze_image_with_qwen(image_b64, api_key, base_url):
    """用 Qwen 多模态模型分析图片"""
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model="qwen-vl-plus",
        messages=[
            {"role": "system", "content": "你是专业的五行穿搭顾问，擅长分析衣物的五行属性。请严格按照JSON格式输出，不要输出其他内容。"},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                {"type": "text", "text": ANALYZE_PROMPT}
            ]}
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
        timeout=60
    )

    return json.loads(response.choices[0].message.content)


def get_embedding(text, api_key):
    """用 DashScope 生成向量"""
    dashscope.api_key = api_key
    response = TextEmbedding.call(
        model='text-embedding-v3',
        input=text
    )
    if response.status_code == 200:
        return response.output['embeddings'][0]['embedding']
    else:
        raise Exception(f"Embedding error: {response.code} - {response.message}")


def build_embedding_text(name, category, color, material, element, tags):
    """构建向量文本"""
    text = f"这是一件{name}，属于{category}类别。"
    text += f"颜色是{color}，五行属{element}。"
    text += f"面料为{material}。"
    if tags:
        text += f"适合场景：{', '.join(tags)}。"
    return text


def insert_wardrobe_item(conn, user_id, item_data, image_url, embedding, image_name):
    """插入衣橱记录"""
    cur = conn.cursor()
    sql = """
    INSERT INTO user_wardrobe (
        user_id, item_code, name, category, image_url,
        primary_element, secondary_element, energy_intensity,
        attributes_detail, embedding, gender,
        applicable_weather, applicable_seasons, temperature_range,
        functionality, thickness_level, is_custom, is_active
    ) VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s, true, true
    )
    ON CONFLICT DO NOTHING
    """
    attrs = {
        "颜色": {"名称": item_data.get("color", ""), "主五行": item_data.get("color_element", "")},
        "面料": {"名称": item_data.get("material", ""), "主五行": item_data.get("material_element", "")},
        "款式": {"形状": item_data.get("shape", ""), "细节": item_data.get("details", [])}
    }

    cur.execute(sql, (
        user_id,
        f"U{user_id}_{image_name}",
        item_data.get("suggested_name", "未命名衣物"),
        item_data.get("category", "其他"),
        image_url,
        item_data.get("primary_element", "金"),
        item_data.get("secondary_element"),
        float(item_data.get("energy_intensity", 0.5)),
        json.dumps(attrs, ensure_ascii=False),
        embedding,
        "中性",
        json.dumps(item_data.get("applicable_weather", []), ensure_ascii=False),
        json.dumps(item_data.get("applicable_seasons", []), ensure_ascii=False),
        json.dumps(item_data.get("temperature_range", {}), ensure_ascii=False),
        json.dumps(item_data.get("functionality", []), ensure_ascii=False),
        item_data.get("thickness_level", "适中")
    ))
    conn.commit()
    cur.close()


async def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    env = dict(os.environ)

    api_key = env.get("DASHSCOPE_API_KEY", "")
    base_url = env.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    if not api_key or api_key == "sk-placeholder":
        log("ERROR", "DASHSCOPE_API_KEY 未设置！")
        return 1

    dashscope.api_key = api_key

    log("INFO", "=" * 50)
    log("INFO", "衣橱数据恢复 — R2图片 → AI识别 → 重建DB")
    log("INFO", "=" * 50)

    # 1. 连接 R2
    log("INFO", "连接 R2 存储...")
    r2_client = get_r2_client(env)

    # 2. 列出图片
    keys = list_wardrobe_images(r2_client)
    log("INFO", f"R2 中找到 {len(keys)} 张衣橱图片")

    if not keys:
        log("WARNING", "没有找到衣橱图片，退出")
        return 0

    # 3. 连接数据库
    log("INFO", "连接数据库...")
    conn = psycopg2.connect(**DB_CONFIG)

    # 4. 逐个处理
    success = 0
    fail = 0
    for i, key in enumerate(keys):
        image_name = Path(key).stem  # 如 "94"
        image_url = f"{R2_PUBLIC_URL_BASE}/{key}"

        try:
            log("INFO", f"[{i+1}/{len(keys)}] 处理 {image_name}...")

            # 下载图片
            image_b64 = download_image(r2_client, key)

            # AI 多模态识别
            result = analyze_image_with_qwen(image_b64, api_key, base_url)
            name = result.get("suggested_name", f"衣物_{image_name}")
            log("INFO", f"  AI识别: {name} | 五行:{result.get('primary_element')} | {result.get('category')}")

            # 生成向量
            emb_text = build_embedding_text(
                name,
                result.get("category", "其他"),
                result.get("color", ""),
                result.get("material", ""),
                result.get("primary_element", "金"),
                result.get("tags", [])
            )
            embedding = get_embedding(emb_text, api_key)

            # 写入数据库
            insert_wardrobe_item(conn, USER_ID, result, image_url, embedding, image_name)
            success += 1

            # 避免 API 限流
            time.sleep(1)

        except Exception as e:
            log("ERROR", f"  处理失败: {e}")
            fail += 1
            conn.rollback()
            time.sleep(2)

    conn.close()

    # 5. 结果
    log("INFO", "-" * 50)
    log("SUCCESS", f"恢复完成: {success} 成功, {fail} 失败")

    # 验证
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM user_wardrobe WHERE user_id = %s", (USER_ID,))
    count = cur.fetchone()[0]
    log("INFO", f"数据库衣橱记录: {count} 条")
    cur.close()
    conn.close()

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
