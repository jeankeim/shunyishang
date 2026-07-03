"""
会员等级权限中间件测试
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestRequirePlan:
    """require_plan 依赖测试"""

    @pytest.mark.asyncio
    async def test_free_user_access_free(self):
        """免费用户访问免费功能"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("free")
        user = {"id": 1, "user_id": 1}

        with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
            mock_svc.get_membership_status.return_value = MagicMock(plan="free", status="active")
            result = await dep(current_user=user)
            assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_monthly_user_access_monthly(self):
        """月度用户访问月度功能"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("monthly")
        user = {"id": 1, "user_id": 1}

        with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
            mock_svc.get_membership_status.return_value = MagicMock(plan="monthly", status="active")
            result = await dep(current_user=user)
            assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_free_user_access_monthly_denied(self):
        """免费用户访问付费功能被拒"""
        from apps.api.core.plan_middleware import require_plan
        from fastapi import HTTPException

        dep = require_plan("monthly")
        user = {"id": 1, "user_id": 1}

        with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
            mock_svc.get_membership_status.return_value = MagicMock(plan="free", status="active")
            with pytest.raises(HTTPException) as exc_info:
                await dep(current_user=user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_monthly_user_access_yearly_denied(self):
        """月度用户访问年度功能被拒"""
        from apps.api.core.plan_middleware import require_plan
        from fastapi import HTTPException

        dep = require_plan("yearly")
        user = {"id": 1, "user_id": 1}

        with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
            mock_svc.get_membership_status.return_value = MagicMock(plan="monthly", status="active")
            with pytest.raises(HTTPException) as exc_info:
                await dep(current_user=user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_yearly_user_access_all(self):
        """年度用户访问所有功能"""
        from apps.api.core.plan_middleware import require_plan

        for min_plan in ["free", "monthly", "yearly"]:
            dep = require_plan(min_plan)
            user = {"id": 1, "user_id": 1}

            with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
                mock_svc.get_membership_status.return_value = MagicMock(plan="yearly", status="active")
                result = await dep(current_user=user)
                assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_unauthenticated_user_denied(self):
        """未认证用户被拒"""
        from apps.api.core.plan_middleware import require_plan
        from fastapi import HTTPException

        dep = require_plan("free")
        user = {}  # 无 id

        with pytest.raises(HTTPException) as exc_info:
            await dep(current_user=user)
        assert exc_info.value.status_code == 401


class TestCheckQuota:
    """check_quota 依赖测试"""

    @pytest.mark.asyncio
    async def test_quota_allowed(self):
        """配额充足"""
        from apps.api.core.plan_middleware import check_quota

        dep = check_quota("daily_recommendations")
        user = {"id": 1, "user_id": 1}

        with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
            mock_svc.check_quota.return_value = MagicMock(
                feature="daily_recommendations", allowed=True, used=1, limit=3
            )
            result = await dep(current_user=user)
            assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_quota_exceeded(self):
        """配额用完被拒"""
        from apps.api.core.plan_middleware import check_quota
        from fastapi import HTTPException

        dep = check_quota("daily_recommendations")
        user = {"id": 1, "user_id": 1}

        with patch("apps.api.core.plan_middleware.membership_service") as mock_svc:
            mock_svc.check_quota.return_value = MagicMock(
                feature="daily_recommendations", allowed=False, used=3, limit=3,
                plan_required="monthly"
            )
            with pytest.raises(HTTPException) as exc_info:
                await dep(current_user=user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_quota_unauthenticated(self):
        """未认证用户配额检查被拒"""
        from apps.api.core.plan_middleware import check_quota
        from fastapi import HTTPException

        dep = check_quota("daily_recommendations")
        user = {}

        with pytest.raises(HTTPException) as exc_info:
            await dep(current_user=user)
        assert exc_info.value.status_code == 401
