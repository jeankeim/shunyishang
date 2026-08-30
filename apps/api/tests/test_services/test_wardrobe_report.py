"""
衣橱年度报告服务测试（批次三 3.2）

覆盖 apps/api/services/wardrobe_report_service.py：
- collect_stats：各段聚合的装配、本命色的日记优先/库存回落、单段查询失败不影响整体
- 文案：LLM 成功合并 + 埋点、LLM 失败降级、空衣橱不调 LLM
- 额度：acquire_quota 的 upsert SQL 与上限语义、get_report 的 JSONB 解析

所有取数都以 monkeypatch / mock cursor 驱动，不连真实库。
"""
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from unittest.mock import MagicMock, patch

import apps.api.services.wardrobe_report_service as wrs


# ============================================================
# 测试助手
# ============================================================

def _patch_queries(mp, **overrides):
    """把 collect_stats 用到的取数函数整体换成固定返回"""
    defaults = {
        "_count_query": lambda user_id, start, end: {
            "total_items": 24, "new_this_year": 6,
            "ever_worn_items": 18, "favorite_items": 3,
        },
        "_worn_span_query": lambda user_id, start, end: {
            "diary_count": 40, "worn_item_count": 15, "top_occasion": "通勤",
        },
        "_top_worn_query": lambda user_id, start, end: {
            "id": 9, "name": "白衬衫", "category": "上装", "image_url": None,
            "primary_element": "金", "wear_times": 12,
        },
        "_idle_item_query": lambda user_id: {
            "id": 3, "name": "礼服裙", "category": "裙装", "image_url": None,
            "primary_element": "火", "wear_count": 1,
            "last_worn_date": (date.today() - timedelta(days=300)).isoformat(),
            "created_at": None,
        },
        "_element_wear_query": lambda user_id, start, end: [
            {"element": "金", "times": 12}, {"element": "木", "times": 5},
        ],
        "_element_stock_query": lambda user_id: [],
        "_monthly_element_query": lambda user_id, start, end: [
            {"month": 3, "element": "木", "times": 4},
            {"month": 3, "element": "金", "times": 2},
            {"month": 7, "element": "火", "times": 6},
        ],
    }
    for name, impl in defaults.items():
        mp.setattr(wrs, name, overrides.get(name, impl))


def _boom(*_args, **_kwargs):
    raise RuntimeError("db down")


# ============================================================
# collect_stats
# ============================================================

class TestCollectStats:
    def test_装配全部事实(self, monkeypatch):
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            stats = wrs.collect_stats(1, 2026)

        assert stats["year"] == 2026
        assert stats["total_items"] == 24
        assert stats["new_this_year"] == 6
        assert stats["diary_count"] == 40
        assert stats["worn_this_year"] == 15
        assert stats["top_occasion"] == "通勤"
        assert stats["top_worn_item"]["name"] == "白衬衫"
        assert stats["top_worn_item"]["wear_times"] == 12
        assert stats["idle_item"]["idle_days"] == 300
        assert stats["element_source"] == "diary"
        assert stats["monthly_elements"][0]["dominant"] == "木"
        assert stats["monthly_elements"][1]["dominant"] == "火"
        assert stats["is_empty"] is False

    def test_本命色按穿着加权取Top1(self, monkeypatch):
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            stats = wrs.collect_stats(1, 2026)

        assert stats["lucky_element"] == "金"
        assert stats["lucky_element_times"] == 12
        # 权重列表按次数降序
        assert [w["times"] for w in stats["element_weights"]] == [12, 5]

    def test_无日记时回落衣橱累计次数(self, monkeypatch):
        with monkeypatch.context() as mp:
            _patch_queries(
                mp,
                _element_wear_query=lambda user_id, start, end: [],
                _element_stock_query=lambda user_id: [
                    {"element": "水", "times": 0}, {"element": "土", "times": 7},
                ],
            )
            stats = wrs.collect_stats(1, 2026)

        assert stats["element_source"] == "wardrobe"
        assert stats["lucky_element"] == "土"
        # times=0 的元素不进入构成
        assert stats["element_weights"] == [{"element": "土", "times": 7}]

    def test_缺last_worn时按created_at兜底(self, monkeypatch):
        created = datetime.now(timezone.utc) - timedelta(days=120)
        with monkeypatch.context() as mp:
            _patch_queries(
                mp,
                _idle_item_query=lambda user_id: {
                    "id": 5, "name": "牛仔裤", "category": "下装", "image_url": None,
                    "primary_element": "木", "wear_count": 0,
                    "last_worn_date": None, "created_at": created,
                },
            )
            stats = wrs.collect_stats(1, 2026)

        assert 118 <= stats["idle_item"]["idle_days"] <= 120
        assert stats["idle_item"]["last_worn"] == created.date().isoformat()

    def test_单段查询失败不影响其他指标(self, monkeypatch):
        with monkeypatch.context() as mp:
            _patch_queries(mp, _top_worn_query=_boom, _monthly_element_query=_boom)
            stats = wrs.collect_stats(1, 2026)

        assert stats["top_worn_item"] is None
        assert stats["monthly_elements"] == []
        # 其他段落仍然完整
        assert stats["total_items"] == 24
        assert stats["lucky_element"] == "金"

    def test_空衣橱标记(self, monkeypatch):
        with monkeypatch.context() as mp:
            _patch_queries(
                mp,
                _count_query=lambda user_id, start, end: {
                    "total_items": 0, "new_this_year": 0,
                    "ever_worn_items": 0, "favorite_items": 0,
                },
                _worn_span_query=lambda user_id, start, end: {
                    "diary_count": 0, "worn_item_count": 0, "top_occasion": None,
                },
                _top_worn_query=lambda user_id, start, end: None,
                _idle_item_query=lambda user_id: None,
                _element_wear_query=lambda user_id, start, end: [],
            )
            stats = wrs.collect_stats(1, 2026)

        assert stats["is_empty"] is True
        assert stats["top_worn_item"] is None
        assert stats["idle_item"] is None

    def test_断舍离摘要并入(self, monkeypatch):
        fake = {
            "total_processed": 4,
            "max_idle_days": 500,
            "summary": "2026 年处理了 4 件衣物",
        }
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            mp.setattr(
                "apps.api.services.wardrobe_analytics_service.get_declutter_report",
                lambda user_id, year: fake,
            )
            stats = wrs.collect_stats(1, 2026)

        assert stats["declutter"] == {
            "total_processed": 4, "max_idle_days": 500, "summary": "2026 年处理了 4 件衣物",
        }

    def test_年份区间为半开区间(self, monkeypatch):
        captured = {}

        def _capture(user_id, start, end):
            captured["start"] = start
            captured["end"] = end
            return {}

        with monkeypatch.context() as mp:
            _patch_queries(mp, _count_query=_capture)
            wrs.collect_stats(1, 2025)

        assert captured["start"] == date(2025, 1, 1)
        assert captured["end"] == date(2026, 1, 1)


# ============================================================
# 文案生成
# ============================================================

def _llm_response(payload: dict):
    """构造一个带 usage 的 chat.completions 响应替身"""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(payload, ensure_ascii=False)
    resp.model = "qwen-plus"
    resp.usage = MagicMock(prompt_tokens=800, completion_tokens=400)
    return resp


class TestNarrative:
    def _service(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        monkeypatch.setattr(svc, "client", MagicMock())
        return svc

    def test_LLM成功时合并并埋点(self, monkeypatch):
        svc = self._service(monkeypatch)
        log = MagicMock()
        monkeypatch.setattr(wrs, "log_llm_usage", log)
        monkeypatch.setattr(
            wrs, "_chat_with_retry",
            lambda client, model, prompt: _llm_response({"title": "衣橱的一年", "overall": "总体文案"}),
        )
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            stats = wrs.collect_stats(1, 2026)
            narrative = svc._build_narrative(1, stats)

        assert narrative["title"] == "衣橱的一年"
        assert narrative["overall"] == "总体文案"
        # LLM 只给了两个键，其余键由规则文案补齐，不出现空洞
        assert narrative["top_item"].startswith("「白衬衫」")
        log.assert_called_once()
        assert log.call_args.args[1] == "wardrobe_report"
        assert log.call_args.kwargs["usage"]["input_tokens"] == 800

    def test_LLM失败降级为规则文案(self, monkeypatch):
        svc = self._service(monkeypatch)
        log = MagicMock()
        monkeypatch.setattr(wrs, "log_llm_usage", log)

        def _fail(*_args):
            raise RuntimeError("timeout")

        monkeypatch.setattr(wrs, "_chat_with_retry", _fail)
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            stats = wrs.collect_stats(1, 2026)
            narrative = svc._build_narrative(1, stats)

        assert "24" in narrative["overall"] or "40" in narrative["overall"]
        assert narrative["idle_item"].startswith("「礼服裙」")
        # 降级路径不记 LLM 成本
        log.assert_not_called()

    def test_LLM返回不可解析时降级(self, monkeypatch):
        svc = self._service(monkeypatch)
        monkeypatch.setattr(wrs, "log_llm_usage", MagicMock())
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = "这不是 JSON"
        monkeypatch.setattr(wrs, "_chat_with_retry", lambda *_a: resp)
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            stats = wrs.collect_stats(1, 2026)
            narrative = svc._build_narrative(1, stats)

        assert narrative["title"] == "2026 年的穿搭节奏"

    def test_空衣橱不调用LLM(self, monkeypatch):
        svc = self._service(monkeypatch)
        called = MagicMock(side_effect=AssertionError("空衣橱不应调用 LLM"))
        monkeypatch.setattr(wrs, "_chat_with_retry", called)
        monkeypatch.setattr(wrs, "log_llm_usage", MagicMock())
        with monkeypatch.context() as mp:
            _patch_queries(
                mp,
                _count_query=lambda user_id, start, end: {"total_items": 0},
                _worn_span_query=lambda user_id, start, end: {},
                _top_worn_query=lambda user_id, start, end: None,
                _idle_item_query=lambda user_id: None,
                _element_wear_query=lambda user_id, start, end: [],
                _monthly_element_query=lambda user_id, start, end: [],
            )
            stats = wrs.collect_stats(1, 2026)
            narrative = svc._build_narrative(1, stats)

        called.assert_not_called()
        assert stats["is_empty"] is True
        assert "还没有留下穿搭记录" in narrative["overall"]

    def test_prompt只给事实不给推断(self, monkeypatch):
        svc = self._service(monkeypatch)
        with monkeypatch.context() as mp:
            _patch_queries(mp)
            stats = wrs.collect_stats(1, 2026)
            prompt = svc._build_prompt(stats)

        assert "白衬衫" in prompt
        assert "本命色" in prompt
        # 合规口径：不作吉凶断言、不出现价格
        assert "不作任何吉凶" in prompt
        assert "价格" in prompt


# ============================================================
# 额度与落库 SQL
# ============================================================

def _capture_sql(monkeypatch, func, *args, fetchone=None):
    """执行 func 并捕获实际 SQL / 参数"""
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr(
        wrs.DatabasePool, "get_connection", staticmethod(lambda: cm)
    )
    result = func(*args)
    sqls = [" ".join(c.args[0].split()) for c in cursor.execute.call_args_list]
    return result, sqls, cursor


class TestQuotaAndSave:
    def test_acquire_quota_是原子upsert(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, sqls, cursor = _capture_sql(
            monkeypatch, svc.acquire_quota, 7, 2026, fetchone=(11,)
        )
        assert result == 11
        sql = sqls[0]
        assert "INSERT INTO wardrobe_reports" in sql
        assert "ON CONFLICT (user_id, report_year) DO UPDATE" in sql
        # 额度判定并入同一条语句，避免检查与自增之间的竞态
        assert "WHERE wardrobe_reports.generate_count < %s" in sql
        assert "generate_count = wardrobe_reports.generate_count + 1" in sql
        assert cursor.execute.call_args.args[1][:2] == [7, 2026]
        assert cursor.execute.call_args.args[1][-1] == wrs.WARDROBE_REPORT_YEARLY_LIMIT

    def test_acquire_quota_用尽返回None(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, _sqls, _cursor = _capture_sql(monkeypatch, svc.acquire_quota, 7, 2026, fetchone=None)
        assert result is None

    def test_get_quota_无记录为零(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, sqls, _cursor = _capture_sql(monkeypatch, svc.get_quota, 7, 2026, fetchone=None)
        assert result == {"year": 2026, "used": 0, "limit": 3, "remaining": 3}
        assert "SELECT generate_count FROM wardrobe_reports" in sqls[0]

    def test_save_ready不动计数(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        content = {"year": 2026, "stats": {}, "narrative": {}}
        result, sqls, cursor = _capture_sql(
            monkeypatch, svc._save_ready, 7, 2026, "标题", content, "摘要", fetchone=(21,)
        )
        assert result == 21
        sql = sqls[0]
        assert "status = 'ready'" in sql
        assert "generate_count" not in sql
        assert json.loads(cursor.execute.call_args.args[1][1])["year"] == 2026

    def test_release_quota回退计数(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        _result, sqls, _cursor = _capture_sql(monkeypatch, svc.release_quota, 7, 2026)
        assert "GREATEST(generate_count - 1, 0)" in sqls[0]
        assert "status = 'failed'" in sqls[0]


class TestGetReport:
    def _row(self, **overrides):
        row = {
            "id": 5,
            "report_year": 2026,
            "title": "2026 年衣橱年度报告",
            "content": {"stats": {"total_items": 3}, "narrative": {"overall": "x"}},
            "summary": "x",
            "status": "ready",
            "generate_count": 2,
            "created_at": datetime(2026, 8, 1),
            "updated_at": datetime(2026, 8, 2),
        }
        row.update(overrides)
        return row

    def test_解析JSONB内容(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, _sqls, _cursor = _capture_sql(
            monkeypatch, svc.get_report, 7, 2026, fetchone=self._row()
        )
        assert result["status"] == "ready"
        assert result["generated"] is True
        assert result["content"]["stats"]["total_items"] == 3

    def test_内容为字符串时反序列化(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        raw = json.dumps({"narrative": {"overall": "文本"}}, ensure_ascii=False)
        result, _sqls, _cursor = _capture_sql(
            monkeypatch, svc.get_report, 7, 2026, fetchone=self._row(content=raw)
        )
        assert result["content"]["narrative"]["overall"] == "文本"

    def test_内容损坏时回落空字典(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, _sqls, _cursor = _capture_sql(
            monkeypatch, svc.get_report, 7, 2026, fetchone=self._row(content="not-json")
        )
        assert result["content"] == {}

    def test_无记录返回None(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, _sqls, _cursor = _capture_sql(monkeypatch, svc.get_report, 7, 2025, fetchone=None)
        assert result is None

    def test_pending状态不算已生成(self, monkeypatch):
        svc = wrs.WardrobeReportService()
        result, _sqls, _cursor = _capture_sql(
            monkeypatch, svc.get_report, 7, 2026,
            fetchone=self._row(status="pending", content={}),
        )
        assert result["generated"] is False

    def test_默认年份为当年(self, monkeypatch):
        from apps.api.core.time_utils import today_cn

        svc = wrs.WardrobeReportService()
        result, _sqls, cursor = _capture_sql(
            monkeypatch, svc.get_report, 7, None, fetchone=self._row()
        )
        assert result["year"] == 2026
        assert cursor.execute.call_args.args[1] == [7, today_cn().year]
