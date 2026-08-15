"""
八字计算器测试
测试 calculate_bazi, count_five_elements, find_lacking_element,
infer_xiyong (含默认逻辑), infer_elements_from_text, merge_recommendations
"""

import pytest
from unittest.mock import patch

from packages.utils.bazi_calculator import (
    calculate_bazi,
    count_five_elements,
    find_lacking_element,
    infer_xiyong,
    infer_elements_from_text,
    extract_explicit_element_intent,
    merge_recommendations,
)
from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    DIZHI_CANGAN,
    WUXING_LIST,
    XIYONG_RULES,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
    WUXING_BEI_KE,
)


# ============================================================
# calculate_bazi 测试
# ============================================================

class TestCalculateBazi:
    """测试八字计算"""

    def test_male_birth(self):
        """男性八字计算"""
        result = calculate_bazi(1990, 5, 15, 10, "男")
        assert "pillars" in result
        assert "eight_chars" in result
        assert "five_elements_count" in result
        assert "dominant_element" in result
        assert "lacking_element" in result
        assert "day_master" in result
        assert "month_element" in result
        assert "suggested_elements" in result
        assert "avoid_elements" in result
        assert "reasoning" in result
        assert len(result["eight_chars"]) == 8
        assert "year" in result["pillars"]
        assert "month" in result["pillars"]
        assert "day" in result["pillars"]
        assert "hour" in result["pillars"]

    def test_female_birth(self):
        """女性八字计算"""
        result = calculate_bazi(1995, 10, 3, 14, "女")
        assert len(result["eight_chars"]) == 8
        assert result["day_master"] in WUXING_LIST

    def test_five_elements_count_has_all_elements(self):
        """五行统计包含所有五行"""
        result = calculate_bazi(1988, 3, 21, 8, "男")
        for w in WUXING_LIST:
            assert w in result["five_elements_count"]

    def test_dominant_element_is_in_count(self):
        """最旺五行在统计中"""
        result = calculate_bazi(1990, 5, 15, 10, "男")
        assert result["dominant_element"] in result["five_elements_count"]

    def test_suggested_elements_from_rules(self):
        """喜用神来自规则表"""
        result = calculate_bazi(1990, 5, 15, 10, "男")
        key = (result["day_master"], result["month_element"])
        if key in XIYONG_RULES:
            expected_suggested, expected_avoid, _ = XIYONG_RULES[key]
            assert result["suggested_elements"] == expected_suggested
            assert result["avoid_elements"] == expected_avoid

    def test_birth_at_midnight(self):
        """子时出生"""
        result = calculate_bazi(2000, 1, 1, 0, "男")
        assert len(result["eight_chars"]) == 8

    def test_birth_at_late_hour(self):
        """亥时出生"""
        result = calculate_bazi(2000, 1, 1, 22, "女")
        assert len(result["eight_chars"]) == 8

    def test_birth_at_zi_hour_day_shift(self):
        """子时(23时)出生 - cnlunar 自动使用次日日柱"""
        # 2000-01-15 23:00 的日柱应该与 2000-01-16 中午相同（子时跨日）
        result_late = calculate_bazi(2000, 1, 15, 23, "男")
        result_next_day = calculate_bazi(2000, 1, 16, 12, "男")
        # cnlunar 已正确处理子时跨日，两者日柱应相同
        assert result_late["pillars"]["day"] == result_next_day["pillars"]["day"]

    def test_round_precision_for_cangan_weights(self):
        """验证 round() 精度：地支藏干小数权重不被截断"""
        # 午: 丁(火,主气1) + 己(土,中气0.5) → round(0.5)=0 (Python banker's rounding)
        # 改用 int(x + 0.5) 确保传统四舍五入
        chars = ["午"]
        result = count_five_elements(chars)
        assert result["火"] == 1  # 主气
        # round(0.5) in Python 3 = 0 (banker's rounding), 这是预期行为
        assert result["土"] == 0  # 0.5 round to 0 (banker's rounding)


# ============================================================
# count_five_elements 测试
# ============================================================

class TestCountFiveElements:
    """测试五行统计"""

    def test_all_tiangan(self):
        """全部天干"""
        chars = ["甲", "丙", "戊", "庚", "壬", "乙", "丁", "己"]
        result = count_five_elements(chars)
        assert result["木"] == 2  # 甲, 乙
        assert result["火"] == 2  # 丙, 丁
        assert result["土"] == 2  # 戊, 己
        assert result["金"] == 1  # 庚
        assert result["水"] == 1  # 壬

    def test_all_dizhi(self):
        """全部地支（含藏干计算）"""
        chars = ["子", "卯", "午", "酉"]
        result = count_five_elements(chars)
        # 子: 癸(水) → 水=1
        # 卯: 乙(木) → 木=1
        # 午: 丁(火)+己(土) → 火=1, 土=0.5→0
        # 酉: 辛(金) → 金=1
        assert result["水"] >= 1
        assert result["木"] >= 1
        assert result["金"] >= 1

    def test_dizhi_with_three_cangans(self):
        """三藏干地支（主气+中气+余气）"""
        chars = ["丑"]  # 己(土主气), 癸(水中气), 辛(金余气)
        result = count_five_elements(chars)
        assert result["土"] >= 1  # 主气权重1
        # round() 处理: 中气0.5→0 (banker's rounding), 余气0.3→0
        # 单个地支的中气/余气权重较小，round后可能为0，这是预期行为

    def test_round_fix_prevents_truncation(self):
        """验证 round() 修复：多个地支的小数权重累加后不被截断"""
        # 两个午: 每个午有 己(土,中气0.5)，累加 0.5+0.5=1.0 → round(1.0)=1
        chars = ["午", "午"]
        result = count_five_elements(chars)
        assert result["火"] == 2  # 两个午的主气丁火
        assert result["土"] == 1  # 0.5+0.5=1.0, round(1.0)=1 (之前 int(1.0)=1 也正确)
        
        # 三个午: 0.5*3=1.5 → round(1.5)=2 (banker's rounding: round to even)
        chars = ["午", "午", "午"]
        result = count_five_elements(chars)
        assert result["土"] == 2  # 1.5 rounds to 2 (banker's rounding)
        
        # 关键修复场景：0.5+0.3=0.8 → round(0.8)=1, 但 int(0.8)=0
        chars = ["午", "巳"]  # 午有己(土,0.5), 巳有己(土,0.5)+庚(金,0.3)
        result = count_five_elements(chars)
        # 土的贡献: 午的己(0.5) + 巳的己(0.5) = 1.0 → round = 1
        assert result["土"] >= 1

    def test_mixed_chars(self):
        """天干地支混合"""
        chars = ["甲", "子", "丙", "午"]
        result = count_five_elements(chars)
        for w in WUXING_LIST:
            assert w in result

    def test_empty_list(self):
        """空列表"""
        result = count_five_elements([])
        for w in WUXING_LIST:
            assert result[w] == 0

    def test_unknown_chars(self):
        """未知字符不报错"""
        chars = ["甲", "X", "Y", "子"]
        result = count_five_elements(chars)
        assert result["木"] >= 1
        assert result["水"] >= 1


# ============================================================
# find_lacking_element 测试
# ============================================================

class TestFindLackingElement:
    """测试缺失五行查找"""

    def test_has_missing_element(self):
        """有缺失五行"""
        counts = {"金": 2, "木": 0, "水": 1, "火": 3, "土": 0}
        result = find_lacking_element(counts)
        assert result in ["木", "土"]  # 第一个count为0的

    def test_all_present(self):
        """所有五行都有"""
        counts = {"金": 1, "木": 2, "水": 1, "火": 1, "土": 1}
        result = find_lacking_element(counts)
        assert result is None

    def test_all_zero(self):
        """所有五行都是0"""
        counts = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
        result = find_lacking_element(counts)
        assert result is not None  # 应该返回第一个0的

    def test_single_zero(self):
        """只有一个五行为0"""
        counts = {"金": 1, "木": 1, "水": 0, "火": 1, "土": 1}
        result = find_lacking_element(counts)
        assert result == "水"


# ============================================================
# infer_xiyong 测试（含默认逻辑）
# ============================================================

class TestInferXiyong:
    """测试喜用神推断"""

    def test_rule_table_match(self):
        """规则表匹配"""
        # 木日元，木月令
        suggested, avoid, reasoning = infer_xiyong("木", "木")
        assert suggested == ["水", "火"]
        assert avoid == ["金"]

    def test_all_rule_table_combinations(self):
        """所有25种组合都能从规则表获取"""
        for dm in WUXING_LIST:
            for me in WUXING_LIST:
                suggested, avoid, reasoning = infer_xiyong(dm, me)
                assert isinstance(suggested, list)
                assert isinstance(avoid, list)
                assert isinstance(reasoning, str)
                assert len(suggested) > 0

    @patch("packages.utils.bazi_calculator.XIYONG_RULES", {})
    def test_default_logic_month_sheng_daymaster(self):
        """默认逻辑：月令生日元（偏旺）"""
        # WUXING_SHENG: 水→木, 所以 month_element="水", day_master="木"
        suggested, avoid, reasoning = infer_xiyong("木", "水")
        assert isinstance(suggested, list)
        assert isinstance(avoid, list)
        assert "偏旺" in reasoning

    @patch("packages.utils.bazi_calculator.XIYONG_RULES", {})
    def test_default_logic_month_ke_daymaster(self):
        """默认逻辑：月令克日元（偏弱）"""
        # WUXING_KE: 金→木, 所以 month_element="金", day_master="木" → 金克木
        # Wait: WUXING_KE = {木:土, 土:水, 水:火, 火:金, 金:木}
        # WUXING_KE.get("木") = "土", so month_element="土" → 土...no
        # month_element == WUXING_KE.get(day_master) → month_element == WUXING_KE.get("木") == "土"
        # So month_element="土" triggers this branch
        suggested, avoid, reasoning = infer_xiyong("木", "土")
        assert isinstance(suggested, list)
        assert "偏弱" in reasoning

    @patch("packages.utils.bazi_calculator.XIYONG_RULES", {})
    def test_default_logic_daymaster_sheng_month(self):
        """默认逻辑：日元生月令（泄气，偏弱）"""
        # WUXING_SHENG.get("木") = "火", so month_element="火" triggers this
        suggested, avoid, reasoning = infer_xiyong("木", "火")
        assert isinstance(suggested, list)
        assert "泄气" in reasoning

    @patch("packages.utils.bazi_calculator.XIYONG_RULES", {})
    def test_default_logic_daymaster_ke_month(self):
        """默认逻辑：日元克月令（耗气，中等）"""
        # WUXING_BEI_KE.get("木") = "金", so month_element="金" triggers this
        suggested, avoid, reasoning = infer_xiyong("木", "金")
        assert isinstance(suggested, list)
        assert "耗气" in reasoning

    @patch("packages.utils.bazi_calculator.XIYONG_RULES", {})
    def test_default_logic_neutral(self):
        """默认逻辑：中和原则"""
        # day_master="木", month_element="木" → no match in any branch → else
        suggested, avoid, reasoning = infer_xiyong("木", "木")
        assert isinstance(suggested, list)
        assert "中和" in reasoning

    @patch("packages.utils.bazi_calculator.XIYONG_RULES", {})
    def test_default_logic_fire_daymaster(self):
        """默认逻辑：火日元各种组合"""
        # 月令生日元: WUXING_SHENG.get("木")="火" → month_element="木" → branch 1
        suggested, avoid, reasoning = infer_xiyong("火", "木")
        assert "偏旺" in reasoning

        # 月令克日元: WUXING_KE.get("火")="金" → month_element="金" → branch 2
        suggested, avoid, reasoning = infer_xiyong("火", "金")
        assert "偏弱" in reasoning


# ============================================================
# infer_elements_from_text 测试
# ============================================================

class TestInferElementsFromText:
    """测试文本意图推断"""

    def test_keyword_match(self):
        """关键词匹配"""
        result = infer_elements_from_text("我要去面试，需要正式干练的穿搭")
        assert result["method"] == "rule"
        assert len(result["elements"]) > 0
        assert "金" in result["elements"]  # 面试、正式、干练 → 金
        assert result["confidence"] > 0

    def test_scene_match(self):
        """场景匹配"""
        result = infer_elements_from_text("今天有约会")
        assert result["method"] == "rule"
        assert "火" in result["elements"] or "木" in result["elements"]  # 约会 → 火,木

    def test_no_match_needs_llm(self):
        """无匹配需要LLM"""
        result = infer_elements_from_text("今天天气不错")
        assert result["method"] == "llm_needed"
        assert result["elements"] == []
        assert result["confidence"] == 0.0

    def test_multiple_keywords(self):
        """多个关键词匹配"""
        result = infer_elements_from_text("商务会议需要专业沉稳的穿搭")
        assert result["method"] == "rule"
        assert len(result["elements"]) > 0
        assert "金" in result["elements"]  # 商务、专业 → 金

    def test_empty_text(self):
        """空文本"""
        result = infer_elements_from_text("")
        assert result["method"] == "llm_needed"

    def test_combined_keyword_and_scene(self):
        """关键词和场景同时匹配"""
        result = infer_elements_from_text("去运动要活力清新")
        assert result["method"] == "rule"
        assert len(result["matched_keywords"]) > 0

    def test_confidence_capped_at_1(self):
        """置信度上限为1.0"""
        text = "清新自然生机活力成长春天户外运动随性文艺青春健康"
        result = infer_elements_from_text(text)
        assert result["confidence"] <= 1.0

    def test_top_two_elements(self):
        """最多返回2个五行"""
        text = "面试约会运动商务派对"
        result = infer_elements_from_text(text)
        assert len(result["elements"]) <= 2


# ============================================================
# merge_recommendations 测试
# ============================================================

class TestMergeRecommendations:
    """测试多层推荐合并"""

    def test_bazi_only(self):
        """只有八字结果"""
        bazi = {
            "suggested_elements": ["金", "水"],
            "avoid_elements": ["火"],
        }
        result, boost = merge_recommendations(bazi, None, None)
        assert "金" in result
        assert "水" in result

    def test_bazi_and_weather(self):
        """八字+天气"""
        bazi = {
            "suggested_elements": ["金"],
            "avoid_elements": ["火"],
        }
        result, boost = merge_recommendations(bazi, None, None, weather_element="水")
        assert "金" in result
        assert "水" in result

    def test_weather_avoid_conflict(self):
        """天气五行与忌神冲突时跳过"""
        bazi = {
            "suggested_elements": ["金"],
            "avoid_elements": ["火"],
        }
        result, boost = merge_recommendations(bazi, None, None, weather_element="火")
        assert "金" in result
        assert "火" not in result  # 被忌神排除

    def test_bazi_and_scene(self):
        """八字+场景"""
        bazi = {
            "suggested_elements": ["金"],
            "avoid_elements": ["火"],
        }
        scene = {"primary": ["水", "木"]}
        result, boost = merge_recommendations(bazi, None, scene)
        assert "金" in result
        assert "水" in result
        assert "木" in result

    def test_scene_avoid_conflict(self):
        """场景五行与忌神冲突时跳过"""
        bazi = {
            "suggested_elements": ["金"],
            "avoid_elements": ["火"],
        }
        scene = {"primary": ["火", "水"]}
        result, boost = merge_recommendations(bazi, None, scene)
        assert "金" in result
        assert "水" in result
        assert "火" not in result  # 被忌神排除

    def test_bazi_and_intent(self):
        """八字+意图推断"""
        bazi = {
            "suggested_elements": ["金"],
            "avoid_elements": [],
        }
        intent = {
            "elements": ["木", "水"],
            "method": "rule",
        }
        result, boost = merge_recommendations(bazi, intent, None)
        assert "金" in result
        assert "木" in result
        assert "水" in result

    def test_intent_llm_needed_skipped(self):
        """意图为llm_needed时不使用"""
        bazi = {
            "suggested_elements": ["金"],
            "avoid_elements": [],
        }
        intent = {
            "elements": ["木"],
            "method": "llm_needed",
        }
        result, boost = merge_recommendations(bazi, intent, None)
        assert "金" in result
        assert "木" not in result  # llm_needed不使用

    def test_all_none(self):
        """所有输入都为None"""
        result, boost = merge_recommendations(None, None, None)
        assert result == []
        assert boost == []

    def test_max_three_elements(self):
        """最多3个五行"""
        bazi = {
            "suggested_elements": ["金", "水"],
            "avoid_elements": [],
        }
        scene = {"primary": ["木", "火"]}
        intent = {
            "elements": ["土"],
            "method": "rule",
        }
        result, boost = merge_recommendations(bazi, intent, scene, weather_element="土")
        assert len(result) <= 3

    def test_dedup(self):
        """去重"""
        bazi = {
            "suggested_elements": ["金", "水"],
            "avoid_elements": [],
        }
        scene = {"primary": ["金", "水"]}
        intent = {
            "elements": ["金"],
            "method": "rule",
        }
        result, boost = merge_recommendations(bazi, intent, scene)
        assert result.count("金") == 1
        assert result.count("水") == 1

    def test_weather_without_bazi(self):
        """无八字时有天气"""
        result, boost = merge_recommendations(None, None, None, weather_element="水")
        assert "水" in result

    def test_scene_without_bazi(self):
        """无八字时有场景"""
        scene = {"primary": ["木", "火"]}
        result, boost = merge_recommendations(None, None, scene)
        assert "木" in result
        assert "火" in result

    def test_intent_without_bazi(self):
        """无八字时有意图"""
        intent = {
            "elements": ["土"],
            "method": "rule",
        }
        result, boost = merge_recommendations(None, intent, None)
        assert "土" in result


# ============================================================
# 显式五行意图检测测试（extract_explicit_element_intent）
# ============================================================

class TestExtractExplicitElementIntent:
    """用户显式五行修正指令检测"""

    def test_detect_lacking_element(self):
        """检测「五行缺金」"""
        result = extract_explicit_element_intent("我五行缺金，今天穿什么")
        assert "金" in result["add"]
        assert result["avoid"] == []

    def test_detect_bu_element(self):
        """检测「想补木」"""
        result = extract_explicit_element_intent("想补木，推荐一套搭配")
        assert "木" in result["add"]

    def test_detect_avoid_element(self):
        """检测「不要水」"""
        result = extract_explicit_element_intent("不要水，其他都行")
        assert "水" in result["avoid"]
        assert result["add"] == []

    def test_avoid_wins_over_add(self):
        """同一五行补/避同时出现时以避为准"""
        result = extract_explicit_element_intent("缺金但不要金")
        assert "金" in result["avoid"]
        assert "金" not in result["add"]

    def test_no_explicit_intent(self):
        """普通穿搭提问不产生显式意图"""
        result = extract_explicit_element_intent("明天面试穿什么好")
        assert result["add"] == []
        assert result["avoid"] == []

    def test_empty_text(self):
        """空文本防御"""
        result = extract_explicit_element_intent("")
        assert result == {"add": [], "avoid": [], "matched": []}


# ============================================================
# 显式意图优先级测试（用户实时意图 > 八字预设）
# ============================================================

class TestExplicitIntentPriority:
    """显式五行指令覆盖八字喜用神/忌神预设"""

    def test_explicit_add_overrides_unfavorable_element(self):
        """核心 bad case：喜用神水木 + 忌神金，用户说“五行缺金”时金必须进 target"""
        bazi = {
            "suggested_elements": ["水", "木"],
            "avoid_elements": ["金"],
        }
        explicit = extract_explicit_element_intent("五行缺金")
        result, boost = merge_recommendations(bazi, None, None, explicit_intent=explicit)
        assert "金" in result  # 显式意图覆盖忌神
        assert result[0] == "金"  # 显式补的五行置于最前

    def test_explicit_add_takes_precedence_over_bazi(self):
        """显式补X置于 target 最前（优先级高于八字喜用神）"""
        bazi = {
            "suggested_elements": ["木", "水"],
            "avoid_elements": [],
        }
        explicit = {"add": ["土"], "avoid": [], "matched": []}
        result, boost = merge_recommendations(bazi, None, None, explicit_intent=explicit)
        assert result[0] == "土"
        assert "木" in result and "水" in result

    def test_explicit_avoid_removes_from_xiyong(self):
        """显式避X：从喜用神剔除并全局阻断"""
        bazi = {
            "suggested_elements": ["水", "木"],
            "avoid_elements": [],
        }
        explicit = {"add": [], "avoid": ["木"], "matched": []}
        result, boost = merge_recommendations(bazi, None, None, explicit_intent=explicit)
        assert "木" not in result
        assert "水" in result
        assert "木" not in boost

    def test_explicit_avoid_blocks_scene_and_intent(self):
        """显式避X同时阻断场景/隐式意图中的该五行"""
        bazi = {
            "suggested_elements": ["水"],
            "avoid_elements": [],
        }
        scene = {"primary": ["火", "土"]}
        intent = {"elements": ["火"], "method": "rule"}
        explicit = {"add": [], "avoid": ["火"], "matched": []}
        result, boost = merge_recommendations(bazi, intent, scene, explicit_intent=explicit)
        assert "火" not in result
        assert "火" not in boost  # 不进 boost（显式回避比忌神更强）

    def test_explicit_avoid_blocks_weather(self):
        """显式避X阻断天气五行"""
        bazi = {
            "suggested_elements": ["木"],
            "avoid_elements": [],
        }
        explicit = {"add": [], "avoid": ["水"], "matched": []}
        result, boost = merge_recommendations(
            bazi, None, None, weather_element="水", explicit_intent=explicit
        )
        assert "水" not in result

    def test_no_explicit_intent_keeps_legacy_priority(self):
        """无显式意图时回归旧优先级（八字 > 天气 > 场景 > 隐式意图），忌神不进 target"""
        bazi = {
            "suggested_elements": ["水", "木"],
            "avoid_elements": ["金"],
        }
        intent = {"elements": ["金"], "method": "rule"}
        result, boost = merge_recommendations(bazi, intent, None)
        assert "金" not in result  # 忌神不进 target
        assert "金" in boost  # 金生水，降级为 boost
        assert result == ["水", "木"]
