"""
智能提醒服务测试
覆盖: services/smart_reminder_service.py
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def mock_cache():
    with patch("apps.api.services.smart_reminder_service.redis_cache") as m:
        m.get.return_value = None
        m.set.return_value = True
        yield m


@pytest.fixture
def mock_db():
    with patch("apps.api.services.smart_reminder_service.DatabasePool") as m:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        m.get_connection.return_value = mock_conn
        yield m, mock_cursor


class TestSmartReminderService:
    """SmartReminderService 测试"""

    def _create_service(self):
        from apps.api.services.smart_reminder_service import SmartReminderService
        return SmartReminderService()

    def test_check_and_notify_no_alerts(self, mock_cache, mock_db):
        _, mock_cursor = mock_db
        mock_cursor.fetchall.return_value = []
        svc = self._create_service()
        result = svc.check_and_notify(user_id=1)
        assert result == []

    def test_check_and_notify_with_weather_alert(self, mock_cache, mock_db):
        _, mock_cursor = mock_db
        mock_cursor.fetchall.return_value = []

        # Simulate yesterday was warmer
        def cache_get_side_effect(key):
            if "weather_snapshot" in key:
                return "30"  # yesterday was 30°C
            return None  # no alert cache
        mock_cache.get.side_effect = cache_get_side_effect

        weather = {"temperature": 20, "weather_condition": "晴", "city": "杭州"}
        svc = self._create_service()

        with patch("apps.api.services.smart_reminder_service.push_service", create=True) as mock_push:
            with patch("apps.api.services.smart_reminder_service.solar_term_service", create=True) as mock_st:
                mock_st.get_upcoming_solar_term.return_value = None
                # Import the module to patch correctly
                import apps.api.services.smart_reminder_service as mod
                with patch.object(mod, 'push_service', create=True) as mock_push2:
                    pass  # push import is inline, need different approach

        # Simpler: just call and check it doesn't crash
        with patch("apps.api.services.smart_reminder_service.SmartReminderService._check_weather_change") as m1:
            m1.return_value = {"type": "weather_change", "message": "降温10°C"}
            with patch("apps.api.services.smart_reminder_service.SmartReminderService._check_idle_wardrobe") as m2:
                m2.return_value = None
                with patch("apps.api.services.smart_reminder_service.SmartReminderService._check_solar_term_change") as m3:
                    m3.return_value = None
                    result = svc.check_and_notify(user_id=1)
                    assert len(result) == 1
                    assert result[0]["type"] == "weather_change"

    def test_check_weather_change_no_weather(self, mock_cache):
        svc = self._create_service()
        result = svc._check_weather_change(user_id=1, weather_info=None)
        assert result is None

    def test_check_weather_change_no_temp(self, mock_cache):
        svc = self._create_service()
        result = svc._check_weather_change(user_id=1, weather_info={"city": "杭州"})
        assert result is None

    def test_check_weather_change_cached(self, mock_cache):
        mock_cache.get.return_value = "1"  # already alerted today
        svc = self._create_service()
        result = svc._check_weather_change(
            user_id=1, weather_info={"temperature": 20}
        )
        assert result is None

    def test_check_weather_change_cooling(self, mock_cache):
        def cache_get(key):
            if "weather_snapshot" in key:
                return "30"
            return None
        mock_cache.get.side_effect = cache_get

        svc = self._create_service()
        with patch("apps.api.services.smart_reminder_service.push_service", create=True):
            result = svc._check_weather_change(
                user_id=1,
                weather_info={"temperature": 20, "weather_condition": "晴", "city": "杭州"}
            )
        assert result is not None
        assert "降温" in result["message"]

    def test_check_weather_change_warming(self, mock_cache):
        def cache_get(key):
            if "weather_snapshot" in key:
                return "15"
            return None
        mock_cache.get.side_effect = cache_get

        svc = self._create_service()
        with patch("apps.api.services.smart_reminder_service.push_service", create=True):
            result = svc._check_weather_change(
                user_id=1,
                weather_info={"temperature": 30, "weather_condition": "晴", "city": ""}
            )
        assert result is not None
        assert "升温" in result["message"]

    def test_check_weather_change_rain(self, mock_cache):
        mock_cache.get.return_value = None
        svc = self._create_service()
        with patch("apps.api.services.smart_reminder_service.push_service", create=True):
            result = svc._check_weather_change(
                user_id=1,
                weather_info={"temperature": 22, "weather_condition": "light rain"}
            )
        assert result is not None
        assert "降雨" in result["message"]

    def test_check_weather_change_no_alert(self, mock_cache):
        mock_cache.get.return_value = None
        svc = self._create_service()
        result = svc._check_weather_change(
            user_id=1,
            weather_info={"temperature": 22, "weather_condition": "晴"}
        )
        assert result is None  # no significant change

    def test_check_idle_wardrobe_cached(self, mock_cache):
        mock_cache.get.return_value = "1"
        svc = self._create_service()
        result = svc._check_idle_wardrobe(user_id=1)
        assert result is None

    def test_check_idle_wardrobe_with_items(self, mock_cache, mock_db):
        _, mock_cursor = mock_db
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "红色T恤", "category": "上装", "primary_element": "火", "last_worn_date": None, "created_at": date(2025, 1, 1)},
            {"id": 2, "name": "蓝色外套", "category": "外套", "primary_element": "水", "last_worn_date": None, "created_at": date(2025, 1, 1)},
        ]
        svc = self._create_service()
        with patch("apps.api.services.smart_reminder_service.push_service", create=True):
            result = svc._check_idle_wardrobe(user_id=1)
        assert result is not None
        assert result["type"] == "idle_wardrobe"
        assert "2 件" in result["message"]

    def test_check_idle_wardrobe_no_items(self, mock_cache, mock_db):
        _, mock_cursor = mock_db
        mock_cursor.fetchall.return_value = []
        svc = self._create_service()
        result = svc._check_idle_wardrobe(user_id=1)
        assert result is None

    def test_check_idle_wardrobe_db_error(self, mock_cache, mock_db):
        mock_db[0].get_connection.side_effect = Exception("db error")
        svc = self._create_service()
        result = svc._check_idle_wardrobe(user_id=1)
        assert result is None

    def test_check_solar_term_change_no_upcoming(self, mock_cache):
        svc = self._create_service()
        with patch("apps.api.services.smart_reminder_service.solar_term_service", create=True) as mock_st:
            mock_st.get_upcoming_solar_term.return_value = None
            result = svc._check_solar_term_change(user_id=1)
        assert result is None

    def test_check_solar_term_change_cached(self, mock_cache):
        mock_cache.get.return_value = "1"
        svc = self._create_service()
        with patch("apps.api.services.smart_reminder_service.solar_term_service", create=True) as mock_st:
            mock_st.get_upcoming_solar_term.return_value = {"name": "小暑", "element": "火"}
            result = svc._check_solar_term_change(user_id=1)
        assert result is None

    def test_check_solar_term_change_with_term(self, mock_cache):
        mock_cache.get.return_value = None
        svc = self._create_service()
        mock_term_data = {
            "name": "小暑", "element": "火", "date": date(2025, 7, 7),
            "days_until": 1, "description": "天气开始炎热"
        }
        with patch("apps.api.services.solar_term_service.solar_term_service") as mock_st:
            mock_st.get_upcoming_solar_term.return_value = mock_term_data
            mock_st.get_outfit_suggestion.return_value = "建议穿轻薄透气的衣物"
            with patch("apps.api.services.push_service.push_service"):
                with patch("apps.api.services.user_service.get_user_bazi", return_value={}):
                    result = svc._check_solar_term_change(user_id=1)
        assert result is not None
        assert result["type"] == "solar_term"
        assert result["solar_term"] == "小暑"

    def test_check_solar_term_change_fallback_message(self, mock_cache):
        mock_cache.get.return_value = None
        svc = self._create_service()
        mock_term_data = {
            "name": "大寒", "element": "水", "date": date(2025, 1, 20),
            "days_until": 2, "description": "一年中最冷的时候"
        }
        with patch("apps.api.services.solar_term_service.solar_term_service") as mock_st:
            mock_st.get_upcoming_solar_term.return_value = mock_term_data
            mock_st.get_outfit_suggestion.side_effect = Exception("error")
            with patch("apps.api.services.push_service.push_service"):
                with patch("apps.api.services.user_service.get_user_bazi", side_effect=Exception("no bazi")):
                    result = svc._check_solar_term_change(user_id=1)
        assert result is not None
        assert "大寒" in result["message"]
