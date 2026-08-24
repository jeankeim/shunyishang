"""
场景-功能不匹配回归测试（用户反馈 #9）

收录朋友体验反馈中的具体 bad case，防止推荐权重规则调整后回归：
1. 「健身」场景推荐「木戒指」→ 运动场景必须排除饰品/文玩类
2. 「气温 33°C」推荐「长袖上衣」→ 高温区间必须拦截长袖/保暖类单品
3. 仅输入地点无出行日期 → 不提取行程、不生成天气预判
4. 未提及旅行/出差关键词 → 不输出行程规划结构化内容
"""

import pytest

from packages.utils.scene_mapping import get_scene_rules
from packages.recommendation.filters import (
    apply_scene_hard_filter,
    apply_temperature_hard_filter,
    is_hot_unfit_item,
)
from packages.recommendation.context_extraction import (
    extract_context_by_rules,
    has_travel_intent,
    has_date_signal,
)


class TestSportSceneExcludesAccessories:
    """Bad case：健身场景推荐木戒指"""

    def test_sport_scene_excludes_jewelry_categories(self):
        """运动场景规则必须排除饰品/文玩/配饰品类"""
        rules = get_scene_rules("运动")
        assert rules is not None
        excluded = set(rules.get("excluded_categories", []))
        assert "饰品" in excluded
        assert "文玩" in excluded
        assert "配饰" in excluded

    def test_scene_hard_filter_removes_wooden_ring(self):
        """场景硬过滤在评分层拦截健身场景下的木戒指"""
        scored = [
            {"name": "木戒指", "category": "饰品", "final_score": 90},
            {"name": "速干短袖", "category": "上装", "final_score": 85},
            {"name": "运动短裤", "category": "下装", "final_score": 84},
        ]
        kept = apply_scene_hard_filter(scored, "运动")
        kept_names = [it["name"] for it in kept]
        assert "木戒指" not in kept_names
        assert "速干短袖" in kept_names
        assert "运动短裤" in kept_names

    def test_scene_hard_filter_no_scene_keeps_all(self):
        """无场景时不做过滤，避免误伤通用推荐"""
        scored = [{"name": "木戒指", "category": "饰品", "final_score": 90}]
        assert apply_scene_hard_filter(scored, None) == scored

    def test_scene_hard_filter_removes_excluded_keywords(self):
        """运动场景排除西装等关键词类单品"""
        scored = [
            {"name": "黑色西装外套", "category": "外套", "final_score": 88},
            {"name": "透气跑步鞋", "category": "鞋履", "final_score": 86},
        ]
        kept = apply_scene_hard_filter(scored, "运动")
        kept_names = [it["name"] for it in kept]
        assert "黑色西装外套" not in kept_names
        assert "透气跑步鞋" in kept_names


class TestHotTemperatureLongSleeveFilter:
    """Bad case：气温 33°C 推荐长袖上衣"""

    def test_long_sleeve_unfit_at_33c(self):
        assert is_hot_unfit_item({"name": "白色长袖上衣"}, 33) is True

    def test_long_sleeve_fit_at_25c(self):
        """25°C 未达高温阈值，长袖不应被拦截"""
        assert is_hot_unfit_item({"name": "白色长袖上衣"}, 25) is False

    def test_sun_protection_long_sleeve_exempt(self):
        """防晒类长袖是合理夏季单品，豁免拦截"""
        assert is_hot_unfit_item({"name": "冰丝防晒长袖外套"}, 33) is False

    def test_temperature_hard_filter_blocks_long_sleeve_at_33c(self):
        """温度硬过滤在高温区间剔除长袖类单品"""
        items = [
            {"name": "加厚长袖毛衣", "category": "上装", "applicable_seasons": ["秋", "冬"]},
            {"name": "纯棉短袖T恤", "category": "上装", "applicable_seasons": ["夏"]},
        ]
        kept = apply_temperature_hard_filter(items, {"temperature": 33})
        kept_names = [it["name"] for it in kept]
        assert "加厚长袖毛衣" not in kept_names
        assert "纯棉短袖T恤" in kept_names


class TestTravelIntentGating:
    """Bad case：无旅行关键词仍输出 3 天行程规划；仅地点无日期强行生成天气"""

    def test_travel_intent_keywords(self):
        assert has_travel_intent("去北京出差3天") is True
        assert has_travel_intent("下周去三亚旅游") is True
        assert has_travel_intent("明天面试穿什么") is False
        assert has_travel_intent("今天33度穿什么") is False

    def test_no_travel_keyword_no_itinerary(self):
        """无旅行关键词的 Query 不提取天数/目的地，不触发行程规划"""
        result = extract_context_by_rules("明天面试穿什么比较好")
        assert result["travel_days"] is None
        assert result["destination"] is None

    def test_plain_scene_query_no_itinerary(self):
        """普通场景 Query 不应误出行程规划"""
        result = extract_context_by_rules("周末约会穿什么")
        assert result["travel_days"] is None
        assert result["destination"] is None

    def test_date_signal_detection(self):
        assert has_date_signal("明天去北京出差") is True
        assert has_date_signal("8月28日去三亚") is True
        assert has_date_signal("下周一去上海") is True
        assert has_date_signal("去北京出差") is False

    def test_location_only_without_date_not_confirmed(self):
        """「北京三天行程」有旅行意图但无日期信号：不确认日期，天气不预判"""
        result = extract_context_by_rules("北京三天行程")
        assert result["travel_days"] == 3
        assert result["travel_date_confirmed"] is False

    def test_travel_without_date_signal_not_confirmed(self):
        """有目的地的旅行 Query 无日期信号时同样不确认日期"""
        result = extract_context_by_rules("去北京玩三天")
        assert result["travel_days"] == 3
        assert result["destination"] == "北京"
        assert result["travel_date_confirmed"] is False

    def test_with_date_signal_confirmed(self):
        """包含明确日期信号时 weather 预判可生成"""
        result = extract_context_by_rules("明天去北京出差3天")
        assert result["travel_days"] == 3
        assert result["travel_date_confirmed"] is True

    def test_existing_travel_cases_not_broken(self):
        """回归保障：既有旅行用例不受门控影响"""
        result = extract_context_by_rules("去三亚玩5天")
        assert result["travel_days"] == 5
