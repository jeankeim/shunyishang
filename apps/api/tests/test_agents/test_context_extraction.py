"""
上下文提取测试
测试 graph.py 中的场景识别、多天行程提取、目的地城市提取
"""

import pytest
from packages.ai_agents.graph import _extract_context_by_rules


class TestSceneExtraction:
    """测试新场景识别"""

    def test_chuchai_scene(self):
        """出差场景识别"""
        result = _extract_context_by_rules("下周要去北京出差")
        assert result["scene"] == "出差"

    def test_chuchai_scene_2(self):
        """商务旅行场景识别"""
        result = _extract_context_by_rules("准备一次商务旅行")
        assert result["scene"] == "出差"

    def test_dujia_scene(self):
        """度假场景识别"""
        result = _extract_context_by_rules("去三亚度假")
        assert result["scene"] == "度假"

    def test_dujia_scene_haibian(self):
        """海边度假场景识别"""
        result = _extract_context_by_rules("去海边度假")
        assert result["scene"] == "度假"

    def test_dujia_scene_wenquan(self):
        """温泉度假场景识别"""
        result = _extract_context_by_rules("温泉旅行")
        assert result["scene"] == "度假"

    def test_huwai_tanxian_hiking(self):
        """徒步登山场景识别"""
        result = _extract_context_by_rules("周末去徒步登山")
        assert result["scene"] == "户外探险"

    def test_huwai_tanxian_camping(self):
        """露营场景识别"""
        result = _extract_context_by_rules("去露营探险")
        assert result["scene"] == "户外探险"

    def test_huwai_tanxian_skiing(self):
        """滑雪场景识别"""
        result = _extract_context_by_rules("冬天去滑雪")
        assert result["scene"] == "户外探险"

    def test_shangwu_priority_over_travel(self):
        """商务优先级高于旅行"""
        result = _extract_context_by_rules("明天有商务会议")
        assert result["scene"] == "商务"

    def test_chuchai_priority_over_travel(self):
        """出差优先级高于旅行"""
        result = _extract_context_by_rules("要去上海出差3天")
        assert result["scene"] == "出差"

    def test_dujia_priority_over_travel(self):
        """度假优先级高于旅行"""
        result = _extract_context_by_rules("去三亚度假5天")
        assert result["scene"] == "度假"

    def test_existing_scenes_still_work(self):
        """原有场景仍然正常"""
        assert _extract_context_by_rules("去面试")["scene"] == "面试"
        assert _extract_context_by_rules("去约会")["scene"] == "约会"
        assert _extract_context_by_rules("在家休息")["scene"] == "居家"
        assert _extract_context_by_rules("去参加婚礼")["scene"] == "婚礼"
        assert _extract_context_by_rules("去参加派对")["scene"] == "派对"


class TestTravelDaysExtraction:
    """测试多天行程提取"""

    def test_extract_days_arabic(self):
        """阿拉伯数字天数提取"""
        result = _extract_context_by_rules("去北京出差3天")
        assert result["travel_days"] == 3

    def test_extract_days_5_days(self):
        """5天行程提取"""
        result = _extract_context_by_rules("去三亚玩5天")
        assert result["travel_days"] == 5

    def test_extract_days_7_days(self):
        """7天行程提取"""
        result = _extract_context_by_rules("去云南旅游7天")
        assert result["travel_days"] == 7

    def test_extract_days_chinese(self):
        """中文数字天数提取"""
        result = _extract_context_by_rules("去北京出差三天")
        assert result["travel_days"] == 3

    def test_extract_days_chinese_5(self):
        """中文五天提取"""
        result = _extract_context_by_rules("去三亚度假五天")
        assert result["travel_days"] == 5

    def test_extract_days_chinese_7(self):
        """中文七天提取"""
        result = _extract_context_by_rules("去成都玩七天")
        assert result["travel_days"] == 7

    def test_extract_days_using_ri(self):
        """使用'日'字提取"""
        result = _extract_context_by_rules("去北京出差3日")
        assert result["travel_days"] == 3

    def test_extract_days_none(self):
        """无天数信息"""
        result = _extract_context_by_rules("去北京出差")
        assert result["travel_days"] is None

    def test_extract_days_two(self):
        """两天行程"""
        result = _extract_context_by_rules("去上海出差两天")
        assert result["travel_days"] == 2


class TestDestinationExtraction:
    """测试目的地城市提取"""

    def test_extract_destination_qu(self):
        """'去'后面城市提取"""
        result = _extract_context_by_rules("去北京出差3天")
        assert result["destination"] == "北京"

    def test_extract_destination_dao(self):
        """'到'后面城市提取"""
        result = _extract_context_by_rules("到上海出差")
        assert result["destination"] == "上海"

    def test_extract_destination_fei(self):
        """'飞'后面城市提取"""
        result = _extract_context_by_rules("飞三亚度假")
        assert result["destination"] == "三亚"

    def test_extract_destination_qianwang(self):
        """'前往'后面城市提取"""
        result = _extract_context_by_rules("前往成都旅游")
        assert result["destination"] == "成都"

    def test_extract_destination_none(self):
        """无目的地"""
        result = _extract_context_by_rules("今天在家休息")
        assert result["destination"] is None

    def test_extract_destination_filtered_words(self):
        """过滤非城市词"""
        result = _extract_context_by_rules("去外面散步")
        assert result["destination"] is None or result["destination"] != "外面"


class TestWeatherExtraction:
    """测试天气提取（原有功能不破坏）"""

    def test_temperature_extraction(self):
        """温度提取"""
        result = _extract_context_by_rules("今天25度")
        assert result["weather_info"] is not None
        assert result["weather_info"]["temperature"] == 25

    def test_weather_desc_extraction(self):
        """天气描述提取"""
        result = _extract_context_by_rules("今天下雨天")
        assert result["weather_info"] is not None
        assert result["weather_info"]["weather_desc"] == "雨天"
        assert result["weather_element"] == "水"

    def test_combined_scene_and_days(self):
        """组合场景和天数"""
        result = _extract_context_by_rules("去北京出差3天，25度")
        assert result["scene"] == "出差"
        assert result["travel_days"] == 3
        assert result["weather_info"] is not None
        assert result["weather_info"]["temperature"] == 25


class TestFallbackLogic:
    """测试规则提取兜底逻辑"""

    def test_empty_input(self):
        """空输入"""
        result = _extract_context_by_rules("")
        assert result["scene"] is None
        assert result["travel_days"] is None
        assert result["destination"] is None

    def test_no_match_input(self):
        """无匹配输入"""
        result = _extract_context_by_rules("今天心情不错")
        assert result["scene"] is None
        assert result["travel_days"] is None

    def test_result_has_all_keys(self):
        """结果包含所有键"""
        result = _extract_context_by_rules("去北京出差3天")
        assert "scene" in result
        assert "weather_info" in result
        assert "weather_element" in result
        assert "travel_days" in result
        assert "destination" in result
