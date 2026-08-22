"""
Skill 统一执行器：渲染 prompt → 调用 LLM → 解析校验 → 返回 (result, usage)

所有技能走同一执行路径，保证：
- prompt 模板集中管理（SkillSpec.prompt_template）
- LLM 调用走 tenacity 指数退避重试（对齐项目约定：禁止裸调外部 LLM）
- 输出 JSON 统一清洗（markdown 代码块）与必备键校验
- 验收断言统一执行（不通过抛 SkillAssertionError → 调用方降级）
- token 用量统一提取（extract_llm_usage），scene = 技能名
失败一律抛 SkillError 系异常，由调用方决定降级策略（不在框架内静默吞错）。
"""

import json
import logging
from typing import Any, Callable, Dict, Optional, Tuple, Union

from openai import OpenAI
from tenacity import retry as tenacity_retry

from apps.api.core.config import settings
from apps.api.core.retry import get_llm_retry_config
from apps.api.services.llm_usage_service import extract_llm_usage

from packages.ai_skills.base import (
    SkillAssertionError,
    SkillError,
    SkillSpec,
    skill_registry,
)

logger = logging.getLogger(__name__)

# 客户端工厂可被测试 monkeypatch（返回 chat.completions.create 兼容对象）
_client_factory: Optional[Callable[[int], OpenAI]] = None


def set_client_factory(factory: Optional[Callable[[int], OpenAI]]) -> None:
    """注入自定义客户端工厂（测试用；传 None 恢复默认）"""
    global _client_factory
    _client_factory = factory


def _build_client(timeout: int) -> OpenAI:
    if _client_factory is not None:
        return _client_factory(timeout)
    return OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        timeout=timeout,  # 限制 LLM 调用耗时，避免后台增强线程长时间挂起
    )


def render_prompt(spec: SkillSpec, context: Dict[str, Any]) -> str:
    """渲染 prompt 模板；context 缺占位符视为技能实现错误，直接抛出"""
    try:
        return spec.prompt_template.format(**context)
    except KeyError as e:
        raise SkillError(f"技能 {spec.name} 上下文缺少占位符: {e}") from e


def clean_llm_json(content: str) -> str:
    """剥离模型可能附加的 markdown 代码块标记"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
    return content.strip()


def _invoke_llm(spec: SkillSpec, prompt: str):
    """单次 LLM 调用（供带重试的包装函数使用，独立拆出便于测试 mock）"""
    client = _build_client(spec.timeout)
    return client.chat.completions.create(
        model=spec.model or settings.qwen_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
    )


# 指数退避重试：超时/连接/限流类抖动自动重试，与 nodes.py 推荐链路同款策略
_invoke_llm_with_retry = tenacity_retry(**get_llm_retry_config(max_attempts=2, min_wait=1.0, max_wait=3.0))(_invoke_llm)


def run_skill(
    skill: Union[str, SkillSpec],
    context: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    执行一个技能

    Args:
        skill: 技能名（走注册表）或 SkillSpec 实例
        context: prompt 占位符上下文

    Returns:
        (result, usage)：解析校验后的 JSON 结果 + token 用量
        （usage 结构同 extract_llm_usage，调用方负责 log_llm_usage 记账）

    Raises:
        SkillError / SkillAssertionError：任何失败都抛出，由调用方降级
    """
    spec = skill_registry.get(skill) if isinstance(skill, str) else skill

    prompt = render_prompt(spec, context)

    try:
        response = _invoke_llm_with_retry(spec, prompt)
        content = response.choices[0].message.content
    except Exception as e:
        logger.error(f"[Skill:{spec.name}] LLM 调用异常（重试后仍失败）: {e}")
        raise SkillError(f"技能 {spec.name} LLM 调用失败: {e}") from e

    if not content:
        raise SkillError(f"技能 {spec.name} 返回空内容")

    try:
        result = json.loads(clean_llm_json(content))
    except (ValueError, TypeError) as e:
        logger.error(f"[Skill:{spec.name}] 输出 JSON 解析失败: {content[:200]}")
        raise SkillError(f"技能 {spec.name} 输出非法 JSON: {e}") from e

    if not isinstance(result, dict):
        raise SkillError(f"技能 {spec.name} 输出非 JSON 对象")

    missing = [k for k in spec.output_keys if not str(result.get(k) or "").strip()]
    if missing:
        raise SkillError(f"技能 {spec.name} 输出缺少必备键: {missing}")

    # 验收断言（红线校验，如喜用神不得被篡改、合规措辞等）
    for assertion in spec.assertions:
        assertion(result, context)

    return result, extract_llm_usage(response)
