"""
衣橱客户端测试
覆盖 wardrobe_client.py 所有方法
"""
import pytest
from unittest.mock import patch, MagicMock

from packages.ai_agents.wardrobe_client import WardrobeClient


class TestGetWardrobeItems:
    def test_success(self):
        """成功获取衣橱物品"""
        mock_rows = [
            (1, "红色T恤", "上装", "火", None, {}, "http://img.com/1.jpg", 0,
             "中性", [], ["夏"], {"min": 20, "max": 35}, ["透气"], "轻薄"),
            (2, "蓝色牛仔裤", "下装", "水", None, {}, "http://img.com/2.jpg", 5,
             "男", ["晴"], ["春", "秋"], None, [], "适中"),
        ]
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.get_wardrobe_items(1)
        assert len(result) == 2
        assert result[0]["name"] == "红色T恤"
        assert result[0]["id"] == 1

    def test_empty(self):
        """空衣橱"""
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.get_wardrobe_items(1)
        assert result == []

    def test_error(self):
        """数据库错误返回空列表"""
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_db.get_connection.side_effect = Exception("db error")
            result = client.get_wardrobe_items(1)
        assert result == []


class TestGetWardrobeItemIds:
    def test_success(self):
        mock_rows = [(1,), (2,), (3,)]
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.get_wardrobe_item_ids(1)
        assert result == [1, 2, 3]

    def test_empty(self):
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.get_wardrobe_item_ids(1)
        assert result == []

    def test_error(self):
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_db.get_connection.side_effect = Exception("db error")
            result = client.get_wardrobe_item_ids(1)
        assert result == []


class TestVectorSearchWardrobe:
    def test_success(self):
        """成功向量搜索"""
        mock_rows = [
            (1, "红色T恤", "上装", "火", None, {}, "http://img.com/1.jpg",
             "中性", ["晴"], ["夏"], {"min": 20, "max": 35}, ["透气"], "轻薄", 0.9),
        ]
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.vector_search_wardrobe(1, [0.1] * 1024)
        assert len(result) == 1
        assert result[0]["name"] == "红色T恤"
        assert result[0]["source"] == "wardrobe"
        assert result[0]["semantic_score"] == 0.9

    def test_empty_result(self):
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.vector_search_wardrobe(1, [0.1] * 1024)
        assert result == []

    def test_with_weather_info(self):
        """带天气信息"""
        mock_rows = []
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.vector_search_wardrobe(
                1, [0.1] * 1024,
                weather_info={"temperature": 3, "weather_desc": "雪"},
            )
        assert result == []

    def test_error(self):
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_db.get_connection.side_effect = Exception("db error")
            result = client.vector_search_wardrobe(1, [0.1] * 1024)
        assert result == []

    def test_none_semantic_score(self):
        """semantic_score 为 None 时使用默认值 0.5"""
        mock_rows = [
            (1, "T恤", "上装", "火", None, {}, "", "中性", [], [], None, [], None, None),
        ]
        client = WardrobeClient()
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.vector_search_wardrobe(1, [0.1] * 1024)
        assert result[0]["semantic_score"] == 0.5


class TestBuildWeatherFilter:
    def test_no_weather(self):
        client = WardrobeClient()
        assert client._build_wardrobe_weather_filter(None) == ""
        assert client._build_wardrobe_weather_filter({}) == ""

    def test_extreme_cold(self):
        client = WardrobeClient()
        result = client._build_wardrobe_weather_filter({"temperature": 3, "weather_desc": "雪"})
        assert "thickness_level" in result
        assert "丝绸" in result  # 雪天排除丝绸

    def test_cold(self):
        client = WardrobeClient()
        result = client._build_wardrobe_weather_filter({"temperature": 10, "weather_desc": "阴"})
        assert "thickness_level" in result

    def test_hot(self):
        client = WardrobeClient()
        result = client._build_wardrobe_weather_filter({"temperature": 30, "weather_desc": "晴"})
        assert "thickness_level" in result

    def test_mild_no_filter(self):
        """温和天气（11-24°C）添加宽松温度过滤（与公共库 6 档对齐）"""
        client = WardrobeClient()
        result = client._build_wardrobe_weather_filter({"temperature": 20, "weather_desc": "多云"})
        # 6 档对齐后，适中温度也会生成宽松过滤（允许适中/轻薄/极薄/中厚）
        assert "thickness_level" in result
        assert "适中" in result

    def test_rain_excludes_silk(self):
        client = WardrobeClient()
        result = client._build_wardrobe_weather_filter({"temperature": 20, "weather_desc": "雨"})
        assert "丝绸" in result

    def test_no_temperature(self):
        """无温度只有天气描述"""
        client = WardrobeClient()
        result = client._build_wardrobe_weather_filter({"weather_desc": "雨"})
        assert "丝绸" in result


class TestCheckWardrobeEmpty:
    def test_empty(self):
        """衣橱为空"""
        client = WardrobeClient()
        client._empty_cache = {}  # 清除缓存
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = (False,)  # has_items = False
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.check_wardrobe_empty(1)
        assert result is True

    def test_not_empty(self):
        """衣橱不为空"""
        client = WardrobeClient()
        client._empty_cache = {}
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = (True,)  # has_items = True
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.check_wardrobe_empty(1)
        assert result is False

    def test_cache_hit(self):
        """缓存命中"""
        client = WardrobeClient()
        import time
        client._empty_cache = {1: (True, time.time())}
        result = client.check_wardrobe_empty(1)
        assert result is True

    def test_cache_expired(self):
        """缓存过期重新查询"""
        client = WardrobeClient()
        import time
        client._empty_cache = {1: (True, time.time() - 120)}  # 120秒前，已过期
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = (True,)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            result = client.check_wardrobe_empty(1)
        assert result is False

    def test_error_returns_false(self):
        """错误时返回 False（非空）"""
        client = WardrobeClient()
        client._empty_cache = {}
        with patch("packages.ai_agents.wardrobe_client.DatabasePool") as mock_db:
            mock_db.get_connection.side_effect = Exception("db error")
            result = client.check_wardrobe_empty(1)
        assert result is False


class TestGetEmbeddingModel:
    def test_returns_none(self):
        """_get_embedding_model 委托给 nodes 模块"""
        client = WardrobeClient()
        with patch("packages.ai_agents.nodes._get_embedding_model", return_value=None):
            result = client._get_embedding_model()
        assert result is None
