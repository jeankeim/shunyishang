"""
穿搭日记反馈回流服务
从用户日记中提取偏好信号，回流到偏好学习系统

触发逻辑：
- 日记评分 >= 4 → 物品属性视为 'like'
- 日记评分 <= 2 → 物品属性视为 'dislike'
- 日记评分 = 3 → 不触发偏好更新
- 关联衣物的颜色、五行、分类、风格、材质、厚度均参与学习
"""

import logging
from typing import List, Dict, Any, Optional

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.services.preference_service import preference_service

logger = logging.getLogger(__name__)

# 评分阈值
LIKE_THRESHOLD = 4       # >= 4 视为喜欢
DISLIKE_THRESHOLD = 2     # <= 2 视为不喜欢


class DiaryFeedbackService:
    """穿搭日记反馈回流服务"""

    def process_diary_feedback(self, user_id: int, diary_id: int, rating: Optional[int]) -> None:
        """
        处理日记反馈，将评分转化为偏好信号

        Args:
            user_id: 用户ID
            diary_id: 日记ID
            rating: 日记评分 (1-5)，None 则跳过
        """
        if rating is None:
            return

        # 确定偏好动作
        if rating >= LIKE_THRESHOLD:
            action = 'like'
        elif rating <= DISLIKE_THRESHOLD:
            action = 'dislike'
        else:
            # 中性评分，不更新偏好
            return

        # 获取日记关联的所有衣物
        items = self._get_diary_items(diary_id)
        if not items:
            logger.debug(f"[DiaryFeedback] diary={diary_id} 无关联衣物，跳过")
            return

        # 逐个衣物更新偏好
        updated_count = 0
        for item_attrs in items:
            try:
                preference_service.update_preference(user_id, item_attrs, action)
                updated_count += 1
            except Exception as e:
                logger.warning(f"[DiaryFeedback] 偏好更新失败: item={item_attrs.get('name')}, err={e}")

        logger.info(
            f"[DiaryFeedback] user={user_id}, diary={diary_id}, "
            f"rating={rating}, action={action}, items_updated={updated_count}"
        )

    def _get_diary_items(self, diary_id: int) -> List[Dict[str, Any]]:
        """
        获取日记关联衣物的属性

        Returns:
            物品属性列表 [{color, primary_element, category, style, material, thickness_level}, ...]
        """
        query = """
            SELECT doi.item_source, doi.wardrobe_item_id, doi.seed_item_code, doi.category,
                   i.name, i.primary_element, i.attributes_detail,
                   i.color, i.style, i.material, i.thickness_level
            FROM diary_outfit_items doi
            LEFT JOIN items i ON (
                (doi.item_source = 'wardrobe' AND doi.wardrobe_item_id = i.id)
                OR (doi.item_source = 'public' AND doi.seed_item_code = i.item_code)
            )
            WHERE doi.diary_id = %s
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [diary_id])
                rows = cur.fetchall()

        items = []
        for row in rows:
            attrs = self._extract_item_attributes(dict(row))
            if attrs:
                items.append(attrs)

        return items

    @staticmethod
    def _extract_item_attributes(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        从数据库行提取偏好学习所需的属性

        优先使用显式字段，其次从 attributes_detail JSON 中提取
        """
        attrs_detail = row.get('attributes_detail') or {}

        # 显式字段优先，fallback 到 attributes_detail
        color = row.get('color') or attrs_detail.get('color', '')
        element = row.get('primary_element') or attrs_detail.get('primary_element', '')
        category = row.get('category') or attrs_detail.get('category', '')
        style = row.get('style') or attrs_detail.get('style', '')
        material = row.get('material') or attrs_detail.get('material', '')
        thickness = row.get('thickness_level') or attrs_detail.get('thickness_level', '')

        # 至少有一个属性才返回
        if not any([color, element, category, style, material, thickness]):
            return {}

        return {
            'color': color,
            'primary_element': element,
            'category': category,
            'style': style,
            'material': material,
            'thickness_level': thickness,
        }


# 模块级单例
diary_feedback_service = DiaryFeedbackService()
