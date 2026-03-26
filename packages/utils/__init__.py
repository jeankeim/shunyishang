"""
WuXing AI Stylist - 工具函数模块
"""
from packages.utils.bazi_calculator import (
    calculate_bazi,
    infer_elements_from_text,
    merge_recommendations,
)
from packages.utils.scene_mapper import (
    extract_scene_from_text,
    get_scene_elements,
    get_color_by_element,
)

__all__ = [
    "calculate_bazi",
    "infer_elements_from_text",
    "merge_recommendations",
    "extract_scene_from_text",
    "get_scene_elements",
    "get_color_by_element",
]
