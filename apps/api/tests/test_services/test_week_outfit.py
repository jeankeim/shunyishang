"""
一周穿搭日历 / 场景急救测试

覆盖 daily_outfit_service 的 _build_outfit 重构与一周、场景能力：
- 7 天结构完整（date/weekday/温度/天气/幸运元素/成套/completeness/match_score）
- 跨天复用上限生效（同品类单品不被无限复用）
- 天气兜底（预报缺失、字段异常）不抛异常
- _build_outfit 重构后每日穿搭响应字段无回归
- 端点缓存命中、date 入参校验、未知场景拒绝
"""

import re
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.routers.auth import get_current_user
from apps.api.services import daily_outfit_service as dos

CITY = "杭州"


@pytest.fixture
def mock_user():
    return {"id": 1, "user_code": "TEST001", "phone": None, "email": "test@test.com"}


def _wardrobe(prefix: str = "IT", accessory_count: int = 5) -> list:
    """构造品类齐全的衣橱：4 上装 / 4 下装 / 4 鞋履 / N 配饰，分数依次递减"""
    rows = []
    item_id = 1
    for category, count in (("上装", 4), ("下装", 4), ("鞋履", 4), ("配饰", accessory_count)):
        for _ in range(count):
            rows.append({
                "id": item_id,
                "user_id": 1,
                "item_code": f"{prefix}{item_id}",
                "name": f"{category}{item_id}",
                "category": category,
                "image_url": None,
                "primary_element": "木",
                "secondary_element": None,
                "attributes_detail": {},
                "wear_count": 0,
                "is_favorite": False,
                "applicable_weather": [],
                "applicable_seasons": ["夏"],
                "temperature_range": None,
                "functionality": ["透气"],
                "thickness_level": "轻薄",
                "energy_intensity": 0.5,
            })
            item_id += 1
    return rows


def _forecast(days: int = 7, start: date | None = None) -> list:
    start = start or date.today()
    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "temperature_max": 30,
            "temperature_min": 24,
            "weather_desc": "晴" if i % 2 == 0 else "小雨",
            "humidity": 60,
            "wind_level": 2,
        }
        for i in range(days)
    ]


@pytest.fixture
def mocked_week(monkeypatch):
    """把一周穿搭的外部依赖全部打桩：八字/运势/偏好/衣橱/天气预报"""
    calls = {"wardrobe": 0, "prefs": 0}

    def _fake_wardrobe(user_id):
        calls["wardrobe"] += 1
        return _wardrobe()

    def _fake_prefs(user_id):
        calls["prefs"] += 1
        return {}

    monkeypatch.setattr(dos, "get_user_bazi", lambda uid: {
        "suggested_elements": ["木", "水"], "avoid_elements": ["金"],
    })
    monkeypatch.setattr(dos, "calculate_daily_fortune", lambda bazi, day: {
        "lucky_elements": {"elements": ["木"], "colors": ["绿色"]},
        "overall_score": 78,
    })
    monkeypatch.setattr(dos, "_query_wardrobe", _fake_wardrobe)
    monkeypatch.setattr(dos, "_get_user_prefs", _fake_prefs)
    monkeypatch.setattr(dos, "_get_weather_sync", lambda city: {
        "city": city, "temperature": 27, "temperature_max": 30,
        "temperature_min": 24, "weather": "晴", "humidity": 60, "element": "火",
    })
    monkeypatch.setattr(dos, "_get_user_city", lambda uid: CITY)
    return calls


class TestWeekStructure:
    def test_seven_days_complete(self, mocked_week):
        """7 天逐日返回约定字段，且天气取自预报而非实时天气"""
        with patch.object(dos, "_get_forecast", return_value=_forecast()):
            week = dos.generate_week_outfit(1)

        assert week["city"] == CITY
        assert week["is_empty"] is False
        assert len(week["days"]) == 7
        first = week["days"][0]
        for key in ("date", "weekday", "temp_min", "temp_max", "weather",
                    "lucky_elements", "outfit_items", "completeness", "match_score"):
            assert key in first, f"缺少字段 {key}"
        assert first["temp_min"] == 24 and first["temp_max"] == 30
        assert first["weekday"] in ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
        assert first["lucky_elements"] == ["木"]
        assert first["completeness"]["missing"] == []
        assert 0 <= first["match_score"] <= 100
        # 日期连续且不重复
        dates = [d["date"] for d in week["days"]]
        assert dates == sorted(dates) and len(set(dates)) == 7

    def test_wardrobe_queried_once(self, mocked_week):
        """八字/偏好/衣橱在 7 天之间只查一次，避免 7 次重复 IO"""
        with patch.object(dos, "_get_forecast", return_value=_forecast()):
            dos.generate_week_outfit(1)
        assert mocked_week["wardrobe"] == 1
        assert mocked_week["prefs"] == 1

    def test_empty_wardrobe(self, mocked_week):
        """空衣橱：每天都是空成套并给出缺口，不抛异常"""
        with patch.object(dos, "_query_wardrobe", return_value=[]), \
                patch.object(dos, "_get_forecast", return_value=_forecast()):
            week = dos.generate_week_outfit(1)
        assert week["is_empty"] is True
        assert all(d["outfit_items"] == [] for d in week["days"])
        assert week["days"][0]["completeness"]["missing"]


class TestCrossDayReuse:
    def _caps(self, week):
        counts: dict = {}
        for day in week["days"]:
            for it in day["outfit_items"]:
                counts.setdefault((it["category"], it["id"]), 0)
                counts[(it["category"], it["id"])] += 1
        return counts

    def test_reuse_within_cap(self, mocked_week):
        """衣橱容量足够时：上装/配饰≤3 次，下装/鞋履≤2 次"""
        with patch.object(dos, "_get_forecast", return_value=_forecast()):
            week = dos.generate_week_outfit(1)

        caps = {"上装": 3, "下装": 2, "鞋履": 2, "配饰": 3}
        counts = self._caps(week)
        assert counts, "应至少选出单品"
        for (category, item_id), used in counts.items():
            assert used <= caps[category], f"{category} #{item_id} 一周被用 {used} 次"

    def test_not_the_same_outfit_every_day(self, mocked_week):
        """7 天不应是同一套方案（白 T 复读机）"""
        with patch.object(dos, "_get_forecast", return_value=_forecast()):
            week = dos.generate_week_outfit(1)
        outfits = {tuple(sorted(i["id"] for i in d["outfit_items"])) for d in week["days"]}
        assert len(outfits) >= 4, f"7 天只有 {len(outfits)} 种组合，复用过度"

    def test_tiny_wardrobe_breaks_cap_instead_of_empty(self, mocked_week):
        """容量不足（配饰只 1 件）时宁可超上限，也不能让成套缺位"""
        with patch.object(dos, "_query_wardrobe", return_value=_wardrobe(accessory_count=1)), \
                patch.object(dos, "_get_forecast", return_value=_forecast()):
            week = dos.generate_week_outfit(1)
        counts = self._caps(week)
        accessory_uses = [used for (cat, _), used in counts.items() if cat == "配饰"]
        assert sum(accessory_uses) == 7, "配饰每天仍应出一件"
        assert max(accessory_uses) > 3


class TestWeatherFallback:
    def test_missing_forecast_falls_back_to_today(self, mocked_week):
        """预报为空：用当日实时天气补齐 7 天，不抛"""
        with patch.object(dos, "_get_forecast", return_value=[]):
            week = dos.generate_week_outfit(1)
        assert len(week["days"]) == 7
        assert week["days"][0]["weather"] == "晴"
        assert all(d["outfit_items"] for d in week["days"])

    def test_partial_forecast(self, mocked_week):
        """预报只有 3 天（如 3d 接口）：其余天走兜底，仍出 7 天"""
        with patch.object(dos, "_get_forecast", return_value=_forecast(days=3)):
            week = dos.generate_week_outfit(1)
        assert len(week["days"]) == 7
        assert week["days"][2]["temp_max"] == 30

    def test_forecast_exception_swallowed(self, mocked_week):
        """预报函数抛异常（网络）时降级为空列表，不影响出方案"""
        import packages.utils.weather_forecast as wf
        with patch.object(wf, "get_destination_weather", side_effect=RuntimeError("boom")):
            assert dos._get_forecast(CITY, 7) == []
        week = dos.generate_week_outfit(1)
        assert len(week["days"]) == 7

    def test_bad_temperature_fields(self):
        """预报字段类型异常时取默认值，温度不 NaN"""
        weather = dos._weather_from_forecast(
            {"temperature_max": None, "temperature_min": "abc", "weather_desc": ""}, CITY
        )
        assert weather["temperature_max"] == 25
        assert weather["temperature_min"] == 15
        assert weather["weather"] == "晴"
        assert weather["element"] in ("金", "木", "水", "火", "土")


class TestSingleDaySwap:
    def test_response_shape_matches_daily(self, mocked_week):
        """单日换一套的响应结构与每日穿搭完全一致（前端可复用同一渲染）"""
        target = date.today() + timedelta(days=2)
        with patch.object(dos, "_get_forecast", return_value=_forecast()):
            single = dos.generate_week_day_outfit(1, target, batch_index=1)
            daily = dos.generate_daily_outfit(1, batch_index=0)
        assert sorted(single.keys()) == sorted(daily.keys())
        assert single["date"] == target.isoformat()
        assert len(single["outfit_items"]) == len(daily["outfit_items"])

    def test_batch_changes_selection(self, mocked_week):
        """同一天的 batch 0 / 1 不重合"""
        target = date.today() + timedelta(days=1)
        with patch.object(dos, "_get_forecast", return_value=_forecast()):
            a = dos.generate_week_day_outfit(1, target, batch_index=0)
            b = dos.generate_week_day_outfit(1, target, batch_index=1)
        assert {i["id"] for i in a["outfit_items"]}.isdisjoint(
            {i["id"] for i in b["outfit_items"]}
        )


class TestDailyRegression:
    """_build_outfit 重构后，每日穿搭的对外契约保持不变"""

    def test_response_keys_and_content(self, mocked_week):
        result = dos.generate_daily_outfit(1, batch_index=0)
        assert set(result) == {
            "outfit_items", "reasoning", "weather_summary",
            "fortune_summary", "style_tip", "match_score", "completeness", "date",
        }
        assert result["date"] == date.today().isoformat()
        assert result["weather_summary"]["city"] == CITY
        assert result["fortune_summary"]["overall_score"] == 78
        assert result["reasoning"] and result["style_tip"]
        assert len(result["outfit_items"]) == 5
        assert all(
            {"id", "name", "category", "image_url", "primary_element",
             "secondary_element", "wear_count", "is_favorite", "match_score"} <= set(it)
            for it in result["outfit_items"]
        )

    def test_empty_wardrobe_contract(self, mocked_week):
        with patch.object(dos, "_query_wardrobe", return_value=[]):
            result = dos.generate_daily_outfit(1)
        assert result["outfit_items"] == []
        assert result["match_score"] == 0
        assert result["completeness"]["missing"]

    def test_city_override_used(self, mocked_week):
        with patch.object(dos, "_get_weather_sync", wraps=dos._get_weather_sync) as spy:
            dos.generate_daily_outfit(1, city_override="北京")
        spy.assert_called_once_with("北京")


class TestSceneBonus:
    """场景加成改变排序，未知场景兜底为无加成"""

    _ITEMS = [
        {"id": 1, "name": "金项链", "category": "配饰", "primary_element": "金",
         "secondary_element": None, "attributes_detail": {"款式": {"风格": "简约"}}},
        {"id": 2, "name": "木手串", "category": "配饰", "primary_element": "木",
         "secondary_element": None, "attributes_detail": {}},
    ]

    def _score(self, item, scene):
        return dos._score_item(
            item=item, lucky_elements=[], lucky_colors=[],
            suggested_elements=[], avoid_elements=[],
            temperature=22, weather_element="土", season="夏",
            user_prefs={}, scene=scene,
        )

    def test_scene_changes_ranking(self):
        assert self._score(self._ITEMS[0], None) == self._score(self._ITEMS[1], None)
        gold = self._score(self._ITEMS[0], "面试")   # 面试 primary 金
        wood = self._score(self._ITEMS[1], "面试")
        assert gold > wood, "场景主元素单品应更高分"

    def test_unknown_scene_no_bonus(self):
        base = self._score(self._ITEMS[0], None)
        assert self._score(self._ITEMS[0], "不存在的场景") == base

    def test_bonus_capped(self):
        """主元素 + 风格全命中时也不超过 SCENE_BONUS_CAP"""
        hit = self._score(self._ITEMS[0], "面试")
        none = self._score(self._ITEMS[0], None)
        assert 0 < hit - none <= dos.SCENE_BONUS_CAP

    def test_scene_rescue_service_fields(self, mocked_week):
        with patch.object(dos, "_query_wardrobe", return_value=[
            dict(i, primary_element=("金" if i["category"] == "上装" else "木"))
            for i in _wardrobe()
        ]):
            result = dos.generate_scene_rescue(1, "面试")
        assert result["scene"] == "面试"
        assert result["scene_elements"]["primary"] == ["金"]
        assert result["scene_advice"].startswith("面试讲究")
        assert result["outfit_items"], "急救搭配必须成套出物"
        assert "scene_advice" in result and "reasoning" in result


class TestWeekOutfitEndpoint:
    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        response = await async_client.get("/api/v1/recommend/week-outfit")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_date(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            bad = await async_client.get(
                "/api/v1/recommend/week-outfit?date=2026-13-45", headers=auth_headers
            )
            past = await async_client.get(
                "/api/v1/recommend/week-outfit?date=2000-01-01", headers=auth_headers
            )
            far = await async_client.get(
                "/api/v1/recommend/week-outfit?date="
                + (date.today() + timedelta(days=30)).isoformat(),
                headers=auth_headers,
            )
        finally:
            test_app.dependency_overrides.clear()
        assert bad.status_code == 422
        assert past.status_code == 422
        assert far.status_code == 422

    @pytest.mark.asyncio
    async def test_week_success(self, async_client, auth_headers, test_app, mock_user):
        payload = {"city": CITY, "start_date": date.today().isoformat(), "days": []}
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        with patch("apps.api.services.daily_outfit_service.generate_week_outfit",
                   return_value=payload) as mocked:
            try:
                response = await async_client.get(
                    "/api/v1/recommend/week-outfit?city=杭州", headers=auth_headers
                )
            finally:
                test_app.dependency_overrides.clear()
        assert response.status_code == 200
        assert response.json() == payload
        mocked.assert_called_once_with(1, city_override="杭州")

    @pytest.mark.asyncio
    async def test_cache_hit_skips_service(self, async_client, auth_headers, test_app, mock_user):
        from apps.api.core.config import settings

        cached = {"city": CITY, "cached": True, "days": []}
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=cached)
        mock_cache.set = AsyncMock()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        expected_key = f"week_outfit:1:{monday.isoformat()}:default"

        with patch("apps.api.routers.recommend.cache", mock_cache), \
                patch("apps.api.services.daily_outfit_service.generate_week_outfit") as mocked:
            original = settings.redis_enabled
            settings.redis_enabled = True
            test_app.dependency_overrides[get_current_user] = lambda: mock_user
            try:
                response = await async_client.get(
                    "/api/v1/recommend/week-outfit", headers=auth_headers
                )
            finally:
                settings.redis_enabled = original
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["cached"] is True
        mocked.assert_not_called()
        mock_cache.get.assert_awaited_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_single_day_cached_separately(self, async_client, auth_headers, test_app, mock_user):
        from apps.api.core.config import settings

        target = date.today() + timedelta(days=1)
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        day_payload = {"outfit_items": [], "date": target.isoformat()}

        with patch("apps.api.routers.recommend.cache", mock_cache), \
                patch("apps.api.services.daily_outfit_service.generate_week_day_outfit",
                      return_value=day_payload) as mocked:
            original = settings.redis_enabled
            settings.redis_enabled = True
            test_app.dependency_overrides[get_current_user] = lambda: mock_user
            try:
                response = await async_client.get(
                    f"/api/v1/recommend/week-outfit?date={target.isoformat()}&batch_index=2",
                    headers=auth_headers,
                )
            finally:
                settings.redis_enabled = original
                test_app.dependency_overrides.clear()

        assert response.status_code == 200
        mocked.assert_called_once_with(1, target, batch_index=2, city_override=None)
        called_key = mock_cache.set.await_args.args[0]
        assert called_key == f"week_outfit_day:1:{target.isoformat()}:2:default"


class TestSceneRescueEndpoint:
    @pytest.mark.asyncio
    async def test_requires_auth(self, async_client):
        response = await async_client.post(
            "/api/v1/recommend/scene-rescue", json={"scene": "面试"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_scene_rejected(self, async_client, auth_headers, test_app, mock_user):
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            response = await async_client.post(
                "/api/v1/recommend/scene-rescue",
                json={"scene": "外星Meeting"}, headers=auth_headers,
            )
        finally:
            test_app.dependency_overrides.clear()
        assert response.status_code == 422
        assert "未知场景" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cache_isolated_by_scene(self, async_client, auth_headers, test_app, mock_user):
        """同一天不同场景的缓存键互不覆盖"""
        keys = []
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(side_effect=lambda k, v, ttl=None: keys.append(k))
        payload = {"scene": "约会", "outfit_items": [], "scene_advice": "..."}

        with patch("apps.api.routers.recommend.cache", mock_cache), \
                patch("apps.api.core.config.settings.redis_enabled", True), \
                patch("apps.api.services.daily_outfit_service.generate_scene_rescue",
                      return_value=payload) as mocked:
            test_app.dependency_overrides[get_current_user] = lambda: mock_user
            try:
                for scene in ("面试", "约会"):
                    response = await async_client.post(
                        "/api/v1/recommend/scene-rescue",
                        json={"scene": scene}, headers=auth_headers,
                    )
                    assert response.status_code == 200
            finally:
                test_app.dependency_overrides.clear()

        assert [c.args[1] for c in mocked.call_args_list] == ["面试", "约会"]
        assert len(keys) == 2 and len(set(keys)) == 2
        assert all(
            re.match(rf"scene_rescue:1:(面试|约会):\d{{4}}-\d{{2}}-\d{{2}}:default", k)
            for k in keys
        )
