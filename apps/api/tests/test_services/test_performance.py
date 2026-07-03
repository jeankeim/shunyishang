"""
服务层性能基准测试
测试关键服务的响应时间、缓存效果和 embedding 生成性能
使用 mock 基础设施，不连接真实数据库或外部 API
"""

import time
import json
import pytest
from unittest.mock import patch, MagicMock

from apps.api.services.embedding_service import EmbeddingService, build_wardrobe_embedding_text
from apps.api.services.wardrobe_service import WardrobeService


class TestEmbeddingPerformance:
    """Embedding 生成性能测试"""

    def test_build_embedding_text_performance(self):
        """测试 embedding 文本构建速度（纯 CPU 操作，应极快）"""
        ai_result = {
            "color": "红色",
            "color_element": "火",
            "energy_intensity": 0.85,
            "material": "羊毛",
            "material_element": "土",
            "shape": "长方",
            "details": ["V领", "珍珠扣"],
            "tags": ["商务", "保暖"],
        }

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            text = build_wardrobe_embedding_text(
                name="红色羊毛大衣",
                category="外套",
                ai_result=ai_result,
                description="冬天穿的红色大衣",
            )
        elapsed = time.perf_counter() - start

        # 1000 次文本构建应在 100ms 内完成
        assert elapsed < 0.1, f"文本构建过慢: {elapsed:.3f}s / {iterations}次"
        assert isinstance(text, str)
        assert len(text) > 0

    def test_build_embedding_text_none_ai_result(self):
        """测试 AI 结果为空时的文本构建性能"""
        start = time.perf_counter()
        for _ in range(1000):
            text = build_wardrobe_embedding_text(
                name="简单T恤",
                category="上装",
                ai_result=None,
                description=None,
            )
        elapsed = time.perf_counter() - start
        assert elapsed < 0.05, f"空 AI 结果文本构建过慢: {elapsed:.3f}s"

    @patch("apps.api.services.embedding_service._encode_text_with_dashscope")
    def test_generate_embedding_mock_latency(self, mock_encode):
        """测试 embedding 生成的调用链路（mock API，验证非 API 部分开销）"""
        mock_encode.return_value = [0.1] * 1024

        service = EmbeddingService()
        start = time.perf_counter()
        result = service.generate_embedding("测试文本")
        elapsed = time.perf_counter() - start

        assert len(result) == 1024
        # Mock 调用应极快（< 10ms）
        assert elapsed < 0.01, f"Mock embedding 生成过慢: {elapsed:.3f}s"

    @patch("apps.api.services.embedding_service._encode_text_with_dashscope")
    def test_batch_embedding_performance(self, mock_encode):
        """测试批量 embedding 生成性能"""
        mock_encode.return_value = [0.1] * 1024

        service = EmbeddingService()
        texts = [f"测试文本_{i}" for i in range(10)]

        start = time.perf_counter()
        results = service.generate_embedding_batch(texts)
        elapsed = time.perf_counter() - start

        assert len(results) == 10
        # 10 个 mock 调用应 < 50ms
        assert elapsed < 0.05, f"批量 embedding 过慢: {elapsed:.3f}s / 10次"

    def test_compute_similarity_performance(self):
        """测试向量相似度计算性能"""
        import numpy as np

        service = EmbeddingService()
        # 预构建 numpy 向量，减少循环内转换开销
        vec1 = np.random.rand(1024).tolist()
        vec2 = np.random.rand(1024).tolist()

        # 预热
        service.compute_similarity(vec1, vec2)

        start = time.perf_counter()
        for _ in range(100):
            score = service.compute_similarity(vec1, vec2)
        elapsed = time.perf_counter() - start

        assert isinstance(score, float)
        # 100 次 1024 维向量相似度计算（含 list→numpy 转换）应 < 5s
        assert elapsed < 5.0, f"相似度计算过慢: {elapsed:.3f}s / 100次"


class TestWardrobeServicePerformance:
    """衣橱服务性能测试"""

    @pytest.mark.asyncio
    async def test_get_wardrobe_items_mock_performance(self, mock_db_pool):
        """测试衣橱列表查询的 mock 链路性能"""
        mock_cursor = mock_db_pool["cursor"]

        # 模拟返回数据
        mock_rows = [
            {
                "id": i,
                "user_id": 1,
                "item_code": f"ITEM_{i:03d}",
                "name": f"测试衣物_{i}",
                "category": "上装",
                "image_url": "https://test.com/img.png",
                "primary_element": "金",
                "secondary_element": "木",
                "attributes_detail": {},
                "is_custom": False,
                "is_active": True,
                "wear_count": 0,
                "last_worn_date": None,
                "is_favorite": False,
                "notes": None,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "gender": "中性",
                "applicable_weather": [],
                "applicable_seasons": [],
                "temperature_range": {},
                "functionality": [],
                "thickness_level": "适中",
                "energy_intensity": 0.5,
            }
            for i in range(1, 11)
        ]

        # 模拟 fetchall 返回不同结果（列表、统计、总数）
        call_count = {"n": 0}

        def side_effect_fetchall():
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_rows  # 列表查询
            elif call_count["n"] == 2:
                return [{"primary_element": "金", "count": 5}, {"primary_element": "木", "count": 5}]
            return []

        def side_effect_fetchone():
            return {"total": 10}

        mock_cursor.fetchall.side_effect = side_effect_fetchall
        mock_cursor.fetchone.side_effect = side_effect_fetchone

        start = time.perf_counter()
        result = await WardrobeService.get_wardrobe_items(user_id=1, limit=10)
        elapsed = time.perf_counter() - start

        assert result.total == 10
        assert len(result.items) == 10
        # Mock 查询应极快
        assert elapsed < 0.05, f"衣橱列表查询过慢: {elapsed:.3f}s"
