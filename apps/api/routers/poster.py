"""
海报生成路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from apps.api.services.poster_service import generate_poster
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/poster", tags=["海报生成"])


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
