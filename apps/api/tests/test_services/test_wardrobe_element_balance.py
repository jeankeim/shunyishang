"""
五行衣橱平衡仪表盘测试（批次一 1.2）

覆盖 wardrobe_analytics_service.get_element_balance 的占比权重、目标参考口径、
忌神上限、空衣橱空态与补运建议排序。DB / 天气 / 公共库查询均打桩。
"""

from unittest.mock import patch

import pytest

from apps.api.services import wardrobe_analytics_service as was
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

# autouse fixture 会打桩 _query_suggestion_items，取真实实现供 SQL 对齐用例使用
_REAL_QUERY_SUGGESTION = was._query_suggestion_items


def _item(item_id, category, primary, secondary=None, item_code=None):
    return {
        "id": item_id,
        "item_code": item_code,
        "name": f"衣物{item_id}",
        "category": category,
        "primary_element": primary,
        "secondary_element": secondary,
        "image_url": None,
        "wear_count": 0,
    }


@pytest.fixture(autouse=True)
def _no_weather(monkeypatch):
    """天气与公共库单品打桩，避免测试触网"""
    monkeypatch.setattr(was, "_current_temperature", lambda city: None)
    monkeypatch.setattr(
        was, "_query_suggestion_items",
        lambda elem, season, temperature, wardrobe, gender=None, category=None: [
            {"item_code": f"SUG_{elem}", "name": f"建议{elem}", "category": category or "上装",
             "primary_element": elem, "color": None, "image_url": None}
        ],
    )


def _balance(wardrobe, bazi):
    with patch.object(was, "_query_wardrobe", return_value=wardrobe), \
            patch.object(was, "_get_bazi_safe", return_value=bazi):
        return was.get_element_balance(1)


def _by_elem(result):
    return {e["element"]: e for e in result["elements"]}


def _near_target_wardrobe():
    """20 件：水40% 木25% 金10% 火10% 土15%（相对 40/25/11.7 参考口径几乎无缺口）"""
    spec = [("上装", "水", 8), ("下装", "木", 5), ("外套", "金", 2), ("鞋履", "火", 2), ("配饰", "土", 3)]
    items = []
    idx = 1
    for category, elem, qty in spec:
        for _ in range(qty):
            items.append(_item(idx, category, elem))
            idx += 1
    return items


class TestActualRatio:
    def test_secondary_element_weight(self):
        """主五行计 1.0、次五行计 0.5"""
        wardrobe = [
            _item(1, "上装", "火", secondary="木"),
            _item(2, "下装", "火"),
        ]
        entry = _by_elem(_balance(wardrobe, {}))
        # 权重合计 2.5：火 1.0+1.0 → 80%，木 0.5 → 20%
        assert entry["火"]["actual_pct"] == pytest.approx(80.0)
        assert entry["木"]["actual_pct"] == pytest.approx(20.0)
        # 件数：火 2 件、木 1 件
        assert entry["火"]["count"] == 2
        assert entry["木"]["count"] == 1

    def test_all_elements_present(self):
        result = _balance([_item(1, "上装", "金")], {})
        assert [e["element"] for e in result["elements"]] == ["金", "木", "水", "火", "土"]
        assert sum(e["actual_pct"] for e in result["elements"]) == pytest.approx(100.0, abs=0.2)


class TestTargetRatio:
    def test_lucky_targets(self):
        """第一喜用 40%、第二 25%、其余三行均分 35%"""
        result = _balance([_item(1, "上装", "金")], {"suggested_elements": ["水", "木"], "avoid_elements": []})
        entry = _by_elem(result)
        assert entry["水"]["target_pct"] == 40.0
        assert entry["木"]["target_pct"] == 25.0
        assert entry["金"]["target_pct"] == pytest.approx(11.7)
        assert entry["火"]["target_pct"] == pytest.approx(11.7)

    def test_no_bazi_falls_back_to_even_split(self):
        """无八字（未录入）时目标五行均分 20%"""
        entry = _by_elem(_balance([_item(1, "上装", "金")], {"suggested_elements": [], "avoid_elements": []}))
        assert all(e["target_pct"] == 20.0 for e in entry.values())

    def test_avoid_element_capped(self):
        """忌神行目标压到 10% 上限，且占比超上限即判 surplus"""
        wardrobe = [_item(i, "上装", "火") for i in range(1, 6)] + [_item(9, "下装", "水")]
        # 火落在「其余三行均分 35%」档（11.7%），因是忌神被压到 10%
        result = _balance(wardrobe, {"suggested_elements": ["水", "木"], "avoid_elements": ["火"]})
        entry = _by_elem(result)
        assert entry["火"]["target_pct"] == 10.0
        assert entry["火"]["status"] == "surplus"
        assert entry["水"]["status"] == "deficient"

    def test_more_than_two_lucky_elements(self):
        """喜用神多于两个：前两档不变，第三及以后按「其余行」档均分；忌神仍压 10%"""
        entry = _by_elem(_balance(
            [_item(1, "上装", "水")],
            {"suggested_elements": ["水", "木", "金", "火"], "avoid_elements": ["土"]},
        ))
        assert entry["水"]["target_pct"] == 40.0
        assert entry["木"]["target_pct"] == 25.0
        assert entry["金"]["target_pct"] == pytest.approx(11.7)
        assert entry["火"]["target_pct"] == pytest.approx(11.7)
        assert entry["土"]["target_pct"] == 10.0

    def test_unknown_element_ignored(self):
        """脏数据（非五行值）不参与目标计算"""
        entry = _by_elem(_balance([_item(1, "上装", "金")], {"suggested_elements": ["水", "月"], "avoid_elements": ["火"]}))
        assert entry["水"]["target_pct"] == 40.0
        assert "月" not in entry


class TestEmptyWardrobe:
    def test_empty_state(self):
        result = _balance([], {"suggested_elements": ["水"]})
        assert result["is_empty"] is True
        assert result["total_items"] == 0
        assert result["advice"] == []
        assert all(e["actual_pct"] == 0.0 for e in result["elements"])


class TestAdvice:
    def test_gap_order_and_cap(self):
        """建议按缺口从大到小取最多 2 行"""
        wardrobe = [_item(1, "上装", "火"), _item(2, "下装", "火")]
        result = _balance(wardrobe, {"suggested_elements": ["水", "木", "金"], "avoid_elements": []})
        advice = result["advice"]
        assert 1 <= len(advice) <= 2
        gaps = [a["gap_pct"] for a in advice]
        assert gaps == sorted(gaps, reverse=True)
        assert all(a["gap_pct"] >= was.GAP_MIN_PCT for a in advice)
        assert advice[0]["element"] == "水"

    def test_balanced_wardrobe_has_no_advice(self):
        """缺口都小于阈值时不出建议"""
        result = _balance(_near_target_wardrobe(), {"suggested_elements": ["水", "木"], "avoid_elements": []})
        assert result["advice"] == []

    def test_advice_shape(self):
        """建议含 headline / want（品类、颜色、季节）与公共库单品"""
        wardrobe = [_item(1, "上装", "火"), _item(2, "下装", "火")]
        result = _balance(wardrobe, {"suggested_elements": ["水"], "avoid_elements": []})
        a = result["advice"][0]
        assert set(a["want"]) == {"category", "colors", "seasons"}
        assert a["want"]["category"] in ("上装", "下装", "外套", "鞋履", "配饰")
        assert a["want"]["colors"] == ELEMENT_COLOR_MAP["水"][:3]
        assert a["want"]["seasons"] == [result["season"]]
        assert a["headline"].startswith("水属性单品偏少")
        assert a["items"][0]["item_code"] == "SUG_水"

    def test_pick_want_category(self):
        """建议品类取该行在衣橱里最少见的核心品类"""
        wardrobe = [_item(1, "上装", "水"), _item(2, "上装", "水"), _item(3, "鞋履", "水")]
        assert was._pick_want_category(wardrobe, "水") == "下装"
        # 该五行完全缺席时，仍取第一个最缺的品类（按核心品类顺序）
        assert was._pick_want_category([], "水") == "上装"


class TestStatusBoundary:
    def test_gap_within_threshold_is_balanced(self):
        """占比与目标差小于 GAP_MIN_PCT 判 balanced，超出判 surplus"""
        entry = _by_elem(_balance(_near_target_wardrobe(), {"suggested_elements": ["水", "木"]}))
        assert entry["水"]["actual_pct"] == 40.0
        assert entry["水"]["gap_pct"] == 0.0
        assert entry["水"]["status"] == "balanced"
        assert entry["木"]["status"] == "balanced"
        assert entry["土"]["status"] == "surplus"

    def test_empty_actual_ratio_is_deficient_when_lucky(self):
        """喜用行完全缺席 → 最大缺口"""
        entry = _by_elem(_balance([_item(1, "上装", "火")], {"suggested_elements": ["水"]}))
        assert entry["水"]["status"] == "deficient"
        assert entry["水"]["gap_pct"] == pytest.approx(40.0)


class TestSuggestionQuery:
    """公共库单品查询：SQL 占位符与参数必须逐项对齐（曾有错位导致建议恒空）"""

    def _capture(self, monkeypatch, **kwargs):
        calls = []

        def fake_fetch(sql, params):
            calls.append((sql, list(params)))
            return []

        monkeypatch.setattr(was, "_fetch_items", fake_fetch)
        _REAL_QUERY_SUGGESTION(**kwargs)
        return calls

    def test_placeholder_param_alignment(self, monkeypatch):
        wardrobe = [_item(1, "上装", "火", item_code="ITEM_001")]
        for gender in (None, "女"):
            for temperature in (None, 30, 5):
                calls = self._capture(
                    monkeypatch,
                    elem="木", season="夏", temperature=temperature,
                    wardrobe=wardrobe, gender=gender, category="鞋履",
                )
                assert calls, "查询未执行"
                for sql, params in calls:
                    assert sql.count("%s") == len(params), f"占位符 {sql.count('%s')} != 参数 {len(params)}"
                    assert params[0] == "木" and params[1] == "木"
                    owned_idx = 2 if not gender else 3
                    assert params[owned_idx] == ["ITEM_001"]

    def test_gap_category_forwarded_to_advice(self):
        """建议单品的取数品类与 want.category 一致"""
        wardrobe = [_item(1, "上装", "火"), _item(2, "上装", "火")]
        result = _balance(wardrobe, {"suggested_elements": ["水"], "avoid_elements": []})
        a = result["advice"][0]
        assert a["items"][0]["category"] == a["want"]["category"]
