"""
周报运势服务测试
覆盖: services/weekly_fortune_service.py
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class TestWeeklyFortuneHelpers:
    """测试纯函数辅助方法"""

    def test_get_week_range(self):
        from apps.api.services.weekly_fortune_service import _get_week_range
        # Wednesday July 15, 2026
        ref = date(2026, 7, 15)
        start, end = _get_week_range(ref)
        assert start == date(2026, 7, 13)  # Monday
        assert end == date(2026, 7, 19)    # Sunday

    def test_get_week_range_monday(self):
        from apps.api.services.weekly_fortune_service import _get_week_range
        ref = date(2026, 7, 13)  # Monday
        start, end = _get_week_range(ref)
        assert start == date(2026, 7, 13)
        assert end == date(2026, 7, 19)

    def test_get_week_range_sunday(self):
        from apps.api.services.weekly_fortune_service import _get_week_range
        ref = date(2026, 7, 19)  # Sunday
        start, end = _get_week_range(ref)
        assert start == date(2026, 7, 13)
        assert end == date(2026, 7, 19)

    def test_get_week_range_default(self):
        from apps.api.services.weekly_fortune_service import _get_week_range
        start, end = _get_week_range()
        assert start <= date.today() <= end

    def test_determine_trend_rising(self):
        from apps.api.services.weekly_fortune_service import _determine_trend
        scores = [60, 62, 65, 75, 78, 80, 82]
        assert _determine_trend(scores) == "上升"

    def test_determine_trend_falling(self):
        from apps.api.services.weekly_fortune_service import _determine_trend
        scores = [85, 82, 80, 70, 65, 60, 58]
        assert _determine_trend(scores) == "下降"

    def test_determine_trend_stable(self):
        from apps.api.services.weekly_fortune_service import _determine_trend
        scores = [70, 72, 71, 73, 70, 72, 71]
        assert _determine_trend(scores) == "平稳"

    def test_determine_trend_short_list(self):
        from apps.api.services.weekly_fortune_service import _determine_trend
        assert _determine_trend([70, 71, 72]) == "平稳"
        assert _determine_trend([]) == "平稳"

    def test_generate_weekly_style_keywords(self):
        from apps.api.services.weekly_fortune_service import _generate_weekly_style_keywords
        keywords = _generate_weekly_style_keywords(["木", "火"])
        assert isinstance(keywords, list)
        assert len(keywords) <= 4

    def test_generate_weekly_style_keywords_empty(self):
        from apps.api.services.weekly_fortune_service import _generate_weekly_style_keywords
        keywords = _generate_weekly_style_keywords([])
        assert keywords == []

    def test_generate_weekly_outfit_suggestion_rising(self):
        from apps.api.services.weekly_fortune_service import _generate_weekly_outfit_suggestion
        result = _generate_weekly_outfit_suggestion(
            weekly_elements=["木", "火"],
            day_master="土",
            overall_score=80,
            trend="上升"
        )
        assert "上升" in result
        assert "木" in result or "火" in result

    def test_generate_weekly_outfit_suggestion_falling(self):
        from apps.api.services.weekly_fortune_service import _generate_weekly_outfit_suggestion
        result = _generate_weekly_outfit_suggestion(
            weekly_elements=["水"],
            day_master="木",
            overall_score=60,
            trend="下降"
        )
        assert "回落" in result

    def test_generate_weekly_outfit_suggestion_stable(self):
        from apps.api.services.weekly_fortune_service import _generate_weekly_outfit_suggestion
        result = _generate_weekly_outfit_suggestion(
            weekly_elements=["土"],
            day_master="金",
            overall_score=70,
            trend="平稳"
        )
        assert "平稳" in result

    def test_compute_weekly_lucky_elements(self):
        from apps.api.services.weekly_fortune_service import _compute_weekly_lucky_elements
        daily_fortunes = [
            {"lucky_elements": {"elements": ["木", "火"]}},
            {"lucky_elements": {"elements": ["木", "水"]}},
            {"lucky_elements": {"elements": ["火"]}},
        ]
        result = _compute_weekly_lucky_elements(daily_fortunes, ["木", "火"], "土")
        assert "木" in result
        assert len(result) <= 3

    def test_compute_weekly_lucky_elements_no_suggested(self):
        from apps.api.services.weekly_fortune_service import _compute_weekly_lucky_elements
        daily_fortunes = [
            {"lucky_elements": {"elements": ["金"]}},
        ]
        result = _compute_weekly_lucky_elements(daily_fortunes, [], "土")
        assert len(result) >= 1

    def test_compute_weekly_lucky_elements_empty(self):
        from apps.api.services.weekly_fortune_service import _compute_weekly_lucky_elements
        result = _compute_weekly_lucky_elements([], [], "土")
        assert result == ["土"]


class TestWeeklyFortuneService:
    """WeeklyFortuneService 测试"""

    @pytest.mark.asyncio
    async def test_calculate_weekly_fortune_success(self):
        from apps.api.services.weekly_fortune_service import WeeklyFortuneService
        svc = WeeklyFortuneService()

        mock_bazi = {
            "day_master": "木",
            "suggested_elements": ["木", "火"],
            "pillars": {"year": "甲子", "month": "丙寅", "day": "乙卯", "hour": "丁亥"},
        }
        mock_daily = {
            "overall_score": 75,
            "scores": {"career": 80, "wealth": 70},
            "lucky_elements": {"elements": ["木", "火"], "colors": ["绿色", "红色"]},
            "outfit_suggestion": "适合绿色系",
        }

        with patch("apps.api.services.weekly_fortune_service.get_user_bazi", return_value=mock_bazi):
            with patch("apps.api.services.weekly_fortune_service.calculate_daily_fortune", return_value=mock_daily):
                result = await svc.calculate_weekly_fortune(user_id=1)

        assert result["overall_score"] == 75
        assert result["day_master"] == "木"
        assert len(result["daily_fortunes"]) == 7
        assert result["overall_trend"] in ("上升", "下降", "平稳")
        assert result["best_day"] is not None
        assert result["low_day"] is not None

    @pytest.mark.asyncio
    async def test_calculate_weekly_fortune_fallback(self):
        from apps.api.services.weekly_fortune_service import WeeklyFortuneService
        svc = WeeklyFortuneService()

        with patch("apps.api.services.weekly_fortune_service.get_user_bazi", side_effect=Exception("no bazi")):
            result = await svc.calculate_weekly_fortune(user_id=999)

        assert result["overall_trend"] == "平稳"
        assert result["overall_score"] == 65
        assert result["daily_fortunes"] == []

    def test_fallback_weekly_report(self):
        from apps.api.services.weekly_fortune_service import WeeklyFortuneService
        svc = WeeklyFortuneService()
        result = svc._fallback_weekly_report()
        assert "week_number" in result
        assert result["overall_trend"] == "平稳"
        assert result["overall_score"] == 65
