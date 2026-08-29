"""
海报生成路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Optional
from apps.api.services.poster_service import generate_poster, generate_week_poster_bytes
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/poster", tags=["海报生成"])


class PosterGenerateRequest(BaseModel):
    """海报生成请求"""
    layout: str = "simple"  # simple/wuxing/card
    title: str = "今日五行穿搭推荐"
    items: List[dict] = []
    xiyong_elements: List[str] = []
    theme: str = "fire"  # fire/wood/earth/metal/water
    quote: Optional[str] = ""
    signature: Optional[str] = "顺衣尚"
    scene: Optional[str] = ""
    username: Optional[str] = ""


@router.post("/generate")
async def generate_poster_image(request: PosterGenerateRequest):
    """
    生成海报图片
    
    Returns:
        PNG 图片二进制数据
    """
    try:
        logger.info(f"收到海报生成请求: {request.title}")
        
        # 生成海报
        image_bytes = generate_poster(
            layout=request.layout,
            title=request.title,
            items=request.items,
            xiyong_elements=request.xiyong_elements,
            theme=request.theme,
            quote=request.quote or "",
            signature=request.signature or "顺衣尚",
            scene=request.scene or "",
            username=request.username or "",
        )
        
        # 返回图片
        # 处理中文文件名编码
        from urllib.parse import quote
        filename_encoded = quote(f"{request.title}.png")
        
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}",
                "Cache-Control": "no-cache",
            }
        )
        
    except Exception as e:
        logger.error(f"海报生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"海报生成失败: {str(e)}")


@router.post("/generate-base64")
async def generate_poster_base64(request: PosterGenerateRequest):
    """
    生成海报并返回 Base64 编码
    
    Returns:
        { "image": "base64_string", "filename": "xxx.png" }
    """
    try:
        import base64
        
        logger.info(f"收到 Base64 海报生成请求: {request.title}")
        
        # 生成海报
        image_bytes = generate_poster(
            layout=request.layout,
            title=request.title,
            items=request.items,
            xiyong_elements=request.xiyong_elements,
            theme=request.theme,
            quote=request.quote or "",
            signature=request.signature or "顺衣尚",
            scene=request.scene or "",
            username=request.username or "",
        )
        
        # 转换为 Base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        return {
            "image": image_base64,
            "filename": f"{request.title}.png",
            "size": len(image_bytes),
        }
        
    except Exception as e:
        logger.error(f"Base64 海报生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"海报生成失败: {str(e)}")


# ============================================================
# 一周穿搭海报
# ============================================================

VALID_WEEK_THEMES = {"fire", "wood", "earth", "metal", "water"}


class WeekPosterRequest(BaseModel):
    """一周穿搭海报请求（days 来自 GET /recommend/week-outfit）"""
    days: List[dict]
    theme: str = "wood"
    username: Optional[str] = ""
    signature: Optional[str] = "顺衣尚"
    city: Optional[str] = ""

    @field_validator("days")
    @classmethod
    def _check_days(cls, v: List[dict]) -> List[dict]:
        if not v:
            raise ValueError("days 不能为空")
        if len(v) > 7:
            raise ValueError("days 最多 7 天")
        for day in v:
            if not str(day.get("date") or "").strip():
                raise ValueError("每一天都需要 date 字段")
            items = day.get("items")
            if items is not None and not isinstance(items, list):
                raise ValueError("items 必须是数组")
        return v

    @field_validator("theme")
    @classmethod
    def _check_theme(cls, v: str) -> str:
        return v if v in VALID_WEEK_THEMES else "wood"


@router.post("/week")
async def generate_week_poster_image(request: WeekPosterRequest):
    """
    生成一周穿搭海报并返回 Base64 编码

    Returns:
        { "image": "base64_string", "filename": "xxx.png", "size": 字节数 }
    """
    try:
        import base64

        logger.info(f"收到一周海报生成请求: {len(request.days)} 天, theme={request.theme}")

        image_bytes = generate_week_poster_bytes(
            days=request.days,
            theme=request.theme,
            username=request.username or "",
            signature=request.signature or "顺衣尚",
            city=request.city or "",
        )

        return {
            "image": base64.b64encode(image_bytes).decode("utf-8"),
            "filename": "一周穿搭海报.png",
            "size": len(image_bytes),
        }

    except Exception as e:
        logger.error(f"一周海报生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"海报生成失败: {str(e)}")
