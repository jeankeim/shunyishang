"""
LLM 意图理解层

使用低成本大模型（qwen-flash）从用户自然语言输入中提取结构化意图，
映射到现有推荐系统的规则 schema，保持下游链路不变。

双通道设计：
- 主路径：LLM 提取（泛化能力强，覆盖规则未覆盖的维度如品类/风格/颜色否定）
- 备用路径：规则提取（LLM 失败时回退，保证可用性）
"""

import re
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================
# 枚举词表（作为 prompt context 注入，确保 LLM 输出落在现有 schema 内）
# ============================================================

# 五行枚举
WUXING_ENUM = ["金", "木", "水", "火", "土"]

# 品类枚举（items 表 category 字段的实际取值）
CATEGORY_ENUM = ["上装", "下装", "裙装", "外套", "鞋履", "配饰", "饰品", "文玩"]

# 场景枚举（SCENE_ELEMENT_MAP 键 + 旅行场景扩展）
SCENE_ENUM = [
    "面试", "约会", "日常", "商务", "运动", "派对", "居家",
    "旅行", "婚礼", "会议", "出差", "度假", "户外探险",
]

# 厚度枚举
THICKNESS_ENUM = ["厚重", "中厚", "适中", "轻薄", "极薄"]

# 天气描述枚举
WEATHER_DESC_ENUM = ["闷热", "炎热", "寒冷", "雨天", "雪天", "晴天", "多云", "大风"]

# 颜色词表（从 ELEMENT_COLOR_MAP 展开）
COLOR_VOCAB = [
    "白色", "银色", "灰色", "米白", "乳白", "香槟", "金色",
    "绿色", "青色", "翠绿", "墨绿", "浅绿", "草绿", "薄荷",
    "黑色", "蓝色", "深蓝", "藏青", "墨蓝", "海军蓝", "深灰",
    "红色", "粉色", "橙色", "紫色", "玫红", "酒红", "珊瑚",
    "棕色", "黄色", "卡其", "驼色", "米色", "咖啡", "土黄",
]

# 材质词表（从 ELEMENT_MATERIAL_MAP 展开）
MATERIAL_VOCAB = [
    "棉", "麻", "丝绸", "真丝", "羊毛", "羊绒", "皮革", "牛仔",
    "涤纶", "尼龙", "雪纺", "蕾丝", "天鹅绒", "灯芯绒", "帆布",
]

# 风格词表（从 ELEMENT_STYLE_MAP 展开）
STYLE_VOCAB = [
    "清新", "自然", "生机", "活力", "成长", "春天", "户外", "运动",
    "随性", "文艺", "青春", "健康", "舒展", "宽松", "热情", "浪漫",
    "活泼", "张扬", "喜庆", "派对", "约会", "桃花", "亮丽", "旺桃花",
    "性感", "明艳", "活力", "热烈", "稳重", "踏实", "温暖", "亲和",
    "家居", "休闲", "舒适", "包容", "温柔", "可靠", "沉稳", "大地",
    "质朴", "干练", "专业", "正式", "精致", "简约", "利落", "面试",
    "商务", "高冷", "天真", "清纯", "优雅", "高级", "大气", "职场",
    "神秘", "深沉", "冷静", "沉稳", "内敛", "智慧", "高贵", "优雅",
    "知性", "深邃", "低调", "内涵", "气质",
]


# ============================================================
# 意图数据结构
# ============================================================

@dataclass
class QueryIntent:
    """LLM 意图理解结果"""
    # 基础意图
    is_fashion: bool = True  # 是否穿搭意图
    confidence: float = 0.0  # 整体置信度 (0-1)

    # 五行意图
    elements_add: List[str] = field(default_factory=list)  # 要补的五行（缺X/补X/旺X）
    elements_avoid: List[str] = field(default_factory=list)  # 要避的五行（忌X/不要X）
    xiyong: List[str] = field(default_factory=list)  # 用户自述喜用神（喜用神是X）
    ming: List[str] = field(default_factory=list)  # 用户自述命主（X命人/日主X）

    # 品类约束（新增维度）
    categories: List[str] = field(default_factory=list)  # 用户指定的品类（上装/裙装等）

    # 颜色/材质/风格偏好
    colors: List[str] = field(default_factory=list)  # 颜色偏好
    colors_avoid: List[str] = field(default_factory=list)  # 颜色回避（不要绿色）
    materials: List[str] = field(default_factory=list)  # 材质偏好
    styles: List[str] = field(default_factory=list)  # 风格偏好（正式/休闲）
    thickness: Optional[str] = None  # 厚度偏好（薄一点/厚一点）

    # 场景/天气
    scene: Optional[str] = None  # 主场景
    sub_scene: Optional[str] = None  # 子场景（如马拉松/瑜伽）
    temperature: Optional[int] = None  # 气温（摄氏度）
    weather_desc: Optional[str] = None  # 天气描述

    # 旅行参数
    destination: Optional[str] = None  # 目的地城市
    travel_days: Optional[int] = None  # 旅行天数

    # 锚点单品
    anchor_phrases: List[str] = field(default_factory=list)  # 用户指定的已有单品（白衬衫/黑色风衣）

    # 原始槽位（调试用）
    raw_slots: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 缓存
# ============================================================

_intent_cache: Dict[str, QueryIntent] = {}  # 内存缓存：md5(query) -> QueryIntent
_INTENT_CACHE_TTL = 3600  # 1 小时
_cache_timestamps: Dict[str, float] = {}


def _get_cached_intent(query: str) -> Optional[QueryIntent]:
    """获取缓存的意图（内存缓存，进程级）"""
    import time
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in _intent_cache:
        ts = _cache_timestamps.get(cache_key, 0)
        if time.time() - ts < _INTENT_CACHE_TTL:
            logger.debug(f"[意图缓存] 命中: {query[:30]}...")
            return _intent_cache[cache_key]
    return None


def _set_cached_intent(query: str, intent: QueryIntent) -> None:
    """缓存意图结果"""
    import time
    cache_key = hashlib.md5(query.encode()).hexdigest()
    _intent_cache[cache_key] = intent
    _cache_timestamps[cache_key] = time.time()


# ============================================================
# 枚举校验层（防止 LLM 幻觉产出非法值）
# ============================================================

def _validate_enum(value: Optional[str], enum_list: List[str]) -> Optional[str]:
    """校验单个值是否在枚举内"""
    if not value:
        return None
    if value in enum_list:
        return value
    # 模糊匹配：枚举项包含 value 或 value 包含枚举项
    for item in enum_list:
        if value in item or item in value:
            return item
    return None


def _validate_enum_list(values: Optional[List[str]], enum_list: List[str]) -> List[str]:
    """校验列表中的每个值是否在枚举内"""
    if not values:
        return []
    result = []
    for v in values:
        validated = _validate_enum(v, enum_list)
        if validated and validated not in result:
            result.append(validated)
    return result


def _validate_intent(intent: QueryIntent) -> QueryIntent:
    """校验并清洗意图结果，丢弃非法值"""
    intent.elements_add = _validate_enum_list(intent.elements_add, WUXING_ENUM)
    intent.elements_avoid = _validate_enum_list(intent.elements_avoid, WUXING_ENUM)
    intent.xiyong = _validate_enum_list(intent.xiyong, WUXING_ENUM)
    intent.ming = _validate_enum_list(intent.ming, WUXING_ENUM)
    intent.categories = _validate_enum_list(intent.categories, CATEGORY_ENUM)
    intent.colors = _validate_enum_list(intent.colors, COLOR_VOCAB)
    intent.colors_avoid = _validate_enum_list(intent.colors_avoid, COLOR_VOCAB)
    intent.materials = _validate_enum_list(intent.materials, MATERIAL_VOCAB)
    intent.styles = _validate_enum_list(intent.styles, STYLE_VOCAB)
    intent.thickness = _validate_enum(intent.thickness, THICKNESS_ENUM)
    intent.scene = _validate_enum(intent.scene, SCENE_ENUM)
    intent.weather_desc = _validate_enum(intent.weather_desc, WEATHER_DESC_ENUM)
    return intent


# ============================================================
# LLM 意图提取（主路径）
# ============================================================

_INTENT_PROMPT_TEMPLATE = """你是一位穿搭意图理解专家。请从用户的输入中提取结构化意图。

## 用户输入
{user_input}

## 提取维度与可选值

### 1. 基础判断
- is_fashion: 是否与穿搭/服装/配饰相关（true/false）

### 2. 五行意图（仅当用户明确提及五行指令时提取）
- elements_add: 用户要求补/加强的五行，可选值：{wuxing_enum}
  触发词：缺X、补X、旺X、想要X、需要X、多穿X
- elements_avoid: 用户要求回避的五行，可选值：{wuxing_enum}
  触发词：忌X、不要X、别穿X、少穿X、避开X
- xiyong: 用户自述喜用神，可选值：{wuxing_enum}
  触发词：喜用神是X、用神为X
- ming: 用户自述命主，可选值：{wuxing_enum}
  触发词：X命人、日主X

### 3. 品类约束（用户明确指定要/不要某类衣物时提取）
- categories: 用户指定的品类，可选值：{category_enum}
  示例："上装"、"裙子"→裙装、"鞋子"→鞋履、"外套"→外套
  注意：仅当用户明确要求某品类时提取，不要过度推断

### 4. 颜色/材质/风格偏好
- colors: 用户喜欢的颜色，可选值：{color_vocab}
- colors_avoid: 用户不要的颜色，可选值：{color_vocab}
  触发词：不要X色、别穿X色、避开X色
- materials: 用户喜欢的材质，可选值：{material_vocab}
- styles: 用户喜欢的风格，可选值：{style_vocab}
  示例："正式一点"→正式、"休闲"→休闲、"商务"→商务

### 5. 厚度偏好
- thickness: 薄/厚偏好，可选值：{thickness_enum}
  触发词：薄一点、厚一点、轻薄、厚重

### 6. 场景/天气
- scene: 场景，可选值：{scene_enum}
- sub_scene: 子场景（如马拉松/瑜伽/游泳），自由文本
- temperature: 气温（数字，摄氏度）
- weather_desc: 天气描述，可选值：{weather_desc_enum}

### 7. 旅行参数（仅当用户明确提及旅行/出差时提取）
- destination: 目的地城市
- travel_days: 旅行天数（数字）

### 8. 锚点单品（用户提到自己已拥有的某件单品，要搭配其他）
- anchor_phrases: 锚点单品短语列表
  示例："我有一个白色裤子"→["白色裤子"]、"用我的黑色风衣搭一套"→["黑色风衣"]

## 提取规则
1. 只提取用户**明确提及**的信息，不要过度推断
2. 品类只在用户明确说"上装/裙子/鞋子"等时提取，"今天穿什么"不提取品类
3. 五行指令必须用户明确说"缺 X/补 X/忌 X/喜用神是 X"等才提取
4. 锚点单品必须是用户说自己"已有"的物品，不是要求推荐的物品
5. 如果某个维度没有信息，返回 null 或空数组

## 常见错误示例（务必避免）

### 错误 1：把品类当成锚点
- 用户说："推荐一件木属性的上装"
- 错误：categories=["上装"], anchor_phrases=["上装"]  ← 上装是目标品类，不是已有单品
- 正确：categories=["上装"], anchor_phrases=[]

### 错误 2：把目标品类当成已有物品
- 用户说："我想买条裙子"
- 错误：anchor_phrases=["裙子"]  ← 用户要买，不是已有
- 正确：categories=["裙装"], anchor_phrases=[]

### 错误 3：过度推断五行
- 用户说："今天穿什么"
- 错误：elements_add=["木"]  ← 用户没说五行，不要推断
- 正确：elements_add=[]

### 错误 4：把场景当成锚点
- 用户说："开会穿什么"
- 错误：anchor_phrases=["开会"]  ← 开会是场景，不是物品
- 正确：scene="商务", anchor_phrases=[]

## 输出格式
返回严格的 JSON，不要有任何其他内容：
{{
  "is_fashion": true,
  "confidence": 0.9,
  "elements_add": [],
  "elements_avoid": [],
  "xiyong": [],
  "ming": [],
  "categories": [],
  "colors": [],
  "colors_avoid": [],
  "materials": [],
  "styles": [],
  "thickness": null,
  "scene": null,
  "sub_scene": null,
  "temperature": null,
  "weather_desc": null,
  "destination": null,
  "travel_days": null,
  "anchor_phrases": []
}}
"""


def _call_intent_llm(user_input: str) -> Optional[QueryIntent]:
    """
    调用 LLM 提取意图（主路径）

    Returns:
        QueryIntent 或 None（失败时）
    """
    try:
        from apps.api.core.config import settings
        from packages.ai_agents.nodes import get_llm_client, call_llm_with_retry

        client = get_llm_client(timeout=10)  # 意图理解给 10s 超时

        prompt = _INTENT_PROMPT_TEMPLATE.format(
            user_input=user_input,
            wuxing_enum="、".join(WUXING_ENUM),
            category_enum="、".join(CATEGORY_ENUM),
            scene_enum="、".join(SCENE_ENUM),
            thickness_enum="、".join(THICKNESS_ENUM),
            weather_desc_enum="、".join(WEATHER_DESC_ENUM),
            color_vocab="、".join(COLOR_VOCAB[:15]),  # 截断避免 prompt 过长
            material_vocab="、".join(MATERIAL_VOCAB[:10]),
            style_vocab="、".join(STYLE_VOCAB[:15]),
        )

        response = call_llm_with_retry(
            client=client,
            messages=[
                {"role": "system", "content": "你是意图提取助手，只返回 JSON。"},
                {"role": "user", "content": prompt},
            ],
            model=settings.qwen_flash_model,
            max_tokens=300,
            temperature=0,
            stream=False,
        )

        raw = json.loads(response.choices[0].message.content)

        # 构建 QueryIntent
        intent = QueryIntent(
            is_fashion=raw.get("is_fashion", True),
            confidence=raw.get("confidence", 0.5),
            elements_add=raw.get("elements_add") or [],
            elements_avoid=raw.get("elements_avoid") or [],
            xiyong=raw.get("xiyong") or [],
            ming=raw.get("ming") or [],
            categories=raw.get("categories") or [],
            colors=raw.get("colors") or [],
            colors_avoid=raw.get("colors_avoid") or [],
            materials=raw.get("materials") or [],
            styles=raw.get("styles") or [],
            thickness=raw.get("thickness"),
            scene=raw.get("scene"),
            sub_scene=raw.get("sub_scene"),
            temperature=raw.get("temperature"),
            weather_desc=raw.get("weather_desc"),
            destination=raw.get("destination"),
            travel_days=raw.get("travel_days"),
            anchor_phrases=raw.get("anchor_phrases") or [],
            raw_slots=raw,
        )

        # 枚举校验
        intent = _validate_intent(intent)

        logger.info(
            f"[LLM意图] 提取成功: fashion={intent.is_fashion}, "
            f"categories={intent.categories}, elements_add={intent.elements_add}, "
            f"scene={intent.scene}, anchors={intent.anchor_phrases}"
        )

        return intent

    except Exception as e:
        logger.warning(f"[LLM意图] 调用失败，回退规则提取: {e}")
        return None


# ============================================================
# 规则提取（备用路径）
# ============================================================

def _extract_intent_by_rules(user_input: str) -> QueryIntent:
    """
    基于规则的意图提取（备用路径）

    当 LLM 失败时，使用现有规则链路提取意图。
    """
    from packages.utils.bazi_calculator import (
        infer_elements_from_text,
        extract_explicit_element_intent,
    )
    from packages.utils.anchor_item import extract_anchor_specs
    from packages.utils.scene_mapper import extract_scene_multidimensional
    from packages.recommendation.context_extraction import extract_context_by_rules

    intent = QueryIntent()

    # 五行意图
    element_result = infer_elements_from_text(user_input)
    if element_result.get("elements"):
        intent.elements_add = element_result["elements"]

    # 显式五行指令
    explicit = extract_explicit_element_intent(user_input)
    intent.elements_add = explicit.get("add", []) or intent.elements_add
    intent.elements_avoid = explicit.get("avoid", [])
    intent.xiyong = explicit.get("xiyong", [])
    intent.ming = explicit.get("ming", [])

    # 锚点单品
    anchors = extract_anchor_specs(user_input)
    intent.anchor_phrases = [a.get("phrase", "") for a in anchors if a.get("phrase")]

    # 场景
    scene_data = extract_scene_multidimensional(user_input)
    intent.scene = scene_data.get("main_scene")
    intent.sub_scene = scene_data.get("sub_scene")

    # 天气/旅行
    context = extract_context_by_rules(user_input)
    intent.temperature = context.get("weather_info", {}).get("temperature") if context.get("weather_info") else None
    intent.weather_desc = context.get("weather_info", {}).get("weather_desc") if context.get("weather_info") else None
    intent.destination = context.get("destination")
    intent.travel_days = context.get("travel_days")

    intent.confidence = 0.6  # 规则提取置信度较低
    intent.raw_slots = {"method": "rules"}

    return intent


# ============================================================
# 主入口
# ============================================================

def understand_query(user_input: str) -> QueryIntent:
    """
    理解用户 query 的结构化意图

    双通道：
    1. 主路径：LLM 提取（qwen-flash，泛化能力强）
    2. 备用路径：规则提取（LLM 失败时回退）

    Args:
        user_input: 用户输入文本

    Returns:
        QueryIntent: 结构化意图
    """
    if not user_input or not user_input.strip():
        return QueryIntent(is_fashion=False, confidence=0.0)

    # 1. 检查缓存
    cached = _get_cached_intent(user_input)
    if cached:
        return cached

    # 2. LLM 主路径
    intent = _call_intent_llm(user_input)

    # 3. 失败时回退规则
    if intent is None:
        logger.info(f"[意图理解] LLM 失败，使用规则提取: {user_input[:50]}")
        intent = _extract_intent_by_rules(user_input)

    # 4. 写入缓存
    _set_cached_intent(user_input, intent)

    return intent
