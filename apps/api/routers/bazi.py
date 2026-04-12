"""
八字计算路由模块
提供独立的八字计算接口，供前端实时预览雷达图
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from packages.utils.bazi_calculator import calculate_bazi
from apps.api.core.cache import cache

router = APIRouter()


class BaziCalculateRequest(BaseModel):
    """八字计算请求"""
    birth_year: int = Field(..., ge=1900, le=2100, description="出生年（公历）")
    birth_month: int = Field(..., ge=1, le=12, description="出生月")
    birth_day: int = Field(..., ge=1, le=31, description="出生日")
    birth_hour: int = Field(..., ge=0, le=23, description="出生时（0-23）")
    gender: str = Field(..., pattern="^(男|女)$", description="性别：男/女")


class BaziCalculateResponse(BaseModel):
    """八字计算响应"""
    pillars: Dict[str, str] = Field(..., description="四柱：年柱、月柱、日柱、时柱")
    eight_chars: List[str] = Field(..., description="八字：8个字")
    five_elements_count: Dict[str, int] = Field(..., description="五行统计")
    dominant_element: str = Field(..., description="最旺五行")
    lacking_element: Optional[str] = Field(None, description="缺失五行")
    day_master: str = Field(..., description="日元五行")
    month_element: str = Field(..., description="月令五行")
    suggested_elements: List[str] = Field(..., description="喜用神")
    avoid_elements: List[str] = Field(..., description="忌神")
    reasoning: str = Field(..., description="推理说明")


@router.post(
    "/calculate",
    response_model=BaziCalculateResponse,
    summary="八字计算接口",
)
async def bazi_calculate(request: BaziCalculateRequest):
    """
    八字计算接口
    
    **源码位置**: `apps/api/routers/bazi.py:bazi_calculate()` (第44行起)
    
    **核心逻辑**:
    1. 生成缓存键（出生年月日时+性别）
    2. 优先从缓存读取结果
    3. 缓存未命中则调用 `packages/utils/bazi_calculator.py:calculate_bazi()`
    4. 将结果写入缓存后返回
    
    **用途**: 前端在用户输入八字后，可先调用此接口预览雷达图
    
    **依赖**: `packages/utils/bazi_calculator.py:calculate_bazi()`
    """
    # 生成缓存键
    birth_key = f"bazi:{request.birth_year}:{request.birth_month}:{request.birth_day}:{request.birth_hour}:{request.gender}"
    
    # 尝试读取缓存
    cached = await cache.get(birth_key)
    if cached:
        print(f"[Cache] 八字缓存命中: {birth_key}")
        return cached
    
    try:
        result = calculate_bazi(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            gender=request.gender,
        )
        
        # 写入缓存（24小时）
        await cache.set(birth_key, result, ttl=86400)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"八字计算失败: {str(e)}")
