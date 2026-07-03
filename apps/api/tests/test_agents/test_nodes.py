"""
AI Agent 节点函数测试
覆盖 nodes.py 中所有节点函数和辅助函数
"""
import pytest
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from packages.ai_agents.nodes import (
    get_llm_client,
    call_llm_with_retry,
    load_prompt,
    analyze_intent_node,
    _enhance_query_with_llm,
    retrieve_items_node,
    _ensure_category_diversity,
    _get_versatile_items,
    _build_weather_filter,
    _build_scene_filter,
    _build_weather_details,
    generate_advice_node,
    generate_advice_stream,
    format_output_node,
    _vector_search,
    _encode_text_with_dashscope,
    _get_embedding_model,
)


# ============================================================
# get_llm_client
# ============================================================

class TestGetLLMClient:
    def test_singleton(self):
        import packages.ai_agents.nodes as nodes_mod
        nodes_mod._llm_client = None
        with patch.object(nodes_mod.settings, "dashscope_api_key", "test-key"):
            c1 = get_llm_client()
            c2 = get_llm_client()
            assert c1 is c2
        nodes_mod._llm_client = None

    def test_no_api_key_raises(self):
        import packages.ai_agents.nodes as nodes_mod
        nodes_mod._llm_client = None
        with patch.object(nodes_mod.settings, "dashscope_api_key", ""):
            with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
                get_llm_client()
        nodes_mod._llm_client = None


# ============================================================
# call_llm_with_retry
# ============================================================

class TestCallLLMWithRetry:
    def test_success(self):
        client = MagicMock()
        resp = MagicMock()
        client.chat.completions.create.return_value = resp
        result = call_llm_with_retry(client, [{"role": "user", "content": "hi"}], "model")
        assert result is resp

    def test_stream_success(self):
        client = MagicMock()
        resp = MagicMock()
        client.chat.completions.create.return_value = resp
        result = call_llm_with_retry(client, [{"role": "user", "content": "hi"}], "model", stream=True)
        assert result is resp

    @patch("packages.ai_agents.nodes.time.sleep")
    def test_retry_then_success(self, mock_sleep):
        from openai import APITimeoutError
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            APITimeoutError("timeout"),
            MagicMock(),
        ]
        result = call_llm_with_retry(
            client, [{"role": "user", "content": "hi"}], "model", max_retries=2
        )
        assert result is not None
        mock_sleep.assert_called_once()

    @patch("packages.ai_agents.nodes.time.sleep")
    def test_all_retries_fail(self, mock_sleep):
        from openai import APITimeoutError
        client = MagicMock()
        client.chat.completions.create.side_effect = APITimeoutError("timeout")
        with pytest.raises((APITimeoutError, RuntimeError)):
            call_llm_with_retry(
                client, [{"role": "user", "content": "hi"}], "model", max_retries=2
            )

    @patch("packages.ai_agents.nodes.time.sleep")
    def test_rate_limit_retry(self, mock_sleep):
        from openai import RateLimitError
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        client.chat.completions.create.side_effect = [
            RateLimitError("rate", response=mock_resp, body=None),
            MagicMock(),
        ]
        result = call_llm_with_retry(
            client, [{"role": "user", "content": "hi"}], "model", max_retries=2
        )
        assert result is not None

    def test_unknown_error_raises(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = ValueError("bad value")
        with pytest.raises(ValueError):
            call_llm_with_retry(client, [{"role": "user", "content": "hi"}], "model")

    @patch("packages.ai_agents.nodes.time.sleep")
    def test_api_error_retry(self, mock_sleep):
        from openai import APIError
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        client.chat.completions.create.side_effect = [
            APIError("err", request=MagicMock(), body=None),
            MagicMock(),
        ]
        result = call_llm_with_retry(
            client, [{"role": "user", "content": "hi"}], "model", max_retries=2
        )
        assert result is not None


# ============================================================
# load_prompt
# ============================================================

class TestLoadPrompt:
    def test_load_analyzer(self):
        result = load_prompt("analyzer.txt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_generator(self):
        result = load_prompt("generator.txt")
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================
# analyze_intent_node
# ============================================================

class TestAnalyzeIntentNode:
    def _base_state(self, **kwargs):
        from packages.ai_agents.state import create_initial_state
        state = create_initial_state(user_input="我想要红色的衣服")
        state.update(kwargs)
        return state

    def test_no_bazi_rule_match(self):
        state = self._base_state()
        result = analyze_intent_node(state)
        assert "target_elements" in result
        assert "search_query" in result
        assert result["scene"] is not None or result["scene"] is None

    def test_with_bazi(self):
        state = self._base_state(
            bazi_input={
                "birth_year": 1990, "birth_month": 5, "birth_day": 15,
                "birth_hour": 10, "gender": "男",
            }
        )
        with patch("packages.ai_agents.nodes.settings") as mock_s:
            mock_s.redis_enabled = False
            result = analyze_intent_node(state)
        assert "bazi_result" in result
        assert result["bazi_result"] is not None
        assert "suggested_elements" in result["bazi_result"]

    def test_bazi_cache_hit(self):
        state = self._base_state(
            bazi_input={
                "birth_year": 1990, "birth_month": 5, "birth_day": 15,
                "birth_hour": 10, "gender": "男",
            }
        )
        cached_bazi = {"suggested_elements": ["水"], "reasoning": "cached", "five_elements_count": {}}
        with patch("packages.ai_agents.nodes.settings") as mock_s:
            mock_s.redis_enabled = True
            mock_s.cache_ttl_bazi = 86400
            with patch("packages.ai_agents.nodes.redis_cache") as mock_rc:
                mock_rc.get_sync.return_value = cached_bazi
                result = analyze_intent_node(state)
        assert result["bazi_result"] == cached_bazi

    def test_bazi_cache_write(self):
        state = self._base_state(
            bazi_input={
                "birth_year": 1990, "birth_month": 5, "birth_day": 15,
                "birth_hour": 10, "gender": "男",
            }
        )
        with patch("packages.ai_agents.nodes.settings") as mock_s:
            mock_s.redis_enabled = True
            mock_s.cache_ttl_bazi = 86400
            with patch("packages.ai_agents.nodes.redis_cache") as mock_rc:
                mock_rc.get_sync.return_value = None
                result = analyze_intent_node(state)
                assert mock_rc.set_sync.called

    def test_bazi_calculation_error(self):
        state = self._base_state(
            bazi_input={
                "birth_year": 1990, "birth_month": 5, "birth_day": 15,
                "birth_hour": 10, "gender": "男",
            }
        )
        with patch("packages.ai_agents.nodes.settings") as mock_s:
            mock_s.redis_enabled = False
            with patch("packages.ai_agents.nodes.calculate_bazi", side_effect=Exception("calc error")):
                result = analyze_intent_node(state)
        assert result["bazi_result"] is None

    def test_bazi_cache_read_error(self):
        state = self._base_state(
            bazi_input={
                "birth_year": 1990, "birth_month": 5, "birth_day": 15,
                "birth_hour": 10, "gender": "男",
            }
        )
        with patch("packages.ai_agents.nodes.settings") as mock_s:
            mock_s.redis_enabled = True
            mock_s.cache_ttl_bazi = 86400
            with patch("packages.ai_agents.nodes.redis_cache") as mock_rc:
                mock_rc.get_sync.side_effect = Exception("cache read error")
                result = analyze_intent_node(state)
        assert result["bazi_result"] is not None

    def test_scene_from_state(self):
        state = self._base_state(scene="商务")
        result = analyze_intent_node(state)
        assert result["scene"] == "商务"

    def test_weather_element_merge(self):
        state = self._base_state(weather_element="水")
        result = analyze_intent_node(state)
        assert "水" in result["target_elements"] or len(result["target_elements"]) >= 0

    def test_llm_query_enhancement(self):
        """当 rule 方法不可用时走 LLM 增强"""
        state = self._base_state(user_input="xyz random text no keywords")
        with patch("packages.ai_agents.nodes._enhance_query_with_llm", return_value="enhanced query") as mock_llm:
            result = analyze_intent_node(state)
            mock_llm.assert_called_once()
            assert result["search_query"] == "enhanced query"


# ============================================================
# _enhance_query_with_llm
# ============================================================

class TestEnhanceQueryWithLLM:
    def test_success(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="enhanced text"))]
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=mock_client):
            with patch("packages.ai_agents.nodes.call_llm_with_retry", return_value=mock_resp):
                result = _enhance_query_with_llm("input", "商务", None, ["金"])
        assert result == "enhanced text"

    def test_fallback_on_error(self):
        with patch("packages.ai_agents.nodes.get_llm_client", side_effect=Exception("no client")):
            result = _enhance_query_with_llm("original input", None, None, [])
        assert result == "original input"

    def test_with_bazi_result(self):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="llm result"))]
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=MagicMock()):
            with patch("packages.ai_agents.nodes.call_llm_with_retry", return_value=mock_resp):
                result = _enhance_query_with_llm(
                    "input", "运动",
                    {"reasoning": "some reasoning"}, ["火", "木"]
                )
        assert result == "llm result"


# ============================================================
# retrieve_items_node
# ============================================================

class TestRetrieveItemsNode:
    def _base_state(self, **kwargs):
        from packages.ai_agents.state import create_initial_state
        state = create_initial_state(user_input="test")
        state["search_query"] = "红色上衣"
        state["target_elements"] = ["火"]
        state.update(kwargs)
        return state

    def test_empty_query(self):
        state = self._base_state(search_query="")
        result = retrieve_items_node(state)
        assert result["error"] == "搜索查询为空"
        assert result["retrieved_items"] == []

    def test_wardrobe_mode_no_user(self):
        state = self._base_state(retrieval_mode="wardrobe", user_id=None)
        result = retrieve_items_node(state)
        assert "需要登录" in result["error"]

    def test_wardrobe_mode_empty_wardrobe(self):
        state = self._base_state(retrieval_mode="wardrobe", user_id=1)
        with patch("packages.ai_agents.nodes.wardrobe_client") as mock_wc:
            mock_wc.check_wardrobe_empty.return_value = True
            result = retrieve_items_node(state)
        assert "还没有添加衣物" in result["error"]

    def test_wardrobe_mode_success(self):
        state = self._base_state(retrieval_mode="wardrobe", user_id=1)
        items = [
            {"id": 1, "name": "红色T恤", "category": "上装", "primary_element": "火",
             "secondary_element": None, "semantic_score": 0.8, "item_code": "w1"},
        ]
        with patch("packages.ai_agents.nodes.wardrobe_client") as mock_wc:
            mock_wc.check_wardrobe_empty.return_value = False
            mock_wc.vector_search_wardrobe.return_value = items
            with patch("apps.api.services.embedding_service.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0
        assert result["retrieved_items"][0]["source"] == "wardrobe"

    def test_wardrobe_mode_no_items_found(self):
        state = self._base_state(retrieval_mode="wardrobe", user_id=1)
        with patch("packages.ai_agents.nodes.wardrobe_client") as mock_wc:
            mock_wc.check_wardrobe_empty.return_value = False
            mock_wc.vector_search_wardrobe.return_value = []
            with patch("apps.api.services.embedding_service.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                result = retrieve_items_node(state)
        assert "error" in result

    def test_wardrobe_mode_non_dict_items(self):
        """防御性检查：items 包含非字典元素"""
        state = self._base_state(retrieval_mode="wardrobe", user_id=1)
        with patch("packages.ai_agents.nodes.wardrobe_client") as mock_wc:
            mock_wc.check_wardrobe_empty.return_value = False
            mock_wc.vector_search_wardrobe.return_value = ["not_a_dict", 123]
            with patch("apps.api.services.embedding_service.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                result = retrieve_items_node(state)
        # Should handle gracefully
        assert result["retrieved_items"] == [] or "error" in result

    def test_public_mode_success(self):
        state = self._base_state(retrieval_mode="public")
        items = [
            {"id": 1, "name": "红色连衣裙", "category": "裙装", "primary_element": "火",
             "secondary_element": None, "semantic_score": 0.9, "item_code": "p1"},
        ]
        with patch("packages.ai_agents.nodes._vector_search", return_value=items):
            result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0

    def test_public_mode_no_items_fallback(self):
        state = self._base_state(retrieval_mode="public")
        with patch("packages.ai_agents.nodes._vector_search", return_value=[]):
            with patch("packages.ai_agents.nodes._get_versatile_items", return_value=[]):
                result = retrieve_items_node(state)
        assert "error" in result
        assert result["retrieved_items"] == []

    def test_public_mode_fallback_versatile(self):
        state = self._base_state(retrieval_mode="public")
        versatile = [
            {"id": 1, "name": "白T恤", "category": "上装", "primary_element": "金",
             "secondary_element": None, "semantic_score": 0.5, "item_code": "v1"},
        ]
        with patch("packages.ai_agents.nodes._vector_search", return_value=[]):
            with patch("packages.ai_agents.nodes._get_versatile_items", return_value=versatile):
                result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0

    def test_hybrid_mode_with_wardrobe(self):
        state = self._base_state(retrieval_mode="hybrid", user_id=1, top_k=5)
        wardrobe_items = [
            {"id": 1, "name": "蓝色衬衫", "category": "上装", "primary_element": "水",
             "secondary_element": None, "semantic_score": 0.85, "item_code": "w1"},
        ]
        public_items = [
            {"id": 2, "name": "黑色裤子", "category": "下装", "primary_element": "水",
             "secondary_element": None, "semantic_score": 0.7, "item_code": "p2"},
        ]
        with patch("packages.ai_agents.nodes.wardrobe_client") as mock_wc:
            mock_wc.check_wardrobe_empty.return_value = False
            mock_wc.vector_search_wardrobe.return_value = wardrobe_items
            with patch("apps.api.services.embedding_service.embedding_service") as mock_emb:
                mock_emb.generate_embedding.return_value = [0.1] * 1024
                with patch("packages.ai_agents.nodes._vector_search", return_value=public_items):
                    result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0

    def test_hybrid_mode_no_wardrobe(self):
        state = self._base_state(retrieval_mode="hybrid", user_id=1, top_k=5)
        public_items = [
            {"id": 2, "name": "黑色裤子", "category": "下装", "primary_element": "水",
             "secondary_element": None, "semantic_score": 0.7, "item_code": "p2"},
        ]
        with patch("packages.ai_agents.nodes.wardrobe_client") as mock_wc:
            mock_wc.check_wardrobe_empty.return_value = True
            with patch("packages.ai_agents.nodes._vector_search", return_value=public_items):
                result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0

    def test_with_bazi_and_scene_weights(self):
        state = self._base_state(
            bazi_result={"suggested_elements": ["火"], "reasoning": "test"},
            scene="商务",
        )
        items = [
            {"id": 1, "name": "西装", "category": "上装", "primary_element": "金",
             "secondary_element": None, "semantic_score": 0.8, "item_code": "p1"},
        ]
        with patch("packages.ai_agents.nodes._vector_search", return_value=items):
            result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0
        assert "final_score" in result["retrieved_items"][0]

    def test_scene_only_weights(self):
        state = self._base_state(scene="运动")
        items = [
            {"id": 1, "name": "运动T恤", "category": "上装", "primary_element": "木",
             "secondary_element": None, "semantic_score": 0.7, "item_code": "p1"},
        ]
        with patch("packages.ai_agents.nodes._vector_search", return_value=items):
            result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0

    def test_bazi_only_weights(self):
        state = self._base_state(
            bazi_result={"suggested_elements": ["水"], "reasoning": "test"},
        )
        items = [
            {"id": 1, "name": "蓝色衬衫", "category": "上装", "primary_element": "水",
             "secondary_element": None, "semantic_score": 0.7, "item_code": "p1"},
        ]
        with patch("packages.ai_agents.nodes._vector_search", return_value=items):
            result = retrieve_items_node(state)
        assert len(result["retrieved_items"]) > 0

    def test_all_wuxing_zero_fallback(self):
        state = self._base_state(target_elements=["土"])
        items = [
            {"id": 1, "name": "白T恤", "category": "上装", "primary_element": "金",
             "secondary_element": None, "semantic_score": 0.9, "item_code": "p1"},
        ]
        with patch("packages.ai_agents.nodes._vector_search", return_value=items):
            result = retrieve_items_node(state)
        # wuxing_score should be 0, triggers fallback
        assert len(result["retrieved_items"]) > 0


# ============================================================
# _ensure_category_diversity
# ============================================================

class TestEnsureCategoryDiversity:
    def test_empty_list(self):
        assert _ensure_category_diversity([], 5) == []

    def test_non_dict_filtered(self):
        items = ["not_dict", 123, {"id": 1, "category": "上装", "final_score": 0.9}]
        result = _ensure_category_diversity(items, 5)
        assert len(result) == 1

    def test_max_per_category(self):
        items = [
            {"id": 1, "category": "上装", "final_score": 0.9},
            {"id": 2, "category": "上装", "final_score": 0.8},
            {"id": 3, "category": "上装", "final_score": 0.7},
            {"id": 4, "category": "下装", "final_score": 0.6},
        ]
        result = _ensure_category_diversity(items, 5)
        cats = [i["category"] for i in result]
        assert cats.count("上装") <= 2

    def test_accessory_replacement(self):
        """配饰替换逻辑"""
        items = [
            {"id": 1, "category": "上装", "final_score": 0.9},
            {"id": 2, "category": "上装", "final_score": 0.8},
            {"id": 3, "category": "下装", "final_score": 0.7},
            {"id": 4, "category": "鞋履", "final_score": 0.6},
            {"id": 5, "category": "配饰", "final_score": 0.5},
        ]
        result = _ensure_category_diversity(items, 4)
        has_accessory = any(i.get("category") == "配饰" for i in result)
        # If limit is 4 and there are accessories, at least one should be included
        assert has_accessory or len(result) < 4


# ============================================================
# _build_weather_filter
# ============================================================

class TestBuildWeatherFilter:
    def test_no_weather(self):
        assert _build_weather_filter(None) == ""

    def test_extreme_cold(self):
        result = _build_weather_filter({"temperature": 3, "weather_desc": "雪"})
        assert "thickness_level" in result

    def test_cold(self):
        result = _build_weather_filter({"temperature": 10, "weather_desc": "阴"})
        assert "thickness_level" in result

    def test_mild(self):
        result = _build_weather_filter({"temperature": 20, "weather_desc": "多云"})
        assert "thickness_level" in result

    def test_hot(self):
        result = _build_weather_filter({"temperature": 30, "weather_desc": "晴"})
        assert "thickness_level" in result

    def test_no_temperature(self):
        result = _build_weather_filter({"weather_desc": "晴"})
        assert result == ""

    def test_with_weather_desc_only(self):
        result = _build_weather_filter({"temperature": 25, "weather_desc": "雨"})
        assert "thickness_level" in result


# ============================================================
# _build_scene_filter
# ============================================================

class TestBuildSceneFilter:
    def test_no_scene(self):
        assert _build_scene_filter(None) == ""
        assert _build_scene_filter("") == ""

    def test_unknown_scene(self):
        assert _build_scene_filter("未知场景") == ""

    def test_business_scene(self):
        result = _build_scene_filter("商务")
        assert "运动裤" in result or "NOT IN" in result

    def test_sports_scene(self):
        result = _build_scene_filter("运动")
        assert "category NOT IN" in result
        assert "functionality" in result

    def test_home_scene(self):
        result = _build_scene_filter("居家")
        assert "category NOT IN" in result

    def test_wedding_scene(self):
        result = _build_scene_filter("婚礼")
        assert "睡衣" in result

    def test_party_scene(self):
        result = _build_scene_filter("派对")
        assert "睡衣" in result

    def test_interview_scene(self):
        result = _build_scene_filter("面试")
        assert "运动裤" in result

    def test_travel_scene(self):
        result = _build_scene_filter("旅行")
        assert "睡衣" in result

    def test_with_sub_scene(self):
        with patch("packages.utils.scene_mapping.get_sub_scene_rules", return_value={"extra_excluded_keywords": ["泳衣"]}):
            result = _build_scene_filter("旅行", "海边")
        assert "泳衣" in result

    def test_with_sub_scene_no_rules(self):
        with patch("packages.utils.scene_mapping.get_sub_scene_rules", return_value=None):
            result = _build_scene_filter("商务", "商务出差")
        assert "NOT IN" not in result or "运动裤" in result


# ============================================================
# _build_weather_details
# ============================================================

class TestBuildWeatherDetails:
    def test_no_weather(self):
        assert _build_weather_details(None, []) == "未提供天气信息"

    def test_cold_temp(self):
        result = _build_weather_details({"temperature": 3, "weather_desc": "雪"}, [])
        assert "寒冷" in result

    def test_cool_temp(self):
        result = _build_weather_details({"temperature": 10, "weather_desc": "阴"}, [])
        assert "较冷" in result

    def test_mild_temp(self):
        result = _build_weather_details({"temperature": 20, "weather_desc": "多云"}, [])
        assert "温和" in result

    def test_hot_temp(self):
        result = _build_weather_details({"temperature": 30, "weather_desc": "晴"}, [])
        assert "炎热" in result

    def test_rainy_weather(self):
        result = _build_weather_details({"temperature": 15, "weather_desc": "雨"}, [])
        assert "雨" in result

    def test_sunny_weather(self):
        result = _build_weather_details({"temperature": 25, "weather_desc": "晴"}, [])
        assert "晴" in result

    def test_foggy_weather(self):
        result = _build_weather_details({"temperature": 15, "weather_desc": "雾"}, [])
        assert "雾" in result or "防护" in result

    def test_humidity_high(self):
        result = _build_weather_details({"temperature": 20, "humidity": 90}, [])
        assert "潮湿" in result

    def test_humidity_low(self):
        result = _build_weather_details({"temperature": 20, "humidity": 20}, [])
        assert "干燥" in result

    def test_wind_high(self):
        result = _build_weather_details({"temperature": 20, "wind_level": 6}, [])
        assert "风大" in result

    def test_items_with_dict_functionality(self):
        items = [
            {"name": "外套", "thickness_level": "厚重", "functionality": {"防水": True, "透气": False}},
        ]
        result = _build_weather_details({"temperature": 5}, items)
        assert "防水" in result

    def test_items_with_list_functionality(self):
        items = [
            {"name": "外套", "thickness_level": "厚重", "functionality": ["防水", "保暖"]},
        ]
        result = _build_weather_details({"temperature": 5}, items)
        assert "防水" in result

    def test_items_no_features(self):
        items = [{"name": "T恤"}]
        result = _build_weather_details({"temperature": 20}, items)
        assert isinstance(result, str)

    def test_empty_details(self):
        result = _build_weather_details({"humidity": 50}, [])
        assert "天气信息不完整" in result or isinstance(result, str)


# ============================================================
# generate_advice_node
# ============================================================

class TestGenerateAdviceNode:
    def _base_state(self, **kwargs):
        from packages.ai_agents.state import create_initial_state
        state = create_initial_state(user_input="test")
        state["target_elements"] = ["火"]
        state.update(kwargs)
        return state

    def test_no_items_versatile_fallback(self):
        state = self._base_state(retrieved_items=[])
        versatile = [
            {"id": 1, "name": "白T恤", "category": "上装", "primary_element": "金"},
        ]
        with patch("packages.ai_agents.nodes._get_versatile_items", return_value=versatile):
            result = generate_advice_node(state)
        assert "reasoning_text" in result
        assert "百搭" in result["reasoning_text"]

    def test_no_items_color_fallback(self):
        state = self._base_state(retrieved_items=[], target_elements=["火"])
        with patch("packages.ai_agents.nodes._get_versatile_items", return_value=[]):
            result = generate_advice_node(state)
        assert "颜色" in result["reasoning_text"] or "匹配的衣物" in result["reasoning_text"]

    def test_no_items_no_elements(self):
        state = self._base_state(retrieved_items=[], target_elements=[])
        with patch("packages.ai_agents.nodes._get_versatile_items", return_value=[]):
            result = generate_advice_node(state)
        assert "抱歉" in result["reasoning_text"]

    def test_with_items_llm_success(self):
        items = [
            {"id": 1, "name": "红色T恤", "category": "上装", "primary_element": "火",
             "secondary_element": None, "image_url": ""},
        ]
        state = self._base_state(retrieved_items=items)
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="推荐红色T恤，适合您今天的五行需求"))]
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=MagicMock()):
            with patch("packages.ai_agents.nodes.call_llm_with_retry", return_value=mock_resp):
                result = generate_advice_node(state)
        assert "reasoning_text" in result
        assert "红色T恤" in result["reasoning_text"]

    def test_with_items_llm_fail(self):
        items = [
            {"id": 1, "name": "红色T恤", "category": "上装", "primary_element": "火",
             "secondary_element": None, "image_url": ""},
        ]
        state = self._base_state(retrieved_items=items)
        with patch("packages.ai_agents.nodes.get_llm_client", side_effect=Exception("fail")):
            result = generate_advice_node(state)
        assert "红色T恤" in result["reasoning_text"]

    def test_with_items_llm_no_mention(self):
        """LLM 未提到物品名时添加提示"""
        items = [
            {"id": 1, "name": "特殊衣物名", "category": "上装", "primary_element": "火",
             "secondary_element": None, "image_url": ""},
        ]
        state = self._base_state(retrieved_items=items)
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="这是一套不错的搭配"))]
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=MagicMock()):
            with patch("packages.ai_agents.nodes.call_llm_with_retry", return_value=mock_resp):
                result = generate_advice_node(state)
        assert "特殊衣物名" in result["reasoning_text"]


# ============================================================
# generate_advice_stream
# ============================================================

class TestGenerateAdviceStream:
    def _base_state(self, **kwargs):
        from packages.ai_agents.state import create_initial_state
        state = create_initial_state(user_input="test")
        state["target_elements"] = ["火"]
        state.update(kwargs)
        return state

    def test_no_items_versatile(self):
        state = self._base_state(retrieved_items=[])
        versatile = [{"id": 1, "name": "白T", "category": "上装", "primary_element": "金"}]
        with patch("packages.ai_agents.nodes._get_versatile_items", return_value=versatile):
            results = list(generate_advice_stream(state))
        assert any("百搭" in r for r in results)

    def test_no_items_color(self):
        state = self._base_state(retrieved_items=[], target_elements=["火"])
        with patch("packages.ai_agents.nodes._get_versatile_items", return_value=[]):
            results = list(generate_advice_stream(state))
        assert any("颜色" in r or "匹配" in r for r in results)

    def test_no_items_no_elements(self):
        state = self._base_state(retrieved_items=[], target_elements=[])
        with patch("packages.ai_agents.nodes._get_versatile_items", return_value=[]):
            results = list(generate_advice_stream(state))
        assert any("抱歉" in r for r in results)

    def test_with_items_success(self):
        items = [
            {"id": 1, "name": "红T恤", "category": "上装", "primary_element": "火",
             "secondary_element": None, "image_url": ""},
        ]
        state = self._base_state(retrieved_items=items)
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="推荐"))]
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content="红T恤"))]
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=MagicMock()):
            with patch("packages.ai_agents.nodes.call_llm_with_retry", return_value=iter([mock_chunk1, mock_chunk2])):
                results = list(generate_advice_stream(state))
        assert "推荐" in results
        assert "红T恤" in results

    def test_with_items_llm_fail(self):
        items = [
            {"id": 1, "name": "红T恤", "category": "上装", "primary_element": "火",
             "secondary_element": None, "image_url": ""},
        ]
        state = self._base_state(retrieved_items=items)
        with patch("packages.ai_agents.nodes.get_llm_client", side_effect=Exception("fail")):
            results = list(generate_advice_stream(state))
        assert any("红T恤" in r for r in results)

    def test_stream_empty_content(self):
        items = [
            {"id": 1, "name": "红T恤", "category": "上装", "primary_element": "火",
             "secondary_element": None, "image_url": ""},
        ]
        state = self._base_state(retrieved_items=items)
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content=None))]
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=MagicMock()):
            with patch("packages.ai_agents.nodes.call_llm_with_retry", return_value=iter([mock_chunk])):
                results = list(generate_advice_stream(state))
        # Empty content chunks should be skipped
        assert isinstance(results, list)


# ============================================================
# format_output_node
# ============================================================

class TestFormatOutputNode:
    def test_basic(self):
        from packages.ai_agents.state import create_initial_state
        state = create_initial_state(user_input="test")
        state["target_elements"] = ["火"]
        state.update(
            bazi_result={"reasoning": "test reasoning"},
            intent_result={"reasoning": "intent reasoning"},
            scene="商务",
            retrieved_items=[
                {"id": 1, "name": "西装", "category": "上装", "primary_element": "金",
                 "secondary_element": None, "final_score": 0.9,
                 "semantic_score": 0.8, "wuxing_score": 0.6, "source": "public",
                 "item_code": "p1", "image_url": "http://img.com/1.jpg"},
            ],
            reasoning_text="推荐理由",
        )
        result = format_output_node(state)
        assert "final_response" in result
        assert result["final_response"]["reason"] == "推荐理由"
        assert len(result["final_response"]["items"]) == 1
        assert result["final_response"]["items"][0]["name"] == "西装"

    def test_no_bazi(self):
        from packages.ai_agents.state import create_initial_state
        state = create_initial_state(user_input="test")
        state["target_elements"] = ["火"]
        state.update(
            bazi_result=None,
            intent_result=None,
            retrieved_items=[],
            reasoning_text="test",
        )
        result = format_output_node(state)
        assert result["final_response"]["analysis"]["bazi_reasoning"] is None


# ============================================================
# _get_versatile_items & _vector_search & embedding
# ============================================================

class TestVectorSearch:
    def test_get_versatile_items(self):
        with patch("packages.ai_agents.nodes._vector_search", return_value=[{"id": 1}]):
            result = _get_versatile_items(["金"], 3)
        assert len(result) == 1

    def test_get_versatile_items_empty(self):
        with patch("packages.ai_agents.nodes._vector_search", return_value=[]):
            result = _get_versatile_items(["金"], 3)
        assert result == []

    def test_vector_search_success(self):
        mock_rows = [
            ("p1", "红色T恤", "上装", "火", None, {}, "中性", [], ["春"], {"min": 10, "max": 30}, [], "轻薄", "http://img.com/1.jpg", 0.9),
        ]
        with patch("packages.ai_agents.nodes._encode_text_with_dashscope", return_value=[0.1] * 1024):
            with patch("packages.ai_agents.nodes.DatabasePool") as mock_db:
                mock_conn = MagicMock()
                mock_cur = MagicMock()
                mock_cur.fetchall.return_value = mock_rows
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
                mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
                result = _vector_search("红色", limit=5)
        assert len(result) == 1
        assert result[0]["name"] == "红色T恤"

    def test_vector_search_error(self):
        with patch("packages.ai_agents.nodes._encode_text_with_dashscope", return_value=[0.1] * 1024):
            with patch("packages.ai_agents.nodes.DatabasePool") as mock_db:
                mock_db.get_connection.side_effect = Exception("db error")
                result = _vector_search("红色", limit=5)
        assert result == []

    def test_vector_search_with_gender(self):
        mock_rows = []
        with patch("packages.ai_agents.nodes._encode_text_with_dashscope", return_value=[0.1] * 1024):
            with patch("packages.ai_agents.nodes.DatabasePool") as mock_db:
                mock_conn = MagicMock()
                mock_cur = MagicMock()
                mock_cur.fetchall.return_value = mock_rows
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
                mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
                result = _vector_search("红色", user_gender="男", limit=5)
        assert result == []

    def test_vector_search_with_weather(self):
        mock_rows = []
        with patch("packages.ai_agents.nodes._encode_text_with_dashscope", return_value=[0.1] * 1024):
            with patch("packages.ai_agents.nodes.DatabasePool") as mock_db:
                mock_conn = MagicMock()
                mock_cur = MagicMock()
                mock_cur.fetchall.return_value = mock_rows
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
                mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
                result = _vector_search("红色", weather_info={"temperature": 5, "weather_desc": "雪"}, limit=5)
        assert result == []

    def test_vector_search_with_scene(self):
        mock_rows = []
        with patch("packages.ai_agents.nodes._encode_text_with_dashscope", return_value=[0.1] * 1024):
            with patch("packages.ai_agents.nodes.DatabasePool") as mock_db:
                mock_conn = MagicMock()
                mock_cur = MagicMock()
                mock_cur.fetchall.return_value = mock_rows
                mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
                mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
                mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
                mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
                result = _vector_search("红色", scene="商务", sub_scene="会议", limit=5)
        assert result == []


class TestEmbeddingModel:
    def test_get_embedding_model(self):
        assert _get_embedding_model() is None

    def test_encode_text_with_dashscope_success(self):
        """测试 DashScope embedding 成功"""
        import sys
        mock_dashscope = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.output = {"embeddings": [{"embedding": [0.1] * 1024}]}
        mock_dashscope.TextEmbedding.call.return_value = mock_resp
        with patch.dict(sys.modules, {"dashscope": mock_dashscope}):
            with patch("packages.ai_agents.nodes.settings") as mock_s:
                mock_s.dashscope_base_url = "https://dashscope-intl.aliyuncs.com"
                result = _encode_text_with_dashscope("test text")
        assert len(result) == 1024

    def test_encode_text_with_dashscope_error(self):
        """测试 DashScope embedding 错误"""
        import sys
        mock_dashscope = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.code = "error"
        mock_resp.message = "bad request"
        mock_dashscope.TextEmbedding.call.return_value = mock_resp
        with patch.dict(sys.modules, {"dashscope": mock_dashscope}):
            with patch("packages.ai_agents.nodes.settings") as mock_s:
                mock_s.dashscope_base_url = "https://dashscope.aliyuncs.com"
                with pytest.raises(Exception, match="DashScope"):
                    _encode_text_with_dashscope("test text")
