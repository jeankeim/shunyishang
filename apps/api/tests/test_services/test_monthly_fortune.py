"""
月度运势穿搭建议服务测试
"""

import pytest

from apps.api.services.monthly_fortune_service import (
    calculate_monthly_fortune,
    generate_monthly_outfit_strategy,
    calculate_yearly_fortune,
    _get_month_ganzhi,
    _analyze_month_elements,
    _generate_yearly_advice,
)


@pytest.fixture
def sample_user_bazi():
    """测试用用户八字"""
    return {
        "day_master": "土",
        "suggested_elements": ["火", "土"],
        "avoid_elements": ["木", "水"],
        "pillars": {
            "year": "甲子",
            "month": "丙寅",
            "day": "戊午",
            "hour": "庚申",
        },
        "eight_chars": ["甲", "子", "丙", "寅", "戊", "午", "庚", "申"],
        "gender": "男",
    }


@pytest.fixture
def sample_user_bazi_water():
    """水日元测试八字"""
    return {
        "day_master": "水",
        "suggested_elements": ["金", "水"],
        "avoid_elements": ["土", "火"],
        "pillars": {
            "year": "壬子",
            "month": "辛亥",
            "day": "壬子",
            "hour": "癸丑",
        },
        "eight_chars": ["壬", "子", "辛", "亥", "壬", "子", "癸", "丑"],
        "gender": "女",
    }


# ============================================================
# 月度干支获取测试
# ============================================================

class TestMonthGanzhi:
    """月柱干支获取测试"""

    def test_get_month_ganzhi_returns_tuple(self):
        """返回天干地支元组"""
        tg, dz = _get_month_ganzhi(2025, 6)
        assert isinstance(tg, str)
        assert isinstance(dz, str)
        assert len(tg) == 1
        assert len(dz) == 1

    def test_get_month_ganzhi_different_months(self):
        """不同月份干支不同"""
        tg1, dz1 = _get_month_ganzhi(2025, 1)
        tg2, dz2 = _get_month_ganzhi(2025, 7)
        assert (tg1, dz1) != (tg2, dz2)


# ============================================================
# 月度运势计算测试
# ============================================================

class TestMonthlyFortune:
    """月度运势计算测试"""

    def test_monthly_fortune_structure(self, sample_user_bazi):
        """月度运势结构完整性"""
        result = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        assert result["year"] == 2025
        assert result["month"] == 6
        assert "month_ganzhi" in result
        assert "scores" in result
        assert "overall_score" in result
        assert "element_analysis" in result
        assert "outfit_strategy" in result

    def test_monthly_fortune_scores_range(self, sample_user_bazi):
        """五维度评分在0-100范围"""
        result = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        for dim in ["career", "wealth", "love", "health", "study"]:
            assert dim in result["scores"]
            assert 0 <= result["scores"][dim] <= 100

    def test_monthly_fortune_overall_score(self, sample_user_bazi):
        """综合评分为五维度均值"""
        result = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        expected = int(sum(result["scores"].values()) / len(result["scores"]))
        assert result["overall_score"] == expected

    def test_monthly_fortune_different_months(self, sample_user_bazi):
        """不同月份运势不同"""
        r1 = calculate_monthly_fortune(sample_user_bazi, 2025, 1)
        r2 = calculate_monthly_fortune(sample_user_bazi, 2025, 7)
        assert r1["month_ganzhi"] != r2["month_ganzhi"]

    def test_monthly_fortune_element_analysis(self, sample_user_bazi):
        """五行分析结构"""
        result = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        ea = result["element_analysis"]
        assert "strong_elements" in ea
        assert "weak_elements" in ea
        assert "season_element" in ea
        assert "month_tg_element" in ea
        assert "month_dz_element" in ea

    def test_monthly_fortune_deterministic(self, sample_user_bazi):
        """同用户同月结果确定"""
        r1 = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        r2 = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        assert r1["scores"] == r2["scores"]

    def test_monthly_fortune_water_master(self, sample_user_bazi_water):
        """水日元月度运势"""
        result = calculate_monthly_fortune(sample_user_bazi_water, 2025, 3)
        assert result["year"] == 2025
        assert len(result["scores"]) == 5

    def test_monthly_fortune_all_months(self, sample_user_bazi):
        """12个月都能计算"""
        for month in range(1, 13):
            result = calculate_monthly_fortune(sample_user_bazi, 2025, month)
            assert result["month"] == month
            assert len(result["scores"]) == 5


# ============================================================
# 穿搭策略测试
# ============================================================

class TestOutfitStrategy:
    """穿搭策略生成测试"""

    def test_outfit_strategy_structure(self, sample_user_bazi):
        """穿搭策略结构"""
        fortune = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        strategy = fortune["outfit_strategy"]
        assert "primary_colors" in strategy
        assert "secondary_colors" in strategy
        assert "styles" in strategy
        assert "materials" in strategy
        assert "avoid_colors" in strategy

    def test_outfit_strategy_primary_colors_not_empty(self, sample_user_bazi):
        """主色调不为空"""
        fortune = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        assert len(fortune["outfit_strategy"]["primary_colors"]) > 0

    def test_outfit_strategy_avoid_colors(self, sample_user_bazi):
        """忌用颜色基于忌神"""
        fortune = calculate_monthly_fortune(sample_user_bazi, 2025, 6)
        # sample_user_bazi avoid = ["木", "水"]
        # 木=绿色系, 水=黑色系
        avoid = fortune["outfit_strategy"]["avoid_colors"]
        # 应该有忌用颜色
        assert isinstance(avoid, list)

    def test_outfit_strategy_direct_call(self):
        """直接调用穿搭策略生成"""
        monthly_data = {
            "suggested_elements": ["火", "土"],
            "avoid_elements": ["木", "水"],
            "day_master": "土",
            "season_element": "火",
            "element_analysis": {
                "strong_elements": ["火", "土"],
            },
        }
        result = generate_monthly_outfit_strategy(monthly_data)
        assert "primary_colors" in result
        assert len(result["primary_colors"]) > 0
        assert "primary_elements" in result


# ============================================================
# 年度运势汇总测试
# ============================================================

class TestYearlyFortune:
    """年度运势汇总测试"""

    def test_yearly_fortune_structure(self, sample_user_bazi):
        """年度运势结构"""
        result = calculate_yearly_fortune(sample_user_bazi, 2025)
        assert result["year"] == 2025
        assert "overall_score" in result
        assert "monthly_summary" in result
        assert "peak_months" in result
        assert "low_months" in result
        assert "yearly_advice" in result

    def test_yearly_fortune_12_months(self, sample_user_bazi):
        """年度运势包含12个月"""
        result = calculate_yearly_fortune(sample_user_bazi, 2025)
        assert len(result["monthly_summary"]) == 12
        for i, m in enumerate(result["monthly_summary"]):
            assert m["month"] == i + 1

    def test_yearly_fortune_overall_score_range(self, sample_user_bazi):
        """年度综合评分在合理范围"""
        result = calculate_yearly_fortune(sample_user_bazi, 2025)
        assert 0 <= result["overall_score"] <= 100

    def test_yearly_fortune_peak_months(self, sample_user_bazi):
        """旺月识别"""
        result = calculate_yearly_fortune(sample_user_bazi, 2025)
        # 旺月应来自评分最高的月份
        scores = [(m["month"], m["overall_score"]) for m in result["monthly_summary"]]
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
        # 旺月应包含最高分月份
        if result["peak_months"]:
            assert sorted_scores[0][0] in result["peak_months"]

    def test_yearly_fortune_low_months(self, sample_user_bazi):
        """衰月识别"""
        result = calculate_yearly_fortune(sample_user_bazi, 2025)
        scores = [(m["month"], m["overall_score"]) for m in result["monthly_summary"]]
        sorted_scores = sorted(scores, key=lambda x: x[1])
        # 衰月应包含最低分月份
        if result["low_months"]:
            assert sorted_scores[0][0] in result["low_months"]

    def test_yearly_fortune_advice_not_empty(self, sample_user_bazi):
        """年度建议不为空"""
        result = calculate_yearly_fortune(sample_user_bazi, 2025)
        assert len(result["yearly_advice"]) > 10

    def test_yearly_fortune_different_users(self, sample_user_bazi, sample_user_bazi_water):
        """不同用户年度运势不同"""
        r1 = calculate_yearly_fortune(sample_user_bazi, 2025)
        r2 = calculate_yearly_fortune(sample_user_bazi_water, 2025)
        assert r1["overall_score"] != r2["overall_score"] or \
               r1["peak_months"] != r2["peak_months"]

    def test_yearly_fortune_different_years(self, sample_user_bazi):
        """不同年份运势不同"""
        r1 = calculate_yearly_fortune(sample_user_bazi, 2024)
        r2 = calculate_yearly_fortune(sample_user_bazi, 2025)
        # 至少月度干支应不同
        assert r1["monthly_summary"][0]["month_ganzhi"] != \
               r2["monthly_summary"][0]["month_ganzhi"]


# ============================================================
# 辅助函数测试
# ============================================================

class TestHelperFunctions:
    """辅助函数测试"""

    def test_analyze_month_elements(self):
        """月度五行分析"""
        result = _analyze_month_elements("火", "土", "火", "土", ["火", "土"], ["木", "水"])
        assert "strong_elements" in result
        assert "weak_elements" in result
        assert "season_element" in result
        assert "beneficial" in result
        assert "harmful" in result

    def test_generate_yearly_advice_high_score(self):
        """高分年度建议"""
        advice = _generate_yearly_advice(85, [3, 6, 9], [], {"day_master": "土"}, 2025)
        assert "大吉" in advice

    def test_generate_yearly_advice_low_score(self):
        """低分年度建议"""
        advice = _generate_yearly_advice(40, [], [2, 5, 8], {"day_master": "土"}, 2025)
        assert "偏弱" in advice

    def test_generate_yearly_advice_with_suggested(self):
        """带喜用神的年度建议"""
        advice = _generate_yearly_advice(70, [3], [7], 
                                          {"day_master": "土", "suggested_elements": ["火", "土"]}, 2025)
        assert "火" in advice or "土" in advice
