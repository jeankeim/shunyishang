"""
会员服务测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from apps.api.schemas.membership import (
    MembershipStatusResponse,
    PlansListResponse,
    SubscribeResponse,
    CancelResponse,
    UpgradeResponse,
    RenewResponse,
    QuotaResponse,
)


class TestMembershipService:
    """会员服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库连接"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with patch("apps.api.services.membership_service.DatabasePool") as mock_pool:
            mock_pool.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
            yield {"conn": mock_conn, "cursor": mock_cursor}

    def test_get_membership_status_free(self, mock_db):
        """测试免费用户状态"""
        from apps.api.services.membership_service import MembershipService

        mock_db["cursor"].fetchone.return_value = None
        result = MembershipService.get_membership_status(1)
        assert result.plan == "free"
        assert result.status == "active"

    def test_get_membership_status_monthly(self, mock_db):
        """测试月度会员状态"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        expires = now + timedelta(days=15)
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "plan": "monthly", "status": "active",
            "started_at": now, "expires_at": expires, "auto_renew": True,
        }
        result = MembershipService.get_membership_status(1)
        assert result.plan == "monthly"
        assert result.status == "active"
        assert result.days_remaining is not None
        assert result.days_remaining >= 14

    def test_get_membership_status_yearly(self, mock_db):
        """测试年度会员状态"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        expires = now + timedelta(days=200)
        mock_db["cursor"].fetchone.return_value = {
            "id": 2, "plan": "yearly", "status": "active",
            "started_at": now, "expires_at": expires, "auto_renew": False,
        }
        result = MembershipService.get_membership_status(1)
        assert result.plan == "yearly"
        assert result.days_remaining >= 199

    def test_get_membership_status_expired(self, mock_db):
        """测试过期订阅"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        expired = now - timedelta(days=5)
        mock_db["cursor"].fetchone.return_value = {
            "id": 3, "plan": "monthly", "status": "active",
            "started_at": now - timedelta(days=35), "expires_at": expired, "auto_renew": False,
        }
        result = MembershipService.get_membership_status(1)
        assert result.plan == "free"  # 过期后回退到免费版

    def test_get_available_plans(self):
        """测试获取套餐列表"""
        from apps.api.services.membership_service import MembershipService

        result = MembershipService.get_available_plans()
        assert len(result.plans) == 3
        plan_keys = [p.plan_key for p in result.plans]
        assert "free" in plan_keys
        assert "monthly" in plan_keys
        assert "yearly" in plan_keys

    def test_get_plan_prices(self):
        """测试套餐价格"""
        from apps.api.services.membership_service import MembershipService

        result = MembershipService.get_available_plans()
        plans_dict = {p.plan_key: p for p in result.plans}
        assert plans_dict["free"].price_monthly == 0.0
        assert plans_dict["monthly"].price_monthly == 19.9
        assert plans_dict["yearly"].price_yearly == 168.0

    def test_subscribe_monthly(self, mock_db):
        """测试订阅月度会员"""
        from apps.api.services.membership_service import MembershipService

        mock_db["cursor"].fetchone.return_value = {"id": 1}
        result = MembershipService.subscribe(1, "monthly", "mock")
        assert result.subscription_id == 1
        assert result.status == "active"
        assert result.payment_url is not None

    def test_subscribe_yearly(self, mock_db):
        """测试订阅年度会员"""
        from apps.api.services.membership_service import MembershipService

        mock_db["cursor"].fetchone.return_value = {"id": 2}
        result = MembershipService.subscribe(1, "yearly", "mock")
        assert result.subscription_id == 2
        assert result.status == "active"

    def test_subscribe_invalid_plan(self, mock_db):
        """测试无效套餐"""
        from apps.api.services.membership_service import MembershipService

        with pytest.raises(ValueError, match="无效套餐"):
            MembershipService.subscribe(1, "invalid", "mock")

    def test_cancel_subscription(self, mock_db):
        """测试取消订阅"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        expires = now + timedelta(days=15)
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "expires_at": expires,
        }
        result = MembershipService.cancel_subscription(1, 1)
        assert result.status == "cancelled"
        assert result.expires_at == expires

    def test_cancel_nonexistent(self, mock_db):
        """测试取消不存在的订阅"""
        from apps.api.services.membership_service import MembershipService

        mock_db["cursor"].fetchone.return_value = None
        with pytest.raises(ValueError, match="订阅不存在"):
            MembershipService.cancel_subscription(1, 999)

    def test_upgrade_monthly_to_yearly(self, mock_db):
        """测试从月度升级到年度"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        mock_db["cursor"].fetchone.side_effect = [
            {
                "id": 1, "plan": "monthly",
                "expires_at": now + timedelta(days=15),
                "started_at": now - timedelta(days=15),
            },
            {"id": 1},
        ]
        result = MembershipService.upgrade(1, "yearly")
        assert result.plan == "yearly"
        assert result.status == "active"

    def test_upgrade_same_plan(self, mock_db):
        """测试升级同级套餐报错"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "plan": "yearly",
            "expires_at": now + timedelta(days=100),
            "started_at": now - timedelta(days=265),
        }
        with pytest.raises(ValueError, match="更高级"):
            MembershipService.upgrade(1, "monthly")

    def test_renew(self, mock_db):
        """测试续费"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "plan": "monthly",
            "expires_at": now + timedelta(days=5),
        }
        result = MembershipService.renew(1, "mock")
        assert result.status == "active"
        assert result.expires_at is not None

    def test_check_quota_free_user(self, mock_db):
        """测试免费用户配额"""
        from apps.api.services.membership_service import MembershipService

        mock_db["cursor"].fetchone.return_value = None  # 免费用户
        result = MembershipService.check_quota(1, "ai_review")
        assert result.allowed is False
        assert result.plan_required is not None

    def test_check_quota_monthly_user(self, mock_db):
        """测试月度用户配额"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "plan": "monthly", "status": "active",
            "started_at": now, "expires_at": now + timedelta(days=30), "auto_renew": True,
        }
        result = MembershipService.check_quota(1, "ai_review")
        assert result.allowed is True

    def test_check_quota_unlimited(self, mock_db):
        """测试无限配额"""
        from apps.api.services.membership_service import MembershipService

        now = datetime.utcnow()
        mock_db["cursor"].fetchone.return_value = {
            "id": 1, "plan": "monthly", "status": "active",
            "started_at": now, "expires_at": now + timedelta(days=30), "auto_renew": True,
        }
        result = MembershipService.check_quota(1, "daily_recommendations")
        assert result.allowed is True
        assert result.limit is None  # 无限制

    def test_process_payment_callback_completed(self, mock_db):
        """测试支付回调-完成"""
        from apps.api.services.membership_service import MembershipService

        result = MembershipService.process_payment_callback("TX-001", "completed")
        assert result["status"] == "processed"

    def test_process_payment_callback_failed(self, mock_db):
        """测试支付回调-失败"""
        from apps.api.services.membership_service import MembershipService

        result = MembershipService.process_payment_callback("TX-002", "failed")
        assert result["status"] == "failed"
