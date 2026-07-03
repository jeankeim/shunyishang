"""
旅行穿搭推荐路由
提供多天旅行穿搭推荐接口
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.routers.auth import get_current_user
from apps.api.services.travel_recommend_service import generate_travel_recommendation

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 请求/响应模型
# ============================================================

class TravelRecommendRequest(BaseModel):
    """旅行推荐请求体"""
    destination: str = Field(..., min_length=1, max_length=50, description="目的地城市")
    days: int = Field(..., ge=1, le=30, description="旅行天数")
    scenes_per_day: List[str] = Field(
        default_factory=list,
        description="每天场景列表（长度应等于 days，不足自动填充为'日常'）"
    )
    luggage_size: str = Field("中", pattern="^(小|中|大)$", description="行李箱大小：小/中/大")
    bazi: Optional[dict] = Field(None, description="八字信息（可选）")


class TravelRecommendResponse(BaseModel):
    """旅行推荐响应体"""
    outfits_plan: List[dict]
    luggage_summary: dict
    weather_forecast: List[dict]
    wuxing_analysis: dict


# ============================================================
# 路由
# ============================================================

@router.post(
    "/travel/recommend",
    response_model=TravelRecommendResponse,
    summary="旅行穿搭推荐",
)
async def travel_recommend(
    request: TravelRecommendRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    旅行穿搭推荐接口

    根据目的地、天数、场景和行李箱大小，生成多天穿搭推荐方案。

    **核心逻辑**:
    1. 调用天气预测获取目的地多天天气
    2. 调用旅行规划器生成每日穿搭
    3. 集成八字五行分析
    4. 优化行李箱容量

    **请求示例**:
    ```json
    {
        "destination": "北京",
        "days": 3,
        "scenes_per_day": ["出差", "商务", "日常"],
        "luggage_size": "中",
        "bazi": {"suggested_elements": ["金", "水"]}
    }
    ```

    **返回**:
    - outfits_plan: 每日穿搭计划
    - luggage_summary: 行李摘要（含评分）
    - weather_forecast: 天气预测
    - wuxing_analysis: 五行分析
    """
    # 参数验证
    if request.days > 0 and request.scenes_per_day and len(request.scenes_per_day) > request.days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"场景列表长度({len(request.scenes_per_day)})不能超过天数({request.days})"
        )

    try:
        result = generate_travel_recommendation(
            user_id=current_user.get("id"),
            destination=request.destination,
            days=request.days,
            scenes_per_day=request.scenes_per_day,
            luggage_size=request.luggage_size,
            bazi=request.bazi,
        )
        return TravelRecommendResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[旅行推荐] 接口异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"旅行推荐生成失败: {str(e)}"
        )
