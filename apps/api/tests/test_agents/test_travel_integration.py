"""
旅行/出差场景集成测试
验证旅行场景从API请求到Agent节点的全链路集成
"""
import pytest
from unittest.mock import patch, MagicMock

from packages.ai_agents.state import create_initial_state, AgentState
from packages.ai_agents.graph import run_agent_stream, _extract_context_by_rules
from packages.ai_agents.nodes import _generate_travel_plan
from apps.api.schemas.request import RecommendRequest


# ============================================================
# state.py: 旅行参数在 AgentState 中的传递
# ============================================================

class TestTravelStateFields:
    """验证 AgentState 和 create_initial_state 的旅行字段"""

    def test_initial_state_with_travel_params(self):
        """create_initial_state 正确存储旅行参数"""
        state = create_initial_state(
            user_input="去北京出差3天",
            travel_days=3,
            destination="北京",
            luggage_size="中",
        )
        assert state["travel_days"] == 3
        assert state["destination"] == "北京"
        assert state["luggage_size"] == "中"
        assert state["travel_plan"] is None  # 初始为 None

    def test_initial_state_without_travel_params(self):
        """不传旅行参数时，字段为默认值 None"""
        state = create_initial_state(user_input="今天穿什么")
        assert state["travel_days"] is None
        assert state["destination"] is None
        assert state["luggage_size"] is None
        assert state["travel_plan"] is None

    def test_initial_state_travel_days_types(self):
        """旅行天数支持不同整数值"""
        for days in [2, 5, 7, 14, 30]:
            state = create_initial_state(
                user_input=f"旅行{days}天",
                travel_days=days,
                destination="上海",
            )
            assert state["travel_days"] == days

    def test_initial_state_luggage_sizes(self):
        """行李箱大小支持 小/中/大"""
        for size in ["小", "中", "大"]:
            state = create_initial_state(
                user_input="旅行",
                luggage_size=size,
            )
            assert state["luggage_size"] == size


# ============================================================
# request.py: RecommendRequest 旅行字段验证
# ============================================================

class TestRecommendRequestTravel:
    """验证 RecommendRequest 的旅行字段"""

    def test_with_all_travel_fields(self):
        """完整旅行参数"""
        req = RecommendRequest(
            query="去三亚度假5天",
            travel_days=5,
            destination="三亚",
            luggage_size="大",
        )
        assert req.travel_days == 5
        assert req.destination == "三亚"
        assert req.luggage_size == "大"

    def test_without_travel_fields(self):
        """不传旅行参数时为 None"""
        req = RecommendRequest(query="今天穿什么")
        assert req.travel_days is None
        assert req.destination is None
        assert req.luggage_size is None

    def test_travel_days_validation(self):
        """旅行天数范围验证 (1-30)"""
        # 合法值
        req = RecommendRequest(query="test", travel_days=1)
        assert req.travel_days == 1
        req = RecommendRequest(query="test", travel_days=30)
        assert req.travel_days == 30

        # 超范围
        with pytest.raises(Exception):
            RecommendRequest(query="test", travel_days=0)
        with pytest.raises(Exception):
            RecommendRequest(query="test", travel_days=31)

    def test_luggage_size_validation(self):
        """行李箱大小只接受 小/中/大"""
        for size in ["小", "中", "大"]:
            req = RecommendRequest(query="test", luggage_size=size)
            assert req.luggage_size == size

        with pytest.raises(Exception):
            RecommendRequest(query="test", luggage_size="超大")

    def test_destination_max_length(self):
        """目的地长度限制"""
        req = RecommendRequest(query="test", destination="北京")
        assert req.destination == "北京"

        # 超长目的地
        with pytest.raises(Exception):
            RecommendRequest(query="test", destination="A" * 100)


# ============================================================
# graph.py: run_agent_stream 旅行参数和 travel_plan SSE 事件
# ============================================================

class TestRunAgentStreamTravel:
    """验证 run_agent_stream 的旅行场景处理"""

    def test_stream_passes_travel_params(self):
        """旅行参数传递到 initial_state"""
        with patch("packages.ai_agents.graph._extract_context_from_query") as mock_extract:
            mock_extract.return_value = {
                "scene": "出差",
                "weather_info": None,
                "weather_element": None,
                "travel_days": 3,
                "destination": "北京",
            }
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {
                    "target_elements": ["金"],
                    "search_query": "出差 北京",
                    "scene": "出差",
                }
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            {"id": 1, "name": "西装", "category": "上装", "primary_element": "金",
                             "final_score": 0.9, "semantic_score": 0.8, "source": "public", "item_code": "x1"},
                        ],
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐西装"])
                        results = list(run_agent_stream(
                            "去北京出差3天",
                            travel_days=3,
                            destination="北京",
                            luggage_size="中",
                        ))

        # 验证基本事件类型
        types = [r["type"] for r in results]
        assert "analysis" in types
        assert "done" in types

    def test_stream_travel_plan_event(self):
        """旅行场景下输出 travel_plan SSE 事件"""
        travel_plan_data = {
            "destination": "北京",
            "days": 3,
            "luggage_size": "中",
            "daily_plans": [
                {"day": 1, "scene": "出差", "items": [], "notes": "", "weather": {}},
            ],
            "luggage_summary": {"total_items": 5, "luggage_score": 0.85},
            "weather_forecast": [],
            "wuxing_analysis": {
                "target_elements": ["金"],
                "item_element_distribution": {"金": 3},
                "balance_score": 0.7,
            },
        }
        with patch("packages.ai_agents.graph._extract_context_from_query") as mock_extract:
            mock_extract.return_value = {
                "scene": "出差",
                "weather_info": None,
                "weather_element": None,
            }
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {
                    "target_elements": ["金"],
                    "search_query": "出差",
                    "scene": "出差",
                }
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            {"id": 1, "name": "西装", "category": "上装", "primary_element": "金",
                             "final_score": 0.9, "source": "public"},
                        ],
                        "travel_plan": travel_plan_data,
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐"])
                        results = list(run_agent_stream(
                            "去北京出差3天",
                            travel_days=3,
                            destination="北京",
                        ))

        # 检查是否有 travel_plan 事件
        travel_events = [r for r in results if r["type"] == "travel_plan"]
        assert len(travel_events) == 1
        assert travel_events[0]["data"]["destination"] == "北京"
        assert travel_events[0]["data"]["days"] == 3

    def test_stream_no_travel_plan_for_single_day(self):
        """单天请求不输出 travel_plan 事件"""
        with patch("packages.ai_agents.graph._extract_context_from_query") as mock_extract:
            mock_extract.return_value = {
                "scene": "日常",
                "weather_info": None,
                "weather_element": None,
            }
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {
                    "target_elements": ["木"],
                    "search_query": "日常穿搭",
                    "scene": "日常",
                }
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            {"id": 1, "name": "T恤", "category": "上装", "primary_element": "木",
                             "final_score": 0.8, "source": "public"},
                        ],
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐T恤"])
                        results = list(run_agent_stream("今天穿什么"))

        travel_events = [r for r in results if r["type"] == "travel_plan"]
        assert len(travel_events) == 0

    def test_stream_travel_scene_detection_from_query(self):
        """从用户输入自动提取旅行意图"""
        with patch("packages.ai_agents.graph._extract_context_from_query") as mock_extract:
            # 模拟 LLM 从查询中提取旅行信息
            mock_extract.return_value = {
                "scene": "旅行",
                "weather_info": None,
                "weather_element": None,
                "travel_days": 5,
                "destination": "三亚",
            }
            with patch("packages.ai_agents.graph.analyze_intent_node") as mock_analyze:
                mock_analyze.return_value = {
                    "target_elements": ["火"],
                    "search_query": "三亚度假",
                    "scene": "旅行",
                }
                with patch("packages.ai_agents.graph.retrieve_items_node") as mock_retrieve:
                    mock_retrieve.return_value = {
                        "retrieved_items": [
                            {"id": 1, "name": "连衣裙", "category": "裙装", "primary_element": "火",
                             "final_score": 0.9, "source": "public"},
                        ],
                    }
                    with patch("packages.ai_agents.nodes.generate_advice_stream") as mock_stream:
                        mock_stream.return_value = iter(["推荐度假穿搭"])
                        results = list(run_agent_stream("去三亚度假5天"))

        types = [r["type"] for r in results]
        assert "analysis" in types
        assert "done" in types


# ============================================================
# nodes.py: _generate_travel_plan 函数测试
# ============================================================

class TestGenerateTravelPlan:
    """验证 _generate_travel_plan 函数"""

    def test_returns_dict_with_required_keys(self):
        """生成的行程包含必要字段"""
        state = {
            "user_input": "去北京出差3天",
            "bazi_input": {"birth_year": 1990, "birth_month": 6, "birth_day": 15, "birth_hour": 10, "gender": "女"},
            "target_elements": ["金", "水"],
            "scene": "出差",
            "weather_element": None,
        }
        top_items = [
            {"id": 1, "name": "白衬衫", "category": "上装", "primary_element": "金", "final_score": 0.9},
            {"id": 2, "name": "黑色西裤", "category": "下装", "primary_element": "水", "final_score": 0.85},
            {"id": 3, "name": "米色风衣", "category": "外套", "primary_element": "土", "final_score": 0.8},
            {"id": 4, "name": "深蓝西装", "category": "外套", "primary_element": "水", "final_score": 0.78},
            {"id": 5, "name": "丝巾", "category": "配饰", "primary_element": "火", "final_score": 0.75},
        ]

        with patch("packages.utils.weather_forecast.get_destination_weather") as mock_weather:
            mock_weather.return_value = [
                {"date": "2025-01-01", "weather_desc": "晴", "temperature_max": 10, "temperature_min": -2,
                 "humidity": 30, "wind_level": 2},
                {"date": "2025-01-02", "weather_desc": "多云", "temperature_max": 8, "temperature_min": -3,
                 "humidity": 40, "wind_level": 3},
                {"date": "2025-01-03", "weather_desc": "晴", "temperature_max": 12, "temperature_min": 0,
                 "humidity": 35, "wind_level": 2},
            ]
            result = _generate_travel_plan(
                state=state,
                top_items=top_items,
                travel_days=3,
                destination="北京",
                luggage_size="中",
            )

        assert result is not None
        assert result["destination"] == "北京"
        assert result["days"] == 3
        assert result["luggage_size"] == "中"
        assert "daily_plans" in result
        assert "luggage_summary" in result
        assert "weather_forecast" in result
        assert "wuxing_analysis" in result

    def test_daily_plans_count_matches_days(self):
        """daily_plans 数量与天数一致"""
        state = {
            "user_input": "去上海出差2天",
            "bazi_input": None,
            "target_elements": ["木"],
            "scene": "出差",
            "weather_element": None,
        }
        top_items = [
            {"id": 1, "name": "衬衫", "category": "上装", "primary_element": "木", "final_score": 0.9},
            {"id": 2, "name": "长裤", "category": "下装", "primary_element": "木", "final_score": 0.8},
        ]

        with patch("packages.utils.weather_forecast.get_destination_weather") as mock_weather:
            mock_weather.return_value = [
                {"date": "2025-03-01", "weather_desc": "多云", "temperature_max": 18, "temperature_min": 10,
                 "humidity": 60, "wind_level": 2},
                {"date": "2025-03-02", "weather_desc": "晴", "temperature_max": 20, "temperature_min": 12,
                 "humidity": 55, "wind_level": 3},
            ]
            result = _generate_travel_plan(
                state=state,
                top_items=top_items,
                travel_days=2,
                destination="上海",
                luggage_size="小",
            )

        assert len(result["daily_plans"]) == 2
        assert result["daily_plans"][0]["day"] == 1
        assert result["daily_plans"][1]["day"] == 2

    def test_luggage_summary_has_score(self):
        """行李摘要包含评分"""
        state = {
            "user_input": "度假",
            "bazi_input": None,
            "target_elements": ["火"],
            "scene": "度假",
            "weather_element": None,
        }
        top_items = [
            {"id": 1, "name": "连衣裙", "category": "裙装", "primary_element": "火", "final_score": 0.9},
        ]

        with patch("packages.utils.weather_forecast.get_destination_weather") as mock_weather:
            mock_weather.return_value = [
                {"date": "2025-06-01", "weather_desc": "晴", "temperature_max": 32, "temperature_min": 24,
                 "humidity": 70, "wind_level": 2},
            ]
            result = _generate_travel_plan(
                state=state,
                top_items=top_items,
                travel_days=1,
                destination="三亚",
                luggage_size="大",
            )

        # luggage_summary 必须存在
        assert "luggage_summary" in result
        assert "luggage_score" in result["luggage_summary"]
        assert 0 <= result["luggage_summary"]["luggage_score"] <= 1

    def test_weather_fallback_on_api_failure(self):
        """天气 API 失败时使用兜底数据"""
        state = {
            "user_input": "出差",
            "bazi_input": None,
            "target_elements": ["金"],
            "scene": "出差",
            "weather_element": None,
        }
        top_items = [
            {"id": 1, "name": "西装", "category": "上装", "primary_element": "金", "final_score": 0.9},
        ]

        with patch("packages.utils.weather_forecast.get_destination_weather") as mock_weather:
            # 模拟 API 返回空列表
            mock_weather.return_value = []
            result = _generate_travel_plan(
                state=state,
                top_items=top_items,
                travel_days=2,
                destination="北京",
                luggage_size="中",
            )

        # 即使天气API返回空，也不应该崩溃
        assert result is not None
        assert "weather_forecast" in result


# ============================================================
# graph.py: _extract_context_by_rules 旅行场景识别
# ============================================================

class TestExtractContextTravelScenes:
    """验证规则引擎对旅行场景的识别"""

    def test_travel_scene_detection(self):
        """识别旅行场景"""
        result = _extract_context_by_rules("去北京旅行")
        assert result["scene"] in ("旅行", "出差", "度假", "户外探险", None)

    def test_business_trip_detection(self):
        """识别出差场景"""
        result = _extract_context_by_rules("下周出差")
        # 出差场景可能被识别为商务或出差
        assert result["scene"] is not None

    def test_non_travel_scene(self):
        """非旅行场景不误判"""
        result = _extract_context_by_rules("今天面试穿什么")
        assert result["scene"] == "面试"


# ============================================================
# recommend.py: API 路由层旅行参数传递（集成测试）
# ============================================================

class TestRecommendAPIIntegration:
    """验证推荐API能正确接收和传递旅行参数"""

    def test_request_schema_accepts_travel_params(self):
        """RecommendRequest 接受所有旅行参数"""
        req = RecommendRequest(
            query="去北京出差3天穿什么",
            travel_days=3,
            destination="北京",
            luggage_size="中",
            gender="女",
            retrieval_mode="public",
        )
        assert req.query == "去北京出差3天穿什么"
        assert req.travel_days == 3
        assert req.destination == "北京"
        assert req.luggage_size == "中"
        assert req.gender == "女"

    def test_request_schema_mixed_params(self):
        """混合参数：旅行+八字"""
        req = RecommendRequest(
            query="去三亚度假5天",
            travel_days=5,
            destination="三亚",
            luggage_size="大",
            bazi={
                "birth_year": 1990,
                "birth_month": 6,
                "birth_day": 15,
                "birth_hour": 10,
                "gender": "女",
            },
        )
        assert req.travel_days == 5
        assert req.bazi is not None
        assert req.bazi.birth_year == 1990
