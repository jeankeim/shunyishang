"""
AI Skill 框架：LLM 能力的统一注册表与执行器

用法：
    from packages.ai_skills import run_skill

    try:
        result, usage = run_skill("fortune_narrative", context)
    except SkillError:
        result = 降级方案(...)

导入本包即完成内置技能注册（definitions.py）。
"""

from packages.ai_skills.base import (
    AssertionFn,
    SkillAssertionError,
    SkillError,
    SkillSpec,
    SkillRegistry,
    skill_registry,
)
from packages.ai_skills.executor import (
    clean_llm_json,
    render_prompt,
    run_skill,
    set_client_factory,
)

# 触发内置技能注册（幂等：重复 import 不会重复注册）
import packages.ai_skills.definitions  # noqa: F401,E402

__all__ = [
    "AssertionFn",
    "SkillAssertionError",
    "SkillError",
    "SkillSpec",
    "SkillRegistry",
    "skill_registry",
    "clean_llm_json",
    "render_prompt",
    "run_skill",
    "set_client_factory",
]
