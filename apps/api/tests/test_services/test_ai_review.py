"""
AI穿搭点评测试
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAIReview:
    """AI穿搭点评测试"""

    def test_rule_based_review_basic(self):
        """测试规则兜底点评"""
        from apps.api.services.ai_review_service import _rule_based_review

        bazi = {
            "day_master": "火",
            "suggested_elements": ["木", "火"],
            "avoid_elements": ["水"],
        }
        items = [
            {"name": "红色衬衫", "primary_element": "火", "category": "上装"},
            {"name": "绿色裤子", "primary_element": "木", "category": "下装"},
        ]

        result = _rule_based_review(bazi, items, None, None)
        assert "score" in result
        assert "comment" in result
        assert "suggestions" in result
        assert "wuxing_analysis" in result
        assert 0 <= result["score"] <= 100

    def test_rule_based_review_empty_items(self):
        """测试空衣物列表"""
        from apps.api.services.ai_review_service import _rule_based_review

        bazi = {"day_master": "火", "suggested_elements": ["木"], "avoid_elements": []}
        result = _rule_based_review(bazi, [], None, None)
        assert result["score"] == 50
        assert "穿搭" in result["comment"]

    def test_rule_based_review_avoid_element(self):
        """测试忌神元素穿搭"""
        from apps.api.services.ai_review_service import _rule_based_review

        bazi = {
            "day_master": "火",
            "suggested_elements": ["木"],
            "avoid_elements": ["水"],
        }
        items = [
            {"name": "蓝色外套", "primary_element": "水", "category": "外套"},
        ]

        result = _rule_based_review(bazi, items, None, None)
        assert result["score"] < 60  # 忌神应该低分

    def test_generate_ai_review_fallback(self):
        """测试LLM失败时使用兜底"""
        from apps.api.services.ai_review_service import generate_ai_review

        bazi = {"day_master": "土", "suggested_elements": ["火"], "avoid_elements": ["水"]}
        items = [{"name": "红色上衣", "primary_element": "火", "category": "上装"}]

        # mock LLM 调用失败
        with patch("apps.api.services.ai_review_service._llm_review", side_effect=Exception("LLM error")):
            result = generate_ai_review(bazi, items)
            assert "score" in result
            assert result["score"] >= 0

    def test_bazi_matching_analysis(self):
        """测试八字匹配分析"""
        from apps.api.services.ai_review_service import _rule_based_review

        bazi = {
            "day_master": "金",
            "suggested_elements": ["土", "金"],
            "avoid_elements": ["火"],
        }
        items = [
            {"name": "白色衬衫", "primary_element": "金", "category": "上装"},
            {"name": "棕色裤子", "primary_element": "土", "category": "下装"},
        ]

        result = _rule_based_review(bazi, items, None, None)
        # 两个都是喜用神，应该高分
        assert result["score"] >= 80
