"""
每日智能穿搭：槽位式成套选择单元测试

覆盖 daily_outfit_service._select_complete_outfit：
- 槽位齐全（核心位/鞋履/外套/配饰）
- 缺品类时的回落与 missing 登记
- 温度阈值决定是否保留外套槽
- 裙装替代上装+下装的判定
- 换一批批次间不重合、品类上限
"""

import pytest

from apps.api.services.daily_outfit_service import (
    ACCESSORY_CATEGORIES,
    CATEGORY_MAX_PER_OUTFIT,
    _empty_completeness,
    _select_complete_outfit,
)


def _item(item_id: int, category: str, name: str = "") -> dict:
    return {
        "id": item_id,
        "name": name or f"{category}{item_id}",
        "category": category,
        "image_url": None,
        "primary_element": "木",
        "secondary_element": None,
        "wear_count": 0,
        "is_favorite": False,
    }


def _scored(pairs) -> list:
    """[(item, score)]，按分数降序排列（与 generate_daily_outfit 产出一致）"""
    rows = [(_item(i, cat), score) for i, cat, score in pairs]
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


def _categories(selected) -> list:
    return [it["category"] for it in selected]


class TestSlotCompleteness:
    """槽位齐全与缺口登记"""

    def test_all_slots_filled(self):
        """衣橱品类齐全时成套含上装/下装/鞋履/外套/配饰"""
        scored = _scored([
            (1, "上装", 95),
            (2, "下装", 90),
            (3, "鞋履", 85),
            (4, "配饰", 80),
            (5, "外套", 75),
            (6, "配饰", 70),
            (7, "上装", 65),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=10, target_count=5)

        cats = _categories(selected)
        assert "上装" in cats and "下装" in cats and "鞋履" in cats and "外套" in cats
        assert "配饰" in cats
        assert comp["has_top"] and comp["has_bottom_or_dress"]
        assert comp["has_shoes"] and comp["has_accessory"]
        assert comp["missing"] == []

    def test_accessory_slot_allows_two(self):
        """配饰槽位可出 2 件（与 CATEGORY_MAX_PER_OUTFIT['配饰'] 对齐）"""
        scored = _scored([
            (1, "上装", 95),
            (2, "下装", 90),
            (3, "鞋履", 85),
            (4, "配饰", 80),
            (5, "配饰", 79),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=25, target_count=5)

        assert _categories(selected).count("配饰") == 2
        assert comp["has_accessory"]

    def test_missing_categories_recorded(self):
        """衣橱只有上装时：其余槽位回落失败，missing 登记缺口"""
        scored = _scored([
            (1, "上装", 95),
            (2, "上装", 90),
            (3, "上装", 85),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=25, target_count=5)

        assert len(selected) == 1, "品类上限为 1，同品类不应堆量"
        assert comp["has_top"] is True
        assert comp["has_bottom_or_dress"] is False
        assert comp["missing"] == ["下装", "鞋履", "配饰"]

    def test_no_shoes_records_missing_but_keeps_count(self):
        """无鞋履时跳过鞋履位并记入 missing，其余槽位照常出（不为凑数塞重复品类）"""
        scored = _scored([
            (1, "上装", 95),
            (2, "下装", 90),
            (3, "配饰", 88),
            (4, "外套", 85),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=25, target_count=4)

        assert "鞋履" in comp["missing"]
        assert comp["has_shoes"] is False
        assert [it["category"] for it in selected] == ["上装", "下装", "配饰"]

    def test_one_piece_counts_as_top_and_bottom(self):
        """套装同时满足上身与下身，不产生缺口"""
        scored = _scored([
            (1, "套装", 95),
            (2, "鞋履", 90),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=25, target_count=5)

        assert "套装" in _categories(selected)
        assert comp["has_top"] is True
        assert comp["has_bottom_or_dress"] is True
        assert "上装" not in comp["missing"] and "下装" not in comp["missing"]

    def test_empty_pool(self):
        """无候选时返回空列表与空完整性摘要"""
        selected, comp = _select_complete_outfit([], temperature=20, target_count=5)
        assert selected == []
        assert comp == _empty_completeness()


class TestOuterwearSlotTemperature:
    """外套位由温度阈值决定"""

    _PAIRS = [
        (1, "上装", 95),
        (2, "下装", 90),
        (3, "鞋履", 85),
        (4, "配饰", 80),
        (5, "外套", 75),
    ]

    def test_cold_keeps_outer_slot(self):
        scored = _scored(self._PAIRS)
        selected, _ = _select_complete_outfit(scored, temperature=12, target_count=5)
        assert "外套" in _categories(selected)

    def test_warm_drops_outer_slot(self):
        scored = _scored(self._PAIRS)
        selected, comp = _select_complete_outfit(scored, temperature=26, target_count=5)
        assert "外套" not in _categories(selected)
        assert "外套" not in comp["missing"]

    def test_threshold_boundary_inclusive(self):
        """temperature == 15 仍保留外套槽"""
        scored = _scored(self._PAIRS)
        selected, _ = _select_complete_outfit(scored, temperature=15, target_count=5)
        assert "外套" in _categories(selected)

    def test_cold_without_outer_stocked_marks_missing(self):
        """低温且衣橱无外套 → 登记缺口；高温无外套 → 不登记"""
        scored = _scored([(1, "上装", 95), (2, "下装", 90), (3, "鞋履", 85)])
        _, cold_comp = _select_complete_outfit(scored, temperature=5, target_count=5)
        _, warm_comp = _select_complete_outfit(scored, temperature=30, target_count=5)
        assert "外套" in cold_comp["missing"]
        assert "外套" not in warm_comp["missing"]


class TestDressSubstitution:
    """裙装替代上装+下装的判定"""

    def test_dress_wins_when_higher_than_top_plus_bottom(self):
        scored = _scored([
            (1, "裙装", 98),
            (2, "上装", 60),
            (3, "下装", 30),
            (4, "鞋履", 20),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=25, target_count=4)

        # 核心位走裙装（首件即裙装），不占用下装槽
        assert selected[0]["category"] == "裙装"
        assert selected[1]["category"] == "鞋履"
        assert comp["has_top"] and comp["has_bottom_or_dress"]

    def test_top_bottom_win_when_combined_higher(self):
        scored = _scored([
            (1, "裙装", 50),
            (2, "上装", 95),
            (3, "下装", 90),
            (4, "鞋履", 85),
        ])
        selected, _ = _select_complete_outfit(scored, temperature=25, target_count=3)

        assert [it["category"] for it in selected] == ["上装", "下装", "鞋履"]

    def test_dress_used_when_bottom_absent(self):
        """无下装时裙装即唯一核心，不应判成缺下装"""
        scored = _scored([
            (1, "裙装", 40),
            (2, "上装", 95),
            (3, "鞋履", 85),
        ])
        selected, comp = _select_complete_outfit(scored, temperature=25, target_count=5)
        cats = _categories(selected)

        assert "裙装" in cats
        assert comp["has_bottom_or_dress"] is True
        assert "下装" not in comp["missing"]


class TestBatchDiversity:
    """换一批：批次间不重合、品类上限、候选耗尽回退"""

    @staticmethod
    def _full_wardrobe(n: int = 24) -> list:
        cats = ["上装", "下装", "裙装", "外套", "鞋履", "配饰"]
        pairs = [(i + 1, cats[i % len(cats)], 100 - i) for i in range(n)]
        return _scored(pairs)

    def test_batches_disjoint(self):
        scored = self._full_wardrobe(24)
        seen = []
        for batch in range(3):
            selected, comp = _select_complete_outfit(scored, temperature=12, target_count=5, batch_index=batch)
            assert len(selected) == 5
            assert comp["missing"] == []
            seen.append({it["id"] for it in selected})

        assert seen[0].isdisjoint(seen[1])
        assert seen[0].isdisjoint(seen[2])
        assert seen[1].isdisjoint(seen[2])

    def test_category_caps_respected_across_batches(self):
        scored = self._full_wardrobe(24)
        for batch in range(4):
            selected, _ = _select_complete_outfit(scored, temperature=12, target_count=5, batch_index=batch)
            counts: dict = {}
            for it in selected:
                counts[it["category"]] = counts.get(it["category"], 0) + 1
            for cat, cnt in counts.items():
                assert cnt <= CATEGORY_MAX_PER_OUTFIT.get(cat, 1), f"批次{batch} 品类 {cat} 超限"

    def test_exhausted_candidates_fall_back(self):
        """候选耗尽时回退复用已展示物品，不返回空"""
        scored = self._full_wardrobe(5)
        selected, _ = _select_complete_outfit(scored, temperature=12, target_count=5, batch_index=3)
        assert selected, "候选耗尽应回退而非返回空"

    def test_slot_order_prefers_high_score_per_category(self):
        """同品类内取分数最高者（槽位语义，而非全局前 5）"""
        scored = _scored([
            (1, "配饰", 99),
            (2, "上装", 60),
            (3, "下装", 55),
            (4, "鞋履", 50),
            (5, "配饰", 45),
        ])
        selected, _ = _select_complete_outfit(scored, temperature=25, target_count=4)
        accessory_ids = [it["id"] for it in selected if it["category"] in ACCESSORY_CATEGORIES]

        assert 1 in accessory_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
