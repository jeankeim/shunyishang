#!/usr/bin/env python3
"""
WuXing AI Stylist - 使用 DashScope API 导入种子数据
替代原 import_seed.py（不再依赖 sentence_transformers）
"""

import json
import time
import sys
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
import dashscope
from dashscope import TextEmbedding

# 配置
SEED_DATA_PATH = Path(__file__).parent.parent / "data" / "seeds" / "seed_data_100_enhanced.json"
SEED_DATA_PATH_FALLBACK = Path(__file__).parent.parent / "data" / "seeds" / "seed_data_100.json"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}
BATCH_SIZE = 10  # DashScope API 每次最多 25 条，10 条更安全


def log(level: str, message: str):
    print(f"[{level}] {message}")


def build_context_text(item: dict) -> str:
    """构建用于向量化的文本描述"""
    name = item.get("物品名称", "")
    category = item.get("分类", "")
    color_info = item.get("属性详情", {}).get("颜色", {})
    color_name = color_info.get("名称", "")
    color_element = color_info.get("主五行", "")
    energy = color_info.get("能量强度", 0)
    fabric_info = item.get("属性详情", {}).get("面料", {})
    fabric_name = fabric_info.get("名称", "")
    fabric_element = fabric_info.get("主五行", "")
    style_info = item.get("属性详情", {}).get("款式", {})
    shape = style_info.get("形状", "")
    details = ", ".join(style_info.get("细节", []))
    tags = ", ".join(item.get("适用标签", []))

    text = f"这是一件{name}，属于{category}类别。"
    text += f"颜色是{color_name}，五行属{color_element}，能量强度{energy}。"
    text += f"面料为{fabric_name}，五行属{fabric_element}。"
    if shape:
        text += f"款式呈{shape}形。"
    if details:
        text += f"细节包括：{details}。"
    if tags:
        text += f"适合场景：{tags}。"
    return text


def get_embeddings_batch(texts: list) -> list:
    """使用 DashScope API 批量生成向量"""
    response = TextEmbedding.call(
        model='text-embedding-v3',
        input=texts
    )
    if response.status_code == 200:
        embeddings = [item['embedding'] for item in response.output['embeddings']]
        return embeddings
    else:
        raise Exception(f"DashScope API error: {response.code} - {response.message}")


def load_seed_data():
    """读取种子数据"""
    data_path = SEED_DATA_PATH if SEED_DATA_PATH.exists() else SEED_DATA_PATH_FALLBACK
    log("INFO", f"读取数据: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    log("INFO", f"读取数据: {len(items)} 条")
    return items


def connect_db():
    """连接数据库"""
    log("INFO", "连接数据库...")
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def import_data(items, conn):
    """导入数据到数据库"""
    log("INFO", "开始向量化...")
    cur = conn.cursor()
    total = len(items)
    success_count = 0
    fail_count = 0
    start_time = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        try:
            # 构建文本
            texts = [build_context_text(item) for item in batch]

            # 调用 DashScope API 生成向量
            embeddings = get_embeddings_batch(texts)

            # 准备数据
            values = []
            for item, emb in zip(batch, embeddings):
                values.append((
                    item["物品 ID"],
                    item["物品名称"],
                    item["分类"],
                    item["属性详情"]["颜色"]["主五行"],
                    item["属性详情"]["颜色"].get("次五行"),
                    item["属性详情"]["颜色"]["能量强度"],
                    item.get("适用性别", "中性"),
                    json.dumps(item["属性详情"], ensure_ascii=False),
                    emb,
                    json.dumps(item.get("适用天气", []), ensure_ascii=False),
                    json.dumps(item.get("适用季节", []), ensure_ascii=False),
                    json.dumps(item.get("适用温度范围", {}), ensure_ascii=False),
                    json.dumps(item.get("功能性", {}), ensure_ascii=False),
                    item.get("厚度等级", "适中")
                ))

            # 批量插入
            sql = """
            INSERT INTO items (item_code, name, category, primary_element, secondary_element,
                               energy_intensity, gender, attributes_detail, embedding,
                               applicable_weather, applicable_seasons, temperature_range,
                               functionality, thickness_level)
            VALUES %s
            ON CONFLICT (item_code) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                attributes_detail = EXCLUDED.attributes_detail,
                gender = EXCLUDED.gender,
                applicable_weather = EXCLUDED.applicable_weather,
                applicable_seasons = EXCLUDED.applicable_seasons,
                temperature_range = EXCLUDED.temperature_range,
                functionality = EXCLUDED.functionality,
                thickness_level = EXCLUDED.thickness_level,
                updated_at = CURRENT_TIMESTAMP
            """
            execute_values(cur, sql, values)
            conn.commit()

            success_count += len(batch)
            log("INFO", f"已处理 {min(i + BATCH_SIZE, total)}/{total} 条")

            # 避免 API 限流
            time.sleep(0.5)

        except Exception as e:
            log("ERROR", f"处理批次 {i//BATCH_SIZE + 1} 失败: {e}")
            fail_count += len(batch)
            conn.rollback()
            time.sleep(2)  # 出错后等待更久

    cur.close()
    elapsed = time.time() - start_time
    log("SUCCESS", f"导入完成: {success_count} 条成功, {fail_count} 条失败")
    log("INFO", f"总耗时: {elapsed:.1f} 秒")
    return success_count, fail_count


def verify_import(conn):
    """验证导入结果"""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]
    log("INFO", f"数据库记录数: {count}")

    cur.execute("SELECT COUNT(*) FROM items WHERE embedding IS NULL")
    null_count = cur.fetchone()[0]
    log("INFO", f"空向量记录数: {null_count}")

    cur.execute("SELECT item_code, name, primary_element, vector_dims(embedding) as dims FROM items LIMIT 3")
    rows = cur.fetchall()
    for row in rows:
        log("INFO", f"  样本: {row[0]} | {row[1]} | 五行:{row[2]} | 维度:{row[3]}")

    cur.close()
    return count, null_count


def main():
    # 加载 .env
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    # 设置 DashScope API Key
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key or api_key == "sk-placeholder":
        log("ERROR", "DASHSCOPE_API_KEY 未设置！请在 .env 中配置")
        return 1
    dashscope.api_key = api_key

    log("INFO", "=" * 50)
    log("INFO", "WuXing AI Stylist - DashScope 种子数据导入")
    log("INFO", "=" * 50)

    try:
        items = load_seed_data()
        conn = connect_db()
        success, fail = import_data(items, conn)

        log("INFO", "-" * 50)
        log("INFO", "验证导入结果...")
        count, null_count = verify_import(conn)
        conn.close()

        log("INFO", "-" * 50)
        if fail == 0 and null_count == 0:
            log("SUCCESS", "导入完成，所有数据导入成功！")
            return 0
        else:
            log("WARNING", f"导入完成，但有 {fail} 条失败，{null_count} 条向量为空")
            return 1

    except Exception as e:
        log("ERROR", f"导入失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
