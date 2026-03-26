"""
场景映射工具模块
提供场景提取、五行颜色映射等工具函数
"""

from typing import Optional, List, Dict

from packages.utils.wuxing_rules import (
    SCENE_ELEMENT_MAP,
    ELEMENT_COLOR_MAP,
    ELEMENT_MATERIAL_MAP,
    ELEMENT_STYLE_MAP,
    MONTH_SEASON_WUXING,
)


def extract_scene_from_text(text: str) -> Optional[str]:
    """
    从用户输入中提取场景关键词
    
    Args:
        text: 用户输入文本
    
    Returns:
        Optional[str]: 识别到的场景，未识别返回 None
    """
    # 场景关键词映射（扩展匹配）
    scene_keywords = {
        "面试": ["面试", "求职", "应聘", "招聘", "笔试", "复试"],
        "约会": ["约会", "相亲", "见面", "约会穿", "约会去"],
        "日常": ["日常", "平时", "通勤", "上班", "逛街"],
        "商务": ["商务", "谈判", "签约", "合作", "会议", "汇报"],
        "运动": ["运动", "健身", "跑步", "瑜伽", "游泳", "打球"],
        "派对": ["派对", "聚会", "party", "蹦迪", "夜店", "KTV"],
        "居家": ["居家", "在家", "宅家", "休息", "睡觉"],
        "旅行": ["旅行", "旅游", "出差", "度假", "游玩"],
        "婚礼": ["婚礼", "结婚", "婚宴", "参加婚礼", "当伴郎", "当伴娘"],
        "会议": ["会议", "开会", "演讲", "汇报", "展示"],
    }
    
    text_lower = text.lower()
    for scene, keywords in scene_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return scene
    
    return None


def get_scene_elements(scene: str) -> Optional[Dict]:
    """
    获取场景对应的五行
    
    Args:
        scene: 场景名称
    
    Returns:
        Optional[Dict]: 场景五行映射，未找到返回 None
    """
    return SCENE_ELEMENT_MAP.get(scene)


def get_season_element(month: int) -> str:
    """
    根据月份返回当令五行
    
    Args:
        month: 月份（1-12）
    
    Returns:
        str: 当令五行
    """
    return MONTH_SEASON_WUXING.get(month, "土")


def get_color_by_element(element: str) -> List[str]:
    """
    根据五行返回对应颜色关键词
    
    Args:
        element: 五行名称
        
    Returns:
        List[str]: 颜色关键词列表
    """
    return ELEMENT_COLOR_MAP.get(element, [])


def get_material_by_element(element: str) -> List[str]:
    """
    根据五行返回对应材质关键词
    
    Args:
        element: 五行名称
        
    Returns:
        List[str]: 材质关键词列表
    """
    return ELEMENT_MATERIAL_MAP.get(element, [])


def get_style_by_element(element: str) -> List[str]:
    """
    根据五行返回对应款式关键词
    
    Args:
        element: 五行名称
        
    Returns:
        List[str]: 款式关键词列表
    """
    return ELEMENT_STYLE_MAP.get(element, [])


def get_element_by_color(color: str) -> Optional[str]:
    """
    根据颜色反推五行
    
    Args:
        color: 颜色名称
    
    Returns:
        Optional[str]: 五行名称，未找到返回 None
    """
    color_lower = color.lower()
    for element, colors in ELEMENT_COLOR_MAP.items():
        for c in colors:
            if c.lower() == color_lower or color_lower in c.lower():
                return element
    return None


def build_search_query(
    target_elements: List[str],
    scene: Optional[str] = None,
    user_query: str = ""
) -> str:
    """
    构建向量搜索查询文本（增强版）
    
    增强内容：
    - 颜色关键词
    - 材质关键词
    - 款式关键词
    - 场景风格描述
    - 用户原始查询
    
    Args:
        target_elements: 目标五行列表
        scene: 场景名称
        user_query: 用户原始输入
        
    Returns:
        str: 搜索查询文本
    """
    parts = []
    
    # 1. 添加颜色关键词（每个五行取前2个颜色）
    for element in target_elements[:2]:
        colors = get_color_by_element(element)
        if colors:
            parts.extend(colors[:2])
    
    # 2. 添加材质关键词（每个五行取前1个材质）
    for element in target_elements[:2]:
        materials = get_material_by_element(element)
        if materials:
            parts.append(materials[0])
    
    # 3. 添加款式关键词（每个五行取前1个款式）
    for element in target_elements[:2]:
        styles = get_style_by_element(element)
        if styles:
            parts.append(styles[0])
    
    # 4. 添加场景风格描述
    if scene:
        scene_info = get_scene_elements(scene)
        if scene_info:
            parts.append(scene_info.get("desc", ""))
    
    # 5. 添加用户原始查询的关键词
    if user_query:
        parts.append(user_query[:20])
    
    return " ".join(parts)


def get_season_name(month: int) -> str:
    """
    根据月份返回季节名称
    
    Args:
        month: 月份（1-12）
    
    Returns:
        str: 季节名称
    """
    if month in [2, 3, 4]:
        return "春"
    elif month in [5, 6, 7]:
        return "夏"
    elif month in [8, 9, 10]:
        return "秋"
    else:  # 11, 12, 1
        return "冬"
