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
from apps.api.services.user_service import get_user_bazi
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
    OutfitRecommendation,
)
from apps.api.services.diary_service import diary_service
from apps.api.services.ai_review_service import generate_ai_review
from apps.api.services.ai_tagging_service import ai_tagging_service
from apps.api.services.diary_feedback_service import diary_feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diary", tags=["diary"])

# 颜色关键词 → 五行映射（用于从穿搭描述提取颜色匹配）
_COLOR_KEYWORD_ELEMENT: dict = {
    "白": "金", "银": "金", "灰": "金", "米白": "金", "香槟": "金",
    "绿": "木", "青": "木", "翠": "木", "薄荷": "木", "草绿": "木",
    "黑": "水", "蓝": "水", "藏青": "水", "海军蓝": "水", "深灰": "水",
    "红": "火", "粉": "火", "橙": "火", "紫": "火", "玫红": "火", "酒红": "火",
    "棕": "土", "黄": "土", "卡其": "土", "驼": "土", "米": "土", "咖啡": "土",
}


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


def _extract_elements_from_text(text: str) -> list:
    """从穿搭描述中提取五行元素"""
    found = []
    for keyword, element in _COLOR_KEYWORD_ELEMENT.items():
        if keyword in text:
            if element not in found:
                found.append(element)
    return found


def _compute_fortune_match(
    ai_tags: dict,
    description: str,
    lucky_elements: list,
    lucky_colors: list,
) -> int:
    """
    计算穿搭与今日运势的匹配度 (0-100)。
    基于 AI 识别的颜色/五行 + 描述中的颜色关键词 与今日幸运元素对比。
    """
    if not lucky_elements:
        return 70  # 无运势数据时默认分

    score = 60  # 基础分
    matched = set()

    # 1. AI 识别的 primary_element 匹配幸运五行
    primary_elem = ai_tags.get("primary_element") or ai_tags.get("color_element")
    if primary_elem and primary_elem in lucky_elements:
        score += 20
        matched.add(primary_elem)

    # 2. 从描述中提取颜色五行匹配
    desc_elements = _extract_elements_from_text(description)
    for elem in desc_elements:
        if elem in lucky_elements and elem not in matched:
            score += 10
            matched.add(elem)
            if len(matched) >= 3:
                break

    # 3. AI 识别的颜色字面匹配幸运颜色
    ai_color = ai_tags.get("color", "")
    if ai_color and lucky_colors:
        for lc in lucky_colors:
            if lc in ai_color or ai_color in lc:
                score += 10
                break

    return min(100, score)


def _get_outfit_recommendation_from_wardrobe(
    user_id: int,
    lucky_elements: list,
    lucky_colors: list,
) -> Optional[dict]:
    """从用户衣橱中选1件与今日幸运五行/颜色最匹配的物品"""
    if not lucky_elements:
        return None

    query = """
        SELECT id, name, category, image_url, primary_element, secondary_element
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 100
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                items = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.debug(f"[QuickCheckIn] 衣橱查询失败: {e}")
        return None

    if not items:
        return None

    # 简单评分：primary_element 匹配幸运五行得2分，secondary匹配得1分
    best_item = None
    best_score = -1
    for item in items:
        s = 0
        pe = item.get("primary_element") or ""
        se = item.get("secondary_element") or ""
        if pe in lucky_elements:
            s += 2
        if se in lucky_elements:
            s += 1
        # 颜色名匹配加分
        name = item.get("name") or ""
        for lc in lucky_colors:
            if lc in name:
                s += 1
                break
        if s > best_score:
            best_score = s
            best_item = item

    if not best_item:
        return None

    # 构建推荐理由
    pe = best_item.get("primary_element") or ""
    reason_parts = []
    if pe and pe in lucky_elements:
        reason_parts.append(f"五行属{pe}，与今日幸运元素相合")
    else:
        reason_parts.append(f"今日运势推荐穿着")
    if lucky_colors:
        reason_parts.append(f"宜选{lucky_colors[0]}色系")
    reason = "，".join(reason_parts)

    return {
        "item_name": best_item.get("name", ""),
        "item_id": best_item.get("id"),
        "image_url": best_item.get("image_url"),
        "reason": reason,
    }


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
            user_bazi = get_user_bazi(user_id)
            outfit_items = [_item_to_dict(it) for it in diary.items]
            review = generate_ai_review(user_bazi, outfit_items, None, request.occasion)
            diary = diary_service.update_ai_review(diary.id, user_id, review) or diary

        # 穿搭日记反馈回流：评分转化为偏好信号
        try:
            diary_feedback_service.process_diary_feedback(user_id, diary.id, request.rating)
        except Exception as e:
            logger.warning(f"[Diary] 反馈回流失败: {e}")

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
    try:
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
        lucky_elements: list = []
        lucky_colors: list = []
        try:
            from apps.api.services.fortune_engine import calculate_daily_fortune
            user_bazi = get_user_bazi(user_id)
            fortune = calculate_daily_fortune(user_bazi, today)
            outfit_suggestion = fortune.get("outfit_suggestion", "")
            le = fortune.get("lucky_elements", {})
            lucky_elements = le.get("elements", [])
            lucky_colors = le.get("colors", [])
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
    except Exception as e:
        # 并发/重复打卡：唯一约束冲突时回退为"今日已打卡"
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            existing = diary_service.get_diaries(user_id, 1, 1, None, today, today)
            if existing and existing.diaries:
                return QuickCheckInResponse(
                    diary_id=existing.diaries[0].id,
                    diary_date=today,
                    ai_tags=ai_tags,
                    outfit_suggestion="",
                    created=False,
                )
        logger.error(f"[QuickCheckIn] 打卡失败: {e}")
        raise HTTPException(status_code=500, detail="打卡失败，请稍后重试")

    # 打卡成功，失效 daily-ritual 缓存
    _invalidate_daily_ritual_cache(user_id)

    # 自动更新穿着物品的 wear_count 和 last_worn_date
    _auto_update_wear_count(user_id, description, ai_tags)

    # 计算运势匹配度 & 衣橱单品推荐
    fortune_match_score = _compute_fortune_match(
        ai_tags, description, lucky_elements, lucky_colors
    )
    outfit_rec_data = _get_outfit_recommendation_from_wardrobe(
        user_id, lucky_elements, lucky_colors
    )
    outfit_rec = (
        OutfitRecommendation(**outfit_rec_data) if outfit_rec_data else None
    )

    # 获取连续打卡天数
    streak_days = None
    try:
        from apps.api.services.gamification_service import gamification_service
        profile = gamification_service.get_user_profile(user_id)
        streak_days = profile.get("streak_days", 0)
    except Exception as e:
        logger.debug(f"[QuickCheckIn] 获取连续打卡天数失败: {e}")

    return QuickCheckInResponse(
        diary_id=diary.id,
        diary_date=today,
        ai_tags=ai_tags,
        outfit_suggestion=outfit_suggestion,
        created=True,
        fortune_match_score=fortune_match_score,
        outfit_recommendation=outfit_rec,
        streak_days=streak_days,
    )


def _invalidate_daily_ritual_cache(user_id: int) -> None:
    """打卡后失效 daily-ritual 缓存"""
    try:
        from apps.api.core.config import settings as _settings
        if _settings.redis_enabled:
            from apps.api.core.cache import cache as redis_cache
            today_str = date.today().isoformat()
            redis_cache.delete_sync(f"daily_ritual:{user_id}:{today_str}")
    except Exception as e:
        logger.debug(f"[Diary] daily_ritual 缓存失效失败: {e}")


def _auto_update_wear_count(user_id: int, description: str, ai_tags: dict) -> None:
    """
    打卡时自动更新穿着物品的 wear_count 和 last_worn_date

    匹配策略（按优先级）:
    1. 名称包含匹配：描述文本中出现衣橱物品名称（>= 2字）
    2. AI标签颜色匹配：AI识别的颜色/五行与衣橱物品吻合
    """
    if not description and not ai_tags:
        return

    try:
        from apps.api.core.database import DatabasePool
        from psycopg2.extras import RealDictCursor
        from datetime import date as _date

        # 查询用户衣橱（仅活跃物品）
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, category, primary_element, attributes_detail
                    FROM user_wardrobe
                    WHERE user_id = %s AND is_active = TRUE
                    LIMIT 300
                    """,
                    [user_id],
                )
                wardrobe = [dict(row) for row in cur.fetchall()]

        if not wardrobe:
            return

        matched_ids = set()
        desc = description.lower() if description else ""

        # 策略1：名称包含匹配（物品名称出现在描述中）
        if desc:
            for item in wardrobe:
                name = (item.get("name") or "").lower()
                # 名称至少2字，且描述中包含
                if len(name) >= 2 and name in desc:
                    matched_ids.add(item["id"])

        # 策略2：AI识别的五行/颜色与物品匹配（补充兜底）
        ai_elem = ai_tags.get("primary_element") or ""
        ai_color = ai_tags.get("color") or ""
        if ai_elem and not matched_ids:
            for item in wardrobe:
                if (item.get("primary_element") or "") == ai_elem:
                    # 再校验颜色是否也匹配（防止误匹配）
                    item_detail = item.get("attributes_detail") or {}
                    if isinstance(item_detail, str):
                        try:
                            item_detail = json.loads(item_detail)
                        except Exception:
                            item_detail = {}
                    item_color = ""
                    if isinstance(item_detail, dict):
                        ci = item_detail.get("颜色", {})
                        item_color = (ci.get("名称", "") if isinstance(ci, dict) else str(ci)) or ""
                    # 颜色匹配或无颜色信息时按五行匹配
                    if ai_color and item_color and ai_color in item_color:
                        matched_ids.add(item["id"])
                    elif not ai_color or not item_color:
                        matched_ids.add(item["id"])

        if not matched_ids:
            return

        # 批量更新 wear_count + last_worn_date
        today = _date.today()
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                for item_id in matched_ids:
                    cur.execute(
                        """
                        UPDATE user_wardrobe
                        SET wear_count = COALESCE(wear_count, 0) + 1,
                            last_worn_date = %s
                        WHERE id = %s
                        """,
                        [today, item_id],
                    )
            conn.commit()

        logger.info(f"[QuickCheckIn] 更新 {len(matched_ids)} 件物品的 wear_count: {list(matched_ids)}")

    except Exception as e:
        # wear_count 更新失败不影响打卡主流程
        logger.warning(f"[QuickCheckIn] wear_count 自动更新失败: {e}")


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

    # 穿搭日记反馈回流：评分更新时重新学习偏好
    if request.rating is not None:
        try:
            diary_feedback_service.process_diary_feedback(user_id, diary_id, request.rating)
        except Exception as e:
            logger.warning(f"[Diary] 反馈回流失败: {e}")

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

    user_bazi = get_user_bazi(user_id)
    outfit_items = [_item_to_dict(it) for it in diary.items]
    review = generate_ai_review(user_bazi, outfit_items)

    diary = diary_service.update_ai_review(diary_id, user_id, review) or diary
    return {"ai_review": review}



def _item_to_dict(item) -> dict:
    """将 DiaryOutfitItemResponse 转为 dict"""
    return {
        "name": item.name or "未知",
        "primary_element": item.primary_element or "",
        "category": item.category or "",
        "image_url": item.image_url or "",
    }
