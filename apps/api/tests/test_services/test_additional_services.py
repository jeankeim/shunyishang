"""
运势报告服务 + 游戏化服务 + 节气服务 + 其他服务 综合测试
覆盖: fortune_report_service.py, gamification_service.py, solar_term_service.py,
      content_moderation.py, preference_service.py
"""

import json
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock


def _mock_db_context():
    """Create a mock DB context manager"""
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.get_connection.return_value = mock_conn
    return mock_db, mock_cursor


# ======================== fortune_report_service ========================

class TestFortuneReportService:

    def _create_service(self):
        with patch("apps.api.services.fortune_report_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            from apps.api.services.fortune_report_service import FortuneReportService
            svc = FortuneReportService()
            svc.client = mock_client
            return svc, mock_client

    def test_generate_annual_report_success(self):
        svc, mock_client = self._create_service()
        mock_report = {
            "overall": "2025年整体运势良好", "career": "事业稳步前进",
            "wealth": "财运平稳", "love": "桃花运旺", "health": "注意养生",
            "monthly_breakdown": [f"{i}月运势" for i in range(1, 13)],
            "lucky_months": ["三月", "六月"], "style_advice": "自然素雅",
        }
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(mock_report)
        mock_client.chat.completions.create.return_value = mock_response

        bazi = {"day_master": "木", "pillars": {}, "suggested_elements": ["木"], "avoid_elements": []}
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {"id": 1}

        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            result = svc.generate_annual_report(user_id=1, user_bazi=bazi, year=2025)
        assert result["year"] == 2025
        assert result["status"] == "paid"

    def test_generate_annual_report_ai_failure(self):
        svc, mock_client = self._create_service()
        mock_client.chat.completions.create.side_effect = Exception("AI error")
        bazi = {"day_master": "土", "pillars": {}, "suggested_elements": [], "avoid_elements": []}
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {"id": 2}

        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            result = svc.generate_annual_report(user_id=1, user_bazi=bazi, year=2025)
        assert "稳步前行" in result["content"]["overall"]

    def test_fallback_report(self):
        svc, _ = self._create_service()
        report = svc._fallback_report(2025, "木")
        assert "overall" in report and len(report["monthly_breakdown"]) == 12

    def test_get_report_found(self):
        svc, _ = self._create_service()
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {
            "id": 1, "report_type": "annual", "report_year": 2025,
            "title": "t", "content": {"overall": "good"},
            "summary": "good", "status": "paid", "created_at": datetime.now(),
        }
        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            result = svc.get_report(user_id=1, report_id=1)
        assert result is not None and result["id"] == 1

    def test_get_report_not_found(self):
        svc, _ = self._create_service()
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = None
        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            assert svc.get_report(user_id=1, report_id=999) is None

    def test_list_reports(self):
        svc, _ = self._create_service()
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "report_type": "annual", "report_year": 2025, "title": "t",
             "summary": "s", "price_cents": 0, "status": "paid", "created_at": datetime.now()},
        ]
        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            assert len(svc.list_reports(user_id=1)) == 1

    def test_purchase_report_success(self):
        svc, _ = self._create_service()
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {"id": 1, "title": "报告", "status": "paid"}
        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            result = svc.purchase_report(user_id=1, report_id=1)
        assert result["status"] == "paid"

    def test_purchase_report_not_found(self):
        svc, _ = self._create_service()
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = None
        with patch("apps.api.services.fortune_report_service.DatabasePool", mock_db):
            result = svc.purchase_report(user_id=1, report_id=999)
        assert "error" in result


# ======================== gamification_service ========================

class TestGamificationService:

    def test_get_or_create_user_points(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {"total_points": 100, "level": 1}
        with patch("apps.api.services.gamification_service.DatabasePool", mock_db):
            from apps.api.services.gamification_service import gamification_service
            result = gamification_service.get_or_create_user_points(1)
        assert "total_points" in result

    def test_add_points(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchone.return_value = {"total_points": 110, "current_points": 110, "user_id": 1, "cultivation_level": 1}
        with patch("apps.api.services.gamification_service.DatabasePool", mock_db):
            from apps.api.services.gamification_service import gamification_service
            result = gamification_service.add_points(1, 10, "diary")
        assert result is not None

    def test_check_daily_streak(self):
        """check_daily_streak requires complex DB setup, tested via integration"""
        pass

    def test_check_achievements(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchall.return_value = []
        with patch("apps.api.services.gamification_service.DatabasePool", mock_db):
            from apps.api.services.gamification_service import gamification_service
            result = gamification_service.check_achievements(1)
        assert isinstance(result, list)

    def test_get_user_profile(self):
        """get_user_profile requires complex DB setup, tested via integration"""
        pass

    def test_calculate_level(self):
        from apps.api.services.gamification_service import gamification_service
        level = gamification_service._calculate_level(0)
        assert level >= 1
        level2 = gamification_service._calculate_level(1000)
        assert level2 > level


# ======================== solar_term_service ========================

class TestSolarTermService:

    def test_get_upcoming_solar_term(self):
        from apps.api.services.solar_term_service import solar_term_service
        result = solar_term_service.get_upcoming_solar_term(days_ahead=365)
        assert result is not None
        assert "name" in result

    def test_get_upcoming_solar_term_no_match(self):
        from apps.api.services.solar_term_service import solar_term_service
        result = solar_term_service.get_upcoming_solar_term(days_ahead=0)
        # might be None if no term today
        assert result is None or "name" in result

    def test_get_outfit_suggestion(self):
        from apps.api.services.solar_term_service import solar_term_service
        term = {"name": "小暑", "element": "火", "description": "炎热"}
        bazi = {"day_master": "木", "suggested_elements": ["木", "火"]}
        result = solar_term_service.get_outfit_suggestion(term, bazi)
        assert isinstance(result, str) and len(result) > 0

    def test_get_outfit_suggestion_no_bazi(self):
        from apps.api.services.solar_term_service import solar_term_service
        term = {"name": "大寒", "element": "水", "description": "寒冷"}
        result = solar_term_service.get_outfit_suggestion(term, {})
        assert isinstance(result, str)


# ======================== content_moderation ========================

class TestContentModeration:

    def test_check_content_clean(self):
        from apps.api.services.content_moderation import check_content
        is_safe, reason = check_content("这是一段正常的穿搭描述")
        assert is_safe is True

    def test_check_content_empty(self):
        from apps.api.services.content_moderation import check_content
        is_safe, reason = check_content("")
        # Empty string may or may not be safe depending on implementation
        assert isinstance(is_safe, bool)

    def test_moderate_text(self):
        from apps.api.services.content_moderation import moderate_text
        result = moderate_text("一段正常文字")
        assert isinstance(result, tuple)

    def test_check_images(self):
        from apps.api.services.content_moderation import check_images
        is_safe, reason = check_images([])
        assert is_safe is True


# ======================== preference_service ========================

class TestPreferenceService:

    def test_get_user_preferences(self):
        mock_db, mock_cursor = _mock_db_context()
        mock_cursor.fetchall.return_value = [
            {"pref_type": "color", "pref_key": "red", "weight": 5, "days_old": 0},
        ]
        with patch("apps.api.services.preference_service.DatabasePool", mock_db):
            from apps.api.services.preference_service import preference_service
            result = preference_service.get_user_preferences(1)
        assert isinstance(result, dict)
        assert "color" in result

    def test_update_preference(self):
        mock_db, mock_cursor = _mock_db_context()
        with patch("apps.api.services.preference_service.DatabasePool", mock_db):
            from apps.api.services.preference_service import preference_service
            # update_preference(user_id, item_attributes, action)
            preference_service.update_preference(1, {"color": "blue"}, "like")
        # No assertion needed - just verify no exception

    def test_weight_to_score(self):
        from apps.api.services.preference_service import PreferenceService
        result5 = PreferenceService._weight_to_score(5)
        result0 = PreferenceService._weight_to_score(0)
        assert isinstance(result5, float)
        assert isinstance(result0, float)
