""" 
推荐路由模块
实现 SSE 流式推荐接口
"""

import json
import asyncio
import hashlib
from typing import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.schemas.request import RecommendRequest
from apps.api.schemas.response import RecommendResponse
from packages.ai_agents.graph import run_agent_stream
from apps.api.core.config import settings

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
        cache_key_parts = [
            request.query or "",
            request.scene or "",
            request.weather_element or "",
            str(request.user_id),
            request.retrieval_mode or "vector",
            str(request.top_k or 10),
        ]
        if request.bazi:
            cache_key_parts.extend([
                str(request.bazi.birth_year),
                str(request.bazi.birth_month),
                str(request.bazi.birth_day),
                str(request.bazi.birth_hour),
            ])
        
        cache_key_raw = "|".join(cache_key_parts)
        cache_key = f"recommend:{hashlib.md5(cache_key_raw.encode()).hexdigest()}"
        
        # 尝试从缓存获取（同步方式，避免事件循环冲突）
        cached_result = None
        if settings.redis_enabled and settings.upstash_redis_rest_url:
            try:
                import requests
                # Upstash REST API GET 方法
                response = requests.post(
                    settings.upstash_redis_rest_url,
                    headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
                    json=["GET", cache_key],
                    timeout=1.0
                )
                if response.status_code == 200:
                    data = response.json()
                    # Upstash 返回格式: {"result": "JSON字符串"} 或 {"result": null}
                    result_str = data.get("result")
                    if result_str is not None:
                        cached_result = json.loads(result_str)
                        print(f"[Cache] ✅ 推荐缓存命中: {cache_key}")
            except Exception as e:
                print(f"[Cache] 缓存读取失败: {e}")
        
        # 如果缓存命中，直接返回缓存结果
        if cached_result:
            # 快速返回缓存的分析结果
            yield f"data: {json.dumps({'type': 'analysis', 'data': cached_result['analysis']}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # 快速返回缓存的物品列表
            yield f"data: {json.dumps({'type': 'items', 'data': cached_result['items']}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # 一次性返回完整理由（不再逐字符模拟）
            reason = cached_result['reason']
            yield f"data: {json.dumps({'type': 'token', 'data': reason}, ensure_ascii=False)}\n\n".encode("utf-8")
            
            # 结束标记
            yield f"data: {json.dumps({'type': 'done', 'data': None}, ensure_ascii=False)}\n\n".encode("utf-8")
            return
        
        print(f"[Cache] ❌ 推荐缓存未命中，开始计算: {cache_key}")
        
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
        ):
            # 收集结果用于缓存
            if event.get("type") == "analysis":
                collected_analysis = event.get("data")
            elif event.get("type") == "items":
                collected_items = event.get("data")
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
                serialized = json.dumps(cache_data, ensure_ascii=False, default=str)
                
                # 写入缓存（15分钟，优化：从 5 分钟增加到 15 分钟，提升命中率）
                import requests
                # Upstash REST API SET 方法
                requests.post(
                    settings.upstash_redis_rest_url,
                    headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
                    json=["SET", cache_key, serialized],
                    timeout=1.0
                )
                # 设置过期时间
                requests.post(
                    settings.upstash_redis_rest_url,
                    headers={"Authorization": f"Bearer {settings.upstash_redis_rest_token}"},
                    json=["EXPIRE", cache_key, "900"],  # 15分钟 = 900秒
                    timeout=1.0
                )
                print(f"[Cache] 💾 推荐结果已缓存: {cache_key}")
            except Exception as e:
                print(f"[Cache] 缓存写入失败: {e}")
                
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
