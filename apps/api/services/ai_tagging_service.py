"""
AI 自动打标服务
分析衣物描述，返回五行属性
"""

import json
import logging
import os
from typing import Dict, Optional, List

from openai import AsyncOpenAI

from apps.api.core.config import settings
from apps.api.services.llm_usage_service import extract_llm_usage

logger = logging.getLogger(__name__)


class AITaggingService:
    """
    AI 自动打标服务
    分析衣物描述，返回五行属性
    支持 AI 自动识别 + 人工兜底
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url
        )
        self.model = settings.qwen_model
        self.vl_model = settings.qwen_vl_model  # 多模态视觉模型（拍照看图）
        self.timeout = 30.0
    
    async def analyze_item(
        self, 
        description: str, 
        image_url: Optional[str] = None
    ) -> Dict:
        """
        分析衣物，返回五行属性（增强版）
        
        Args:
            description: 衣物描述，如 "红色羊毛大衣"
            image_url: 图片URL（可选，未来支持图片识别）
        
        Returns:
            {
                "primary_element": "火",
                "secondary_element": "土",
                "color": "红色",
                "color_element": "火",           # 颜色五行
                "material": "羊毛",
                "material_element": "土",        # 面料五行
                "style": "正式",
                "shape": "长方",                 # 款式形状
                "details": ["V领", "珍珠扣"],    # 款式细节
                "energy_intensity": 0.85,        # 能量强度
                "season": ["秋", "冬"],
                "tags": ["商务", "保暖"],
                "applicable_weather": ["晴", "多云", "阴"],
                "applicable_seasons": ["秋", "冬"],
                "temperature_range": {"min": -5, "max": 15},
                "functionality": ["商务", "日常"],
                "thickness_level": "加厚",
                "suggested_name": "红色羊毛大衣",
                "confidence": 0.85
            }
        """
        
        use_vision = self._is_fetchable_image(image_url)
        prompt = self._build_prompt(description, has_image=use_vision)
        model = self.vl_model if use_vision else self.model

        # 视觉路径：把图片作为多模态输入让模型"看"；文字路径：仅传描述
        if use_vision:
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        else:
            user_content = prompt

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是专业的五行穿搭顾问，擅长分析衣物的五行属性。请严格按照JSON格式输出，不要输出其他内容。"
                    },
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,  # 降低随机性，提高一致性
                response_format={"type": "json_object"},
                timeout=self.timeout
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 风格词表归一化：与场景偏好词表/风格偏好词表保持一致
            result["style"] = self._normalize_style(result.get("style"))
            
            # suggested_name 兜底：AI 有时只识别属性却不给名称，
            # 用"颜色+分类"生成友好名称，避免前端出现"未命名衣物"
            if not (result.get("suggested_name") or "").strip():
                result["suggested_name"] = self._fallback_name(result)
            
            # 计算置信度
            result["confidence"] = self._calculate_confidence(result, description)

            # token 用量随结果带回，供埋点折算成本（调用方 pop 后传 log_llm_usage）
            usage = extract_llm_usage(response)
            if usage:
                result["_llm_usage"] = usage
            
            logger.info(
                f"AI打标成功[{'视觉' if use_vision else '文字'}]: {description} "
                f"-> {result.get('primary_element')} (confidence: {result['confidence']:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"AI打标失败[{'视觉' if use_vision else '文字'}]: {e}")
            # 返回默认值，让用户手动修正
            return self._get_default_result(description, str(e))
    
    @staticmethod
    def _is_fetchable_image(image_url: Optional[str]) -> bool:
        """
        判断 image_url 是否为模型可获取的图片

        仅公网 http(s) URL 或 base64 data URI 才能被远端视觉模型读取；
        本地相对路径等无法获取，退回纯文字打标。
        """
        if not image_url:
            return False
        return image_url.startswith(("http://", "https://", "data:image/"))
    
    def _build_prompt(self, description: str, has_image: bool = False) -> str:
        """构建分析提示词（增强版）

        Args:
            description: 衣物文字描述
            has_image: 是否随消息附带图片（多模态路径），为真时以图为主、文字为辅
        """
        
        if has_image:
            source_hint = (
                "请以图片为主识别这件衣物（颜色/材质/款式/分类等），文字描述仅作补充参考。\n"
                f"用户补充描述（可能为占位或空）: {description}"
            )
        else:
            source_hint = f"衣物描述: {description}"

        prompt = f"""你是一个专业的五行穿搭顾问。请分析这件衣物的五行属性。

{source_hint}

请根据以下规则分析：

1. 颜色五行对照：
   - 红、橙、紫、粉色 → 火
   - 黄、棕、土色、卡其 → 土  
   - 白、金、银、米色 → 金
   - 黑、蓝、灰、藏青 → 水
   - 绿、青、墨绿 → 木

2. 材质五行对照：
   - 丝绸、棉麻、棉布 → 木
   - 皮革、毛呢、灯芯绒 → 土
   - 羽绒、羊毛、针织 → 水或火（视颜色而定）
   - 金属装饰、亮片 → 金
   - 化纤、混纺 → 根据主要成分判断
   - 天然矿石/水晶/玛瑙/玉石 → 根据颜色和质地判断（详见下方饰品规则）

3. 款式五行对照：
   - 正装、西装、职业装 → 金
   - 运动休闲、宽松舒适 → 木
   - 华丽礼服、时尚前卫 → 火
   - 简约基础、经典款 → 水
   - 自然田园、森系 → 土

4. 厚度等级判断：
   - 轻薄：T恤、衬衫、薄裙、手串、吊坠
   - 适中：卫衣、针织衫、风衣
   - 加厚：毛衣、厚外套
   - 厚重：羽绒服、棉服、厚大衣

5. 温度范围估算：
   - 根据 thickness_level 和材质判断适合的温度范围
   - 饰品/文玩类不受温度限制，可填 {{"min": -30, "max": 50}}

6. 能量强度评估：
   - 根据颜色纯度、材质特性评估五行能量强度（0.0-1.0）
   - 纯色、强五行属性材质 → 高能量（0.8-1.0）
   - 混合色、中性材质 → 中等能量（0.5-0.7）
   - 浅色、淡色 → 较低能量（0.3-0.4）
   - 天然矿石/宝石/玉石 → 能量通常较高（0.8-1.0）

7. 款式形状判断：
   - 长方：西装、风衣、大衣
   - 正方：短款外套、夹克
   - 圆形：圆领上衣、斗篷、手串、佛珠、吊坠
   - 三角：V领、下摆扩展款
   - 不规则：设计感强的款式

8. **饰品/文玩专项规则**（重要）：
   - 识别到饰品、手串、佛珠、吊坠、手镯等物品时，category 应为"饰品"或"文玩"
   - 文玩类：佛珠（小叶紫檀/沉香/崖柏/菩提子）、木质手串、蜜蜡
   - 饰品类：水晶、玛瑙、玉石、翡翠、银饰、碧玺、黑曜石
   - **传统文化寓意映射**：
     - 黑曜石 → 静心宁神，水属性
     - 紫水晶 → 智慧开悟，水属性
     - 黄水晶/貔貅 → 纳福寓意，土/金属性
     - 粉水晶/芙蓉石 → 旺桃花人缘，火属性
     - 绿幽灵 → 正财事业，木属性
     - 红玛瑙/南红 → 沉稳安心，火属性
     - 和田玉 → 温润养人，土/金属性
     - 翡翠 → 通灵养性，木属性
     - 银饰 → 解毒安神，金属性
     - 小叶紫檀/沉香/崖柏 → 安神定气，木属性
     - 菩提子 → 开悟增慧，木/金属性
     - 蜜蜡/琥珀 → 温养身心，土属性
   - 饰品/文玩类 functionality 填 ["禅修", "静心", "纳福", "日常", "装饰"] 等

请以 JSON 格式输出分析结果，不要输出其他内容：
{{
    "primary_element": "主五行（金/木/水/火/土之一）",
    "secondary_element": "次五行（可选）",
    "color": "主色调名称",
    "color_element": "颜色对应的五行",
    "material": "材质名称",
    "material_element": "材质对应的五行",
    "style": "风格（必须从以下词表中选一个：商务/知性/简约/优雅/甜美/性感/休闲/运动/街头/森系/文艺/国潮。西装正装→商务，基础百搭→简约或休闲，礼服→优雅，饰品文玩按气质选知性/文艺/简约）",
    "shape": "款式形状（长方/正方/圆形/三角/不规则）",
    "details": ["款式细节1", "款式细节2"],
    "energy_intensity": 0.8,
    "category": "分类（上装/下装/外套/鞋履/配饰/饰品/文玩/裙装/套装/其他）",
    "season": ["适合季节"],
    "tags": ["标签1", "标签2"],
    "applicable_weather": ["适用天气: 晴/多云/阴/雨/雪"],
    "applicable_seasons": ["适用季节: 春/夏/秋/冬"],
    "temperature_range": {{"min": 最低温度, "max": 最高温度}},
    "functionality": ["功能场景: 面试/约会/商务/日常/运动/派对/居家/旅行/禅修/静心/纳福"],
    "thickness_level": "厚度等级: 轻薄/适中/加厚/厚重",
    "suggested_name": "建议名称"
}}"""
        
        return prompt
    
    # 统一风格词表（与 packages/recommendation/config.py:STYLE_KEYWORDS、
    # packages/utils/scene_mapping.py:SCENE_PREFERRED_STYLES 对齐）
    STYLE_VOCAB = {
        "商务", "知性", "简约", "优雅", "甜美", "性感",
        "休闲", "运动", "街头", "森系", "文艺", "国潮",
    }
    # 旧词表/常见越界值 → 统一词表映射
    STYLE_ALIASES = {
        "正式": "商务",
        "职业": "商务",
        "时尚": "街头",
        "潮流": "街头",
        "传统": "国潮",
        "中式": "国潮",
        "禅意": "文艺",
        "复古": "文艺",
        "极简": "简约",
        "基础": "简约",
        "日常": "休闲",
        "户外": "运动",
        "可爱": "甜美",
        "自然": "森系",
        "气质": "优雅",
        "干练": "知性",
    }

    @classmethod
    def _normalize_style(cls, style) -> Optional[str]:
        """将 AI 返回的风格归一化到统一词表；无法归一时返回 None（不参与风格惩罚）"""
        if not style or not isinstance(style, str):
            return None
        style = style.strip()
        if style in cls.STYLE_VOCAB:
            return style
        if style in cls.STYLE_ALIASES:
            return cls.STYLE_ALIASES[style]
        # 模糊包含匹配（如"商务休闲"→取最先出现的词表词）
        hits = [(style.find(v), v) for v in cls.STYLE_VOCAB if v in style]
        if hits:
            return min(hits)[1]
        return None

    @staticmethod
    def _fallback_name(result: Dict) -> str:
        """AI 未返回 suggested_name 时，用"颜色+分类"兜底生成名称"""
        color = (result.get("color") or "").strip()
        if color in ("", "未知"):
            color = ""
        category = (result.get("category") or "").strip()
        name = f"{color}{category}".strip()
        return name or "衣物"

    def _calculate_confidence(self, result: Dict, description: str) -> float:
        """
        计算置信度
        根据返回结果的完整性和描述的匹配度评估
        """
        confidence = 1.0
        
        # 检查关键字段
        required_fields = ["primary_element", "color", "suggested_name"]
        for field in required_fields:
            if not result.get(field):
                confidence -= 0.2
        
        # 检查五行是否有效
        valid_elements = ["金", "木", "水", "火", "土"]
        if result.get("primary_element") not in valid_elements:
            confidence -= 0.3
        
        # 检查描述中是否包含颜色关键词
        color_keywords = ["红", "橙", "黄", "绿", "青", "蓝", "紫", "黑", "白", "灰", "粉", "棕", "卡其", "米"]
        has_color_in_desc = any(c in description for c in color_keywords)
        if has_color_in_desc and result.get("color"):
            confidence += 0.1
        
        # 限制在 0-1 范围
        return max(0.0, min(1.0, confidence))
    
    def _get_default_result(self, description: str, error: str) -> Dict:
        """AI 失败时返回默认结果，允许用户手动修正"""
        return {
            "primary_element": "金",  # 默认五行
            "secondary_element": None,
            "color": "未知",
            "color_element": "金",
            "material": "未知",
            "material_element": "金",
            "style": "休闲",
            "shape": None,
            "details": [],
            "energy_intensity": 0.5,
            "category": None,  # 分类
            "season": ["春", "秋"],
            "tags": ["待确认"],
            "applicable_weather": ["晴", "多云"],
            "applicable_seasons": ["春", "秋"],
            "temperature_range": {"min": 10, "max": 25},
            "functionality": ["日常"],
            "thickness_level": "适中",
            "suggested_name": description[:50] if len(description) > 50 else description,
            "confidence": 0.0,
            "ai_error": error,  # 标记 AI 识别失败
            "needs_manual_review": True  # 需要人工确认
        }
    
    async def batch_analyze(self, descriptions: List[str]) -> List[Dict]:
        """批量分析衣物"""
        results = []
        for desc in descriptions:
            result = await self.analyze_item(desc)
            results.append(result)
        return results


# 单例
ai_tagging_service = AITaggingService()
