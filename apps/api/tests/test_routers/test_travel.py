"""
旅行推荐路由测试
测试旅行推荐端点、认证保护、参数验证
"""

import pytest
from unittest.mock import patch, MagicMock


class TestTravelRouter:
    """旅行推荐路由测试"""

    @pytest.mark.asyncio
    async def test_travel_recommend_no_auth(self, async_client):
        """未认证时返回401"""
        response = await async_client.post(
            "/api/v1/travel/recommend",
            json={
                "destination": "北京",
                "days": 3,
                "scenes_per_day": ["出差", "商务", "日常"],
                "luggage_size": "中",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_travel_recommend_authenticated(
        self, async_client, auth_headers, mock_db_pool, test_app
    ):
        """已认证获取旅行推荐"""
        from apps.api.routers.auth import get_current_user
        from apps.api.services.travel_recommend_service import (
            generate_travel_recommendation,
        )

        mock_result = {
            "outfits_plan": [
                {
                    "day": 1,
                    "scene": "出差",
                    "sub_scene": None,
                    "weather": {
                        "date": "2026-07-01",
                        "temperature_max": 28,
                        "temperature_min": 18,
                        "weather_desc": "晴",
                        "humidity": 60,
                        "wind_level": 2,
                    },
                    "items": [
                        {
                            "id": 1,
                            "name": "商务衬衫",
                            "category": "上装",
                            "primary_element": "金",
                            "final_score": 0.85,
                            "scene_score": 0.8,
                            "wuxing_score": 0.9,
                            "weather_score": 0.7,
                        }
                    ],
                    "notes": "第出差天，天气晴，18~28°C。推荐1件：上装。",
                }
            ],
            "luggage_summary": {
                "total_items": 1,
                "categories": {"上装": 1},
                "reusable_items": [
                    {"name": "商务衬衫", "category": "上装"}
                ],
                "luggage_score": 0.65,
            },
            "weather_forecast": [
                {
                    "date": "2026-07-01",
                    "temperature_max": 28,
                    "temperature_min": 18,
                    "weather_desc": "晴",
                    "humidity": 60,
                    "wind_level": 2,
                }
            ],
            "wuxing_analysis": {
                "target_elements": ["金", "水"],
                "weather_elements": [
                    {"date": "2026-07-01", "weather": "晴", "element": "火"}
                ],
                "item_element_distribution": {"金": 1},
                "balance_score": 0.2,
                "balance_reasoning": "当前行李五行覆盖 1/5 行（金）。",
            },
        }

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            with patch(
                "apps.api.routers.travel.generate_travel_recommendation",
                return_value=mock_result,
            ):
                response = await async_client.post(
                    "/api/v1/travel/recommend",
                    json={
                        "destination": "北京",
                        "days": 1,
                        "scenes_per_day": ["出差"],
                        "luggage_size": "中",
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert "outfits_plan" in data
            assert "luggage_summary" in data
            assert "weather_forecast" in data
            assert "wuxing_analysis" in data
            assert len(data["outfits_plan"]) == 1
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_travel_recommend_missing_destination(
        self, async_client, auth_headers, test_app
    ):
        """缺少必填参数"""
        from apps.api.routers.auth import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.post(
                "/api/v1/travel/recommend",
                json={
                    "days": 3,
                    "luggage_size": "中",
                },
                headers=auth_headers,
            )
            assert response.status_code == 422  # 验证失败
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_travel_recommend_invalid_luggage_size(
        self, async_client, auth_headers, test_app
    ):
        """无效行李箱大小"""
        from apps.api.routers.auth import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.post(
                "/api/v1/travel/recommend",
                json={
                    "destination": "北京",
                    "days": 3,
                    "luggage_size": "超大",  # 无效值
                },
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_travel_recommend_invalid_days(
        self, async_client, auth_headers, test_app
    ):
        """无效天数"""
        from apps.api.routers.auth import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            response = await async_client.post(
                "/api/v1/travel/recommend",
                json={
                    "destination": "北京",
                    "days": 0,  # 无效
                    "luggage_size": "中",
                },
                headers=auth_headers,
            )
            assert response.status_code == 422
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_travel_recommend_scenes_too_many(
        self, async_client, auth_headers, mock_db_pool, test_app
    ):
        """场景列表超过天数"""
        from apps.api.routers.auth import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            with patch(
                "apps.api.routers.travel.generate_travel_recommendation"
            ):
                response = await async_client.post(
                    "/api/v1/travel/recommend",
                    json={
                        "destination": "北京",
                        "days": 2,
                        "scenes_per_day": ["出差", "商务", "日常"],  # 超过2天
                        "luggage_size": "中",
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 400
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_travel_recommend_with_bazi(
        self, async_client, auth_headers, mock_db_pool, test_app
    ):
        """携带八字信息的旅行推荐"""
        from apps.api.routers.auth import get_current_user

        mock_result = {
            "outfits_plan": [],
            "luggage_summary": {
                "total_items": 0,
                "categories": {},
                "reusable_items": [],
                "luggage_score": 0.0,
            },
            "weather_forecast": [],
            "wuxing_analysis": {
                "target_elements": ["金", "水"],
                "weather_elements": [],
                "item_element_distribution": {},
                "balance_score": 0.0,
                "balance_reasoning": "暂无衣物数据，无法分析五行平衡。",
            },
        }

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            with patch(
                "apps.api.routers.travel.generate_travel_recommendation",
                return_value=mock_result,
            ):
                response = await async_client.post(
                    "/api/v1/travel/recommend",
                    json={
                        "destination": "三亚",
                        "days": 5,
                        "scenes_per_day": ["度假", "度假", "度假", "日常", "日常"],
                        "luggage_size": "大",
                        "bazi": {
                            "suggested_elements": ["金", "水"],
                            "reasoning": "测试八字",
                        },
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_travel_recommend_empty_scenes(
        self, async_client, auth_headers, mock_db_pool, test_app
    ):
        """空场景列表（自动填充为日常）"""
        from apps.api.routers.auth import get_current_user

        mock_result = {
            "outfits_plan": [
                {"day": 1, "scene": "日常", "items": [], "notes": "测试"}
            ],
            "luggage_summary": {
                "total_items": 0,
                "categories": {},
                "reusable_items": [],
                "luggage_score": 0.0,
            },
            "weather_forecast": [],
            "wuxing_analysis": {
                "target_elements": [],
                "weather_elements": [],
                "item_element_distribution": {},
                "balance_score": 0.0,
                "balance_reasoning": "测试",
            },
        }

        test_app.dependency_overrides[get_current_user] = lambda: {"id": 1}
        try:
            with patch(
                "apps.api.routers.travel.generate_travel_recommendation",
                return_value=mock_result,
            ):
                response = await async_client.post(
                    "/api/v1/travel/recommend",
                    json={
                        "destination": "上海",
                        "days": 1,
                        "scenes_per_day": [],
                        "luggage_size": "小",
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()
