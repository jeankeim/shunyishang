"""
运势路由扩展测试 - 覆盖 authenticated endpoints
覆盖: apps/api/routers/fortune.py (256行未覆盖 → 目标90%+)
"""

import json
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock, AsyncMock

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def _fortune_row(**overrides):
    """构造运势数据库行"""
    base = {
        "id": 1, "user_id": 1, "fortune_date": date(2026, 7, 17),
        "scores": {"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 85},
        "overall_score": 74, "advice_text": "今日宜穿搭",
        "lucky_elements": {"colors": ["红色", "橙色"], "elements": ["火"], "directions": ["南"]},
        "outfit_suggestion": "红色连衣裙",
        "bazi_snapshot": {"day_master": "火", "target_day_ganzhi": "丙午", "target_day_element": "火"},
        "created_at": datetime.now(),
    }
    base.update(overrides)
    return base


class TestHelperFunctions:
    def test_get_user_id_ok(self):
        from apps.api.routers.fortune import _get_user_id
        assert _get_user_id({"id": 42}) == 42
        assert _get_user_id({"user_id": 42}) == 42

    def test_get_user_id_missing(self):
        from apps.api.routers.fortune import _get_user_id
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _get_user_id({})

    def test_get_fortune_level(self):
        from apps.api.routers.fortune import _get_fortune_level
        assert _get_fortune_level(90) == "great"
        assert _get_fortune_level(70) == "good"
        assert _get_fortune_level(55) == "normal"
        assert _get_fortune_level(30) == "weak"

    def test_row_to_fortune_response(self):
        from apps.api.routers.fortune import _row_to_fortune_response
        row = _fortune_row()
        result = _row_to_fortune_response(row)
        assert result.overall_score == 74
        assert result.scores.career == 80

    def test_row_to_fortune_response_json_strings(self):
        from apps.api.routers.fortune import _row_to_fortune_response
        row = _fortune_row(
            scores=json.dumps({"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 85}),
            lucky_elements=json.dumps({"colors": ["红色"], "elements": ["火"], "directions": ["南"]}),
            bazi_snapshot=json.dumps({"day_master": "火"}),
        )
        result = _row_to_fortune_response(row)
        assert result.overall_score == 74

    def test_build_today_card(self):
        from apps.api.routers.fortune import _build_today_card, _row_to_fortune_response
        fortune = _row_to_fortune_response(_fortune_row())
        card = _build_today_card(fortune)
        assert card.fortune_level == "good"
        assert card.day_master == "火"
        assert len(card.lucky_colors) <= 3
        assert isinstance(card.avoid_colors, list)


class TestGetTodayFortune:
    @pytest.mark.asyncio
    async def test_cached_in_db(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """DB中有缓存时直接返回"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _fortune_row()

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/fortune/today", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["overall_score"] == 74
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_new(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """DB中无缓存时计算并存储"""
        mock_cursor = mock_db_pool["cursor"]
        # First call: _get_cached_fortune returns None
        # Second call: _generate_and_store calls get_user_bazi + calculate + INSERT
        bazi = {"day_master": "火", "pillars": {"year": "丙午"}, "suggested_elements": ["火"], "avoid_elements": []}
        fortune_result = {
            "scores": {"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 85},
            "overall_score": 74, "advice_text": "今日大吉",
            "lucky_elements": {"colors": ["红色"], "elements": ["火"], "directions": ["南"]},
            "outfit_suggestion": "红色上衣", "bazi_snapshot": bazi,
        }
        mock_cursor.fetchone.side_effect = [
            None,  # _get_cached_fortune → no cache
            {"id": 1, **bazi, "phone": None, "email": "t@t.com", "user_code": "T1", "gender": "男", "nickname": "u"},  # get_user_bazi
            _fortune_row(),  # _generate_and_store INSERT RETURNING
        ]

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.fortune.calculate_daily_fortune", return_value=fortune_result):
                response = await async_client.get("/api/v1/fortune/today", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestGetFortune:
    @pytest.mark.asyncio
    async def test_with_cache(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """指定日期，有缓存"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _fortune_row()

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get(
                "/api/v1/fortune?date=2026-07-17", headers=auth_headers
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestGenerateFortune:
    @pytest.mark.asyncio
    async def test_generate(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """手动生成运势"""
        mock_cursor = mock_db_pool["cursor"]
        bazi = {"day_master": "火", "pillars": {"year": "丙午"}, "suggested_elements": ["火"], "avoid_elements": []}
        fortune_result = {
            "scores": {"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 85},
            "overall_score": 74, "advice_text": "test",
            "lucky_elements": {"colors": ["红色"], "elements": ["火"], "directions": ["南"]},
            "outfit_suggestion": "红衣", "bazi_snapshot": bazi,
        }
        mock_cursor.fetchone.side_effect = [
            {"id": 1, **bazi, "phone": None, "email": "t@t.com", "user_code": "T1", "gender": "男", "nickname": "u"},
            _fortune_row(),
        ]

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.fortune.calculate_daily_fortune", return_value=fortune_result):
                response = await async_client.post("/api/v1/fortune/generate", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestTodayCard:
    @pytest.mark.asyncio
    async def test_today_card(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """今日运势卡片"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = _fortune_row()

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/fortune/today-card", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "fortune_level" in data
            assert "lucky_colors" in data
            assert "avoid_colors" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_today_card_no_auth(self, async_client):
        response = await async_client.get("/api/v1/fortune/today-card")
        assert response.status_code == 401


class TestWeeklyFortune:
    @pytest.mark.asyncio
    async def test_anonymous(self, async_client, test_app, mock_db_pool):
        """未登录返回通用周报"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        with patch("apps.api.routers.fortune._get_optional_user", return_value=None):
            with patch("apps.api.services.weekly_fortune_service.WeeklyFortuneService._fallback_weekly_report",
                        return_value={"title": "通用周报", "summary": "test"}):
                response = await async_client.get("/api/v1/fortune/weekly")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logged_in(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """已登录返回个性化周报"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (1, "test", "男", "{}")

        mock_user_data = {"id": 1, "nickname": "test", "gender": "男", "bazi": "{}"}
        with patch("apps.api.routers.fortune._get_optional_user", return_value=mock_user_data):
            with patch("apps.api.services.weekly_fortune_service.WeeklyFortuneService.calculate_weekly_fortune",
                        new_callable=AsyncMock, return_value={"title": "个性化周报", "summary": "test"}):
                response = await async_client.get("/api/v1/fortune/weekly", headers=auth_headers)
        assert response.status_code == 200


class TestDailyRitual:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/fortune/daily-ritual")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """每日仪式摘要"""
        mock_cursor = mock_db_pool["cursor"]
        bazi = {"day_master": "火", "pillars": {"year": "丙午"}, "suggested_elements": ["火"], "avoid_elements": []}
        fortune_result = {
            "scores": {"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 85},
            "overall_score": 74, "advice_text": "test",
            "lucky_elements": {"colors": ["红色"], "elements": ["火"], "directions": ["南"]},
            "outfit_suggestion": "红衣", "bazi_snapshot": bazi,
        }
        # Multiple DB queries: get_cached_fortune + get_user_bazi + diary stats + cultivation
        mock_cursor.fetchone.side_effect = [
            None,  # _get_cached_fortune
            {"id": 1, **bazi, "phone": None, "email": "t@t.com", "user_code": "T1", "gender": "男", "nickname": "u"},  # get_user_bazi
            _fortune_row(),  # _generate_and_store RETURNING
            {"cnt": 1},  # diary checked_in_today
            {"total": 5},  # total diaries
            {"total_points": 100, "streak_days": 3, "cultivation_level": 2},  # cultivation
        ]
        mock_cursor.fetchall.return_value = []  # streak dates

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.fortune.calculate_daily_fortune", return_value=fortune_result):
                response = await async_client.get("/api/v1/fortune/daily-ritual", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "fortune" in data
            assert "diary" in data
            assert "cultivation" in data
        finally:
            test_app.dependency_overrides.clear()


class TestReportsEndpoints:
    @pytest.mark.asyncio
    async def test_list_reports(self, async_client, auth_headers, test_app, mock_user):
        """获取报告列表"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.services.fortune_report_service.fortune_report_service") as mock_svc:
                mock_svc.list_reports.return_value = []
                response = await async_client.get("/api/v1/fortune/reports", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_found(self, async_client, auth_headers, test_app, mock_user):
        """获取报告详情"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.services.fortune_report_service.fortune_report_service") as mock_svc:
                mock_svc.get_report.return_value = {"id": 1, "title": "2026年报"}
                response = await async_client.get("/api/v1/fortune/reports/1", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["id"] == 1
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, async_client, auth_headers, test_app, mock_user):
        """报告不存在"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.services.fortune_report_service.fortune_report_service") as mock_svc:
                mock_svc.get_report.return_value = None
                response = await async_client.get("/api/v1/fortune/reports/999", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_annual_report(self, async_client, auth_headers, test_app, mock_user):
        """生成年度报告：提交异步任务，返回 202 + task_id"""
        bazi = {"day_master": "火", "pillars": {}, "suggested_elements": [], "avoid_elements": []}
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.fortune.get_user_bazi", return_value=bazi):
                # mock 限频计数，避免真实 DB 中残留的历史报告记录触发 429
                with patch("apps.api.services.fortune_report_service.fortune_report_service.count_reports_for_year", return_value=0):
                    with patch("apps.api.services.task_service.create_task", return_value="uuid-123") as mock_create:
                        response = await async_client.post("/api/v1/fortune/reports/annual?year=2026", headers=auth_headers)
            assert response.status_code == 202
            data = response.json()
            assert data["task_id"] == "uuid-123"
            assert data["status"] == "pending"
            mock_create.assert_called_once()
            assert mock_create.call_args.kwargs["task_type"] == "annual_report"
            assert mock_create.call_args.kwargs["payload"] == {"year": 2026}
        finally:
            test_app.dependency_overrides.clear()
"""
运势路由测试
"""

import pytest
from unittest.mock import patch


class TestFortuneRouter:
    """运势路由测试"""

    @pytest.mark.asyncio
    async def test_today_fortune_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/fortune/today")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_fortune_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.get("/api/v1/fortune?date=2025-07-01")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_fortune_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post("/api/v1/fortune/generate")
        assert response.status_code == 401
