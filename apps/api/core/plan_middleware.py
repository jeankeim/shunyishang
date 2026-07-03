"""
会员等级权限中间件
提供 require_plan 和 check_quota 依赖注入
"""

import logging
from typing import Callable

from fastapi import Depends, HTTPException, status

from apps.api.routers.auth import get_current_user
from apps.api.services.membership_service import membership_service, PLAN_HIERARCHY

logger = logging.getLogger(__name__)


def require_plan(min_plan: str = "free"):
    """
    FastAPI 依赖：检查用户是否拥有指定等级
    
    Usage:
        @router.get("/premium-feature")
        async def premium_feature(user=Depends(require_plan("monthly"))):
            ...
    """
    async def dependency(current_user: dict = Depends(get_current_user)):
        user_id = current_user.get("id") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户未登录",
            )

        member_status = membership_service.get_membership_status(user_id)
        user_level = PLAN_HIERARCHY.get(member_status.plan, 0)
        required_level = PLAN_HIERARCHY.get(min_plan, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"此功能需要 {min_plan} 及以上会员",
            )

        return current_user

    return dependency


def check_quota(feature: str):
    """
    FastAPI 依赖：检查功能配额
    
    Usage:
        @router.post("/recommend")
        async def recommend(user=Depends(check_quota("daily_recommendations"))):
            ...
    """
    async def dependency(current_user: dict = Depends(get_current_user)):
        user_id = current_user.get("id") or current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户未登录",
            )

        quota = membership_service.check_quota(user_id, feature)
        if not quota.allowed:
            plan_required = quota.plan_required or "monthly"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"配额已用完，请升级到 {plan_required} 会员",
            )

        return current_user

    return dependency
