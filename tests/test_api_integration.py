"""
API 集成测试
测试各接口的连通性和基本功能
"""

import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


class TestHealthAPI:
    """健康检查接口测试"""
    
    def test_health_check(self):
        """测试健康检查接口"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "db" in data
        assert "env" in data
    
    def test_docs_accessible(self):
        """测试文档接口可访问"""
        response = client.get("/docs")
        assert response.status_code == 200


class TestBaziAPI:
    """八字计算接口测试"""
    
    def test_bazi_calculate_success(self):
        """测试八字计算成功"""
        payload = {
            "birth_year": 1995,
            "birth_month": 6,
            "birth_day": 15,
            "birth_hour": 10,
            "gender": "男"
        }
        response = client.post("/api/v1/bazi/calculate", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "pillars" in data
        assert "eight_chars" in data
        assert "suggested_elements" in data
        assert len(data["eight_chars"]) == 8
    
    def test_bazi_calculate_invalid_gender(self):
        """测试无效性别"""
        payload = {
            "birth_year": 1995,
            "birth_month": 6,
            "birth_day": 15,
            "birth_hour": 10,
            "gender": "未知"  # 无效性别
        }
        response = client.post("/api/v1/bazi/calculate", json=payload)
        assert response.status_code == 422  # 验证错误
    
    def test_bazi_calculate_invalid_date(self):
        """测试无效日期"""
        payload = {
            "birth_year": 1995,
            "birth_month": 13,  # 无效月份
            "birth_day": 15,
            "birth_hour": 10,
            "gender": "男"
        }
        response = client.post("/api/v1/bazi/calculate", json=payload)
        assert response.status_code == 422


class TestWeatherAPI:
    """天气接口测试"""
    
    def test_weather_get(self):
        """测试获取天气"""
        response = client.get("/api/v1/weather/weather?city=北京")
        assert response.status_code == 200
        
        data = response.json()
        assert "city" in data
        assert "temperature" in data
        assert "weather" in data
        assert "element" in data
        assert data["city"] == "北京"
    
    def test_weather_elements(self):
        """测试天气五行映射"""
        response = client.get("/api/v1/weather/weather/elements")
        assert response.status_code == 200
        
        data = response.json()
        assert "水" in data
        assert "火" in data
        assert "木" in data
        assert "金" in data
        assert "土" in data


class TestRecommendAPI:
    """推荐接口测试"""
    
    def test_recommend_basic(self):
        """测试基础推荐"""
        payload = {
            "query": "今天穿什么",
            "scene": "日常",
            "top_k": 3
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "analysis" in data
        assert "items" in data
        assert "reason" in data
        assert len(data["items"]) <= 3
    
    def test_recommend_with_bazi(self):
        """测试带八字的推荐"""
        payload = {
            "query": "今天穿什么",
            "scene": "面试",
            "bazi": {
                "birth_year": 1995,
                "birth_month": 6,
                "birth_day": 15,
                "birth_hour": 10,
                "gender": "男"
            },
            "top_k": 5
        }
        response = client.post("/api/v1/recommend", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "analysis" in data
        assert "items" in data
        # 验证分析中包含八字相关信息
        if "target_elements" in data["analysis"]:
            assert len(data["analysis"]["target_elements"]) > 0


class TestCacheIntegration:
    """缓存集成测试"""
    
    def test_bazi_cache(self):
        """测试八字缓存"""
        payload = {
            "birth_year": 1990,
            "birth_month": 1,
            "birth_day": 1,
            "birth_hour": 12,
            "gender": "男"
        }
        
        # 第一次请求
        response1 = client.post("/api/v1/bazi/calculate", json=payload)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # 第二次请求（应该命中缓存）
        response2 = client.post("/api/v1/bazi/calculate", json=payload)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 结果应该相同
        assert data1["eight_chars"] == data2["eight_chars"]
        assert data1["suggested_elements"] == data2["suggested_elements"]


class TestErrorHandling:
    """错误处理测试"""
    
    def test_404_error(self):
        """测试404错误"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """测试方法不允许"""
        response = client.get("/api/v1/recommend")  # POST接口用GET访问
        assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
