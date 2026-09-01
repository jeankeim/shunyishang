""" 
衣橱客户端
用于获取用户衣橱数据和从衣橱中检索物品
"""

import logging
import time
from typing import List, Dict, Optional, Any

import numpy as np

from apps.api.core.database import DatabasePool
from packages.recommendation.config import (
    EXTREME_HOT_TEMP, HOT_TEMP, MILD_HOT_TEMP,
    EXTREME_COLD_TEMP, MILD_COLD_TEMP,
)

logger = logging.getLogger(__name__)


class WardrobeClient:
    """
    用户衣橱客户端
    负责从 user_wardrobe 表检索数据
    """
    
    def __init__(self):
        # 衣橱空状态缓存（避免重复查询）
        self._empty_cache = {}  # {user_id: (is_empty, timestamp)}
        self._cache_ttl = 60  # 缓存 60 秒
    
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
                   temperature_range, functionality, thickness_level, style
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
                            "style": row[14],
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
        limit: int = 20,
        category_constraint: Optional[List[str]] = None,
        explicit_elements: Optional[List[str]] = None,  # 显式五行指令（用户明确要求补X）
        explicit_avoid: Optional[List[str]] = None,  # 硬禁忌（用户显式不要的元素）
    ) -> List[Dict]:
        """
        从用户衣橱进行向量搜索
        
        ⚠️ 必须在 WHERE 子句中强制加上 user_id 过滤！
        
        Args:
            user_id: 用户ID（权限控制必需）
            query_embedding: 查询向量
            target_elements: 目标五行列表（含八字偏好，不用于衣橱硬过滤）
            weather_info: 天气信息
            limit: 返回数量
            category_constraint: 品类约束列表（如["上装"]），为 None 时不限制
            explicit_elements: 显式五行指令（如用户说"推荐属木的裤子"），有值时强制过滤
            explicit_avoid: 硬禁忌（如用户说"不要水"），SQL 层直接排除
        
        Returns:
            匹配的物品列表，每个物品带有 source='wardrobe' 标记
        """
        query_vector = np.array(query_embedding, dtype=np.float32)
        
        # 构建查询条件（使用固定的参数位置）
        conditions = ["user_id = %(user_id)s", "is_active = TRUE", "embedding IS NOT NULL"]
        params = {"user_id": user_id, "query_vector": query_vector.tolist(), "limit": limit}
        
        # 显式五行指令过滤（最高优先级）
        # 当用户明确说"推荐属木的裤子"时，必须只返回木属性衣物
        # 注意：target_elements（八字偏好）不用于衣橱硬过滤，避免衣橱无匹配物品时返回空结果
        if explicit_elements:
            element_placeholders = ",".join([f"%(elem{i})s" for i in range(len(explicit_elements))])
            conditions.append(
                f"(primary_element IN ({element_placeholders}) OR secondary_element IN ({element_placeholders}))"
            )
            for i, elem in enumerate(explicit_elements):
                params[f"elem{i}"] = elem
            logger.info(f"[衣橱检索] 显式指令元素过滤: explicit_elements={explicit_elements}")
        
        # 硬禁忌过滤（用户显式不要的元素，primary 或 secondary 都不能有）
        if explicit_avoid:
            avoid_placeholders = ",".join([f"%(avoid{i})s" for i in range(len(explicit_avoid))])
            conditions.append(
                f"primary_element NOT IN ({avoid_placeholders}) "
                f"AND (secondary_element IS NULL OR secondary_element NOT IN ({avoid_placeholders}))"
            )
            for i, elem in enumerate(explicit_avoid):
                params[f"avoid{i}"] = elem
            logger.info(f"[衣橱检索] 硬禁忌过滤: explicit_avoid={explicit_avoid}")
        
        # 天气过滤
        weather_filter = self._build_wardrobe_weather_filter(weather_info)
        if weather_filter:
            conditions.append(weather_filter)
        
        # 品类约束过滤（新增）
        if category_constraint:
            # 使用参数化查询防止 SQL 注入
            category_placeholders = ",".join([f"%(cat{i})s" for i in range(len(category_constraint))])
            conditions.append(f"category IN ({category_placeholders})")
            for i, cat in enumerate(category_constraint):
                params[f"cat{i}"] = cat
        
        where_clause = " AND ".join(conditions)
        
        sql = f"""
            SELECT 
                id, name, category, primary_element, secondary_element,
                attributes_detail, image_url, gender, applicable_weather, applicable_seasons,
                temperature_range, functionality, thickness_level,
                style,
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
                            "style": row[13],
                            "semantic_score": float(row[14]) if row[14] else 0.5,
                            "source": "wardrobe",  # 标记来源
                            "source_label": "🏠 自有",
                        })
        except Exception as e:
            logger.error(f"衣橱向量搜索失败: {e}")
        
        return items
    
    def _build_wardrobe_weather_filter(self, weather_info: Optional[Dict]) -> str:
        """
        构建衣橱物品的天气过滤条件

        与公共库 filters.py:build_weather_filter 保持 6 档对齐，
        使用相同的厚度词表（厚重/中厚/适中/轻薄/极薄）和中文 JSON 键（最低/最高）。
        """
        if not weather_info:
            return ""

        conditions = []
        temperature = weather_info.get("temperature")

        if temperature is not None:
            if temperature <= EXTREME_COLD_TEMP:
                # 极端低温（≤5°C）：优先厚重/中厚衣物
                conditions.append(
                    f"(thickness_level IN ('厚重', '中厚') OR "
                    f"temperature_range->>'最低' IS NOT NULL AND "
                    f"(temperature_range->>'最低')::int <= {EXTREME_COLD_TEMP})"
                )
            elif temperature <= MILD_COLD_TEMP:
                # 低温（6-10°C）：厚重/中厚/适中
                conditions.append(
                    f"(thickness_level IN ('厚重', '中厚', '适中') OR "
                    f"temperature_range->>'最低' IS NOT NULL AND "
                    f"(temperature_range->>'最低')::int <= {MILD_COLD_TEMP})"
                )
            elif temperature < MILD_HOT_TEMP:
                # 适中温度（11-24°C）：适中/轻薄/极薄/中厚均可
                conditions.append(
                    f"(thickness_level IN ('适中', '轻薄', '极薄', '中厚') OR "
                    f"temperature_range->>'最低' IS NOT NULL AND "
                    f"(temperature_range->>'最低')::int <= {MILD_HOT_TEMP})"
                )
            elif temperature < HOT_TEMP:
                # 中高温（25-27°C）：轻薄/极薄/适中
                conditions.append(
                    f"(thickness_level IN ('轻薄', '极薄', '适中') OR "
                    f"temperature_range->>'最高' IS NOT NULL AND "
                    f"(temperature_range->>'最高')::int >= {MILD_HOT_TEMP})"
                )
            elif temperature < EXTREME_HOT_TEMP:
                # 高温（28-29°C）：轻薄/极薄/适中
                conditions.append(
                    f"(thickness_level IN ('轻薄', '极薄', '适中') OR "
                    f"temperature_range->>'最高' IS NOT NULL AND "
                    f"(temperature_range->>'最高')::int >= {HOT_TEMP})"
                )
            else:
                # 极端高温（≥30°C）：只推轻薄/极薄
                conditions.append(
                    f"(thickness_level IN ('轻薄', '极薄') OR "
                    f"temperature_range->>'最高' IS NOT NULL AND "
                    f"(temperature_range->>'最高')::int >= {EXTREME_HOT_TEMP})"
                )

        # 雨雪天：排除丝绸等不宜沾水的材质
        weather_desc = weather_info.get("weather_desc", "")
        if "雨" in weather_desc or "雪" in weather_desc:
            conditions.append(
                "(attributes_detail::jsonb->>'material' IS NULL OR "
                "attributes_detail::jsonb->>'material' NOT LIKE '%%丝绸%%')"
            )

        if conditions:
            return " AND ".join([f"({c})" for c in conditions])
        return ""
    
    def check_wardrobe_empty(self, user_id: int) -> bool:
        """
        检查用户衣橱是否为空（带缓存优化）
        
        Args:
            user_id: 用户ID
        
        Returns:
            True if empty, False otherwise
        """
        # 检查缓存
        now = time.time()
        if user_id in self._empty_cache:
            cached_result, cached_time = self._empty_cache[user_id]
            if now - cached_time < self._cache_ttl:
                logger.debug(f"[衣橱缓存] 命中: user_id={user_id}, is_empty={cached_result}")
                return cached_result
        
        # 缓存未命中，查询数据库（使用 EXISTS 优化，避免 COUNT(*) 全表扫描）
        query = """
            SELECT EXISTS(
                SELECT 1 FROM user_wardrobe
                WHERE user_id = %s AND is_active = TRUE
                LIMIT 1
            )
        """
        
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (user_id,))
                    has_items = cur.fetchone()[0]
                    is_empty = not has_items
                    
                    # 更新缓存
                    self._empty_cache[user_id] = (is_empty, now)
                    logger.debug(f"[衣橱缓存] 写入: user_id={user_id}, is_empty={is_empty}, has_items={has_items}")
                    
                    return is_empty
        except Exception as e:
            logger.error(f"检查衣橱空状态失败: {e}")
            return False  # 失败时默认为非空，避免阻塞用户


# 单例
wardrobe_client = WardrobeClient()
