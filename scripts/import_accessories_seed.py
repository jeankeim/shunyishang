#!/usr/bin/env python3
"""
传统文化饰品种子数据导入脚本
将 seed_data_accessories.json 中的 25 件饰品/文玩导入 items 表
- 生成 DashScope text-embedding-v3 向量
- 写入 items 表（ON CONFLICT 更新）
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import execute_values
import dashscope
from dashscope import TextEmbedding

# ============================================================
# 配置
# ============================================================
SEED_PATH = ROOT / "data" / "seeds" / "seed_data_accessories.json"
BATCH_SIZE = 10


def load_env():
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
    text += f"材质为{fabric_name}，五行属{fabric_element}。"
    if shape:
        text += f"款式呈{shape}形。"
    if details:
        text += f"细节包括：{details}。"
    if tags:
        text += f"适合场景/功效：{tags}。"
    return text


def get_embeddings_batch(texts: list) -> list:
    """DashScope text-embedding-v3 批量向量"""
    response = TextEmbedding.call(
        model='text-embedding-v3',
        input=texts
    )
    if response.status_code == 200:
        return [item['embedding'] for item in response.output['embeddings']]
    else:
        raise Exception(f"DashScope embedding error: {response.code} - {response.message}")


def infer_seasons(item: dict) -> list:
    """根据材质/品类推断适用季节"""
    fabric_name = item.get("属性详情", {}).get("面料", {}).get("名称", "").lower()
    category = item.get("分类", "")
    # 饰品/文玩四季皆宜
    seasons = ["春", "夏", "秋", "冬"]
    return seasons


def infer_weather(item: dict) -> list:
    """根据材质推断适用天气"""
    return ["晴", "多云", "阴"]


def infer_temperature(item: dict) -> dict:
    """饰品无温度限制"""
    return {"最低": -10, "最高": 45}


def infer_functionality(item: dict) -> dict:
    """从标签推断功能性"""
    tags = item.get("适用标签", [])
    func = {}
    tag_map = {
        "辟邪": "辟邪", "护身": "护身", "安神": "安神",
        "招财": "招财", "纳福": "纳福", "旺运": "旺运",
        "桃花": "旺桃花", "人缘": "增人缘", "智慧": "增智慧",
        "养颜": "养颜", "美容": "美容", "禅修": "禅修",
        "静心": "静心", "净化": "净化磁场",
    }
    for tag in tags:
        if tag in tag_map:
            func[tag_map[tag]] = True
    return func


def main():
    load_env()

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key or api_key == "sk-placeholder":
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1
    dashscope.api_key = api_key

    # 读取种子数据
    if not SEED_PATH.exists():
        print(f"ERROR: 种子文件不存在: {SEED_PATH}")
        return 1

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        all_items = json.load(f)

    print(f"读取饰品种子数据: {len(all_items)} 件")

    conn = get_db_conn()
    cur = conn.cursor()

    success = 0
    failed = 0

    for i in range(0, len(all_items), BATCH_SIZE):
        batch = all_items[i:i + BATCH_SIZE]
        try:
            # 生成向量
            texts = [build_context_text(item) for item in batch]
            embeddings = get_embeddings_batch(texts)

            values = []
            for item, emb in zip(batch, embeddings):
                color_info = item.get("属性详情", {}).get("颜色", {})
                values.append((
                    item["物品 ID"],
                    item["物品名称"],
                    item.get("分类", "饰品"),
                    color_info.get("主五行", ""),
                    color_info.get("次五行"),
                    color_info.get("能量强度", 0.8),
                    item.get("适用性别", "中性"),
                    json.dumps(item.get("属性详情", {}), ensure_ascii=False),
                    emb,
                    json.dumps(infer_weather(item), ensure_ascii=False),
                    json.dumps(infer_seasons(item), ensure_ascii=False),
                    json.dumps(infer_temperature(item), ensure_ascii=False),
                    json.dumps(infer_functionality(item), ensure_ascii=False),
                    "轻薄",  # 饰品厚度
                ))

            sql = """
            INSERT INTO items (item_code, name, category, primary_element, secondary_element,
                               energy_intensity, gender, attributes_detail, embedding,
                               applicable_weather, applicable_seasons, temperature_range,
                               functionality, thickness_level)
            VALUES %s
            ON CONFLICT (item_code) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                primary_element = EXCLUDED.primary_element,
                secondary_element = EXCLUDED.secondary_element,
                energy_intensity = EXCLUDED.energy_intensity,
                gender = EXCLUDED.gender,
                attributes_detail = EXCLUDED.attributes_detail,
                embedding = EXCLUDED.embedding,
                applicable_weather = EXCLUDED.applicable_weather,
                applicable_seasons = EXCLUDED.applicable_seasons,
                temperature_range = EXCLUDED.temperature_range,
                functionality = EXCLUDED.functionality,
                thickness_level = EXCLUDED.thickness_level,
                updated_at = CURRENT_TIMESTAMP
            """
            execute_values(cur, sql, values)
            conn.commit()
            success += len(batch)
            print(f"  已导入 {min(i + BATCH_SIZE, len(all_items))}/{len(all_items)}")
            time.sleep(0.5)

        except Exception as e:
            print(f"  批次 {i // BATCH_SIZE + 1} 失败: {e}")
            failed += len(batch)
            conn.rollback()
            time.sleep(2)

    cur.close()
    conn.close()

    print(f"\n{'=' * 50}")
    print(f"导入完成: {success} 成功, {failed} 失败")
    print(f"{'=' * 50}")

    # 验证
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items WHERE item_code LIKE 'ITEM_1%'")
    acc_count = cur.fetchone()[0]
    cur.execute("SELECT item_code, name, category, primary_element FROM items WHERE item_code LIKE 'ITEM_1%' ORDER BY item_code LIMIT 5")
    rows = cur.fetchall()
    for row in rows:
        print(f"  {row[0]} | {row[1]} | {row[2]} | 五行:{row[3]}")
    cur.close()
    conn.close()

    print(f"\n数据库中饰品/文玩类物品: {acc_count} 件")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
