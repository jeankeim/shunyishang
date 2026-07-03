"""
Service 层测试 fixtures
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_embedding_service():
    """模拟 Embedding 服务，避免调用真实 DashScope API"""
    with patch("apps.api.services.embedding_service") as mock_svc:
        mock_svc.generate_embedding.return_value = [0.1] * 1024
        yield mock_svc


@pytest.fixture
def mock_r2_storage():
    """模拟 R2 对象存储，避免调用真实 Cloudflare API"""
    with patch("apps.api.services.r2_storage") as mock_storage:
        mock_storage.upload_file.return_value = "https://pub-test.r2.dev/test.png"
        mock_storage.delete_file.return_value = True
        yield mock_storage
