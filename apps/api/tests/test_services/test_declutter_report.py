"""
断舍离战报与停用口径测试（批次三 3.1）

覆盖：
- wardrobe_analytics_service.get_declutter_report 的三态分布、释放件数、
  最久闲置天数（含从未穿着用入库日兜底）、五行构成、少买折算、清单上限
- 处理动作依赖的「活跃衣橱」口径：每日成套 / 推荐检索 / 衣橱分析三处候选
  SQL 必须带 is_active = TRUE，停用后自动移出候选
"""

from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import MagicMock

from apps.api.core.database import DatabasePool
from apps.api.services import wardrobe_analytics_service as was
from apps.api.core.time_utils import CN_TZ, today_cn


def _acted(days_ago: int) -> datetime:
    """N 天前的处理时刻（带时区，模拟 TIMESTAMPTZ 回读）"""
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _row(item_id, action="donate", element="木", is_active=False,
         last_worn=None, owned=None, days_ago=10):
    return {
        "action": action,
        "acted_at": _acted(days_ago),
        "id": item_id,
        "name": f"衣物{item_id}",
        "category": "上装",
        "image_url": None,
        "primary_element": element,
        "is_active": is_active,
        "last_worn_date": last_worn,
        "owned_since": owned or datetime.now(CN_TZ) - timedelta(days=30),
    }


def _report(rows, year=None):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(was, "_fetch_declutter_rows", lambda user_id, target_year: list(rows))
        return was.get_declutter_report(1, year)


class TestDeclutterReport:
    def test_empty_year_has_no_placeholder(self):
        report = _report([])
        assert report["total_processed"] == 0
        assert report["released_count"] == 0
        assert report["max_idle_days"] is None
        assert report["element_breakdown"] == []
        assert report["processed_items"] == []
        assert "还没有处理过" in report["summary"]

    def test_default_year_is_current_cn_year(self):
        assert _report([])["year"] == today_cn().year

    def test_action_distribution_and_release_count(self):
        rows = [
            _row(1, "donate"),
            _row(2, "donate"),
            _row(3, "sell"),
            _row(4, "discard"),
        ]
        report = _report(rows)
        counts = {entry["action"]: entry["count"] for entry in report["by_action"]}
        assert counts == {"donate": 2, "sell": 1, "discard": 1}
        assert {entry["label"] for entry in report["by_action"]} == {"捐赠", "转让", "舍弃"}
        assert report["total_processed"] == 4
        assert report["released_count"] == 4
        # 无价格字段 → 只做件数折算
        assert report["avoided_purchase_count"] == 4

    def test_released_counts_only_still_inactive(self):
        """仍留在衣橱里的（异常回滚等场景）不计入释放件数"""
        report = _report([_row(1, "donate", is_active=True), _row(2, "sell")])
        assert report["total_processed"] == 2
        assert report["released_count"] == 1

    def test_max_idle_days_uses_last_worn_then_created_at(self):
        today = datetime.now(CN_TZ).date()
        rows = [
            # 穿过但很久没穿：以 last_worn_date 起算（days_ago=0 让处理时刻落在今天）
            _row(1, "donate", last_worn=today - timedelta(days=400), days_ago=0),
            # 从未穿过：以入库时间起算
            _row(
                2, "sell", last_worn=None,
                owned=datetime.now(CN_TZ) - timedelta(days=900), days_ago=0,
            ),
        ]
        report = _report(rows)
        assert report["max_idle_days"] == 900
        idle_by_item = {p["id"]: p["idle_days_at_action"] for p in report["processed_items"]}
        assert idle_by_item[1] == 400

    def test_element_breakdown_sorted_desc(self):
        rows = [
            _row(1, "donate", element="火"),
            _row(2, "sell", element="木"),
            _row(3, "sell", element="木"),
            _row(4, "discard", element=None),
        ]
        report = _report(rows)
        assert report["element_breakdown"] == [{"element": "木", "count": 2}, {"element": "火", "count": 1}]
        # 无五行标注的衣物不进入构成，但仍计入处理件数
        assert report["total_processed"] == 4

    def test_processed_items_capped_but_total_is_full(self):
        rows = [_row(i, "donate") for i in range(1, 42)]
        report = _report(rows)
        assert report["total_processed"] == 41
        assert len(report["processed_items"]) == was.DECLUTTER_DETAIL_LIMIT

    def test_summary_mentions_main_action_and_avoided_purchase(self):
        rows = [_row(1, "donate"), _row(2, "donate"), _row(3, "sell")]
        report = _report(rows, year=2026)
        assert "以捐赠为主" in report["summary"]
        assert "相当于少买 3 件" in report["summary"]

    def test_unknown_action_not_in_breakdown_but_counted(self):
        """CHECK 约束之外的脏数据不炸三态分布，也不丢总数"""
        report = _report([_row(1, "recycle")])
        assert report["total_processed"] == 1
        assert sum(entry["count"] for entry in report["by_action"]) == 0


def _capture_sql(func, *args):
    """把 DatabasePool.get_connection 换成假连接，返回 func 实际执行的最后一条 SQL"""
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(DatabasePool, "get_connection", staticmethod(lambda: cm))
        func(*args)
    return " ".join(cursor.execute.call_args.args[0].split()), cursor


class TestFetchDeclutterSQL:
    def test_query_filters_by_user_and_cn_year(self):
        """年份按北京时间切，UTC 容器里 12/31 与 1/1 边界不串年"""
        sql, cursor = _capture_sql(was._fetch_declutter_rows, 7, 2026)
        assert "EXTRACT(YEAR FROM a.created_at AT TIME ZONE 'Asia/Shanghai') = %s" in sql
        assert cursor.execute.call_args.args[1] == [7, 2026]

    def test_query_failure_returns_empty(self):
        """库异常时返回空列表，不向上抛（战报卡直接不展示）"""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                DatabasePool, "get_connection",
                staticmethod(lambda: MagicMock(__enter__=MagicMock(side_effect=RuntimeError("down")))),
            )
            assert was._fetch_declutter_rows(1, 2026) == []


class TestDeactivatedItemsLeaveCandidates:
    """停用（is_active=FALSE）后不应再出现在每日成套 / 检索 / 分析候选里"""

    def test_daily_outfit_wardrobe_query(self):
        from apps.api.services import daily_outfit_service as dos

        sql, _ = _capture_sql(dos._query_wardrobe, 1)
        assert "is_active = TRUE" in sql

    def test_analytics_wardrobe_query(self):
        sql, _ = _capture_sql(was._query_wardrobe, 1)
        assert "is_active = TRUE" in sql

    def test_recommendation_retrieval_query(self):
        from packages.ai_agents.wardrobe_client import wardrobe_client

        sql, _ = _capture_sql(wardrobe_client.get_wardrobe_items, 1)
        assert "is_active = TRUE" in sql
