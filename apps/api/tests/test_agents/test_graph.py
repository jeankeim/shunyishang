"""
LangGraph 状态机测试
覆盖 graph.py 所有函数
"""
import pytest
from unittest.mock import patch, MagicMock

from packages.ai_agents.graph import (
    check_error,
    check_retrieved_items,
    build_graph,
    _extract_context_from_query,
    _extract_context_by_rules,
    run_agent,
    run_agent_stream,
)


class TestCheckError:
    def test_with_error(self):
        state = {"error": "something went wrong"}
        assert check_error(state) == "error"

    def test_no_error(self):
        state = {"error": None}
        assert check_error(state) == "continue"

    def test_no_error_key(self):
        state = {}
        assert check_error(state) == "continue"


class TestCheckRetrievedItems:
    def test_with_items(self):
        state = {"retrieved_items": [{"id": 1}]}
        assert check_retrieved_items(state) == "continue"

    def test_empty_items(self):
        state = {"retrieved_items": []}
        assert check_retrieved_items(state) == "error"

    def test_no_items_key(self):
        state = {}
        assert check_retrieved_items(state) == "error"


class TestBuildGraph:
    def test_builds_graph(self):
        graph = build_graph()
        assert graph is not None


class TestExtractContextByRules:
    def test_business_scene(self):
        result = _extract_context_by_rules("我要去商务会议")
        assert result["scene"] == "商务"

    def test_interview_scene(self):
        result = _extract_context_by_rules("明天面试穿什么")
        assert result["scene"] == "面试"

    def test_date_scene(self):
        result = _extract_context_by_rules("约会穿什么好")
        assert result["scene"] == "约会"

    def test_sports_scene(self):
        result = _extract_context_by_rules("去跑步运动")
        assert result["scene"] == "运动"

    def test_home_scene(self):
        result = _extract_context_by_rules("居家休息")
        assert result["scene"] == "居家"

    def test_wedding_scene(self):
        result = _extract_context_by_rules("参加婚礼")
        assert result["scene"] == "婚礼"

    def test_party_scene(self):
        result = _extract_context_by_rules("晚上去派对")
        assert result["scene"] == "派对"

    def test_travel_scene(self):
        result = _extract_context_by_rules("去成都旅行")
        assert result["scene"] == "旅行"

    def test_business_trip_scene(self):
        result = _extract_context_by_rules("去北京出差3天")
        assert result["scene"] == "出差"
        assert result["travel_days"] == 3
        assert result["destination"] == "北京"

    def test_vacation_scene(self):
        result = _extract_context_by_rules("去三亚度假")
        assert result["scene"] == "度假"

    def test_outdoor_scene(self):
        result = _extract_context_by_rules("去徒步登山")
        assert result["scene"] == "户外探险"

    def test_work_scene(self):
        result = _extract_context_by_rules("上班穿什么")
        assert result["scene"] == "商务"

    def test_no_scene(self):
        result = _extract_context_by_rules("今天穿什么")
        assert result["scene"] is None

    def test_temperature_extraction(self):
        result = _extract_context_by_rules("今天25度穿什么")
        assert result["weather_info"] is not None
        assert result["weather_info"]["temperature"] == 25

    def test_temperature_celsius(self):
        result = _extract_context_by_rules("气温30°C")
        assert result["weather_info"]["temperature"] == 30

    def test_weather_hot(self):
        result = _extract_context_by_rules("今天很炎热")
        assert result["weather_info"]["weather_desc"] == "炎热"
        assert result["weather_element"] == "火"

    def test_weather_cold(self):
        result = _extract_context_by_rules("今天很寒冷")
        assert result["weather_info"]["weather_desc"] == "寒冷"
        assert result["weather_element"] == "水"

    def test_weather_rain(self):
        result = _extract_context_by_rules("下雨天穿什么")
        assert result["weather_info"]["weather_desc"] == "雨天"
        assert result["weather_element"] == "水"

    def test_weather_snow(self):
        result = _extract_context_by_rules("下雪天穿什么")
        assert result["weather_info"]["weather_desc"] == "雪天"
        assert result["weather_element"] == "水"

    def test_weather_sunny(self):
        result = _extract_context_by_rules("晴天穿什么")
        assert result["weather_info"]["weather_desc"] == "晴天"
        assert result["weather_element"] == "火"

    def test_weather_cloudy(self):
        result = _extract_context_by_rules("多云天气")
        assert result["weather_info"]["weather_desc"] == "多云"
        assert result["weather_element"] == "土"

    def test_weather_wind(self):
        result = _extract_context_by_rules("今天大风")
        assert result["weather_info"]["weather_desc"] == "大风"
        assert result["weather_element"] == "木"

    def test_weather_humid(self):
        result = _extract_context_by_rules("今天闷热潮湿")
        assert result["weather_info"]["weather_desc"] == "闷热"
        assert result["weather_element"] == "火"

    def test_travel_days_numeric(self):
        result = _extract_context_by_rules("去北京5天")
        assert result["travel_days"] == 5

    def test_travel_days_chinese(self):
        result = _extract_context_by_rules("去北京三天")
        assert result["travel_days"] == 3

    def test_destination_extraction(self):
        result = _extract_context_by_rules("去上海出差")
        assert result["destination"] == "上海"

    def test_destination_with_travel(self):
        result = _extract_context_by_rules("去成都旅游")
        assert result["destination"] == "成都"

    def test_no_weather_info(self):
        result = _extract_context_by_rules("推荐一套穿搭")
        assert result["weather_info"] is None
        assert result["weather_element"] is None

    def test_combined_scene_and_weather(self):
        result = _extract_context_by_rules("去北京出差3天，15度多云")
        assert result["scene"] == "出差"
        assert result["travel_days"] == 3
        assert result["destination"] == "北京"
        assert result["weather_info"]["temperature"] == 15
        assert result["weather_info"]["weather_desc"] == "多云"


class TestExtractContextFromQuery:
    def test_llm_success(self):
        """LLM 提取成功"""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"scene": "商务", "temperature": 20, "weather_desc": "多云", "travel_days": null, "destination": null}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=mock_client):
            result = _extract_context_from_query("商务会议穿什么")
        assert result["scene"] == "商务"
        assert result["weather_info"]["temperature"] == 20
        assert result["weather_element"] == "土"

    def test_llm_with_travel(self):
        """LLM 提取带旅行信息"""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"scene": "出差", "temperature": 15, "weather_desc": "多云", "travel_days": 3, "destination": "北京"}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=mock_client):
            result = _extract_context_from_query("去北京出差3天")
        assert result["scene"] == "出差"
        assert result["travel_days"] == 3
        assert result["destination"] == "北京"

    def test_llm_scene_mapping(self):
        """LLM 场景映射（上班 -> 商务）"""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"scene": "上班", "temperature": null, "weather_desc": null, "travel_days": null, "destination": null}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=mock_client):
            result = _extract_context_from_query("上班穿什么")
        assert result["scene"] == "商务"

    def test_llm_fallback_to_rules(self):
        """LLM 失败时回退到规则提取"""
        with patch("packages.ai_agents.nodes.get_llm_client", side_effect=Exception("no LLM")):
            result = _extract_context_from_query("去商务会议")
        assert result["scene"] == "商务"

    def test_llm_invalid_json_fallback(self):
        """LLM 返回无效 JSON 时回退"""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="not valid json"))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=mock_client):
            result = _extract_context_from_query("商务会议")
        assert result["scene"] == "商务"

    def test_llm_travel_days_non_int(self):
        """travel_days 非整数"""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"scene": null, "temperature": null, "weather_desc": null, "travel_days": "abc", "destination": null}'))]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("packages.ai_agents.nodes.get_llm_client", return_value=mock_client):
            result = _extract_context_from_query("test")
        assert result["travel_days"] is None


class TestRunAgent:
    def test_run_agent(self):
        """测试 run_agent 同步调用"""
        mock_result = {"final_response": {"reason": "test", "items": []}}
        with patch("packages.ai_agents.graph.app") as mock_app:
            mock_app.invoke.return_value = mock_result
            with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
                result = run_agent("测试穿搭")
        assert "reason" in result

    def test_run_agent_with_bazi(self):
        """带八字输入"""
        mock_result = {"final_response": {"reason": "test"}}
        with patch("packages.ai_agents.graph.app") as mock_app:
            mock_app.invoke.return_value = mock_result
            with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
                result = run_agent(
                    "测试",
                    bazi_input={"birth_year": 1990, "birth_month": 5, "birth_day": 15, "birth_hour": 10, "gender": "男"},
                )
        assert isinstance(result, dict)


class TestRunAgentStream:
    def test_stream_success(self):
        """流式推荐成功"""
        with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {
                    "target_elements": ["火"],
                    "search_query": "test",
                    "scene": None,
                    "bazi_result": None,
                    "intent_result": None,
                }
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            {"id": 1, "name": "红色T恤", "category": "上装", "primary_element": "火",
                             "secondary_element": None, "final_score": 0.9, "semantic_score": 0.8,
                             "wuxing_score": 0.6, "source": "public", "item_code": "p1", "image_url": ""}
                        ],
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐", "红色T恤"])
                        results = list(run_agent_stream("测试穿搭"))
        types = [r["type"] for r in results]
        assert "analysis" in types
        assert "items" in types
        assert "token" in types
        assert "done" in types

    def test_stream_error_in_analyze(self):
        """分析阶段错误"""
        with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {"error": "分析失败", "retrieved_items": []}
                results = list(run_agent_stream("测试"))
        assert any(r["type"] == "error" for r in results)

    def test_stream_no_items(self):
        """无物品"""
        with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {"target_elements": ["火"], "search_query": "test"}
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {"retrieved_items": [], "error": "没有找到"}
                    results = list(run_agent_stream("测试"))
        assert any(r["type"] == "error" for r in results)

    def test_stream_empty_items_no_error(self):
        """无物品但无 error 字段"""
        with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {"target_elements": ["火"], "search_query": "test"}
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {"retrieved_items": []}
                    results = list(run_agent_stream("测试"))
        assert any(r["type"] == "error" for r in results)

    def test_stream_non_dict_items(self):
        """物品列表包含非字典元素"""
        with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": None, "weather_info": None, "weather_element": None}):
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {"target_elements": ["火"], "search_query": "test", "bazi_result": {"reasoning": "test", "suggested_elements": ["火"], "five_elements_count": {}}}
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            "not_a_dict",
                            {"id": 1, "name": "T恤", "category": "上装", "primary_element": "火",
                             "final_score": 0.9, "semantic_score": 0.8, "source": "public"},
                        ],
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐"])
                        results = list(run_agent_stream("测试"))
        items_result = [r for r in results if r["type"] == "items"]
        assert len(items_result) == 1
        # Non-dict items should be filtered out
        assert len(items_result[0]["data"]) == 1

    def test_stream_with_bazi(self):
        """带八字的流式推荐"""
        with patch("packages.ai_agents.graph._extract_context_from_query", return_value={"scene": "商务", "weather_info": None, "weather_element": None}):
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {
                    "target_elements": ["水"],
                    "search_query": "商务",
                    "scene": "商务",
                    "bazi_result": {"reasoning": "bazi", "suggested_elements": ["水"], "five_elements_count": {"水": 3}},
                    "intent_result": {"reasoning": "intent"},
                }
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            {"id": 1, "name": "西装", "category": "上装", "primary_element": "水",
                             "final_score": 0.9, "semantic_score": 0.8, "source": "wardrobe"},
                        ],
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐西装"])
                        results = list(run_agent_stream(
                            "商务穿搭",
                            bazi_input={"gender": "男"},
                        ))
        analysis = [r for r in results if r["type"] == "analysis"]
        assert len(analysis) == 1
        assert analysis[0]["data"]["scene"] == "商务"
        assert "suggested_elements" in analysis[0]["data"]
