"""
后台管理路由（仅管理员可见）

鉴权方式：环境变量 ADMIN_USER_CODES 白名单（users.user_code 逗号分隔）。
路由级统一依赖 require_admin：所有 /admin 路由均要求登录 + 白名单校验，
user_code 仅从 JWT 解析，白名单为空时任何人不可访问，非管理员返回 403。
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from apps.api.core.config import settings
from apps.api.routers.auth import get_current_user
from apps.api.services import admin_stats_service, aliyun_billing_service

logger = logging.getLogger(__name__)


def _is_admin(user: dict) -> bool:
    return user.get("user_code") in settings.admin_user_codes_list


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """管理员依赖：登录 + 白名单校验（白名单为空时任何人不可通过）"""
    if not settings.admin_user_codes_list or not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="无管理员权限")
    return current_user


# 路由级统一依赖：杜绝单个路由遗漏鉴权
router = APIRouter(dependencies=[Depends(require_admin)])


class AdminMeResponse(BaseModel):
    is_admin: bool
    nickname: str = ""


class BillSyncResponse(BaseModel):
    synced_days: int
    synced_rows: int
    errors: list = []
    synced_at: str = ""


@router.get("/me", response_model=AdminMeResponse, summary="查询当前用户管理员身份")
async def admin_me(current_user: dict = Depends(get_current_user)):
    """供前端 /admin 守卫判断（路由级依赖已保证管理员身份，非管理员收到 403）"""
    return AdminMeResponse(
        is_admin=True,
        nickname=current_user.get("nickname") or "",
    )


@router.get("/dashboard", summary="运营数据看板")
async def get_dashboard(
    days: int = Query(30, ge=1, le=365, description="趋势天数"),
):
    """
    运营数据看板：近 N 天趋势（历史取每日快照，当天实时计算）+ 累计概况

    指标：DAU、新增用户、推荐次数、接口调用量、日记数、运势查询数、
    点赞/点踩数、新增衣橱衣物。
    """
    return await asyncio.to_thread(admin_stats_service.get_dashboard, days)


@router.get("/bills", summary="阿里云费用账单汇总")
async def get_bills(
    days: int = Query(31, ge=1, le=366, description="统计天数"),
):
    """阿里云全产品（ECS/RDS/OSS/CDN/大模型等）按天账单汇总"""
    return await asyncio.to_thread(aliyun_billing_service.get_bill_summary, days)


@router.post("/bills/sync", response_model=BillSyncResponse, summary="手动同步阿里云账单")
async def sync_bills(
    days: int = Query(3, ge=1, le=90, description="回刷天数（账单有约1天延迟）"),
):
    """手动触发账单同步（首次接入可传 days=30 回填一个月）"""
    result = await asyncio.to_thread(aliyun_billing_service.sync_bills, days)
    return BillSyncResponse(**result)
