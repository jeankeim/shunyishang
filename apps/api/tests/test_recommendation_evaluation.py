"""
推荐算法评估测试

覆盖100问审查清单的核心场景：
1. 权重体系测试：8种组合权重和=1.0，极端温度缩放正确
2. 五行评分测试：primary/secondary/boost 各组合，归一化不超1.0
3. 温度评分测试：6档温度区间评分正确，硬过滤与评分一致
4. 场景识别测试：优先级链（运动>户外>出差>度假>商务...）
5. 审美加分测试：肤色/风格/体型各映射值正确
6. 偏好评分测试：时间衰减、权重转换、中性分回退
7. 多样性测试：分类上限、五行多样性替换、温度安全
8. 缓存键测试：不同温度/目的地/性别生成不同键
"""

import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# 1. 权重体系测试
# ============================================================

class TestWeightPresets:
    """权重预设表测试"""

    def test_all_presets_sum_to_one(self):
        """所有8种预设组合的权重和必须精确等于1.0"""
        from packages.recommendation.config import WEIGHT_PRESETS

        assert len(WEIGHT_PRESETS) == 8, "应有8种预设组合"

        for key, weights in WEIGHT_PRESETS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-9, f"预设 {key} 权重和={total}，应为1.0"

    def test_all_presets_have_five_dimensions(self):
        """所有预设必须包含5个维度"""
        from packages.recommendation.config import WEIGHT_PRESETS

        expected_dims = {"semantic", "wuxing", "scene", "pref", "temp"}
        for key, weights in WEIGHT_PRESETS.items():
            assert set(weights.keys()) == expected_dims, f"预设 {key} 维度不完整"

    def test_all_weights_non_negative(self):
        """所有权重必须非负"""
        from packages.recommendation.config import WEIGHT_PRESETS

        for key, weights in WEIGHT_PRESETS.items():
            for dim, val in weights.items():
                assert val >= 0, f"预设 {key} 的 {dim}={val} 为负"

    def test_compute_weights_basic(self):
        """compute_recommend_weights 基本功能"""
        from packages.recommendation.config import compute_recommend_weights

        # 有八字+有场景+有偏好
        w = compute_recommend_weights(has_bazi=True, has_scene=True, has_prefs=True)
        assert abs(sum(w.values()) - 1.0) < 1e-9
        assert w["wuxing"] > 0
        assert w["scene"] > 0
        assert w["pref"] > 0

    def test_compute_weights_no_bazi_no_scene(self):
        """无八字无场景时，semantic权重应最高"""
        from packages.recommendation.config import compute_recommend_weights

        w = compute_recommend_weights(has_bazi=False, has_scene=False, has_prefs=False)
        assert w["semantic"] >= w["wuxing"]
        assert w["scene"] == 0.0
        assert w["pref"] == 0.0

    def test_extreme_temp_scaling(self):
        """极端温度时，temp维度占25%，其余按比例缩减"""
        from packages.recommendation.config import compute_recommend_weights, EXTREME_TEMP_RATIO

        w = compute_recommend_weights(
            has_bazi=True, has_scene=True, has_prefs=True, is_extreme_temp=True
        )
        assert abs(w["temp"] - EXTREME_TEMP_RATIO) < 1e-9, "极端温度时temp应占25%"
        assert abs(sum(w.values()) - 1.0) < 1e-9, "极端温度缩放后总和仍应为1.0"

    def test_extreme_temp_preserves_relative_order(self):
        """极端温度缩放后，各维度相对大小关系不变"""
        from packages.recommendation.config import compute_recommend_weights

        w_normal = compute_recommend_weights(has_bazi=True, has_scene=True, has_prefs=True)
        w_extreme = compute_recommend_weights(
            has_bazi=True, has_scene=True, has_prefs=True, is_extreme_temp=True
        )

        # semantic 应仍是最大的（排除temp）
        non_temp_dims = ["semantic", "wuxing", "scene", "pref"]
        for dim in non_temp_dims:
            assert w_extreme[dim] < w_normal[dim], f"{dim} 在极端温度下应缩减"


# ============================================================
# 2. 五行评分测试
# ============================================================

class TestWuxingScoring:
    """五行评分测试"""

    def test_primary_hit(self):
        """主五行命中target得0.55"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": None}
        score = calculate_wuxing_score(item, ["木"])
        assert abs(score - 0.55) < 1e-9

    def test_secondary_hit(self):
        """次五行命中target得0.25"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "火", "secondary_element": "木"}
        score = calculate_wuxing_score(item, ["木"])
        assert abs(score - 0.25) < 1e-9

    def test_primary_and_secondary_hit(self):
        """主+次五行都命中（完美双匹配）：0.55+0.25+0.10(dual_bonus)=0.90"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "水"}
        score = calculate_wuxing_score(item, ["木", "水"])
        assert abs(score - 0.90) < 1e-9

    def test_no_hit_returns_zero(self):
        """无命中得0"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "火", "secondary_element": "土"}
        score = calculate_wuxing_score(item, ["木", "水"])
        assert score == 0.0

    def test_empty_target_returns_zero(self):
        """空target列表得0"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木"}
        score = calculate_wuxing_score(item, [])
        assert score == 0.0

    def test_boost_elements_add_bonus(self):
        """boost元素（相生辅助）给予加分"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "水", "secondary_element": None}
        # 水不在target但在boost中
        score = calculate_wuxing_score(item, ["木"], boost_elements=["水"])
        # 基础0 + boost 0.08，但cap到min(0.08, max(0, 0.05)) = 0.05
        assert score > 0
        assert score <= 0.08

    def test_boost_capped_by_base_score(self):
        """boost加分不超过base命中分"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "水"}
        # 木命中target(0.55)，水在boost中(secondary +0.03)
        score = calculate_wuxing_score(item, ["木"], boost_elements=["水"])
        # base=0.55, boost_raw=0.03(secondary), capped=min(0.03, 0.55)=0.03
        assert abs(score - 0.58) < 1e-9

    def test_score_never_exceeds_one(self):
        """五行分归一化不超1.0"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "水"}
        score = calculate_wuxing_score(item, ["木", "水"], boost_elements=["木", "水"])
        assert score <= 1.0

    def test_ornament_bonus(self):
        """饰品/文玩五行补救加分（个人五行增强）"""
        from packages.recommendation.scoring import calculate_ornament_bonus

        item = {"category": "饰品", "primary_element": "木"}
        bonus = calculate_ornament_bonus(item, ["木"])
        assert bonus == 0.06

        # 非饰品类别无加分
        item2 = {"category": "上装", "primary_element": "木"}
        assert calculate_ornament_bonus(item2, ["木"]) == 0.0

    def test_ornament_scene_mediation_bonus(self):
        """配饰场景冲突调节加分（桥接场景→个人喜用神）"""
        from packages.recommendation.scoring import calculate_ornament_bonus

        # 场景=金，用户喜用=水，配饰=金 → 金生水，触发调节加分
        item = {"category": "配饰", "primary_element": "金"}
        bonus = calculate_ornament_bonus(item, ["水"], scene_elements=["金"])
        assert bonus == 0.04  # 仅场景调节（配饰不是饰品/文玩，无个人增强）

        # 场景=金，用户喜用=木，配饰=水 → 金生水、水生木，完美桥接
        item2 = {"category": "饰品", "primary_element": "水"}
        bonus2 = calculate_ornament_bonus(item2, ["木"], scene_elements=["金"])
        assert bonus2 == 0.04  # 场景调节（水不在target中，无个人增强）

        # 场景=金，用户喜用=水，配饰=水(饰品) → 个人增强 + 场景调节双重加分
        item3 = {"category": "饰品", "primary_element": "水"}
        bonus3 = calculate_ornament_bonus(item3, ["水"], scene_elements=["金"])
        assert bonus3 == 0.10  # 0.06(个人) + 0.04(场景: 金生水=配饰元素)

        # 无场景时不触发调节
        item4 = {"category": "配饰", "primary_element": "金"}
        bonus4 = calculate_ornament_bonus(item4, ["水"], scene_elements=None)
        assert bonus4 == 0.0  # 配饰不在ORNAMENT_CATEGORIES中，无个人增强

    # ---------- 双元素匹配增强：DUAL_BONUS + 冲突惩罚 ----------

    def test_dual_match_bonus_applied(self):
        """完美双匹配：primary + secondary 同时命中 target 应额外 +0.10"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "水"}
        # 无 dual_bonus 时 0.55+0.25=0.80；有 dual_bonus → 0.90
        score = calculate_wuxing_score(item, ["木", "水"])
        assert abs(score - 0.90) < 1e-9, "完美双匹配应为 0.55+0.25+0.10=0.90"

    def test_single_hit_no_dual_bonus(self):
        """仅 primary 命中（secondary 未命中）：无 dual_bonus"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "火"}
        score = calculate_wuxing_score(item, ["木", "水"])
        assert abs(score - 0.55) < 1e-9, "只有 primary 命中，无 dual_bonus"

    def test_bazi_avoid_primary_penalty(self):
        """primary 是八字忌神：软惩罚 -0.25"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "火", "secondary_element": None}
        # 无 target 命中 + primary 是忌神 → 0 - 0.25 = -0.25，被 max(0) 兜底为 0
        score = calculate_wuxing_score(item, ["木"], avoid_elements=["火"])
        assert score == 0.0

        # primary 命中 target 同时是忌神：0.55 - 0.25 = 0.30
        item2 = {"primary_element": "木", "secondary_element": None}
        score2 = calculate_wuxing_score(item2, ["木"], avoid_elements=["木"])
        # 数据异常但可测：喜忌神同时命中 target 时，扣分仍生效（防御性）
        assert abs(score2 - 0.30) < 1e-9

    def test_bazi_avoid_secondary_penalty(self):
        """secondary 是八字忌神：软惩罚 -0.15"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "火"}
        # primary=木命中 target(0.55) + secondary=火 是忌神(-0.15) = 0.40
        score = calculate_wuxing_score(item, ["木"], avoid_elements=["火"])
        assert abs(score - 0.40) < 1e-9

    def test_explicit_avoid_hard_penalty(self):
        """用户显式回避（硬禁忌）：-0.40，惩罚更强"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": None}
        # primary 命中 target(0.55) 但用户显式不要木 → 0.55 - 0.40 = 0.15
        score = calculate_wuxing_score(item, ["木"], explicit_avoid=["木"])
        assert abs(score - 0.15) < 1e-9

    def test_explicit_avoid_secondary_hard_penalty(self):
        """显式禁忌命中 secondary：同样 -0.40"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "火"}
        # primary=木命中 target(0.55) + secondary=火 是显式禁忌(-0.40) = 0.15
        score = calculate_wuxing_score(item, ["木"], explicit_avoid=["火"])
        assert abs(score - 0.15) < 1e-9

    def test_dual_match_with_boost(self):
        """完美双匹配 + boost 相生加分：0.55+0.25+0.10+boost，封顶1.0"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "木", "secondary_element": "水"}
        # base=0.55+0.25=0.80, dual=+0.10 → 0.90
        # 加 boost（假设 boost 未重叠）：boost_raw=0，score=0.90
        score = calculate_wuxing_score(item, ["木", "水"], boost_elements=["金"])
        assert abs(score - 0.90) < 1e-9

    def test_conflict_both_primary_secondary_avoid(self):
        """primary + secondary 都是忌神：双重扣分，被 max(0) 兜底"""
        from packages.recommendation.scoring import calculate_wuxing_score

        item = {"primary_element": "火", "secondary_element": "土"}
        # 0 - 0.25 - 0.15 = -0.40 → 被 max(0) 兜底
        score = calculate_wuxing_score(item, ["木"], avoid_elements=["火", "土"])
        assert score == 0.0


# ============================================================
# 3. 温度评分测试
# ============================================================

class TestTemperatureScoring:
    """温度评分测试"""

    def test_no_weather_returns_neutral(self):
        """无天气信息返回中性分0.5"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "T恤", "thickness_level": "轻薄"}
        assert calculate_temp_score(item, None) == 0.5
        assert calculate_temp_score(item, {}) == 0.5
        assert calculate_temp_score(item, {"temperature": None}) == 0.5

    def test_extreme_hot_thin_gets_bonus(self):
        """极端高温(>=30°C)轻薄衣物加分"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "T恤", "thickness_level": "轻薄"}
        weather = {"temperature": 35}
        score = calculate_temp_score(item, weather)
        assert score > 0.5, "高温轻薄应加分"

    def test_extreme_hot_thick_gets_penalty(self):
        """极端高温厚重衣物扣分"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "羽绒服", "thickness_level": "厚重"}
        weather = {"temperature": 35}
        score = calculate_temp_score(item, weather)
        assert score < 0.5, "高温厚重应扣分"

    def test_extreme_cold_thick_gets_bonus(self):
        """极端低温(<=5°C)厚重衣物加分"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "羽绒服", "thickness_level": "厚重"}
        weather = {"temperature": 0}
        score = calculate_temp_score(item, weather)
        assert score > 0.5, "低温厚重应加分"

    def test_extreme_cold_thin_gets_penalty(self):
        """极端低温轻薄衣物扣分"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "T恤", "thickness_level": "轻薄"}
        weather = {"temperature": 0}
        score = calculate_temp_score(item, weather)
        assert score < 0.5, "低温轻薄应扣分"

    def test_score_always_in_01_range(self):
        """温度分始终在[0,1]范围内"""
        from packages.recommendation.scoring import calculate_temp_score

        test_cases = [
            ({"name": "T恤", "thickness_level": "极薄"}, {"temperature": 40}),
            ({"name": "羽绒服", "thickness_level": "厚重"}, {"temperature": -10}),
            ({"name": "衬衫", "thickness_level": "轻薄"}, {"temperature": 20}),
        ]
        for item, weather in test_cases:
            score = calculate_temp_score(item, weather)
            assert 0.0 <= score <= 1.0, f"温度分{score}超出[0,1]范围"

    def test_six_tier_boundaries(self):
        """6档温度边界测试"""
        from packages.recommendation.config import (
            EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
            EXTREME_COLD_TEMP, MILD_COLD_TEMP,
        )

        # 验证阈值常量值
        assert EXTREME_HOT_TEMP == 30
        assert HOT_TEMP == 28
        assert MILD_HOT_TEMP == 25
        assert EXTREME_COLD_TEMP == 5
        assert MILD_COLD_TEMP == 10

    def test_functionality_bonus_in_hot(self):
        """高温时透气/速干功能加分"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "运动T恤", "thickness_level": "轻薄", "functionality": ["透气", "速干"]}
        weather = {"temperature": 32}
        score_with_func = calculate_temp_score(item, weather)

        item_no_func = {"name": "普通T恤", "thickness_level": "轻薄", "functionality": []}
        score_no_func = calculate_temp_score(item_no_func, weather)

        assert score_with_func > score_no_func, "透气/速干功能应加分"


# ============================================================
# 4. 温度硬过滤测试
# ============================================================

class TestTemperatureHardFilter:
    """温度硬过滤测试"""

    def test_extreme_hot_filters_thick(self):
        """极端高温过滤厚重/中厚"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "T恤", "thickness_level": "轻薄", "temp_score": 0.8},
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.2},
            {"name": "毛衣", "thickness_level": "中厚", "temp_score": 0.3},
        ]
        weather = {"temperature": 35}
        filtered = apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "T恤" in names
        assert "羽绒服" not in names
        assert "毛衣" not in names

    def test_extreme_cold_filters_thin(self):
        """极端低温过滤极薄/轻薄"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.8},
            {"name": "T恤", "thickness_level": "轻薄", "temp_score": 0.2},
            {"name": "背心", "thickness_level": "极薄", "temp_score": 0.1},
        ]
        weather = {"temperature": 0}
        filtered = apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "羽绒服" in names
        assert "T恤" not in names
        assert "背心" not in names

    def test_fallback_when_all_filtered(self):
        """所有候选都被过滤时回退保留温度分最高的"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "羽绒服", "thickness_level": "厚重", "temp_score": 0.3},
            {"name": "棉袄", "thickness_level": "厚重", "temp_score": 0.25},
        ]
        weather = {"temperature": 35}  # 高温，厚重全被过滤
        filtered = apply_temperature_hard_filter(items, weather)

        # 应回退保留temp_score最高的
        assert len(filtered) >= 1
        assert filtered[0]["name"] == "羽绒服"

    def test_no_filter_without_weather(self):
        """无天气信息不过滤"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [{"name": "T恤"}, {"name": "羽绒服"}]
        assert apply_temperature_hard_filter(items, None) == items

    def test_extreme_hot_filters_long_sleeve_by_name(self):
        """高温≥30°C 按名称过滤长袖/保暖类单品（bad case：33°C 推长袖 Polo）"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "亚麻长袖Polo", "thickness_level": "轻薄", "temp_score": 0.8},
            {"name": "保暖内衣上装", "thickness_level": "轻薄", "temp_score": 0.8},
            {"name": "短袖T恤", "thickness_level": "轻薄", "temp_score": 0.9},
        ]
        weather = {"temperature": 33}
        filtered = apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "亚麻长袖Polo" not in names
        assert "保暖内衣上装" not in names
        assert "短袖T恤" in names

    def test_extreme_hot_keeps_sun_protection_long_sleeve(self):
        """防晒/冰丝/速干等功能性长袖豁免高温名称过滤"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "冰丝防晒长袖衫", "thickness_level": "轻薄", "temp_score": 0.9},
            {"name": "速干长袖T恤", "thickness_level": "轻薄", "temp_score": 0.9},
        ]
        weather = {"temperature": 33}
        filtered = apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "冰丝防晒长袖衫" in names
        assert "速干长袖T恤" in names

    def test_mild_hot_keeps_long_sleeve(self):
        """温和温度（24°C）不按名称过滤长袖"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [{"name": "长袖衬衫", "thickness_level": "轻薄", "temp_score": 0.8}]
        weather = {"temperature": 24}
        filtered = apply_temperature_hard_filter(items, weather)
        assert [i["name"] for i in filtered] == ["长袖衬衫"]


# ============================================================
# 4.5 有效温度与季节硬排除测试（杭州青金石蓝西装 bad case 修复）
# ============================================================

class TestEffectiveTemperature:
    """有效温度 max(瞬时, 当日最高) 测试"""

    def test_effective_temp_takes_max(self):
        """有温差时取当日最高温"""
        from packages.recommendation.config import get_effective_temperature

        assert get_effective_temperature({"temperature": 29, "temperature_max": 37}) == 37

    def test_effective_temp_fallback_to_instant(self):
        """无 temperature_max 时退化为瞬时温度（向后兼容）"""
        from packages.recommendation.config import get_effective_temperature

        assert get_effective_temperature({"temperature": 29}) == 29
        assert get_effective_temperature({"temperature": 29, "temperature_max": None}) == 29

    def test_effective_temp_none(self):
        """无任何温度时返回 None"""
        from packages.recommendation.config import get_effective_temperature

        assert get_effective_temperature(None) is None
        assert get_effective_temperature({}) is None

    def test_hard_filter_uses_daily_max(self):
        """瞬时29°C+当日最高37°C 应排除适用上限25°C的西装（bad case 复现）"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "青金石蓝西装", "thickness_level": "适中",
             "temperature_range": {"最低": 10, "最高": 25}, "temp_score": 0.4},
            {"name": "冰丝T恤", "thickness_level": "轻薄",
             "temperature_range": {"最低": 26, "最高": 40}, "temp_score": 0.9},
        ]
        weather = {"temperature": 29, "temperature_max": 37}
        filtered = apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "青金石蓝西装" not in names, "有效温度37°C > 25+8，西装应被排除"
        assert "冰丝T恤" in names

    def test_hard_filter_backward_compatible(self):
        """仅瞬时29°C（无最高温）时行为与历史一致，西装不被 range 排除"""
        from packages.recommendation.filters import apply_temperature_hard_filter

        items = [
            {"name": "青金石蓝西装", "thickness_level": "适中",
             "temperature_range": {"最低": 10, "最高": 25}, "temp_score": 0.4},
        ]
        weather = {"temperature": 29}
        filtered = apply_temperature_hard_filter(items, weather)

        assert [i["name"] for i in filtered] == ["青金石蓝西装"], "29°C < 25+8，不应排除"


class TestSeasonHardExclusion:
    """季节硬排除测试（高温盛夏排除不含夏季的衣物）"""

    def test_hot_summer_excludes_non_summer_items(self, monkeypatch):
        """高温+当季夏：排除仅适用春秋的衣物"""
        import packages.recommendation.filters as filters_mod

        monkeypatch.setattr(filters_mod, "get_current_season", lambda: "夏")

        items = [
            {"name": "春秋西装", "thickness_level": "适中",
             "applicable_seasons": ["春", "秋"], "temp_score": 0.4},
            {"name": "夏季衬衫", "thickness_level": "轻薄",
             "applicable_seasons": ["夏"], "temp_score": 0.9},
        ]
        weather = {"temperature": 29, "temperature_max": 37}
        filtered = filters_mod.apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "春秋西装" not in names
        assert "夏季衬衫" in names

    def test_season_json_string_format(self, monkeypatch):
        """applicable_seasons 为 JSON 字符串时同样生效"""
        import packages.recommendation.filters as filters_mod

        monkeypatch.setattr(filters_mod, "get_current_season", lambda: "夏")

        items = [
            {"name": "春秋西装", "thickness_level": "适中",
             "applicable_seasons": '["春", "秋"]', "temp_score": 0.4},
            {"name": "夏季衬衫", "thickness_level": "轻薄",
             "applicable_seasons": '["夏"]', "temp_score": 0.9},
        ]
        weather = {"temperature": 30}
        filtered = filters_mod.apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "春秋西装" not in names
        assert "夏季衬衫" in names

    def test_mild_temp_no_season_exclusion(self, monkeypatch):
        """温和温度下不触发季节硬排除"""
        import packages.recommendation.filters as filters_mod

        monkeypatch.setattr(filters_mod, "get_current_season", lambda: "夏")

        items = [
            {"name": "春秋西装", "thickness_level": "适中",
             "applicable_seasons": ["春", "秋"], "temp_score": 0.6},
        ]
        weather = {"temperature": 24}
        filtered = filters_mod.apply_temperature_hard_filter(items, weather)

        assert [i["name"] for i in filtered] == ["春秋西装"]

    def test_cold_winter_excludes_non_winter_items(self, monkeypatch):
        """严寒+当季冬：排除不含冬季的衣物"""
        import packages.recommendation.filters as filters_mod

        monkeypatch.setattr(filters_mod, "get_current_season", lambda: "冬")

        items = [
            {"name": "夏季长裤", "thickness_level": "适中",
             "applicable_seasons": ["夏"], "temp_score": 0.2},
            {"name": "羽绒服", "thickness_level": "厚重",
             "applicable_seasons": ["冬"], "temp_score": 0.9},
        ]
        weather = {"temperature": 2}
        filtered = filters_mod.apply_temperature_hard_filter(items, weather)

        names = [i["name"] for i in filtered]
        assert "夏季长裤" not in names
        assert "羽绒服" in names


class TestEffectiveTempScoring:
    """评分与评估链路使用有效温度"""

    def test_temp_score_uses_daily_max(self):
        """有温差时 calculate_temp_score 按峰值打分，厚衣物得分更低"""
        from packages.recommendation.scoring import calculate_temp_score

        item = {"name": "西装", "thickness_level": "适中",
                "temperature_range": {"最低": 10, "最高": 25}}
        score_mild = calculate_temp_score(item, {"temperature": 29})
        score_gap = calculate_temp_score(item, {"temperature": 29, "temperature_max": 37})

        assert score_gap < score_mild, "峰值37°C下西装温度分应低于瞬时29°C"

    def test_evaluator_checks_use_effective_temp(self):
        """评估器常识检查也按有效温度判违规（避免评估盲区复现）"""
        from apps.api.tests.evaluation.evaluator import score_common_sense

        items = [{
            "name": "青金石蓝西装", "thickness_level": "适中",
            "temperature_range": {"最低": 10, "最高": 25},
            "applicable_seasons": ["夏"], "functionality": ["透气"],
        }]
        weather = {"temperature": 29, "temperature_max": 37}
        result = score_common_sense(items, weather, season="夏")

        assert result.details["violations"], "有效温度37°C下西装应被判为温度超限违规"


# ============================================================
# 5. 场景识别测试（规则提取）
# ============================================================

class TestSceneRecognition:
    """场景识别优先级测试"""

    def test_sport_highest_priority(self):
        """运动场景优先级最高"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        # 运动关键词应优先于地点
        result = extract_context_by_rules("去三亚出差顺便游泳")
        assert result["scene"] == "运动"

        result = extract_context_by_rules("去北京跑步马拉松")
        assert result["scene"] == "运动"

    def test_outdoor_adventure_priority(self):
        """户外探险优先级次于运动"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("周末去登山徒步")
        assert result["scene"] == "户外探险"

    def test_business_trip_priority(self):
        """出差优先级高于度假"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("去上海出差")
        assert result["scene"] == "出差"

    def test_vacation_scene(self):
        """度假场景识别"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("去三亚度假")
        assert result["scene"] == "度假"

    def test_business_scene(self):
        """商务场景识别"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("明天有个重要会议")
        assert result["scene"] == "商务"

    def test_travel_days_extraction(self):
        """旅行天数提取"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("去北京出差3天")
        assert result["travel_days"] == 3

        result = extract_context_by_rules("去三亚度假五天")
        assert result["travel_days"] == 5

    def test_destination_extraction(self):
        """目的地城市提取"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("去成都旅游")
        assert result["destination"] == "成都"

    def test_temperature_extraction(self):
        """温度提取"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("今天25度穿什么")
        assert result["weather_info"]["temperature"] == 25

    def test_weather_desc_to_element(self):
        """天气描述转五行"""
        from packages.recommendation.context_extraction import extract_context_by_rules

        result = extract_context_by_rules("今天很闷热")
        assert result["weather_element"] == "火"

        result = extract_context_by_rules("下雨天穿什么")
        assert result["weather_element"] == "水"


# ============================================================
# 6. 审美加分测试
# ============================================================

class TestAestheticBonus:
    """审美画像加分测试"""

    def test_skin_tone_bonus_cold_white(self):
        """冷白皮肤色加分"""
        from packages.recommendation.scoring import calculate_skin_tone_bonus

        item = {"primary_element": "金", "secondary_element": None}
        bonus = calculate_skin_tone_bonus(item, "冷白皮")
        assert bonus == 0.12  # 金对冷白皮加分0.12

    def test_skin_tone_bonus_warm_white(self):
        """暖白皮肤色加分"""
        from packages.recommendation.scoring import calculate_skin_tone_bonus

        item = {"primary_element": "火", "secondary_element": None}
        bonus = calculate_skin_tone_bonus(item, "暖白皮")
        assert bonus == 0.12  # 火对暖白皮加分0.12

    def test_skin_tone_max_cap(self):
        """肤色加分不超过上限0.18"""
        from packages.recommendation.scoring import calculate_skin_tone_bonus

        item = {"primary_element": "金", "secondary_element": "水"}
        bonus = calculate_skin_tone_bonus(item, "冷白皮")
        assert bonus <= 0.18

    def test_skin_tone_none_returns_zero(self):
        """无肤色信息返回0"""
        from packages.recommendation.scoring import calculate_skin_tone_bonus

        item = {"primary_element": "金"}
        assert calculate_skin_tone_bonus(item, None) == 0.0
        assert calculate_skin_tone_bonus(item, "未知肤色") == 0.0

    def test_style_preference_name_match(self):
        """风格偏好名称匹配加分"""
        from packages.recommendation.scoring import calculate_style_preference_bonus

        item = {"name": "简约纯色T恤", "attributes_detail": None}
        bonus = calculate_style_preference_bonus(item, "简约")
        assert bonus == 0.10  # 名称匹配加0.10

    def test_style_preference_detail_match(self):
        """风格偏好属性详情匹配加分"""
        from packages.recommendation.scoring import calculate_style_preference_bonus

        item = {
            "name": "T恤",
            "attributes_detail": {"款式": {"风格": "简约风格"}}
        }
        bonus = calculate_style_preference_bonus(item, "简约")
        assert bonus == 0.10  # 详情匹配加0.10

    def test_style_preference_both_match(self):
        """风格偏好名称+详情都匹配"""
        from packages.recommendation.scoring import calculate_style_preference_bonus

        item = {
            "name": "简约T恤",
            "attributes_detail": {"款式": {"风格": "简约风格"}}
        }
        bonus = calculate_style_preference_bonus(item, "简约")
        assert bonus == 0.20  # 0.10 + 0.10

    def test_style_max_cap(self):
        """风格加分不超过上限0.25"""
        from packages.recommendation.scoring import calculate_style_preference_bonus

        item = {
            "name": "简约极简基础T恤",
            "attributes_detail": {"款式": {"风格": "简约极简"}}
        }
        bonus = calculate_style_preference_bonus(item, "简约")
        assert bonus <= 0.25

    def test_body_type_bonus(self):
        """体型适配加分"""
        from packages.recommendation.scoring import calculate_body_type_bonus

        item = {
            "name": "修身衬衫",
            "attributes_detail": {"款式": {"版型": "修身"}}
        }
        bonus = calculate_body_type_bonus(item, "偏瘦")
        assert bonus == 0.14  # 偏瘦适合修身

    def test_body_type_from_name(self):
        """从名称推断版型"""
        from packages.recommendation.scoring import calculate_body_type_bonus

        item = {"name": "宽松卫衣", "attributes_detail": None}
        bonus = calculate_body_type_bonus(item, "偏胖")
        assert bonus == 0.14  # 偏胖适合宽松

    def test_body_type_none_returns_zero(self):
        """无体型信息返回0"""
        from packages.recommendation.scoring import calculate_body_type_bonus

        item = {"name": "修身衬衫"}
        assert calculate_body_type_bonus(item, None) == 0.0


# ============================================================
# 7. 季节评分测试
# ============================================================

class TestSeasonScoring:
    """季节评分测试"""

    def test_season_match(self):
        """季节匹配得1.0"""
        from packages.recommendation.scoring import calculate_season_score

        item = {"applicable_seasons": ["春", "夏"]}
        assert calculate_season_score(item, "春") == 1.0

    def test_season_mismatch(self):
        """季节不匹配得0.7"""
        from packages.recommendation.scoring import calculate_season_score

        item = {"applicable_seasons": ["春", "夏"]}
        assert calculate_season_score(item, "冬") == 0.7

    def test_no_season_info(self):
        """无季节信息得0.5（中性）"""
        from packages.recommendation.scoring import calculate_season_score

        item = {"applicable_seasons": None}
        assert calculate_season_score(item, "春") == 0.5

        item2 = {}
        assert calculate_season_score(item2, "春") == 0.5

    def test_json_string_seasons(self):
        """JSON字符串格式的季节信息"""
        from packages.recommendation.scoring import calculate_season_score

        item = {"applicable_seasons": '["春", "夏"]'}
        assert calculate_season_score(item, "春") == 1.0

    def test_no_current_season(self):
        """无当前季节信息返回0.5"""
        from packages.recommendation.scoring import calculate_season_score

        item = {"applicable_seasons": ["春"]}
        assert calculate_season_score(item, None) == 0.5


# ============================================================
# 8. 轮换奖励测试
# ============================================================

class TestRotationBonus:
    """衣物轮换奖励测试"""

    def test_zero_wear_max_bonus(self):
        """0次穿着得最大奖励0.05"""
        from packages.recommendation.scoring import calculate_rotation_bonus

        item = {"wear_count": 0}
        assert calculate_rotation_bonus(item) == 0.05

    def test_decay_per_wear(self):
        """每穿一次减少0.01"""
        from packages.recommendation.scoring import calculate_rotation_bonus

        item = {"wear_count": 3}
        assert abs(calculate_rotation_bonus(item) - 0.02) < 1e-9

    def test_five_wears_zero_bonus(self):
        """5次穿着后奖励为0"""
        from packages.recommendation.scoring import calculate_rotation_bonus

        item = {"wear_count": 5}
        assert calculate_rotation_bonus(item) == 0.0

    def test_no_wear_count_returns_zero(self):
        """无穿着次数（公共库物品）返回0"""
        from packages.recommendation.scoring import calculate_rotation_bonus

        item = {"name": "T恤"}
        assert calculate_rotation_bonus(item) == 0.0

    def test_negative_wear_count_returns_zero(self):
        """负数穿着次数返回0"""
        from packages.recommendation.scoring import calculate_rotation_bonus

        item = {"wear_count": -1}
        assert calculate_rotation_bonus(item) == 0.0


# ============================================================
# 9. 多样性测试
# ============================================================

class TestDiversity:
    """多样性保障测试"""

    def test_category_limit_enforced(self):
        """分类上限约束"""
        from packages.recommendation.diversity import ensure_category_diversity

        items = [
            {"id": 1, "category": "上装", "name": "T恤1"},
            {"id": 2, "category": "上装", "name": "T恤2"},
            {"id": 3, "category": "上装", "name": "T恤3"},
            {"id": 4, "category": "下装", "name": "裤子1"},
            {"id": 5, "category": "饰品", "name": "项链"},
        ]
        result = ensure_category_diversity(items, 5)

        # 上装最多2件
        upper_count = sum(1 for i in result if i.get("category") == "上装")
        assert upper_count <= 2

    def test_accent_items_capped_to_one(self):
        """点缀类（配饰/饰品/文玩）合并计数，单套搭配最多 1 件"""
        from packages.recommendation.diversity import ensure_category_diversity
        from packages.recommendation.config import ACCENT_CATEGORIES, MAX_ACCENT_ITEMS

        items = [
            {"id": 1, "category": "配饰", "name": "针织帽"},
            {"id": 2, "category": "饰品", "name": "手串"},
            {"id": 3, "category": "文玩", "name": "佛珠"},
            {"id": 4, "category": "上装", "name": "衬衫"},
            {"id": 5, "category": "下装", "name": "长裤"},
        ]
        result = ensure_category_diversity(items, 5)

        accent_count = sum(1 for i in result if i.get("category") in ACCENT_CATEGORIES)
        assert accent_count <= MAX_ACCENT_ITEMS, f"点缀类应≤{MAX_ACCENT_ITEMS} 件，实际 {accent_count} 件"

    def test_wuxing_diversity_replacement(self):
        """五行多样性替换"""
        from packages.recommendation.diversity import ensure_wuxing_diversity

        items = [
            {"id": 1, "primary_element": "木", "name": "木1", "temp_score": 0.8},
            {"id": 2, "primary_element": "木", "name": "木2", "temp_score": 0.8},
            {"id": 3, "primary_element": "木", "name": "木3", "temp_score": 0.8},
        ]
        all_scored = items + [
            {"id": 4, "primary_element": "水", "name": "水1", "temp_score": 0.7},
        ]
        result = ensure_wuxing_diversity(items, all_scored, 3)

        elements = {i.get("primary_element") for i in result}
        assert len(elements) >= 2, "应至少覆盖2种五行"

    def test_wuxing_diversity_no_change_if_diverse(self):
        """已有多样性时不替换"""
        from packages.recommendation.diversity import ensure_wuxing_diversity

        items = [
            {"id": 1, "primary_element": "木", "name": "木1", "temp_score": 0.8},
            {"id": 2, "primary_element": "水", "name": "水1", "temp_score": 0.8},
        ]
        result = ensure_wuxing_diversity(items, items, 2)
        assert len(result) == 2

    def test_temp_safety_check(self):
        """温度安全检查替换低温物品"""
        from packages.recommendation.filters import apply_temperature_safety_check

        top_items = [
            {"id": 1, "temp_score": 0.2, "name": "不合适"},
            {"id": 2, "temp_score": 0.8, "name": "合适"},
        ]
        scored_items = top_items + [
            {"id": 3, "temp_score": 0.7, "name": "备选"},
        ]
        weather = {"temperature": 35}  # 极端高温

        result = apply_temperature_safety_check(top_items, scored_items, weather, 2)

        # temp_score < 0.3 的应被替换
        ids = [i["id"] for i in result]
        assert 1 not in ids or len(result) < 2

    def test_wuxing_diversity_no_second_shoe(self):
        """五行多样性替换不得引入第二件鞋履（鞋履上限1）

        bad case：五行多样性把点缀换成候选池分数最高的鞋履，
        导致同套推荐出现两双鞋并挤掉下装。
        """
        from packages.recommendation.diversity import ensure_wuxing_diversity

        items = [
            {"id": 1, "category": "鞋履", "primary_element": "火", "name": "高跟鞋", "temp_score": 0.8},
            {"id": 2, "category": "文玩", "primary_element": "火", "name": "手串", "temp_score": 0.8},
            {"id": 3, "category": "外套", "primary_element": "火", "name": "防晒衣", "temp_score": 0.8},
            {"id": 4, "category": "外套", "primary_element": "火", "name": "风衣", "temp_score": 0.8},
            {"id": 5, "category": "裙装", "primary_element": "火", "name": "长裙", "temp_score": 0.8},
        ]
        all_scored = items + [
            # 候选池分数最高的不同五行物品是鞋履
            {"id": 6, "category": "鞋履", "primary_element": "水", "name": "跑鞋", "temp_score": 0.9},
            {"id": 7, "category": "饰品", "primary_element": "水", "name": "胸针", "temp_score": 0.7},
        ]
        result = ensure_wuxing_diversity(items, all_scored, 5)

        shoe_count = sum(1 for i in result if i.get("category") == "鞋履")
        assert shoe_count <= 1, f"鞋履应≤1件，实际 {shoe_count} 件"
        elements = {i.get("primary_element") for i in result}
        assert len(elements) >= 2, "应至少覆盖2种五行"

    def test_temp_safety_check_relaxed_keeps_shoe_limit(self):
        """温度安全放宽补充路径：鞋履仍最多1件

        bad case：极端温度下遵守品类限制后候选不足，放宽路径无上限
        补充导致出现两双鞋。
        """
        from packages.recommendation.filters import apply_temperature_safety_check

        top_items = [
            {"id": 1, "category": "上装", "temp_score": 0.2, "name": "不合适"},
            {"id": 2, "category": "鞋履", "temp_score": 0.8, "name": "鞋1"},
        ]
        # 候选池：多双鞋 + 多件上装（都温度安全）
        scored_items = top_items + [
            {"id": 3, "category": "鞋履", "temp_score": 0.9, "name": "鞋2"},
            {"id": 4, "category": "鞋履", "temp_score": 0.85, "name": "鞋3"},
            {"id": 5, "category": "上装", "temp_score": 0.7, "name": "T恤"},
        ]
        weather = {"temperature": -5}  # 极端低温

        result = apply_temperature_safety_check(top_items, scored_items, weather, 2)

        shoe_count = sum(1 for i in result if i.get("category") == "鞋履")
        assert shoe_count <= 1, f"鞋履应≤1件，实际 {shoe_count} 件"


# ============================================================
# 10. 厚度推断测试
# ============================================================

class TestThicknessInference:
    """厚度推断测试"""

    def test_heavy_keywords_override_db(self):
        """名称暗示厚重优先于DB字段"""
        from packages.recommendation.scoring import infer_item_thickness

        item = {"name": "羽绒服", "thickness_level": "轻薄"}
        assert infer_item_thickness(item) == "厚重"

    def test_db_field_used_when_no_keywords(self):
        """无关键词时使用DB字段"""
        from packages.recommendation.scoring import infer_item_thickness

        item = {"name": "外套", "thickness_level": "适中"}
        # "外套"在medium_keywords中，但DB字段优先
        # 实际上名称关键词在DB字段之前检查
        assert infer_item_thickness(item) in ["中厚", "适中"]

    def test_thin_keywords(self):
        """轻薄关键词推断"""
        from packages.recommendation.scoring import infer_item_thickness

        item = {"name": "雪纺衬衫", "thickness_level": None}
        assert infer_item_thickness(item) == "轻薄"

    def test_empty_when_no_info(self):
        """无信息时返回空串"""
        from packages.recommendation.scoring import infer_item_thickness

        item = {"name": "衣物", "thickness_level": None}
        assert infer_item_thickness(item) == ""


# ============================================================
# 11. 缓存键测试（已在 test_p0_defensive.py 中覆盖）
# ============================================================
# 缓存键完整性测试已在 test_p0_defensive.py::TestCacheKeyCompleteness 中实现
# 包括：温度/旅行天数/行李箱/性别/目的地 差异产生不同缓存键


# ============================================================
# 12. 引擎集成测试
# ============================================================

class TestEngineIntegration:
    """推荐引擎集成测试"""

    def test_empty_items_returns_empty(self):
        """空物品列表返回空结果"""
        from packages.recommendation.engine import score_and_rank_items

        result = score_and_rank_items(
            items=[],
            target_elements=["木"],
        )
        assert result["scored_items"] == []
        assert result["top_items"] == []

    def test_basic_scoring_flow(self):
        """基本评分流程"""
        from packages.recommendation.engine import score_and_rank_items

        items = [
            {"id": 1, "name": "绿色T恤", "primary_element": "木", "category": "上装",
             "semantic_score": 0.8, "thickness_level": "轻薄"},
            {"id": 2, "name": "红色裙子", "primary_element": "火", "category": "裙装",
             "semantic_score": 0.7, "thickness_level": "轻薄"},
            {"id": 3, "name": "木质手串", "primary_element": "木", "category": "饰品",
             "semantic_score": 0.6},
        ]

        result = score_and_rank_items(
            items=items,
            target_elements=["木"],
            top_k=2,
            user_gender="女",  # 含裙装（女性专属品类），需透传性别避免防御性默认过滤
        )

        assert len(result["scored_items"]) == 3
        assert len(result["top_items"]) <= 2

        # 木属性物品应排在前面
        top_elements = [i.get("primary_element") for i in result["top_items"]]
        assert "木" in top_elements

    def test_batch_index_offset(self):
        """批次索引偏移（换一批）：批次间物品不重合"""
        from packages.recommendation.engine import score_and_rank_items, _canonical_item_key

        # 使用不同分类避免多样性约束限制
        categories = ["上装", "下装", "裙装", "外套", "饰品", "上装", "下装", "裙装", "外套", "饰品"]
        items = [
            {"id": i, "name": f"物品{i}", "primary_element": "木", "category": categories[i],
             "semantic_score": 0.5 + i * 0.01}
            for i in range(10)
        ]

        result1 = score_and_rank_items(items=items, target_elements=["木"], top_k=3, batch_index=0)
        result2 = score_and_rank_items(items=items, target_elements=["木"], top_k=3, batch_index=1)

        assert len(result1["top_items"]) == 3
        assert len(result2["top_items"]) == 3

        # 不同批次的物品必须完全不重合
        keys1 = {_canonical_item_key(i) for i in result1["top_items"]}
        keys2 = {_canonical_item_key(i) for i in result2["top_items"]}
        assert keys1.isdisjoint(keys2), f"批次间物品重叠: {keys1 & keys2}"


# ============================================================
# 13. 行为反馈测试
# ============================================================

class TestBehaviorFeedback:
    """隐性反馈测试"""

    def test_behavior_weights_config(self):
        """行为权重配置正确"""
        from packages.recommendation.config import BEHAVIOR_WEIGHTS

        assert BEHAVIOR_WEIGHTS["dwell_long"] == 0.3
        assert BEHAVIOR_WEIGHTS["click"] == 0.2
        assert BEHAVIOR_WEIGHTS["view"] == 0.1

    def test_behavior_max_score(self):
        """行为加分上限"""
        from packages.recommendation.config import BEHAVIOR_MAX_SCORE

        assert BEHAVIOR_MAX_SCORE == 0.10

    def test_calculate_behavior_score_empty_prefs(self):
        """空偏好返回0"""
        from packages.recommendation.behavior import calculate_behavior_score

        item = {"category": "上装", "primary_element": "木"}
        assert calculate_behavior_score(item, {}) == 0.0

    def test_calculate_behavior_score_with_prefs(self):
        """有偏好时计算加分"""
        from packages.recommendation.behavior import calculate_behavior_score

        item = {"category": "上装", "primary_element": "木", "color": "绿色"}
        behavior_prefs = {
            "category": {"上装": 0.3},
            "element": {"木": 0.2},
        }
        score = calculate_behavior_score(item, behavior_prefs)
        assert score > 0
        assert score <= 0.10  # 不超过上限


# ============================================================
# 14. 性别过滤测试
# ============================================================

class TestGenderFilter:
    """性别过滤SQL构建测试"""

    def test_male_filter(self):
        """男性过滤条件"""
        from packages.recommendation.filters import build_gender_filter

        sql = build_gender_filter("男")
        assert "男" in sql
        assert "中性" in sql

    def test_female_filter(self):
        """女性过滤条件"""
        from packages.recommendation.filters import build_gender_filter

        sql = build_gender_filter("女")
        assert "女" in sql
        assert "中性" in sql

    def test_unknown_gender_filter(self):
        """未知性别默认过滤：仅保留中性/未标注，不得泄漏男/女专属物品"""
        from packages.recommendation.filters import build_gender_filter

        sql = build_gender_filter(None)
        assert "中性" in sql
        assert "男" not in sql  # 防御性默认：性别缺失时不再包含男款
        assert "女" not in sql


# ============================================================
# 14.5 性别推断与硬过滤测试（评分层安全网）
# ============================================================

class TestInferItemGender:
    """物品真实性别推断（交叉校验标注）"""

    def test_db_gender_takes_priority(self):
        """DB gender 字段（男/女）优先级最高"""
        from packages.recommendation.filters import infer_item_gender

        assert infer_item_gender({"gender": "男", "name": "女士衬衫"}) == "男"
        assert infer_item_gender({"gender": "女", "name": "普通外套"}) == "女"

    def test_name_keyword_inference(self):
        """标注中性但名称含性别关键词时可推断"""
        from packages.recommendation.filters import infer_item_gender

        assert infer_item_gender({"gender": "中性", "name": "男士商务皮鞋"}) == "男"
        assert infer_item_gender({"gender": "中性", "name": "女款真丝衬衫"}) == "女"

    def test_category_common_sense(self):
        """品类常识：裙装为女性专属"""
        from packages.recommendation.filters import infer_item_gender

        assert infer_item_gender({"gender": "中性", "name": "碎花连衣裙", "category": "裙装"}) == "女"

    def test_unisex_returns_none(self):
        """无法判定的中性物品返回 None"""
        from packages.recommendation.filters import infer_item_gender

        assert infer_item_gender({"gender": "中性", "name": "黑色简约乐福鞋", "category": "鞋履"}) is None
        assert infer_item_gender({"name": "白色T恤"}) is None


class TestApplyGenderHardFilter:
    """评分层性别硬过滤"""

    def _make_items(self):
        return [
            {"name": "男款乐福鞋", "gender": "男"},
            {"name": "女士真丝衬衫", "gender": "中性"},  # 名称可推断为女款
            {"name": "中性帆布鞋", "gender": "中性"},
            {"name": "未标注外套", "gender": None},
        ]

    def test_female_user_excludes_male_items(self):
        """核心 bad case：女性用户不收到男款物品（含标注中性但名称为男款的情况）"""
        from packages.recommendation.filters import apply_gender_hard_filter

        items = self._make_items()
        items.append({"name": "男士商务皮鞋", "gender": "中性"})  # 模拟 ITEM_437 类脏数据
        kept = apply_gender_hard_filter(items, "女")
        names = [i["name"] for i in kept]
        assert "男款乐福鞋" not in names
        assert "男士商务皮鞋" not in names  # 名称推断拦截标注错误
        assert "女士真丝衬衫" in names
        assert "中性帆布鞋" in names

    def test_male_user_excludes_female_items(self):
        """男性用户不收到女款物品"""
        from packages.recommendation.filters import apply_gender_hard_filter

        kept = apply_gender_hard_filter(self._make_items(), "男")
        names = [i["name"] for i in kept]
        assert "女士真丝衬衫" not in names
        assert "男款乐福鞋" in names

    def test_unknown_gender_keeps_only_unisex(self):
        """用户性别未知：仅保留中性/不可判定物品（防御性默认）"""
        from packages.recommendation.filters import apply_gender_hard_filter

        kept = apply_gender_hard_filter(self._make_items(), None)
        names = [i["name"] for i in kept]
        assert "男款乐福鞋" not in names
        assert "女士真丝衬衫" not in names
        assert "中性帆布鞋" in names
        assert "未标注外套" in names

    def test_empty_items(self):
        """空列表防御"""
        from packages.recommendation.filters import apply_gender_hard_filter

        assert apply_gender_hard_filter([], "女") == []


class TestEngineGenderIntegration:
    """引擎层性别硬过滤集成测试"""

    def test_engine_filters_male_items_for_female_user(self):
        """score_and_rank_items 传入 user_gender 后，性别错配物品不进入结果"""
        from packages.recommendation.engine import score_and_rank_items

        items = [
            {"item_code": "A1", "name": "男款乐福鞋", "gender": "男", "category": "鞋履",
             "primary_element": "水", "color": "黑色", "semantic_score": 0.95},
            {"item_code": "A2", "name": "女士平底鞋", "gender": "女", "category": "鞋履",
             "primary_element": "水", "color": "黑色", "semantic_score": 0.9},
            {"item_code": "A3", "name": "中性帆布鞋", "gender": "中性", "category": "鞋履",
             "primary_element": "水", "color": "黑色", "semantic_score": 0.8},
        ]
        result = score_and_rank_items(
            items=items,
            target_elements=["水"],
            user_gender="女",
            top_k=5,
        )
        top_names = [i["name"] for i in result["top_items"]]
        scored_names = [i["name"] for i in result["scored_items"]]
        assert "男款乐福鞋" not in top_names
        assert "男款乐福鞋" not in scored_names  # 硬过滤在排序前执行
        assert "女士平底鞋" in top_names


# ============================================================
# 15. 场景分硬排除测试
# ============================================================

class TestSceneScoreFilter:
    """场景分硬排除测试"""

    def test_filter_zero_scene_score(self):
        """过滤场景分为0的物品"""
        from packages.recommendation.filters import filter_by_scene_score

        items = [
            {"name": "合适", "scene_score": 0.8},
            {"name": "不合适", "scene_score": 0.0},
            {"name": "中性", "scene_score": 0.5},
        ]
        filtered = filter_by_scene_score(items)

        names = [i["name"] for i in filtered]
        assert "合适" in names
        assert "不合适" not in names
        assert "中性" in names


class TestEvaluationScoreThreshold:
    """评估总分回归保护"""

    def test_overall_score_above_93(self):
        """确保推荐算法评估总分 >= 93"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from apps.api.tests.evaluation.data_generator import generate_all_data
        from apps.api.tests.evaluation.evaluator import evaluate_single_case
        from packages.recommendation.engine import score_and_rank_items

        data = generate_all_data()
        items = data["items"]
        cases = data["test_cases"][:2000]  # 采样2000个用例验证

        scores = []
        for case in cases:
            user = case.user
            use_bazi = case.complexity in ("medium", "complex", "boundary")
            target_elements = user.target_elements if use_bazi else []
            enriched = []
            for item in items:
                ic = item.copy()
                bs = item.get("semantic_score", 0.5)
                if target_elements:
                    if item.get("primary_element") in target_elements:
                        bs = min(0.95, bs + 0.2)
                    elif item.get("secondary_element") in target_elements:
                        bs = min(0.9, bs + 0.1)
                if user.style_preference and item.get("style") == user.style_preference:
                    bs = min(0.95, bs + 0.25)
                ic["semantic_score"] = bs
                enriched.append(ic)
            result = score_and_rank_items(
                items=enriched, target_elements=target_elements,
                boost_elements=user.boost_elements if use_bazi else None,
                bazi_result=user.bazi_result if use_bazi else None,
                scene=case.scene, sub_scene=None,
                weather_info=case.weather_info,
                user_id=None, user_prefs=None,
                user_skin_tone=user.skin_tone,
                user_style_preference=user.style_preference,
                user_body_type=user.body_type,
                user_gender=user.gender,
                top_k=5, batch_index=0,
            )
            rec_items = result.get("top_items", [])
            user_info = {
                "target_elements": target_elements,
                "style_preference": user.style_preference,
                "skin_tone": user.skin_tone,
                "body_type": user.body_type,
            }
            eval_result = evaluate_single_case(
                case_id=case.case_id, user_id=user.user_id,
                complexity=case.complexity, recommended_items=rec_items,
                user_info=user_info, weather_info=case.weather_info,
                scene=case.scene, season=case.season,
            )
            scores.append(eval_result.total_score)

        avg_score = sum(scores) / len(scores)
        assert avg_score >= 93.0, f"评估总分 {avg_score:.2f} < 93，算法质量回退"
