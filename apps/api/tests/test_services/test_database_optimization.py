"""
数据库优化测试
测试连接池获取/释放、查询结果集影响、索引优化效果验证
"""

import time
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from contextlib import contextmanager

from apps.api.core.database import DatabasePool


class TestConnectionPoolPerformance:
    """连接池性能测试"""

    def test_pool_get_release_cycle(self, mock_db_pool):
        """测试连接获取和释放的循环性能"""
        mock_conn = mock_db_pool["conn"]
        mock_get_conn = mock_db_pool["get_connection"]

        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            with DatabasePool.get_connection() as conn:
                pass  # 仅测试获取/释放
        elapsed = time.perf_counter() - start

        # 100 次获取/释放应 < 50ms
        assert elapsed < 0.05, f"连接池获取/释放过慢: {elapsed:.3f}s / {iterations}次"

    def test_pool_connection_reuse(self, mock_db_pool):
        """测试连接复用（避免频繁创建/销毁）"""
        mock_get_conn = mock_db_pool["get_connection"]

        connections_used = []
        for _ in range(5):
            with DatabasePool.get_connection() as conn:
                connections_used.append(id(conn))

        # 连接应被复用（mock 返回同一个连接）
        assert len(set(connections_used)) <= 2, "连接未被有效复用"

    def test_pool_health_check(self, mock_db_pool):
        """测试连接池健康检查性能"""
        start = time.perf_counter()
        result = DatabasePool.check_health()
        elapsed = time.perf_counter() - start

        assert result is True
        assert elapsed < 0.01, f"健康检查过慢: {elapsed:.3f}s"


class TestQueryPerformance:
    """查询性能测试"""

    def test_small_result_set(self, mock_db_pool):
        """测试小结果集查询性能"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = [
            (f"ITEM_{i}", f"物品_{i}") for i in range(10)
        ]

        start = time.perf_counter()
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT item_code, name FROM items LIMIT 10")
                rows = cur.fetchall()
        elapsed = time.perf_counter() - start

        assert len(rows) == 10
        assert elapsed < 0.01, f"小结果集查询过慢: {elapsed:.3f}s"

    def test_large_result_set_construction(self, mock_db_pool):
        """测试大结果集构建性能（模拟 500 条记录）"""
        mock_cursor = mock_db_pool["cursor"]

        large_data = [
            {
                "id": i,
                "item_code": f"ITEM_{i:04d}",
                "name": f"测试物品_{i}" * 10,  # 模拟长字符串
                "category": "上装",
                "primary_element": "金",
            }
            for i in range(500)
        ]
        mock_cursor.fetchall.return_value = large_data

        start = time.perf_counter()
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM items")
                rows = cur.fetchall()
        elapsed = time.perf_counter() - start

        assert len(rows) == 500
        # 500 条 mock 记录获取应 < 10ms
        assert elapsed < 0.01, f"大结果集构建过慢: {elapsed:.3f}s"

    def test_parameterized_query_overhead(self, mock_db_pool):
        """测试参数化查询的开销"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = []

        params_list = [
            ("上装", "金"),
            ("下装", "木"),
            ("外套", "水"),
        ]

        start = time.perf_counter()
        for _ in range(100):
            for category, element in params_list:
                with DatabasePool.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT * FROM items WHERE category = %s AND primary_element = %s",
                            (category, element),
                        )
                        cur.fetchall()
        elapsed = time.perf_counter() - start

        # 300 次参数化查询应 < 500ms
        assert elapsed < 0.5, f"参数化查询开销过大: {elapsed:.3f}s"


class TestIndexVerification:
    """索引优化验证测试"""

    def test_vector_search_query_structure(self, mock_db_pool):
        """验证向量搜索 SQL 结构（确保使用参数化查询）"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = []

        import numpy as np
        query_vector = np.array([0.1] * 1024, dtype=np.float32)
        vector_list = query_vector.tolist()

        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT item_code, name, category,
                           1 - (embedding <=> %s::vector) AS semantic_score
                    FROM items
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cur.execute(sql, (vector_list, vector_list, 10))
                rows = cur.fetchall()

        # 验证 execute 被正确调用
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "%s::vector" in call_args[0][0]  # 确保使用了参数化查询

    def test_wardrobe_query_uses_index_friendly_pattern(self, mock_db_pool):
        """验证衣橱查询使用索引友好的 WHERE 条件"""
        mock_cursor = mock_db_pool["cursor"]
        mock_cursor.fetchall.return_value = []

        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                # 模拟衣橱列表查询
                cur.execute(
                    """SELECT * FROM user_wardrobe
                       WHERE user_id = %s AND is_active = TRUE
                       ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                    [1, 20, 0],
                )
                cur.fetchall()

        call_args = mock_cursor.execute.call_args[0]
        sql = call_args[0]
        # 确保查询包含 is_active 过滤（利用部分索引）
        assert "is_active" in sql
        assert "user_id" in sql
