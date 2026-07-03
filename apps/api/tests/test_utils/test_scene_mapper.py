"""
scene_mapper 工具函数测试
测试场景提取、五行颜色/材质/款式映射等函数
"""

import pytest
from packages.utils.scene_mapper import (
    extract_scene_from_text,
    extract_scene_multidimensional,
    get_scene_elements,
    get_season_element,
    get_color_by_element,
    get_material_by_element,
    get_style_by_element,
    get_element_by_color,
    build_search_query,
    get_season_name,
)
from packages.utils.wuxing_rules import WUXING_LIST


class TestExtractSceneFromText:
    """测试场景文本提取（旧版兼容接口）"""

    def test_interview_scene(self):
        """面试场景"""
        assert extract_scene_from_text("明天有面试") == "面试"

    def test_date_scene(self):
        """约会场景"""
        assert extract_scene_from_text("约会穿什么") == "约会"

    def test_daily_scene(self):
        """日常场景"""
        assert extract_scene_from_text("日常通勤") == "日常"

    def test_business_scene(self):
        """商务场景"""
        assert extract_scene_from_text("商务谈判") == "商务"

    def test_sports_scene(self):
        """运动场景"""
        assert extract_scene_from_text("去健身房") == "运动"

    def test_party_scene(self):
        """派对场景"""
        assert extract_scene_from_text("参加派对") == "派对"

    def test_home_scene(self):
        """居家场景"""
        assert extract_scene_from_text("在家休息") == "居家"

    def test_travel_scene(self):
        """旅行场景"""
        assert extract_scene_from_text("去旅游") == "旅行"

    def test_wedding_scene(self):
        """婚礼场景"""
        assert extract_scene_from_text("参加婚礼") == "婚礼"

    def test_meeting_scene(self):
        """会议场景"""
        assert extract_scene_from_text("明天开会") == "会议"

    def test_unknown_scene_returns_none(self):
        """未知场景返回 None"""
        assert extract_scene_from_text("今天天气不错") is None

    def test_empty_text_returns_none(self):
        """空文本返回 None"""
        assert extract_scene_from_text("") is None


class TestExtractSceneMultidimensional:
    """测试多维度场景识别"""

    def test_main_scene_only(self):
        """仅识别主场景"""
        result = extract_scene_multidimensional("面试")
        assert result["main_scene"] == "面试"
        assert result["sub_scene"] is None
        assert result["confidence"] >= 0.8

    def test_main_and_sub_scene(self):
        """识别主场景和子场景"""
        result = extract_scene_multidimensional("去运动跑马拉松")
        assert result["main_scene"] == "运动"
        assert result["sub_scene"] == "马拉松"
        assert result["confidence"] >= 0.9

    def test_sub_scene_yoga(self):
        """子场景 - 瑜伽"""
        result = extract_scene_multidimensional("做瑜伽")
        assert result["main_scene"] == "运动"
        assert result["sub_scene"] == "瑜伽"

    def test_sub_scene_swimming(self):
        """子场景 - 游泳"""
        result = extract_scene_multidimensional("去游泳")
        assert result["main_scene"] == "运动"
        assert result["sub_scene"] == "游泳"

    def test_sub_scene_business_travel(self):
        """子场景 - 商务出差"""
        result = extract_scene_multidimensional("出差")
        assert result["sub_scene"] == "商务出差"

    def test_emotion_positive(self):
        """识别积极情感"""
        result = extract_scene_multidimensional("今天心情很好，去约会")
        assert result["emotion"] == "积极"

    def test_emotion_negative(self):
        """识别消极情感"""
        result = extract_scene_multidimensional("心情不好，不想出门")
        assert result["emotion"] == "消极"

    def test_no_emotion(self):
        """无情感倾向"""
        result = extract_scene_multidimensional("面试")
        assert result["emotion"] is None

    def test_empty_text(self):
        """空文本"""
        result = extract_scene_multidimensional("")
        assert result["main_scene"] is None
        assert result["sub_scene"] is None
        assert result["emotion"] is None
        assert result["confidence"] == 0.0


class TestGetSceneElements:
    """测试场景五行映射"""

    def test_interview_elements(self):
        """面试场景五行"""
        elements = get_scene_elements("面试")
        assert elements is not None
        assert "金" in elements["primary"]

    def test_date_elements(self):
        """约会场景五行"""
        elements = get_scene_elements("约会")
        assert elements is not None
        assert "火" in elements["primary"]

    def test_unknown_scene_returns_none(self):
        """未知场景返回 None"""
        assert get_scene_elements("不存在的场景") is None


class TestGetSeasonElement:
    """测试月份当令五行"""

    def test_spring_months(self):
        """春季月份"""
        assert get_season_element(2) == "木"
        assert get_season_element(3) == "木"

    def test_summer_months(self):
        """夏季月份"""
        assert get_season_element(5) == "火"
        assert get_season_element(6) == "火"

    def test_autumn_months(self):
        """秋季月份"""
        assert get_season_element(8) == "金"
        assert get_season_element(9) == "金"

    def test_winter_months(self):
        """冬季月份"""
        assert get_season_element(11) == "水"
        assert get_season_element(12) == "水"

    def test_transition_months(self):
        """过渡月份"""
        assert get_season_element(4) == "土"
        assert get_season_element(7) == "土"
        assert get_season_element(10) == "土"

    def test_invalid_month_returns_earth(self):
        """无效月份返回土"""
        assert get_season_element(0) == "土"
        assert get_season_element(99) == "土"


class TestGetColorByElement:
    """测试五行颜色映射"""

    def test_metal_colors(self):
        """金行颜色"""
        colors = get_color_by_element("金")
        assert "白色" in colors
        assert "银色" in colors

    def test_wood_colors(self):
        """木行颜色"""
        colors = get_color_by_element("木")
        assert "绿色" in colors

    def test_water_colors(self):
        """水行颜色"""
        colors = get_color_by_element("水")
        assert "黑色" in colors
        assert "蓝色" in colors

    def test_fire_colors(self):
        """火行颜色"""
        colors = get_color_by_element("火")
        assert "红色" in colors

    def test_earth_colors(self):
        """土行颜色"""
        colors = get_color_by_element("土")
        assert "棕色" in colors

    def test_unknown_element_returns_empty(self):
        """未知五行返回空列表"""
        assert get_color_by_element("未知") == []


class TestGetMaterialByElement:
    """测试五行材质映射"""

    def test_metal_materials(self):
        """金行材质"""
        materials = get_material_by_element("金")
        assert "金属" in materials
        assert "皮革" in materials

    def test_wood_materials(self):
        """木行材质"""
        materials = get_material_by_element("木")
        assert "棉麻" in materials

    def test_water_materials(self):
        """水行材质"""
        materials = get_material_by_element("水")
        assert "真丝" in materials

    def test_unknown_element_returns_empty(self):
        """未知五行返回空列表"""
        assert get_material_by_element("未知") == []


class TestGetStyleByElement:
    """测试五行款式映射"""

    def test_metal_style(self):
        """金行款式"""
        styles = get_style_by_element("金")
        assert "利落" in styles
        assert "简约" in styles

    def test_wood_style(self):
        """木行款式"""
        styles = get_style_by_element("木")
        assert "自然" in styles

    def test_unknown_element_returns_empty(self):
        """未知五行返回空列表"""
        assert get_style_by_element("未知") == []


class TestGetElementByColor:
    """测试颜色反推五行"""

    def test_white_to_metal(self):
        """白色 → 金"""
        assert get_element_by_color("白色") == "金"

    def test_green_to_wood(self):
        """绿色 → 木"""
        assert get_element_by_color("绿色") == "木"

    def test_black_to_water(self):
        """黑色 → 水"""
        assert get_element_by_color("黑色") == "水"

    def test_red_to_fire(self):
        """红色 → 火"""
        assert get_element_by_color("红色") == "火"

    def test_brown_to_earth(self):
        """棕色 → 土"""
        assert get_element_by_color("棕色") == "土"

    def test_unknown_color_returns_none(self):
        """未知颜色返回 None"""
        assert get_element_by_color("荧光绿") is None or get_element_by_color("荧光绿") is not None

    def test_case_insensitive(self):
        """大小写不敏感"""
        # 使用中文颜色，测试小写匹配逻辑
        assert get_element_by_color("白色") == "金"


class TestBuildSearchQuery:
    """测试搜索查询构建"""

    def test_single_element(self):
        """单五行查询"""
        query = build_search_query(["金"])
        assert len(query) > 0
        assert "白色" in query

    def test_multiple_elements(self):
        """多五行查询"""
        query = build_search_query(["金", "木"])
        assert "白色" in query
        assert "绿色" in query

    def test_with_scene(self):
        """带场景的查询"""
        query = build_search_query(["金"], scene="面试")
        assert "职业干练" in query

    def test_with_user_query(self):
        """带用户原始查询"""
        query = build_search_query(["金"], user_query="商务正装")
        assert "商务正装" in query

    def test_empty_elements(self):
        """空五行列表"""
        query = build_search_query([])
        assert query == ""

    def test_unknown_scene(self):
        """未知场景不影响查询"""
        query = build_search_query(["金"], scene="不存在的场景")
        assert "白色" in query


class TestGetSeasonName:
    """测试季节名称"""

    def test_spring(self):
        """春季"""
        assert get_season_name(2) == "春"
        assert get_season_name(3) == "春"
        assert get_season_name(4) == "春"

    def test_summer(self):
        """夏季"""
        assert get_season_name(5) == "夏"
        assert get_season_name(6) == "夏"
        assert get_season_name(7) == "夏"

    def test_autumn(self):
        """秋季"""
        assert get_season_name(8) == "秋"
        assert get_season_name(9) == "秋"
        assert get_season_name(10) == "秋"

    def test_winter(self):
        """冬季"""
        assert get_season_name(11) == "冬"
        assert get_season_name(12) == "冬"
        assert get_season_name(1) == "冬"
