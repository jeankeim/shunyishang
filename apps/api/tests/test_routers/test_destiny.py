"""
命理进阶功能路由测试
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user_bazi():
    """模拟用户八字数据"""
    return {
        "bazi": json.dumps({
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"},
            "eight_chars": ["甲", "子", "丙", "寅", "戊", "午", "庚", "申"],
            "five_elements_count": {"金": 1, "木": 2, "水": 1, "火": 2, "土": 2},
            "dominant_element": "木",
            "lacking_element": None,
            "day_master": "土",
            "month_element": "木",
            "suggested_elements": ["火", "土"],
            "avoid_elements": ["木", "水"],
            "reasoning": "测试",
        }),
        "xiyong_elements": None,
        "gender": "男",
        "birth_date": date(1995, 6, 15),
    }


@pytest.fixture
def mock_destiny_db(mock_db_pool, mock_user_bazi):
    """模拟命理路由所需的数据库"""
    mock_cursor = mock_db_pool["cursor"]
    # 第一次fetchone: get_user_bazi 查询
    mock_cursor.fetchone.return_value = mock_user_bazi
    return mock_db_pool


class TestDestinyRouterAuth:
    """命理路由认证保护测试"""

    @pytest.mark.asyncio
    async def test_major_luck_no_auth(self, async_client):
        """未认证返回401"""
        response = await async_client.get("/api/v1/destiny/major-luck")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_annual_luck_no_auth(self, async_client):
        """未认证返回401"""
        response = await async_client.get("/api/v1/destiny/annual-luck?year=2025")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ten_gods_no_auth(self, async_client):
        """未认证返回401"""
        response = await async_client.get("/api/v1/destiny/ten-gods")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_monthly_fortune_no_auth(self, async_client):
        """未认证返回401"""
        response = await async_client.get("/api/v1/destiny/monthly-fortune?year=2025&month=6")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_yearly_fortune_no_auth(self, async_client):
        """未认证返回401"""
        response = await async_client.get("/api/v1/destiny/yearly-fortune?year=2025")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_advanced_bazi_no_auth(self, async_client):
        """未认证返回401"""
        response = await async_client.get("/api/v1/destiny/advanced-bazi")
        assert response.status_code == 401


class TestDestinyRouterParams:
    """命理路由参数验证测试"""

    @pytest.mark.asyncio
    async def test_annual_luck_missing_year(self, async_client, auth_headers, test_app):
        """缺少year参数返回422"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/annual-luck",
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_annual_luck_invalid_year(self, async_client, auth_headers, test_app):
        """无效year参数返回422"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/annual-luck?year=1800",
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_monthly_fortune_missing_month(self, async_client, auth_headers, test_app):
        """缺少month参数返回422"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/monthly-fortune?year=2025",
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_monthly_fortune_invalid_month(self, async_client, auth_headers, test_app):
        """无效month参数返回422"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/monthly-fortune?year=2025&month=13",
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_yearly_fortune_missing_year(self, async_client, auth_headers, test_app):
        """缺少year参数返回422"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/yearly-fortune",
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()


class TestDestinyRouterEndpoints:
    """命理路由端点功能测试"""

    @pytest.mark.asyncio
    async def test_major_luck_success(self, async_client, auth_headers, test_app, mock_destiny_db):
        """测试大运周期查询"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/major-luck",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "luck_periods" in data
            assert len(data["luck_periods"]) == 8
            for period in data["luck_periods"]:
                assert "start_age" in period
                assert "end_age" in period
                assert "heavenly_stem" in period
                assert "earthly_branch" in period
                assert "ganzhi" in period
                assert "element" in period
                assert "luck_level" in period
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_annual_luck_success(self, async_client, auth_headers, test_app, mock_destiny_db):
        """测试流年运势查询"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/annual-luck?year=2025",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "annual_luck" in data
            assert data["annual_luck"]["year"] == 2025
            assert "scores" in data
            assert "overall_score" in data
            assert "lucky_colors" in data
            assert "outfit_advice" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ten_gods_success(self, async_client, auth_headers, test_app, mock_destiny_db):
        """测试十神格局查询"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/ten-gods",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "pillars" in data
            assert "year" in data["pillars"]
            assert "month" in data["pillars"]
            assert "day" in data["pillars"]
            assert "hour" in data["pillars"]
            assert "analysis" in data
            assert "dominant_gods" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_monthly_fortune_success(self, async_client, auth_headers, test_app, mock_destiny_db):
        """测试月度运势查询"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/monthly-fortune?year=2025&month=6",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["year"] == 2025
            assert data["month"] == 6
            assert "scores" in data
            assert "overall_score" in data
            assert "outfit_strategy" in data
            assert "element_analysis" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_yearly_fortune_success(self, async_client, auth_headers, test_app, mock_destiny_db):
        """测试年度运势查询"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/yearly-fortune?year=2025",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["year"] == 2025
            assert "overall_score" in data
            assert "monthly_summary" in data
            assert len(data["monthly_summary"]) == 12
            assert "peak_months" in data
            assert "low_months" in data
            assert "yearly_advice" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_advanced_bazi_success(self, async_client, auth_headers, test_app, mock_destiny_db):
        """测试高级八字分析"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.get(
                "/api/v1/destiny/advanced-bazi",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "pillars" in data
            assert "nayin" in data
            assert "hidden_stems" in data
            assert "chong" in data
            assert "xing" in data
            assert "hai" in data
            assert "he" in data
            assert "analysis" in data
        finally:
            test_app.dependency_overrides.clear()
