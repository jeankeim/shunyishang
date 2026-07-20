""" 
推荐路由模块
实现 SSE 流式推荐接口 + 每日精选推荐
"""

import json
import asyncio
import hashlib
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from psycopg2.extras import RealDictCursor

from apps.api.schemas.request import RecommendRequest
from apps.api.schemas.response import RecommendResponse
from packages.ai_agents.graph import run_agent_stream
from apps.api.core.config import settings
from apps.api.core.cache import cache
from apps.api.core.database import DatabasePool
from apps.api.routers.auth import get_current_user
from apps.api.services.user_service import get_user_bazi
from apps.api.services.fortune_engine import calculate_daily_fortune
from packages.utils.wuxing_rules import ELEMENT_COLOR_MAP

logger = logging.getLogger(__name__)
router = APIRouter()

# 颜色 → 五行反向映射（从 ELEMENT_COLOR_MAP 构建）
COLOR_TO_ELEMENT: Dict[str, str] = {}
for _elem, _colors in ELEMENT_COLOR_MAP.items():
    for _c in _colors:
        COLOR_TO_ELEMENT[_c] = _elem


# ============================================================
# 非穿搭意图检测
# ============================================================
# 明确的非穿搭话题（优先级高于默认穿搭判定）
_NON_FASHION_PATTERNS = [
    "今天天气怎么样", "天气预报", "几点了", "现在时间",
    "你是谁", "你叫什么", "帮我写", "写代码", "编程",
    "翻译", "数学", "物理", "化学", "历史", "地理",
    "新闻", "股票", "基金", "理财", "投资",
    "做饭", "菜谱", "美食", "餐厅推荐",
    "电影推荐", "音乐推荐", "游戏推荐",
    "感冒", "生病", "吃药", "医院",
]


def _is_fashion_intent(query: str) -> bool:
    """
    检测用户输入是否为穿搭相关意图
    
    策略：宽松判定 —— 只要不包含明确的非穿搭主题关键词，即视为穿搭意图。
    这样用户输入"今天出门"、"推荐一下"等模糊内容也能正常触发推荐流程。
    
    Args:
        query: 用户输入文本
    
    Returns:
        True = 穿搭意图, False = 非穿搭意图
    """
    if not query:
        return False
    
    query_lower = query.lower().strip()
    
    # 检查明确的非穿搭模式：匹配到任一则判定为非穿搭意图
    for pattern in _NON_FASHION_PATTERNS:
        if pattern in query_lower:
            return False
    
    # 未匹配到任何非穿搭模式，默认视为穿搭意图
    return True


# 诙谐友好的非穿搭提示语
_NON_FASHION_HINTS = [
    "哎呀，这里是五行穿搭助手的主场哦～我虽然上知天文下知地理，但最擅长的还是帮你挑衣服！问问今天穿什么吧 👗",
    "嘿嘿，这个问题超出了我的业务范围啦～我是你的专属穿搭顾问，帮你用五行选美衣才是正经事！试试问我「今天穿什么」？✨",
    "唔～这个问题我不太在行，但说到穿搭我可就来精神了！告诉我你的场景或心情，让我帮你搭配一套旺运穿搭吧 🎨",
    "哈哈，你问倒我啦！不过论穿搭我可不含糊～无论是面试、约会还是日常，我都能帮你找到最旺运的那一套！来试试吧 🌟",
]


async def generate_sse(request: RecommendRequest) -> AsyncGenerator[bytes, None]:
    """
    SSE 流式生成器
    
    3段式输出：
    1. analysis: 分析结果
    2. items: 推荐物品列表
    3. token: 逐字推荐理由
    4. done: 结束标记
    """
    try:
        # ========== 非穿搭意图检测 ==========
        if not _is_fashion_intent(request.query or ""):
            import random as _random
            hint_text = _random.choice(_NON_FASHION_HINTS)
            yield f"data: {json.dumps({'type': 'hint', 'data': hint_text}, ensure_ascii=False)}\n\n".encode("utf-8")
            yield f"data: {json.dumps({'type': 'done', 'data': None}, ensure_ascii=False)}\n\n".encode("utf-8")
            return
        
        # 生成缓存键（基于查询条件）
        # 注意：缓存键必须覆盖所有会影响推荐结果的输入，否则不同请求会命中错误缓存。
        cache_key_parts = [
            request.query or "",
            request.scene or "",
            request.weather_element or "",
            str(request.user_id),
            request.retrieval_mode or "public",
            str(request.top_k),
            # 性别影响性别过滤，必须纳入缓存键
            request.gender or "",
            # 旅行/出差参数直接改变多天行程规划结果
            str(request.travel_days) if request.travel_days is not None else "",
            request.destination or "",
            request.luggage_size or "",
            # 换一批：不同批次返回不同结果
            str(request.batch_index),
        ]
        # 天气详情（温度/描述/湿度/风力）会改变温度过滤与评分，必须纳入缓存键
        if request.weather:
            cache_key_parts.extend([
                str(request.weather.temperature) if request.weather.temperature is not None else "",
                request.weather.weather_desc or "",
                str(request.weather.humidity) if request.weather.humidity is not None else "",
                str(request.weather.wind_level) if request.weather.wind_level is not None else "",
            ])
        if request.bazi:
            cache_key_parts.extend([
                str(request.bazi.birth_year),
                str(request.bazi.birth_month),
                str(request.bazi.birth_day),
                str(request.bazi.birth_hour),
                request.bazi.gender or "",
            ])
        
        cache_key_raw = "|".join(cache_key_parts)
        cache_key = f"recommend:{hashlib.md5(cache_key_raw.encode()).hexdigest()}"
        
        # 尝试从缓存获取（使用统一的 cache.py 异步接口）
        cached_result = None
        if settings.redis_enabled:
            try:
                cached_result = await cache.get(cache_key)
                if cached_result:
                    logger.info(f"[Cache] 推荐缓存命中: {cache_key}")
            except Exception as e:
                logger.error(f"[Cache] 缓存读取失败: {e}")
        
        # 如果缓存命中，直接返回缓存结果
        if cached_result:
            # 快速返回缓存的分析结果
            yield f"data: {json.dumps({'type': 'analysis', 'data': cached_result['analysis']}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # 快速返回缓存的物品列表
            yield f"data: {json.dumps({'type': 'items', 'data': cached_result['items']}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # P2-98 快速返回缓存的旅行规划（如有）
            if cached_result.get('travel_plan'):
                yield f"data: {json.dumps({'type': 'travel_plan', 'data': cached_result['travel_plan']}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # 一次性返回完整理由（不再逐字符模拟）
            reason = cached_result['reason']
            yield f"data: {json.dumps({'type': 'token', 'data': reason}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # 结束标记
            yield f"data: {json.dumps({'type': 'done', 'data': None}, ensure_ascii=False)}\n\n".encode("utf-8")
            return
        
        logger.info(f"[Cache] 推荐缓存未命中，开始计算: {cache_key}")
        
        # 准备输入参数
        bazi_input = None
        if request.bazi:
            bazi_input = {
                "birth_year": request.bazi.birth_year,
                "birth_month": request.bazi.birth_month,
                "birth_day": request.bazi.birth_day,
                "birth_hour": request.bazi.birth_hour,
                "gender": request.bazi.gender,
            }
        
        # 准备天气信息
        weather_info = None
        if request.weather:
            weather_info = {
                "temperature": request.weather.temperature,
                "weather_desc": request.weather.weather_desc,
                "humidity": request.weather.humidity,
                "wind_level": request.weather.wind_level,
            }
        
        # 运行 Agent 流式输出，并收集结果用于缓存
        collected_analysis = None
        collected_items = None
        collected_travel_plan = None  # P2-98：收集旅行规划事件
        collected_reason = []
        
        # 优先使用 request.gender，其次从 bazi_input 中获取
        user_gender = request.gender or (bazi_input.get("gender") if bazi_input else None)
        
        for event in run_agent_stream(
            user_input=request.query,
            scene=request.scene,
            weather_element=request.weather_element,
            weather_info=weather_info,
            bazi_input=bazi_input,
            user_gender=user_gender,
            user_id=request.user_id,
            retrieval_mode=request.retrieval_mode,
            top_k=request.top_k,
            travel_days=request.travel_days,
            destination=request.destination,
            luggage_size=request.luggage_size,
            batch_index=request.batch_index,
        ):
            # 收集结果用于缓存
            if event.get("type") == "analysis":
                collected_analysis = event.get("data")
            elif event.get("type") == "items":
                collected_items = event.get("data")
            elif event.get("type") == "travel_plan":
                collected_travel_plan = event.get("data")
            elif event.get("type") == "token":
                collected_reason.append(event.get("data", ""))
            
            # 编码为 SSE 格式
            data = json.dumps(event, ensure_ascii=False)
            yield f"data: {data}\n\n".encode("utf-8")
            
            # 如果是结束标记，跳出
            if event.get("type") == "done":
                break
        
        # 缓存完整结果（如果收集到了）
        if collected_analysis and collected_items and settings.redis_enabled:
            try:
                cache_data = {
                    "analysis": collected_analysis,
                    "items": collected_items,
                    "reason": "".join(collected_reason),
                    "timestamp": datetime.now().isoformat()
                }
                # P2-98：将旅行规划一并缓存，避免缓存命中时丢失行程
                if collected_travel_plan:
                    cache_data["travel_plan"] = collected_travel_plan
                # 使用统一的 cache.py 异步接口写入缓存（15分钟）
                await cache.set(cache_key, cache_data, ttl=900)
                logger.info(f"[Cache] 推荐结果已缓存: {cache_key}")
            except Exception as e:
                logger.error(f"[Cache] 缓存写入失败: {e}")
                
    except Exception as e:
        # 错误处理：记录完整堆栈，避免 SSE 错误事件成为诊断盲区
        logger.error(f"[SSE] 推荐流程异常: {e}", exc_info=True)
        error_event = {"type": "error", "data": str(e)}
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n".encode("utf-8")
        
        # 发送结束标记
        done_event = {"type": "done", "data": None}
        yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n".encode("utf-8")


@router.post(
    "/recommend/stream",
    summary="流式推荐接口",
    responses={
        200: {
            "description": "SSE 流式响应",
            "content": {"text/event-stream": {}}
        }
    }
)
async def recommend_stream(request: RecommendRequest):
    """
    流式推荐接口
    
    **源码位置**: `apps/api/routers/recommend.py:recommend_stream()` (第96行起)
    
    **核心逻辑**:
    1. 接收用户查询、八字、天气等上下文
    2. 调用 `packages/ai_agents/graph.py:run_agent_stream()` 运行推荐 Agent
    3. 通过 SSE 流式返回结果
    
    **SSE 事件类型**:
    - `analysis`: 五行分析结果
    - `items`: 推荐物品列表
    - `token`: 逐字推荐理由（流式）
    - `done`: 结束标记
    
    **依赖**: `packages/ai_agents/graph.py:run_agent_stream()`
    """
    return StreamingResponse(
        generate_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁止 nginx 缓冲
            "Connection": "keep-alive",
        }
    )


# ========== 每日精选推荐 ==========


def _score_wardrobe_item(
    item: Dict[str, Any],
    lucky_elements: List[str],
    lucky_colors: List[str],
) -> int:
    """
    为衣橱单品计算与今日运势的匹配度分数（0-100）。

    评分维度：
    - 主五行命中幸运五行：+40
    - 副五行命中幸运五行：+15
    - 颜色命中幸运色：+20
    - 颜色所属五行命中幸运五行：+15
    - wear_count 少（≤2）：+10（鼓励穿少穿的衣物）
    """
    score = 0
    primary = item.get("primary_element") or ""
    secondary = item.get("secondary_element") or ""

    # 五行匹配
    if primary in lucky_elements:
        score += 40
    if secondary and secondary in lucky_elements:
        score += 15

    # 颜色匹配（从 attributes_detail 提取颜色名称）
    detail = item.get("attributes_detail") or {}
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            detail = {}
    color_name = ""
    if isinstance(detail, dict):
        color_info = detail.get("颜色", {})
        if isinstance(color_info, dict):
            color_name = color_info.get("名称", "") or ""

    if color_name and color_name in lucky_colors:
        score += 20
    # 颜色本身的五行
    color_elem = COLOR_TO_ELEMENT.get(color_name, "")
    if color_elem and color_elem in lucky_elements:
        score += 15

    # wear_count 加分（少穿的衣物优先）
    wear_count = item.get("wear_count") or 0
    if wear_count <= 2:
        score += 10

    return min(score, 100)


def _build_reason(item: Dict[str, Any], lucky_element: str, lucky_color: str) -> str:
    """生成推荐理由（≤50字）"""
    name = item.get("name", "单品")
    elem = item.get("primary_element", "")
    parts = []
    if elem and elem == lucky_element:
        parts.append(f"五行属{elem}，契合今日幸运元素")
    elif elem:
        parts.append(f"五行属{elem}")
    if lucky_color:
        parts.append(f"宜搭配{lucky_color}系")
    reason = f"「{name}」{'，'.join(parts)}，助力今日运势。"
    # 截断保护
    return reason[:50] if len(reason) <= 50 else reason[:47] + "..."


@router.get(
    "/recommend/daily-pick",
    summary="每日精选推荐",
    description="基于用户八字和当日运势，从个人衣橱中推荐1件精选单品",
)
async def get_daily_pick(
    current_user: dict = Depends(get_current_user),
):
    """每日精选推荐 - 基于用户八字和当日运势从衣橱推荐1件单品"""
    user_id = current_user["id"]
    today = date.today()

    # ── 1. 检查 Redis 缓存 ──────────────────────────────────────────────────
    cache_key = f"daily_pick:{user_id}:{today.isoformat()}"
    if settings.redis_enabled:
        try:
            cached = await cache.get(cache_key)
            if cached:
                logger.info(f"[DailyPick] 缓存命中: {cache_key}")
                return cached
        except Exception as e:
            logger.error(f"[DailyPick] 缓存读取失败: {e}")

    # ── 2. 获取用户八字信息 ──────────────────────────────────────────────────
    user_bazi = get_user_bazi(user_id)  # 同步调用（psycopg2）

    # ── 3. 计算今日运势 ──────────────────────────────────────────────────────
    fortune = calculate_daily_fortune(user_bazi, today)
    lucky_elements: List[str] = fortune.get("lucky_elements", {}).get("elements", [])
    lucky_colors: List[str] = fortune.get("lucky_elements", {}).get("colors", [])
    primary_lucky_element = lucky_elements[0] if lucky_elements else user_bazi.get("day_master", "土")
    primary_lucky_color = lucky_colors[0] if lucky_colors else ""

    # ── 4. 查询用户衣橱 ──────────────────────────────────────────────────────
    wardrobe_query = """
        SELECT id, user_id, item_code, name, category, image_url,
               primary_element, secondary_element, attributes_detail,
               wear_count, is_favorite, energy_intensity
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 200
    """
    items: List[Dict[str, Any]] = []
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(wardrobe_query, [user_id])
                items = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"[DailyPick] 衣橱查询失败: {e}")

    # ── 5. 评分并选出最佳单品 ────────────────────────────────────────────────
    best_item: Optional[Dict[str, Any]] = None
    best_score = -1

    for item in items:
        score = _score_wardrobe_item(item, lucky_elements, lucky_colors)
        if score > best_score:
            best_score = score
            best_item = item

    # ── 6. 构建响应 ──────────────────────────────────────────────────────────
    if best_item:
        # 序列化 attributes_detail（可能是 dict 或 str）
        detail = best_item.get("attributes_detail") or {}
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except Exception:
                detail = {}

        item_payload = {
            "id": best_item["id"],
            "name": best_item.get("name", ""),
            "category": best_item.get("category"),
            "image_url": best_item.get("image_url"),
            "primary_element": best_item.get("primary_element"),
            "secondary_element": best_item.get("secondary_element"),
            "wear_count": best_item.get("wear_count", 0),
            "is_favorite": best_item.get("is_favorite", False),
        }
        reason = _build_reason(best_item, primary_lucky_element, primary_lucky_color)
        match_score = best_score
    else:
        item_payload = None
        reason = f"今日幸运五行「{primary_lucky_element}」，建议穿着{primary_lucky_color or '相应'}色系衣物增运"
        match_score = 0

    result = {
        "item": item_payload,
        "reason": reason,
        "lucky_element": primary_lucky_element,
        "lucky_color": primary_lucky_color,
        "match_score": match_score,
        "date": today.isoformat(),
        "overall_fortune": fortune.get("overall_score", 0),
    }

    # ── 7. 写入缓存（TTL 24h）────────────────────────────────────────────────
    if settings.redis_enabled:
        try:
            await cache.set(cache_key, result, ttl=86400)
            logger.info(f"[DailyPick] 结果已缓存: {cache_key}")
        except Exception as e:
            logger.error(f"[DailyPick] 缓存写入失败: {e}")

    return result


# ========== 用户不喜欢物品 ==========


@router.post(
    "/recommend/dislike",
    summary="记录用户不喜欢的物品",
)
async def report_dislike(
    item_code: str = Query(..., description="物品编码"),
    reason: Optional[str] = Query(None, description="原因"),
    current_user: dict = Depends(get_current_user),
):
    """记录用户不喜欢的物品，后续推荐将排除"""
    user_id = current_user["id"]
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_disliked_items (user_id, item_code, reason)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, item_code) DO NOTHING
                """, [user_id, item_code, reason])
                conn.commit()
        logger.info(f"[Dislike] user={user_id} item={item_code} reason={reason}")
        return {"success": True, "message": "已记录，后续不再推荐此物品"}
    except Exception as e:
        logger.error(f"[Dislike] 记录失败: {e}")
        raise HTTPException(status_code=500, detail="记录失败")


@router.get(
    "/recommend/disliked",
    summary="获取用户不喜欢的物品列表",
)
async def get_disliked_items(
    current_user: dict = Depends(get_current_user),
):
    """获取用户已标记不喜欢的物品列表"""
    user_id = current_user["id"]
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT d.item_code, d.reason, d.created_at, i.name, i.category, i.image_url
                    FROM user_disliked_items d
                    LEFT JOIN items i ON d.item_code = i.item_code
                    WHERE d.user_id = %s
                    ORDER BY d.created_at DESC
                """, [user_id])
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"[Dislike] 查询失败: {e}")
        return []


@router.delete(
    "/recommend/dislike/{item_code}",
    summary="取消不喜欢",
)
async def remove_dislike(
    item_code: str,
    current_user: dict = Depends(get_current_user),
):
    """取消标记不喜欢"""
    user_id = current_user["id"]
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_disliked_items WHERE user_id = %s AND item_code = %s",
                    [user_id, item_code]
                )
                conn.commit()
        return {"success": True}
    except Exception as e:
        logger.error(f"[Dislike] 删除失败: {e}")
        raise HTTPException(status_code=500, detail="操作失败")


# ========== 每日智能穿搭建议 ==========


@router.get(
    "/recommend/daily-outfit",
    summary="每日智能穿搭建议",
    description="基于用户八字、运势、天气、季节、偏好和衣橱，自动推荐3-5件完整搭配",
)
async def get_daily_outfit(
    batch_index: int = Query(0, ge=0, le=2, description="换一批批次 (0-2)"),
    city: Optional[str] = Query(None, max_length=20, description="前端定位城市（优先于用户设置）"),
    current_user: dict = Depends(get_current_user),
):
    """
    首页智能每日穿搭建议

    用户打开应用时无需输入任何内容，即可看到当天专属的穿搭建议。
    系统基于用户八字命理、当日运势、实时天气、季节、个人偏好和衣橱库存自动生成。

    响应结构:
    - outfit_items: 3-5件搭配物品
    - reasoning: 推荐理由
    - weather_summary: 天气摘要
    - fortune_summary: 运势摘要
    - style_tip: 穿搭贴士
    - match_score: 综合匹配分 (0-100)
    """
    user_id = current_user["id"]
    today = date.today()

    # ── Redis 缓存 ──────────────────────────────────────────────────────────
    cache_key = f"daily_outfit:{user_id}:{today.isoformat()}:{batch_index}:{city or 'default'}"
    if settings.redis_enabled:
        try:
            cached = await cache.get(cache_key)
            if cached:
                logger.info(f"[DailyOutfit] 缓存命中: {cache_key}")
                return cached
        except Exception as e:
            logger.debug(f"[DailyOutfit] 缓存读取失败: {e}")

    # ── 调用核心服务 ────────────────────────────────────────────────────────
    from apps.api.services.daily_outfit_service import generate_daily_outfit

    result = generate_daily_outfit(user_id, batch_index=batch_index, city_override=city)

    # ── 写入缓存 ────────────────────────────────────────────────────────────
    if settings.redis_enabled:
        # TTL: 当日剩余秒数（最多 24h）
        now = datetime.now()
        end_of_day = datetime(today.year, today.month, today.day, 23, 59, 59)
        ttl = max(600, int((end_of_day - now).total_seconds()))  # 最少 10 分钟
        try:
            await cache.set(cache_key, result, ttl=ttl)
            logger.info(f"[DailyOutfit] 结果已缓存 (TTL={ttl}s): {cache_key}")
        except Exception as e:
            logger.debug(f"[DailyOutfit] 缓存写入失败: {e}")

    return result
