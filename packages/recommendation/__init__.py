"""
推荐引擎模块

将原 packages/ai_agents/nodes.py 中的推荐算法逻辑提取为独立模块，
实现配置化权重管理、纯函数评分、可测试的过滤/多样性逻辑。

模块结构：
- config: 权重预设、温度阈值、审美映射表（纯配置）
- scoring: 评分引擎（五行/温度/季节/审美/轮换）
- filters: 过滤逻辑（温度硬过滤/场景SQL/天气SQL/性别）
- diversity: 多样性保障（分类/五行/温度安全）
- context_extraction: 上下文提取（LLM + 规则双路径）
- behavior: 用户行为反馈处理（显性+隐性）
- engine: 推荐引擎主入口（编排 scoring -> filtering -> diversity）
"""

from packages.recommendation.config import (
    compute_recommend_weights,
    WEIGHT_PRESETS,
    EXTREME_HOT_TEMP,
    EXTREME_COLD_TEMP,
    MAX_TARGET_ELEMENTS,
)
from packages.recommendation.scoring import (
    calculate_wuxing_score,
    calculate_temp_score,
    calculate_season_score,
    calculate_skin_tone_bonus,
    calculate_style_preference_bonus,
    calculate_body_type_bonus,
    calculate_rotation_bonus,
    calculate_final_score,
    infer_item_thickness,
    get_current_season,
)
from packages.recommendation.filters import (
    apply_temperature_hard_filter,
    apply_temperature_safety_check,
    build_gender_filter,
    build_weather_filter,
    build_scene_filter,
    filter_by_scene_score,
)
from packages.recommendation.diversity import (
    ensure_category_diversity,
    ensure_wuxing_diversity,
)
from packages.recommendation.context_extraction import (
    extract_context_from_query,
    extract_context_by_rules,
)
from packages.recommendation.behavior import (
    get_user_behavior_preferences,
    calculate_behavior_score,
    record_user_behavior,
)
from packages.recommendation.engine import (
    score_and_rank_items,
)

__all__ = [
    # config
    "compute_recommend_weights",
    "WEIGHT_PRESETS",
    "EXTREME_HOT_TEMP",
    "EXTREME_COLD_TEMP",
    "MAX_TARGET_ELEMENTS",
    # scoring
    "calculate_wuxing_score",
    "calculate_temp_score",
    "calculate_season_score",
    "calculate_skin_tone_bonus",
    "calculate_style_preference_bonus",
    "calculate_body_type_bonus",
    "calculate_rotation_bonus",
    "calculate_final_score",
    "infer_item_thickness",
    "get_current_season",
    # filters
    "apply_temperature_hard_filter",
    "apply_temperature_safety_check",
    "build_gender_filter",
    "build_weather_filter",
    "build_scene_filter",
    "filter_by_scene_score",
    # diversity
    "ensure_category_diversity",
    "ensure_wuxing_diversity",
    # context_extraction
    "extract_context_from_query",
    "extract_context_by_rules",
    # behavior
    "get_user_behavior_preferences",
    "calculate_behavior_score",
    "record_user_behavior",
    # engine
    "score_and_rank_items",
]
