"""
内置技能定义：集中注册所有 AI 技能

新增技能流程：
1. 在本文件定义 SkillSpec（prompt 模板 + 输出键 + 验收断言）
2. skill_registry.register(spec)
3. 业务侧 run_skill("技能名", context)，失败走各自降级链
"""

from typing import Any, Dict

from packages.ai_skills.base import SkillAssertionError, SkillSpec, skill_registry

# ============================================================
# 技能一：每日运势个性化叙事（原 fortune_engine._generate_ai_narrative 收编）
# ============================================================

FORTUNE_NARRATIVE_OUTPUT_KEYS = [
    "overview",
    "career_tip",
    "love_tip",
    "health_tip",
    "lucky_action",
    "avoid_action",
]

FORTUNE_NARRATIVE_PROMPT = """你是一位精通中国传统命理学的运势大师，请为用户生成今日运势的个性化叙事。

## 用户八字
- 日主：{day_master}
- 喜用神：{suggested_text}
- 忌讳五行：{avoid_text}
- 四柱：{pillars_json}
{shen_sha_section}
## 今日干支
- 天干：{day_tiangan}（五行属{day_element}）
- 地支：{day_dizhi}
- 日干对日主关系：{relation_cn}

## 五维度评分
- 事业：{career_score} | 财运：{wealth_score} | 桃花：{love_score}
- 健康：{health_score} | 学业：{study_score}
- 综合：{overall} 分
- 最强维度：{best_dim_text}
- 最弱维度：{worst_dim_text}

## 黄历信息
- 宜：{yi_text}
- 忌：{ji_text}
- 冲煞：{chong_sha}
{solar_context}

## 要求
请生成结构化 JSON，每段 50-80 字，温暖有共鸣，有具体可操作的建议。
如提供「命带神煞」信息，请在 overview 或任一提示中自然融入至少一条神煞提及（传统文化参考口吻，避免确定性断言）。

返回 JSON 格式：
{{
  "overview": "今日格局概述（结合五行生克关系）",
  "career_tip": "事业/学业提示",
  "love_tip": "感情/人际提示",
  "health_tip": "健康/情绪提示",
  "lucky_action": "今日最宜做的1件事",
  "avoid_action": "今日最应避免的1件事"
}}

直接返回 JSON，不要加 markdown 代码块标记。"""


def _assert_no_deterministic_fortune(result: Dict[str, Any], context: Dict[str, Any]) -> None:
    """合规红线：运势叙事不得出现确定性断言措辞"""
    banned = ("必将", "一定发", "肯定能", "注定")
    for key in FORTUNE_NARRATIVE_OUTPUT_KEYS:
        text = str(result.get(key) or "")
        for word in banned:
            if word in text:
                raise SkillAssertionError(
                    f"运势叙事触碰确定性断言红线（{key} 含「{word}」）"
                )


skill_registry.register(
    SkillSpec(
        name="fortune_narrative",
        description="每日运势个性化叙事（八字+黄历+神煞 → 六段式 JSON）",
        prompt_template=FORTUNE_NARRATIVE_PROMPT,
        output_keys=FORTUNE_NARRATIVE_OUTPUT_KEYS,
        assertions=[_assert_no_deterministic_fortune],
        temperature=0.7,
        max_tokens=800,
        timeout=20,
    )
)
