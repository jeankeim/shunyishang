"""
会员路由模块
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.routers.auth import get_current_user
from apps.api.schemas.membership import (
    MembershipStatusResponse,
    PlansListResponse,
    SubscribeRequest,
    SubscribeResponse,
    CancelResponse,
    UpgradeRequest,
    UpgradeResponse,
    RenewRequest,
    RenewResponse,
    QuotaResponse,
)
from apps.api.services.membership_service import membership_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/membership", tags=["membership"])


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


@router.get("/status", response_model=MembershipStatusResponse)
async def get_status(user: dict = Depends(get_current_user)):
    """获取会员状态"""
    user_id = _get_user_id(user)
    return membership_service.get_membership_status(user_id)


@router.get("/plans", response_model=PlansListResponse)
async def get_plans(user: dict = Depends(get_current_user)):
    """获取套餐列表"""
    return membership_service.get_available_plans()


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(request: SubscribeRequest, user: dict = Depends(get_current_user)):
    """订阅"""
    user_id = _get_user_id(user)
    try:
        return membership_service.subscribe(user_id, request.plan, request.payment_method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"订阅失败: {e}")


@router.post("/cancel", response_model=CancelResponse)
async def cancel(subscription_id: int, user: dict = Depends(get_current_user)):
    """取消订阅"""
    user_id = _get_user_id(user)
    try:
        return membership_service.cancel_subscription(user_id, subscription_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upgrade", response_model=UpgradeResponse)
async def upgrade(request: UpgradeRequest, user: dict = Depends(get_current_user)):
    """升级套餐"""
    user_id = _get_user_id(user)
    try:
        return membership_service.upgrade(user_id, request.new_plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/renew", response_model=RenewResponse)
async def renew(request: RenewRequest, user: dict = Depends(get_current_user)):
    """续费"""
    user_id = _get_user_id(user)
    try:
        return membership_service.renew(user_id, request.payment_method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/quota/{feature}", response_model=QuotaResponse)
async def get_quota(feature: str, user: dict = Depends(get_current_user)):
    """检查功能配额"""
    user_id = _get_user_id(user)
    return membership_service.check_quota(user_id, feature)
