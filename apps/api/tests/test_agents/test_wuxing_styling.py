"""
五行穿搭百科Agent测试
覆盖: packages/ai_agents/wuxing_styling.py
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock


class TestEnsureWikiLoaded:
    def test_load_success(self):
        import packages.ai_agents.wuxing_styling as mod
        # Reset cached data
        mod._WIKI_DATA = []
        mod._WIKI_BY_ELEMENT = {}
        mod._ensure_wiki_loaded()
        assert len(mod._WIKI_DATA) > 0
        assert len(mod._WIKI_BY_ELEMENT) > 0

    def test_load_failure_fallback(self):
        import packages.ai_agents.wuxing_styling as mod
        mod._WIKI_DATA = []
        mod._WIKI_BY_ELEMENT = {}
        with patch("builtins.open", side_effect=FileNotFoundError("not found")):
            mod._ensure_wiki_loaded()
        assert mod._WIKI_DATA == []

    def test_cached_data_not_reloaded(self):
        import packages.ai_agents.wuxing_styling as mod
        mod._WIKI_DATA = [{"element": "木", "tip": "cached"}]
        mod._WIKI_BY_ELEMENT = {"木": [{"element": "木", "tip": "cached"}]}
        mod._ensure_wiki_loaded()  # should not reload
        assert mod._WIKI_DATA[0]["tip"] == "cached"
        mod._WIKI_DATA = []
        mod._WIKI_BY_ELEMENT = {}


class TestGetTodayElement:
    def test_with_cnlunar(self):
        from packages.ai_agents.wuxing_styling import get_today_element
        import cnlunar as real_cl
        # Mock cnlunar.Lunar to return controlled data
        with patch.object(real_cl, "Lunar") as mock_lunar_cls:
            mock_lunar = MagicMock()
            mock_lunar.day8Char = "甲子"
            mock_lunar_cls.return_value = mock_lunar
            elem = get_today_element(date(2025, 7, 15))
        assert elem in ["木", "火", "土", "金", "水"]

    def test_fallback_on_error(self):
        from packages.ai_agents.wuxing_styling import get_today_element
        with patch.dict("sys.modules", {"cnlunar": None}):
            elem = get_today_element(date(2025, 7, 15))
        assert elem in ["木", "火", "土", "金", "水"]

    def test_default_date(self):
        from packages.ai_agents.wuxing_styling import get_today_element
        import cnlunar as real_cl
        with patch.object(real_cl, "Lunar") as mock_lunar_cls:
            mock_lunar = MagicMock()
            mock_lunar.day8Char = "丙寅"
            mock_lunar_cls.return_value = mock_lunar
            elem = get_today_element()
        assert elem == "火"  # 丙 = 火


class TestWuxingStylingAgent:
    def test_init(self):
        import packages.ai_agents.wuxing_styling as mod
        mod._WIKI_DATA = []
        mod._WIKI_BY_ELEMENT = {}
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        assert len(agent.wiki_data) > 0

    def test_get_today_tip_with_element(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        result = agent.get_today_tip(element="木")
        assert result["element"] == "木"
        assert "date" in result
        assert "tip" in result

    def test_get_today_tip_auto_element(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        result = agent.get_today_tip(target_date=date(2025, 7, 15))
        assert "element" in result

    def test_get_today_tip_empty_data(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        agent.wiki_data = []
        agent.wiki_by_element = {}
        result = agent.get_today_tip(element="木")
        assert result["tip"] == {"message": "暂无数据"}

    def test_get_all_tips_by_element(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        result = agent.get_all_tips(element="木")
        assert result["element"] == "木"
        assert isinstance(result["tips"], list)

    def test_get_all_tips_all(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        result = agent.get_all_tips()
        assert "tips" in result

    def test_get_tips_by_category(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        # Use a category that might exist
        result = agent.get_tips_by_category("颜色搭配", element="木")
        assert isinstance(result, list)

    def test_get_tips_by_category_all(self):
        from packages.ai_agents.wuxing_styling import WuxingStylingAgent
        agent = WuxingStylingAgent()
        result = agent.get_tips_by_category("nonexistent_category")
        assert isinstance(result, list)
