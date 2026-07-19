"""
测试数据生成器

生成：
1. 标准化物品池（120件，覆盖所有分类/五行/厚度/风格）
2. 200个虚拟用户（不同八字/审美/性别）
3. 2000-4000个测试用例（覆盖简单/中等/高复杂度场景）
"""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# 固定随机种子确保可复现
random.seed(42)

# ============================================================
# 五行基础数据
# ============================================================
FIVE_ELEMENTS = ["金", "木", "水", "火", "土"]

# 五行相生关系：金生水、水生木、木生火、火生土、土生金
ELEMENT_GENERATES = {
    "金": "水", "水": "木", "木": "火", "火": "土", "土": "金"
}

# 五行相克关系：金克木、木克土、土克水、水克火、火克金
ELEMENT_OVERCOMES = {
    "金": "木", "木": "土", "土": "水", "水": "火", "火": "金"
}

# 五行对应颜色
ELEMENT_COLORS = {
    "金": ["白色", "银色", "金色"],
    "木": ["绿色", "青色", "翠色"],
    "水": ["黑色", "蓝色", "深蓝"],
    "火": ["红色", "紫色", "橙色"],
    "土": ["黄色", "棕色", "卡其色"],
}

# 日主五行与喜用神映射（简化版，实际需根据八字强弱判断）
DAY_MASTER_PATTERNS = [
    # (日主, 身强/身弱, 喜用神列表, 忌神列表)
    ("甲木", "身强", ["火", "土", "金"], ["水", "木"]),
    ("甲木", "身弱", ["水", "木"], ["火", "土", "金"]),
    ("乙木", "身强", ["火", "土", "金"], ["水", "木"]),
    ("乙木", "身弱", ["水", "木"], ["火", "土", "金"]),
    ("丙火", "身强", ["土", "金", "水"], ["木", "火"]),
    ("丙火", "身弱", ["木", "火"], ["土", "金", "水"]),
    ("丁火", "身强", ["土", "金", "水"], ["木", "火"]),
    ("丁火", "身弱", ["木", "火"], ["土", "金", "水"]),
    ("戊土", "身强", ["金", "水", "木"], ["火", "土"]),
    ("戊土", "身弱", ["火", "土"], ["金", "水", "木"]),
    ("己土", "身强", ["金", "水", "木"], ["火", "土"]),
    ("己土", "身弱", ["火", "土"], ["金", "水", "木"]),
    ("庚金", "身强", ["水", "木", "火"], ["土", "金"]),
    ("庚金", "身弱", ["土", "金"], ["水", "木", "火"]),
    ("辛金", "身强", ["水", "木", "火"], ["土", "金"]),
    ("辛金", "身弱", ["土", "金"], ["水", "木", "火"]),
    ("壬水", "身强", ["木", "火", "土"], ["金", "水"]),
    ("壬水", "身弱", ["金", "水"], ["木", "火", "土"]),
    ("癸水", "身强", ["木", "火", "土"], ["金", "水"]),
    ("癸水", "身弱", ["金", "水"], ["木", "火", "土"]),
]


# ============================================================
# 物品池生成
# ============================================================

# 物品模板：(分类, 名称模板, 适用厚度, 适用季节, 风格关键词)
ITEM_TEMPLATES = [
    # 上装
    ("上装", "简约纯色T恤", ["轻薄", "极薄"], ["春", "夏", "秋"], ["简约", "休闲"]),
    ("上装", "商务衬衫", ["轻薄", "适中"], ["春", "夏", "秋"], ["商务", "知性"]),
    ("上装", "运动速干T恤", ["极薄", "轻薄"], ["夏"], ["运动"]),
    ("上装", "针织毛衣", ["中厚"], ["秋", "冬"], ["文艺", "休闲"]),
    ("上装", "卫衣", ["中厚"], ["春", "秋", "冬"], ["休闲", "街头"]),
    ("上装", "丝绸衬衫", ["轻薄"], ["春", "夏"], ["优雅", "知性"]),
    ("上装", "国潮刺绣上衣", ["适中"], ["春", "秋"], ["国潮"]),
    ("上装", "蕾丝甜美上衣", ["轻薄"], ["春", "夏"], ["甜美"]),
    ("上装", "修身打底衫", ["轻薄", "适中"], ["春", "秋", "冬"], ["简约", "性感"]),
    ("上装", "宽松oversize卫衣", ["中厚"], ["秋", "冬"], ["街头", "休闲"]),
    ("上装", "棉麻文艺衬衫", ["轻薄"], ["春", "夏", "秋"], ["文艺", "森系"]),
    ("上装", "西装外套内搭", ["适中"], ["春", "秋", "冬"], ["商务", "知性"]),
    # 下装
    ("下装", "休闲直筒裤", ["适中"], ["春", "秋"], ["休闲", "简约"]),
    ("下装", "商务西裤", ["适中"], ["春", "夏", "秋", "冬"], ["商务", "知性"]),
    ("下装", "运动短裤", ["极薄", "轻薄"], ["夏"], ["运动"]),
    ("下装", "牛仔裤", ["适中", "中厚"], ["春", "秋", "冬"], ["休闲", "街头"]),
    ("下装", "阔腿裤", ["适中"], ["春", "夏", "秋"], ["休闲", "优雅"]),
    ("下装", "修身铅笔裤", ["适中"], ["春", "秋", "冬"], ["商务", "性感"]),
    ("下装", "棉麻休闲裤", ["轻薄"], ["春", "夏"], ["文艺", "森系"]),
    ("下装", "加绒保暖裤", ["厚重"], ["冬"], ["休闲"]),
    # 裙装
    ("裙装", "优雅连衣裙", ["适中"], ["春", "夏", "秋"], ["优雅", "知性"]),
    ("裙装", "甜美碎花裙", ["轻薄"], ["春", "夏"], ["甜美", "森系"]),
    ("裙装", "商务套裙", ["适中"], ["春", "夏", "秋"], ["商务"]),
    ("裙装", "运动短裙", ["轻薄"], ["夏"], ["运动"]),
    ("裙装", "国潮汉服裙", ["适中", "中厚"], ["春", "秋"], ["国潮"]),
    ("裙装", "修身包臀裙", ["适中"], ["春", "秋"], ["性感", "商务"]),
    ("裙装", "宽松棉麻长裙", ["轻薄"], ["夏"], ["文艺", "森系"]),
    ("裙装", "蕾丝公主裙", ["适中"], ["春", "夏"], ["甜美"]),
    # 外套
    ("外套", "商务西装外套", ["中厚"], ["春", "秋", "冬"], ["商务", "知性"]),
    ("外套", "休闲夹克", ["中厚"], ["春", "秋"], ["休闲", "街头"]),
    ("外套", "运动风衣", ["轻薄", "适中"], ["春", "夏", "秋"], ["运动"]),
    ("外套", "羽绒服", ["厚重"], ["冬"], ["休闲"]),
    ("外套", "毛呢大衣", ["厚重"], ["秋", "冬"], ["优雅", "商务"]),
    ("外套", "牛仔外套", ["中厚"], ["春", "秋"], ["街头", "休闲"]),
    ("外套", "针织开衫", ["中厚"], ["春", "秋"], ["文艺", "休闲"]),
    ("外套", "皮衣", ["中厚"], ["春", "秋"], ["街头", "性感"]),
    ("外套", "防晒衣", ["极薄"], ["夏"], ["运动", "休闲"]),
    ("外套", "国潮盘扣外套", ["中厚"], ["春", "秋"], ["国潮"]),
    # 配饰
    ("配饰", "商务领带", ["轻薄"], ["春", "夏", "秋", "冬"], ["商务"]),
    ("配饰", "丝巾", ["轻薄"], ["春", "秋"], ["优雅", "知性"]),
    ("配饰", "运动头带", ["极薄"], ["夏"], ["运动"]),
    ("配饰", "围巾", ["中厚", "厚重"], ["秋", "冬"], ["休闲", "文艺"]),
    ("配饰", "腰带", ["轻薄"], ["春", "夏", "秋", "冬"], ["商务", "休闲"]),
    # 饰品
    ("饰品", "金属项链", ["轻薄"], ["春", "夏", "秋", "冬"], ["简约", "优雅"]),
    ("饰品", "木质手串", ["轻薄"], ["春", "夏", "秋", "冬"], ["文艺", "国潮"]),
    ("饰品", "玉石吊坠", ["轻薄"], ["春", "夏", "秋", "冬"], ["国潮", "优雅"]),
    ("饰品", "珍珠耳环", ["轻薄"], ["春", "夏", "秋", "冬"], ["优雅", "知性"]),
    ("饰品", "银饰手链", ["轻薄"], ["春", "夏", "秋", "冬"], ["简约", "街头"]),
    ("饰品", "水晶胸针", ["轻薄"], ["春", "夏", "秋", "冬"], ["甜美", "优雅"]),
    # 文玩
    ("文玩", "檀木佛珠", ["轻薄"], ["春", "夏", "秋", "冬"], ["国潮", "文艺"]),
    ("文玩", "核桃手把件", ["轻薄"], ["春", "夏", "秋", "冬"], ["国潮"]),
    ("文玩", "玉镯", ["轻薄"], ["春", "夏", "秋", "冬"], ["优雅", "国潮"]),
    # 鞋履
    ("鞋履", "商务皮鞋", ["适中"], ["春", "夏", "秋", "冬"], ["商务"]),
    ("鞋履", "运动跑鞋", ["轻薄"], ["春", "夏", "秋"], ["运动"]),
    ("鞋履", "休闲帆布鞋", ["轻薄"], ["春", "夏", "秋"], ["休闲", "街头"]),
    ("鞋履", "优雅高跟鞋", ["轻薄"], ["春", "夏", "秋"], ["优雅", "性感"]),
    ("鞋履", "保暖雪地靴", ["厚重"], ["冬"], ["休闲"]),
    ("鞋履", "文艺布鞋", ["轻薄"], ["春", "夏", "秋"], ["文艺", "森系"]),
]


def generate_item_pool() -> List[Dict]:
    """
    生成标准化物品池（120件）
    
    每件物品包含：
    - id, item_code, name, category
    - primary_element, secondary_element（五行属性）
    - color（颜色）
    - thickness_level（厚度）
    - applicable_seasons（适用季节）
    - style（风格标签）
    - functionality（功能性）
    - attributes_detail（详细属性）
    - semantic_score（语义分，模拟检索结果）
    """
    items = []
    item_id = 1
    
    for template in ITEM_TEMPLATES:
        category, base_name, thicknesses, seasons, styles = template
        
        # 为每个模板生成2件不同五行的物品
        for element_idx in range(2):
            primary_element = FIVE_ELEMENTS[(item_id + element_idx) % 5]
            secondary_element = FIVE_ELEMENTS[(item_id + element_idx + 2) % 5]
            colors = ELEMENT_COLORS[primary_element]
            color = random.choice(colors)
            thickness = random.choice(thicknesses)
            style = random.choice(styles)
            
            # 生成名称（加入五行/颜色特征）
            element_prefix = {"金": "银白", "木": "青绿", "水": "墨蓝", "火": "赤红", "土": "土黄"}
            name = f"{element_prefix[primary_element]}{base_name}"
            
            # 功能性
            functionality = []
            if "运动" in styles:
                functionality.extend(["透气", "速干"])
            if category == "外套" and thickness in ("厚重", "中厚"):
                functionality.append("保暖")
            if thickness in ("极薄", "轻薄"):
                functionality.append("透气")
            
            # 版型
            fit_type = random.choice(["修身", "适中", "宽松"])
            if "修身" in base_name or "修身" in str(styles):
                fit_type = "修身"
            elif "宽松" in base_name or "oversize" in base_name:
                fit_type = "宽松"
            
            item = {
                "id": item_id,
                "item_code": f"ITEM{item_id:04d}",
                "name": name,
                "category": category,
                "primary_element": primary_element,
                "secondary_element": secondary_element,
                "color": color,
                "thickness_level": thickness,
                "applicable_seasons": seasons,
                "style": style,
                "functionality": functionality,
                "attributes_detail": {
                    "款式": {
                        "风格": style,
                        "版型": fit_type,
                    }
                },
                "semantic_score": round(random.uniform(0.4, 0.9), 3),
                "gender": random.choice(["中性", "中性", "男", "女"]),
                "temperature_range": _get_temp_range(thickness),
            }
            items.append(item)
            item_id += 1
    
    return items


def _get_temp_range(thickness: str) -> Dict:
    """根据厚度推断适用温度范围"""
    ranges = {
        "极薄": {"最低": 25, "最高": 40},
        "轻薄": {"最低": 18, "最高": 35},
        "适中": {"最低": 10, "最高": 28},
        "中厚": {"最低": 5, "最高": 20},
        "厚重": {"最低": -10, "最高": 12},
    }
    return ranges.get(thickness, {"最低": 10, "最高": 30})


# ============================================================
# 虚拟用户生成
# ============================================================

SKIN_TONES = ["冷白皮", "暖白皮", "自然色", "小麦色", "黑皮"]
BODY_TYPES = ["偏瘦", "标准", "偏胖"]
STYLE_PREFERENCES = list(STYLE_KEYWORDS_KEYS) if 'STYLE_KEYWORDS_KEYS' in dir() else [
    "简约", "国潮", "运动", "商务", "甜美", "街头", "文艺", "优雅", "休闲", "性感", "知性", "森系"
]


@dataclass
class VirtualUser:
    """虚拟用户档案"""
    user_id: int
    gender: str
    day_master: str           # 日主（如"甲木"）
    strength: str             # 身强/身弱
    target_elements: List[str]  # 喜用神
    avoid_elements: List[str]   # 忌神
    boost_elements: List[str]   # 相生辅助
    skin_tone: Optional[str]
    body_type: Optional[str]
    style_preference: Optional[str]
    bazi_result: Optional[Dict] = None
    
    def __post_init__(self):
        # 构建模拟的八字结果
        self.bazi_result = {
            "day_master": self.day_master,
            "strength": self.strength,
            "suggested_elements": self.target_elements,
            "avoid_elements": self.avoid_elements,
            "reasoning": f"日主{self.day_master}，{self.strength}，喜用神为{'、'.join(self.target_elements)}",
        }


def generate_users(count: int = 200) -> List[VirtualUser]:
    """
    生成指定数量的虚拟用户
    
    确保覆盖：
    - 10种日主 × 身强/身弱 = 20种八字模式
    - 5种肤色
    - 3种体型
    - 12种风格偏好
    - 男/女两种性别
    """
    users = []
    
    for i in range(count):
        # 循环使用八字模式确保覆盖
        pattern = DAY_MASTER_PATTERNS[i % len(DAY_MASTER_PATTERNS)]
        day_master, strength, target, avoid = pattern
        
        # 相生辅助：生喜用神的元素
        boost = []
        for elem in target[:2]:  # 取前2个喜用神
            for src, dst in ELEMENT_GENERATES.items():
                if dst == elem and src not in target:
                    boost.append(src)
                    break
        
        # 随机分配审美特征（确保多样性）
        gender = "男" if i % 2 == 0 else "女"
        skin_tone = SKIN_TONES[i % len(SKIN_TONES)] if random.random() > 0.2 else None
        body_type = BODY_TYPES[i % len(BODY_TYPES)] if random.random() > 0.15 else None
        style_pref = STYLE_PREFERENCES[i % len(STYLE_PREFERENCES)] if random.random() > 0.1 else None
        
        user = VirtualUser(
            user_id=i + 1,
            gender=gender,
            day_master=day_master,
            strength=strength,
            target_elements=target[:3],  # 最多3个喜用神
            avoid_elements=avoid,
            boost_elements=boost[:2],
            skin_tone=skin_tone,
            body_type=body_type,
            style_preference=style_pref,
        )
        users.append(user)
    
    return users


# ============================================================
# 测试用例生成
# ============================================================

# 场景列表
SCENES = [None, "商务", "面试", "约会", "运动", "居家", "婚礼", "派对", "旅行", "出差", "度假", "户外探险"]

# 天气条件
WEATHER_CONDITIONS = [
    # (温度, 天气描述, 季节)
    (35, "炎热", "夏"),      # 极端高温
    (32, "闷热", "夏"),      # 高温
    (28, "晴天", "夏"),      # 中高温
    (22, "多云", "春"),      # 舒适
    (15, "晴天", "秋"),      # 微凉
    (8, "大风", "秋"),       # 低温
    (3, "寒冷", "冬"),       # 极端低温
    (-5, "雪天", "冬"),      # 严寒
    (25, "雨天", "夏"),      # 温暖雨天
    (12, "阴天", "春"),      # 春季阴天
]


@dataclass
class TestCase:
    """测试用例"""
    case_id: str
    user: VirtualUser
    scene: Optional[str]
    weather_info: Optional[Dict]
    season: str
    complexity: str  # simple / medium / complex
    description: str
    expected_criteria: Dict = field(default_factory=dict)


def generate_test_cases(users: List[VirtualUser], cases_per_user: int = 15) -> List[TestCase]:
    """
    为每个用户生成测试用例
    
    复杂度分布：
    - 简单（30%）：仅天气
    - 中等（40%）：八字 + 天气
    - 高复杂度（30%）：八字 + 场景 + 审美 + 天气 + 季节
    """
    test_cases = []
    case_counter = 0
    
    for user in users:
        # 简单场景（仅天气，无八字无场景）
        simple_count = int(cases_per_user * 0.3)
        for _ in range(simple_count):
            case_counter += 1
            temp, weather_desc, season = random.choice(WEATHER_CONDITIONS)
            
            tc = TestCase(
                case_id=f"TC{case_counter:05d}",
                user=user,
                scene=None,
                weather_info={"temperature": temp, "weather_desc": weather_desc},
                season=season,
                complexity="simple",
                description=f"简单场景：{season}季{temp}°C{weather_desc}",
                expected_criteria={
                    "temp_appropriate": True,
                    "no_bazi_match": True,  # 不考虑八字
                }
            )
            test_cases.append(tc)
        
        # 中等复杂度（八字 + 天气）
        medium_count = int(cases_per_user * 0.4)
        for _ in range(medium_count):
            case_counter += 1
            temp, weather_desc, season = random.choice(WEATHER_CONDITIONS)
            
            tc = TestCase(
                case_id=f"TC{case_counter:05d}",
                user=user,
                scene=None,
                weather_info={"temperature": temp, "weather_desc": weather_desc},
                season=season,
                complexity="medium",
                description=f"中等场景：{user.day_master}({user.strength})，{season}季{temp}°C",
                expected_criteria={
                    "temp_appropriate": True,
                    "bazi_match": True,
                    "target_elements": user.target_elements,
                }
            )
            test_cases.append(tc)
        
        # 高复杂度（八字 + 场景 + 审美 + 天气 + 季节）
        complex_count = cases_per_user - simple_count - medium_count
        for _ in range(complex_count):
            case_counter += 1
            temp, weather_desc, season = random.choice(WEATHER_CONDITIONS)
            scene = random.choice([s for s in SCENES if s is not None])
            
            tc = TestCase(
                case_id=f"TC{case_counter:05d}",
                user=user,
                scene=scene,
                weather_info={"temperature": temp, "weather_desc": weather_desc},
                season=season,
                complexity="complex",
                description=f"复杂场景：{user.day_master}，{scene}，{temp}°C，{user.style_preference or '无风格'}",
                expected_criteria={
                    "temp_appropriate": True,
                    "bazi_match": True,
                    "scene_match": True,
                    "aesthetic_match": True,
                    "target_elements": user.target_elements,
                    "scene": scene,
                    "skin_tone": user.skin_tone,
                    "body_type": user.body_type,
                    "style_preference": user.style_preference,
                }
            )
            test_cases.append(tc)
    
    return test_cases


# ============================================================
# 搭配完整性专项测试用例
# ============================================================

# 搭配场景：强制要求完整搭配的场景
OUTFIT_SCENES = [
    # (场景, 温度, 天气, 季节, 描述)
    ("商务", 22, "晴天", "春", "春季商务穿搭，需要完整搭配"),
    ("约会", 25, "多云", "夏", "夏季约会穿搭，需要时尚搭配"),
    ("面试", 18, "阴天", "秋", "秋季面试穿搭，需要正式搭配"),
    ("旅行", 28, "晴天", "夏", "夏季旅行穿搭，需要舒适搭配"),
    ("婚礼", 20, "晴天", "春", "春季婚礼穿搭，需要优雅搭配"),
    ("运动", 30, "炎热", "夏", "夏季运动穿搭，需要运动搭配"),
    ("出差", 8, "大风", "秋", "秋季出差穿搭，需要保暖搭配"),
    ("度假", 32, "晴天", "夏", "夏季度假穿搭，需要休闲搭配"),
    ("派对", 15, "晴天", "秋", "秋季派对穿搭，需要时尚搭配"),
    ("居家", 12, "阴天", "春", "春季居家穿搭，需要舒适搭配"),
]


def generate_outfit_cases(users: List[VirtualUser]) -> List[TestCase]:
    """
    生成搭配完整性专项测试用例
    
    设计原则：
    - 每个用例都要求推荐结果能形成一套完整穿搭
    - 覆盖不同场景下的搭配需求
    - 覆盖不同季节/温度下的搭配组合
    - 包含边界情况（极端温度下的搭配、特殊体型的搭配）
    """
    outfit_cases = []
    case_counter = 80000
    
    # 为每个用户生成2个搭配专项测试
    for user in users:
        # 随机选取2个搭配场景
        selected_scenes = random.sample(OUTFIT_SCENES, min(2, len(OUTFIT_SCENES)))
        
        for scene, temp, weather_desc, season, desc in selected_scenes:
            case_counter += 1
            tc = TestCase(
                case_id=f"TC{case_counter:05d}",
                user=user,
                scene=scene,
                weather_info={"temperature": temp, "weather_desc": weather_desc},
                season=season,
                complexity="complex",
                description=f"搭配测试：{desc}，{user.day_master}({user.strength})",
                expected_criteria={
                    "outfit_completeness": True,
                    "temp_appropriate": True,
                    "bazi_match": True,
                    "scene_match": True,
                    "target_elements": user.target_elements,
                    "scene": scene,
                    "skin_tone": user.skin_tone,
                    "body_type": user.body_type,
                    "style_preference": user.style_preference,
                    # 搭配完整性期望
                    "expect_top": True,       # 期望有上半身
                    "expect_bottom": True,    # 期望有下半身
                    "expect_diverse": True,   # 期望品类多样
                }
            )
            outfit_cases.append(tc)
    
    # 极端温度搭配测试（验证极端天气下仍能形成搭配）
    extreme_outfit_tests = [
        (-8, "严寒", "冬", "极寒搭配：需要保暖且完整"),
        (40, "酷暑", "夏", "极热搭配：需要清凉且完整"),
        (0, "冰点", "冬", "冰点搭配：需要保暖且多样"),
        (36, "高温", "夏", "高温搭配：需要透气且多样"),
    ]
    
    for user in users[:50]:  # 取前50个用户
        temp, weather_desc, season, desc = random.choice(extreme_outfit_tests)
        case_counter += 1
        tc = TestCase(
            case_id=f"TC{case_counter:05d}",
            user=user,
            scene=random.choice(["商务", "休闲", "旅行"]),
            weather_info={"temperature": temp, "weather_desc": weather_desc},
            season=season,
            complexity="boundary",
            description=f"搭配边界：{desc}，{temp}°C",
            expected_criteria={
                "outfit_completeness": True,
                "temp_critical": True,
                "temp_value": temp,
                "expect_top": True,
                "expect_bottom": True,
                "expect_diverse": True,
            }
        )
        outfit_cases.append(tc)
    
    return outfit_cases


# ============================================================
# 边界测试用例
# ============================================================

def generate_boundary_cases(users: List[VirtualUser]) -> List[TestCase]:
    """
    生成边界测试用例
    
    覆盖：
    - 极端温度（-10°C, 42°C）
    - 特殊体型（偏胖 + 修身偏好冲突）
    - 小众审美（森系 + 商务场景冲突）
    - 五行全不匹配
    """
    boundary_cases = []
    case_counter = 90000
    
    # 极端温度测试
    extreme_temps = [(-10, "极寒"), (42, "极热"), (0, "冰点"), (38, "酷暑")]
    for user in users[:10]:  # 取前10个用户
        for temp, desc in extreme_temps:
            case_counter += 1
            tc = TestCase(
                case_id=f"TC{case_counter:05d}",
                user=user,
                scene=None,
                weather_info={"temperature": temp, "weather_desc": desc},
                season="冬" if temp < 10 else "夏",
                complexity="boundary",
                description=f"边界测试：{desc}({temp}°C)",
                expected_criteria={
                    "temp_critical": True,
                    "temp_value": temp,
                }
            )
            boundary_cases.append(tc)
    
    # 场景冲突测试
    conflict_scenes = [
        ("森系", "商务", "风格与场景冲突"),
        ("性感", "面试", "风格与场景冲突"),
        ("运动", "婚礼", "风格与场景冲突"),
    ]
    for user in users[10:20]:
        for style, scene, desc in conflict_scenes:
            case_counter += 1
            user.style_preference = style
            tc = TestCase(
                case_id=f"TC{case_counter:05d}",
                user=user,
                scene=scene,
                weather_info={"temperature": 20, "weather_desc": "晴天"},
                season="春",
                complexity="boundary",
                description=f"边界测试：{desc}（{style}+{scene}）",
                expected_criteria={
                    "scene_priority": True,
                    "scene": scene,
                }
            )
            boundary_cases.append(tc)
    
    return boundary_cases


# ============================================================
# 数据生成入口
# ============================================================

def generate_all_data() -> Dict:
    """
    生成完整测试数据集
    
    Returns:
        {
            "items": 物品池,
            "users": 用户列表,
            "test_cases": 测试用例列表,
            "stats": 统计信息,
        }
    """
    print("📦 生成物品池...")
    items = generate_item_pool()
    print(f"   ✓ 物品池: {len(items)} 件")
    
    print("👥 生成虚拟用户...")
    users = generate_users(200)
    print(f"   ✓ 虚拟用户: {len(users)} 人")
    
    print("📝 生成测试用例...")
    normal_cases = generate_test_cases(users, cases_per_user=15)
    boundary_cases = generate_boundary_cases(users)
    outfit_cases = generate_outfit_cases(users)
    all_cases = normal_cases + boundary_cases + outfit_cases
    print(f"   ✓ 测试用例: {len(all_cases)} 个")
    print(f"     - 常规用例: {len(normal_cases)} 个")
    print(f"     - 边界用例: {len(boundary_cases)} 个")
    print(f"     - 搭配专项: {len(outfit_cases)} 个")
    
    # 统计
    complexity_dist = {}
    for tc in all_cases:
        complexity_dist[tc.complexity] = complexity_dist.get(tc.complexity, 0) + 1
    
    scene_dist = {}
    for tc in all_cases:
        s = tc.scene or "无场景"
        scene_dist[s] = scene_dist.get(s, 0) + 1
    
    # 搭配测试统计
    outfit_test_count = sum(1 for tc in all_cases if tc.expected_criteria.get("outfit_completeness"))
    
    stats = {
        "total_items": len(items),
        "total_users": len(users),
        "total_cases": len(all_cases),
        "complexity_distribution": complexity_dist,
        "scene_distribution": scene_dist,
        "users_with_bazi": sum(1 for u in users if u.bazi_result),
        "users_with_aesthetic": sum(1 for u in users if u.skin_tone or u.body_type or u.style_preference),
        "outfit_completeness_cases": outfit_test_count,
    }
    
    return {
        "items": items,
        "users": users,
        "test_cases": all_cases,
        "stats": stats,
    }


if __name__ == "__main__":
    data = generate_all_data()
    print("\n📊 数据集统计:")
    for k, v in data["stats"].items():
        print(f"   {k}: {v}")
