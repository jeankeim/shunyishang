"""
衣橱服务层
处理用户衣橱 CRUD 操作
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.schemas.wardrobe import (
    WardrobeItemCreate,
    WardrobeItemResponse,
    WardrobeItemListResponse,
    FeedbackCreate,
    FeedbackResponse,
    AITaggingResult,
)

logger = logging.getLogger(__name__)


class WardrobeService:
    """衣橱服务"""
    
    @staticmethod
    async def get_wardrobe_items(
        user_id: int,
        element_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> WardrobeItemListResponse:
        """获取用户衣橱物品列表"""
        
        # 构建查询
        base_query = """
            SELECT id, user_id, item_code, name, category, image_url,
                   primary_element, secondary_element, attributes_detail,
                   is_custom, is_active, wear_count, last_worn_date,
                   is_favorite, notes, created_at, updated_at,
                   gender, applicable_weather, applicable_seasons,
                   temperature_range, functionality, thickness_level, energy_intensity
            FROM user_wardrobe
            WHERE user_id = %s AND is_active = TRUE
        """
        params = [user_id]
        
        if element_filter:
            base_query += " AND primary_element = %s"
            params.append(element_filter)
        
        if category_filter:
            base_query += " AND category = %s"
            params.append(category_filter)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM ({base_query}) sub"
        
        # 获取列表
        list_query = base_query + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取列表
                cur.execute(list_query, params)
                rows = cur.fetchall()
                
                # 获取五行统计
                stats_query = """
                    SELECT primary_element, COUNT(*) as count
                    FROM user_wardrobe
                    WHERE user_id = %s AND is_active = TRUE
                    GROUP BY primary_element
                """
                cur.execute(stats_query, [user_id])
                stats_rows = cur.fetchall()
                
                # 获取总数
                cur.execute(count_query, params[:len(params)-2] if element_filter or category_filter else [user_id])
                total = cur.fetchone()['total'] if cur.fetchone() else 0
        
        # 转换为响应格式
        items = [WardrobeItemResponse(**dict(row)) for row in rows]
        element_stats = {row['primary_element']: row['count'] for row in stats_rows}
        
        return WardrobeItemListResponse(
            items=items,
            total=total if isinstance(total, int) else 0,
            element_stats=element_stats
        )
    
    @staticmethod
    async def add_wardrobe_item(
        user_id: int,
        item_data: WardrobeItemCreate,
        embedding: Optional[List[float]] = None
    ) -> WardrobeItemResponse:
        """添加衣物到衣橱"""
        
        is_custom = item_data.item_code is None
        
        query = """
            INSERT INTO user_wardrobe (
                user_id, item_code, name, category, image_url,
                primary_element, secondary_element, attributes_detail,
                is_custom, embedding,
                gender, applicable_weather, applicable_seasons,
                temperature_range, functionality, thickness_level, energy_intensity
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, item_code, name, category, image_url,
                      primary_element, secondary_element, attributes_detail,
                      is_custom, is_active, wear_count, last_worn_date,
                      is_favorite, notes, created_at, updated_at,
                      gender, applicable_weather, applicable_seasons,
                      temperature_range, functionality, thickness_level, energy_intensity
        """
        
        params = [
            user_id,
            item_data.item_code,
            item_data.name,
            item_data.category,
            item_data.image_url,
            item_data.primary_element,
            item_data.secondary_element,
            item_data.attributes_detail,
            is_custom,
            embedding,  # 向量嵌入
            item_data.gender,
            item_data.applicable_weather,
            item_data.applicable_seasons,
            item_data.temperature_range,
            item_data.functionality,
            item_data.thickness_level,
            item_data.energy_intensity,
        ]
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()
        
        return WardrobeItemResponse(**dict(row))
    
    @staticmethod
    async def delete_wardrobe_item(user_id: int, item_id: int) -> bool:
        """删除衣橱物品（软删除）"""
        
        query = """
            UPDATE user_wardrobe
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s AND is_active = TRUE
        """
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [item_id, user_id])
                affected = cur.rowcount
                conn.commit()
        
        return affected > 0
    
    @staticmethod
    async def get_wardrobe_item_ids(user_id: int) -> List[int]:
        """获取用户衣橱物品ID列表"""
        
        query = """
            SELECT id FROM user_wardrobe
            WHERE user_id = %s AND is_active = TRUE
        """
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [user_id])
                rows = cur.fetchall()
        
        return [row[0] for row in rows]
    
    @staticmethod
    async def create_feedback(
        user_id: int,
        feedback_data: FeedbackCreate,
        query_text: Optional[str] = None,
        scene: Optional[str] = None
    ) -> FeedbackResponse:
        """创建反馈记录"""
        
        query = """
            INSERT INTO feedback_logs (
                user_id, session_id, query_text, scene,
                item_id, item_code, item_source, action, feedback_reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, action, created_at
        """
        
        params = [
            user_id,
            feedback_data.session_id,
            query_text,
            scene,
            feedback_data.item_id,
            feedback_data.item_code,
            feedback_data.item_source,
            feedback_data.action,
            feedback_data.feedback_reason
        ]
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()
        
        return FeedbackResponse(**dict(row))
    
    @staticmethod
    async def get_user_feedback_history(
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户反馈历史"""
        
        query = """
            SELECT id, session_id, query_text, scene, item_id, item_code,
                   item_source, action, feedback_reason, created_at
            FROM feedback_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id, limit])
                rows = cur.fetchall()
        
        return [dict(row) for row in rows]


# 便捷导出
wardrobe_service = WardrobeService()
