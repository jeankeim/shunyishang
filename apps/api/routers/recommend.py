""" 
推荐路由模块
实现 SSE 流式推荐接口
"""

import json
import asyncio
import hashlib
import logging
from typing import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.schemas.request import RecommendRequest
from apps.api.schemas.response import RecommendResponse
from packages.ai_agents.graph import run_agent_stream
from apps.api.core.config import settings
from apps.api.core.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter()


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
        # 错误处理
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
