"""
穿搭日记路由模块
"""

import json
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.routers.auth import get_current_user
from apps.api.schemas.diary import (
    CreateDiaryRequest,
    UpdateDiaryRequest,
    DiaryItemRequest,
    DiaryResponse,
    DiaryListResponse,
    DiaryCalendarResponse,
    DiaryStatsResponse,
    DiaryOutfitItemResponse,
    QuickCheckInRequest,
    QuickCheckInResponse,
)
from apps.api.services.diary_service import diary_service
from apps.api.services.ai_review_service import generate_ai_review
from apps.api.services.ai_tagging_service import ai_tagging_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diary", tags=["diary"])


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


@router.post("", response_model=DiaryResponse)
async def create_diary(
    request: CreateDiaryRequest,
    user: dict = Depends(get_current_user),
):
    """创建穿搭日记"""
    user_id = _get_user_id(user)
    try:
        diary = diary_service.create_diary(user_id, request)

        # 可选触发 AI 点评
        if request.trigger_ai_review and diary.items:
            user_bazi = _get_user_bazi(user_id)
            outfit_items = [_item_to_dict(it) for it in diary.items]
            review = generate_ai_review(user_bazi, outfit_items, None, request.occasion)
            diary = diary_service.update_ai_review(diary.id, user_id, review) or diary

        return diary
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="该日期已有日记记录")
        logger.error(f"创建日记失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建日记失败: {e}")


@router.get("", response_model=DiaryListResponse)
async def list_diaries(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    mood: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    user: dict = Depends(get_current_user),
):
    """获取日记列表"""
    user_id = _get_user_id(user)
    return diary_service.get_diaries(user_id, page, size, mood, date_from, date_to)


@router.get("/calendar", response_model=DiaryCalendarResponse)
async def get_calendar(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: dict = Depends(get_current_user),
):
    """获取日历视图"""
    user_id = _get_user_id(user)
    return diary_service.get_calendar(user_id, year, month)


@router.get("/stats", response_model=DiaryStatsResponse)
async def get_stats(
    user: dict = Depends(get_current_user),
):
    """获取统计数据"""
    user_id = _get_user_id(user)
    return diary_service.get_stats(user_id)


@router.post("/quick-checkin", response_model=QuickCheckInResponse)
async def quick_checkin(
    request: QuickCheckInRequest,
    user: dict = Depends(get_current_user),
):
    """
    快捷穿搭打卡

    30秒完成今日穿搭记录：
    1. AI 自动分析穿搭颜色/材质/风格
    2. 自动关联天气快照
    3. 创建今日日记
    """
    user_id = _get_user_id(user)
    today = date.today()

    # 1. AI 分析穿搭（如果有描述或图片）
    ai_tags = {}
    description = request.description or ""
    if description or request.image_url:
        try:
            ai_result = await ai_tagging_service.analyze_item(
                description=description or "今日穿搭",
                image_url=request.image_url,
            )
            ai_tags = {
                "color": ai_result.get("color", ""),
                "color_element": ai_result.get("color_element", ""),
                "material": ai_result.get("material", ""),
                "style": ai_result.get("style", ""),
                "primary_element": ai_result.get("primary_element", ""),
            }
        except Exception as e:
            logger.warning(f"[QuickCheckIn] AI 分析失败: {e}")

    # 2. 检查今日是否已有日记
    existing = diary_service.get_diaries(user_id, 1, 1, None, today, today)
    if existing and existing.diaries:
        existing_diary = existing.diaries[0]
        return QuickCheckInResponse(
            diary_id=existing_diary.id,
            diary_date=today,
            ai_tags=ai_tags,
            outfit_suggestion="",
            created=False,
        )

    # 3. 获取今日运势穿搭建议
    outfit_suggestion = ""
    try:
        from apps.api.services.fortune_engine import calculate_daily_fortune
        user_bazi = _get_user_bazi(user_id)
        fortune = calculate_daily_fortune(user_bazi, today)
        outfit_suggestion = fortune.get("outfit_suggestion", "")
    except Exception as e:
        logger.debug(f"[QuickCheckIn] 运势获取失败: {e}")

    # 4. 创建日记
    notes_parts = []
    if ai_tags.get("color"):
        notes_parts.append(f"今日穿搭: {ai_tags['color']}系")
    if ai_tags.get("style"):
        notes_parts.append(ai_tags['style'])
    notes = "，".join(notes_parts) if notes_parts else None

    image_urls = [request.image_url] if request.image_url else []

    create_req = CreateDiaryRequest(
        diary_date=today,
        mood=request.mood or "neutral",
        occasion=None,
        notes=notes,
        rating=None,
        image_urls=image_urls,
        items=[],
        trigger_ai_review=False,
    )

    diary = diary_service.create_diary(user_id, create_req)

    return QuickCheckInResponse(
        diary_id=diary.id,
        diary_date=today,
        ai_tags=ai_tags,
        outfit_suggestion=outfit_suggestion,
        created=True,
    )


@router.get("/{diary_id}", response_model=DiaryResponse)
async def get_diary(
    diary_id: int,
    user: dict = Depends(get_current_user),
):
    """获取日记详情"""
    user_id = _get_user_id(user)
    diary = diary_service.get_diary_by_id(diary_id, user_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在或无权访问")
    return diary


@router.put("/{diary_id}", response_model=DiaryResponse)
async def update_diary(
    diary_id: int,
    request: UpdateDiaryRequest,
    user: dict = Depends(get_current_user),
):
    """更新日记"""
    user_id = _get_user_id(user)
    diary = diary_service.update_diary(diary_id, user_id, request)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在或无权访问")
    return diary


@router.delete("/{diary_id}")
async def delete_diary(
    diary_id: int,
    user: dict = Depends(get_current_user),
):
    """删除日记"""
    user_id = _get_user_id(user)
    deleted = diary_service.delete_diary(diary_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="日记不存在或无权访问")
    return {"message": "删除成功"}


@router.post("/{diary_id}/items", response_model=DiaryOutfitItemResponse)
async def add_item(
    diary_id: int,
    request: DiaryItemRequest,
    user: dict = Depends(get_current_user),
):
    """添加衣物到日记"""
    user_id = _get_user_id(user)
    item = diary_service.add_item_to_diary(diary_id, user_id, request)
    if not item:
        raise HTTPException(status_code=404, detail="日记不存在或无权访问")
    return item


@router.delete("/{diary_id}/items/{item_id}")
async def remove_item(
    diary_id: int,
    item_id: int,
    user: dict = Depends(get_current_user),
):
    """从日记移除衣物"""
    user_id = _get_user_id(user)
    removed = diary_service.remove_item_from_diary(diary_id, user_id, item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="日记或衣物不存在")
    return {"message": "移除成功"}


@router.post("/{diary_id}/review")
async def trigger_review(
    diary_id: int,
    user: dict = Depends(get_current_user),
):
    """触发AI穿搭点评"""
    user_id = _get_user_id(user)
    diary = diary_service.get_diary_by_id(diary_id, user_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在或无权访问")

    user_bazi = _get_user_bazi(user_id)
    outfit_items = [_item_to_dict(it) for it in diary.items]
    review = generate_ai_review(user_bazi, outfit_items)

    diary = diary_service.update_ai_review(diary_id, user_id, review) or diary
    return {"ai_review": review}


def _get_user_bazi(user_id: int) -> dict:
    """从数据库获取用户八字信息"""
    query = "SELECT bazi, xiyong_elements FROM users WHERE id = %s"
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id])
            row = cur.fetchone()

    if not row or not row.get('bazi'):
        return {"day_master": "土", "suggested_elements": [], "avoid_elements": []}

    bazi = row['bazi']
    if isinstance(bazi, str):
        import json
        bazi = json.loads(bazi)

    return {
        "day_master": bazi.get("day_master", "土"),
        "suggested_elements": bazi.get("suggested_elements", []),
        "avoid_elements": bazi.get("avoid_elements", []),
        "pillars": bazi.get("pillars", {}),
    }


def _item_to_dict(item) -> dict:
    """将 DiaryOutfitItemResponse 转为 dict"""
    return {
        "name": item.name or "未知",
        "primary_element": item.primary_element or "",
        "category": item.category or "",
        "image_url": item.image_url or "",
    }
