"""
运势引擎测试
"""

import pytest
from datetime import date

from apps.api.services.fortune_engine import (
    calculate_daily_fortune,
    generate_outfit_suggestion,
    _get_day_ganzhi,
    _get_element_relation,
    _calculate_relation_score,
)


class TestFortuneEngine:
    """运势引擎测试"""

    @pytest.fixture
    def sample_bazi(self):
        return {
            "day_master": "火",
            "suggested_elements": ["木", "火"],
            "avoid_elements": ["水", "金"],
            "pillars": {
                "year": "壬申",
                "month": "乙巳",
                "day": "丁未",
                "hour": "丙午",
            },
        }

    def test_calculate_daily_fortune_structure(self, sample_bazi):
        """测试运势结果结构"""
        result = calculate_daily_fortune(sample_bazi, date(2025, 7, 1))

        assert "scores" in result
        assert "overall_score" in result
        assert "advice_text" in result
        assert "lucky_elements" in result
        assert "outfit_suggestion" in result

        scores = result["scores"]
        assert "career" in scores
        assert "wealth" in scores
        assert "love" in scores
        assert "health" in scores
        assert "study" in scores

    def test_scores_range(self, sample_bazi):
        """测试分数范围 0-100"""
        for d in range(1, 31):
            result = calculate_daily_fortune(sample_bazi, date(2025, 7, d))
            for dim, score in result["scores"].items():
                assert 0 <= score <= 100, f"{dim} score {score} out of range on day {d}"
            assert 0 <= result["overall_score"] <= 100

    def test_deterministic(self, sample_bazi):
        """同一天结果一致"""
        r1 = calculate_daily_fortune(sample_bazi, date(2025, 7, 15))
        r2 = calculate_daily_fortune(sample_bazi, date(2025, 7, 15))
        assert r1["scores"] == r2["scores"]
        assert r1["overall_score"] == r2["overall_score"]

    def test_different_days_different_results(self, sample_bazi):
        """不同天结果可能不同"""
        r1 = calculate_daily_fortune(sample_bazi, date(2025, 7, 1))
        r2 = calculate_daily_fortune(sample_bazi, date(2025, 7, 15))
        # 至少某些维度不同
        assert r1["scores"] != r2["scores"] or r1["overall_score"] != r2["overall_score"]

    def test_no_bazi_fallback(self):
        """无八字信息时的兜底"""
        bazi = {"day_master": "土", "suggested_elements": [], "avoid_elements": []}
        result = calculate_daily_fortune(bazi, date(2025, 7, 1))
        assert result["overall_score"] >= 0
        assert result["overall_score"] <= 100

    def test_lucky_elements_structure(self, sample_bazi):
        """测试幸运元素结构"""
        result = calculate_daily_fortune(sample_bazi, date(2025, 7, 1))
        le = result["lucky_elements"]

        assert "colors" in le
        assert "materials" in le
        assert "directions" in le
        assert "elements" in le
        assert len(le["colors"]) > 0
        assert len(le["elements"]) > 0

    def test_outfit_suggestion_not_empty(self, sample_bazi):
        """测试穿搭建议非空"""
        result = calculate_daily_fortune(sample_bazi, date(2025, 7, 1))
        assert result["outfit_suggestion"]
        assert len(result["outfit_suggestion"]) > 10

    def test_advice_text_not_empty(self, sample_bazi):
        """测试建议文本非空"""
        result = calculate_daily_fortune(sample_bazi, date(2025, 7, 1))
        assert result["advice_text"]
        assert len(result["advice_text"]) > 10


class TestElementRelation:
    """五行关系测试"""

    def test_bi_relation(self):
        """比（同元素）"""
        assert _get_element_relation("木", "木") == "bi"

    def test_sheng_relation(self):
        """生（水生木）"""
        assert _get_element_relation("木", "水") == "sheng"

    def test_ke_relation(self):
        """克（金克木）"""
        assert _get_element_relation("木", "金") == "ke"

    def test_xie_relation(self):
        """泄（木生火）"""
        assert _get_element_relation("木", "火") == "xie"

    def test_hao_relation(self):
        """耗（木克土）"""
        assert _get_element_relation("木", "土") == "hao"


class TestRelationScore:
    """关系分数测试"""

    def test_sheng_highest(self):
        assert _calculate_relation_score("sheng") > _calculate_relation_score("bi")

    def test_ke_lowest(self):
        assert _calculate_relation_score("ke") < _calculate_relation_score("hao")

    def test_bi_better_than_xie(self):
        assert _calculate_relation_score("bi") > _calculate_relation_score("xie")


class TestGenerateOutfitSuggestion:
    """穿搭建议生成测试"""

    def test_basic_suggestion(self):
        scores = {"career": 80, "wealth": 70, "love": 90, "health": 60, "study": 75}
        bazi = {"day_master": "火", "suggested_elements": ["木", "火"]}
        lucky = {"colors": ["绿色", "红色"], "materials": ["棉麻", "丝绸"]}

        result = generate_outfit_suggestion(scores, bazi, lucky)
        assert "桃花" in result  # love is highest
        assert len(result) > 20

    def test_without_lucky_elements(self):
        scores = {"career": 60, "wealth": 60, "love": 60, "health": 60, "study": 60}
        bazi = {"day_master": "土", "suggested_elements": ["土"]}

        result = generate_outfit_suggestion(scores, bazi)
        assert len(result) > 0
