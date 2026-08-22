"""
AI Skill 框架单测

覆盖：
- 注册表：注册/重复注册/未注册查询/列表
- prompt 渲染：占位符替换 / 缺占位符抛错 / 字面花括号转义
- JSON 清洗：markdown 代码块剥离
- 执行器（mock client）：成功路径 / 非法 JSON / 缺键 / 空内容 / LLM 异常 / 断言红线
- fortune_engine 接线：_generate_ai_narrative 走技能后行为不变（返回 narrative+usage）
"""

import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from packages.ai_skills import (
    SkillAssertionError,
    SkillError,
    SkillSpec,
    clean_llm_json,
    render_prompt,
    run_skill,
    set_client_factory,
    skill_registry,
)
from packages.ai_skills.definitions import (
    FORTUNE_NARRATIVE_OUTPUT_KEYS,
    _assert_no_deterministic_fortune,
)


# ---------- 测试辅助 ----------

def _fake_response(content, model="qwen-plus", with_usage=True):
    """构造 chat.completions.create 兼容的假响应"""
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model=model,
    )
    resp.usage = (
        SimpleNamespace(prompt_tokens=100, completion_tokens=50) if with_usage else None
    )
    return resp


def _mock_client(content=None, raise_exc=None):
    client = MagicMock()
    if raise_exc:
        client.chat.completions.create.side_effect = raise_exc
    else:
        client.chat.completions.create.return_value = _fake_response(content)
    return client


@pytest.fixture(autouse=True)
def _reset_client_factory():
    yield
    set_client_factory(None)


# ---------- 注册表 ----------

class TestRegistry:
    def test_builtin_fortune_narrative_registered(self):
        spec = skill_registry.get("fortune_narrative")
        assert spec.output_keys == FORTUNE_NARRATIVE_OUTPUT_KEYS
        assert "{day_master}" in spec.prompt_template

    def test_unknown_skill_raises(self):
        with pytest.raises(KeyError):
            skill_registry.get("not_exist_skill")

    def test_duplicate_register_raises(self):
        spec = SkillSpec(name="_dup_test_skill")
        skill_registry.register(spec)
        try:
            with pytest.raises(ValueError):
                skill_registry.register(SkillSpec(name="_dup_test_skill"))
        finally:
            skill_registry._skills.pop("_dup_test_skill", None)

    def test_list_includes_builtin(self):
        names = [s.name for s in skill_registry.list()]
        assert "fortune_narrative" in names


# ---------- prompt 渲染与 JSON 清洗 ----------

class TestRenderAndClean:
    def test_render_substitutes_placeholders(self):
        spec = SkillSpec(name="t", prompt_template="日主：{day_master}，忌：{{字面括号}}")
        assert render_prompt(spec, {"day_master": "木"}) == "日主：木，忌：{字面括号}"

    def test_render_missing_placeholder_raises(self):
        spec = SkillSpec(name="t", prompt_template="缺 {missing_key}")
        with pytest.raises(SkillError):
            render_prompt(spec, {})

    def test_clean_strips_markdown_fences(self):
        assert clean_llm_json('```json\n{"a": 1}\n```') == '{"a": 1}'
        assert clean_llm_json('  {"a": 1}  ') == '{"a": 1}'

    def test_fortune_template_renders_full_context(self):
        """运势技能模板在完整上下文下可渲染，且神煞段落按需出现"""
        spec = skill_registry.get("fortune_narrative")
        ctx = {
            "day_master": "木", "suggested_text": "水", "avoid_text": "土",
            "pillars_json": "{}", "shen_sha_section": "\n## 命带神煞\n- 华盖\n",
            "day_tiangan": "甲", "day_element": "木", "day_dizhi": "子",
            "relation_cn": "比和", "career_score": 80, "wealth_score": 70,
            "love_score": 60, "health_score": 75, "study_score": 65,
            "overall": 70, "best_dim_text": "事业（80分）", "worst_dim_text": "感情（60分）",
            "yi_text": "出行", "ji_text": "动土", "chong_sha": "冲马", "solar_context": "",
        }
        prompt = render_prompt(spec, ctx)
        assert "命带神煞" in prompt and "华盖" in prompt
        # JSON 示例的字面花括号正确转义为单层
        assert '"overview": "今日格局概述' in prompt


# ---------- 执行器 ----------

class TestRunSkill:
    def _spec(self, **kw):
        defaults = dict(
            name="t_exec", prompt_template="hi {x}",
            output_keys=["a"], assertions=[],
        )
        defaults.update(kw)
        return SkillSpec(**defaults)

    def test_success_returns_result_and_usage(self):
        set_client_factory(lambda timeout: _mock_client('{"a": "1"}'))
        result, usage = run_skill(self._spec(), {"x": "1"})
        assert result == {"a": "1"}
        assert usage == {"model": "qwen-plus", "input_tokens": 100, "output_tokens": 50}

    def test_markdown_wrapped_json_ok(self):
        set_client_factory(lambda timeout: _mock_client('```json\n{"a": "1"}\n```'))
        result, _ = run_skill(self._spec(), {"x": "1"})
        assert result == {"a": "1"}

    def test_invalid_json_raises_skill_error(self):
        set_client_factory(lambda timeout: _mock_client("not json"))
        with pytest.raises(SkillError):
            run_skill(self._spec(), {"x": "1"})

    def test_missing_output_key_raises(self):
        set_client_factory(lambda timeout: _mock_client('{"b": "1"}'))
        with pytest.raises(SkillError):
            run_skill(self._spec(), {"x": "1"})

    def test_empty_value_key_raises(self):
        set_client_factory(lambda timeout: _mock_client('{"a": "  "}'))
        with pytest.raises(SkillError):
            run_skill(self._spec(), {"x": "1"})

    def test_empty_content_raises(self):
        set_client_factory(lambda timeout: _mock_client(""))
        with pytest.raises(SkillError):
            run_skill(self._spec(), {"x": "1"})

    def test_llm_exception_wrapped_as_skill_error(self):
        set_client_factory(lambda timeout: _mock_client(raise_exc=TimeoutError("boom")))
        with pytest.raises(SkillError):
            run_skill(self._spec(), {"x": "1"})

    def test_assertion_failure_raises(self):
        def bad(result, context):
            raise SkillAssertionError("红线")

        set_client_factory(lambda timeout: _mock_client('{"a": "1"}'))
        with pytest.raises(SkillAssertionError):
            run_skill(self._spec(assertions=[bad]), {"x": "1"})


# ---------- 运势叙事红线断言 ----------

class TestFortuneAssertions:
    def _ok_result(self, **overrides):
        base = {k: "平稳向好" for k in FORTUNE_NARRATIVE_OUTPUT_KEYS}
        base.update(overrides)
        return base

    def test_clean_text_passes(self):
        _assert_no_deterministic_fortune(self._ok_result(), {})

    def test_deterministic_word_fails(self):
        with pytest.raises(SkillAssertionError):
            _assert_no_deterministic_fortune(self._ok_result(overview="今日必将大涨"), {})


# ---------- fortune_engine 接线（行为不变性） ----------

class TestFortuneEngineWiring:
    def test_generate_ai_narrative_returns_narrative_and_usage(self):
        from apps.api.services import fortune_engine

        payload = {k: f"{k}文案" for k in FORTUNE_NARRATIVE_OUTPUT_KEYS}
        set_client_factory(lambda timeout: _mock_client(json.dumps(payload, ensure_ascii=False)))

        user_bazi = {
            "day_master": "木",
            "suggested_elements": ["水"],
            "avoid_elements": ["土"],
            "pillars": {"year": "乙丑", "month": "庚辰", "day": "乙未", "hour": "癸未"},
            "eight_chars": list("乙丑庚辰乙未癸未"),
        }
        scores = {"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 65}
        huangli = {"yi": ["出行"], "ji": ["动土"], "chong_sha": "冲马"}

        narrative, usage = fortune_engine._generate_ai_narrative(
            user_bazi=user_bazi,
            target_date=date(2026, 8, 22),
            scores=scores,
            overall=70,
            huangli=huangli,
        )
        assert narrative == payload
        assert usage["input_tokens"] == 100

    def test_generate_ai_narrative_failure_raises_for_fallback(self):
        """LLM 失败时抛出异常（由调用方降级到公式叙事，行为与迁移前一致）"""
        from apps.api.services import fortune_engine

        set_client_factory(lambda timeout: _mock_client(raise_exc=TimeoutError("boom")))
        with pytest.raises(SkillError):
            fortune_engine._generate_ai_narrative(
                user_bazi={"day_master": "木"},
                target_date=date(2026, 8, 22),
                scores={"career": 80, "wealth": 70, "love": 60, "health": 75, "study": 65},
                overall=70,
                huangli={},
            )
