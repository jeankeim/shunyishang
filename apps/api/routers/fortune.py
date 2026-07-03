"""
每日运势路由模块
"""

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.config import settings
from apps.api.routers.auth import get_current_user
from apps.api.schemas.diary import FortuneResponse, FortuneScores, LuckyElements, TodayCardResponse
from apps.api.services.fortune_engine import calculate_daily_fortune

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fortune", tags=["fortune"])


def _get_user_id(user: dict) -> int:
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")
    return user_id


def _get_user_bazi(user_id: int) -> dict:
    """从数据库获取用户八字"""
    query = "SELECT bazi, xiyong_elements FROM users WHERE id = %s"
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id])
            row = cur.fetchone()

    if not row or not row.get('bazi'):
        return {"day_master": "土", "suggested_elements": [], "avoid_elements": [], "pillars": {}}

    bazi = row['bazi']
    if isinstance(bazi, str):
        bazi = json.loads(bazi)

    return {
        "day_master": bazi.get("day_master", "土"),
        "suggested_elements": bazi.get("suggested_elements", []),
        "avoid_elements": bazi.get("avoid_elements", []),
        "pillars": bazi.get("pillars", {}),
    }


def _row_to_fortune_response(row: dict) -> FortuneResponse:
    """将数据库行转换为 FortuneResponse"""
    data = dict(row)
    scores_data = data.get('scores', {})
    if isinstance(scores_data, str):
        scores_data = json.loads(scores_data)

    lucky_data = data.get('lucky_elements', {})
    if isinstance(lucky_data, str):
        lucky_data = json.loads(lucky_data)

    bazi_snap = data.get('bazi_snapshot', {})
    if isinstance(bazi_snap, str):
        bazi_snap = json.loads(bazi_snap)

    return FortuneResponse(
        id=data['id'],
        user_id=data['user_id'],
        fortune_date=data['fortune_date'],
        scores=FortuneScores(**scores_data),
        overall_score=data['overall_score'],
        advice_text=data.get('advice_text'),
        lucky_elements=LuckyElements(**lucky_data) if lucky_data else LuckyElements(),
        outfit_suggestion=data.get('outfit_suggestion'),
        bazi_snapshot=bazi_snap,
        created_at=data['created_at'],
    )


@router.get("/today", response_model=FortuneResponse)
async def get_today_fortune(
    user: dict = Depends(get_current_user),
):
    """获取今日运势"""
    user_id = _get_user_id(user)
    today = date.today()

    # 先查缓存（当日已生成的运势）
    cached = _get_cached_fortune(user_id, today)
    if cached:
        return cached

    # 计算并存储
    return _generate_and_store(user_id, today)


@router.get("", response_model=FortuneResponse)
async def get_fortune(
    date: date = Query(..., alias="date", description="日期"),
    user: dict = Depends(get_current_user),
):
    """获取指定日期运势"""
    user_id = _get_user_id(user)

    cached = _get_cached_fortune(user_id, date)
    if cached:
        return cached

    return _generate_and_store(user_id, date)


@router.post("/generate", response_model=FortuneResponse)
async def generate_fortune(
    user: dict = Depends(get_current_user),
):
    """手动生成/刷新生成今日运势"""
    user_id = _get_user_id(user)
    today = date.today()
    return _generate_and_store(user_id, today, force=True)


def _get_cached_fortune(user_id: int, target_date: date):
    """查询已缓存的运势"""
    query = "SELECT * FROM daily_fortune WHERE user_id = %s AND fortune_date = %s"
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id, target_date])
            row = cur.fetchone()

    if row:
        return _row_to_fortune_response(row)
    return None


def _generate_and_store(user_id: int, target_date: date, force: bool = False) -> FortuneResponse:
    """计算运势并存储"""
    user_bazi = _get_user_bazi(user_id)

    result = calculate_daily_fortune(user_bazi, target_date)

    # 使用 UPSERT
    query = """
        INSERT INTO daily_fortune (
            user_id, fortune_date, scores, overall_score,
            advice_text, lucky_elements, outfit_suggestion, bazi_snapshot
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, fortune_date) DO UPDATE SET
            scores = EXCLUDED.scores,
            overall_score = EXCLUDED.overall_score,
            advice_text = EXCLUDED.advice_text,
            lucky_elements = EXCLUDED.lucky_elements,
            outfit_suggestion = EXCLUDED.outfit_suggestion,
            bazi_snapshot = EXCLUDED.bazi_snapshot
        RETURNING *
    """

    params = [
        user_id,
        target_date,
        json.dumps(result['scores']),
        result['overall_score'],
        result['advice_text'],
        json.dumps(result['lucky_elements']),
        result['outfit_suggestion'],
        json.dumps(result['bazi_snapshot']),
    ]

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()

    return _row_to_fortune_response(row)


# ============================================================
# 今日运势卡片（轻量接口，首页使用）
# ============================================================

# 忌讳颜色映射（基于五行相克）
_AVOID_COLOR_MAP = {
    "金": ["绿色", "青色"],     # 金克木
    "木": ["白色", "银色"],     # 木克土（土色）但金克木 -> 白色
    "水": ["红色", "紫色"],     # 水克火
    "火": ["黑色", "蓝色"],     # 火克金（水克火）
    "土": ["绿色", "青色"],     # 土克水（木克土）
}


def _get_fortune_level(score: int) -> str:
    """根据综合分数返回运势等级"""
    if score >= 80:
        return "great"
    elif score >= 65:
        return "good"
    elif score >= 50:
        return "normal"
    return "weak"


def _build_today_card(fortune: FortuneResponse) -> TodayCardResponse:
    """从完整运势数据构建轻量卡片"""
    bazi_snap = fortune.bazi_snapshot or {}
    lucky = fortune.lucky_elements

    # 计算忌讳颜色
    day_master = bazi_snap.get("day_master", "土")
    avoid_colors = _AVOID_COLOR_MAP.get(day_master, [])

    return TodayCardResponse(
        fortune_date=fortune.fortune_date,
        day_ganzhi=bazi_snap.get("target_day_ganzhi", ""),
        day_element=bazi_snap.get("target_day_element", ""),
        day_master=day_master,
        scores=fortune.scores,
        overall_score=fortune.overall_score,
        lucky_colors=lucky.colors[:3] if lucky.colors else [],
        avoid_colors=avoid_colors[:2],
        outfit_suggestion=fortune.outfit_suggestion or "",
        advice_text=fortune.advice_text or "",
        fortune_level=_get_fortune_level(fortune.overall_score),
    )


@router.get("/today-card", response_model=TodayCardResponse)
async def get_today_card(
    user: dict = Depends(get_current_user),
):
    """
    首页今日运势卡片（轻量接口）

    返回5维评分 + 幸运色 + 忌讳色 + 穿搭建议
    优先从 Redis 缓存读取（24h），缓存未命中则从 DB 获取或计算
    """
    user_id = _get_user_id(user)
    today = date.today()
    cache_key = f"today_card:{user_id}:{today.isoformat()}"

    # 1. 尝试 Redis 缓存
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            cached = redis_cache.get_sync(cache_key)
            if cached:
                logger.debug(f"[FortuneCard] Redis 缓存命中: {cache_key}")
                return TodayCardResponse(**cached)
        except Exception as e:
            logger.debug(f"[FortuneCard] Redis 读取失败: {e}")

    # 2. 从 DB 获取或计算
    fortune = _get_cached_fortune(user_id, today)
    if not fortune:
        fortune = _generate_and_store(user_id, today)

    card = _build_today_card(fortune)

    # 3. 写入 Redis 缓存（24h = 86400s）
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            redis_cache.set_sync(cache_key, card.model_dump(mode='json'), ttl=86400)
            logger.debug(f"[FortuneCard] Redis 缓存写入: {cache_key}")
        except Exception as e:
            logger.debug(f"[FortuneCard] Redis 写入失败: {e}")

    return card


# ========== 每日仪式摘要 API ==========

@router.get("/daily-ritual")
async def get_daily_ritual(user: dict = Depends(get_current_user)):
    """
    每日仪式摘要（首页聚合卡片）

    返回：
    - 今日运势卡片（轻量版）
    - 今日是否已打卡
    - 日记连续天数 + 总日记数
    - 修炼等级 + 积分 + 签到连续天数
    """
    user_id = _get_user_id(user)
    today = date.today()
    result = {
        "fortune": None,
        "diary": {"checked_in_today": False, "streak_days": 0, "total_diaries": 0},
        "cultivation": {"level": "初识", "points": 0, "streak_days": 0},
    }

    # 1. 今日运势卡片
    try:
        user_bazi = _get_user_bazi(user_id)
        if user_bazi.get("pillars"):  # 有八字才计算运势
            fortune = _get_cached_fortune(user_id, today)
            if not fortune:
                fortune = _generate_and_store(user_id, today)
            card = _build_today_card(fortune)
            result["fortune"] = card.model_dump(mode="json")
    except Exception as e:
        logger.debug(f"[DailyRitual] 运势计算失败: {e}")

    # 2. 日记状态
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 今日是否已打卡
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM outfit_diaries WHERE user_id = %s AND diary_date = %s",
                    [user_id, today],
                )
                result["diary"]["checked_in_today"] = (cur.fetchone()["cnt"] or 0) > 0

                # 连续打卡天数 + 总数
                cur.execute(
                    "SELECT COUNT(*) as total FROM outfit_diaries WHERE user_id = %s",
                    [user_id],
                )
                result["diary"]["total_diaries"] = cur.fetchone()["total"] or 0

                # 计算连续打卡天数
                cur.execute(
                    """SELECT DISTINCT diary_date FROM outfit_diaries
                       WHERE user_id = %s ORDER BY diary_date DESC LIMIT 365""",
                    [user_id],
                )
                dates = [r["diary_date"] for r in cur.fetchall()]
                if dates:
                    streak = 0
                    check_date = today
                    from datetime import timedelta
                    for d in dates:
                        if d == check_date:
                            streak += 1
                            check_date -= timedelta(days=1)
                        elif d == check_date - timedelta(days=1) and streak == 0:
                            # 允许今天还没打卡，从昨天开始算
                            streak = 1
                            check_date = d - timedelta(days=1)
                        else:
                            break
                    result["diary"]["streak_days"] = streak
    except Exception as e:
        logger.debug(f"[DailyRitual] 日记状态查询失败: {e}")

    # 3. 修炼/游戏化状态
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT total_points, streak_days, cultivation_level FROM user_points WHERE user_id = %s",
                    [user_id],
                )
                row = cur.fetchone()
                if row:
                    result["cultivation"]["points"] = row.get("total_points", 0)
                    result["cultivation"]["streak_days"] = row.get("streak_days", 0)
                    # 等级映射：1-5 -> 名称
                    level_names = {1: "初识", 2: "入门", 3: "通悟", 4: "精通", 5: "大师"}
                    level_icons = {1: "🌱", 2: "🌿", 3: "🌳", 4: "🏔️", 5: "⭐"}
                    lv = row.get("cultivation_level", 1)
                    result["cultivation"]["level"] = level_names.get(lv, "初识")
                    result["cultivation"]["level_icon"] = level_icons.get(lv, "🌱")
    except Exception as e:
        logger.debug(f"[DailyRitual] 修炼状态查询失败: {e}")

    return result


# ========== 付费运势报告 API ==========

@router.post("/reports/annual")
async def generate_annual_report(
    year: int = Query(None, description="报告年份，默认当前年+1"),
    user: dict = Depends(get_current_user),
):
    """生成年度运势详批报告（付费 99 元）"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    target_year = year or (date.today().year + 1)

    # 获取用户八字
    from apps.api.routers.diary import _get_user_bazi
    user_bazi = _get_user_bazi(user_id)

    from apps.api.services.fortune_report_service import fortune_report_service
    report = fortune_report_service.generate_annual_report(user_id, user_bazi, target_year)

    return report


@router.get("/reports")
async def list_reports(user: dict = Depends(get_current_user)):
    """获取用户的运势报告列表"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    from apps.api.services.fortune_report_service import fortune_report_service
    return fortune_report_service.list_reports(user_id)


@router.get("/reports/{report_id}")
async def get_report(report_id: int, user: dict = Depends(get_current_user)):
    """获取运势报告详情"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    from apps.api.services.fortune_report_service import fortune_report_service
    report = fortune_report_service.get_report(user_id, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.post("/reports/{report_id}/purchase")
async def purchase_report(report_id: int, user: dict = Depends(get_current_user)):
    """购买运势报告（Mock 支付，待企业备案后接入微信支付）"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    from apps.api.services.fortune_report_service import fortune_report_service
    result = fortune_report_service.purchase_report(user_id, report_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
