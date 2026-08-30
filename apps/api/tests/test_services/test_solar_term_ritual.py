"""
换季开柜仪式测试（批次三 3.3）

覆盖 apps/api/services/solar_term_service.py 的新增能力：
- get_term_pair：交节当天与跨年（冬至→次年小寒）的当前/下一节气定位
- _store_away_query / _take_out_query：该收该拿的 SQL 条件与参数
- _shape_ritual_item：last_worn_date 缺失时按 created_at 兜底
- get_wardrobe_ritual：清单装配、单段查询失败降级、空态、换季判定
- _ritual_yi_ji：八字取数失败时的降级文案与五行缺口截断

DB 全部打桩，不连真实库；节气定位另有 2026 立春的真实 cnlunar 用例。
"""
import json
from datetime import date, datetime

import pytest

from apps.api.services import solar_term_service as sts


SERVICE = sts.SolarTermService()


def _term(name, y, m, d):
    return {
        "name": name,
        "date": date(y, m, d),
        "element": sts.TERM_META[name]["element"],
        "description": sts.TERM_META[name]["description"],
        "outfit_hint": sts.TERM_META[name]["outfit_hint"],
    }


# ============================================================
# get_term_pair：节气交界定位
# ============================================================

class TestGetTermPair:
    def test_real_li_chun_boundary(self):
        """真实 cnlunar：2026 立春在 2/4，交节前是大寒，交节当天即算已交节"""
        current, upcoming = SERVICE.get_term_pair(date(2026, 2, 3))
        assert current["name"] == "大寒"
        assert upcoming["name"] == "立春"
        assert upcoming["date"] == date(2026, 2, 4)

        current, upcoming = SERVICE.get_term_pair(date(2026, 2, 4))
        assert current["name"] == "立春"
        assert upcoming["name"] == "雨水"

    def test_cross_year_winter_solstice(self, monkeypatch):
        """12/25 的下一节气是次年小寒（当年表里没有它）"""
        tables = {
            2025: [_term("冬至", 2025, 12, 21)],
            2026: [_term("冬至", 2026, 12, 21)],
            2027: [_term("小寒", 2027, 1, 5), _term("大寒", 2027, 1, 20)],
        }
        monkeypatch.setattr(sts.SolarTermService, "_year_terms", lambda self, year: tables.get(year, []))
        current, upcoming = SERVICE.get_term_pair(date(2026, 12, 25))
        assert current["name"] == "冬至" and current["date"] == date(2026, 12, 21)
        assert upcoming["name"] == "小寒"

    def test_missing_term_returns_none(self, monkeypatch):
        """新年份表早于所有条目时 current 为 None（不报错）"""
        monkeypatch.setattr(
            sts.SolarTermService, "_year_terms", lambda self, year: [_term("立春", 2099, 2, 4)] if year == 2099 else []
        )
        current, upcoming = SERVICE.get_term_pair(date(2098, 1, 10))
        assert current is None
        assert upcoming["name"] == "立春"

    def test_all_years_fail_returns_none_none(self, monkeypatch):
        def _boom(self, year):
            raise RuntimeError("cnlunar broken")

        monkeypatch.setattr(sts.SolarTermService, "_year_terms", _boom)
        assert SERVICE.get_term_pair(date(2026, 3, 1)) == (None, None)


# ============================================================
# 清单查询：SQL 条件与参数
# ============================================================

class TestRitualQueries:
    def test_store_away_conditions(self, monkeypatch):
        """该收：季节标签非空且不含下一季 + 厚度非空且不在下一季档位"""
        captured = {}

        def _fake(query, params):
            captured["sql"] = " ".join(query.split())
            captured["params"] = params
            return [{
                "id": 5, "name": "羽绒服", "category": "外套", "image_url": None,
                "primary_element": "水", "thickness_level": "厚重",
                "applicable_seasons": ["冬"], "wear_count": 2,
                "last_worn_date": date(2026, 2, 1), "created_at": None,
                "total_matched": 7,
            }]

        monkeypatch.setattr(sts, "_fetch_rows", _fake)
        ref = date(2026, 2, 1)
        items, total = sts._store_away_query(1, "春", ["适中", "轻薄"], ref)
        assert total == 7
        assert len(items) == 1
        assert "is_active = TRUE" in captured["sql"]
        assert "applicable_seasons, '[]'::jsonb) <> '[]'::jsonb" in captured["sql"]
        assert "NOT (COALESCE(applicable_seasons, '[]'::jsonb) @> %s::jsonb)" in captured["sql"]
        assert "thickness_level IS NOT NULL" in captured["sql"]
        assert "NOT (thickness_level = ANY(%s))" in captured["sql"]
        assert captured["params"] == [1, json.dumps(["春"], ensure_ascii=False), ["适中", "轻薄"], sts.RITUAL_LIST_LIMIT]

    def test_take_out_idle_fallback(self, monkeypatch):
        """该拿：@> 下一季 + COALESCE(last_worn_date, created_at) 超过闲置阈值，最久没穿排前"""
        captured = {}

        def _fake(query, params):
            captured["sql"] = " ".join(query.split())
            captured["params"] = params
            return []

        monkeypatch.setattr(sts, "_fetch_rows", _fake)
        ref = date(2026, 2, 1)
        items, total = sts._take_out_query(1, "春", ref)
        assert items == [] and total == 0
        assert "COALESCE(applicable_seasons, '[]'::jsonb) @> %s::jsonb" in captured["sql"]
        assert "COALESCE(last_worn_date, created_at)::date <= %s::date - %s" in captured["sql"]
        assert "ORDER BY COALESCE(last_worn_date, created_at)::date ASC" in captured["sql"]
        assert captured["params"] == [1, json.dumps(["春"], ensure_ascii=False), ref, sts.RITUAL_IDLE_DAYS, sts.RITUAL_LIST_LIMIT]


# ============================================================
# 清单条目塑形
# ============================================================

class TestShapeRitualItem:
    def test_missing_last_worn_falls_back_to_created_at(self):
        """没穿过的新物：idle_days 按入橱时间算，last_worn 保持为空供前端区分"""
        row = {
            "id": 8, "name": None, "category": "上装", "image_url": "/uploads/a.png",
            "primary_element": "木", "thickness_level": "适中",
            "applicable_seasons": '["春", "秋"]', "wear_count": None,
            "last_worn_date": None, "created_at": "2026-01-01T10:00:00+08:00",
        }
        item = sts._shape_ritual_item(row, date(2026, 2, 1))
        assert item["name"] == "未命名衣物"
        assert item["last_worn"] is None
        assert item["idle_days"] == 31
        assert item["wear_count"] == 0
        assert item["seasons"] == ["春", "秋"]

    def test_real_last_worn_preferred(self):
        row = {
            "id": 9, "name": "风衣", "category": "外套", "image_url": None,
            "primary_element": "金", "thickness_level": "适中",
            "applicable_seasons": ["春"], "wear_count": 4,
            "last_worn_date": date(2025, 11, 2), "created_at": datetime(2024, 1, 1),
        }
        item = sts._shape_ritual_item(row, date(2026, 2, 1))
        assert item["last_worn"] == "2025-11-02"
        assert item["idle_days"] == 91

    def test_broken_seasons_string_is_tolerated(self):
        row = {
            "id": 10, "name": "T恤", "category": "上装", "image_url": None,
            "primary_element": None, "thickness_level": None,
            "applicable_seasons": "not-json", "wear_count": 0,
            "last_worn_date": None, "created_at": None,
        }
        item = sts._shape_ritual_item(row, date(2026, 2, 1))
        assert item["seasons"] == []
        assert item["idle_days"] is None


# ============================================================
# get_wardrobe_ritual：整体装配
# ============================================================

@pytest.fixture
def ritual_env(monkeypatch):
    """打桩两份清单 + 宜忌，返回可配置的信封"""
    state = {
        "store": ([], 0),
        "take": ([], 0),
        "pair": (_term("大寒", 2026, 1, 20), _term("立春", 2026, 2, 4)),
    }

    def _store(user_id, next_season, expected_thickness, ref, limit=sts.RITUAL_LIST_LIMIT):
        state["captured_store"] = (next_season, expected_thickness)
        if isinstance(state["store"], Exception):
            raise state["store"]
        return state["store"]

    def _take(user_id, next_season, ref, idle_days=sts.RITUAL_IDLE_DAYS, limit=sts.RITUAL_LIST_LIMIT):
        state["captured_take"] = next_season
        if isinstance(state["take"], Exception):
            raise state["take"]
        return state["take"]

    monkeypatch.setattr(sts, "_store_away_query", _store)
    monkeypatch.setattr(sts, "_take_out_query", _take)
    monkeypatch.setattr(
        sts.SolarTermService, "get_term_pair",
        lambda self, today=None: state["pair"],
    )
    monkeypatch.setattr(
        SERVICE, "_ritual_yi_ji",
        lambda user_id, term: {"advice": "宜清淡配色", "gap_elements": []},
    )
    return state


class TestGetWardrobeRitual:
    def test_season_boundary_assembly(self, ritual_env):
        """大寒→立春：下一季春，厚度档位适中/轻薄，判定为换季"""
        shirt = {"id": 1, "name": "衬衫", "category": "上装", "image_url": None,
                 "primary_element": "木", "thickness_level": "适中", "seasons": ["春"],
                 "wear_count": 1, "last_worn": "2025-10-01", "idle_days": 126}
        coat = {"id": 2, "name": "羽绒服", "category": "外套", "image_url": None,
                "primary_element": "水", "thickness_level": "厚重", "seasons": ["冬"],
                "wear_count": 9, "last_worn": "2026-01-20", "idle_days": 15}
        ritual_env["store"] = ([coat], 12)
        ritual_env["take"] = ([shirt], 3)

        result = SERVICE.get_wardrobe_ritual(1, today=date(2026, 2, 1))

        assert result["next_season"] == "春"
        assert result["expected_thickness"] == ["适中", "轻薄"]
        assert result["is_season_boundary"] is True
        assert result["solar_term"]["name"] == "立春"
        assert result["solar_term"]["days_until"] == 3
        assert result["current_term"]["name"] == "大寒"
        assert result["store_away"]["total"] == 12
        assert result["take_out"]["items"] == [shirt]
        assert result["has_action"] is True
        assert ritual_env["captured_store"] == ("春", ["适中", "轻薄"])
        assert ritual_env["captured_take"] == "春"
        assert "90" in result["take_out"]["reason"]

    def test_same_season_not_boundary(self, ritual_env):
        """立春→雨水同属春季：不是换季，卡片文案口径为常规检查"""
        ritual_env["pair"] = (_term("立春", 2026, 2, 4), _term("雨水", 2026, 2, 18))
        result = SERVICE.get_wardrobe_ritual(1, today=date(2026, 2, 10))
        assert result["next_season"] == "春"
        assert result["is_season_boundary"] is False

    def test_empty_wardrobe(self, ritual_env):
        """空衣橱：两张清单都空，has_action False，结构仍完整"""
        result = SERVICE.get_wardrobe_ritual(1, today=date(2026, 2, 1))
        assert result["store_away"] == {"items": [], "total": 0, "reason": result["store_away"]["reason"]}
        assert result["take_out"]["items"] == []
        assert result["has_action"] is False

    def test_one_query_failure_keeps_the_other(self, ritual_env):
        """该收查询炸掉只影响该收清单，该拿照常返回"""
        ritual_env["store"] = RuntimeError("db down")
        ritual_env["take"] = ([{"id": 4, "name": "卫衣"}], 1)
        result = SERVICE.get_wardrobe_ritual(1, today=date(2026, 2, 1))
        assert result["store_away"]["items"] == []
        assert result["store_away"]["total"] == 0
        assert result["take_out"]["items"] == [{"id": 4, "name": "卫衣"}]
        assert result["has_action"] is True

    def test_explicit_term_overrides_positioning(self, ritual_env):
        """外部指定节气（如推送场景）时以它为准"""
        result = SERVICE.get_wardrobe_ritual(1, solar_term=_term("大雪", 2026, 12, 7), today=date(2026, 2, 1))
        assert result["solar_term"]["name"] == "大雪"
        assert result["next_season"] == "冬"
        assert result["expected_thickness"] == ["加厚", "厚重"]

    def test_month_fallback_when_term_unknown(self, ritual_env):
        """定位不到节气时用月份兜底季节，不至于给出空清单条件"""
        ritual_env["pair"] = (None, None)
        result = SERVICE.get_wardrobe_ritual(1, today=date(2026, 8, 15))
        assert result["solar_term"] is None
        assert result["current_term"] is None
        assert result["next_season"] == sts._MONTH_SEASON[8]
        assert result["is_season_boundary"] is False

    def test_unknown_season_skips_queries(self, ritual_env, monkeypatch):
        """季节完全判定不出来时不查库，返回空清单而不是错误清单"""
        monkeypatch.setattr(sts, "TERM_SEASON", {})
        monkeypatch.setattr(sts, "_MONTH_SEASON", {})
        called = {"n": 0}

        def _count(*args, **kwargs):
            called["n"] += 1
            return ([], 0)

        monkeypatch.setattr(sts, "_store_away_query", _count)
        monkeypatch.setattr(sts, "_take_out_query", _count)
        result = SERVICE.get_wardrobe_ritual(1, today=date(2026, 8, 15))
        assert called["n"] == 0
        assert result["next_season"] == ""
        assert result["expected_thickness"] == []
        assert result["has_action"] is False
        assert result["current_term"]["name"] == "大寒"


# ============================================================
# _shape_term
# ============================================================

class TestShapeTerm:
    def test_accepts_datetime_and_iso_string(self):
        t1 = SERVICE._shape_term({"name": "立秋", "date": datetime(2026, 8, 7, 10, 30)}, date(2026, 8, 1))
        assert t1["date"] == "2026-08-07" and t1["days_until"] == 6

        t2 = SERVICE._shape_term({"name": "立秋", "date": "2026-08-07"}, date(2026, 8, 1))
        assert t2 == t1

    def test_backfills_meta_and_tolerates_bad_date(self):
        shaped = SERVICE._shape_term({"name": "白露", "date": "去年吧"}, date(2026, 9, 1))
        assert shaped["element"] == "金"
        assert shaped["season"] == "秋"
        assert shaped["date"] is None and shaped["days_until"] is None
        assert shaped["outfit_hint"]

    def test_unknown_name_keeps_given_fields(self):
        shaped = SERVICE._shape_term({"name": "外星节", "element": "火"}, date(2026, 9, 1))
        assert shaped["element"] == "火"
        assert shaped["season"] == ""
        assert shaped["description"] == ""

    def test_empty_term_returns_none(self):
        assert SERVICE._shape_term({}, date(2026, 9, 1)) is None
        assert SERVICE._shape_term({"date": "2026-09-01"}, date(2026, 9, 1)) is None


# ============================================================
# _ritual_yi_ji
# ============================================================

class TestRitualYiJi:
    def test_gap_elements_truncated_to_two(self, monkeypatch):
        from apps.api.services import user_service
        from apps.api.services import wardrobe_analytics_service as was

        monkeypatch.setattr(user_service, "get_user_bazi", lambda uid: {
            "suggested_elements": ["木", "火"], "avoid_elements": ["金"],
        })
        monkeypatch.setattr(was, "get_element_balance", lambda uid: {
            "advice": [
                {"element": "木", "headline": "木气缺口最大"},
                {"element": "火", "headline": "火气略缺"},
                {"element": "土", "headline": "土气略缺"},
            ]
        })
        yi_ji = SERVICE._ritual_yi_ji(1, _term("立春", 2026, 2, 4))
        assert "立春" in yi_ji["advice"]
        assert [g["element"] for g in yi_ji["gap_elements"]] == ["木", "火"]

    def test_bazi_failure_degrades_to_local_text(self, monkeypatch):
        from apps.api.services import user_service
        from apps.api.services import wardrobe_analytics_service as was

        def _boom(uid):
            raise RuntimeError("no bazi")

        monkeypatch.setattr(user_service, "get_user_bazi", _boom)
        monkeypatch.setattr(was, "get_element_balance", lambda uid: (_ for _ in ()).throw(RuntimeError("db down")))
        yi_ji = SERVICE._ritual_yi_ji(1, _term("大暑", 2026, 7, 23))
        assert "薄透短袖" in yi_ji["advice"]      # 回落节气 outfit_hint
        assert yi_ji["gap_elements"] == []
