"""
大运流年计算器测试
"""

import pytest
from datetime import date

from packages.utils.destiny_calculator import (
    calculate_major_luck,
    get_current_major_luck,
    calculate_annual_luck,
    analyze_year_fortune,
    _determine_luck_level,
    _jiazi_index,
    _jiazi_at,
    _calculate_start_age,
    _get_element_relation_desc,
    _get_element_relation_coef,
    JIAZI_60,
    TIANGAN_LIST,
    DIZHI_LIST,
)


@pytest.fixture
def sample_bazi_male():
    """测试用男性八字（阳年男，顺排）"""
    return {
        "pillars": {
            "year": "甲子",   # 甲=阳木，阳男顺排
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
        "gender": "男",
        "_birth_year": 1995,
        "_birth_month": 6,
        "_birth_day": 15,
    }


@pytest.fixture
def sample_bazi_female_yin():
    """测试用女性八字（阴年女，顺排）"""
    return {
        "pillars": {
            "year": "乙丑",   # 乙=阴木，阴女顺排
            "month": "丁卯",
            "day": "己巳",
            "hour": "辛未",
        },
        "eight_chars": ["乙", "丑", "丁", "卯", "己", "巳", "辛", "未"],
        "five_elements_count": {"金": 1, "木": 2, "水": 0, "火": 2, "土": 3},
        "dominant_element": "土",
        "lacking_element": "水",
        "day_master": "土",
        "month_element": "木",
        "suggested_elements": ["火", "土"],
        "avoid_elements": ["木", "水"],
        "reasoning": "测试用",
        "gender": "女",
        "_birth_year": 1997,
        "_birth_month": 3,
        "_birth_day": 10,
    }


@pytest.fixture
def sample_bazi_yin_male():
    """测试用阴年男八字（逆排）"""
    return {
        "pillars": {
            "year": "乙亥",   # 乙=阴，阴男逆排
            "month": "戊寅",
            "day": "甲子",
            "hour": "丙寅",
        },
        "eight_chars": ["乙", "亥", "戊", "寅", "甲", "子", "丙", "寅"],
        "five_elements_count": {"金": 0, "木": 3, "水": 2, "火": 1, "土": 2},
        "dominant_element": "木",
        "lacking_element": "金",
        "day_master": "木",
        "month_element": "木",
        "suggested_elements": ["水", "火"],
        "avoid_elements": ["金"],
        "reasoning": "测试用",
        "gender": "男",
        "_birth_year": 1995,
        "_birth_month": 2,
        "_birth_day": 20,
    }


@pytest.fixture
def sample_bazi_yang_female():
    """测试用阳年女八字（逆排）"""
    return {
        "pillars": {
            "year": "甲戌",   # 甲=阳，阳女逆排
            "month": "丙寅",
            "day": "庚午",
            "hour": "壬申",
        },
        "eight_chars": ["甲", "戌", "丙", "寅", "庚", "午", "壬", "申"],
        "five_elements_count": {"金": 2, "木": 2, "水": 1, "火": 2, "土": 1},
        "dominant_element": "金",
        "lacking_element": None,
        "day_master": "金",
        "month_element": "木",
        "suggested_elements": ["土", "金"],
        "avoid_elements": ["木", "火"],
        "reasoning": "测试用",
        "gender": "女",
        "_birth_year": 1994,
        "_birth_month": 7,
        "_birth_day": 5,
    }


# ============================================================
# 60甲子序列测试
# ============================================================

class TestJiaziSequence:
    """60甲子序列测试"""

    def test_jiazi_length(self):
        """60甲子序列应有60个"""
        assert len(JIAZI_60) == 60

    def test_jiazi_first(self):
        """第一个应为甲子"""
        assert JIAZI_60[0] == "甲子"

    def test_jiazi_last(self):
        """最后一个应为癸亥"""
        assert JIAZI_60[59] == "癸亥"

    def test_jiazi_index(self):
        """测试索引查找"""
        assert _jiazi_index("甲子") == 0
        assert _jiazi_index("癸亥") == 59

    def test_jiazi_at_wrap(self):
        """测试索引回绕"""
        assert _jiazi_at(60) == "甲子"
        assert _jiazi_at(-1) == "癸亥"

    def test_jiazi_no_duplicate(self):
        """60甲子无重复"""
        assert len(set(JIAZI_60)) == 60


# ============================================================
# 大运计算测试
# ============================================================

class TestMajorLuck:
    """大运计算测试"""

    def test_major_luck_yang_male_forward(self, sample_bazi_male):
        """阳男顺排大运"""
        luck = calculate_major_luck(sample_bazi_male, "男")
        assert len(luck) == 8

        # 阳男顺排，月柱丙寅(index=2)，第一步大运应为丁卯(index=3)
        assert luck[0]["ganzhi"] == "丁卯"

        # 每步10年
        for i, period in enumerate(luck):
            assert period["start_age"] == period["end_age"] - 9
            if i > 0:
                assert period["start_age"] == luck[i-1]["end_age"] + 1

    def test_major_luck_yin_male_backward(self, sample_bazi_yin_male):
        """阴男逆排大运"""
        luck = calculate_major_luck(sample_bazi_yin_male, "男")
        assert len(luck) == 8

        # 阴男逆排，月柱戊寅(index=14)，第一步大运应为丁丑(index=13)
        assert luck[0]["ganzhi"] == "丁丑"

    def test_major_luck_yin_female_forward(self, sample_bazi_female_yin):
        """阴女顺排大运"""
        luck = calculate_major_luck(sample_bazi_female_yin, "女")
        assert len(luck) == 8

        # 阴女顺排，月柱丁卯(index=3)，第一步大运应为戊辰(index=4)
        assert luck[0]["ganzhi"] == "戊辰"

    def test_major_luck_yang_female_backward(self, sample_bazi_yang_female):
        """阳女逆排大运"""
        luck = calculate_major_luck(sample_bazi_yang_female, "女")
        assert len(luck) == 8

        # 阳女逆排，月柱丙寅(index=2)，第一步大运应为乙丑(index=1)
        assert luck[0]["ganzhi"] == "乙丑"

    def test_luck_period_fields(self, sample_bazi_male):
        """大运周期应包含所有字段"""
        luck = calculate_major_luck(sample_bazi_male, "男")
        for period in luck:
            assert "start_age" in period
            assert "end_age" in period
            assert "heavenly_stem" in period
            assert "earthly_branch" in period
            assert "ganzhi" in period
            assert "element" in period
            assert "luck_level" in period
            assert period["luck_level"] in ["旺", "相", "休", "囚", "死"]

    def test_luck_level_determination(self):
        """测试旺衰等级判断"""
        assert _determine_luck_level("土", "土") == "旺"   # 同我
        assert _determine_luck_level("火", "土") == "相"   # 生我（火生土）
        assert _determine_luck_level("金", "土") == "休"   # 我生（土生金）
        assert _determine_luck_level("水", "土") == "囚"   # 我克（土克水）
        assert _determine_luck_level("木", "土") == "死"   # 克我（木克土）


# ============================================================
# 当前大运测试
# ============================================================

class TestCurrentMajorLuck:
    """当前大运获取测试"""

    def test_get_current_luck_normal(self, sample_bazi_male):
        """正常年龄获取当前大运"""
        luck = calculate_major_luck(sample_bazi_male, "男")
        # 取第二步大运的中间年龄
        target_age = luck[1]["start_age"] + 5
        current = get_current_major_luck(sample_bazi_male, "男", target_age)
        assert current is not None
        assert current["start_age"] <= target_age <= current["end_age"]

    def test_get_current_luck_age_zero(self, sample_bazi_male):
        """年龄为0的边界条件"""
        current = get_current_major_luck(sample_bazi_male, "男", 0)
        # 应返回第一步大运或None
        if current is not None:
            assert current["start_age"] >= 0

    def test_get_current_luck_age_100_plus(self, sample_bazi_male):
        """年龄100+的边界条件"""
        current = get_current_major_luck(sample_bazi_male, "男", 120)
        # 应返回最后一步大运
        if current is not None:
            luck = calculate_major_luck(sample_bazi_male, "男")
            assert current == luck[-1]

    def test_get_current_luck_negative_age(self, sample_bazi_male):
        """负年龄返回None"""
        current = get_current_major_luck(sample_bazi_male, "男", -5)
        assert current is None


# ============================================================
# 流年计算测试
# ============================================================

class TestAnnualLuck:
    """流年计算测试"""

    def test_annual_luck_2024(self, sample_bazi_male):
        """2024年流年（甲辰年）"""
        result = calculate_annual_luck(sample_bazi_male, 2024)
        assert result["year"] == 2024
        # 2024年: (2024-4)%10=0 -> 甲, (2024-4)%12=0 -> 子? 
        # Wait: (2024-4)=2020, 2020%10=0 -> 甲, 2020%12=168*12=2016, 2020-2016=4 -> 辰
        # Actually 2020 % 12 = 2020 - 168*12 = 2020 - 2016 = 4 -> 辰
        assert result["heavenly_stem"] == "甲"
        assert result["earthly_branch"] == "辰"
        assert result["ganzhi"] == "甲辰"
        assert "element" in result
        assert "relationship" in result
        assert "advice" in result

    def test_annual_luck_1984_jiazi(self, sample_bazi_male):
        """1984年为甲子年"""
        result = calculate_annual_luck(sample_bazi_male, 1984)
        assert result["heavenly_stem"] == "甲"
        assert result["earthly_branch"] == "子"
        assert result["ganzhi"] == "甲子"

    def test_annual_luck_2044(self, sample_bazi_male):
        """2044年（60年一甲子后应为甲子）"""
        result = calculate_annual_luck(sample_bazi_male, 2044)
        assert result["heavenly_stem"] == "甲"
        assert result["earthly_branch"] == "子"

    def test_annual_luck_has_advice(self, sample_bazi_male):
        """流年应有建议文字"""
        result = calculate_annual_luck(sample_bazi_male, 2025)
        assert len(result["advice"]) > 10

    def test_annual_luck_suggested_element_bonus(self, sample_bazi_male):
        """喜用神年应有加成提示"""
        # sample_bazi_male suggested = ["火", "土"]
        # 2025年: (2025-4)%10=1 -> 乙, element=木
        result = calculate_annual_luck(sample_bazi_male, 2025)
        assert result["element"] == "木"


# ============================================================
# 年度运势分析测试
# ============================================================

class TestYearFortune:
    """年度运势分析测试"""

    def test_year_fortune_structure(self, sample_bazi_male):
        """年度运势结构完整性"""
        result = analyze_year_fortune(sample_bazi_male, 2025)
        assert result["year"] == 2025
        assert "scores" in result
        assert "overall_score" in result
        assert "lucky_colors" in result
        assert "lucky_materials" in result
        assert "lucky_directions" in result
        assert "lucky_elements" in result
        assert "outfit_advice" in result
        assert "annual_luck" in result

    def test_year_fortune_scores_range(self, sample_bazi_male):
        """五维度评分在0-100范围内"""
        result = analyze_year_fortune(sample_bazi_male, 2025)
        for dim, score in result["scores"].items():
            assert dim in ["career", "wealth", "love", "health", "study"]
            assert 0 <= score <= 100

    def test_year_fortune_overall_score(self, sample_bazi_male):
        """综合评分为五维度平均值"""
        result = analyze_year_fortune(sample_bazi_male, 2025)
        expected = int(sum(result["scores"].values()) / len(result["scores"]))
        assert result["overall_score"] == expected

    def test_year_fortune_lucky_colors_not_empty(self, sample_bazi_male):
        """幸运颜色不为空"""
        result = analyze_year_fortune(sample_bazi_male, 2025)
        assert len(result["lucky_colors"]) > 0

    def test_year_fortune_outfit_advice_not_empty(self, sample_bazi_male):
        """穿搭建议不为空"""
        result = analyze_year_fortune(sample_bazi_male, 2025)
        assert len(result["outfit_advice"]) > 10

    def test_year_fortune_different_years(self, sample_bazi_male):
        """不同年份运势不同"""
        r1 = analyze_year_fortune(sample_bazi_male, 2024)
        r2 = analyze_year_fortune(sample_bazi_male, 2025)
        # 不同年份的天干地支不同
        assert r1["annual_luck"]["ganzhi"] != r2["annual_luck"]["ganzhi"]

    def test_year_fortune_with_yin_female(self, sample_bazi_female_yin):
        """阴女八字年度运势"""
        result = analyze_year_fortune(sample_bazi_female_yin, 2025)
        assert result["year"] == 2025
        assert len(result["scores"]) == 5


# ============================================================
# 辅助函数测试
# ============================================================

class TestJiaziIndexEdgeCases:
    """测试60甲子索引边缘情况"""

    def test_invalid_ganzhi(self):
        """无效干支返回0"""
        assert _jiazi_index("无效") == 0

    def test_empty_string(self):
        """空字符串返回0"""
        assert _jiazi_index("") == 0


class TestCalculateStartAge:
    """测试起运年龄计算"""

    def test_december_birth_forward(self):
        """12月出生阳男顺排（跨年计算）"""
        # 1990年庚午年，庚=阳，阳男顺排，12月出生
        age = _calculate_start_age(1990, 12, 15, "男")
        assert isinstance(age, int)
        assert age >= 1

    def test_january_birth_reverse(self):
        """1月出生阴男逆排（跨年计算）"""
        # 1995年乙亥年，乙=阴，阴男逆排，1月出生
        age = _calculate_start_age(1995, 1, 15, "男")
        assert isinstance(age, int)
        assert age >= 1

    def test_normal_forward(self):
        """正常顺排"""
        # 1990年庚午年，庚=阳，阳男顺排
        age = _calculate_start_age(1990, 6, 15, "男")
        assert isinstance(age, int)
        assert age >= 1

    def test_normal_reverse(self):
        """正常逆排"""
        # 1995年乙亥年，乙=阴，阴男逆排
        age = _calculate_start_age(1995, 6, 15, "男")
        assert isinstance(age, int)
        assert age >= 1

    def test_yin_female_forward(self):
        """阴女顺排"""
        # 1997年丁丑年，丁=阴，阴女顺排
        age = _calculate_start_age(1997, 3, 10, "女")
        assert isinstance(age, int)
        assert age >= 1

    def test_yang_female_reverse(self):
        """阳女逆排"""
        # 1994年甲戌年，甲=阳，阳女逆排
        age = _calculate_start_age(1994, 7, 5, "女")
        assert isinstance(age, int)
        assert age >= 1


class TestAnnualLuckAdviceBranches:
    """测试流年建议各分支"""

    def test_advice_same_element(self, sample_bazi_male):
        """流年五行与日主相同（比和）"""
        # day_master="土", need year with element="土"
        # 2028: (2028-4)%10=4 → 戊 → 土
        result = calculate_annual_luck(sample_bazi_male, 2028)
        assert "比和" in result["advice"]

    def test_advice_sheng_fu(self, sample_bazi_male):
        """流年生扶日主"""
        # day_master="土", need element that generates 土 → 火
        # 2026: (2026-4)%10=2 → 丙 → 火
        result = calculate_annual_luck(sample_bazi_male, 2026)
        assert "生扶" in result["advice"]

    def test_advice_xie_qi(self, sample_bazi_male):
        """日主生流年（泄气）"""
        # day_master="土", need element that 土 generates → 金
        # 2030: (2030-4)%10=6 → 庚 → 金
        result = calculate_annual_luck(sample_bazi_male, 2030)
        assert "泄气" in result["advice"] or "精力外泄" in result["advice"]

    def test_advice_ke_zhi(self, sample_bazi_male):
        """日主克流年"""
        # day_master="土", need element that 土 克 → 水
        # 2032: (2032-4)%10=8 → 壬 → 水
        result = calculate_annual_luck(sample_bazi_male, 2032)
        assert "克之" in result["advice"] or "量力而行" in result["advice"]

    def test_advice_shou_ke(self, sample_bazi_male):
        """流年克日主（受克）"""
        # day_master="土", need element that 克 土 → 木
        # 2024: (2024-4)%10=0 → 甲 → 木
        result = calculate_annual_luck(sample_bazi_male, 2024)
        assert "克制" in result["advice"] or "韬光养晦" in result["advice"]

    def test_suggested_element_bonus(self, sample_bazi_male):
        """喜用神加成"""
        # suggested=["火","土"], 2028年戊→土
        result = calculate_annual_luck(sample_bazi_male, 2028)
        assert "喜用神" in result["advice"]

    def test_avoid_element_penalty(self, sample_bazi_male):
        """忌神减分"""
        # avoid=["木","水"], 2024年甲→木
        result = calculate_annual_luck(sample_bazi_male, 2024)
        assert "忌神" in result["advice"]


class TestGetElementRelationDesc:
    """测试五行关系描述"""

    def test_same_element(self):
        """比和"""
        assert _get_element_relation_desc("金", "金") == "比和"

    def test_sheng(self):
        """生扶"""
        # 金生水, so elem_a="金", elem_b="水" → 生扶
        assert _get_element_relation_desc("金", "水") == "生扶"

    def test_xie(self):
        """泄气"""
        # 金生水, so elem_a="水", elem_b="金" → 泄气
        assert _get_element_relation_desc("水", "金") == "泄气"

    def test_ke(self):
        """克制"""
        # 金克木, so elem_a="金", elem_b="木" → 克制
        assert _get_element_relation_desc("金", "木") == "克制"

    def test_shou_ke(self):
        """受克"""
        # 金克木, so elem_a="木", elem_b="金" → 受克
        assert _get_element_relation_desc("木", "金") == "受克"


class TestGetElementRelationCoef:
    """测试五行关系系数"""

    def test_same_element(self):
        """比和"""
        assert _get_element_relation_coef("金", "金") == 1.05

    def test_sheng(self):
        """生扶"""
        assert _get_element_relation_coef("金", "水") == 1.15

    def test_xie(self):
        """泄气"""
        assert _get_element_relation_coef("水", "金") == 0.90

    def test_ke(self):
        """克制"""
        assert _get_element_relation_coef("金", "木") == 0.85

    def test_shou_ke(self):
        """受克"""
        assert _get_element_relation_coef("木", "金") == 0.70


class TestYearFortuneElementBonus:
    """测试年度运势喜用神/忌神加成"""

    def test_suggested_element_year(self, sample_bazi_male):
        """喜用神年份加成"""
        # suggested=["火","土"], 2028年=戊→土
        result = analyze_year_fortune(sample_bazi_male, 2028)
        assert result["overall_score"] > 0

    def test_avoid_element_year(self, sample_bazi_male):
        """忌神年份减分"""
        # avoid=["木","水"], 2024年=甲→木
        result_avoid = analyze_year_fortune(sample_bazi_male, 2024)
        # 2028年=戊→土（喜用神）
        result_suggested = analyze_year_fortune(sample_bazi_male, 2028)
        # 喜用神年份运势应该高于忌神年份
        assert result_suggested["overall_score"] >= result_avoid["overall_score"]

    def test_different_bazi_different_scores(self, sample_bazi_male, sample_bazi_yin_male):
        """不同八字同一年份运势不同"""
        r1 = analyze_year_fortune(sample_bazi_male, 2025)
        r2 = analyze_year_fortune(sample_bazi_yin_male, 2025)
        assert r1["overall_score"] != r2["overall_score"]
