"""
推荐上下文提取

从用户输入中提取场景、天气、旅行等上下文信息。
支持 LLM 提取（主路径）和规则提取（备用路径）双通道。
"""

import re
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 旅行/出差意图关键词：仅当 Query 明确涉及旅行/出差语境时才提取行程参数，
# 避免普通穿搭提问（如"北京穿什么"）被误判为行程规划（用户反馈 #4）
TRAVEL_INTENT_KEYWORDS = (
    "出差", "旅行", "旅游", "行程", "度假", "出行", "差旅", "商务旅行",
    "行李", "行李箱", "打包",
)

# 明确日期/时间信号：只有提及具体出发时间时，目的地天气预报才有时间维度依据；
# 仅有地点+天数（如"北京三天行程"）时不做天气预判，避免输出不准确的天气数据（用户反馈 #4）
DATE_SIGNAL_PATTERNS = (
    r"明天", r"后天", r"大后天", r"今天",
    r"下周", r"本周", r"这周", r"周末",
    r"下个月", r"月底", r"月初",
    r"\d+\s*月\s*\d+\s*[日号]",
    r"周[一二三四五六日天末]",
    r"星期[一二三四五六日天]",
    r"\d+\s*[天日周后]后",
    # 数字月日写法（如 "8.30，8.31去武汉出差"，用户反馈：明确给了日期仍提示未提供）；
    # 月份限定 1-12、日期限定 1-31，前置 (?<![\d.]) 与后置单位排除避免误匹配 "36.5度"/"3.5小时"
    r"(?<![\d.])(?:[1-9]|1[0-2])\.(?:0?[1-9]|[12]\d|3[01])(?!\s*(?:度|℃|小时|分钟|点|折|倍|年|月))",
    r"(?<![\d.])(?:[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])(?!\s*(?:度|℃|小时|分钟|点|折|倍))",
)


def has_travel_intent(user_input: str) -> bool:
    """判断 Query 是否明确涉及旅行/出差意图"""
    return any(kw in user_input for kw in TRAVEL_INTENT_KEYWORDS)


def has_date_signal(user_input: str) -> bool:
    """判断 Query 是否包含明确的出行日期/时间信号"""
    return any(re.search(p, user_input) for p in DATE_SIGNAL_PATTERNS)


def extract_context_from_query(user_input: str) -> Dict:
    """
    使用大模型从用户输入中提取场景、天气、气温信息

    优先级：用户提问中的信息 > 外部设置
    失败时自动回退到规则提取。

    Returns:
        {
            "scene": str | None,
            "weather_info": dict | None,
            "weather_element": str | None,
            "travel_days": int | None,
            "destination": str | None,
            "travel_date_confirmed": bool,  # 用户是否提供了明确出行日期
        }
    """
    try:
        from packages.ai_agents.nodes import get_llm_client
        from apps.api.core.config import settings

        client = get_llm_client(timeout=30)

        prompt = f"""你是一位信息提取专家，请从用户的穿搭咨询中提取关键信息。

用户输入：{user_input}

请提取以下信息（如果存在）：
1. scene: 场景（商务/面试/约会/运动/居家/婚礼/派对/旅行/出差/度假/户外探险/会议/上班/其他）
2. temperature: 气温（数字，单位摄氏度）
3. weather_desc: 天气描述（闷热/炎热/寒冷/雨天/雪天/晴天/多云/大风）
4. travel_days: 旅行天数（数字，如用户提到"去北京出差3天"则为3）
5. destination: 目的地城市（如用户提到"去三亚"则为"三亚"）

**重要旅行参数提取规则**：
- 仅当用户**明确提及旅行/出差/行程/度假/出行等旅行语境**时，才提取 travel_days 和 destination；
  普通穿搭提问（如"北京今天穿什么"）即使包含城市名也不要提取旅行参数

**重要场景识别规则**：
- 如果提到“游泳”、“戏水”、“玩水”、“海边游泳”、“泳池”等，场景应该是“运动”（不是“旅行”）
- 如果提到"马拉松"、"跑步"、"健身"、"瑜伽"等，场景应该是"运动"
- 如果提到"三亚"、"海边"、"度假"但**没有**提到具体运动，场景才是"度假"
- 如果提到"出差"、"商务旅行"，场景应该是"出差"
- 如果提到"徒步"、"登山"、"露营"、"滑雪"等，场景应该是"户外探险"
- 运动场景优先级 > 出差/度假/旅行场景

返回严格的 JSON 格式，不要有任何其他内容。如果某个信息不存在，使用 null。

示例格式：
{{"scene": "出差", "temperature": 15, "weather_desc": "多云", "travel_days": 3, "destination": "北京"}}
"""

        response = client.chat.completions.create(
            model=settings.qwen_model,
            messages=[
                {"role": "system", "content": "你是一个信息提取助手，只返回 JSON 格式的结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        extracted = json.loads(response.choices[0].message.content)

        result = {
            "scene": None,
            "weather_info": None,
            "weather_element": None,
            "travel_days": None,
            "destination": None,
            "travel_date_confirmed": has_date_signal(user_input),
        }

        scene = extracted.get("scene")
        temperature = extracted.get("temperature")
        weather_desc = extracted.get("weather_desc")
        travel_days = extracted.get("travel_days")
        destination = extracted.get("destination")

        # 旅行意图安全网：LLM 可能过度提取，无旅行关键词时强制丢弃行程参数（用户反馈 #4）
        if not has_travel_intent(user_input):
            travel_days = None
            destination = None

        # 场景映射
        scene_mapping = {
            "商务": "商务", "面试": "面试", "约会": "约会",
            "运动": "运动", "居家": "居家", "婚礼": "婚礼",
            "派对": "派对", "旅行": "旅行", "出差": "出差",
            "度假": "度假", "户外探险": "户外探险",
            "上班": "商务", "办公": "商务", "会议": "会议",
        }

        if scene:
            result["scene"] = scene_mapping.get(scene, scene)

        if travel_days is not None:
            try:
                result["travel_days"] = int(travel_days)
            except (ValueError, TypeError):
                pass

        if destination:
            result["destination"] = destination

        if temperature is not None or weather_desc:
            result["weather_info"] = {
                "temperature": temperature,
                "weather_desc": weather_desc,
                "humidity": None,
                "wind_level": None,
            }
            if weather_desc:
                result["weather_element"] = _weather_desc_to_element(weather_desc)

        logger.info(f"[LLM提取] 场景: {result['scene']}, 天气: {weather_desc}, 温度: {temperature}")

        # token 用量随结果带回，供 agent 链路累加成本核算
        from apps.api.services.llm_usage_service import extract_llm_usage
        usage = extract_llm_usage(response)
        if usage:
            result["llm_usage"] = usage

        return result

    except Exception as e:
        logger.warning(f"[LLM提取] 失败，回退到规则提取: {e}")
        return extract_context_by_rules(user_input)


def extract_context_by_rules(user_input: str) -> Dict:
    """
    基于规则的上下文提取（备用方案）

    场景优先级：运动 > 户外探险 > 出差 > 度假 > 商务 > 面试 > 旅行 > 上班 > 约会 > 居家 > 婚礼 > 派对
    """
    result = {
        "scene": None,
        "weather_info": None,
        "weather_element": None,
        "travel_days": None,
        "destination": None,
        "travel_date_confirmed": has_date_signal(user_input),
    }

    text = user_input.lower()

    # 1. 场景提取（活动型优先于地点型）
    if any(kw in text for kw in ['马拉松', '跑步', '健身', '运动', '打球', '游泳', '瑜伽', '戏水', '玩水']):
        result["scene"] = "运动"
    elif any(kw in text for kw in ['徒步', '登山', '露营', '探险', '滑雪', '户外探险']):
        result["scene"] = "户外探险"
    elif any(kw in text for kw in ['出差', '商务旅行', '多天出差']):
        result["scene"] = "出差"
    elif any(kw in text for kw in ['度假', '海边', '温泉', '三亚', '旅游度假', '去三亚', '去海边']):
        result["scene"] = "度假"
    elif any(kw in text for kw in ['商务', '会议', '见客户', '办公']):
        result["scene"] = "商务"
    elif '面试' in text:
        result["scene"] = "面试"
    elif any(kw in text for kw in ['旅行', '旅游', '去成都', '去北京', '去上海', '去广州', '去深圳']):
        result["scene"] = "旅行"
    elif any(kw in text for kw in ['上班', '工作']):
        result["scene"] = "商务"
    elif any(kw in text for kw in ['约会', '相亲', '见面']):
        result["scene"] = "约会"
    elif any(kw in text for kw in ['居家', '在家', '宅', '休息']):
        result["scene"] = "居家"
    elif any(kw in text for kw in ['婚礼', '结婚', '婚宴']):
        result["scene"] = "婚礼"
    elif any(kw in text for kw in ['派对', '聚会', 'party']):
        result["scene"] = "派对"

    # 旅行意图门控：无旅行/出差关键词且场景非旅行类时不提取行程参数，
    # 避免普通提问（如"北京穿什么"）误触发行程规划（用户反馈 #4）
    travel_intent = has_travel_intent(user_input) or result["scene"] in (
        "旅行", "出差", "度假", "户外探险",
    )

    # 2. 多天行程提取（仅在明确旅行意图时）
    if travel_intent:
        day_match = re.search(r'(\d+)\s*[天日]', text)
        if day_match:
            result["travel_days"] = int(day_match.group(1))
        else:
            cn_num_map = {'一': 1, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
            cn_day_match = re.search(r'([一二两三四五六七八九十])\s*[天日]', text)
            if cn_day_match:
                result["travel_days"] = cn_num_map.get(cn_day_match.group(1), 1)

    # 3. 目的地城市提取（仅在明确旅行意图时）
    dest_match = None
    if travel_intent:
        dest_match = re.search(
            r'(?:去|到|飞|前往|出发去)\s*([\u4e00-\u9fa5]{2,4}?)(?=[出差旅游度假玩天日回来了\s]|$)',
            text,
        )
    if dest_match:
        city = dest_match.group(1)
        non_city_words = {'什么', '哪里', '怎么', '这里', '那里', '外面', '室内', '户外'}
        if city not in non_city_words and len(city) >= 2:
            result["destination"] = city

    # 4. 气温提取
    temp_match = re.search(r'(\d+)\s*[°度℃cC]', text)
    if not temp_match:
        temp_match = re.search(r'气温[^\d]*(\d+)', text)

    temperature = None
    if temp_match:
        temperature = int(temp_match.group(1))

    # 5. 天气描述提取
    weather_desc = None
    if any(kw in text for kw in ['潮湿', '闷热', '潮湿闷热']):
        weather_desc = "闷热"
    elif any(kw in text for kw in ['炎热', '高温', '很热', '太热']):
        weather_desc = "炎热"
    elif any(kw in text for kw in ['寒冷', '低温', '很冷', '太冷', '极寒']):
        weather_desc = "寒冷"
    elif any(kw in text for kw in ['下雨', '雨天', '阴雨']):
        weather_desc = "雨天"
    elif any(kw in text for kw in ['下雪', '雪天']):
        weather_desc = "雪天"
    elif any(kw in text for kw in ['晴天', '晴朗', '出太阳']):
        weather_desc = "晴天"
    elif '多云' in text:
        weather_desc = "多云"
    elif any(kw in text for kw in ['大风', '刮风']):
        weather_desc = "大风"

    # 6. 组装天气信息
    if temperature is not None or weather_desc is not None:
        result["weather_info"] = {
            "temperature": temperature,
            "weather_desc": weather_desc,
            "humidity": None,
            "wind_level": None,
        }
        if weather_desc:
            result["weather_element"] = _weather_desc_to_element(weather_desc)

    return result


def _weather_desc_to_element(weather_desc: str) -> Optional[str]:
    """天气描述 → 五行元素映射"""
    weather_element_map = {
        "闷热": "火", "炎热": "火", "寒冷": "水",
        "雨天": "水", "雪天": "水", "晴天": "火",
        "多云": "土", "大风": "木",
    }
    return weather_element_map.get(weather_desc)
