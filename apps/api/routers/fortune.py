"""
每日运势路由模块
"""

import json
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.services.user_service import get_user_bazi
from apps.api.core.config import settings
from apps.api.core.security import decode_access_token
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

    huangli_data = data.get('huangli', {})
    if isinstance(huangli_data, str):
        huangli_data = json.loads(huangli_data)

    ai_narrative_data = data.get('ai_narrative', {})
    if isinstance(ai_narrative_data, str):
        ai_narrative_data = json.loads(ai_narrative_data)

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
        huangli=huangli_data,
        ai_narrative=ai_narrative_data,
        created_at=data['created_at'],
    )


@router.get("/today", response_model=FortuneResponse)
async def get_today_fortune(
    user: dict = Depends(get_current_user),
):
    """获取今日运势"""
    user_id = _get_user_id(user)
    today = date.today()

    # Redis 缓存层（优先于 DB 查询）
    cache_key = f"fortune_today:{user_id}:{today.isoformat()}"
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            cached = redis_cache.get_sync(cache_key)
            if cached:
                logger.debug(f"[FortuneToday] Redis 缓存命中: {cache_key}")
                return FortuneResponse(**cached)
        except Exception as e:
            logger.debug(f"[FortuneToday] Redis 读取失败: {e}")

    # DB 持久化缓存
    cached = _get_cached_fortune(user_id, today)
    if cached:
        # 回写 Redis
        if settings.redis_enabled:
            try:
                from apps.api.core.cache import cache as redis_cache
                redis_cache.set_sync(cache_key, cached.model_dump(mode='json'), ttl=86400)
            except Exception as e:
                logger.debug(f"[FortuneToday] Redis 写入失败: {e}")
        return cached

    # 计算并存储
    result = _generate_and_store(user_id, today, generate_ai=True)

    # 写入 Redis
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            redis_cache.set_sync(cache_key, result.model_dump(mode='json'), ttl=86400)
        except Exception as e:
            logger.debug(f"[FortuneToday] Redis 写入失败: {e}")

    return result


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

    return _generate_and_store(user_id, date, generate_ai=True)


@router.post("/generate", response_model=FortuneResponse)
async def generate_fortune(
    user: dict = Depends(get_current_user),
):
    """手动生成/刷新生成今日运势"""
    user_id = _get_user_id(user)
    today = date.today()
    result = _generate_and_store(user_id, today, force=True, generate_ai=True)

    # 清除 Redis 缓存，确保后续 GET 请求拿到最新数据
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            today_str = today.isoformat()
            redis_cache.delete_sync(f"fortune_today:{user_id}:{today_str}")
            redis_cache.delete_sync(f"today_card:{user_id}:{today_str}")
            redis_cache.delete_sync(f"daily_ritual:{user_id}:{today_str}")
        except Exception as e:
            logger.debug(f"[FortuneGenerate] Redis cache invalidation failed: {e}")

    return result


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


def _generate_and_store(user_id: int, target_date: date, force: bool = False, generate_ai: bool = False) -> FortuneResponse:
    """计算运势并存储"""
    user_bazi = get_user_bazi(user_id)

    result = calculate_daily_fortune(user_bazi, target_date, generate_ai=generate_ai)

    # 使用 UPSERT
    query = """
        INSERT INTO daily_fortune (
            user_id, fortune_date, scores, overall_score,
            advice_text, lucky_elements, outfit_suggestion, bazi_snapshot,
            huangli, ai_narrative
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, fortune_date) DO UPDATE SET
            scores = EXCLUDED.scores,
            overall_score = EXCLUDED.overall_score,
            advice_text = EXCLUDED.advice_text,
            lucky_elements = EXCLUDED.lucky_elements,
            outfit_suggestion = EXCLUDED.outfit_suggestion,
            bazi_snapshot = EXCLUDED.bazi_snapshot,
            huangli = EXCLUDED.huangli,
            ai_narrative = EXCLUDED.ai_narrative
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
        json.dumps(result.get('huangli', {})),
        json.dumps(result.get('ai_narrative', {})),
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

    # 黄历摘要
    huangli = fortune.huangli or {}
    ai_narrative = fortune.ai_narrative or {}

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
        huangli_yi=huangli.get("yi", [])[:4],
        huangli_ji=huangli.get("ji", [])[:4],
        chong_sha=huangli.get("chong_sha", ""),
        ai_overview=ai_narrative.get("overview", ""),
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


# ========== 运势周报 API ==========

async def _get_optional_user(request: Request) -> dict | None:
    """尝试从请求头提取用户身份，未登录或 token 无效时返回 None（不抛异常）"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    payload = decode_access_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nickname, gender, bazi FROM users WHERE id = %s AND is_active = TRUE",
                    (user_id,),
                )
                row = cur.fetchone()
                if row:
                    return {"id": row[0], "nickname": row[1], "gender": row[2], "bazi": row[3]}
    except Exception as e:
        logger.debug(f"[OptionalAuth] DB查询失败: {e}")
    return None


@router.get("/weekly")
async def get_weekly_fortune(request: Request):
    """
    获取本周运势周报

    - 已登录：返回基于用户八字的个性化周报
    - 未登录：返回通用基础版周报（不含个人八字分析）
    缓存键: weekly_fortune:{user_id|anonymous}:{year}:{week}  TTL 604800s（7天）
    """
    user = await _get_optional_user(request)

    now = datetime.now()
    iso_cal = now.isocalendar()
    week_key = f"{iso_cal[0]}:{iso_cal[1]}"
    user_key = str(user["id"]) if user else "anonymous"
    cache_key = f"weekly_fortune:{user_key}:{week_key}"

    # Redis 缓存检查
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            cached = redis_cache.get_sync(cache_key)
            if cached:
                logger.debug(f"[WeeklyFortune] Redis 缓存命中: {cache_key}")
                return cached
        except Exception as e:
            logger.debug(f"[WeeklyFortune] Redis 读取失败: {e}")

    # 计算周报
    from apps.api.services.weekly_fortune_service import WeeklyFortuneService
    service = WeeklyFortuneService()

    if user:
        result = await service.calculate_weekly_fortune(user["id"])
    else:
        result = service._fallback_weekly_report()

    # 写入缓存 TTL 7天 = 604800s
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            redis_cache.set_sync(cache_key, result, ttl=604800)
            logger.debug(f"[WeeklyFortune] Redis 缓存写入: {cache_key}")
        except Exception as e:
            logger.debug(f"[WeeklyFortune] Redis 写入失败: {e}")

    return result


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
    date_str = today.isoformat()

    # Redis 整体缓存（1小时 TTL）
    cache_key = f"daily_ritual:{user_id}:{date_str}"
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            cached = redis_cache.get_sync(cache_key)
            if cached:
                logger.debug(f"[DailyRitual] Redis 缓存命中: {cache_key}")
                return cached
        except Exception as e:
            logger.debug(f"[DailyRitual] Redis 读取失败: {e}")

    result = {
        "fortune": None,
        "diary": {"checked_in_today": False, "streak_days": 0, "total_diaries": 0},
        "cultivation": {"level": "初识", "points": 0, "streak_days": 0},
    }

    # 1. 今日运势卡片
    try:
        user_bazi = get_user_bazi(user_id)
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

    # 写入 Redis 缓存
    if settings.redis_enabled:
        try:
            from apps.api.core.cache import cache as redis_cache
            redis_cache.set_sync(cache_key, result, ttl=3600)
            logger.debug(f"[DailyRitual] Redis 缓存写入: {cache_key}")
        except Exception as e:
            logger.debug(f"[DailyRitual] Redis 写入失败: {e}")

    return result


# ========== 运势报告 API（个人备案版：免费） ==========

# 年度报告每年最多生成次数（防止重复消耗 AI 调用）
ANNUAL_REPORT_YEARLY_LIMIT = 3


@router.post("/reports/annual", status_code=202)
async def generate_annual_report(
    year: int = Query(None, description="报告年份，默认当前年"),
    user: dict = Depends(get_current_user),
):
    """提交年度运势详批报告生成任务（异步，通过 GET /tasks/{task_id} 查询结果）"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    target_year = year or date.today().year

    # 校验用户已有八字信息（尽早失败，避免任务入队后才报错）
    get_user_bazi(user_id)

    # 限频：每用户每年最多生成 ANNUAL_REPORT_YEARLY_LIMIT 次
    from apps.api.services.fortune_report_service import fortune_report_service
    existing = fortune_report_service.count_reports_for_year(user_id, target_year)
    if existing >= ANNUAL_REPORT_YEARLY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"{target_year}年年度报告最多生成 {ANNUAL_REPORT_YEARLY_LIMIT} 次，您已达上限，可直接查看已生成的报告",
        )

    from apps.api.services import task_service
    task_id = task_service.create_task(
        user_id=user_id,
        task_type="annual_report",
        payload={"year": target_year},
    )

    return {"task_id": task_id, "status": "pending"}


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


# 个人备案版：购买端点已禁用，报告生成后自动可用
# @router.post("/reports/{report_id}/purchase")
# async def purchase_report(report_id: int, user: dict = Depends(get_current_user)):
#     """购买运势报告（个人备案版：已禁用）"""
#     ...
