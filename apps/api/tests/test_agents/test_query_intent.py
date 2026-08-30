"""
LLM 意图理解层测试

测试 query_intent.py 模块：
- 枚举校验层（防止 LLM 幻觉）
- 规则提取（备用路径）
- 缓存机制
- 主入口 understand_query
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from packages.recommendation.query_intent import (
    QueryIntent,
    _validate_enum,
    _validate_enum_list,
    _validate_intent,
    _extract_intent_by_rules,
    _get_cached_intent,
    _set_cached_intent,
    _intent_cache,
    _cache_timestamps,
    understand_query,
    WUXING_ENUM,
    CATEGORY_ENUM,
    SCENE_ENUM,
    COLOR_VOCAB,
)


class TestValidateEnum:
    """测试枚举校验函数"""

    def test_valid_enum_exact_match(self):
        """精确匹配"""
        assert _validate_enum("木", WUXING_ENUM) == "木"
        assert _validate_enum("上装", CATEGORY_ENUM) == "上装"

    def test_invalid_enum_returns_none(self):
        """非法值返回 None"""
        assert _validate_enum("_invalid_element", WUXING_ENUM) is None
        assert _validate_enum("不存在品类", CATEGORY_ENUM) is None

    def test_empty_value_returns_none(self):
        """空值返回 None"""
        assert _validate_enum(None, WUXING_ENUM) is None
        assert _validate_enum("", WUXING_ENUM) is None

    def test_fuzzy_match_subset(self):
        """模糊匹配：值包含在枚举项中"""
        # "裙" 是 "裙装" 的子串
        assert _validate_enum("裙", CATEGORY_ENUM) == "裙装"

    def test_fuzzy_match_superset(self):
        """模糊匹配：枚举项包含在值中"""
        # "上装外套" 包含 "上装"
        assert _validate_enum("上装外套", CATEGORY_ENUM) == "上装"


class TestValidateEnumList:
    """测试列表枚举校验函数"""

    def test_valid_list(self):
        """合法列表"""
        result = _validate_enum_list(["木", "火"], WUXING_ENUM)
        assert result == ["木", "火"]

    def test_mixed_valid_invalid(self):
        """混合合法与非法值"""
        result = _validate_enum_list(["木", "invalid", "火"], WUXING_ENUM)
        assert result == ["木", "火"]

    def test_deduplication(self):
        """去重"""
        result = _validate_enum_list(["木", "木", "火"], WUXING_ENUM)
        assert result == ["木", "火"]

    def test_empty_list(self):
        """空列表"""
        assert _validate_enum_list([], WUXING_ENUM) == []
        assert _validate_enum_list(None, WUXING_ENUM) == []


class TestValidateIntent:
    """测试意图校验"""

    def test_validate_categories(self):
        """品类校验"""
        intent = QueryIntent(categories=["上装", "invalid_category", "裙装"])
        validated = _validate_intent(intent)
        assert validated.categories == ["上装", "裙装"]

    def test_validate_elements(self):
        """五行校验"""
        intent = QueryIntent(elements_add=["木", "invalid"], elements_avoid=["火"])
        validated = _validate_intent(intent)
        assert validated.elements_add == ["木"]
        assert validated.elements_avoid == ["火"]

    def test_validate_scene(self):
        """场景校验"""
        intent = QueryIntent(scene="面试")
        validated = _validate_intent(intent)
        assert validated.scene == "面试"

        intent_invalid = QueryIntent(scene="不存在的场景")
        validated_invalid = _validate_intent(intent_invalid)
        assert validated_invalid.scene is None


class TestCache:
    """测试缓存机制"""

    def setup_method(self):
        """每个测试前清空缓存"""
        _intent_cache.clear()
        _cache_timestamps.clear()

    def test_cache_miss(self):
        """缓存未命中"""
        result = _get_cached_intent("新查询")
        assert result is None

    def test_cache_set_and_get(self):
        """设置并获取缓存"""
        intent = QueryIntent(is_fashion=True, confidence=0.9, categories=["上装"])
        _set_cached_intent("测试查询", intent)
        
        cached = _get_cached_intent("测试查询")
        assert cached is not None
        assert cached.categories == ["上装"]

    def test_cache_ttl_expiry(self):
        """缓存过期"""
        intent = QueryIntent(is_fashion=True)
        _set_cached_intent("过期测试", intent)
        
        # 手动修改时间戳模拟过期
        import hashlib
        cache_key = hashlib.md5("过期测试".encode()).hexdigest()
        _cache_timestamps[cache_key] = time.time() - 3700  # 超过 3600 秒
        
        cached = _get_cached_intent("过期测试")
        assert cached is None


class TestExtractIntentByRules:
    """测试规则提取（备用路径）"""

    def test_extract_wuxing_intent(self):
        """提取五行意图"""
        intent = _extract_intent_by_rules("我缺木")
        assert "木" in intent.elements_add

    def test_extract_explicit_avoid(self):
        """提取显式回避"""
        intent = _extract_intent_by_rules("忌火")
        assert "火" in intent.elements_avoid

    def test_extract_scene(self):
        """提取场景"""
        intent = _extract_intent_by_rules("下周去面试")
        assert intent.scene == "面试"

    def test_extract_anchor(self):
        """提取锚点单品"""
        intent = _extract_intent_by_rules("我有白色裤子，帮我搭配")
        assert "白色裤子" in intent.anchor_phrases

    def test_confidence_is_lower(self):
        """规则提取置信度较低"""
        intent = _extract_intent_by_rules("推荐一件上装")
        assert intent.confidence == 0.6


class TestUnderstandQuery:
    """测试主入口"""

    def setup_method(self):
        """每个测试前清空缓存"""
        _intent_cache.clear()
        _cache_timestamps.clear()

    def test_empty_input(self):
        """空输入返回非穿搭意图"""
        result = understand_query("")
        assert result.is_fashion is False
        assert result.confidence == 0.0

    def test_whitespace_input(self):
        """空白输入返回非穿搭意图"""
        result = understand_query("   ")
        assert result.is_fashion is False

    @patch("packages.recommendation.query_intent._call_intent_llm")
    def test_llm_success(self, mock_llm):
        """LLM 成功时返回 LLM 结果"""
        mock_intent = QueryIntent(
            is_fashion=True,
            confidence=0.95,
            categories=["上装"],
            elements_add=["木"],
        )
        mock_llm.return_value = mock_intent
        
        result = understand_query("推荐一件木属性的上装")
        
        assert result.is_fashion is True
        assert result.categories == ["上装"]
        assert result.elements_add == ["木"]
        assert result.confidence == 0.95

    @patch("packages.recommendation.query_intent._call_intent_llm")
    def test_llm_failure_fallback_to_rules(self, mock_llm):
        """LLM 失败时回退到规则"""
        mock_llm.return_value = None
        
        result = understand_query("我缺木")
        
        # 应该回退到规则提取
        assert "木" in result.elements_add
        assert result.confidence == 0.6  # 规则提取的置信度

    @patch("packages.recommendation.query_intent._call_intent_llm")
    def test_caching_works(self, mock_llm):
        """缓存生效"""
        mock_intent = QueryIntent(is_fashion=True, confidence=0.9)
        mock_llm.return_value = mock_intent
        
        # 第一次调用
        result1 = understand_query("缓存测试查询")
        assert mock_llm.call_count == 1
        
        # 第二次调用应该命中缓存
        result2 = understand_query("缓存测试查询")
        assert mock_llm.call_count == 1  # 不应该再次调用 LLM
        assert result2.confidence == 0.9


class TestQueryIntentDataclass:
    """测试 QueryIntent 数据结构"""

    def test_default_values(self):
        """默认值"""
        intent = QueryIntent()
        assert intent.is_fashion is True
        assert intent.confidence == 0.0
        assert intent.elements_add == []
        assert intent.categories == []
        assert intent.scene is None

    def test_custom_values(self):
        """自定义值"""
        intent = QueryIntent(
            is_fashion=True,
            confidence=0.8,
            elements_add=["木", "火"],
            categories=["上装", "下装"],
            scene="面试",
        )
        assert intent.elements_add == ["木", "火"]
        assert intent.categories == ["上装", "下装"]
        assert intent.scene == "面试"


class TestCategoryConstraintIntegration:
    """测试品类约束集成场景"""

    def setup_method(self):
        _intent_cache.clear()
        _cache_timestamps.clear()

    @patch("packages.recommendation.query_intent._call_intent_llm")
    def test_category_constraint_extracted(self, mock_llm):
        """品类约束被正确提取"""
        mock_intent = QueryIntent(
            is_fashion=True,
            confidence=0.9,
            categories=["上装"],
        )
        mock_llm.return_value = mock_intent
        
        result = understand_query("推荐一件木属性的上装")
        
        assert result.categories == ["上装"]

    @patch("packages.recommendation.query_intent._call_intent_llm")
    def test_multiple_categories(self, mock_llm):
        """多品类约束"""
        mock_intent = QueryIntent(
            is_fashion=True,
            confidence=0.9,
            categories=["上装", "下装"],
        )
        mock_llm.return_value = mock_intent
        
        result = understand_query("推荐上装和下装")
        
        assert "上装" in result.categories
        assert "下装" in result.categories

    @patch("packages.recommendation.query_intent._call_intent_llm")
    def test_no_category_constraint(self, mock_llm):
        """无品类约束时 categories 为空"""
        mock_intent = QueryIntent(
            is_fashion=True,
            confidence=0.9,
            categories=[],
        )
        mock_llm.return_value = mock_intent
        
        result = understand_query("今天穿什么")
        
        assert result.categories == []
