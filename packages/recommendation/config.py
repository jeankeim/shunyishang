"""
推荐引擎配置中心

集中管理所有推荐算法的配置参数：
- 权重预设表（替代硬编码 if-else）
- 温度分层阈值
- 审美映射表（肤色/风格/体型）
- 多样性约束参数
- 行为反馈权重

所有配置支持运行时覆盖（通过 update_config 函数）。
"""

from typing import Dict, List, Tuple

# ============================================================
# 温度分层阈值（统一"极端温度加权""温度硬过滤""温度评分"三处判定）
# ============================================================
EXTREME_HOT_TEMP = 30    # >=30°C：极端高温
HOT_TEMP = 28            # >=28°C：高温
MILD_HOT_TEMP = 25       # >=25°C：中高温
EXTREME_COLD_TEMP = 5    # <=5°C：极端低温
MILD_COLD_TEMP = 10      # <=10°C：低温

# ============================================================
# 推荐五行数量上限
# ============================================================
MAX_TARGET_ELEMENTS = 3

# ============================================================
# 权重预设表：(has_bazi, has_scene, has_prefs) -> weights
# 所有预设的各权重之和 = 1.0
# ============================================================
WEIGHT_PRESETS: Dict[Tuple[bool, bool, bool], Dict[str, float]] = {
    # 有八字 + 有场景
    (True,  True,  True):  {"semantic": 0.50, "wuxing": 0.25, "scene": 0.15, "pref": 0.10, "temp": 0.00},
    (True,  True,  False): {"semantic": 0.50, "wuxing": 0.30, "scene": 0.20, "pref": 0.00, "temp": 0.00},
    # 有八字 + 无场景
    (True,  False, True):  {"semantic": 0.50, "wuxing": 0.35, "scene": 0.00, "pref": 0.15, "temp": 0.00},
    (True,  False, False): {"semantic": 0.55, "wuxing": 0.45, "scene": 0.00, "pref": 0.00, "temp": 0.00},
    # 无八字 + 有场景
    (False, True,  True):  {"semantic": 0.55, "wuxing": 0.15, "scene": 0.20, "pref": 0.10, "temp": 0.00},
    (False, True,  False): {"semantic": 0.60, "wuxing": 0.20, "scene": 0.20, "pref": 0.00, "temp": 0.00},
    # 无八字 + 无场景
    (False, False, True):  {"semantic": 0.55, "wuxing": 0.30, "scene": 0.00, "pref": 0.15, "temp": 0.00},
    (False, False, False): {"semantic": 0.60, "wuxing": 0.40, "scene": 0.00, "pref": 0.00, "temp": 0.00},
}

# 极端温度时，温度维度占比
EXTREME_TEMP_RATIO = 0.25

# ============================================================
# 五行评分参数
# ============================================================
WUXING_PRIMARY_SCORE = 0.6       # 主五行命中 target
WUXING_SECONDARY_SCORE = 0.3     # 次五行命中 target
WUXING_BOOST_PRIMARY = 0.08      # 主五行命中 boost（相生辅助）
WUXING_BOOST_SECONDARY = 0.04    # 次五行命中 boost
WUXING_BOOST_MIN_CAP = 0.05      # boost 加分最低上限（即使 base=0 也至少 cap 到此值）

# 饰品/文玩五行补救加分（个人五行增强）
ORNAMENT_BONUS = 0.06
ORNAMENT_CATEGORIES = {"饰品", "文玩"}

# 配饰场景冲突调节加分（当配饰五行桥接场景→个人喜用神时触发）
SCENE_MEDIATION_BONUS = 0.04
ACCENT_CATEGORIES_FOR_MEDIATION = {"配饰", "饰品", "文玩"}

# ============================================================
# 轮换奖励参数（自有衣物穿着次数少的加分鼓励轮换）
# ============================================================
ROTATION_MAX_BONUS = 0.05        # 0次穿着 = +0.05
ROTATION_DECAY_PER_WEAR = 0.01   # 每穿一次减少 0.01，5次后为0

# ============================================================
# 审美画像加分配置
# ============================================================

# 肤色 → 适合的颜色五行映射（加分值）
SKIN_TONE_COLOR_FIT: Dict[str, Dict[str, float]] = {
    "冷白皮": {"金": 0.12, "水": 0.12, "木": 0.08, "火": 0.04, "土": 0.04},
    "暖白皮": {"火": 0.12, "土": 0.12, "木": 0.08, "金": 0.04, "水": 0.04},
    "自然色": {"木": 0.10, "土": 0.10, "金": 0.08, "火": 0.08, "水": 0.08},
    "小麦色": {"土": 0.12, "火": 0.12, "金": 0.08, "木": 0.04, "水": 0.04},
    "黑皮":   {"金": 0.12, "火": 0.10, "水": 0.08, "木": 0.04, "土": 0.04},
}
SKIN_TONE_MAX_BONUS = 0.18

# 风格偏好 → 物品风格关键词映射
STYLE_KEYWORDS: Dict[str, List[str]] = {
    "简约": ["简约", "极简", "基础", "纯色", "素色"],
    "国潮": ["国潮", "中式", "传统", "汉服", "刺绣", "盘扣", "水墨"],
    "运动": ["运动", "休闲", "户外", "速干", "透气"],
    "商务": ["商务", "正式", "职业", "西装", "衬衫"],
    "甜美": ["甜美", "可爱", "蕾丝", "蝴蝶结", "粉色"],
    "街头": ["街头", "潮流", "涂鸦", "宽松", "oversize"],
    "文艺": ["文艺", "复古", "棉麻", "亚麻", "民族"],
    "优雅": ["优雅", "气质", "丝绸", "缎面", "垂坠"],
    "休闲": ["休闲", "日常", "舒适", "宽松"],
    "性感": ["性感", "修身", "低领", "露肩"],
    "知性": ["知性", "干练", "利落", "简约"],
    "森系": ["森系", "自然", "棉麻", "宽松", "碎花"],
}
STYLE_NAME_BONUS = 0.10       # 名称匹配加分
STYLE_DETAIL_BONUS = 0.10     # 属性详情匹配加分
STYLE_FIELD_BONUS = 0.15      # style字段精确匹配加分
STYLE_MAX_BONUS = 0.25        # 风格加分上限

# 体型 → 适合版型映射
BODY_TYPE_FIT: Dict[str, Dict[str, float]] = {
    "偏瘦": {"修身": 0.14, "适中": 0.08, "宽松": 0.04},
    "标准": {"修身": 0.10, "适中": 0.14, "宽松": 0.08},
    "偏胖": {"宽松": 0.14, "适中": 0.10, "修身": 0.04},
}
BODY_TYPE_MAX_BONUS = 0.14

# ============================================================
# 多样性约束参数
# ============================================================
CATEGORY_LIMITS: Dict[str, int] = {
    "上装": 2,
    "下装": 2,
    "裙装": 2,
    "外套": 2,
    "配饰": 1,
    "饰品": 2,
    "文玩": 1,
    "鞋履": 1,
}
DEFAULT_CATEGORY_LIMIT = 1
ACCENT_CATEGORIES = {"配饰", "饰品", "文玩"}

# 温度安全检查阈值
TEMP_SAFETY_THRESHOLD = 0.3    # temp_score < 0.3 视为温度不安全
TEMP_ESSENTIAL_THRESHOLD = 0.7  # temp_score >= 0.7 视为温度必需（不替换）

# ============================================================
# 用户行为反馈权重（隐性反馈）
# ============================================================
BEHAVIOR_WEIGHTS: Dict[str, float] = {
    "dwell_long": 0.3,      # 停留 > 10秒
    "dwell_short": 0.1,     # 停留 <= 10秒
    "click": 0.2,           # 点击
    "expand": 0.2,          # 展开详情
    "image_click": 0.25,    # 点击图片
    "view": 0.1,            # 浏览
}
BEHAVIOR_LOOKBACK_DAYS = 7       # 行为回溯天数
BEHAVIOR_MAX_SCORE = 0.10        # 行为加分在 final_score 中的最大占比
BEHAVIOR_DECAY_PER_DAY = 0.05    # 每日衰减

# ============================================================
# 偏好学习参数
# ============================================================
PREF_DECAY_PER_DAY = 0.02       # 偏好每日衰减 2%
PREF_DECAY_MIN = 0.10           # 最低保留 10%
PREF_CACHE_TTL = 600            # 偏好缓存 TTL（秒）

# ============================================================
# 季节评分参数
# ============================================================
SEASON_MATCH_SCORE = 1.0        # 季节完全匹配
SEASON_MISMATCH_SCORE = 0.7     # 季节不匹配（惩罚）
SEASON_UNKNOWN_SCORE = 0.5      # 无季节信息（中性）

# ============================================================
# 换一批随机扰动范围
# ============================================================
BATCH_JITTER_RANGE = 0.05


def compute_recommend_weights(
    has_bazi: bool,
    has_scene: bool,
    has_prefs: bool,
    is_extreme_temp: bool = False,
) -> Dict[str, float]:
    """
    配置化计算推荐权重

    策略：
    1. 从预设表查基础权重
    2. 极端温度时，温度维度占 EXTREME_TEMP_RATIO，其余按比例缩减
    3. 用 semantic 吸收浮点误差，确保总和精确 = 1.0

    Returns:
        各维度权重字典（总和=1.0）
    """
    preset = WEIGHT_PRESETS.get(
        (has_bazi, has_scene, has_prefs),
        WEIGHT_PRESETS[(False, False, False)],
    ).copy()

    if is_extreme_temp:
        preset["temp"] = EXTREME_TEMP_RATIO
        remaining = 1.0 - EXTREME_TEMP_RATIO
        other_sum = sum(v for k, v in preset.items() if k != "temp")
        if other_sum > 0:
            scale = remaining / other_sum
            for k in preset:
                if k != "temp":
                    preset[k] = round(preset[k] * scale, 4)
        # 用 semantic 吸收浮点累积误差
        total_without_semantic = sum(v for k, v in preset.items() if k != "semantic")
        preset["semantic"] = round(1.0 - total_without_semantic, 4)

    return preset
