"""
Skill 框架基座：技能定义（SkillSpec）与统一注册表

Skill = 触发条件 + 上下文 schema + prompt 模板 + 输出 schema + 验收断言 的结构化能力包。
目标：收编散落在各业务模块的 LLM 调用，统一 prompt 管理、输出校验、降级入口与用量核算。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillError(Exception):
    """技能执行失败（LLM 异常 / JSON 解析失败 / 输出缺键），调用方应走降级链"""


class SkillAssertionError(SkillError):
    """验收断言不通过（如输出触碰合规红线），同样走降级链"""


# 验收断言签名：(result, context) -> None，不通过时抛 SkillAssertionError
AssertionFn = Callable[[Dict[str, Any], Dict[str, Any]], None]


@dataclass
class SkillSpec:
    """
    单个 AI 技能的完整定义

    Attributes:
        name: 技能唯一标识（如 fortune_narrative），同时作为用量记账 scene
        description: 技能说明（注册表展示/文档用）
        prompt_template: str.format 风格 prompt 模板，占位符由 context 提供；
                         字面花括号需写成 {{ }}
        output_keys: 输出 JSON 必须包含的键（缺失即视为失败走降级）
        assertions: 验收断言列表，解析成功后依次执行
        model: 模型名，None 表示使用 settings.qwen_model 默认值
        temperature / max_tokens / timeout: 调用参数
    """

    name: str
    description: str = ""
    prompt_template: str = ""
    output_keys: List[str] = field(default_factory=list)
    assertions: List[AssertionFn] = field(default_factory=list)
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 800
    timeout: int = 20


class SkillRegistry:
    """技能注册表：全局唯一，register/get/list 三件套"""

    def __init__(self) -> None:
        self._skills: Dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> SkillSpec:
        if spec.name in self._skills:
            raise ValueError(f"[SkillRegistry] 技能重复注册: {spec.name}")
        self._skills[spec.name] = spec
        logger.info(f"[SkillRegistry] 已注册技能: {spec.name}")
        return spec

    def get(self, name: str) -> SkillSpec:
        spec = self._skills.get(name)
        if spec is None:
            raise KeyError(f"[SkillRegistry] 未注册的技能: {name}")
        return spec

    def list(self) -> List[SkillSpec]:
        return list(self._skills.values())


# 全局注册表单例
skill_registry = SkillRegistry()
