"""
异步任务查询路由
"""

from fastapi import APIRouter, Depends, HTTPException

from apps.api.routers.auth import get_current_user
from apps.api.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str, user: dict = Depends(get_current_user)):
    """查询任务状态与结果（仅限本人任务）"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    task = task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
