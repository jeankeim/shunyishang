"""
推送服务测试
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestPushService:
    """推送服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库连接"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with patch("apps.api.services.push_service.DatabasePool") as mock_pool:
            mock_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            yield {"conn": mock_conn, "cursor": mock_cursor}

    def test_send_push(self, mock_db):
        """测试发送推送"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].fetchone.return_value = {"id": 1}
        result = PushService.send_push(1, "fortune_daily", "今日运势", "查看您的运势")
        assert result == 1

    def test_send_push_with_data(self, mock_db):
        """测试发送带数据的推送"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].fetchone.return_value = {"id": 2}
        result = PushService.send_push(1, "system", "系统通知", data={"action": "update"})
        assert result == 2

    def test_get_push_history(self, mock_db):
        """测试推送历史"""
        from apps.api.services.push_service import PushService

        now = datetime(2025, 1, 15, 10, 0, 0)
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_db["cursor"].fetchone.return_value = {"total": 2}
            elif call_count[0] == 2:
                mock_db["cursor"].fetchall.return_value = [
                    {
                        "id": 1, "type": "fortune_daily", "title": "今日运势",
                        "body": "查看运势", "data": {}, "sent_at": now, "read_at": None,
                    },
                    {
                        "id": 2, "type": "diary_reminder", "title": "日记提醒",
                        "body": "记录穿搭", "data": "{}", "sent_at": now, "read_at": now,
                    },
                ]

        mock_db["cursor"].execute.side_effect = side_effect

        result = PushService.get_push_history(1, page=1, size=20)
        assert result.total == 2
        assert len(result.notifications) == 2
        assert result.notifications[0].type == "fortune_daily"

    def test_get_push_history_empty(self, mock_db):
        """测试空推送历史"""
        from apps.api.services.push_service import PushService

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_db["cursor"].fetchone.return_value = {"total": 0}
            elif call_count[0] == 2:
                mock_db["cursor"].fetchall.return_value = []

        mock_db["cursor"].execute.side_effect = side_effect

        result = PushService.get_push_history(1)
        assert result.total == 0
        assert len(result.notifications) == 0

    def test_mark_as_read(self, mock_db):
        """测试标记已读"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].rowcount = 1
        result = PushService.mark_as_read(1, 1)
        assert result is True

    def test_mark_as_read_already_read(self, mock_db):
        """测试重复标记已读"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].rowcount = 0
        result = PushService.mark_as_read(1, 1)
        assert result is False

    def test_get_unread_count(self, mock_db):
        """测试未读数量"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].fetchone.return_value = {"cnt": 5}
        result = PushService.get_unread_count(1)
        assert result.count == 5

    def test_get_unread_count_zero(self, mock_db):
        """测试零未读"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].fetchone.return_value = {"cnt": 0}
        result = PushService.get_unread_count(1)
        assert result.count == 0

    def test_get_push_settings_default(self, mock_db):
        """测试默认推送设置"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].fetchone.return_value = None
        result = PushService.get_push_settings(1)
        assert result.enabled is True
        assert result.fortune_push is True
        assert result.diary_reminder is True

    def test_get_push_settings_existing(self, mock_db):
        """测试已有推送设置"""
        from apps.api.services.push_service import PushService

        mock_db["cursor"].fetchone.return_value = {
            "user_id": 1, "enabled": True, "fortune_push": False,
            "fortune_push_time": "09:00:00", "diary_reminder": True,
            "diary_reminder_time": "22:00:00", "marketing": True,
            "vibrate": False,
        }
        result = PushService.get_push_settings(1)
        assert result.fortune_push is False
        assert result.fortune_push_time == "09:00:00"
        assert result.marketing is True
        assert result.vibrate is False

    def test_update_push_settings(self, mock_db):
        """测试更新推送设置"""
        from apps.api.services.push_service import PushService
        from apps.api.schemas.membership import PushSettingsUpdate

        # 更新时先返回rowcount，然后get调用返回新设置
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                pass  # update
            elif call_count[0] == 2:
                mock_db["cursor"].fetchone.return_value = {
                    "user_id": 1, "enabled": False, "fortune_push": True,
                    "fortune_push_time": "08:00:00", "diary_reminder": True,
                    "diary_reminder_time": "21:00:00", "marketing": False,
                    "vibrate": True,
                }

        mock_db["cursor"].execute.side_effect = side_effect

        settings = PushSettingsUpdate(enabled=False)
        result = PushService.update_push_settings(1, settings)
        assert result.enabled is False

    def test_init_push_settings(self, mock_db):
        """测试初始化推送设置"""
        from apps.api.services.push_service import PushService

        result = PushService.init_push_settings(1)
        assert result.enabled is True
        assert result.fortune_push is True


class TestPushScheduler:
    """推送调度器测试"""

    @pytest.mark.asyncio
    async def test_schedule_fortune_off_hours(self):
        """测试非推送时段不发送运势推送"""
        from apps.api.services.push_scheduler import PushScheduler
        from unittest.mock import patch

        with patch("apps.api.services.push_scheduler.datetime") as mock_dt:
            # Mock 当前时间为下午3点（不在7-9点范围内）
            mock_now = MagicMock()
            mock_now.hour = 15
            mock_dt.now.return_value = mock_now
            await PushScheduler.schedule_daily_fortune_push()
            # 不在推送时段，不应调用数据库

    @pytest.mark.asyncio
    async def test_schedule_diary_off_hours(self):
        """测试非推送时段不发送日记提醒"""
        from apps.api.services.push_scheduler import PushScheduler
        from unittest.mock import patch

        with patch("apps.api.services.push_scheduler.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.hour = 10
            mock_dt.now.return_value = mock_now
            await PushScheduler.schedule_diary_reminder()
