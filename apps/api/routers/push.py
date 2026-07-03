"""
推送通知路由模块
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.api.routers.auth import get_current_user
from apps.api.schemas.membership import (
    PushSettingsResponse,
    PushSettingsUpdate,
    PushHistoryResponse,
    UnreadCountResponse,
    PushNotificationResponse,
    RegisterPushRequest,
    PaymentCallbackRequest,
)
from apps.api.services.push_service import push_service
from apps.api.services.membership_service import membership_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/push", tags=["push"])


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


@router.get("/settings", response_model=PushSettingsResponse)
async def get_settings(user: dict = Depends(get_current_user)):
    """获取推送设置"""
    user_id = _get_user_id(user)
    return push_service.get_push_settings(user_id)


@router.put("/settings", response_model=PushSettingsResponse)
async def update_settings(request: PushSettingsUpdate, user: dict = Depends(get_current_user)):
    """更新推送设置"""
    user_id = _get_user_id(user)
    return push_service.update_push_settings(user_id, request)


@router.get("/history", response_model=PushHistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """获取推送历史"""
    user_id = _get_user_id(user)
    return push_service.get_push_history(user_id, page, size)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(user: dict = Depends(get_current_user)):
    """获取未读数量"""
    user_id = _get_user_id(user)
    return push_service.get_unread_count(user_id)


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, user: dict = Depends(get_current_user)):
    """标记已读"""
    user_id = _get_user_id(user)
    success = push_service.mark_as_read(notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在或已读")
    return {"message": "已读"}


@router.post("/register")
async def register_push(request: RegisterPushRequest, user: dict = Depends(get_current_user)):
    """注册推送（Web Push subscription，Mock）"""
    # Mock: 只记录日志
    user_id = _get_user_id(user)
    logger.info(f"[Push] 用户 {user_id} 注册推送: {request.endpoint}")
    return {"message": "推送注册成功"}


@router.post("/smart-check")
async def smart_reminder_check(
    weather_info: Optional[dict] = None,
    user: dict = Depends(get_current_user),
):
    """
    智能提醒检查

    前端在首页加载时调用，检查天气变化和衣橱闲置，
    返回触发的提醒列表（用于在首页显示提醒卡片）
    """
    user_id = _get_user_id(user)
    from apps.api.services.smart_reminder_service import smart_reminder_service
    triggered = smart_reminder_service.check_and_notify(user_id, weather_info)
    return {"alerts": triggered}


# 支付回调路由（放在 push router 文件中，也可单独拆分）
payment_router = APIRouter(prefix="/payments", tags=["payments"])


@payment_router.post("/callback/wechat")
async def wechat_callback(request: PaymentCallbackRequest):
    """微信支付回调（Mock）"""
    result = membership_service.process_payment_callback(request.transaction_id, request.status)
    return result


@payment_router.post("/callback/alipay")
async def alipay_callback(request: PaymentCallbackRequest):
    """支付宝回调（Mock）"""
    result = membership_service.process_payment_callback(request.transaction_id, request.status)
    return result
