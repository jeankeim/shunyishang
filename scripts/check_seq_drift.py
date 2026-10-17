"""一次性检查/修复本地库序列漂移（显式 id 导入后 nextval 落在已占用值上）。

用法:
    .venv/bin/python scripts/check_seq_drift.py          # 只报告
    .venv/bin/python scripts/check_seq_drift.py --fix    # setval 到 max(id)
"""
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# 找到「某表的 id 列默认值是 nextval(...)」的全部序列
cur.execute("""
    SELECT t.relname AS tbl, c.attname AS col,
           pg_get_serial_sequence(quote_ident(t.relname), c.attname) AS seqname
    FROM pg_attribute c
    JOIN pg_class t ON t.oid = c.attrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE t.relkind = 'r' AND n.nspname = 'public' AND c.attname = 'id'
      AND pg_get_serial_sequence(quote_ident(t.relname), c.attname) IS NOT NULL
    ORDER BY t.relname
""")
rows = cur.fetchall()

drift = []
for tbl, col, seqname in rows:
    cur.execute(f'SELECT COALESCE(MAX("{col}"), 0) FROM "{tbl}"')
    max_id = cur.fetchone()[0]
    cur.execute(f"SELECT last_value, is_called FROM {seqname}")
    last_value, is_called = cur.fetchone()
    next_val = last_value + (1 if is_called else 0)
    if next_val <= max_id:
        drift.append((tbl, seqname, next_val, max_id))

print(f"检查 {len(rows)} 张带序列 id 的表，发现漂移 {len(drift)} 张：")
for tbl, seqname, next_val, max_id in drift:
    print(f"  {tbl:<28} seq_next={next_val:<8} max_id={max_id}")
    if "--fix" in sys.argv:
        cur.execute(f"SELECT setval('{seqname}', {max_id}, true)")
        print(f"    -> setval({max_id}) = {cur.fetchone()[0]}")

if "--fix" in sys.argv:
    conn.commit()
    print("已提交序列修复")
else:
    conn.rollback()
conn.close()
