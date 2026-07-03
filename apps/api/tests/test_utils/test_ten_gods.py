"""
十神关系解读系统测试
"""

import pytest

from packages.utils.ten_gods import (
    calculate_ten_gods,
    analyze_ten_gods_chart,
    get_style_suggestion,
    get_multi_god_style_suggestion,
    TEN_GODS,
    TEN_GOD_COLOR_MAP,
    TEN_GOD_MATERIAL_MAP,
    TIANGAN_YINYANG,
    _determine_ten_god,
)
from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    WUXING_SHENG,
    WUXING_KE,
)


@pytest.fixture
def sample_bazi():
    """测试用八字"""
    return {
        "pillars": {
            "year": "甲子",
            "month": "丙寅",
            "day": "戊午",
            "hour": "庚申",
        },
        "eight_chars": ["甲", "子", "丙", "寅", "戊", "午", "庚", "申"],
        "five_elements_count": {"金": 1, "木": 2, "水": 1, "火": 2, "土": 2},
        "dominant_element": "木",
        "lacking_element": None,
        "day_master": "土",
        "month_element": "木",
        "suggested_elements": ["火", "土"],
        "avoid_elements": ["木", "水"],
        "reasoning": "测试用",
    }


# ============================================================
# 十神定义测试
# ============================================================

class TestTenGodsDefinition:
    """十神定义完整性测试"""

    def test_all_ten_gods_defined(self):
        """所有10种十神都应定义"""
        expected = {"比肩", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官", "偏印", "正印"}
        assert set(TEN_GODS.keys()) == expected

    def test_ten_gods_have_required_fields(self):
        """每个十神应包含必要字段"""
        for name, info in TEN_GODS.items():
            assert "element_relation" in info
            assert "description" in info
            assert "style_keywords" in info
            assert len(info["style_keywords"]) > 0
            assert info["element_relation"] in ["同我", "我生", "我克", "克我", "生我"]

    def test_ten_god_color_map_complete(self):
        """所有十神应有颜色映射"""
        for name in TEN_GODS:
            assert name in TEN_GOD_COLOR_MAP
            assert len(TEN_GOD_COLOR_MAP[name]) > 0

    def test_ten_god_material_map_complete(self):
        """所有十神应有材质映射"""
        for name in TEN_GODS:
            assert name in TEN_GOD_MATERIAL_MAP
            assert len(TEN_GOD_MATERIAL_MAP[name]) > 0


# ============================================================
# 阴阳属性测试
# ============================================================

class TestYinYang:
    """天干阴阳属性测试"""

    def test_yang_stems(self):
        """阳干"""
        assert TIANGAN_YINYANG["甲"] == "阳"
        assert TIANGAN_YINYANG["丙"] == "阳"
        assert TIANGAN_YINYANG["戊"] == "阳"
        assert TIANGAN_YINYANG["庚"] == "阳"
        assert TIANGAN_YINYANG["壬"] == "阳"

    def test_yin_stems(self):
        """阴干"""
        assert TIANGAN_YINYANG["乙"] == "阴"
        assert TIANGAN_YINYANG["丁"] == "阴"
        assert TIANGAN_YINYANG["己"] == "阴"
        assert TIANGAN_YINYANG["辛"] == "阴"
        assert TIANGAN_YINYANG["癸"] == "阴"


# ============================================================
# 十神计算测试
# ============================================================

class TestCalculateTenGods:
    """十神关系计算测试"""

    def test_bi_jian_same_element_same_polarity(self):
        """比肩：同五行同阴阳"""
        # 甲(阳木) vs 甲(阳木) -> 比肩
        result = calculate_ten_gods("甲", "甲")
        assert result["ten_god"] == "比肩"

    def test_jie_cai_same_element_diff_polarity(self):
        """劫财：同五行异阴阳"""
        # 甲(阳木) vs 乙(阴木) -> 劫财
        result = calculate_ten_gods("甲", "乙")
        assert result["ten_god"] == "劫财"

    def test_shi_shen_i_produce_same_polarity(self):
        """食神：我生同阴阳"""
        # 甲(阳木) 生 丙(阳火) -> 食神
        result = calculate_ten_gods("甲", "丙")
        assert result["ten_god"] == "食神"

    def test_shang_guan_i_produce_diff_polarity(self):
        """伤官：我生异阴阳"""
        # 甲(阳木) 生 丁(阴火) -> 伤官
        result = calculate_ten_gods("甲", "丁")
        assert result["ten_god"] == "伤官"

    def test_pian_cai_i_overcome_same_polarity(self):
        """偏财：我克同阴阳"""
        # 甲(阳木) 克 戊(阳土) -> 偏财
        result = calculate_ten_gods("甲", "戊")
        assert result["ten_god"] == "偏财"

    def test_zheng_cai_i_overcome_diff_polarity(self):
        """正财：我克异阴阳"""
        # 甲(阳木) 克 己(阴土) -> 正财
        result = calculate_ten_gods("甲", "己")
        assert result["ten_god"] == "正财"

    def test_qi_sha_overcomes_me_same_polarity(self):
        """七杀：克我同阴阳"""
        # 庚(阳金) 克 甲(阳木) -> 七杀
        result = calculate_ten_gods("甲", "庚")
        assert result["ten_god"] == "七杀"

    def test_zheng_guan_overcomes_me_diff_polarity(self):
        """正官：克我异阴阳"""
        # 辛(阴金) 克 甲(阳木) -> 正官
        result = calculate_ten_gods("甲", "辛")
        assert result["ten_god"] == "正官"

    def test_pian_yin_produces_me_same_polarity(self):
        """偏印：生我同阴阳"""
        # 壬(阳水) 生 甲(阳木) -> 偏印
        result = calculate_ten_gods("甲", "壬")
        assert result["ten_god"] == "偏印"

    def test_zheng_yin_produces_me_diff_polarity(self):
        """正印：生我异阴阳"""
        # 癸(阴水) 生 甲(阳木) -> 正印
        result = calculate_ten_gods("甲", "癸")
        assert result["ten_god"] == "正印"


# ============================================================
# 所有天干组合覆盖测试
# ============================================================

class TestAllStemCombinations:
    """所有天干组合覆盖测试"""

    def test_all_combinations_return_valid_god(self):
        """所有10x10组合应返回有效十神"""
        stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        valid_gods = set(TEN_GODS.keys())
        
        for day_master in stems:
            for other in stems:
                result = calculate_ten_gods(day_master, other)
                assert result["ten_god"] in valid_gods, \
                    f"{day_master} vs {other} returned {result['ten_god']}"

    def test_same_stem_always_bi_jian(self):
        """同天干一定为比肩"""
        stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        for s in stems:
            result = calculate_ten_gods(s, s)
            assert result["ten_god"] == "比肩"

    def test_same_element_diff_polarity_always_jie_cai(self):
        """同五行异阴阳一定为劫财"""
        pairs = [("甲", "乙"), ("乙", "甲"), ("丙", "丁"), ("丁", "丙"),
                 ("戊", "己"), ("己", "戊"), ("庚", "辛"), ("辛", "庚"),
                 ("壬", "癸"), ("癸", "壬")]
        for a, b in pairs:
            result = calculate_ten_gods(a, b)
            assert result["ten_god"] == "劫财"

    def test_determine_ten_god_function(self):
        """直接测试_determine_ten_god"""
        # 同我
        assert _determine_ten_god("木", "木", True) == "比肩"
        assert _determine_ten_god("木", "木", False) == "劫财"
        # 我生
        assert _determine_ten_god("木", "火", True) == "食神"
        assert _determine_ten_god("木", "火", False) == "伤官"
        # 我克
        assert _determine_ten_god("木", "土", True) == "偏财"
        assert _determine_ten_god("木", "土", False) == "正财"
        # 克我
        assert _determine_ten_god("木", "金", True) == "七杀"
        assert _determine_ten_god("木", "金", False) == "正官"
        # 生我
        assert _determine_ten_god("木", "水", True) == "偏印"
        assert _determine_ten_god("木", "水", False) == "正印"

    def test_all_five_elements_covered(self):
        """每个五行作为日主时，与其他4个五行都有对应十神"""
        elements = ["金", "木", "水", "火", "土"]
        for dm in elements:
            for other in elements:
                if dm == other:
                    continue
                same = _determine_ten_god(dm, other, True)
                diff = _determine_ten_god(dm, other, False)
                # 偏/正对应该不同
                assert same != diff


# ============================================================
# 八字十神格局分析测试
# ============================================================

class TestAnalyzeTenGodsChart:
    """八字十神格局分析测试"""

    def test_chart_structure(self, sample_bazi):
        """格局分析结构完整性"""
        result = analyze_ten_gods_chart(sample_bazi)
        assert "pillars" in result
        assert "hidden_gods" in result
        assert "dominant_gods" in result
        assert "weak_gods" in result
        assert "god_distribution" in result
        assert "analysis" in result

    def test_chart_pillars(self, sample_bazi):
        """四柱十神计算正确"""
        result = analyze_ten_gods_chart(sample_bazi)
        # 日主为戊(阳土)
        pillars = result["pillars"]
        assert "year" in pillars
        assert "month" in pillars
        assert "day" in pillars
        assert "hour" in pillars
        
        # 日柱应为日主
        assert pillars["day"]["ten_god"] == "日主"
        
        # 年柱甲(阳木) vs 戊(阳土) -> 木克土，同阳 -> 七杀
        assert pillars["year"]["ten_god"] == "七杀"
        
        # 月柱丙(阳火) vs 戊(阳土) -> 火生土，同阳 -> 偏印
        assert pillars["month"]["ten_god"] == "偏印"
        
        # 时柱庚(阳金) vs 戊(阳土) -> 土生金，同阳 -> 食神
        assert pillars["hour"]["ten_god"] == "食神"

    def test_chart_hidden_gods(self, sample_bazi):
        """藏干十神不为空"""
        result = analyze_ten_gods_chart(sample_bazi)
        assert len(result["hidden_gods"]) > 0
        for hg in result["hidden_gods"]:
            assert "pillar" in hg
            assert "hidden_stem" in hg
            assert "ten_god" in hg

    def test_chart_dominant_gods(self, sample_bazi):
        """旺神列表"""
        result = analyze_ten_gods_chart(sample_bazi)
        assert isinstance(result["dominant_gods"], list)

    def test_chart_analysis_text(self, sample_bazi):
        """分析文字不为空"""
        result = analyze_ten_gods_chart(sample_bazi)
        assert len(result["analysis"]) > 10

    def test_chart_god_distribution(self, sample_bazi):
        """十神分布字典"""
        result = analyze_ten_gods_chart(sample_bazi)
        dist = result["god_distribution"]
        assert isinstance(dist, dict)
        for god, count in dist.items():
            assert count > 0


# ============================================================
# 穿搭风格建议测试
# ============================================================

class TestStyleSuggestion:
    """穿搭风格建议测试"""

    def test_style_suggestion_all_gods(self):
        """所有十神都有穿搭建议"""
        for name in TEN_GODS:
            result = get_style_suggestion(name)
            assert result["ten_god"] == name
            assert len(result["style_keywords"]) > 0
            assert len(result["color_suggestion"]) > 0
            assert len(result["material_suggestion"]) > 0
            assert "description" in result

    def test_style_suggestion_bi_jian(self):
        """比肩穿搭建议"""
        result = get_style_suggestion("比肩")
        assert "简约" in result["style_keywords"] or "干练" in result["style_keywords"]

    def test_style_suggestion_qi_sha(self):
        """七杀穿搭建议"""
        result = get_style_suggestion("七杀")
        assert "强势" in result["style_keywords"] or "硬朗" in result["style_keywords"]

    def test_multi_god_style(self):
        """多十神综合建议"""
        result = get_multi_god_style_suggestion(["食神", "正官"])
        assert "style_keywords" in result
        assert "colors" in result
        assert "materials" in result
        assert "advice" in result
        assert len(result["style_keywords"]) > 0
        assert len(result["colors"]) > 0

    def test_multi_god_style_dedup(self):
        """多十神建议去重"""
        result = get_multi_god_style_suggestion(["比肩", "比肩"])
        # 重复十神应去重
        keywords = result["style_keywords"]
        assert len(keywords) == len(set(keywords))
