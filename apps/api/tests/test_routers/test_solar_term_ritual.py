"""
换季开柜仪式路由测试（批次三 3.3）

覆盖 GET /api/v1/wardrobe/solar-term-ritual：
- 登录校验
- 透传北京自然日给 service（不接受客户端传日期，避免缓存被绕开）
- 日级缓存命中 / 回写（key 带日期、TTL 到当日结束）
- 未启用 Redis 时完全不碰缓存

service 与 cache 全部 mock，不连真实库。
"""
import pytest
from unittest.mock import patch

from apps.api.core.time_utils import today_cn
from apps.api.routers.auth import get_current_user


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


RITUAL = {
    "solar_term": {"name": "立春", "date": "2026-02-04", "element": "木",
                   "description": "春回大地", "outfit_hint": "轻薄外套", "season": "春",
                   "days_until": 3},
    "current_term": {"name": "大寒", "date": "2026-01-20", "season": "冬"},
    "next_season": "春",
    "expected_thickness": ["适中", "轻薄"],
    "is_season_boundary": True,
    "store_away": {"items": [], "total": 0, "reason": "先收厚外套"},
    "take_out": {"items": [], "total": 0, "reason": "拿出来穿一次"},
    "yi_ji": {"advice": "宜浅色系", "gap_elements": []},
    "has_action": False,
}


# ============================================================
# GET /wardrobe/solar-term-ritual
# ============================================================

class TestSolarTermRitual:
    @pytest.mark.asyncio
    async def test_no_auth(self, async_client):
        response = await async_client.get("/api/v1/wardrobe/solar-term-ritual")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_ritual_with_today(self, async_client, auth_headers, test_app, mock_user):
        """未启用缓存时直接算，且日期由服务端北京时间决定"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("apps.api.core.config.settings.redis_enabled", False), \
                patch("apps.api.core.cache.cache") as mock_cache, \
                patch("apps.api.services.solar_term_service.solar_term_service") as mock_svc:
            mock_svc.get_wardrobe_ritual.return_value = RITUAL
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/solar-term-ritual", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == RITUAL
        call = mock_svc.get_wardrobe_ritual.call_args
        assert call.args == (1,)
        assert call.kwargs["today"] == today_cn()
        mock_cache.get_sync.assert_not_called()
        mock_cache.set_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_service(self, async_client, auth_headers, test_app, mock_user):
        """当日已有缓存则直接返回，不再扫衣橱"""
        cached = dict(RITUAL, next_season="夏")
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("apps.api.core.config.settings.redis_enabled", True), \
                patch("apps.api.core.cache.cache") as mock_cache, \
                patch("apps.api.services.solar_term_service.solar_term_service") as mock_svc:
            mock_cache.get_sync.return_value = cached
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/solar-term-ritual", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.json() == cached
        mock_svc.get_wardrobe_ritual.assert_not_called()
        key = mock_cache.get_sync.call_args.args[0]
        assert key.startswith("wardrobe_solar_ritual:1:")
        mock_cache.set_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_writes_with_day_ttl(self, async_client, auth_headers, test_app, mock_user):
        """计算结果回写缓存，TTL 到当日结束（至少留 600 秒兜底）"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("apps.api.core.config.settings.redis_enabled", True), \
                patch("apps.api.core.cache.cache") as mock_cache, \
                patch("apps.api.services.solar_term_service.solar_term_service") as mock_svc:
            mock_cache.get_sync.return_value = None
            mock_svc.get_wardrobe_ritual.return_value = RITUAL
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/solar-term-ritual", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        key, value = mock_cache.set_sync.call_args.args
        ttl = mock_cache.set_sync.call_args.kwargs["ttl"]
        assert value == RITUAL
        assert key == f"wardrobe_solar_ritual:1:{today_cn().isoformat()}"
        assert 600 <= ttl <= 86400

    @pytest.mark.asyncio
    async def test_cache_read_error_falls_back_to_service(
        self, async_client, auth_headers, test_app, mock_user
    ):
        """Redis 读失败不阻断开柜仪式"""
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("apps.api.core.config.settings.redis_enabled", True), \
                patch("apps.api.core.cache.cache") as mock_cache, \
                patch("apps.api.services.solar_term_service.solar_term_service") as mock_svc:
            mock_cache.get_sync.side_effect = RuntimeError("redis down")
            mock_cache.set_sync.side_effect = RuntimeError("redis down")
            mock_svc.get_wardrobe_ritual.return_value = RITUAL
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/solar-term-ritual", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json() == RITUAL

    @pytest.mark.asyncio
    async def test_missing_user_id_rejected(self, async_client, auth_headers, test_app):
        """token 里解不出用户 id → 401，不调 service"""
        test_app.dependency_overrides[get_current_user] = lambda: {"id": None, "user_code": "X"}
        with patch("apps.api.services.solar_term_service.solar_term_service") as mock_svc:
            try:
                response = await async_client.get(
                    "/api/v1/wardrobe/solar-term-ritual", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()

        assert response.status_code == 401
        mock_svc.get_wardrobe_ritual.assert_not_called()
