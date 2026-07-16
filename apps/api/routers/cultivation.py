"""
游戏化系统路由模块 - 积分、成就、修炼等级
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from apps.api.routers.auth import get_current_user
from apps.api.services.gamification_service import gamification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cultivation", tags=["cultivation"])


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


@router.get("/profile")
async def get_cultivation_profile(
    user: dict = Depends(get_current_user),
):
    """获取用户修炼档案（积分、等级、成就）"""
    user_id = _get_user_id(user)
    return gamification_service.get_user_profile(user_id)


@router.post("/checkin")
async def daily_checkin(
    user: dict = Depends(get_current_user),
):
    """每日签到（更新连续打卡 + 获取积分）"""
    user_id = _get_user_id(user)
    result = gamification_service.check_daily_streak(user_id)

    if not result["streak_updated"]:
        return {"message": "今日已签到", "streak_days": result["streak_days"]}

    # 签到后检查成就解锁
    new_achievements = gamification_service.check_achievements(user_id)

    # 签到成功，失效 daily-ritual 缓存
    try:
        from apps.api.core.config import settings as _settings
        if _settings.redis_enabled:
            from apps.api.core.cache import cache as redis_cache
            today_str = date.today().isoformat()
            redis_cache.delete_sync(f"daily_ritual:{user_id}:{today_str}")
    except Exception as e:
        logger.debug(f"[Cultivation] daily_ritual 缓存失效失败: {e}")

    return {
        "message": "签到成功",
        "streak_days": result["streak_days"],
        "points_earned": result["points_earned"],
        "new_achievements": new_achievements,
    }


@router.post("/check-achievements")
async def check_achievements(
    user: dict = Depends(get_current_user),
):
    """手动检查成就解锁（可定期调用）"""
    user_id = _get_user_id(user)
    new_achievements = gamification_service.check_achievements(user_id)
    return {"new_achievements": new_achievements}


@router.get("/history")
async def get_points_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """获取积分变动历史"""
    user_id = _get_user_id(user)
    return gamification_service.get_points_history(user_id, page, size)
