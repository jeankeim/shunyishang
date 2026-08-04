"""
city_resolver 城市解析模块测试

覆盖：内置映射表命中、和风城市搜索API动态解析、解析结果缓存、
全国城市搜索、坐标反查城市。
"""

from unittest.mock import patch, MagicMock

import pytest

from packages.utils.city_resolver import (
    CITY_ID_MAP,
    resolve_city_id_sync,
    resolve_city_id,
    search_cities,
    reverse_geocode,
    _pick_best_match,
    clear_resolved_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """每个用例前后清空动态解析缓存"""
    clear_resolved_cache()
    yield
    clear_resolved_cache()


def _mock_geo_response(name="昆山", city_id="101190404", adm1="江苏省", adm2="苏州市"):
    """构造和风城市搜索 API 的响应数据"""
    return [{
        "name": name,
        "id": city_id,
        "lat": "31.38",
        "lon": "120.98",
        "adm1": adm1,
        "adm2": adm2,
        "country": "中国",
    }]


class TestCityIdMap:
    """内置映射表完整性"""

    def test_common_cities_exist(self):
        assert "北京" in CITY_ID_MAP
        assert "上海" in CITY_ID_MAP
        assert "三亚" in CITY_ID_MAP
        assert "拉萨" in CITY_ID_MAP

    def test_map_has_100_plus_cities(self):
        assert len(CITY_ID_MAP) >= 100


class TestResolveCityIdSync:
    """同步城市解析"""

    def test_map_hit_without_api_key(self):
        """内置映射表命中，无需 API Key"""
        assert resolve_city_id_sync("杭州", None) == CITY_ID_MAP["杭州"]

    def test_no_api_key_unknown_city_returns_none(self):
        """未配置 API Key 且不在映射表中，返回 None"""
        assert resolve_city_id_sync("昆山", None) is None

    def test_geo_lookup_resolves_unknown_city(self):
        """映射表未命中时调用城市搜索 API 解析"""
        with patch("packages.utils.city_resolver._geo_lookup_sync", return_value=_mock_geo_response()):
            assert resolve_city_id_sync("昆山", "fake_key") == "101190404"

    def test_resolved_result_cached(self):
        """解析成功后缓存，二次查询不再调用 API"""
        with patch("packages.utils.city_resolver._geo_lookup_sync", return_value=_mock_geo_response()) as mock_geo:
            resolve_city_id_sync("昆山", "fake_key")
            resolve_city_id_sync("昆山", "fake_key")
            assert mock_geo.call_count == 1

    def test_geo_lookup_no_result_returns_none(self):
        """API 无匹配结果返回 None"""
        with patch("packages.utils.city_resolver._geo_lookup_sync", return_value=[]):
            assert resolve_city_id_sync("不存在的城市", "fake_key") is None

    def test_empty_city_returns_none(self):
        assert resolve_city_id_sync("", "fake_key") is None
        assert resolve_city_id_sync(None, "fake_key") is None

    def test_overseas_result_filtered(self):
        """非中国境内结果被过滤"""
        overseas = [{"name": "东京", "id": "xxx", "country": "日本"}]
        with patch("packages.utils.city_resolver._geo_lookup_sync", return_value=overseas):
            assert resolve_city_id_sync("东京", "fake_key") is None


class TestResolveCityIdAsync:
    """异步城市解析"""

    @pytest.mark.asyncio
    async def test_map_hit(self):
        assert await resolve_city_id("北京", None) == CITY_ID_MAP["北京"]

    @pytest.mark.asyncio
    async def test_geo_lookup_resolves(self):
        with patch("packages.utils.city_resolver._geo_lookup_async", return_value=_mock_geo_response()):
            assert await resolve_city_id("昆山", "fake_key") == "101190404"

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        assert await resolve_city_id("昆山", None) is None


class TestPickBestMatch:
    """搜索结果挑选逻辑"""

    def test_exact_name_preferred(self):
        candidates = [
            {"name": "昆山", "id": "1", "country": "中国"},
            {"name": "昆山", "id": "2", "country": "中国"},
        ]
        assert _pick_best_match(candidates, "昆山")["id"] == "1"

    def test_fallback_to_first_china_result(self):
        candidates = [{"name": "苏州市", "id": "1", "country": "中国"}]
        assert _pick_best_match(candidates, "苏州")["id"] == "1"

    def test_all_overseas_returns_none(self):
        candidates = [{"name": "巴黎", "id": "1", "country": "法国"}]
        assert _pick_best_match(candidates, "巴黎") is None


class TestSearchCities:
    """全国城市搜索"""

    @pytest.mark.asyncio
    async def test_local_matches_first(self):
        """本地映射表命中直接返回"""
        result = await search_cities("杭州", None)
        assert "杭州" in result

    @pytest.mark.asyncio
    async def test_api_supplements_when_local_insufficient(self):
        """本地结果不足时调用 API 补充"""
        with patch("packages.utils.city_resolver._geo_lookup_async", return_value=_mock_geo_response()):
            result = await search_cities("昆", "fake_key")
        assert "昆山" in result

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        assert await search_cities("", "fake_key") == []
        assert await search_cities("  ", "fake_key") == []

    @pytest.mark.asyncio
    async def test_dedup_and_limit(self):
        """结果去重且不超过 limit"""
        with patch("packages.utils.city_resolver._geo_lookup_async", return_value=_mock_geo_response()):
            result = await search_cities("州", "fake_key", limit=3)
        assert len(result) <= 3
        assert len(result) == len(set(result))


class TestReverseGeocode:
    """坐标反查城市"""

    @pytest.mark.asyncio
    async def test_district_promoted_to_parent_city(self):
        """区县结果上提到地级市（adm2）"""
        with patch("packages.utils.city_resolver._geo_lookup_async", return_value=_mock_geo_response()):
            # adm2=苏州市 → 返回地级市「苏州」而非区县「昆山」
            assert await reverse_geocode(31.38, 120.98, "fake_key") == "苏州"

    @pytest.mark.asyncio
    async def test_no_adm2_returns_district_name(self):
        """无上级行政区时返回区县名"""
        district = [{"name": "某区", "id": "1", "adm2": "", "country": "中国"}]
        with patch("packages.utils.city_resolver._geo_lookup_async", return_value=district):
            assert await reverse_geocode(31.38, 120.98, "fake_key") == "某区"

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        assert await reverse_geocode(31.38, 120.98, None) is None

    @pytest.mark.asyncio
    async def test_api_empty_returns_none(self):
        with patch("packages.utils.city_resolver._geo_lookup_async", return_value=[]):
            assert await reverse_geocode(0, 0, "fake_key") is None
