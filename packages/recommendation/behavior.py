"""
用户行为反馈处理

包含：
- 显性反馈（点赞/点踩）→ 偏好学习（委托 PreferenceService）
- 隐性反馈（浏览/点击/停留）→ 行为加分（本模块核心新增）

隐性反馈机制：
1. 从 user_behaviors 表聚合用户近期行为（7天内）
2. 按行为类型赋予不同权重
3. 转化为物品属性维度的偏好加分
4. 在评分链路中作为独立微调项叠加
"""

import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from packages.recommendation.config import (
    BEHAVIOR_WEIGHTS,
    BEHAVIOR_LOOKBACK_DAYS,
    BEHAVIOR_MAX_SCORE,
    BEHAVIOR_DECAY_PER_DAY,
)

logger = logging.getLogger(__name__)


def get_user_behavior_preferences(user_id: int) -> Dict[str, Dict[str, float]]:
    """
    从 user_behaviors 表聚合用户近期行为，转化为偏好维度

    返回格式与 user_preferences 类似：
    {
        "category": {"上装": 0.3, "饰品": 0.2, ...},
        "element": {"木": 0.15, ...},
        "color": {"绿色": 0.1, ...},
    }

    Args:
        user_id: 用户ID

    Returns:
        行为偏好字典（维度 -> 属性值 -> 加分值）
    """
    if not user_id:
        return {}

    try:
        from apps.api.core.database import DatabasePool

        query = """
            SELECT 
                ub.action,
                ub.dwell_duration,
                ub.item_id,
                ub.item_source,
                COALESCE(i.category, uw.category) as category,
                COALESCE(i.primary_element, uw.primary_element) as element,
                COALESCE(i.color, uw.color) as color,
                COALESCE(i.style, uw.style) as style,
                EXTRACT(EPOCH FROM (NOW() - ub.created_at)) / 86400 AS days_old
            FROM user_behaviors ub
            LEFT JOIN items i ON ub.item_source = 'public' AND ub.item_id = i.item_code
            LEFT JOIN user_wardrobe uw ON ub.item_source = 'wardrobe' AND ub.item_id = uw.id::text
            WHERE ub.user_id = %s
              AND ub.created_at >= NOW() - INTERVAL '%s days'
            ORDER BY ub.created_at DESC
            LIMIT 500
        """ % ("%s", BEHAVIOR_LOOKBACK_DAYS)

        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [user_id])
                columns = [desc[0] for desc in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]

        if not rows:
            return {}

        # 聚合行为到属性维度
        prefs: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for row in rows:
            action = row.get("action", "view")
            days_old = row.get("days_old", 0) or 0
            dwell_duration = row.get("dwell_duration", 0) or 0

            # 计算行为基础权重
            if action == "dwell" and dwell_duration > 10:
                base_weight = BEHAVIOR_WEIGHTS["dwell_long"]
            elif action == "dwell":
                base_weight = BEHAVIOR_WEIGHTS["dwell_short"]
            elif action == "image_click":
                base_weight = BEHAVIOR_WEIGHTS["image_click"]
            elif action in ("click", "expand"):
                base_weight = BEHAVIOR_WEIGHTS["click"]
            else:  # view
                base_weight = BEHAVIOR_WEIGHTS["view"]

            # 时间衰减
            decay = max(0.1, 1.0 - days_old * BEHAVIOR_DECAY_PER_DAY)
            weight = base_weight * decay

            # 写入各属性维度
            category = row.get("category")
            if category:
                prefs["category"][category] += weight

            element = row.get("element")
            if element:
                prefs["element"][element] += weight

            color = row.get("color")
            if color:
                prefs["color"][color] += weight

            style = row.get("style")
            if style:
                prefs["style"][style] += weight

        # 归一化：每个维度内的值缩放到 [0, BEHAVIOR_MAX_SCORE]
        result: Dict[str, Dict[str, float]] = {}
        for dim, values in prefs.items():
            if not values:
                continue
            max_val = max(values.values())
            if max_val > 0:
                result[dim] = {
                    k: round(v / max_val * BEHAVIOR_MAX_SCORE, 4)
                    for k, v in values.items()
                }

        logger.debug(f"[行为偏好] user={user_id}, dims={list(result.keys())}")
        return result

    except Exception as e:
        logger.debug(f"[行为偏好] 获取失败 user={user_id}: {e}")
        return {}


def calculate_behavior_score(
    item: Dict[str, Any],
    behavior_prefs: Dict[str, Dict[str, float]],
) -> float:
    """
    计算物品与用户行为偏好的匹配加分

    Args:
        item: 物品字典
        behavior_prefs: 行为偏好（from get_user_behavior_preferences）

    Returns:
        0.0 ~ BEHAVIOR_MAX_SCORE 之间的行为加分
    """
    if not behavior_prefs:
        return 0.0

    total_score = 0.0
    count = 0

    # 检查分类匹配
    category = item.get("category", "")
    if category and "category" in behavior_prefs:
        score = behavior_prefs["category"].get(category, 0.0)
        if score > 0:
            total_score += score
            count += 1

    # 检查五行匹配
    element = item.get("primary_element", "")
    if element and "element" in behavior_prefs:
        score = behavior_prefs["element"].get(element, 0.0)
        if score > 0:
            total_score += score
            count += 1

    # 检查颜色匹配
    color = item.get("color", "")
    if color and "color" in behavior_prefs:
        score = behavior_prefs["color"].get(color, 0.0)
        if score > 0:
            total_score += score
            count += 1

    # 检查风格匹配
    style = item.get("style", "")
    if style and "style" in behavior_prefs:
        score = behavior_prefs["style"].get(style, 0.0)
        if score > 0:
            total_score += score
            count += 1

    if count == 0:
        return 0.0

    # 取匹配维度的平均分（避免维度越多分越高）
    avg_score = total_score / count
    return min(BEHAVIOR_MAX_SCORE, avg_score)


def record_user_behavior(
    user_id: int,
    item_id: str,
    action: str,
    item_source: str = "public",
    dwell_duration: int = 0,
    session_id: Optional[str] = None,
) -> bool:
    """
    记录用户行为到 user_behaviors 表

    Args:
        user_id: 用户ID
        item_id: 物品ID
        action: 行为类型（view/click/expand/image_click/dwell）
        item_source: 物品来源（public/wardrobe）
        dwell_duration: 停留时长（秒）
        session_id: 推荐会话ID

    Returns:
        是否记录成功
    """
    try:
        from apps.api.core.database import DatabasePool

        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_behaviors (user_id, item_id, item_source, action, dwell_duration, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [user_id, item_id, item_source, action, dwell_duration, session_id],
                )
                conn.commit()
        return True
    except Exception as e:
        logger.debug(f"[行为记录] 失败: {e}")
        return False
