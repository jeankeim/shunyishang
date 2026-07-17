"""
会员等级权限中间件测试

个人备案版：require_plan 和 check_quota 均直接放行，不做等级/配额检查。
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestRequirePlan:
    """require_plan 依赖测试（个人备案版：始终放行）"""

    @pytest.mark.asyncio
    async def test_free_user_access_free(self):
        """免费用户访问免费功能 - 直接放行"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("free")
        user = {"id": 1, "user_id": 1}
        result = await dep(current_user=user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_monthly_user_access_monthly(self):
        """月度用户访问月度功能 - 直接放行"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("monthly")
        user = {"id": 1, "user_id": 1}
        result = await dep(current_user=user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_free_user_access_monthly_allowed(self):
        """个人备案版：免费用户也可访问付费功能（始终放行）"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("monthly")
        user = {"id": 1, "user_id": 1}
        result = await dep(current_user=user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_free_user_access_yearly_allowed(self):
        """个人备案版：免费用户也可访问年度功能（始终放行）"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("yearly")
        user = {"id": 1, "user_id": 1}
        result = await dep(current_user=user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_yearly_user_access_all(self):
        """年度用户访问所有功能 - 直接放行"""
        from apps.api.core.plan_middleware import require_plan

        for min_plan in ["free", "monthly", "yearly"]:
            dep = require_plan(min_plan)
            user = {"id": 1, "user_id": 1}
            result = await dep(current_user=user)
            assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_unauthenticated_user_still_passes(self):
        """个人备案版：即使空用户也放行"""
        from apps.api.core.plan_middleware import require_plan

        dep = require_plan("free")
        user = {}  # 无 id
        result = await dep(current_user=user)
        assert result == {}


class TestCheckQuota:
    """check_quota 依赖测试（个人备案版：始终放行）"""

    @pytest.mark.asyncio
    async def test_quota_allowed(self):
        """配额检查 - 直接放行"""
        from apps.api.core.plan_middleware import check_quota

        dep = check_quota("daily_recommendations")
        user = {"id": 1, "user_id": 1}
        result = await dep(current_user=user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_quota_always_passes(self):
        """个人备案版：不做配额检查，始终放行"""
        from apps.api.core.plan_middleware import check_quota

        dep = check_quota("daily_recommendations")
        user = {"id": 1, "user_id": 1}
        result = await dep(current_user=user)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_quota_unauthenticated_still_passes(self):
        """个人备案版：未认证用户也放行"""
        from apps.api.core.plan_middleware import check_quota

        dep = check_quota("daily_recommendations")
        user = {}
        result = await dep(current_user=user)
        assert result == {}
