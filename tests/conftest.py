"""
Pytest 配置文件
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """FastAPI 应用 fixture"""
    from apps.api.main import app
    return app


@pytest.fixture
def client(app):
    """测试客户端 fixture"""
    return TestClient(app)


@pytest.fixture
def sample_bazi_request():
    """示例八字请求数据"""
    return {
        "birth_year": 1995,
        "birth_month": 6,
        "birth_day": 15,
        "birth_hour": 10,
        "gender": "男"
    }


@pytest.fixture
def sample_recommend_request():
    """示例推荐请求数据"""
    return {
        "query": "今天穿什么",
        "scene": "日常",
        "top_k": 3
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """测试环境初始化"""
    # 禁用缓存以进行测试
    import os
    os.environ["REDIS_ENABLED"] = "false"
    yield
