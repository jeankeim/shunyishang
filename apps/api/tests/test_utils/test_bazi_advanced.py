"""
八字高级分析测试
纳音五行、地支藏干、刑冲克害
"""

import pytest

from packages.utils.bazi_advanced import (
    get_nayin_element,
    get_hidden_stems,
    analyze_chong,
    analyze_xing,
    analyze_hai,
    analyze_he,
    full_bazi_analysis,
    NAYIN_TABLE,
    NAYIN_DESCRIPTIONS,
    HIDDEN_STEMS_TABLE,
    CHONG_PAIRS,
    XING_GROUPS,
    XING_MUTUAL,
    HAI_PAIRS,
    SANHE_GROUPS,
    LIUHE_PAIRS,
)
from packages.utils.wuxing_rules import TIANGAN_WUXING, DIZHI_WUXING


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


@pytest.fixture
def sample_bazi_with_chong():
    """带冲的八字（子午冲）"""
    return {
        "pillars": {
            "year": "甲子",
            "month": "丙午",
            "day": "戊午",
            "hour": "庚申",
        },
        "eight_chars": ["甲", "子", "丙", "午", "戊", "午", "庚", "申"],
        "day_master": "土",
        "pillars_extra": {},
    }


@pytest.fixture
def sample_bazi_with_he():
    """带三合的八字（申子辰合水局）"""
    return {
        "pillars": {
            "year": "甲子",
            "month": "丙辰",
            "day": "戊申",
            "hour": "庚辰",
        },
        "eight_chars": ["甲", "子", "丙", "辰", "戊", "申", "庚", "辰"],
        "day_master": "土",
    }


# ============================================================
# 纳音五行测试
# ============================================================

class TestNayin:
    """纳音五行测试"""

    def test_nayin_table_has_60_entries(self):
        """60甲子纳音表应有60个条目"""
        assert len(NAYIN_TABLE) == 60

    def test_nayin_jiazi(self):
        """甲子纳音为海中金"""
        result = get_nayin_element("甲", "子")
        assert result["nayin_name"] == "海中金"
        assert result["nayin_element"] == "金"

    def test_nayin_guihai(self):
        """癸亥纳音为大海水"""
        result = get_nayin_element("癸", "亥")
        assert result["nayin_name"] == "大海水"
        assert result["nayin_element"] == "水"

    def test_nayin_all_60_jiazi(self):
        """60甲子全部有纳音"""
        # 生成60甲子
        tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        tg_idx, dz_idx = 0, 0
        for i in range(60):
            gz = f"{tiangan[tg_idx]}{dizhi[dz_idx]}"
            assert gz in NAYIN_TABLE, f"缺少纳音: {gz}"
            name, elem = NAYIN_TABLE[gz]
            assert elem in ["金", "木", "水", "火", "土"]
            tg_idx = (tg_idx + 1) % 10
            dz_idx = (dz_idx + 1) % 12

    def test_nayin_has_description(self):
        """每个纳音都有描述"""
        for gz, (name, elem) in NAYIN_TABLE.items():
            assert name in NAYIN_DESCRIPTIONS, f"缺少纳音描述: {name}"

    def test_nayin_returns_ganzhi(self):
        """纳音结果包含干支"""
        result = get_nayin_element("丙", "寅")
        assert result["ganzhi"] == "丙寅"

    def test_nayin_element_distribution(self):
        """纳音五行分布合理（每种五行都有）"""
        elements = set()
        for name, elem in NAYIN_TABLE.values():
            elements.add(elem)
        assert elements == {"金", "木", "水", "火", "土"}

    def test_nayin_unknown_ganzhi(self):
        """未知干支返回默认值"""
        result = get_nayin_element("X", "Y")
        assert result["nayin_name"] == "未知"


# ============================================================
# 地支藏干测试
# ============================================================

class TestHiddenStems:
    """地支藏干测试"""

    def test_hidden_stems_all_12_branches(self):
        """12地支都有藏干"""
        branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        for b in branches:
            assert b in HIDDEN_STEMS_TABLE
            stems = get_hidden_stems(b)
            assert len(stems) > 0

    def test_hidden_stems_zi(self):
        """子藏癸水"""
        stems = get_hidden_stems("子")
        assert len(stems) == 1
        assert stems[0]["stem"] == "癸"
        assert stems[0]["element"] == "水"
        assert stems[0]["is_main"] is True

    def test_hidden_stems_yin(self):
        """寅藏甲丙戊（主气甲木）"""
        stems = get_hidden_stems("寅")
        assert len(stems) == 3
        assert stems[0]["stem"] == "甲"
        assert stems[0]["is_main"] is True
        assert stems[1]["stem"] == "丙"
        assert stems[1]["is_main"] is False
        assert stems[2]["stem"] == "戊"
        assert stems[2]["is_main"] is False

    def test_hidden_stems_you(self):
        """酉藏辛金（单一藏干）"""
        stems = get_hidden_stems("酉")
        assert len(stems) == 1
        assert stems[0]["stem"] == "辛"
        assert stems[0]["element"] == "金"

    def test_hidden_stems_main_exists(self):
        """每个地支至少有一个主气"""
        branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        for b in branches:
            stems = get_hidden_stems(b)
            main_stems = [s for s in stems if s["is_main"]]
            assert len(main_stems) >= 1, f"{b}缺少主气"

    def test_hidden_stems_unknown(self):
        """未知地支返回空列表"""
        stems = get_hidden_stems("X")
        assert stems == []


# ============================================================
# 冲（六冲）测试
# ============================================================

class TestChong:
    """六冲分析测试"""

    def test_chong_pairs_count(self):
        """六冲应有6对"""
        assert len(CHONG_PAIRS) == 6

    def test_chong_zi_wu(self):
        """子午冲"""
        result = analyze_chong(["子", "午", "寅"])
        assert result["has_chong"] is True
        assert result["count"] == 1
        pair = result["pairs"][0]
        assert pair["branch_a"] == "子"
        assert pair["branch_b"] == "午"

    def test_chong_none(self):
        """无冲"""
        result = analyze_chong(["子", "丑", "寅"])
        assert result["has_chong"] is False
        assert result["count"] == 0

    def test_chong_multiple(self):
        """多组冲"""
        result = analyze_chong(["子", "午", "卯", "酉"])
        assert result["has_chong"] is True
        assert result["count"] == 2

    def test_chong_all_six(self):
        """六冲全在"""
        result = analyze_chong(["子", "午", "丑", "未", "寅", "申", "卯", "酉", "辰", "戌", "巳", "亥"])
        assert result["count"] == 6


# ============================================================
# 刑（三刑）测试
# ============================================================

class TestXing:
    """三刑分析测试"""

    def test_xing_groups_count(self):
        """三刑应有2组"""
        assert len(XING_GROUPS) == 2

    def test_xing_yin_si_shen(self):
        """寅巳申三刑"""
        result = analyze_xing(["寅", "巳", "申"])
        assert result["has_xing"] is True
        assert result["count"] >= 1

    def test_xing_chou_xu_wei(self):
        """丑戌未三刑"""
        result = analyze_xing(["丑", "戌", "未"])
        assert result["has_xing"] is True

    def test_xing_zi_mao(self):
        """子卯互刑"""
        result = analyze_xing(["子", "卯"])
        assert result["has_xing"] is True
        xing_types = [g["type"] for g in result["groups"]]
        assert "互刑" in xing_types

    def test_xing_none(self):
        """无刑"""
        result = analyze_xing(["子", "丑", "辰"])
        assert result["has_xing"] is False

    def test_xing_half(self):
        """半刑（三刑中两个）"""
        result = analyze_xing(["寅", "巳"])
        assert result["has_xing"] is True
        xing_types = [g["type"] for g in result["groups"]]
        assert "半刑" in xing_types

    def test_xing_self(self):
        """自刑（辰午酉亥重复）"""
        result = analyze_xing(["辰", "辰"])
        assert result["has_xing"] is True
        xing_types = [g["type"] for g in result["groups"]]
        assert "自刑" in xing_types


# ============================================================
# 害（六害）测试
# ============================================================

class TestHai:
    """六害分析测试"""

    def test_hai_pairs_count(self):
        """六害应有6对"""
        assert len(HAI_PAIRS) == 6

    def test_hai_zi_wei(self):
        """子未害"""
        result = analyze_hai(["子", "未"])
        assert result["has_hai"] is True
        assert result["count"] == 1

    def test_hai_none(self):
        """无害"""
        result = analyze_hai(["子", "丑", "寅"])
        assert result["has_hai"] is False

    def test_hai_all_six(self):
        """六害全在"""
        result = analyze_hai(["子", "未", "丑", "午", "寅", "巳", "卯", "辰", "申", "亥", "酉", "戌"])
        assert result["count"] == 6


# ============================================================
# 合（三合/六合）测试
# ============================================================

class TestHe:
    """合分析测试"""

    def test_sanhe_groups_count(self):
        """三合应有4组"""
        assert len(SANHE_GROUPS) == 4

    def test_liuhe_pairs_count(self):
        """六合应有6对"""
        assert len(LIUHE_PAIRS) == 6

    def test_sanhe_shen_zi_chen(self):
        """申子辰合水局"""
        result = analyze_he(["申", "子", "辰"])
        assert result["has_he"] is True
        assert len(result["sanhe"]) >= 1
        sanhe = result["sanhe"][0]
        assert sanhe["element"] == "水"
        assert sanhe["type"] == "三合"

    def test_sanhe_half(self):
        """半合（三合中两个）"""
        result = analyze_he(["申", "子"])
        assert result["has_he"] is True
        assert len(result["sanhe"]) >= 1
        assert result["sanhe"][0]["type"] == "半合"

    def test_liuhe_zi_chou(self):
        """子丑合化土"""
        result = analyze_he(["子", "丑"])
        assert result["has_he"] is True
        assert len(result["liuhe"]) >= 1
        he = result["liuhe"][0]
        assert he["element"] == "土"

    def test_he_none(self):
        """无合"""
        result = analyze_he(["寅", "卯", "巳"])
        assert result["has_he"] is False

    def test_sanhe_all_four(self):
        """四组三合全在"""
        result = analyze_he(["申", "子", "辰", "亥", "卯", "未", "寅", "午", "戌", "巳", "酉", "丑"])
        sanhe_count = len(result["sanhe"])
        assert sanhe_count == 4


# ============================================================
# 完整八字分析测试
# ============================================================

class TestFullBaziAnalysis:
    """完整八字分析测试"""

    def test_full_analysis_structure(self, sample_bazi):
        """完整分析结构"""
        result = full_bazi_analysis(sample_bazi)
        assert "pillars" in result
        assert "nayin" in result
        assert "hidden_stems" in result
        assert "chong" in result
        assert "xing" in result
        assert "hai" in result
        assert "he" in result
        assert "analysis" in result

    def test_full_analysis_nayin(self, sample_bazi):
        """纳音四柱完整"""
        result = full_bazi_analysis(sample_bazi)
        nayin = result["nayin"]
        assert "year" in nayin
        assert "month" in nayin
        assert "day" in nayin
        assert "hour" in nayin
        for name in ["year", "month", "day", "hour"]:
            assert nayin[name]["nayin_name"] != "未知"

    def test_full_analysis_hidden_stems(self, sample_bazi):
        """藏干四柱完整"""
        result = full_bazi_analysis(sample_bazi)
        hidden = result["hidden_stems"]
        for name in ["year", "month", "day", "hour"]:
            assert len(hidden[name]) > 0

    def test_full_analysis_chong_detection(self, sample_bazi_with_chong):
        """冲检测"""
        result = full_bazi_analysis(sample_bazi_with_chong)
        # 子午冲
        assert result["chong"]["has_chong"] is True

    def test_full_analysis_he_detection(self, sample_bazi_with_he):
        """合检测"""
        result = full_bazi_analysis(sample_bazi_with_he)
        # 申子辰合水局
        assert result["he"]["has_he"] is True

    def test_full_analysis_text(self, sample_bazi):
        """分析文字不为空"""
        result = full_bazi_analysis(sample_bazi)
        assert len(result["analysis"]) > 10

    def test_full_analysis_no_conflict(self, sample_bazi):
        """无刑冲克害时文字说明"""
        # 甲子丙寅戊午庚申 - 无明显冲合
        result = full_bazi_analysis(sample_bazi)
        # analysis应该包含文字
        assert "纳音" in result["analysis"]
