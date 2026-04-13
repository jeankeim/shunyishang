"""
场景-功能映射表
定义各场景下的推荐规则（软过滤配置）

用于场景适配评分，替代硬编码在 nodes.py 中的规则
"""

from typing import Dict, List, Optional


# ============================================================
# 场景映射配置
# ============================================================

SCENE_MAPPING: Dict[str, Dict] = {
    "运动": {
        "description": "运动健身、跑步、瑜伽、打球等",
        "preferred_categories": ["鞋履", "下装", "上装"],
        "excluded_categories": ["外套", "配饰"],  # 不包含泳装
        "preferred_functionality": ["透气", "速干", "运动", "弹性"],
        "excluded_keywords": ["风衣", "大衣", "围巾", "西装", "礼服", "睡衣", "拖鞋", "卫衣", "毛衣", "棉袄", "羽绒服"],  # 不包含泳衣、泳裤
        "preferred_thickness": ["轻薄", "极薄"],
        "temperature_range": {"min": 15, "max": 35},
    },
    "商务": {
        "description": "商务会议、谈判、签约、汇报等正式场合",
        "preferred_categories": ["上装", "下装", "鞋履"],
        "excluded_categories": [],
        "preferred_functionality": ["正式", "职业", "抗皱"],
        "excluded_keywords": ["运动裤", "睡衣", "泳衣", "拖鞋", "短裤", "T恤"],
        "preferred_thickness": ["适中", "中厚"],
        "temperature_range": {"min": 10, "max": 25},
    },
    "居家": {
        "description": "在家休息、宅家、睡觉",
        "preferred_categories": ["上装", "下装"],
        "excluded_categories": ["外套", "鞋履"],
        "preferred_functionality": ["舒适", "休闲", "柔软"],
        "excluded_keywords": ["西装", "礼服", "高跟鞋", "正装"],
        "preferred_thickness": ["轻薄", "适中"],
        "temperature_range": {"min": 18, "max": 28},
    },
    "约会": {
        "description": "约会、相亲、见面",
        "preferred_categories": ["上装", "下装", "裙装", "鞋履", "配饰"],
        "excluded_categories": [],
        "preferred_functionality": ["时尚", "优雅", "修身"],
        "excluded_keywords": ["睡衣", "运动裤", "泳衣", "拖鞋"],
        "preferred_thickness": ["轻薄", "适中"],
        "temperature_range": {"min": 15, "max": 30},
    },
    "面试": {
        "description": "面试、求职、应聘",
        "preferred_categories": ["上装", "下装", "鞋履"],
        "excluded_categories": [],
        "preferred_functionality": ["正式", "职业", "抗皱"],
        "excluded_keywords": ["运动裤", "睡衣", "拖鞋", "泳衣", "短裤", "T恤"],
        "preferred_thickness": ["适中", "中厚"],
        "temperature_range": {"min": 10, "max": 25},
    },
    "婚礼": {
        "description": "婚礼、婚宴、当伴郎/伴娘",
        "preferred_categories": ["上装", "下装", "裙装", "鞋履", "配饰"],
        "excluded_categories": [],
        "preferred_functionality": ["优雅", "正式", "时尚"],
        "excluded_keywords": ["运动裤", "睡衣", "拖鞋", "泳衣", "短裤"],
        "preferred_thickness": ["适中"],
        "temperature_range": {"min": 15, "max": 30},
    },
    "派对": {
        "description": "派对、聚会、party、夜店",
        "preferred_categories": ["上装", "下装", "裙装", "鞋履", "配饰"],
        "excluded_categories": [],
        "preferred_functionality": ["时尚", "个性", "亮眼"],
        "excluded_keywords": ["睡衣", "运动裤", "泳衣", "正装"],
        "preferred_thickness": ["轻薄", "适中"],
        "temperature_range": {"min": 15, "max": 30},
    },
    "旅行": {
        "description": "旅行、旅游、出差、度假",
        "preferred_categories": ["上装", "下装", "鞋履", "外套"],
        "excluded_categories": [],
        "preferred_functionality": ["舒适", "轻便", "百搭"],
        "excluded_keywords": ["睡衣", "泳衣", "拖鞋"],
        "preferred_thickness": ["轻薄", "适中"],
        "temperature_range": {"min": 10, "max": 30},
    },
    "日常": {
        "description": "日常通勤、上班、逛街",
        "preferred_categories": ["上装", "下装", "鞋履"],
        "excluded_categories": [],
        "preferred_functionality": ["舒适", "休闲", "百搭"],
        "excluded_keywords": ["睡衣", "泳衣", "礼服"],
        "preferred_thickness": ["轻薄", "适中", "中厚"],
        "temperature_range": {"min": 5, "max": 35},
    },
    "会议": {
        "description": "会议、开会、演讲、汇报",
        "preferred_categories": ["上装", "下装", "鞋履"],
        "excluded_categories": [],
        "preferred_functionality": ["正式", "职业", "抗皱"],
        "excluded_keywords": ["运动裤", "睡衣", "拖鞋", "泳衣", "短裤"],
        "preferred_thickness": ["适中", "中厚"],
        "temperature_range": {"min": 10, "max": 25},
    },
}


# ============================================================
# 子场景特殊规则
# ============================================================

SUB_SCENE_RULES: Dict[str, Dict] = {
    "马拉松": {
        "parent_scene": "运动",
        "extra_functionality_bonus": {"弹性": 0.15, "透气": 0.15, "减震": 0.1},
        "extra_excluded_keywords": ["厚重", "加厚", "羊毛", "棉袄", "泳衣", "泳裤", "泳装", "睡衣", "卫衣", "毛衣", "羽绒服"],
        "description": "马拉松长跑，需要极强的透气性和弹性",
    },
    "瑜伽": {
        "parent_scene": "运动",
        "extra_functionality_bonus": {"弹性": 0.2, "柔软": 0.15},
        "preferred_categories": ["上装", "下装"],
        "description": "瑜伽运动，需要高弹性和柔软度",
    },
    "游泳": {
        "parent_scene": "运动",
        "extra_functionality_bonus": {"防水": 0.3},
        "preferred_categories": ["泳装", "上装", "下装"],
        "excluded_categories": ["外套", "鞋履"],
        "extra_excluded_keywords": ["高跟鞋", "皮鞋", "靴子", "风衣", "大衣", "羽绒服", "跑鞋", "工装裤", "旗袍", "皮裙", "牛仔裤"],
        "description": "游泳运动，需要防水功能",
    },
    "商务出差": {
        "parent_scene": "商务",
        "extra_functionality_bonus": {"轻便": 0.15, "抗皱": 0.15},
        "extra_excluded_keywords": ["厚重", "加厚"],
        "description": "商务出差，需要正式且轻便",
    },
}


# ============================================================
# 工具函数
# ============================================================

def get_scene_rules(scene: str) -> Optional[Dict]:
    """
    获取场景规则配置
    
    Args:
        scene: 场景名称
    
    Returns:
        场景规则字典，未找到返回 None
    """
    return SCENE_MAPPING.get(scene)


def get_sub_scene_rules(sub_scene: str) -> Optional[Dict]:
    """
    获取子场景特殊规则
    
    Args:
        sub_scene: 子场景名称
    
    Returns:
        子场景规则字典，未找到返回 None
    """
    return SUB_SCENE_RULES.get(sub_scene)


def calculate_scene_match_score(item: Dict, scene: str, sub_scene: Optional[str] = None) -> float:
    """
    计算物品与场景的匹配度
    
    Args:
        item: 衣物信息字典（需包含 category, name, functionality, thickness_level 等字段）
        scene: 主场景名称
        sub_scene: 子场景名称（可选）
    
    Returns:
        float: 0.0-1.0 的匹配度分数
    """
    rules = get_scene_rules(scene)
    if not rules:
        return 0.5  # 未知场景返回基础分
    
    # 合并父子场景的排除类别（硬排除）
    excluded_categories = set(rules.get("excluded_categories", []))
    if sub_scene:
        sub_rules = get_sub_scene_rules(sub_scene)
        if sub_rules and "excluded_categories" in sub_rules:
            excluded_categories.update(sub_rules["excluded_categories"])
    
    # 硬排除：类别在排除列表中，直接返回0.0
    category = item.get("category", "")
    if category in excluded_categories:
        return 0.0
    
    score = 0.5  # 基础分数
    max_bonus = 0.5
    current_bonus = 0.0
    
    # 1. 类别加分
    if category in rules["preferred_categories"]:
        current_bonus += 0.1
    
    # 2. 类别扣分
    if category in rules["excluded_categories"]:
        current_bonus -= 0.2
    
    # 3. 功能加分
    functionality = item.get("functionality", {})
    
    # 处理 functionality 可能是列表或字典的情况
    if isinstance(functionality, list):
        # 如果是列表，检查是否有匹配的功能
        for func in rules["preferred_functionality"]:
            if func in functionality:
                current_bonus += 0.05
    elif isinstance(functionality, str):
        # 如果是字符串，尝试解析为 JSON
        import json
        try:
            functionality = json.loads(functionality)
            for func in rules["preferred_functionality"]:
                if functionality.get(func) is True or functionality.get(func) == "true":
                    current_bonus += 0.05
        except:
            pass
    elif isinstance(functionality, dict):
        # 如果是字典，按原逻辑处理
        for func in rules["preferred_functionality"]:
            if functionality.get(func) is True or functionality.get(func) == "true":
                current_bonus += 0.05
    
    # 4. 关键词扣分
    item_name = item.get("name", "")
    for keyword in rules["excluded_keywords"]:
        if keyword in item_name:
            current_bonus -= 0.15
    
    # 5. 厚度加分
    thickness = item.get("thickness_level", "")
    if thickness in rules["preferred_thickness"]:
        current_bonus += 0.05
    
    # 6. 温度范围匹配
    temp_range = item.get("temperature_range")
    if temp_range and "temperature_range" in rules:
        try:
            if isinstance(temp_range, str):
                import json
                temp_range = json.loads(temp_range)
            
            item_min = temp_range.get("min", 0)
            item_max = temp_range.get("max", 50)
            scene_min = rules["temperature_range"]["min"]
            scene_max = rules["temperature_range"]["max"]
            
            # 计算重叠度
            overlap_min = max(item_min, scene_min)
            overlap_max = min(item_max, scene_max)
            if overlap_max > overlap_min:
                current_bonus += 0.1
        except:
            pass
    
    # 7. 子场景特殊规则
    if sub_scene:
        sub_rules = get_sub_scene_rules(sub_scene)
        if sub_rules:
            # 额外功能加分
            for func, bonus in sub_rules.get("extra_functionality_bonus", {}).items():
                # 处理 functionality 可能是列表或字典的情况
                if isinstance(functionality, list):
                    if func in functionality:
                        current_bonus += bonus
                elif isinstance(functionality, dict):
                    if functionality.get(func) is True or functionality.get(func) == "true":
                        current_bonus += bonus
            
            # 额外关键词扣分
            for keyword in sub_rules.get("extra_excluded_keywords", []):
                if keyword in item_name:
                    current_bonus -= 0.2
    
    # 限制在 0.0-1.0 范围内
    return max(0.0, min(1.0, score + current_bonus))


def get_available_scenes() -> List[str]:
    """
    获取所有可用的场景列表
    
    Returns:
        场景名称列表
    """
    return list(SCENE_MAPPING.keys())


def get_available_sub_scenes() -> List[str]:
    """
    获取所有可用的子场景列表
    
    Returns:
        子场景名称列表
    """
    return list(SUB_SCENE_RULES.keys())
