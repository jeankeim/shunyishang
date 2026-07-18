#!/usr/bin/env python3
"""快速导入饰品种子数据到 items 表（含 DashScope 向量）"""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load env
with open(ROOT / ".env") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

import psycopg2
from psycopg2.extras import execute_values
import dashscope
from dashscope import TextEmbedding

api_key = os.environ.get("DASHSCOPE_API_KEY", "")
if not api_key:
    print("ERROR: DASHSCOPE_API_KEY not set"); sys.exit(1)
dashscope.api_key = api_key

seed_path = ROOT / "data" / "seeds" / "seed_data_accessories.json"
with open(seed_path, "r", encoding="utf-8") as f:
    items = json.load(f)
print(f"Read {len(items)} accessories")

conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
success = 0
failed = 0

for idx, item in enumerate(items):
    try:
        name = item.get("物品名称", "")
        cat = item.get("分类", "饰品")
        ci = item.get("属性详情", {}).get("颜色", {})
        fi = item.get("属性详情", {}).get("面料", {})
        si = item.get("属性详情", {}).get("款式", {})
        tags = ", ".join(item.get("适用标签", []))
        details = ", ".join(si.get("细节", []))
        text = f"{name}，{cat}类。颜色{ci.get('名称','')}，五行属{ci.get('主五行','')}。材质{fi.get('名称','')}。{details}。{tags}。"

        resp = TextEmbedding.call(model="text-embedding-v3", input=[text])
        if resp.status_code != 200:
            print(f"  [{idx+1}] Embedding error: {resp.code}"); failed += 1; continue
        emb = resp.output["embeddings"][0]["embedding"]

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO items (item_code, name, category, primary_element, secondary_element,
                               energy_intensity, gender, attributes_detail, embedding,
                               applicable_weather, applicable_seasons, temperature_range,
                               functionality, thickness_level)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (item_code) DO UPDATE SET
                name=EXCLUDED.name, category=EXCLUDED.category,
                primary_element=EXCLUDED.primary_element, embedding=EXCLUDED.embedding,
                updated_at=CURRENT_TIMESTAMP
        """, (
            item["物品 ID"], name, cat,
            ci.get("主五行",""), ci.get("次五行"),
            ci.get("能量强度", 0.8),
            item.get("适用性别","中性"),
            json.dumps(item.get("属性详情",{}), ensure_ascii=False),
            emb,
            json.dumps(["晴","多云","阴"], ensure_ascii=False),
            json.dumps(["春","夏","秋","冬"], ensure_ascii=False),
            json.dumps({"最低":-10,"最高":45}, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),
            "轻薄",
        ))
        conn.commit()
        cur.close()
        success += 1
        print(f"  [{idx+1}/{len(items)}] OK: {item['物品 ID']} {name}")
        time.sleep(0.3)
    except Exception as e:
        print(f"  [{idx+1}] FAIL: {e}")
        failed += 1
        conn.rollback()
        time.sleep(1)

conn.close()
print(f"\nDone: {success} ok, {failed} fail")
