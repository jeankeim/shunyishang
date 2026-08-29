"""
日记服务测试
"""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from apps.api.schemas.diary import (
    CreateDiaryRequest,
    UpdateDiaryRequest,
    DiaryItemRequest,
)


class TestDiaryService:
    """日记服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库连接"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with patch("apps.api.services.diary_service.DatabasePool") as mock_pool:
            mock_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            yield {"conn": mock_conn, "cursor": mock_cursor}

    def test_create_diary_basic(self, mock_db):
        """测试创建基础日记"""
        from apps.api.services.diary_service import DiaryService

        created_at = datetime(2025, 1, 15, 10, 0, 0)
        mock_db["cursor"].execute.return_value = None
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "user_id": 1, "diary_date": date(2025, 1, 15),
            "mood": "happy", "weather_snapshot": {}, "occasion": "日常",
            "notes": "测试日记", "rating": 4, "ai_review": {},
            "image_urls": [], "created_at": created_at, "updated_at": created_at,
        }

        req = CreateDiaryRequest(
            diary_date=date(2025, 1, 15),
            mood="happy",
            occasion="日常",
            notes="测试日记",
            rating=4,
        )
        result = DiaryService.create_diary(1, req)
        assert result.id == 1
        assert result.mood == "happy"
        assert result.rating == 4

    def test_create_diary_with_items(self, mock_db):
        """测试创建日记带关联衣物"""
        from apps.api.services.diary_service import DiaryService

        created_at = datetime(2025, 1, 15, 10, 0, 0)
        mock_db["cursor"].fetchone.return_value = {
            "id": 2, "user_id": 1, "diary_date": date(2025, 1, 15),
            "mood": "excited", "weather_snapshot": {}, "occasion": None,
            "notes": None, "rating": 5, "ai_review": {},
            "image_urls": [], "created_at": created_at, "updated_at": created_at,
        }

        req = CreateDiaryRequest(
            diary_date=date(2025, 1, 15),
            mood="excited",
            rating=5,
            items=[
                DiaryItemRequest(item_source="wardrobe", wardrobe_item_id=1, category="上装"),
            ],
        )
        result = DiaryService.create_diary(1, req)
        assert result.id == 2

    def test_get_diaries_pagination(self, mock_db):
        """测试分页查询"""
        from apps.api.services.diary_service import DiaryService

        created_at = datetime(2025, 1, 15, 10, 0, 0)
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # count query
                mock_db["cursor"].fetchone.return_value = {"total": 1}
            elif call_count[0] == 2:
                # list query
                mock_db["cursor"].fetchall.return_value = [
                    {
                        "id": 1, "user_id": 1, "diary_date": date(2025, 1, 15),
                        "mood": "happy", "weather_snapshot": {}, "occasion": None,
                        "notes": None, "rating": 4, "ai_review": {},
                        "image_urls": [], "created_at": created_at, "updated_at": created_at,
                    }
                ]
            elif call_count[0] == 3:
                # _get_diary_items query
                mock_db["cursor"].fetchall.return_value = []

        mock_db["cursor"].execute.side_effect = side_effect

        result = DiaryService.get_diaries(1, page=1, size=20)
        assert result.page == 1
        assert result.size == 20

    def test_delete_diary(self, mock_db):
        """测试删除日记"""
        from apps.api.services.diary_service import DiaryService

        mock_db["cursor"].rowcount = 1
        result = DiaryService.delete_diary(1, 1)
        assert result is True

    def test_delete_diary_not_found(self, mock_db):
        """测试删除不存在的日记"""
        from apps.api.services.diary_service import DiaryService

        mock_db["cursor"].rowcount = 0
        result = DiaryService.delete_diary(999, 1)
        assert result is False

    def test_get_calendar(self, mock_db):
        """测试日历视图"""
        from apps.api.services.diary_service import DiaryService

        mock_db["cursor"].fetchall.return_value = [
            {"diary_date": date(2025, 1, 15), "mood": "happy", "rating": 4, "has_items": True},
            {"diary_date": date(2025, 1, 16), "mood": "calm", "rating": 3, "has_items": False},
        ]

        result = DiaryService.get_calendar(1, 2025, 1)
        assert result.year == 2025
        assert result.month == 1
        assert len(result.entries) == 2

    def test_get_stats(self, mock_db):
        """测试统计数据"""
        from apps.api.services.diary_service import DiaryService

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_db["cursor"].fetchone.return_value = {
                    "total_diaries": 10, "avg_rating": 4.2,
                }
            elif call_count[0] == 2:
                mock_db["cursor"].fetchall.return_value = [
                    {"mood": "happy", "count": 5},
                    {"mood": "calm", "count": 3},
                ]
            elif call_count[0] == 3:
                mock_db["cursor"].fetchone.return_value = {"total": 15}
            elif call_count[0] == 4:
                mock_db["cursor"].fetchall.return_value = []

        mock_db["cursor"].execute.side_effect = side_effect

        result = DiaryService.get_stats(1)
        assert result.total_diaries == 10
        assert result.mood_distribution.get("happy") == 5

    def test_user_isolation(self, mock_db):
        """测试用户隔离"""
        from apps.api.services.diary_service import DiaryService

        mock_db["cursor"].fetchone.return_value = None
        result = DiaryService.get_diary_by_id(1, 999)
        assert result is None

    def test_add_item_to_diary(self, mock_db):
        """测试添加衣物到日记"""
        from apps.api.services.diary_service import DiaryService

        created_at = datetime(2025, 1, 15, 10, 0, 0)
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # 验证日记归属
                mock_db["cursor"].fetchone.return_value = {"id": 1}
            elif call_count[0] == 2:
                # 插入衣物
                mock_db["cursor"].fetchone.return_value = {
                    "id": 1, "diary_id": 1, "item_source": "wardrobe",
                    "wardrobe_item_id": 5, "seed_item_code": None,
                    "category": "上装", "notes": None, "created_at": created_at,
                }

        mock_db["cursor"].execute.side_effect = side_effect

        item_data = DiaryItemRequest(item_source="wardrobe", wardrobe_item_id=5, category="上装")
        result = DiaryService.add_item_to_diary(1, 1, item_data)
        assert result is not None
        assert result.wardrobe_item_id == 5

    def test_remove_item_from_diary(self, mock_db):
        """测试从日记移除衣物（含穿着计数回退联动）"""
        from apps.api.services.diary_service import DiaryService

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # 验证日记归属
                mock_db["cursor"].fetchone.return_value = {"id": 1}
            elif call_count[0] == 2:
                # 查询被移除的关联行
                mock_db["cursor"].fetchone.return_value = {
                    "item_source": "wardrobe", "wardrobe_item_id": 5,
                }
            elif call_count[0] == 3:
                # 删除关联行
                mock_db["cursor"].rowcount = 1

        mock_db["cursor"].execute.side_effect = side_effect

        result = DiaryService.remove_item_from_diary(1, 1, 1)
        assert result is True
        # 衣橱衣物移除后应触发穿着计数回退（额外 2 条 UPDATE）
        assert call_count[0] == 5
