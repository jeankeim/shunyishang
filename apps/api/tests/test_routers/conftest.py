"""
API Router 测试 fixtures
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_health_dependencies(mock_db_pool, mock_cache):
    """
    模拟健康检查所需的全部依赖（DB + Cache）

    Usage:
        async def test_health(async_client, mock_health_dependencies):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    return {
        "db": mock_db_pool,
        "cache": mock_cache,
    }
