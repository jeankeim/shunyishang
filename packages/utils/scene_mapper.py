"""
场曷映射工具模块
提供场景提取、五行颜色映射等工具函数

Task 03 增强：多维度场景识别（主场景 + 子场景 + 情感倾向）
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
    从用户输入中提取场景关键词（旧版，保持兼容）
    
    Args:
        text: 用户输入文本
    
    Returns:
        Optional[str]: 识别到的场景，未识别返回 None
    """
    result = extract_scene_multidimensional(text)
    return result.get("main_scene")


def extract_scene_multidimensional(text: str) -> Dict:
    """
    Task 03: 多维度场景识别
    
    从用户输入中提取：
    - 主场景（运动、商务、居家等）
    - 子场景（马拉松、瑜伽、游泳等）
    - 情感倾向（积极、消极）
    - 置信度
    
    Args:
        text: 用户输入文本
    
    Returns:
        Dict: {
            "main_scene": "运动",
            "sub_scene": "马拉松",
            "emotion": "积极",
            "confidence": 0.9
        }
    """
    result = {
        "main_scene": None,
        "sub_scene": None,
        "emotion": None,
        "confidence": 0.0
    }
    
    text_lower = text.lower()
    
    # 1. 主场景识别
    main_scene = _extract_main_scene(text_lower)
    if main_scene:
        result["main_scene"] = main_scene
        result["confidence"] = 0.8
    
    # 2. 子场景识别
    sub_scene = _extract_sub_scene(text_lower)
    if sub_scene:
        result["sub_scene"] = sub_scene
        result["confidence"] = max(result["confidence"], 0.9)
    
    # 3. 情感倾向识别
    emotion = _extract_emotion(text_lower)
    if emotion:
        result["emotion"] = emotion
    
    return result


def _extract_main_scene(text: str) -> Optional[str]:
    """提取主场景"""
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
    
    for scene, keywords in scene_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return scene
    
    return None


def _extract_sub_scene(text: str) -> Optional[str]:
    """提取子场景"""
    sub_scene_keywords = {
        "马拉松": ["马拉松", "长跑", "半马", "全马"],
        "瑜伽": ["瑜伽", "yoga"],
        "游泳": ["游泳", "泳池", "海边"],
        "商务出差": ["出差", "商务旅行"],
    }
    
    for sub_scene, keywords in sub_scene_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return sub_scene
    
    return None


def _extract_emotion(text: str) -> Optional[str]:
    """提取情感倾向"""
    positive_words = ["心情很好", "开心", "高兴", "幸运", "好运", "旺运", "漂亮", "好看", "气质"]
    negative_words = ["心情不好", "不顺", "低落", "沮丧", "烦闷", "郁闷"]
    
    if any(word in text for word in positive_words):
        return "积极"
    elif any(word in text for word in negative_words):
        return "消极"
    
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
