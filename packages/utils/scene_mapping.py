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
        # 饰品/文玩在运动中存在安全隐患且不合场景（bad case：健身场景推荐木戒指）
        "excluded_categories": ["外套", "配饰", "裙装", "饰品", "文玩"],
        "preferred_functionality": ["透气", "速干", "运动", "弹性"],
        "excluded_keywords": ["风衣", "大衣", "围巾", "西装", "礼服", "睡衣", "拖鞋", "卫衣", "毛衣", "棉袄", "羽绒服",
                              "真丝", "丝绸", "汉服", "连衣裙", "长裙", "领带", "方巾", "高跟鞋", "皮鞋", "皮裙",
                              "雪纺", "蕾丝", "扎染"],
        "preferred_thickness": ["轻薄", "极薄"],
        "temperature_range": {"min": 15, "max": 35},
    },
    "商务": {
        "description": "商务会议、谈判、签约、汇报等正式场合",
        "preferred_categories": ["上装", "下装", "鞋履"],
        "excluded_categories": [],
        "preferred_functionality": ["正式", "职业", "抗皱"],
        "excluded_keywords": ["运动裤", "睡衣", "泳衣", "拖鞋", "短裤", "T恤", "帆布鞋"],
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
        "excluded_keywords": ["运动裤", "睡衣", "泳衣", "拖鞋", "短裤", "T恤", "帆布鞋", "风衣"],
        "preferred_thickness": ["适中", "中厚"],
        "temperature_range": {"min": 10, "max": 25},
    },
    "婚礼": {
        "description": "婚礼、婚宴、当伴郎/伴娘",
        "preferred_categories": ["上装", "下装", "裙装", "鞋履", "配饰"],
        "excluded_categories": [],
        "preferred_functionality": ["优雅", "正式", "时尚"],
        "excluded_keywords": ["运动裤", "睡衣", "拖鞋", "泳衣", "短裤",
                              "T恤", "T 恤", "运动鞋", "跑鞋", "扎染", "卫衣", "帽衫", "帆布鞋", "风衣"],
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
        "description": "旅行、旅游、度假",
        "preferred_categories": ["上装", "下装", "鞋履", "外套"],
        "excluded_categories": [],
        "preferred_functionality": ["舒适", "轻便", "百搭"],
        "excluded_keywords": ["睡衣", "泳衣", "拖鞋", "领带", "礼服", "正装", "羽绒服", "棉袄"],
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
    "出差": {
        "description": "商务出差，需要正式且轻便的穿搭",
        "preferred_categories": ["上装", "下装", "鞋履", "外套"],
        "excluded_categories": [],
        "preferred_functionality": ["抗皱", "轻便", "百搭", "正式"],
        "excluded_keywords": ["睡衣", "泳衣", "拖鞋", "礼服", "运动鞋", "跑鞋", "领带", "羽绒服", "棉袄", "大衣"],
        "preferred_thickness": ["轻薄", "适中"],
        "temperature_range": {"min": 5, "max": 30},
    },
    "度假": {
        "description": "海边或山区度假，轻松休闲",
        "preferred_categories": ["上装", "下装", "鞋履", "裙装", "配饰"],
        "excluded_categories": [],
        "preferred_functionality": ["防晒", "速干", "舒适", "休闲"],
        "excluded_keywords": ["西装", "礼服", "正装", "领带", "高跟鞋", "皮鞋", "羽绒服", "棉袄", "大衣", "丝绸", "方巾"],
        "preferred_thickness": ["轻薄", "极薄"],
        "temperature_range": {"min": 15, "max": 35},
    },
    "户外探险": {
        "description": "徒步、登山、露营等户外探险活动",
        "preferred_categories": ["上装", "下装", "鞋履", "外套"],
        "excluded_categories": [],
        "preferred_functionality": ["防水", "耐磨", "保暖", "透气"],
        "excluded_keywords": ["睡衣", "礼服", "高跟鞋", "拖鞋", "泳衣"],
        "preferred_thickness": ["适中", "中厚"],
        "temperature_range": {"min": -10, "max": 30},
    },
}


# ============================================================
# 场景 → 适宜风格映射
# ============================================================
# 定义各场景下得体的服装风格。用于场景适配评分中的“风格得体度”软信号，
# 以及推荐多样性中的“场景风格保障”，避免推荐风格与场合明显冲突的单品
# （例如给「约会」推「运动」风、给「商务」推「街头」风）。
# 点缀类（饰品/文玩/配饰）不分风格，视为始终得体。
SCENE_PREFERRED_STYLES: Dict[str, List[str]] = {
    "商务": ["商务", "知性", "简约", "优雅"],
    "面试": ["商务", "知性", "简约"],
    "约会": ["优雅", "甜美", "性感", "休闲"],
    "运动": ["运动", "休闲"],
    "居家": ["休闲", "简约", "森系"],
    "婚礼": ["优雅", "商务", "知性"],
    "派对": ["街头", "性感", "优雅", "甜美"],
    "旅行": ["休闲", "运动", "简约"],
    "出差": ["商务", "休闲", "简约"],
    "度假": ["休闲", "甜美", "森系", "运动"],
    "户外探险": ["运动", "休闲"],
}

# 点缀类品类：不受场景风格约束（配饰/饰品/文玩任何场合皆可点缀）
SCENE_STYLE_NEUTRAL_CATEGORIES = {"饰品", "文玩", "配饰"}


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
    "海边度假": {
        "parent_scene": "度假",
        "extra_functionality_bonus": {"防晒": 0.2, "速干": 0.15},
        "extra_excluded_keywords": ["羽绒服", "棉袄", "大衣", "毛衣"],
        "description": "海边度假，防晒速干为加分项",
    },
    "温泉旅行": {
        "parent_scene": "度假",
        "extra_functionality_bonus": {"舒适": 0.2, "柔软": 0.15},
        "description": "温泉旅行，舒适柔软为加分项",
    },
    "徒步登山": {
        "parent_scene": "户外探险",
        "extra_functionality_bonus": {"防水": 0.15, "耐磨": 0.15, "保暖": 0.1},
        "extra_excluded_keywords": ["高跟鞋", "拖鞋", "裙装"],
        "description": "徒步登山，需要防水耐磨保暖",
    },
    "多天出差": {
        "parent_scene": "出差",
        "extra_functionality_bonus": {"抗皱": 0.15, "百搭": 0.15},
        "extra_excluded_keywords": ["厚重", "加厚", "羽绒服", "棉袄"],
        "description": "多天出差，抗皱百搭，排除厚重衣物",
    },
    "滑雪旅行": {
        "parent_scene": "户外探险",
        "extra_functionality_bonus": {"保暖": 0.2, "防水": 0.15},
        "extra_excluded_keywords": ["短袖", "短裤", "凉鞋", "拖鞋"],
        "description": "滑雪旅行，保暖防水为加分项",
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


def get_scene_preferred_styles(scene: str) -> Optional[List[str]]:
    """
    获取场景适宜风格列表

    Returns:
        风格列表；未定义风格规则的场景（如日常/会议）返回 None，
        表示不对风格做限制
    """
    return SCENE_PREFERRED_STYLES.get(scene)


def is_style_scene_appropriate(item: Dict, scene: str) -> bool:
    """
    判断物品风格是否适合场景

    规则（与评估器 _is_scene_appropriate 保持一致）：
    - 点缀类（配饰/饰品/文玩）始终得体
    - 未定义风格规则的场景（返回 None）不做限制，视为得体
    - 物品无风格信息时不惩罚（真实 DB 物品可能缺 style 字段）
    - 其余情况：风格命中场景适宜风格列表即得体
    """
    category = item.get("category", "")
    if category in SCENE_STYLE_NEUTRAL_CATEGORIES:
        return True
    preferred = SCENE_PREFERRED_STYLES.get(scene)
    if not preferred:
        return True
    style = item.get("style", "")
    if not style:
        return True
    return style in preferred


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
        except Exception:
            pass
    elif isinstance(functionality, dict):
        # 如果是字典，按原逻辑处理
        for func in rules["preferred_functionality"]:
            if functionality.get(func) is True or functionality.get(func) == "true":
                current_bonus += 0.05
    
    # 4. 关键词扣分（加强惩罚：每个匹配扣0.5，确保不适合的物品不会出现在推荐中）
    item_name = item.get("name") or ""
    for keyword in rules["excluded_keywords"]:
        if keyword in item_name:
            current_bonus -= 0.5
    
    # 5. 厚度加分
    thickness = item.get("thickness_level", "")
    if thickness in rules["preferred_thickness"]:
        current_bonus += 0.05

    # 5.5 风格-场景得体度（软信号）
    # 仅在物品有 style 且该场景定义了风格规则、且非点缀类时生效，
    # 使场景明显不搭的风格（如约会推运动风）排序下沉，但不硬排除。
    # 惩罚加重至 -0.3：原 -0.15 在 scene 权重 0.15~0.2 下差异过小，
    # 无法将风格冲突单品压到得体候选之下（评估发现 38% 场景风格冲突）
    style = item.get("style", "")
    preferred_styles = SCENE_PREFERRED_STYLES.get(scene)
    if style and preferred_styles and category not in SCENE_STYLE_NEUTRAL_CATEGORIES:
        if style in preferred_styles:
            current_bonus += 0.1
        else:
            current_bonus -= 0.3
    
    # 6. 温度范围匹配（兼容中文键“最低/最高”和英文键“min/max”）
    temp_range = item.get("temperature_range")
    if temp_range and "temperature_range" in rules:
        try:
            if isinstance(temp_range, str):
                import json
                temp_range = json.loads(temp_range)
            
            # 兼容两种键名格式（None 值回退到默认值）
            item_min = temp_range.get("最低") or temp_range.get("min") or 0
            item_max = temp_range.get("最高") or temp_range.get("max") or 50
            scene_min = rules["temperature_range"].get("最低") or rules["temperature_range"].get("min") or 0
            scene_max = rules["temperature_range"].get("最高") or rules["temperature_range"].get("max") or 50
            
            # 计算重叠度
            overlap_min = max(item_min, scene_min)
            overlap_max = min(item_max, scene_max)
            if overlap_max > overlap_min:
                current_bonus += 0.1
        except Exception:
            pass
    
    # 7. 子场景特殊规则
    if sub_scene:
        sub_rules = get_sub_scene_rules(sub_scene)
        if sub_rules:
            # 子场景额外类别加分
            if "preferred_categories" in sub_rules:
                if category in sub_rules["preferred_categories"]:
                    current_bonus += 0.1

            # 额外功能加分
            for func, bonus in sub_rules.get("extra_functionality_bonus", {}).items():
                # 处理 functionality 可能是列表或字典的情况
                if isinstance(functionality, list):
                    if func in functionality:
                        current_bonus += bonus
                elif isinstance(functionality, dict):
                    if functionality.get(func) is True or functionality.get(func) == "true":
                        current_bonus += bonus
            
            # 额外关键词扣分（加强惩罚）
            for keyword in sub_rules.get("extra_excluded_keywords", []):
                if keyword in item_name:
                    current_bonus -= 0.5
    
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
