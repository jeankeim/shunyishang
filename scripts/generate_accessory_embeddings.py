#!/usr/bin/env python3
"""
为饰品（ITEM_151-175）生成 embedding 向量
使用 curl 调用 DashScope text-embedding-v3 API（绕过 Python SSL 问题）
"""

import json
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def load_env():
    with open(ROOT / ".env") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def curl_json(url, headers=None, data=None, method="POST"):
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


def get_embedding(text: str, api_key: str) -> list:
    """调用 DashScope text-embedding-v3 获取向量"""
    resp = curl_json(
        "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data={
            "model": "text-embedding-v3",
            "input": {"texts": [text]},
            "parameters": {"dimension": 1024, "text_type": "document"},
        },
    )
    output = resp.get("output", {})
    embeddings = output.get("embeddings", [])
    if embeddings:
        return embeddings[0].get("embedding", [])
    raise Exception(f"Embedding 失败: {json.dumps(resp, ensure_ascii=False)}")


def main():
    load_env()
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY 未设置")
        return 1

    import psycopg2
    from psycopg2.extras import RealDictCursor

    db_conn = psycopg2.connect(os.environ.get("DATABASE_URL"))

    # 查询所有 embedding 为 NULL 的饰品
    cur = db_conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT item_code, name, category, primary_element, attributes_detail
        FROM items
        WHERE item_code >= 'ITEM_151' AND item_code <= 'ITEM_175'
          AND embedding IS NULL
    """)
    items = [dict(row) for row in cur.fetchall()]
    cur.close()

    if not items:
        print("所有饰品已有 embedding，无需处理")
        db_conn.close()
        return 0

    print(f"待处理: {len(items)} 件饰品")

    success = 0
    failed = 0

    for i, item in enumerate(items):
        item_code = item["item_code"]
        name = item["name"]

        # 构建 embedding 文本（包含关键属性信息）
        detail = item.get("attributes_detail") or {}
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except Exception:
                detail = {}

        color_name = ""
        if isinstance(detail, dict):
            color_info = detail.get("颜色", {})
            if isinstance(color_info, dict):
                color_name = color_info.get("名称", "")

        fabric_name = ""
        if isinstance(detail, dict):
            fabric_info = detail.get("面料", {})
            if isinstance(fabric_info, dict):
                fabric_name = fabric_info.get("名称", "")

        text = f"{name} {item.get('category', '')} {color_name} {fabric_name} {item.get('primary_element', '')}"
        text = " ".join(filter(None, text.split()))

        try:
            embedding = get_embedding(text, api_key)
            # 更新 DB
            cur = db_conn.cursor()
            cur.execute(
                "UPDATE items SET embedding = %s::vector WHERE item_code = %s",
                (str(embedding), item_code),
            )
            db_conn.commit()
            cur.close()
            print(f"[{i+1}/{len(items)}] ✓ {item_code} {name}")
            success += 1
        except Exception as e:
            print(f"[{i+1}/{len(items)}] ✗ {item_code} {name}: {e}")
            failed += 1
            db_conn.rollback()

    db_conn.close()
    print(f"\n完成: {success} 成功, {failed} 失败")

    # 验证
    db_conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = db_conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM items
        WHERE item_code >= 'ITEM_151' AND item_code <= 'ITEM_175'
          AND embedding IS NOT NULL
    """)
    cnt = cur.fetchone()[0]
    print(f"饰品 embedding 统计: {cnt}/25 件已有向量")
    cur.close()
    db_conn.close()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
