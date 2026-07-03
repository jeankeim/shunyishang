"""
会员 & 推送通知 Pydantic 模型定义
"""

from datetime import datetime, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================
# 会员相关
# ============================================

class MembershipStatusResponse(BaseModel):
    """会员状态响应"""
    plan: str = Field("free", description="当前套餐: free/monthly/yearly")
    status: str = Field("active", description="状态: active/cancelled/expired/suspended")
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: bool = False
    days_remaining: Optional[int] = None


class PlanInfo(BaseModel):
    """套餐信息"""
    name: str
    plan_key: str
    price_monthly: float
    price_yearly: float
    features: List[str] = Field(default_factory=list)
    limits: Dict[str, Any] = Field(default_factory=dict)


class PlansListResponse(BaseModel):
    """套餐列表响应"""
    plans: List[PlanInfo]


class SubscribeRequest(BaseModel):
    """订阅请求"""
    plan: str = Field(..., pattern="^(monthly|yearly)$", description="套餐: monthly/yearly")
    payment_method: str = Field("mock", pattern="^(wechat|alipay|mock)$", description="支付方式")


class SubscribeResponse(BaseModel):
    """订阅响应"""
    subscription_id: int
    status: str
    payment_url: Optional[str] = None


class CancelResponse(BaseModel):
    """取消订阅响应"""
    status: str
    expires_at: Optional[datetime] = None


class UpgradeRequest(BaseModel):
    """升级请求"""
    new_plan: str = Field(..., pattern="^(monthly|yearly)$")


class UpgradeResponse(BaseModel):
    """升级响应"""
    subscription_id: int
    plan: str
    status: str
    price_diff: float


class RenewRequest(BaseModel):
    """续费请求"""
    payment_method: str = Field("mock", pattern="^(wechat|alipay|mock)$")


class RenewResponse(BaseModel):
    """续费响应"""
    subscription_id: int
    status: str
    expires_at: Optional[datetime] = None
    payment_url: Optional[str] = None


class PaymentCallbackRequest(BaseModel):
    """支付回调请求"""
    transaction_id: str
    status: str = Field(..., pattern="^(completed|failed)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QuotaResponse(BaseModel):
    """配额检查响应"""
    feature: str
    allowed: bool
    used: int = 0
    limit: Optional[int] = None
    plan_required: Optional[str] = None


# ============================================
# 推送相关
# ============================================

class PushSettingsResponse(BaseModel):
    """推送设置响应"""
    enabled: bool = True
    fortune_push: bool = True
    fortune_push_time: Optional[str] = "08:00:00"
    diary_reminder: bool = True
    diary_reminder_time: Optional[str] = "21:00:00"
    marketing: bool = False
    vibrate: bool = True


class PushSettingsUpdate(BaseModel):
    """推送设置更新"""
    enabled: Optional[bool] = None
    fortune_push: Optional[bool] = None
    fortune_push_time: Optional[str] = None
    diary_reminder: Optional[bool] = None
    diary_reminder_time: Optional[str] = None
    marketing: Optional[bool] = None
    vibrate: Optional[bool] = None


class PushNotificationResponse(BaseModel):
    """推送通知响应"""
    id: int
    type: str
    title: str
    body: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime
    read_at: Optional[datetime] = None


class PushHistoryResponse(BaseModel):
    """推送历史响应"""
    notifications: List[PushNotificationResponse]
    total: int
    page: int
    size: int


class UnreadCountResponse(BaseModel):
    """未读数量响应"""
    count: int


class RegisterPushRequest(BaseModel):
    """注册推送请求（Web Push subscription）"""
    endpoint: Optional[str] = None
    keys: Optional[Dict[str, str]] = None
