"""
衣橱路由测试
覆盖 wardrobe.py 所有端点
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


@pytest.fixture
def mock_wardrobe_item():
    """模拟衣橱物品行"""
    return {
        "id": 1,
        "user_id": 1,
        "item_code": "item_001",
        "name": "红色T恤",
        "category": "上装",
        "image_url": "http://img.com/1.jpg",
        "primary_element": "火",
        "secondary_element": None,
        "attributes_detail": {},
        "is_custom": False,
        "is_active": True,
        "wear_count": 0,
        "last_worn_date": None,
        "is_favorite": False,
        "notes": None,
        "created_at": datetime(2025, 1, 1),
        "updated_at": datetime(2025, 1, 1),
        "gender": "中性",
        "applicable_weather": [],
        "applicable_seasons": [],
        "temperature_range": None,
        "functionality": [],
        "thickness_level": None,
        "energy_intensity": None,
    }


class TestListItems:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/items")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """获取衣橱列表"""
        mock_cursor = mock_db_pool["cursor"]
        # fetchall is called twice: items list and stats
        mock_cursor.fetchall.side_effect = [
            [mock_wardrobe_item],  # items list
            [{"primary_element": "火", "count": 1}],  # element stats
        ]
        # fetchone is called for count query
        mock_cursor.fetchone.return_value = {"total": 1}

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/wardrobe/items", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_with_filters(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """带筛选条件"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.side_effect = [
            [],  # items list
            [],  # element stats
        ]
        mock_cursor.fetchone.return_value = {"total": 0}

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get(
                "/api/v1/wardrobe/items?category=上装&element=火&page=1&limit=10",
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestGetItem:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/items/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """获取单个物品"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/wardrobe/items/1", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["name"] == "红色T恤"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """物品不存在"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/wardrobe/items/999", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestAddItem:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post("/api/v1/wardrobe/items", json={"name": "test"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_with_primary_element(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """添加衣物（已指定五行）"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                response = await async_client.post(
                    "/api/v1/wardrobe/items",
                    json={
                        "name": "红色T恤",
                        "category": "上装",
                        "primary_element": "火",
                        "item_code": "item_001",
                    },
                    headers=auth_headers,
                )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_add_with_ai_tagging(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """添加衣物（AI 自动打标，primary_element 为空触发 AI）"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        ai_result = {
            "primary_element": "火",
            "secondary_element": None,
            "color": "红色",
            "color_element": "火",
            "material": "棉",
            "material_element": "木",
            "category": "上装",
            "season": ["夏"],
            "tags": ["休闲"],
            "confidence": 0.9,
            "applicable_weather": ["晴"],
            "applicable_seasons": ["夏"],
            "suggested_name": "红色T恤",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.ai_tagging_service") as mock_ai:
                mock_ai.analyze_item = AsyncMock(return_value=ai_result)
                with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                    mock_emb.generate_embedding.return_value = [0.1] * 1024
                    response = await async_client.post(
                        "/api/v1/wardrobe/items",
                        json={"name": "红色T恤", "primary_element": "", "description": "红色棉质T恤"},
                        headers=auth_headers,
                    )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_add_error(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """添加失败"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.execute.side_effect = Exception("db error")

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/items",
                json={"name": "test", "primary_element": "火", "item_code": "t1"},
                headers=auth_headers,
            )
            assert response.status_code == 500
        finally:
            test_app.dependency_overrides.clear()


class TestUpdateItem:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.patch("/api/v1/wardrobe/items/1", json={"name": "new"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """更新成功"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={"name": "新名称"},
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_no_fields(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """无字段更新"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/1",
                json={},
                headers=auth_headers,
            )
            assert response.status_code == 400
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """物品不存在"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.patch(
                "/api/v1/wardrobe/items/999",
                json={"name": "new"},
                headers=auth_headers,
            )
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestDeleteItem:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.delete("/api/v1/wardrobe/items/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """删除成功"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.rowcount = 1

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/wardrobe/items/1", headers=auth_headers)
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """物品不存在"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.rowcount = 0

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.delete("/api/v1/wardrobe/items/999", headers=auth_headers)
            assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestPreviewTagging:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/wardrobe/items/preview-tagging",
            json={"description": "红色T恤"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_preview_success(self, async_client, auth_headers, test_app, mock_user):
        """预览打标成功"""
        ai_result = {
            "primary_element": "火",
            "secondary_element": None,
            "color": "红色",
            "color_element": "火",
            "material": "棉",
            "material_element": "木",
            "style": "休闲",
            "shape": None,
            "details": [],
            "energy_intensity": 0.8,
            "category": "上装",
            "season": ["夏"],
            "tags": ["休闲"],
            "confidence": 0.9,
            "applicable_weather": ["晴"],
            "applicable_seasons": ["夏"],
            "temperature_range": {"min": 20, "max": 35},
            "functionality": ["透气"],
            "thickness_level": "轻薄",
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.ai_tagging_service") as mock_ai:
                mock_ai.analyze_item = AsyncMock(return_value=ai_result)
                response = await async_client.post(
                    "/api/v1/wardrobe/items/preview-tagging",
                    json={"description": "红色棉质T恤"},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert data["primary_element"] == "火"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_preview_error(self, async_client, auth_headers, test_app, mock_user):
        """打标失败"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.ai_tagging_service") as mock_ai:
                mock_ai.analyze_item = AsyncMock(side_effect=Exception("AI error"))
                response = await async_client.post(
                    "/api/v1/wardrobe/items/preview-tagging",
                    json={"description": "test"},
                    headers=auth_headers,
                )
            assert response.status_code == 500
        finally:
            test_app.dependency_overrides.clear()


class TestWardrobeStats:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """获取统计"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = {"total": 10, "custom_count": 3, "referenced_count": 7}
        mock_cursor.fetchall.return_value = [{"primary_element": "火", "count": 5}, {"primary_element": "金", "count": 5}]

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.get("/api/v1/wardrobe/stats", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 10
        finally:
            test_app.dependency_overrides.clear()


class TestFeedback:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/wardrobe/feedback",
            json={"session_id": "s1", "item_source": "public", "action": "like"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_feedback_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """创建反馈成功"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "user_id": 1,
            "action": "like",
            "created_at": datetime(2025, 7, 2),
        }

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/feedback",
                json={
                    "session_id": "session-1",
                    "item_source": "public",
                    "action": "like",
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
        finally:
            test_app.dependency_overrides.clear()


class TestElementBalance:
    """五行衣橱平衡仪表盘端点"""

    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/element-balance")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_success_passes_city_and_gender(self, async_client, auth_headers, test_app, mock_user):
        """透传定位城市与性别给出入服务"""
        mock_user["preferred_city"] = "杭州"
        mock_user["gender"] = "女"
        payload = {"elements": [], "advice": [], "is_empty": True}
        with patch(
            "apps.api.services.wardrobe_analytics_service.get_element_balance",
            return_value=payload,
        ) as mocked:
            test_app.dependency_overrides[get_current_user] = lambda: mock_user
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/element-balance", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == payload
        assert mocked.call_args.args[0] == 1
        assert mocked.call_args.kwargs == {"city": "杭州", "gender": "女"}

    @pytest.mark.asyncio
    async def test_cache_hit_skips_service(self, async_client, auth_headers, test_app, mock_user):
        """Redis 可用且命中缓存时不再计算"""
        from apps.api.core.config import settings

        cached = {"elements": [], "advice": [], "cached": True}
        mock_cache = MagicMock()
        mock_cache.get_sync.return_value = cached
        with patch("apps.api.core.cache.cache", mock_cache), \
                patch("apps.api.services.wardrobe_analytics_service.get_element_balance") as mocked:
            test_app.dependency_overrides[get_current_user] = lambda: mock_user
            original = settings.redis_enabled
            settings.redis_enabled = True
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/element-balance", headers=auth_headers
                )
            finally:
                settings.redis_enabled = original
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["cached"] is True
        mocked.assert_not_called()
        mock_cache.get_sync.assert_called_once_with("wardrobe_element_balance:1")


class TestLearningSignals:
    """批次一 1.3：穿搭数据反哺显性化的学习信号聚合"""

    def test_aggregation_and_dimension_ranking(self, mock_db_pool):
        """日记套数/穿着件次正确；维度按学习量变化绝对值降序取前 3，delta=0 被过滤"""
        from apps.api.routers.wardrobe import _query_learning_signals

        cursor = mock_db_pool["cursor"]
        cursor.fetchone.return_value = {"diary_count": 5, "wear_count": 12}
        cursor.fetchall.return_value = [
            {"pref_type": "color", "recent": 12, "prior": 4},
            {"pref_type": "element", "recent": 3, "prior": 3},
            {"pref_type": "style", "recent": 1, "prior": 9},
            {"pref_type": "category", "recent": 6, "prior": 5},
            {"pref_type": "material", "recent": 4, "prior": 0},
        ]

        signals = _query_learning_signals(1)

        assert signals["diary_count_30d"] == 5
        assert signals["wear_checkin_count_30d"] == 12
        assert signals["window_days"] == 30
        assert [d["label"] for d in signals["top_changed_dimensions"]] == ["颜色", "风格", "材质"]
        assert [d["delta"] for d in signals["top_changed_dimensions"]] == [8, -8, 4]
        # 两次查询：日记聚合 + 偏好维度变化，窗口天数走参数而非拼接
        assert cursor.execute.call_count == 2
        assert 30 in cursor.execute.call_args_list[1].args[1]

    def test_zero_records(self, mock_db_pool):
        """零记录时全部为 0（前端据此不渲染学习说明）"""
        from apps.api.routers.wardrobe import _query_learning_signals

        cursor = mock_db_pool["cursor"]
        cursor.fetchone.return_value = {"diary_count": 0, "wear_count": 0}
        cursor.fetchall.return_value = []

        assert _query_learning_signals(1) == {
            "diary_count_30d": 0,
            "wear_checkin_count_30d": 0,
            "top_changed_dimensions": [],
            "window_days": 30,
        }

    def test_db_failure_degrades_to_zero(self, mock_db_pool):
        """查询异常不抛出，回落零值结构"""
        from apps.api.routers.wardrobe import _query_learning_signals

        mock_db_pool["cursor"].execute.side_effect = RuntimeError("db down")
        signals = _query_learning_signals(1)
        assert signals["diary_count_30d"] == 0
        assert signals["top_changed_dimensions"] == []

    @pytest.mark.asyncio
    async def test_preference_summary_exposes_signals(
        self, async_client, auth_headers, test_app, mock_user
    ):
        """preference-summary 响应新增 learning_signals（不新建端点）"""
        prefs = {"color": {"红色": 8, "黑色": -3}}
        signals = {
            "diary_count_30d": 2,
            "wear_checkin_count_30d": 7,
            "top_changed_dimensions": [{"key": "color", "label": "颜色", "delta": 5}],
            "window_days": 30,
        }
        with patch(
            "apps.api.services.preference_service.preference_service.get_user_preferences",
            return_value=prefs,
        ), patch(
            "apps.api.routers.wardrobe._query_learning_signals",
            return_value=signals,
        ):
            test_app.dependency_overrides[get_current_user] = lambda: mock_user
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/preference-summary", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        body = response.json()
        assert body["learning_signals"] == signals
        assert body["dimensions"][0]["key"] == "color"
