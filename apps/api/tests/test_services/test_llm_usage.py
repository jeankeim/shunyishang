"""
llm_usage_service 成本核算纯函数单测

覆盖：
- calc_llm_cost：按模型单价折算，无 tokens 为 0，未知模型兜底，带日期后缀模型前缀匹配
- extract_llm_usage：真实 usage 提取、无 usage / 非 int 字段返回 None（含 MagicMock 防护）
- merge_llm_usage：多次调用 tokens 累加、model 取首个非空
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from apps.api.services.llm_usage_service import (
    MODEL_PRICING_PER_1K,
    calc_llm_cost,
    extract_llm_usage,
    merge_llm_usage,
)


class TestCalcLlmCost:
    def test_qwen_plus_basic(self):
        # qwen-plus: 0.0008/千入 + 0.002/千出 → 1000+1000 = 0.0028
        assert calc_llm_cost("qwen-plus", 1000, 1000) == 0.0028

    def test_qwen_max_pricing(self):
        # qwen-max: 0.0024/千入 + 0.0096/千出 → 1000+1000 = 0.012
        assert calc_llm_cost("qwen-max", 1000, 1000) == 0.012

    def test_no_tokens_returns_zero(self):
        assert calc_llm_cost("qwen-plus", None, None) == 0.0
        assert calc_llm_cost("qwen-plus", 0, 0) == 0.0

    def test_unknown_model_fallback(self):
        # 未知模型按 qwen-plus 单价兜底
        assert calc_llm_cost("some-new-model", 1000, 1000) == calc_llm_cost("qwen-plus", 1000, 1000)

    def test_none_model_fallback(self):
        assert calc_llm_cost(None, 1000, 0) == 0.0008

    def test_model_with_date_suffix_prefix_match(self):
        # 带日期后缀的模型 ID 按前缀匹配单价
        assert calc_llm_cost("qwen-plus-2025-12-01", 1000, 1000) == 0.0028

    def test_pricing_table_completeness(self):
        # 关键模型单价必须存在
        for model in ("qwen-max", "qwen-plus", "qwen-turbo", "qwen-vl-max", "qwen-vl-plus"):
            assert model in MODEL_PRICING_PER_1K


class TestExtractLlmUsage:
    def _make_response(self, prompt, completion, model="qwen-plus"):
        usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion)
        return SimpleNamespace(usage=usage, model=model)

    def test_extract_from_normal_response(self):
        usage = extract_llm_usage(self._make_response(120, 45))
        assert usage == {"model": "qwen-plus", "input_tokens": 120, "output_tokens": 45}

    def test_no_usage_returns_none(self):
        assert extract_llm_usage(SimpleNamespace(model="qwen-plus")) is None

    def test_none_response_returns_none(self):
        assert extract_llm_usage(None) is None

    def test_non_int_tokens_returns_none(self):
        assert extract_llm_usage(self._make_response("120", 45)) is None
        assert extract_llm_usage(self._make_response(120, None)) is None

    def test_mockmagic_response_returns_none(self):
        # MagicMock 的属性是 MagicMock 而非 int，必须返回 None，避免误捕获测试桩
        assert extract_llm_usage(MagicMock()) is None

    def test_model_missing_ok(self):
        usage = extract_llm_usage(self._make_response(10, 20, model=None))
        assert usage["model"] is None
        assert usage["input_tokens"] == 10


class TestMergeLlmUsage:
    def test_merge_two_usages(self):
        a = {"model": "qwen-plus", "input_tokens": 100, "output_tokens": 20}
        b = {"model": "qwen-plus", "input_tokens": 50, "output_tokens": 10}
        merged = merge_llm_usage(a, b)
        assert merged["input_tokens"] == 150
        assert merged["output_tokens"] == 30
        assert merged["model"] == "qwen-plus"

    def test_merge_into_none(self):
        b = {"model": "qwen-plus", "input_tokens": 50, "output_tokens": 10}
        merged = merge_llm_usage(None, b)
        assert merged == b

    def test_merge_none_usage_keeps_prev(self):
        a = {"model": "qwen-plus", "input_tokens": 100, "output_tokens": 20}
        merged = merge_llm_usage(a, None)
        assert merged == a
        # 不原地修改 prev
        merged["input_tokens"] = 0
        assert a["input_tokens"] == 100

    def test_both_none(self):
        assert merge_llm_usage(None, None) is None

    def test_model_takes_first_non_empty(self):
        a = {"model": None, "input_tokens": 10, "output_tokens": 1}
        b = {"model": "qwen-vl-plus", "input_tokens": 20, "output_tokens": 2}
        merged = merge_llm_usage(a, b)
        assert merged["model"] == "qwen-vl-plus"
