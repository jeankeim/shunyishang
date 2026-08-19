"""
五行/材质/风格深度分析规则引擎（批量上传第二阶段）

基于 data/standards/ 的三张归一化映射表（颜色/材质/风格 → 五行），
对衣物的视觉属性做确定性五行归属，并结合用户八字喜用神输出匹配标签与建议文案。

设计约束：
- 纯规则计算，无 LLM 调用：确定性结果、零额外成本、可离线降级
- 喜用神只用于比对标注，严禁篡改用户喜用神数据本身
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# data/standards 目录：与本文件相隔四层（services → api → apps → 项目根）
STANDARDS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "standards"

VALID_ELEMENTS = ("金", "木", "水", "火", "土")

# 主五行计算权重：颜色 > 材质 > 风格
ELEMENT_WEIGHTS = {"color": 0.5, "material": 0.3, "style": 0.2}


class WuxingAnalysisService:
    """五行深度分析规则引擎（单例）"""

    def __init__(self):
        self.color_map: Dict[str, str] = {}
        self.material_map: Dict[str, str] = {}
        self.style_map: Dict[str, str] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """加载三张映射表，构建 值 → 五行 反查字典（重名值先到先得）"""

        def _load(filename: str, list_key: str) -> Dict[str, str]:
            reverse: Dict[str, str] = {}
            try:
                with open(STANDARDS_DIR / filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for element, spec in data.get("mappings", {}).items():
                    if element not in VALID_ELEMENTS:
                        continue
                    for value in spec.get(list_key, []):
                        reverse.setdefault(str(value).strip(), element)
            except Exception as e:
                logger.error(f"五行映射表加载失败 {filename}: {e}")
            return reverse

        self.color_map = _load("wuxing_color_mapping.json", "colors")
        self.material_map = _load("wuxing_material_mapping.json", "materials")
        self.style_map = _load("wuxing_style_mapping.json", "styles")
        logger.info(
            f"五行映射表加载完成: 颜色={len(self.color_map)} "
            f"材质={len(self.material_map)} 风格={len(self.style_map)}"
        )

    # ---------- 单维度查表 ----------

    def lookup_color(self, color: Optional[str]) -> Optional[str]:
        """颜色 → 五行（查不到返回 None，保留 AI 原值由用户确认）"""
        return self.color_map.get((color or "").strip()) if color else None

    def lookup_material(self, material: Optional[str]) -> Optional[str]:
        """材质 → 五行"""
        return self.material_map.get((material or "").strip()) if material else None

    def lookup_style(self, style: Optional[str]) -> Optional[str]:
        """风格 → 五行"""
        return self.style_map.get((style or "").strip()) if style else None

    # ---------- 综合分析 ----------

    def analyze_item(
        self,
        item: Dict,
        xiyong_elements: Optional[List[str]] = None,
        avoid_elements: Optional[List[str]] = None,
    ) -> Dict:
        """
        单件衣物五行深度分析

        Args:
            item: 含 color/material/style 基础属性（来自第一阶段识别或用户编辑）
            xiyong_elements: 用户喜用神（只读比对，严禁修改）
            avoid_elements: 用户忌讳五行（来自 users.bazi.avoid_elements，可为空）

        Returns:
            {primary_element, secondary_element, color_element, material_element,
             style_element, xiyong_match, xiyong_advice}
        """
        color_element = self.lookup_color(item.get("color"))
        material_element = self.lookup_material(item.get("material"))
        style_element = self.lookup_style(item.get("style"))

        # 主五行：三维五行按权重累加（同一五行多维度命中会叠加），取最高分
        scores: Dict[str, float] = {}
        for element, weight in (
            (color_element, ELEMENT_WEIGHTS["color"]),
            (material_element, ELEMENT_WEIGHTS["material"]),
            (style_element, ELEMENT_WEIGHTS["style"]),
        ):
            if element:
                scores[element] = scores.get(element, 0.0) + weight

        primary_element: Optional[str] = None
        secondary_element: Optional[str] = None
        if scores:
            # 同分时按 颜色 > 材质 > 风格 优先（sorted 稳定 + 分数降序）
            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            primary_element = ranked[0][0]
            if len(ranked) > 1:
                secondary_element = ranked[1][0]
        else:
            # 三维全部查表未命中：兜底默认值，前端可编辑修正
            primary_element = "金"

        # 喜用神比对（只比对，不修改喜用神数据）
        xiyong_match: Optional[str] = None
        xiyong_advice: Optional[str] = None
        if xiyong_elements:
            xiyong_text = "、".join(xiyong_elements)
            if primary_element in xiyong_elements:
                xiyong_match = "喜用匹配"
                xiyong_advice = f"主五行为{primary_element}，正是您的喜用神（{xiyong_text}），宜常穿以助运势。"
            elif avoid_elements and primary_element in avoid_elements:
                xiyong_match = "忌讳五行"
                xiyong_advice = f"主五行为{primary_element}，属忌讳五行，建议搭配{xiyong_text}属性单品调和。"
            else:
                xiyong_match = "中性"
                xiyong_advice = f"主五行为{primary_element}，与命理中性相合，搭配{xiyong_text}属性单品更佳。"

        return {
            "primary_element": primary_element,
            "secondary_element": secondary_element,
            "color_element": color_element,
            "material_element": material_element,
            "style_element": style_element,
            "xiyong_match": xiyong_match,
            "xiyong_advice": xiyong_advice,
        }

    def analyze_batch(
        self,
        items: List[Dict],
        xiyong_elements: Optional[List[str]] = None,
        avoid_elements: Optional[List[str]] = None,
    ) -> List[Dict]:
        """批量分析（与输入同序返回）"""
        return [self.analyze_item(it, xiyong_elements, avoid_elements) for it in items]


# 单例
wuxing_analysis_service = WuxingAnalysisService()
