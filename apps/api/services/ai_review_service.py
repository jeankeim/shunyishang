"""
AI 穿搭点评服务
基于八字五行分析穿搭匹配度，提供规则兜底
"""

import json
import logging
from typing import Dict, List, Any, Optional

from apps.api.core.config import settings
from packages.utils.wuxing_rules import (
    ELEMENT_COLOR_MAP,
    ELEMENT_MATERIAL_MAP,
    WUXING_SHENG,
    WUXING_KE,
)

logger = logging.getLogger(__name__)


def _get_element_score(item_element: str, user_suggested: List[str], user_avoid: List[str]) -> float:
    """计算单个衣物五行与用户的匹配分数"""
    if item_element in user_suggested:
        return 1.0
    if item_element in user_avoid:
        return 0.3
    # 相生关系
    for sug in user_suggested:
        if WUXING_SHENG.get(sug) == item_element or WUXING_SHENG.get(item_element) == sug:
            return 0.8
    return 0.5


def _rule_based_review(
    user_bazi: Dict[str, Any],
    outfit_items: List[Dict[str, Any]],
    weather: Optional[Dict],
    occasion: Optional[str],
) -> Dict[str, Any]:
    """基于规则的兜底点评"""
    suggested = user_bazi.get("suggested_elements", [])
    avoid = user_bazi.get("avoid_elements", [])
    day_master = user_bazi.get("day_master", "土")

    if not outfit_items:
        return {
            "score": 50,
            "comment": "今天没有记录穿搭哦，记得记录每日穿搭，让AI帮你分析五行搭配。",
            "suggestions": ["尝试添加今日穿搭"],
            "wuxing_analysis": {},
        }

    # 计算五行匹配度
    total_score = 0
    element_counts: Dict[str, int] = {}
    item_analyses = []

    for item in outfit_items:
        elem = item.get("primary_element", "")
        if elem:
            element_counts[elem] = element_counts.get(elem, 0) + 1
            item_score = _get_element_score(elem, suggested, avoid)
            total_score += item_score
            item_analyses.append({
                "name": item.get("name", "未知"),
                "element": elem,
                "match": "✓ 喜用" if elem in suggested else ("✗ 忌" if elem in avoid else "中"),
            })

    avg_score = total_score / len(outfit_items) if outfit_items else 0
    score = int(avg_score * 100)
    score = max(20, min(95, score))

    # 生成评语
    if score >= 80:
        comment = "今日穿搭与五行非常契合！"
    elif score >= 60:
        comment = "今日穿搭五行搭配不错。"
    else:
        comment = "今日穿搭五行匹配度较低，建议调整。"

    suggestions = []
    for elem in suggested:
        if elem not in element_counts:
            colors = ELEMENT_COLOR_MAP.get(elem, [])
            suggestions.append(f"可以尝试添加{elem}属性的单品（如{colors[0] if colors else ''}色系）")

    if avoid:
        for elem in avoid:
            if elem in element_counts:
                suggestions.append(f"今日穿搭中{elem}属性偏多，建议减少")

    return {
        "score": score,
        "comment": comment,
        "suggestions": suggestions[:3],
        "wuxing_analysis": {
            "element_distribution": element_counts,
            "day_master": day_master,
            "suggested_elements": suggested,
            "items": item_analyses,
        },
    }


def generate_ai_review(
    user_bazi: Dict[str, Any],
    outfit_items: List[Dict[str, Any]],
    weather: Optional[Dict] = None,
    occasion: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成AI穿搭点评

    优先使用 LLM 生成，失败时回退到规则兜底。
    """
    # 无穿搭单品时无需调用 LLM，直接返回友好的规则兜底文案
    if not outfit_items:
        return _rule_based_review(user_bazi, outfit_items, weather, occasion)
    try:
        return _llm_review(user_bazi, outfit_items, weather, occasion)
    except Exception as e:
        logger.warning(f"LLM 点评失败，使用规则兜底: {e}")
        return _rule_based_review(user_bazi, outfit_items, weather, occasion)


def _llm_review(
    user_bazi: Dict[str, Any],
    outfit_items: List[Dict[str, Any]],
    weather: Optional[Dict],
    occasion: Optional[str],
) -> Dict[str, Any]:
    """使用 LLM 生成穿搭点评"""
    from packages.ai_agents.nodes import get_llm_client, call_llm_with_retry

    client = get_llm_client(timeout=10)

    # 构建衣物描述
    items_desc = []
    for item in outfit_items:
        desc = f"- {item.get('name', '未知')}（五行: {item.get('primary_element', '未知')}"
        if item.get('category'):
            desc += f", 分类: {item['category']}"
        desc += "）"
        items_desc.append(desc)
    items_text = "\n".join(items_desc)

    day_master = user_bazi.get("day_master", "土")
    suggested = user_bazi.get("suggested_elements", [])
    avoid = user_bazi.get("avoid_elements", [])

    weather_text = ""
    if weather:
        weather_text = f"天气: {weather.get('weather_desc', '未知')}，温度: {weather.get('temperature', '未知')}°C"

    occasion_text = f"场合: {occasion}" if occasion else ""

    prompt = f"""你是一位精通中国传统五行文化的穿搭顾问。请根据以下信息点评今日穿搭：

用户信息：
- 日元五行: {day_master}
- 喜用神: {'、'.join(suggested)}
- 忌神: {'、'.join(avoid) if avoid else '无'}

今日穿搭：
{items_text}

{weather_text}
{occasion_text}

请用JSON格式返回点评结果：
{{"score": 0-100的整数, "comment": "50字以内点评", "suggestions": ["建议1","建议2"]}}

只返回JSON，不要其他内容。"""

    messages = [{"role": "user", "content": prompt}]

    response = call_llm_with_retry(
        client=client,
        messages=messages,
        model=settings.qwen_model,
        max_tokens=300,
    )

    content = response.choices[0].message.content.strip()
    # 尝试解析 JSON
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    result = json.loads(content)

    # 补充五行分析
    element_counts: Dict[str, int] = {}
    for item in outfit_items:
        elem = item.get("primary_element", "")
        if elem:
            element_counts[elem] = element_counts.get(elem, 0) + 1

    result["wuxing_analysis"] = {
        "element_distribution": element_counts,
        "day_master": day_master,
        "suggested_elements": suggested,
    }

    # 确保分数范围
    result["score"] = max(0, min(100, int(result.get("score", 50))))
    result.setdefault("suggestions", [])

    return result
