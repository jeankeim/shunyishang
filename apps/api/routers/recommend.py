"""
推荐路由模块
实现 SSE 流式推荐接口
"""

import json
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from apps.api.schemas.request import RecommendRequest
from apps.api.schemas.response import RecommendResponse
from packages.ai_agents.graph import run_agent_stream

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
        
        # 运行 Agent 流式输出
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
            # 编码为 SSE 格式
            data = json.dumps(event, ensure_ascii=False)
            yield f"data: {data}\n\n".encode("utf-8")
            
            # 如果是结束标记，跳出
            if event.get("type") == "done":
                break
                
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
