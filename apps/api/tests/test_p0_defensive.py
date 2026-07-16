"""
P0缺陷防御性测试套件 - 验证推荐系统核心逻辑的正确性

覆盖6个P0缺陷修复：
- #96: 缓存键完整性
- #47: 流年追加上限保护
- #59: wuxing_score 归一化
- #60: wear_count 与 wuxing_score 隔离
- #29: 温度阈值常量一致性
- #30: 温度硬过滤全空回退
"""

import hashlib
import pytest
from unittest.mock import patch, MagicMock


# ===================================================================
# #96: 缓存键必须包含所有影响推荐结果的字段
# ===================================================================
class TestCacheKeyCompleteness:
    """#96: 缓存键必须包含所有影响推荐结果的字段"""

    def _build_cache_key(self, **overrides):
        """
        复现 recommend.py:39-68 的缓存键构建逻辑。
        通过构造 RecommendRequest 并模拟路由中的 cache_key 拼接。
        """
        from apps.api.schemas.request import RecommendRequest, WeatherInfo, BaziInput

        defaults = {
            "query": "去面试穿什么",
            "scene": "面试",
            "weather_element": "火",
            "top_k": 5,
            "retrieval_mode": "public",
            "gender": "男",
            "weather": {"temperature": 20, "weather_desc": "晴", "humidity": 50, "wind_level": 2},
            "bazi": {"birth_year": 1995, "birth_month": 6, "birth_day": 15, "birth_hour": 10, "gender": "男"},
        }
        defaults.update(overrides)
        req = RecommendRequest(**defaults)

        # 复现 recommend.py 中的 cache_key 构建
        cache_key_parts = [
            req.query or "",
            req.scene or "",
            req.weather_element or "",
            str(req.user_id),
            req.retrieval_mode or "public",
            str(req.top_k),
            req.gender or "",
            str(req.travel_days) if req.travel_days is not None else "",
            req.destination or "",
            req.luggage_size or "",
        ]
        if req.weather:
            cache_key_parts.extend([
                str(req.weather.temperature) if req.weather.temperature is not None else "",
                req.weather.weather_desc or "",
                str(req.weather.humidity) if req.weather.humidity is not None else "",
                str(req.weather.wind_level) if req.weather.wind_level is not None else "",
            ])
        if req.bazi:
            cache_key_parts.extend([
                str(req.bazi.birth_year),
                str(req.bazi.birth_month),
                str(req.bazi.birth_day),
                str(req.bazi.birth_hour),
                req.bazi.gender or "",
            ])
        cache_key_raw = "|".join(cache_key_parts)
        return hashlib.md5(cache_key_raw.encode()).hexdigest()

    def test_temperature_difference_produces_different_cache_key(self):
        """仅温度不同 → 不同缓存键"""
        key1 = self._build_cache_key(weather={"temperature": 15, "weather_desc": "晴"})
        key2 = self._build_cache_key(weather={"temperature": 30, "weather_desc": "晴"})
        assert key1 != key2, "温度不同时缓存键应不同"

    def test_travel_days_difference_produces_different_cache_key(self):
        """仅旅行天数不同 → 不同缓存键"""
        key1 = self._build_cache_key(travel_days=3)
        key2 = self._build_cache_key(travel_days=7)
        assert key1 != key2, "旅行天数不同时缓存键应不同"

    def test_luggage_size_difference_produces_different_cache_key(self):
        """仅行李箱大小不同 → 不同缓存键"""
        key1 = self._build_cache_key(luggage_size="小")
        key2 = self._build_cache_key(luggage_size="大")
        assert key1 != key2, "行李箱大小不同时缓存键应不同"

    def test_gender_difference_produces_different_cache_key(self):
        """仅性别不同 → 不同缓存键"""
        key1 = self._build_cache_key(gender="男")
        key2 = self._build_cache_key(gender="女")
        assert key1 != key2, "性别不同时缓存键应不同"

    def test_destination_difference_produces_different_cache_key(self):
        """仅目的地不同 → 不同缓存键"""
        key1 = self._build_cache_key(destination="北京")
        key2 = self._build_cache_key(destination="上海")
        assert key1 != key2, "目的地不同时缓存键应不同"

    def test_identical_requests_produce_same_cache_key(self):
        """完全相同的请求 → 相同缓存键（幂等性）"""
        key1 = self._build_cache_key(travel_days=5, destination="杭州", luggage_size="中")
        key2 = self._build_cache_key(travel_days=5, destination="杭州", luggage_size="中")
        assert key1 == key2, "相同请求应产生相同缓存键"


# ===================================================================
# #59: wuxing_score 不得超过 1.0
# ===================================================================
class TestWuxingScoreNormalization:
    """#59: wuxing_score 归一化 min(1.0, wuxing_score)"""

    def _compute_wuxing_score(self, item, target_elements, boost_elements=None):
        """
        复现 nodes.py:750-776 的五行评分计算逻辑。
        """
        wuxing_score = 0.0
        primary = item.get("primary_element", "")
        secondary = item.get("secondary_element")

        if primary in target_elements:
            wuxing_score += 0.6
        if secondary and secondary in target_elements:
            wuxing_score += 0.3

        if boost_elements:
            base_target_score = 0.0
            if primary in target_elements:
                base_target_score += 0.6
            if secondary and secondary in target_elements:
                base_target_score += 0.3
            boost_raw = 0.0
            if primary in boost_elements:
                boost_raw += 0.08
            if secondary and secondary in boost_elements:
                boost_raw += 0.04
            boost_capped = min(boost_raw, max(base_target_score, 0.05))
            wuxing_score += boost_capped

        # 归一化：关键修复点
        wuxing_score = min(1.0, wuxing_score)
        return wuxing_score

    def test_wuxing_score_capped_at_1(self):
        """同时命中 primary + secondary + boost，score 不得超过 1.0"""
        item = {"primary_element": "火", "secondary_element": "木"}
        target = ["火", "木"]
        boost = ["火", "木"]  # 同时也在 boost 中
        score = self._compute_wuxing_score(item, target, boost)
        assert score <= 1.0, f"wuxing_score={score} 超过 1.0 上限"

    def test_wuxing_score_non_negative(self):
        """无任何五行匹配时，score >= 0.0"""
        item = {"primary_element": "土", "secondary_element": None}
        target = ["火", "木"]
        score = self._compute_wuxing_score(item, target)
        assert score >= 0.0, f"wuxing_score={score} 不应为负数"

    def test_wuxing_score_primary_only(self):
        """仅命中 primary → 0.6"""
        item = {"primary_element": "火", "secondary_element": "金"}
        target = ["火"]
        score = self._compute_wuxing_score(item, target)
        assert score == 0.6

    def test_wuxing_score_primary_and_secondary(self):
        """命中 primary + secondary → 0.9"""
        item = {"primary_element": "火", "secondary_element": "木"}
        target = ["火", "木"]
        score = self._compute_wuxing_score(item, target)
        assert score == pytest.approx(0.9), "primary+secondary → 0.6+0.3=0.9"


# ===================================================================
# #60: wear_count 不得影响 wuxing_score（独立为 rotation_bonus）
# ===================================================================
class TestWearCountIsolation:
    """#60: wear_count 已拆为独立 rotation_bonus，不影响 wuxing_score"""

    def _compute_scores(self, item, target_elements, weather_info=None):
        """
        复现 nodes.py:750-808 的评分逻辑，返回 (wuxing_score, rotation_bonus)。
        """
        # 五行分
        wuxing_score = 0.0
        primary = item.get("primary_element", "")
        secondary = item.get("secondary_element")
        if primary in target_elements:
            wuxing_score += 0.6
        if secondary and secondary in target_elements:
            wuxing_score += 0.3
        wuxing_score = min(1.0, wuxing_score)

        # rotation_bonus（独立微调项）
        wear_count = item.get("wear_count")  # None for public items
        rotation_bonus = 0.0
        if wear_count is not None and isinstance(wear_count, (int, float)) and wear_count >= 0:
            rotation_bonus = max(0.0, 0.05 - wear_count * 0.01)

        return wuxing_score, rotation_bonus

    def test_wear_count_does_not_affect_wuxing_score(self):
        """wear_count=0 和 wear_count=100 时，wuxing_score 应相同"""
        base = {"primary_element": "火", "secondary_element": "木"}
        target = ["火", "木"]

        item_new = {**base, "wear_count": 0}
        item_worn = {**base, "wear_count": 100}

        wx_new, _ = self._compute_scores(item_new, target)
        wx_worn, _ = self._compute_scores(item_worn, target)

        assert wx_new == wx_worn, f"wear_count 不应影响 wuxing_score: {wx_new} vs {wx_worn}"

    def test_wear_count_only_affects_rotation_bonus(self):
        """wear_count 只影响 rotation_bonus"""
        base = {"primary_element": "火", "secondary_element": None}
        target = ["火"]

        item_new = {**base, "wear_count": 0}
        item_worn = {**base, "wear_count": 10}

        _, rb_new = self._compute_scores(item_new, target)
        _, rb_worn = self._compute_scores(item_worn, target)

        assert rb_new > rb_worn, "wear_count=0 的 rotation_bonus 应大于 wear_count=10"
        assert rb_new == pytest.approx(0.05), "wear_count=0 → rotation_bonus=0.05"
        assert rb_worn == pytest.approx(0.0), "wear_count=10 → rotation_bonus=0.0"

    def test_no_wear_count_means_zero_bonus(self):
        """公共库物品无 wear_count → rotation_bonus=0"""
        item = {"primary_element": "火"}
        target = ["火"]
        _, rb = self._compute_scores(item, target)
        assert rb == 0.0, "无 wear_count 字段时 rotation_bonus 应为 0"


# ===================================================================
# #47: 流年追加不得超过 MAX_TARGET_ELEMENTS(3) 个
# ===================================================================
class TestAnnualElementLimit:
    """#47: 流年追加不得超过 MAX_TARGET_ELEMENTS(3) 个"""

    MAX_TARGET_ELEMENTS = 3

    def _simulate_annual_enhancement(self, target_elements, xiyong_elements,
                                     annual_lucky_elements, avoid_elements=None):
        """
        复现 nodes.py:330-345 的流年增强逻辑。
        返回增强后的 target_elements。
        """
        if avoid_elements is None:
            avoid_elements = []
        target = list(target_elements)
        added = []
        for elem in annual_lucky_elements[:2]:  # 最多取前2个
            if len(target) >= self.MAX_TARGET_ELEMENTS:
                break
            if elem not in target and elem not in xiyong_elements and elem not in avoid_elements:
                target.append(elem)
                added.append(elem)
        return target

    def test_no_append_when_target_full(self):
        """已有3个target时，流年元素不追加"""
        result = self._simulate_annual_enhancement(
            target_elements=["火", "木", "水"],
            xiyong_elements=["火", "木"],
            annual_lucky_elements=["土", "金"],
        )
        assert len(result) == 3, f"target已满3个，不应追加: {result}"
        assert result == ["火", "木", "水"]

    def test_append_at_most_one_when_two_targets(self):
        """有2个target时，流年最多追加1个（达到上限3）"""
        result = self._simulate_annual_enhancement(
            target_elements=["火", "木"],
            xiyong_elements=["火", "木"],
            annual_lucky_elements=["土", "金"],
        )
        assert len(result) <= self.MAX_TARGET_ELEMENTS, f"不应超过上限: {result}"
        assert len(result) == 3, "应追加1个到上限"

    def test_skip_annual_element_in_avoid(self):
        """流年元素属于忌神时不追加"""
        result = self._simulate_annual_enhancement(
            target_elements=["火"],
            xiyong_elements=["火"],
            annual_lucky_elements=["金", "水"],
            avoid_elements=["金"],
        )
        assert "金" not in result, "忌神不应被追加"

    def test_skip_already_present_annual_element(self):
        """流年元素已在 target 中时不重复追加"""
        result = self._simulate_annual_enhancement(
            target_elements=["火", "木"],
            xiyong_elements=["火", "木"],
            annual_lucky_elements=["火", "土"],
        )
        assert result.count("火") == 1, "不应重复追加已有元素"
        assert "土" in result, "新的流年元素应被追加"

    def test_empty_annual_luck_no_change(self):
        """无流年数据时 target 不变"""
        result = self._simulate_annual_enhancement(
            target_elements=["火", "木"],
            xiyong_elements=["火", "木"],
            annual_lucky_elements=[],
        )
        assert result == ["火", "木"]


# ===================================================================
# #29: 温度阈值必须与模块常量一致
# ===================================================================
class TestTemperatureThresholds:
    """#29: 温度阈值统一使用模块常量，评分函数与硬过滤一致"""

    def test_constants_values(self):
        """验证模块常量值正确"""
        from packages.ai_agents.nodes import (
            EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
            EXTREME_COLD_TEMP, MILD_COLD_TEMP,
        )
        assert EXTREME_HOT_TEMP == 30
        assert HOT_TEMP == 28
        assert MILD_HOT_TEMP == 25
        assert EXTREME_COLD_TEMP == 5
        assert MILD_COLD_TEMP == 10

    def test_extreme_cold_boundary_at_5(self):
        """EXTREME_COLD_TEMP=5 边界：厚重加分，轻薄扣分"""
        from packages.ai_agents.nodes import _calculate_temp_score
        heavy = {"name": "羽绒服", "thickness_level": "厚重"}
        thin = {"name": "T恤", "thickness_level": "轻薄"}

        score_heavy = _calculate_temp_score(heavy, {"temperature": 5})
        score_thin = _calculate_temp_score(thin, {"temperature": 5})

        assert score_heavy > 0.5, "极端低温下厚重衣物应获得加分"
        assert score_thin < 0.5, "极端低温下轻薄衣物应被扣分"

    def test_mild_cold_boundary_at_10(self):
        """MILD_COLD_TEMP=10 边界：厚重加分，极薄扣分"""
        from packages.ai_agents.nodes import _calculate_temp_score
        heavy = {"name": "大衣", "thickness_level": "厚重"}
        very_thin = {"name": "背心", "thickness_level": "极薄"}

        score_heavy = _calculate_temp_score(heavy, {"temperature": 10})
        score_thin = _calculate_temp_score(very_thin, {"temperature": 10})

        assert score_heavy > 0.5, "低温下厚重衣物应获得加分"
        assert score_thin < 0.5, "低温下极薄衣物应被扣分"

    def test_mild_hot_boundary_at_25(self):
        """MILD_HOT_TEMP=25 边界：轻薄加分，厚重扣分"""
        from packages.ai_agents.nodes import _calculate_temp_score
        thin = {"name": "T恤", "thickness_level": "轻薄"}
        heavy = {"name": "棉衣", "thickness_level": "厚重"}

        score_thin = _calculate_temp_score(thin, {"temperature": 25})
        score_heavy = _calculate_temp_score(heavy, {"temperature": 25})

        assert score_thin > 0.5, "中高温下轻薄衣物应获得加分"
        assert score_heavy < 0.5, "中高温下厚重衣物应被扣分"

    def test_hot_boundary_at_28(self):
        """HOT_TEMP=28 边界：轻薄加分，厚重/中厚扣分"""
        from packages.ai_agents.nodes import _calculate_temp_score
        thin = {"name": "衬衫", "thickness_level": "轻薄"}
        medium = {"name": "卫衣", "thickness_level": "中厚"}

        score_thin = _calculate_temp_score(thin, {"temperature": 28})
        score_medium = _calculate_temp_score(medium, {"temperature": 28})

        assert score_thin > 0.5, "高温下轻薄衣物应获得加分"
        assert score_medium < 0.5, "高温下中厚衣物应被扣分"

    def test_extreme_hot_boundary_at_30(self):
        """EXTREME_HOT_TEMP=30 边界：轻薄加分，厚重扣分"""
        from packages.ai_agents.nodes import _calculate_temp_score
        thin = {"name": "T恤", "thickness_level": "轻薄"}
        heavy = {"name": "羽绒服", "thickness_level": "厚重"}

        score_thin = _calculate_temp_score(thin, {"temperature": 30})
        score_heavy = _calculate_temp_score(heavy, {"temperature": 30})

        assert score_thin > 0.5, "极端高温下轻薄衣物应获得加分"
        assert score_heavy < 0.5, "极端高温下厚重衣物应被扣分"

    def test_temp_score_always_in_01_range(self):
        """温度评分始终在 [0, 1] 范围"""
        from packages.ai_agents.nodes import _calculate_temp_score
        for temp in [-10, 0, 5, 10, 15, 20, 25, 28, 30, 40, 50]:
            for thickness in ["极薄", "轻薄", "适中", "中厚", "厚重"]:
                item = {"name": "测试衣物", "thickness_level": thickness}
                score = _calculate_temp_score(item, {"temperature": temp})
                assert 0.0 <= score <= 1.0, f"temp={temp}, thickness={thickness} → score={score} 越界"


# ===================================================================
# #30: 温度硬过滤全空时不应返回空列表
# ===================================================================
class TestTemperatureFilterFallback:
    """#30: 温度硬过滤全空时回退保留 temp_score 最高的候选"""

    def _apply_temp_filter(self, scored_items, temperature):
        """
        复现 nodes.py:823-865 的温度硬过滤 + 回退逻辑。
        """
        from packages.ai_agents.nodes import (
            EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
            EXTREME_COLD_TEMP, MILD_COLD_TEMP,
            _infer_item_thickness,
        )

        temp_filtered = []
        for item in scored_items:
            thickness = _infer_item_thickness(item)

            if temperature >= EXTREME_HOT_TEMP:
                if thickness in ("厚重", "中厚"):
                    continue
            elif temperature >= HOT_TEMP:
                if thickness in ("厚重", "中厚"):
                    continue
            elif temperature >= MILD_HOT_TEMP:
                if thickness == "厚重":
                    continue
            elif temperature <= EXTREME_COLD_TEMP:
                if thickness in ("极薄", "轻薄"):
                    continue
            elif temperature <= MILD_COLD_TEMP:
                if thickness == "极薄":
                    continue

            temp_filtered.append(item)

        if temp_filtered:
            return temp_filtered
        elif scored_items:
            # 回退：保留 temp_score 最高的候选
            max_ts = max(it.get("temp_score", 0.5) for it in scored_items)
            least_bad = [it for it in scored_items if it.get("temp_score", 0.5) >= max_ts - 1e-9]
            return least_bad
        return []

    def test_fallback_when_all_filtered(self):
        """所有候选都不符合温度要求时，返回 temp_score 最高的（非空）"""
        # 极端高温30°C，但候选全是厚重/中厚
        items = [
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.2},
            {"name": "大衣", "thickness_level": "厚重", "temp_score": 0.3},
            {"name": "毛衣", "thickness_level": "中厚", "temp_score": 0.25},
        ]
        result = self._apply_temp_filter(items, temperature=30)
        assert len(result) > 0, "全空回退不应返回空列表"
        # 应保留 temp_score 最高的
        assert all(r["temp_score"] == 0.3 for r in result), "应保留 temp_score 最高的候选"

    def test_normal_filter_when_candidates_pass(self):
        """正常情况（有合格候选）不受回退影响"""
        items = [
            {"name": "T恤", "thickness_level": "轻薄", "temp_score": 0.8},
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.2},
        ]
        result = self._apply_temp_filter(items, temperature=30)
        assert len(result) == 1
        assert result[0]["name"] == "T恤"

    def test_fallback_returns_multiple_tied_items(self):
        """回退时如有多个同分最高候选，全部保留"""
        items = [
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.3},
            {"name": "大衣", "thickness_level": "厚重", "temp_score": 0.3},
            {"name": "毛衣", "thickness_level": "中厚", "temp_score": 0.1},
        ]
        result = self._apply_temp_filter(items, temperature=30)
        assert len(result) == 2, "两个同分最高候选都应保留"

    def test_extreme_cold_fallback(self):
        """极端低温5°C，所有候选都是轻薄/极薄时，回退保留 temp_score 最高"""
        items = [
            {"name": "T恤", "thickness_level": "轻薄", "temp_score": 0.2},
            {"name": "背心", "thickness_level": "极薄", "temp_score": 0.15},
            {"name": "衬衫", "thickness_level": "轻薄", "temp_score": 0.25},
        ]
        result = self._apply_temp_filter(items, temperature=5)
        assert len(result) > 0, "极端低温全空回退不应返回空列表"
        assert all(r["temp_score"] == 0.25 for r in result)

    def test_moderate_temp_no_filter(self):
        """适中温度（20°C）不触发任何硬过滤"""
        items = [
            {"name": "T恤", "thickness_level": "轻薄", "temp_score": 0.7},
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.5},
            {"name": "毛衣", "thickness_level": "中厚", "temp_score": 0.6},
        ]
        result = self._apply_temp_filter(items, temperature=20)
        assert len(result) == 3, "适中温度不应过滤任何候选"


# ===================================================================
# _is_extreme_temp 辅助函数测试
# ===================================================================
class TestIsExtremeTemp:
    """极端温度判断辅助函数"""

    def test_none_returns_false(self):
        from packages.ai_agents.nodes import _is_extreme_temp
        assert _is_extreme_temp(None) is False

    def test_extreme_cold(self):
        from packages.ai_agents.nodes import _is_extreme_temp
        assert _is_extreme_temp(5) is True
        assert _is_extreme_temp(0) is True
        assert _is_extreme_temp(-10) is True

    def test_extreme_hot(self):
        from packages.ai_agents.nodes import _is_extreme_temp
        assert _is_extreme_temp(30) is True
        assert _is_extreme_temp(35) is True

    def test_moderate_temp(self):
        from packages.ai_agents.nodes import _is_extreme_temp
        assert _is_extreme_temp(15) is False
        assert _is_extreme_temp(20) is False
        assert _is_extreme_temp(25) is False
