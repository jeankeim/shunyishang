"""
衣橱客户端
用于获取用户衣橱数据和从衣橱中检索物品
"""

import logging
from typing import List, Dict, Optional, Any

import numpy as np

from apps.api.core.database import DatabasePool

logger = logging.getLogger(__name__)


class WardrobeClient:
    """
    用户衣橱客户端
    负责从 user_wardrobe 表检索数据
    """
    
    def _get_embedding_model(self):
        """延迟加载 embedding 模型（避免循环导入）"""
        from packages.ai_agents.nodes import _get_embedding_model
        return _get_embedding_model()
    
    def get_wardrobe_items(self, user_id: int) -> List[Dict]:
        """
        获取用户衣橱物品列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            物品列表
        """
        query = """
            SELECT id, name, category, primary_element, secondary_element,
                   attributes_detail, image_url, wear_count,
                   gender, applicable_weather, applicable_seasons,
                   temperature_range, functionality, thickness_level
            FROM user_wardrobe
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
        """
        
        items = []
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [user_id])
                    rows = cur.fetchall()
                    
                    for row in rows:
                        items.append({
                            "id": row[0],
                            "name": row[1],
                            "category": row[2],
                            "primary_element": row[3],
                            "secondary_element": row[4],
                            "attributes_detail": row[5],
                            "image_url": row[6],
                            "wear_count": row[7],
                            "gender": row[8],
                            "applicable_weather": row[9],
                            "applicable_seasons": row[10],
                            "temperature_range": row[11],
                            "functionality": row[12],
                            "thickness_level": row[13],
                        })
        except Exception as e:
            logger.error(f"获取用户衣橱失败: {e}")
        
        return items
    
    def get_wardrobe_item_ids(self, user_id: int) -> List[int]:
        """
        获取用户衣橱物品ID列表
        
        Args:
            user_id: 用户ID
        
        Returns:
            物品ID列表
        """
        query = """
            SELECT id FROM user_wardrobe
            WHERE user_id = %s AND is_active = TRUE
        """
        
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [user_id])
                    rows = cur.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取衣橱ID列表失败: {e}")
            return []
    
    def vector_search_wardrobe(
        self,
        user_id: int,
        query_embedding: List[float],
        target_elements: Optional[List[str]] = None,
        weather_info: Optional[Dict] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        从用户衣橱进行向量搜索
        
        ⚠️ 必须在 WHERE 子句中强制加上 user_id 过滤！
        
        Args:
            user_id: 用户ID（权限控制必需）
            query_embedding: 查询向量
            target_elements: 目标五行列表
            weather_info: 天气信息
            limit: 返回数量
        
        Returns:
            匹配的物品列表，每个物品带有 source='wardrobe' 标记
        """
        query_vector = np.array(query_embedding, dtype=np.float32)
        
        # 构建查询条件（使用固定的参数位置）
        conditions = ["user_id = %(user_id)s", "is_active = TRUE", "embedding IS NOT NULL"]
        params = {"user_id": user_id, "query_vector": query_vector.tolist(), "limit": limit}
        
        # 注意：衣橱搜索不根据target_elements过滤，让后续打分阶段处理五行匹配
        # 这样可以避免衣橱物品五行不匹配时返回空结果
        
        # 天气过滤
        weather_filter = self._build_wardrobe_weather_filter(weather_info)
        if weather_filter:
            conditions.append(weather_filter)
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT 
                id, name, category, primary_element, secondary_element,
                attributes_detail, image_url, gender, applicable_weather, applicable_seasons,
                temperature_range, functionality, thickness_level,
                1 - (embedding <=> %(query_vector)s::vector) AS semantic_score
            FROM user_wardrobe
            WHERE {where_clause}
            ORDER BY embedding <=> %(query_vector)s::vector
            LIMIT %(limit)s
        """
        
        items = []
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    
                    for row in rows:
                        items.append({
                            "id": row[0],
                            "name": row[1],
                            "category": row[2],
                            "primary_element": row[3],
                            "secondary_element": row[4],
                            "attributes_detail": row[5],
                            "image_url": row[6],
                            "gender": row[7],
                            "applicable_weather": row[8],
                            "applicable_seasons": row[9],
                            "temperature_range": row[10],
                            "functionality": row[11],
                            "thickness_level": row[12],
                            "semantic_score": float(row[13]) if row[13] else 0.5,
                            "source": "wardrobe",  # 标记来源
                            "source_label": "🏠 自有",
                        })
        except Exception as e:
            logger.error(f"衣橱向量搜索失败: {e}")
        
        return items
    
    def _build_wardrobe_weather_filter(self, weather_info: Optional[Dict]) -> str:
        """
        构建衣橱物品的天气过滤条件
        
        复用 Week 2 的天气过滤逻辑
        """
        if not weather_info:
            return ""
        
        conditions = []
        temperature = weather_info.get("temperature")
        weather_desc = weather_info.get("weather_desc", "")
        
        # 温度过滤
        if temperature is not None:
            if temperature < 5:
                # 极冷：优先厚重/加厚衣物
                conditions.append(
                    "(thickness_level IN ('厚重', '加厚') OR "
                    "temperature_range::jsonb->>'min' IS NOT NULL AND "
                    "(temperature_range::jsonb->>'min')::int < 10)"
                )
            elif temperature < 15:
                # 中等温度
                conditions.append(
                    "(thickness_level IN ('适中', '加厚') OR "
                    "temperature_range::jsonb->>'min' IS NOT NULL)"
                )
            elif temperature > 28:
                # 炎热：优先轻薄
                conditions.append(
                    "(thickness_level = '轻薄' OR "
                    "temperature_range::jsonb->>'max' IS NOT NULL AND "
                    "(temperature_range::jsonb->>'max')::int > 25)"
                )
        
        # 天气状况过滤
        if "雨" in weather_desc or "雪" in weather_desc:
            # 雨雪天：排除不宜沾水的衣物（如丝绸）
            conditions.append(
                "(attributes_detail::jsonb->>'material' IS NULL OR "
                "attributes_detail::jsonb->>'material' NOT LIKE '%丝绸%')"
            )
        
        if conditions:
            return " AND ".join([f"({c})" for c in conditions])
        return ""
    
    def check_wardrobe_empty(self, user_id: int) -> bool:
        """
        检查用户衣橱是否为空
        
        Args:
            user_id: 用户ID
        
        Returns:
            True if empty, False otherwise
        """
        query = """
            SELECT COUNT(*) FROM user_wardrobe
            WHERE user_id = %s AND is_active = TRUE
        """
        
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [user_id])
                    count = cur.fetchone()[0]
                    logger.info(f"检查衣橱状态: user_id={user_id}, count={count}")
                    return count == 0
        except Exception as e:
            logger.error(f"检查衣橱状态失败: user_id={user_id}, error={e}")
            return True


# 单例
wardrobe_client = WardrobeClient()
