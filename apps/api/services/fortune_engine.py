"""
每日运势计算引擎
基于八字五行计算五维度运势和穿搭建议

v2 增强：
- 黄历数据（宜忌/冲煞/吉神凶煞/十二时辰吉凶）
- AI 个性化运势叙事（调用 LLM 生成）
- 节气感知
"""

import json
import logging
import random
from datetime import date, datetime
from typing import Dict, List, Optional, Any

import cnlunar

from openai import OpenAI

from apps.api.core.config import settings
from apps.api.services.llm_usage_service import extract_llm_usage

from packages.utils.wuxing_rules import (
    TIANGAN_WUXING,
    DIZHI_WUXING,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
    WUXING_BEI_KE,
    WUXING_LIST,
    ELEMENT_COLOR_MAP,
    ELEMENT_MATERIAL_MAP,
)

logger = logging.getLogger(__name__)

# 十二时辰名称
_SHICHEN_NAMES = [
    "子时(23-01)", "丑时(01-03)", "寅时(03-05)", "卯时(05-07)",
    "辰时(07-09)", "巳时(09-11)", "午时(11-13)", "未时(13-15)",
    "申时(15-17)", "酉时(17-19)", "戌时(19-21)", "亥时(21-23)",
]

# 方位映射
ELEMENT_DIRECTION_MAP: Dict[str, List[str]] = {
    "金": ["西", "西北"],
    "木": ["东", "东南"],
    "水": ["北", "西北"],
    "火": ["南", "西南"],
    "土": ["中", "东北", "西南"],
}

# 五维度与五行的关联权重
# 每个维度有不同的五行偏好
DIMENSION_ELEMENT_AFFINITY: Dict[str, Dict[str, float]] = {
    "career": {"金": 1.2, "土": 1.1, "水": 1.0, "火": 0.9, "木": 0.8},
    "wealth": {"金": 1.3, "水": 1.1, "土": 1.0, "火": 0.9, "木": 0.7},
    "love": {"火": 1.3, "木": 1.1, "水": 1.0, "土": 0.9, "金": 0.7},
    "health": {"木": 1.2, "水": 1.1, "土": 1.0, "金": 0.9, "火": 0.8},
    "study": {"水": 1.3, "木": 1.1, "金": 1.0, "土": 0.9, "火": 0.7},
}


def _get_day_ganzhi(target_date: date) -> tuple:
    """获取目标日期的天干地支"""
    dt = datetime(target_date.year, target_date.month, target_date.day, 12)
    lunar = cnlunar.Lunar(dt, godType='8char')
    day_gz = lunar.day8Char
    return day_gz[0], day_gz[1]  # 天干, 地支


def _get_element_relation(elem_a: str, elem_b: str) -> str:
    """
    判断 elem_a 对 elem_b 的关系
    返回: sheng(生), ke(克), bi(比), xie(泄), hao(耗)
    """
    if elem_a == elem_b:
        return "bi"  # 比（同）
    if WUXING_SHENG.get(elem_a) == elem_b:
        return "xie"  # 泄（我生之）
    if WUXING_KE.get(elem_a) == elem_b:
        return "hao"  # 耗（我克之）
    if WUXING_BEI_SHENG.get(elem_a) == elem_b:
        return "sheng"  # 生（生我者）
    if WUXING_BEI_KE.get(elem_a) == elem_b:
        return "ke"  # 克（克我者）
    return "bi"


def _calculate_relation_score(relation: str) -> float:
    """关系 -> 分数系数"""
    return {
        "sheng": 1.15,   # 被生：好运
        "bi": 1.05,      # 比和：平稳偏好
        "xie": 0.90,     # 泄气：稍弱
        "hao": 0.85,     # 耗气：消耗
        "ke": 0.70,      # 被克：不利
    }.get(relation, 1.0)


def calculate_daily_fortune(
    user_bazi: Dict[str, Any],
    target_date: date,
    generate_ai: bool = False,
) -> Dict[str, Any]:
    """
    计算五维度运势（v2 增强版）

    Args:
        user_bazi: 用户的八字信息 (dict with day_master, suggested_elements, etc.)
        target_date: 目标日期
        generate_ai: 是否调用 AI 生成个性化叙事（默认 False，仅详情页开启）

    Returns:
        {scores: {career, wealth, love, health, study},
         overall_score: int,
         advice_text: str,
         lucky_elements: {colors, materials, directions, elements},
         outfit_suggestion: str,
         huangli: {yi, ji, chong_sha, ji_shen, xiong_sha, solar_term, hour_luck},
         ai_narrative: {overview, career_tip, love_tip, health_tip, lucky_action, avoid_action}}
    """
    day_master = user_bazi.get("day_master", "土")
    suggested_elements = user_bazi.get("suggested_elements", [])
    avoid_elements = user_bazi.get("avoid_elements", [])

    # 获取目标日期的天干地支
    day_tiangan, day_dizhi = _get_day_ganzhi(target_date)
    day_element = TIANGAN_WUXING.get(day_tiangan, "土")
    dizhi_element = DIZHI_WUXING.get(day_dizhi, "土")

    # 计算日干与用户日干的五行关系
    tiangan_relation = _get_element_relation(day_element, day_master)
    dizhi_relation = _get_element_relation(dizhi_element, day_master)

    # 基础分数
    base_score = 65

    # 使用日期作为确定性随机种子（同一天同一用户结果一致）
    seed_val = hash(f"{user_bazi.get('pillars', {}).get('day', 'default')}_{target_date.isoformat()}")
    rng = random.Random(seed_val)

    scores: Dict[str, int] = {}
    for dimension, affinity_map in DIMENSION_ELEMENT_AFFINITY.items():
        # 天干影响(60%) + 地支影响(40%)
        tg_affinity = affinity_map.get(day_element, 1.0)
        dz_affinity = affinity_map.get(dizhi_element, 1.0)

        tg_relation_score = _calculate_relation_score(tiangan_relation)
        dz_relation_score = _calculate_relation_score(dizhi_relation)

        raw = base_score * (tg_affinity * tg_relation_score * 0.6 +
                            dz_affinity * dz_relation_score * 0.4)

        # 喜用神加成
        if day_element in suggested_elements:
            raw += 8
        if dizhi_element in suggested_elements:
            raw += 5

        # 忌神减分
        if day_element in avoid_elements:
            raw -= 8
        if dizhi_element in avoid_elements:
            raw -= 5

        # 小幅随机波动(±5)
        raw += rng.randint(-5, 5)

        scores[dimension] = max(0, min(100, int(raw)))

    overall = int(sum(scores.values()) / len(scores))

    # 幸运元素
    lucky_elements = _generate_lucky_elements(day_element, suggested_elements, day_master)

    # 穿搭建议
    outfit_suggestion = generate_outfit_suggestion(scores, user_bazi, lucky_elements)

    # 运势建议文本（保留原有公式版，作为 AI 降级兜底）
    advice_text = _generate_advice(scores, day_element, day_master, suggested_elements)

    # 黄历数据
    huangli = _get_huangli_data(target_date)

    # AI 个性化叙事
    ai_narrative = {}
    ai_usage = None
    if generate_ai:
        try:
            ai_narrative, ai_usage = _generate_ai_narrative(
                user_bazi=user_bazi,
                target_date=target_date,
                scores=scores,
                overall=overall,
                huangli=huangli,
            )
        except Exception as e:
            logger.warning(f"[FortuneEngine] AI 叙事生成失败，使用降级方案: {e}")
            ai_narrative = _fallback_ai_narrative(scores, day_element, day_master, huangli)
    else:
        # 不调用 AI 时，先用降级方案秒级返回，并标记 _pending 供后台线程异步增强
        ai_narrative = {**_fallback_ai_narrative(scores, day_element, day_master, huangli), "_pending": True}

    return {
        "scores": scores,
        "overall_score": overall,
        "advice_text": advice_text,
        "lucky_elements": lucky_elements,
        "outfit_suggestion": outfit_suggestion,
        "huangli": huangli,
        "ai_narrative": ai_narrative,
        "_llm_usage": ai_usage,
        "bazi_snapshot": {
            "day_master": day_master,
            "target_day_ganzhi": f"{day_tiangan}{day_dizhi}",
            "target_day_element": day_element,
            "pillars": user_bazi.get("pillars", {}),
        },
    }


def _generate_lucky_elements(
    day_element: str,
    suggested_elements: List[str],
    day_master: str,
) -> Dict[str, List[str]]:
    """生成幸运元素"""
    # 幸运五行 = 喜用神优先 + 当日五行辅助
    lucky_wuxing = list(suggested_elements[:2]) if suggested_elements else [day_master]
    if day_element not in lucky_wuxing and len(lucky_wuxing) < 3:
        lucky_wuxing.append(day_element)
    lucky_wuxing = lucky_wuxing[:3]

    # 从幸运五行推导颜色
    colors: List[str] = []
    for elem in lucky_wuxing:
        elem_colors = ELEMENT_COLOR_MAP.get(elem, [])
        colors.extend(elem_colors[:2])
    colors = list(dict.fromkeys(colors))[:5]

    # 材质
    materials: List[str] = []
    for elem in lucky_wuxing:
        elem_materials = ELEMENT_MATERIAL_MAP.get(elem, [])
        materials.extend(elem_materials[:2])
    materials = list(dict.fromkeys(materials))[:4]

    # 方位
    directions: List[str] = []
    for elem in lucky_wuxing:
        dirs = ELEMENT_DIRECTION_MAP.get(elem, [])
        directions.extend(dirs)
    directions = list(dict.fromkeys(directions))[:3]

    return {
        "colors": colors,
        "materials": materials,
        "directions": directions,
        "elements": lucky_wuxing,
    }


def generate_outfit_suggestion(
    fortune_scores: Dict[str, int],
    user_bazi: Dict[str, Any],
    lucky_elements: Optional[Dict] = None,
) -> str:
    """基于运势生成穿搭建议文本"""
    suggested = user_bazi.get("suggested_elements", [])
    day_master = user_bazi.get("day_master", "土")

    # 找出最高和最低维度
    sorted_dims = sorted(fortune_scores.items(), key=lambda x: x[1], reverse=True)
    best_dim = sorted_dims[0]
    worst_dim = sorted_dims[-1]

    dim_names = {
        "career": "事业", "wealth": "财运",
        "love": "桃花", "health": "健康", "study": "学业"
    }

    parts = []
    parts.append(f"今日{dim_names[best_dim[0]]}运最旺（{best_dim[1]}分），"
                 f"{dim_names[worst_dim[0]]}运需留意（{worst_dim[1]}分）。")

    if lucky_elements:
        le = lucky_elements
        if le.get("colors"):
            parts.append(f"建议穿着{'、'.join(le['colors'][:3])}色系衣物。")
        if le.get("materials"):
            parts.append(f"材质上推荐{'、'.join(le['materials'][:2])}。")

    if suggested:
        parts.append(f"五行上宜选{'、'.join(suggested[:2])}属性的穿搭，"
                     f"以增强整体运势。")

    return "".join(parts)


def _generate_advice(
    scores: Dict[str, int],
    day_element: str,
    day_master: str,
    suggested_elements: List[str],
) -> str:
    """生成运势建议文本"""
    overall = int(sum(scores.values()) / len(scores))

    if overall >= 80:
        tone = "今日运势大吉"
    elif overall >= 65:
        tone = "今日运势良好"
    elif overall >= 50:
        tone = "今日运势平稳"
    else:
        tone = "今日运势偏弱"

    parts = [f"{tone}，综合指数 {overall}。"]
    parts.append(f"今日天干属{day_element}，您的日元属{day_master}。")

    relation = _get_element_relation(day_element, day_master)
    relation_text = {
        "sheng": "日元被天干所生，得贵人扶持，但也需注意精力外泄。",
        "bi": "天干与日元比和，平稳安宁，宜守不宜急。",
        "xie": "日元生天干，精力外泄，注意休息。",
        "hao": "日元克天干，耗气劳神，宜量力而行。",
        "ke": "天干克日元，压力较大，宜韬光养晦。",
    }
    parts.append(relation_text.get(relation, ""))

    if suggested_elements:
        parts.append(f"今日宜穿戴{'、'.join(suggested_elements[:2])}五行属性的衣物饰品，以增强运势。")

    return "".join(parts)


# ============================================================
# v2 新增：黄历数据提取
# ============================================================

def _get_lunar(target_date: date) -> cnlunar.Lunar:
    """获取 cnlunar Lunar 对象（缓存友好的封装）"""
    dt = datetime(target_date.year, target_date.month, target_date.day, 12)
    return cnlunar.Lunar(dt, godType='8char')


def _get_huangli_data(target_date: date) -> Dict[str, Any]:
    """
    从 cnlunar 提取黄历关键数据

    Returns:
        {
            yi: ["祭祀", "沐浴", ...],       # 宜
            ji: ["安葬", "开渠", ...],        # 忌
            chong_sha: "猴日冲虎",            # 冲煞
            chong_zodiac: "虎",               # 被冲生肖
            ji_shen: ["四相", "天官", ...],   # 吉神
            xiong_sha: ["劫煞", "五鬼", ...], # 凶煞
            solar_term: "立秋" | None,        # 当天节气
            next_solar_term: "立秋",          # 下一个节气
            days_to_next_term: 5,             # 距下个节气天数
            hour_luck: [                       # 十二时辰吉凶
                {"hour": "子时(23-01)", "ganzhi": "壬子", "lucky": "吉"},
                ...
            ],
        }
    """
    lunar = _get_lunar(target_date)

    # 宜忌
    yi = list(lunar.goodThing) if hasattr(lunar, 'goodThing') and lunar.goodThing else []
    ji = list(lunar.badThing) if hasattr(lunar, 'badThing') and lunar.badThing else []

    # 冲煞
    chong_sha = str(lunar.chineseZodiacClash) if hasattr(lunar, 'chineseZodiacClash') else ""
    chong_zodiac = str(lunar.zodiacLose) if hasattr(lunar, 'zodiacLose') else ""

    # 吉神凶煞
    ji_shen = list(lunar.goodGodName) if hasattr(lunar, 'goodGodName') and lunar.goodGodName else []
    xiong_sha = list(lunar.badGodName) if hasattr(lunar, 'badGodName') and lunar.badGodName else []

    # 节气
    solar_term = str(lunar.todaySolarTerms) if hasattr(lunar, 'todaySolarTerms') else "无"
    if solar_term == "无":
        solar_term = None
    next_solar_term = str(lunar.nextSolarTerm) if hasattr(lunar, 'nextSolarTerm') else ""
    days_to_next_term = 0
    if hasattr(lunar, 'nextSolarTermDate') and lunar.nextSolarTermDate:
        try:
            term_month, term_day = lunar.nextSolarTermDate
            term_date = date(target_date.year, term_month, term_day)
            days_to_next_term = (term_date - target_date).days
        except Exception:
            pass

    # 十二时辰吉凶
    hour_luck: List[Dict[str, str]] = []
    try:
        lucky_list = lunar.get_twohourLuckyList()
        ganzhi_list = lunar.get_twohour8CharList()
        for i in range(12):
            hour_luck.append({
                "hour": _SHICHEN_NAMES[i] if i < len(_SHICHEN_NAMES) else f"时辰{i+1}",
                "ganzhi": ganzhi_list[i] if i < len(ganzhi_list) else "",
                "lucky": lucky_list[i] if i < len(lucky_list) else "平",
            })
    except Exception:
        pass

    return {
        "yi": yi[:6],
        "ji": ji[:6],
        "chong_sha": chong_sha,
        "chong_zodiac": chong_zodiac,
        "ji_shen": ji_shen[:5],
        "xiong_sha": xiong_sha[:5],
        "solar_term": solar_term,
        "next_solar_term": next_solar_term,
        "days_to_next_term": days_to_next_term,
        "hour_luck": hour_luck,
        "today_level_name": str(lunar.todayLevelName) if hasattr(lunar, 'todayLevelName') else "",
    }


# ============================================================
# v2 新增：AI 个性化运势叙事
# ============================================================

# 维度中文名
_DIM_NAMES = {"career": "事业", "wealth": "财运", "love": "桃花", "health": "健康", "study": "学业"}

# 五行生克关系中文
_RELATION_CN = {
    "sheng": "被生（得贵人扶持）",
    "bi": "比和（平稳安宁）",
    "xie": "泄气（精力外泄）",
    "hao": "耗气（劳神费力）",
    "ke": "被克（压力较大）",
}


def _generate_ai_narrative(
    user_bazi: Dict[str, Any],
    target_date: date,
    scores: Dict[str, int],
    overall: int,
    huangli: Dict[str, Any],
) -> tuple:
    """
    调用 LLM 生成个性化运势叙事

    Returns:
        (narrative, usage) 元组：
        narrative: {
            overview: str,       # 今日格局概述
            career_tip: str,     # 事业提示
            love_tip: str,       # 感情提示
            health_tip: str,     # 健康提示
            lucky_action: str,   # 今日宜
            avoid_action: str,   # 今日忌
        }
    """
    day_master = user_bazi.get("day_master", "土")
    suggested = user_bazi.get("suggested_elements", [])
    avoid = user_bazi.get("avoid_elements", [])
    pillars = user_bazi.get("pillars", {})

    day_tiangan, day_dizhi = _get_day_ganzhi(target_date)
    day_element = TIANGAN_WUXING.get(day_tiangan, "土")

    # 五行关系
    relation = _get_element_relation(day_element, day_master)
    relation_cn = _RELATION_CN.get(relation, "")

    # 最好/最差维度
    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_dim = _DIM_NAMES.get(sorted_dims[0][0], sorted_dims[0][0])
    worst_dim = _DIM_NAMES.get(sorted_dims[-1][0], sorted_dims[-1][0])

    # 黄历摘要
    yi_text = "、".join(huangli.get("yi", [])[:3]) or "无特殊宜事"
    ji_text = "、".join(huangli.get("ji", [])[:3]) or "无特殊忌事"
    chong_sha = huangli.get("chong_sha", "")
    solar_term = huangli.get("solar_term") or ""
    next_term = huangli.get("next_solar_term", "")
    days_to_term = huangli.get("days_to_next_term", 0)

    # 节气上下文
    solar_context = ""
    if solar_term:
        solar_context = f"今天是「{solar_term}」节气。"
    elif next_term and 0 < days_to_term <= 7:
        solar_context = f"{days_to_term}天后是「{next_term}」节气，正值换季之际。"

    prompt = f"""你是一位精通中国传统命理学的运势大师，请为用户生成今日运势的个性化叙事。

## 用户八字
- 日主：{day_master}
- 喜用神：{', '.join(suggested) if suggested else '待定'}
- 忌讳五行：{', '.join(avoid) if avoid else '待定'}
- 四柱：{json.dumps(pillars, ensure_ascii=False) if pillars else '未提供'}

## 今日干支
- 天干：{day_tiangan}（五行属{day_element}）
- 地支：{day_dizhi}
- 日干对日主关系：{relation_cn}

## 五维度评分
- 事业：{scores.get('career', 0)} | 财运：{scores.get('wealth', 0)} | 桃花：{scores.get('love', 0)}
- 健康：{scores.get('health', 0)} | 学业：{scores.get('study', 0)}
- 综合：{overall} 分
- 最强维度：{best_dim}（{sorted_dims[0][1]}分）
- 最弱维度：{worst_dim}（{sorted_dims[-1][1]}分）

## 黄历信息
- 宜：{yi_text}
- 忌：{ji_text}
- 冲煞：{chong_sha}
{solar_context}

## 要求
请生成结构化 JSON，每段 50-80 字，温暖有共鸣，有具体可操作的建议。

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

    try:
        client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            timeout=20,  # 限制 LLM 调用耗时，避免后台增强线程长时间挂起
        )
        response = client.chat.completions.create(
            model=settings.qwen_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )
        content = response.choices[0].message.content.strip()

        # 清理 markdown 标记
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]

        return json.loads(content), extract_llm_usage(response)
    except Exception as e:
        logger.error(f"[FortuneEngine] AI 叙事生成异常: {e}")
        raise


def _fallback_ai_narrative(
    scores: Dict[str, int],
    day_element: str,
    day_master: str,
    huangli: Dict[str, Any],
) -> Dict[str, Any]:
    """AI 生成失败时的降级叙事（基于公式 + 黄历拼装）"""
    overall = int(sum(scores.values()) / len(scores))
    relation = _get_element_relation(day_element, day_master)

    sorted_dims = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_dim = _DIM_NAMES.get(sorted_dims[0][0], sorted_dims[0][0])
    worst_dim = _DIM_NAMES.get(sorted_dims[-1][0], sorted_dims[-1][0])

    # 格局概述
    if overall >= 80:
        overview = f"今日{day_element}气旺盛，与您的日元{day_master}形成有利格局，整体运势上扬。{best_dim}运尤为突出，适合把握机会。"
    elif overall >= 65:
        overview = f"今日五行相对平衡，{day_element}与日元{day_master}的互动较为和谐，整体运势平稳向好。"
    elif overall >= 50:
        overview = f"今日运势中规中矩，{worst_dim}方面稍需留意，但整体仍可从容应对。"
    else:
        overview = f"今日{day_element}对日元{day_master}形成克制，整体运势偏弱，建议韬光养晦、减少重要决策。"

    # 各维度提示
    career_tip = f"{best_dim}运较旺（{sorted_dims[0][1]}分），适合专注于核心事务，稳扎稳打。"
    love_tip = "保持平和心态，多与身边人沟通交流，感情贵在真诚。"
    health_tip = "注意作息规律，适度运动有助于平衡五行能量。"

    # 宜忌（从黄历提取）
    yi = huangli.get("yi", [])
    ji = huangli.get("ji", [])
    lucky_action = f"今日宜{'、'.join(yi[:2])}" if yi else "今日宜保持平常心，顺其自然"
    avoid_action = f"今日忌{'、'.join(ji[:2])}" if ji else "今日忌冲动决策，凡事三思"

    return {
        "overview": overview,
        "career_tip": career_tip,
        "love_tip": love_tip,
        "health_tip": health_tip,
        "lucky_action": lucky_action,
        "avoid_action": avoid_action,
    }
