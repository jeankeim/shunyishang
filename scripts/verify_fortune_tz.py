"""ECS 生产环境运势日期修复验证脚本（在 shunyishang-api 容器内执行）"""
import json
import urllib.request

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.security import create_access_token

# 1. 找一个已有运势记录的真实用户（必然有八字数据）
with DatabasePool.get_connection() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT user_id, fortune_date FROM daily_fortune "
            "ORDER BY fortune_date DESC LIMIT 5"
        )
        rows = cur.fetchall()
print("[1] 最近运势记录:", [(r["user_id"], str(r["fortune_date"])) for r in rows])

user_id = rows[0]["user_id"]
token = create_access_token({"sub": str(user_id)})


def call(method, path):
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1" + path,
        method=method,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


# 2. GET 今日运势：应返回 2026-08-05（修复前 UTC 容器会返回 2026-08-04）
t1 = call("GET", "/fortune/today")
print(f"[2] GET /fortune/today → user={user_id}, fortune_date={t1['fortune_date']}, "
      f"score={t1['overall_score']}, created_at={t1['created_at']}")

# 3. POST 重新生成：应写入 2026-08-05 新记录
t2 = call("POST", "/fortune/generate")
print(f"[3] POST /fortune/generate → fortune_date={t2['fortune_date']}, "
      f"score={t2['overall_score']}")

# 4. 再次 GET：应与重新生成结果一致（缓存已失效）
t3 = call("GET", "/fortune/today")
print(f"[4] GET /fortune/today 再次请求 → fortune_date={t3['fortune_date']}, "
      f"score={t3['overall_score']}")

ok = (str(t1["fortune_date"]) == "2026-08-05"
      and str(t2["fortune_date"]) == "2026-08-05"
      and str(t3["fortune_date"]) == "2026-08-05")
print("[结果]", "✅ 全部返回 2026-08-05，修复生效" if ok else "❌ 日期仍异常")
