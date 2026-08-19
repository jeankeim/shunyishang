"""
衣橱批量上传路由测试
覆盖 wardrobe.py 三个批量端点：
- POST /wardrobe/batch/recognize（含单件失败降级、超量拒绝）
- POST /wardrobe/batch/wuxing-analysis（规则引擎查表 + 喜用比对 + 无八字跳过）
- POST /wardrobe/batch/items（部分成功语义、超量拒绝）
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


@pytest.fixture
def mock_wardrobe_item():
    """模拟 user_wardrobe 入库 RETURNING 行"""
    return {
        "id": 1,
        "user_id": 1,
        "item_code": None,
        "name": "白色衬衫",
        "category": "上装",
        "image_url": "http://img.com/1.jpg",
        "primary_element": "金",
        "secondary_element": None,
        "attributes_detail": {},
        "is_custom": True,
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


def _recognize_result(overrides=None):
    """构造工作流归一化后的单件识别结果"""
    base = {
        "suggested_name": "白色棉质衬衫",
        "description": "白色长袖衬衫，纯棉面料",
        "category": "上装",
        "gender": "中性",
        "applicable_seasons": ["春", "秋"],
        "functionality": ["日常"],
        "color": "白色",
        "material": "纯棉",
        "style": "简约",
        "confidence": 0.9,
        "needs_manual_review": False,
    }
    if overrides:
        base.update(overrides)
    return base


class TestBatchRecognize:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/wardrobe/batch/recognize",
            json={"items": [{"index": 0, "image_url": "http://img.com/1.jpg"}]},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_over_limit_rejected(self, async_client, auth_headers, test_app, mock_user):
        """超过每批 5 件上限应被拒绝（schema 校验或路由校验）"""
        items = [{"index": i, "image_url": f"http://img.com/{i}.jpg"} for i in range(6)]
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/batch/recognize",
                json={"items": items},
                headers=auth_headers,
            )
            assert response.status_code in (400, 422)
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_recognize_success(self, async_client, auth_headers, test_app, mock_user):
        """批量识别成功，结果与请求同序"""
        state = {
            "results": [_recognize_result(), _recognize_result({"suggested_name": "黑色长裤", "category": "下装"})],
            "llm_token_usage": {"model": "qwen-vl-max", "input_tokens": 100, "output_tokens": 50},
        }
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.routers.wardrobe.run_batch_tagging",
                new=AsyncMock(return_value=state),
            ):
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/recognize",
                    json={"items": [
                        {"index": 0, "image_url": "http://img.com/0.jpg"},
                        {"index": 1, "image_url": "http://img.com/1.jpg"},
                    ]},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            assert data["results"][0]["suggested_name"] == "白色棉质衬衫"
            assert data["results"][1]["suggested_name"] == "黑色长裤"
            assert data["results"][0]["needs_manual_review"] is False
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_single_item_failure_degrades(self, async_client, auth_headers, test_app, mock_user):
        """单件识别失败降级：该件 needs_manual_review=true，不阻断同批其他件"""
        state = {
            "results": [
                _recognize_result(),
                _recognize_result({
                    "error": "VL 识别超时",
                    "needs_manual_review": True,
                    "suggested_name": "",
                    "confidence": 0.0,
                }),
            ],
        }
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.routers.wardrobe.run_batch_tagging",
                new=AsyncMock(return_value=state),
            ):
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/recognize",
                    json={"items": [
                        {"index": 0, "image_url": "http://img.com/0.jpg"},
                        {"index": 1, "image_url": "http://img.com/1.jpg"},
                    ]},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["needs_manual_review"] is False
            assert data["results"][1]["needs_manual_review"] is True
            assert data["results"][1]["error"] == "VL 识别超时"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_workflow_exception_returns_502(self, async_client, auth_headers, test_app, mock_user):
        """工作流整体异常 → 502"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.routers.wardrobe.run_batch_tagging",
                new=AsyncMock(side_effect=Exception("graph error")),
            ):
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/recognize",
                    json={"items": [{"index": 0, "image_url": "http://img.com/0.jpg"}]},
                    headers=auth_headers,
                )
            assert response.status_code == 502
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_all_failed_returns_502(self, async_client, auth_headers, test_app, mock_user):
        """全部失败（无 results）→ 502"""
        state = {"results": [], "error": "全部衣物识别失败，请稍后重试或手动填写"}
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch(
                "apps.api.routers.wardrobe.run_batch_tagging",
                new=AsyncMock(return_value=state),
            ):
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/recognize",
                    json={"items": [{"index": 0, "image_url": "http://img.com/0.jpg"}]},
                    headers=auth_headers,
                )
            assert response.status_code == 502
        finally:
            test_app.dependency_overrides.clear()


class TestBatchWuxingAnalysis:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/wardrobe/batch/wuxing-analysis",
            json={"items": [{"index": 0}]},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_with_xiyong_match(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """有八字资料：规则引擎查表 + 喜用比对（白色→金，命中喜用神）"""
        mock_cursor = mock_db_pool["cursor"]
        # _get_user_xiyong: SELECT xiyong_elements, bazi → tuple 行
        mock_cursor.fetchone.return_value = (["金", "水"], {"avoid_elements": ["木", "火"]})

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/batch/wuxing-analysis",
                json={"items": [
                    {"index": 0, "name": "白色衬衫", "category": "上装",
                     "color": "白色", "material": "纯棉", "style": "简约"},
                ]},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["xiyong_elements"] == ["金", "水"]
            r = data["results"][0]
            assert r["primary_element"] == "金"
            assert r["xiyong_match"] == "喜用匹配"
            assert r["xiyong_advice"]
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_with_avoid_element(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """主五行命中忌讳五行 → 忌讳五行标签"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (["水"], {"avoid_elements": ["金"]})

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/batch/wuxing-analysis",
                json={"items": [
                    {"index": 0, "color": "白色", "material": "纯棉", "style": "简约"},
                ]},
                headers=auth_headers,
            )
            assert response.status_code == 200
            r = response.json()["results"][0]
            assert r["primary_element"] == "金"
            assert r["xiyong_match"] == "忌讳五行"
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_no_bazi_skips_comparison(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """无八字资料：跳过喜用比对，仅输出五行结果"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = (None, None)

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/batch/wuxing-analysis",
                json={"items": [
                    {"index": 0, "color": "白色", "material": "纯棉", "style": "简约"},
                ]},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["xiyong_elements"] == []
            r = data["results"][0]
            assert r["primary_element"]  # 五行结果仍存在
            assert r["xiyong_match"] is None
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unknown_values_fallback(self, async_client, auth_headers, test_app, mock_db_pool, mock_user):
        """三维全部查表未命中：兜底 primary_element=金，无喜用资料则无比对"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = None  # 用户行不存在

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/batch/wuxing-analysis",
                json={"items": [
                    {"index": 0, "color": "不存在的颜色", "material": "未知材质", "style": "未知风格"},
                ]},
                headers=auth_headers,
            )
            assert response.status_code == 200
            r = response.json()["results"][0]
            assert r["primary_element"] == "金"
            assert r["color_element"] is None
            assert r["xiyong_match"] is None
        finally:
            test_app.dependency_overrides.clear()


class TestBatchAddItems:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/wardrobe/batch/items",
            json={"items": [{"name": "test"}]},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_over_limit_rejected(self, async_client, auth_headers, test_app, mock_user):
        """超过每批 5 件上限应被拒绝"""
        items = [{"name": f"衣物{i}", "primary_element": "金"} for i in range(6)]
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/wardrobe/batch/items",
                json={"items": items},
                headers=auth_headers,
            )
            assert response.status_code in (400, 422)
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_batch_add_all_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """批量入库全部成功"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/items",
                    json={"items": [
                        {"name": "白色衬衫", "category": "上装", "primary_element": "金",
                         "color": "白色", "color_element": "金", "material": "纯棉",
                         "style": "简约", "xiyong_match": "喜用匹配", "xiyong_advice": "宜常穿"},
                        {"name": "黑色长裤", "category": "下装", "primary_element": "水"},
                    ]},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert len(data["created"]) == 2
            assert data["failed"] == []
            # 事务末尾统一 commit
            mock_db_pool["conn"].commit.assert_called()
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_batch_add_partial_success(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """部分成功：第二件 INSERT 失败计入 failed，第一件照常入库"""
        mock_cursor = mock_db_pool["cursor"]
        # 第一件 execute 成功 + fetchone 返回行；第二件 execute 抛异常
        mock_cursor.execute.side_effect = [None, Exception("db error on item 2")]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/items",
                    json={"items": [
                        {"name": "白色衬衫", "primary_element": "金"},
                        {"name": "黑色长裤", "primary_element": "水"},
                    ]},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert len(data["created"]) == 1
            assert len(data["failed"]) == 1
            assert data["failed"][0]["index"] == 1
            assert "db error on item 2" in data["failed"][0]["reason"]
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_embedding_failure_does_not_block(self, async_client, auth_headers, test_app, mock_db_pool, mock_user, mock_wardrobe_item):
        """Embedding 生成失败降级 NULL 向量，照常入库"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchone.return_value = mock_wardrobe_item

        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            with patch("apps.api.routers.wardrobe.embedding_service") as mock_emb:
                mock_emb.generate_embedding.side_effect = Exception("embedding down")
                response = await async_client.post(
                    "/api/v1/wardrobe/batch/items",
                    json={"items": [{"name": "白色衬衫", "primary_element": "金"}]},
                    headers=auth_headers,
                )
            assert response.status_code == 200
            data = response.json()
            assert len(data["created"]) == 1
            assert data["failed"] == []
        finally:
            test_app.dependency_overrides.clear()
