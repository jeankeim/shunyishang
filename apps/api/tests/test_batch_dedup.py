"""
换一批批次去重测试

验证不同批次（batch_index=0/1/2）的推荐物品完全不重合：
1. 推荐引擎 score_and_rank_items 的批次选择（确定性模拟 + 显式排除）
2. 每日穿搭 _select_diverse_items 的批次选择
3. 各种场景：不同天气、不同风格偏好、候选不足回退、确定性复现

测试数据集：make_test_items() 构造跨品类/跨五行/跨厚度的候选集，
模拟公共库向量检索返回的评分前候选。
"""

import pytest

from packages.recommendation.engine import score_and_rank_items, _canonical_item_key


# ============================================================
# 测试数据集构造器
# ============================================================

CATEGORY_CYCLE = ["上装", "下装", "裙装", "外套", "鞋履", "配饰", "饰品", "文玩"]
ELEMENT_CYCLE = ["木", "火", "土", "金", "水"]
STYLE_CYCLE = ["休闲", "正式", "运动", "甜美"]


def make_test_items(n: int = 32, thickness: str = "适中") -> list:
    """
    构造批次去重测试数据集

    - 品类循环覆盖 8 大类（上装/下装/裙装/外套/鞋履/配饰/饰品/文玩）
    - 五行循环覆盖 5 行
    - semantic_score 递减（0.90, 0.89, ...），保证排序有区分度
    - item_code 唯一，模拟公共库物品
    """
    items = []
    for i in range(n):
        items.append({
            "id": i + 1,
            "item_code": f"TEST{i + 1:03d}",
            "name": f"测试物品{i + 1}",
            "category": CATEGORY_CYCLE[i % len(CATEGORY_CYCLE)],
            "primary_element": ELEMENT_CYCLE[i % len(ELEMENT_CYCLE)],
            "style": STYLE_CYCLE[i % len(STYLE_CYCLE)],
            "thickness_level": thickness,
            "semantic_score": 0.90 - i * 0.01,
        })
    return items


def top_keys(result: dict) -> set:
    """提取 top_items 的规范 key 集合"""
    return {_canonical_item_key(it) for it in result["top_items"]}


# ============================================================
# 1. 引擎批次去重：核心保证
# ============================================================

class TestEngineBatchDedup:
    """score_and_rank_items 批次间物品不重合"""

    def test_three_batches_pairwise_disjoint(self):
        """候选充足时，批次 0/1/2 两两不重合"""
        items = make_test_items(32)
        results = [
            score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=b)
            for b in range(3)
        ]
        keys = [top_keys(r) for r in results]

        for r in results:
            assert len(r["top_items"]) == 5

        assert keys[0].isdisjoint(keys[1]), f"批次0/1重叠: {keys[0] & keys[1]}"
        assert keys[0].isdisjoint(keys[2]), f"批次0/2重叠: {keys[0] & keys[2]}"
        assert keys[1].isdisjoint(keys[2]), f"批次1/2重叠: {keys[1] & keys[2]}"

    def test_batch_deterministic_reproducible(self):
        """相同输入重复调用，同一批次结果完全一致（缓存/模拟一致性前提）"""
        for b in range(3):
            r1 = score_and_rank_items(items=make_test_items(32), target_elements=["火"], top_k=5, batch_index=b)
            r2 = score_and_rank_items(items=make_test_items(32), target_elements=["火"], top_k=5, batch_index=b)
            keys1 = [_canonical_item_key(it) for it in r1["top_items"]]
            keys2 = [_canonical_item_key(it) for it in r2["top_items"]]
            assert keys1 == keys2, f"batch_index={b} 结果不可复现"

    def test_batch0_keeps_top_quality(self):
        """批次0仍保持最高质量：全场最高分物品必须在批次0中"""
        items = make_test_items(32)
        result = score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=0)

        best = max(result["scored_items"], key=lambda x: x["final_score"])
        assert _canonical_item_key(best) in top_keys(result), "批次0应包含最高分物品"

    def test_batch1_no_pullback_by_completeness(self):
        """搭配完整性保障不得捞回前批物品（品类稀缺场景）"""
        # 仅 2 件上装：批次0 会选走最高分上装，批次1 只能用另一件（或缺失），绝不能重复
        items = []
        for i in range(2):
            items.append({
                "id": 100 + i, "item_code": f"TOP{i}", "name": f"上装{i}",
                "category": "上装", "primary_element": "木",
                "thickness_level": "适中", "semantic_score": 0.9 - i * 0.01,
            })
        # 其余品类充足
        for i in range(20):
            cat = ["下装", "裙装", "外套", "鞋履", "饰品"][i % 5]
            items.append({
                "id": 200 + i, "item_code": f"OTH{i}", "name": f"其他{i}",
                "category": cat, "primary_element": ELEMENT_CYCLE[i % 5],
                "thickness_level": "适中", "semantic_score": 0.8 - i * 0.01,
            })

        r0 = score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=0)
        r1 = score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=1)

        assert top_keys(r0).isdisjoint(top_keys(r1)), \
            f"批次1捞回了前批物品: {top_keys(r0) & top_keys(r1)}"

    def test_insufficient_candidates_fallback(self):
        """候选不足时优雅回退：不崩溃、结果非空、优先使用新鲜候选"""
        items = make_test_items(7)  # 仅 7 件，top_k=5，batch 2 时新候选必然不足
        r0 = score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=0)
        r2 = score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=2)

        assert len(r0["top_items"]) > 0
        assert len(r2["top_items"]) > 0
        assert len(r2["top_items"]) <= 5

    def test_batch_index_zero_unaffected(self):
        """batch_index=0 行为不受批次机制影响（首批体验不变）"""
        items = make_test_items(32)
        result = score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=0)

        assert len(result["top_items"]) == 5
        # scored_items 保持全量且按 final_score 降序（旅行规划等下游依赖）
        assert len(result["scored_items"]) == 32
        scores = [it["final_score"] for it in result["scored_items"]]
        assert scores == sorted(scores, reverse=True)


# ============================================================
# 2. 多场景验证：天气 / 风格 / 五行 / top_k
# ============================================================

class TestBatchDedupScenarios:
    """不同查询条件下批次去重均生效"""

    def test_disjoint_with_extreme_hot_weather(self):
        """极端高温（32°C）：温度过滤+安全检查后批次仍不重合"""
        items = make_test_items(32, thickness="轻薄")
        weather = {"temperature": 32, "weather_desc": "晴"}

        r0 = score_and_rank_items(items=items, target_elements=["火"], top_k=5,
                                  batch_index=0, weather_info=weather)
        r1 = score_and_rank_items(items=items, target_elements=["火"], top_k=5,
                                  batch_index=1, weather_info=weather)

        assert len(r0["top_items"]) == 5
        assert len(r1["top_items"]) == 5
        assert top_keys(r0).isdisjoint(top_keys(r1))

    def test_disjoint_with_cold_weather(self):
        """低温（8°C）：批次不重合"""
        items = make_test_items(32, thickness="中厚")
        weather = {"temperature": 8, "weather_desc": "阴"}

        r0 = score_and_rank_items(items=items, target_elements=["水"], top_k=5,
                                  batch_index=0, weather_info=weather)
        r1 = score_and_rank_items(items=items, target_elements=["水"], top_k=5,
                                  batch_index=1, weather_info=weather)

        assert top_keys(r0).isdisjoint(top_keys(r1))

    def test_disjoint_with_style_preference(self):
        """不同用户风格偏好（个性化保障路径）：批次不重合"""
        items = make_test_items(32)
        for style in ["休闲", "正式"]:
            r0 = score_and_rank_items(items=items, target_elements=["木"], top_k=5,
                                      batch_index=0, user_style_preference=style)
            r1 = score_and_rank_items(items=items, target_elements=["木"], top_k=5,
                                      batch_index=1, user_style_preference=style)
            assert top_keys(r0).isdisjoint(top_keys(r1)), f"风格={style} 时批次重叠"

    def test_disjoint_with_different_elements(self):
        """不同喜用神五行：批次不重合"""
        items = make_test_items(32)
        for elem in ELEMENT_CYCLE:
            r0 = score_and_rank_items(items=items, target_elements=[elem], top_k=5, batch_index=0)
            r1 = score_and_rank_items(items=items, target_elements=[elem], top_k=5, batch_index=1)
            assert top_keys(r0).isdisjoint(top_keys(r1)), f"五行={elem} 时批次重叠"

    def test_disjoint_with_top_k_3(self):
        """top_k=3（前端最小档）：三批次两两不重合"""
        items = make_test_items(32)
        results = [
            score_and_rank_items(items=items, target_elements=["金"], top_k=3, batch_index=b)
            for b in range(3)
        ]
        keys = [top_keys(r) for r in results]
        assert keys[0].isdisjoint(keys[1])
        assert keys[1].isdisjoint(keys[2])
        assert keys[0].isdisjoint(keys[2])

    def test_quality_not_degraded(self):
        """推荐质量：各批次数量足额、批次0平均分 >= 批次2平均分（高分优先消耗）"""
        items = make_test_items(32)
        results = [
            score_and_rank_items(items=items, target_elements=["木"], top_k=5, batch_index=b)
            for b in range(3)
        ]
        for r in results:
            assert len(r["top_items"]) == 5, "各批次都应返回足额物品"

        avg0 = sum(it["final_score"] for it in results[0]["top_items"]) / 5
        avg2 = sum(it["final_score"] for it in results[2]["top_items"]) / 5
        assert avg0 >= avg2 - 1e-9, "批次0平均分应不低于批次2（高分优先展示）"


# ============================================================
# 3. 每日穿搭 _select_diverse_items 批次去重
# ============================================================

class TestDailyOutfitBatchDedup:
    """daily_outfit_service._select_diverse_items 批次间物品不重合"""

    @staticmethod
    def _make_scored(n: int = 20) -> list:
        """构造 (item, score) 评分元组列表，模拟衣橱评分结果（降序）"""
        cats = ["上装", "下装", "裙装", "外套", "鞋履", "配饰"]
        scored = []
        for i in range(n):
            item = {
                "id": i + 1,
                "name": f"衣橱物品{i + 1}",
                "category": cats[i % len(cats)],
                "primary_element": ELEMENT_CYCLE[i % 5],
            }
            scored.append((item, 100 - i))
        return scored

    def test_daily_batches_disjoint(self):
        """批次 0/1/2 两两不重合"""
        from apps.api.services.daily_outfit_service import _select_diverse_items

        scored = self._make_scored(24)
        ids = []
        for b in range(3):
            selected = _select_diverse_items(scored, target_count=5, batch_index=b)
            assert len(selected) == 5
            ids.append({it["id"] for it in selected})

        assert ids[0].isdisjoint(ids[1]), f"批次0/1重叠: {ids[0] & ids[1]}"
        assert ids[0].isdisjoint(ids[2]), f"批次0/2重叠: {ids[0] & ids[2]}"
        assert ids[1].isdisjoint(ids[2]), f"批次1/2重叠: {ids[1] & ids[2]}"

    def test_daily_category_limit_respected(self):
        """各批次仍遵守品类上限（上装/下装/外套等每类1件，配饰2件）"""
        from apps.api.services.daily_outfit_service import (
            _select_diverse_items, CATEGORY_MAX_PER_OUTFIT,
        )

        scored = self._make_scored(24)
        for b in range(3):
            selected = _select_diverse_items(scored, target_count=5, batch_index=b)
            counts = {}
            for it in selected:
                counts[it["category"]] = counts.get(it["category"], 0) + 1
            for cat, cnt in counts.items():
                assert cnt <= CATEGORY_MAX_PER_OUTFIT.get(cat, 1), \
                    f"批次{b} 品类 {cat} 超限: {cnt}"

    def test_daily_insufficient_fallback(self):
        """候选耗尽时回退复用已展示物品（不返回空）"""
        from apps.api.services.daily_outfit_service import _select_diverse_items

        scored = self._make_scored(5)  # 仅 5 件，batch 2 时候选耗尽
        selected = _select_diverse_items(scored, target_count=5, batch_index=2)
        assert len(selected) > 0, "候选耗尽回退不应返回空"

    def test_daily_batch0_unchanged(self):
        """batch_index=0 选择最高分组合（首批体验不变）"""
        from apps.api.services.daily_outfit_service import _select_diverse_items

        scored = self._make_scored(24)
        selected = _select_diverse_items(scored, target_count=5, batch_index=0)
        # 前 5 件评分最高且品类互不冲突（上装/下装/裙装/外套/鞋履），应原样入选
        assert [it["id"] for it in selected] == [1, 2, 3, 4, 5]
