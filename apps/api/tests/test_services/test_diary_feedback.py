"""
日记评分 → 偏好回流 的取数回归测试

为什么必须打真库：本模块的 SQL 此前只被 MagicMock cursor 覆盖过，而 mock 会接受任意
SQL 字符串 —— 于是 `_get_diary_items` 里那句 `doi.wardrobe_item_id = i.id`（items 表
根本没有 id 列，衣橱单品在 user_wardrobe）的 UndefinedColumn 永远不会在测试里暴露，
线上却因此静默失效：PostgreSQL 在解析期就报错，与 diary_id 取值、与有无关联行都无关。

fixture 全程在一个未提交事务里造数、结束即 rollback，不留测试数据；被测函数被 patch 成
复用这条连接，否则它会从池里另取一条连接、看不到未提交的行。
"""

from typing import Any, Dict, List

import pytest

pytest.importorskip("psycopg2")

import psycopg2  # noqa: E402

from apps.api.core.config import settings  # noqa: E402
from apps.api.services import diary_feedback_service as dfs_mod  # noqa: E402
from apps.api.services.diary_feedback_service import DiaryFeedbackService  # noqa: E402

DIARY_DATE = "2099-01-01"  # 避开 UNIQUE(user_id, diary_date) 与真实数据撞车


def _db_reachable() -> bool:
    try:
        c = psycopg2.connect(settings.database_url, connect_timeout=3)
        c.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_reachable(),
    reason="需要可连接的 PostgreSQL（本地 `docker compose up -d db`）",
)


class _ConnCtx:
    """把测试自己的连接伪装成 DatabasePool.get_connection() 的返回值"""

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *exc):
        return False


@pytest.fixture
def conn():
    c = psycopg2.connect(settings.database_url, connect_timeout=5)
    yield c
    c.rollback()  # 兜底：无论断言在哪一步失败，测试数据都不外流
    c.close()


@pytest.fixture
def seeded(conn, monkeypatch) -> Dict[str, Any]:
    """造 1 个临时用户 + 1 件衣橱单品 + 1 条公共种子单品的日记关联"""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (user_code, nickname) VALUES (%s, %s) RETURNING id",
        ("E2E-FBK-USER", "回流测试用户"),
    )
    user_id = cur.fetchone()[0]

    # user_wardrobe.item_code 有外键指向 items.item_code，必须用真存在的种子码。
    # 故意挑一个品类 != 上装的种子码：若查询错从 items 取衣橱行的属性，品类就会对不上。
    cur.execute(
        """SELECT item_code, name, category, color FROM items
           WHERE category IS NOT NULL AND color IS NOT NULL ORDER BY item_code"""
    )
    seeds = cur.fetchall()
    if len(seeds) < 2:
        pytest.skip("库内带 category/color 的 items 种子行不足，无法构造两个来源")
    fk_row = next((r for r in seeds if r[2] != "上装"), seeds[0])
    seed = next((r for r in seeds if r is not fk_row), seeds[-1])

    cur.execute(
        """
        INSERT INTO user_wardrobe
            (user_id, item_code, name, category, color, primary_element, style, material, thickness_level)
        VALUES (%s, %s, '测试红色上装', '上装', '红色', '火', '休闲', '棉', '厚')
        RETURNING id
        """,
        (user_id, fk_row[0]),
    )
    wardrobe_id = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO outfit_diaries (user_id, diary_date, rating) VALUES (%s, %s, 5) RETURNING id",
        (user_id, DIARY_DATE),
    )
    diary_id = cur.fetchone()[0]

    # category 刻意写 NULL：真实前端提交载荷只带 item_source + wardrobe_item_id，
    # 衣橱关联行的 doi.category 在生产上恒为 NULL（本地端到端实测确认）。
    cur.execute(
        "INSERT INTO diary_outfit_items (diary_id, item_source, wardrobe_item_id, category) "
        "VALUES (%s, 'wardrobe', %s, NULL)",
        (diary_id, wardrobe_id),
    )
    cur.execute(
        "INSERT INTO diary_outfit_items (diary_id, item_source, seed_item_code, category) "
        "VALUES (%s, 'public', %s, NULL)",
        (diary_id, seed[0]),
    )

    monkeypatch.setattr(dfs_mod.DatabasePool, "get_connection", lambda: _ConnCtx(conn))

    return {
        "user_id": user_id,
        "diary_id": diary_id,
        "wardrobe": {"name": "测试红色上装", "category": "上装", "color": "红色",
                     "element": "火", "style": "休闲", "material": "棉", "thickness": "厚"},
        "seed": {"item_code": seed[0], "name": seed[1], "category": seed[2], "color": seed[3]},
        "fk_category": fk_row[2],
    }


DIMS = ("color", "primary_element", "category", "style", "material", "thickness_level")


def _filled(item: Dict[str, Any]) -> int:
    return sum(1 for k in DIMS if item.get(k))


@requires_db
def test_get_diary_items_resolves_both_item_sources(seeded):
    """核心回归：衣橱走 user_wardrobe、种子走 items，两分支都要取到属性

    旧 SQL 在这里会直接抛 UndefinedColumn: column i.id does not exist。
    """
    items = DiaryFeedbackService()._get_diary_items(seeded["diary_id"])
    assert len(items) == 2, f"应取回 2 行衣物属性，实际 {len(items)}：{items}"
    for it in items:
        assert _filled(it) >= 4, f"某行只解析出 {_filled(it)} 个维度，属性没取全：{it}"
    # 守卫 fixture 本身的意义：种子码品类与衣橱行不同，后面的用例才能抓出误 JOIN
    assert seeded["fk_category"] != "上装", "种子行品类与衣橱行重合，测不出误 JOIN"


@requires_db
def test_wardrobe_attributes_come_from_user_wardrobe(seeded):
    """衣橱单品的 6 个学习维度必须全部取到，且 category 回落到 user_wardrobe.category

    这一条专门盯住「只把 JOIN 修对、但 category 仍取恒为 NULL 的 doi.category」的半吊子修法。
    """
    cur = seeded["wardrobe"]
    conn_items = DiaryFeedbackService()._get_diary_items(seeded["diary_id"])
    hit = [it for it in conn_items if it.get("category") == cur["category"]]
    assert hit, f"没有衣橱行解析出 category={cur['category']}：{conn_items}"
    got = hit[0]
    assert got["color"] == cur["color"]
    assert got["primary_element"] == cur["element"]
    assert got["style"] == cur["style"]
    assert got["material"] == cur["material"]
    assert got["thickness_level"] == cur["thickness"]


@requires_db
def test_public_seed_item_resolves_via_items_table(seeded):
    """公共种子单品经 items.item_code 取属性（该分支旧代码写得对，但被同一句 SQL 一起拖死）"""
    s = seeded["seed"]
    items = DiaryFeedbackService()._get_diary_items(seeded["diary_id"])
    hit = [it for it in items if it.get("category") == s["category"] and it.get("color") == s["color"]]
    assert hit, f"种子单品 {s['item_code']} 未解析出 category/color：{items}"


@requires_db
def test_feedback_reaches_preference_update_for_high_rating(seeded, monkeypatch):
    """打通模块本意：rating>=4 的日记，其每件关联衣物的属性都要送到 update_preference"""
    calls: List[tuple] = []
    monkeypatch.setattr(
        dfs_mod.preference_service, "update_preference",
        lambda uid, attrs, action: calls.append((uid, attrs, action)),
    )

    DiaryFeedbackService().process_diary_feedback(seeded["user_id"], seeded["diary_id"], 5)

    assert len(calls) == 2, f"应对 2 件衣物写偏好，实际 {len(calls)} 次：{calls}"
    assert {c[2] for c in calls} == {"like"}
    learned_categories = {c[1].get("category") for c in calls}
    assert seeded["wardrobe"]["category"] in learned_categories, (
        f"衣橱品类没进偏好信号：{learned_categories}"
    )


@pytest.mark.parametrize("rating", [None, 3])
def test_neutral_or_missing_rating_writes_nothing(rating, monkeypatch):
    """评分为空或中性时提前返回，不该碰数据库（无需真库）"""
    called = []
    monkeypatch.setattr(
        DiaryFeedbackService, "_get_diary_items",
        lambda self, did: called.append(did) or [],
    )
    DiaryFeedbackService().process_diary_feedback(1, 1, rating)
    assert called == [], "rating 为空/中性时不应查询关联衣物"
