"""
会员等级权限中间件
提供 require_plan 和 check_quota 依赖注入

个人备案版：所有功能免费开放，不做会员等级和配额检查
"""

import logging
from typing import Callable

from fastapi import Depends, HTTPException, status

from apps.api.routers.auth import get_current_user

logger = logging.getLogger(__name__)


def require_plan(min_plan: str = "free"):
    """
    FastAPI 依赖：检查用户是否拥有指定等级
    
    个人备案版：始终放行，不检查会员等级
    
    Usage:
        @router.get("/premium-feature")
        async def premium_feature(user=Depends(require_plan("monthly"))):
            ...
    """
    async def dependency(current_user: dict = Depends(get_current_user)):
        # 个人备案版：跳过会员等级检查，直接放行
        return current_user

    return dependency


def check_quota(feature: str):
    """
    FastAPI 依赖：检查功能配额
    
    个人备案版：始终放行，不做配额检查
    
    Usage:
        @router.post("/recommend")
        async def recommend(user=Depends(check_quota("daily_recommendations"))):
            ...
    """
    async def dependency(current_user: dict = Depends(get_current_user)):
        # 个人备案版：跳过配额检查，直接放行
        return current_user

    return dependency
