#!/usr/bin/env python3
"""
导入扩充的种子数据到数据库（使用 DashScope API 生成 embedding）
仅导入 ITEM_101 ~ ITEM_150 的新增物品
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import execute_values
import dashscope
from dashscope import TextEmbedding


SEED_PATH = ROOT / "data" / "seeds" / "seed_data_100_enhanced.json"
NEW_ITEM_START = 101
NEW_ITEM_END = 150


def load_env():
    """加载 .env 文件"""
    env_path = ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def build_context_text(item: dict) -> str:
    """构建用于向量化的文本描述（与 import_seed.py 保持一致）"""
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


def encode_text(text: str) -> list:
    """使用 DashScope API 生成 embedding"""
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    response = TextEmbedding.call(
        model='text-embedding-v3',
        input=text,
        api_key=api_key,
    )
    
    if response.status_code == 200:
        return response.output['embeddings'][0]['embedding']
    else:
        raise Exception(f"DashScope API error: {response.code} - {response.message}")


def main():
    load_env()
    
    # 读取种子数据
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        all_items = json.load(f)
    
    # 筛选新增物品
    new_items = [
        item for item in all_items
        if NEW_ITEM_START <= int(item["物品 ID"].split("_")[1]) <= NEW_ITEM_END
    ]
    
    print(f"新增物品: {len(new_items)} 条 (ITEM_{NEW_ITEM_START:03d} ~ ITEM_{NEW_ITEM_END:03d})")
    
    # 连接数据库
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if db_url:
        conn = psycopg2.connect(db_url)
    else:
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ.get("POSTGRES_DB", "wuxing_db"),
            user=os.environ.get("POSTGRES_USER", "wuxing_user"),
            password=os.environ.get("POSTGRES_PASSWORD", "wuxing_password"),
        )
    cur = conn.cursor()
    
    # 检查已存在的物品
    cur.execute("SELECT item_code FROM items")
    existing = set(r[0] for r in cur.fetchall())
    
    success = 0
    skipped = 0
    failed = 0
    
    for item in new_items:
        item_id = item["物品 ID"]
        
        if item_id in existing:
            print(f"  跳过（已存在）: {item_id}")
            skipped += 1
            continue
        
        try:
            # 构建文本描述
            text = build_context_text(item)
            print(f"  生成embedding: {item_id} - {item['物品名称'][:15]}...")
            
            # 生成 embedding
            embedding = encode_text(text)
            
            # 准备数据
            values = [(
                item_id,
                item["物品名称"],
                item["分类"],
                item["属性详情"]["颜色"]["主五行"],
                item["属性详情"]["颜色"].get("次五行"),
                item["属性详情"]["颜色"]["能量强度"],
                item.get("适用性别", "中性"),
                json.dumps(item["属性详情"], ensure_ascii=False),
                embedding,
                json.dumps(item.get("适用天气", []), ensure_ascii=False),
                json.dumps(item.get("适用季节", []), ensure_ascii=False),
                json.dumps(item.get("适用温度范围", {}), ensure_ascii=False),
                json.dumps(item.get("功能性", {}), ensure_ascii=False),
                item.get("厚度等级", "适中"),
            )]
            
            # 插入
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
            success += 1
            
        except Exception as e:
            print(f"  失败: {item_id} - {e}")
            failed += 1
            conn.rollback()
    
    # 验证
    cur.execute("SELECT COUNT(*) FROM items")
    total = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    print(f"\n=== 导入完成 ===")
    print(f"成功: {success}")
    print(f"跳过: {skipped}")
    print(f"失败: {failed}")
    print(f"数据库总计: {total} 件物品")


if __name__ == "__main__":
    main()
