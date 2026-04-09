"""
衣橱管理路由模块
提供衣橱 CRUD 和 AI 打标接口
"""

import logging
import json
import os
import time
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.routers.auth import get_current_user
from apps.api.schemas.wardrobe import (
    AITaggingResult,
    WardrobeItemCreate,
    WardrobeItemResponse,
    WardrobeItemListResponse,
    WardrobeItemUpdate,
    FeedbackCreate,
    FeedbackResponse,
)
from apps.api.services.ai_tagging_service import ai_tagging_service
from apps.api.services.embedding_service import embedding_service, build_wardrobe_embedding_text
from apps.api.services.r2_storage import get_r2_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


# ========== 常量配置 ==========
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "data" / "uploads" / "wardrobe"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# ========== 请求模型 ==========

class AITaggingPreview(BaseModel):
    """AI 打标预览请求"""
    description: str = Field(..., min_length=2, max_length=500, description="衣物描述")
    image_url: Optional[str] = Field(None, description="图片 URL（可选）")


# ========== API 端点 ==========

@router.post("/upload-image")
async def upload_wardrobe_image(
    file: UploadFile = File(..., description="衣物图片"),
    current_user: dict = Depends(get_current_user)
):
    """
    上传衣物图片到 Cloudflare R2
    
    **源码位置**: `apps/api/routers/wardrobe.py:upload_wardrobe_image()`
    
    **核心逻辑**:
    1. 验证文件类型（JPG/PNG/WebP）和大小（≤5MB）
    2. 生成唯一文件名：{user_id}_{timestamp}_{uuid}_{filename}
    3. 上传到 R2 存储桶：uploads/wardrobe/{user_id}/
    4. 返回完整的公共 URL
    
    **用途**: 用户添加衣物时上传图片，用于推荐结果展示
    
    **响应示例**:
    ```json
    {
      "image_url": "https://pub-xxx.r2.dev/uploads/wardrobe/1/abc123_shirt.jpg"
    }
    ```
    """
    try:
        user_id = current_user["id"]
        
        # 1. 验证文件类型
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的图片格式，仅支持 JPG/PNG/WebP"
            )
        
        # 2. 验证文件大小
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片大小超过限制（最大 5MB）"
            )
        
        # 3. 生成唯一文件名
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        original_filename = file.filename or "image.jpg"
        safe_filename = f"{user_id}_{timestamp}_{unique_id}_{original_filename}"
        
        # 4. 上传到 R2
        r2_service = get_r2_service()
        from io import BytesIO
        
        image_url = r2_service.upload_file(
            file_data=BytesIO(content),
            file_name=safe_filename,
            folder="uploads/wardrobe",
            content_type=file.content_type
        )
        
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="图片上传失败，请稍后重试"
            )
        
        logger.info(f"用户 {user_id} 上传图片成功：{image_url}")
        
        return {"image_url": image_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片上传失败：{e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败：{str(e)}"
        )


@router.post("/items/preview-tagging", response_model=AITaggingResult)
async def preview_tagging(
    request: AITaggingPreview,
    user: dict = Depends(get_current_user)
):
    """
    预览 AI 打标结果
    
    **源码位置**: `apps/api/routers/wardrobe.py:preview_tagging()` (第43行起)
    
    **核心逻辑**:
    1. 接收衣物描述和图片URL
    2. 调用 `ai_tagging_service.analyze_item()` 进行AI分析
    3. 返回五行属性、颜色、材质、适用季节等标签
    
    **用途**: 用户添加衣物前可先预览 AI 分析结果，不满意可手动修正
    
    **依赖**: `apps/api/services/ai_tagging_service.py:analyze_item()`
    """
    try:
        result = await ai_tagging_service.analyze_item(
            description=request.description,
            image_url=request.image_url
        )
        
        # 构建 AITaggingResult 响应
        return AITaggingResult(
            primary_element=result.get("primary_element", "金"),
            secondary_element=result.get("secondary_element"),
            color=result.get("color", "未知"),
            color_element=result.get("color_element"),
            material=result.get("material"),
            material_element=result.get("material_element"),
            style=result.get("style"),
            shape=result.get("shape"),
            details=result.get("details", []),
            energy_intensity=result.get("energy_intensity"),
            category=result.get("category"),
            season=result.get("season", []),
            tags=result.get("tags", []),
            confidence=result.get("confidence", 0.0),
            applicable_weather=result.get("applicable_weather", []),
            applicable_seasons=result.get("applicable_seasons", []),
            temperature_range=result.get("temperature_range"),
            functionality=result.get("functionality", []),
            thickness_level=result.get("thickness_level"),
        )
    except Exception as e:
        logger.error(f"AI打标预览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI打标失败: {str(e)}"
        )


@router.post("/items", response_model=WardrobeItemResponse)
async def add_wardrobe_item(
    request: WardrobeItemCreate,
    user: dict = Depends(get_current_user)
):
    """
    添加衣物到个人衣橱
    
    **源码位置**: `apps/api/routers/wardrobe.py:add_wardrobe_item()` (第92行起)
    
    **核心逻辑**:
    1. AI 自动打标（如果未手动指定五行）
    2. 调用 `generate_embedding()` 生成向量
    3. 存入数据库（wardrobe_items 表）
    
    **依赖**:
    - `ai_tagging_service.analyze_item()` - AI 打标
    - `generate_embedding()` - 向量生成
    """
    user_id = user.get("id")  # 修复：使用正确的字段名
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    try:
        # 1. AI 打标（如果用户未指定主五行）
        ai_result = None
        if not request.primary_element:
            ai_result = await ai_tagging_service.analyze_item(
                description=request.description or request.name,
                image_url=request.image_url
            )
        
        # 2. 确定最终值（用户指定优先，AI 结果其次）
        primary_element = request.primary_element or (ai_result.get("primary_element") if ai_result else "金")
        secondary_element = request.secondary_element or (ai_result.get("secondary_element") if ai_result else None)
        name = request.name or (ai_result.get("suggested_name") if ai_result else request.description)
        category = request.category or (ai_result.get("category") if ai_result else None)
        
        # 3. 生成 Embedding（使用与 items 表一致的文本构建逻辑）
        embedding_text = build_wardrobe_embedding_text(
            name=name,
            category=category,
            ai_result=ai_result,
            description=request.description
        )
        embedding = embedding_service.generate_embedding(embedding_text)
        
        # 4. 存入数据库
        is_custom = request.item_code is None
        
        query = """
            INSERT INTO user_wardrobe (
                user_id, item_code, name, category, image_url,
                primary_element, secondary_element, attributes_detail,
                is_custom, embedding,
                gender, applicable_weather, applicable_seasons,
                temperature_range, functionality, thickness_level, energy_intensity
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, item_code, name, category, image_url,
                      primary_element, secondary_element, attributes_detail,
                      is_custom, is_active, wear_count, last_worn_date,
                      is_favorite, notes, created_at, updated_at,
                      gender, applicable_weather, applicable_seasons,
                      temperature_range, functionality, thickness_level, energy_intensity
        """
        
        # 从 AI 结果或请求中获取天气/场景信息
        applicable_weather = request.applicable_weather or (ai_result.get("applicable_weather", []) if ai_result else [])
        applicable_seasons = request.applicable_seasons or (ai_result.get("applicable_seasons", []) if ai_result else [])
        temperature_range = request.temperature_range or (ai_result.get("temperature_range") if ai_result else None)
        functionality = request.functionality or (ai_result.get("functionality", []) if ai_result else [])
        thickness_level = request.thickness_level or (ai_result.get("thickness_level") if ai_result else None)
        energy_intensity = request.energy_intensity or (ai_result.get("energy_intensity") if ai_result else None)
        
        # 构建 attributes_detail（与 items 表结构对齐）
        attributes_detail = {
            # 颜色信息
            "颜色": {
                "名称": ai_result.get("color") if ai_result else None,
                "主五行": ai_result.get("color_element") if ai_result else None,
                "能量强度": ai_result.get("energy_intensity") if ai_result else None,
            },
            # 面料信息
            "面料": {
                "名称": ai_result.get("material") if ai_result else None,
                "主五行": ai_result.get("material_element") if ai_result else None,
            },
            # 款式信息
            "款式": {
                "形状": ai_result.get("shape") if ai_result else None,
                "细节": ai_result.get("details", []) if ai_result else [],
                "风格": ai_result.get("style") if ai_result else None,
            },
            # 其他信息
            "season": ai_result.get("season", []) if ai_result else [],
            "tags": ai_result.get("tags", []) if ai_result else [],
            "ai_confidence": ai_result.get("confidence") if ai_result else None,
        }
        
        import json
        from psycopg2 import sql
        
        params = [
            user_id,
            request.item_code,
            name,
            request.category,
            request.image_url,
            primary_element,
            secondary_element,
            json.dumps(attributes_detail),
            is_custom,
            embedding,  # 向量嵌入
            request.gender,
            json.dumps(applicable_weather),
            json.dumps(applicable_seasons),
            json.dumps(temperature_range) if temperature_range else None,
            json.dumps(functionality),
            thickness_level,
            request.energy_intensity,
        ]
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                conn.commit()
        
        return WardrobeItemResponse(**dict(row))
        
    except Exception as e:
        logger.error(f"添加衣物失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加衣物失败: {str(e)}"
        )


@router.get("/items", response_model=WardrobeItemListResponse)
async def list_wardrobe_items(
    category: Optional[str] = Query(None, description="分类筛选"),
    element: Optional[str] = Query(None, description="五行筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    user: dict = Depends(get_current_user)
):
    """
    获取用户衣橱列表
    
    **源码位置**: `apps/api/routers/wardrobe.py:list_wardrobe_items()` (第211行起)
    
    **核心逻辑**: 查询数据库，支持按分类、五行筛选，分页返回
    
    **筛选参数**:
    - `category`: 分类筛选（上衣、裤子、裙子等）
    - `element`: 五行筛选（金、木、水、火、土）
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    offset = (page - 1) * limit
    
    # 构建查询
    base_query = """
        SELECT id, user_id, item_code, name, category, image_url,
               primary_element, secondary_element, attributes_detail,
               is_custom, is_active, wear_count, last_worn_date,
               is_favorite, notes, created_at, updated_at,
               gender, applicable_weather, applicable_seasons,
               temperature_range, functionality, thickness_level, energy_intensity
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
    """
    params = [user_id]
    
    if category:
        base_query += " AND category = %s"
        params.append(category)
    
    if element:
        base_query += " AND primary_element = %s"
        params.append(element)
    
    # 获取列表
    list_query = base_query + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 获取列表
            cur.execute(list_query, params)
            rows = cur.fetchall()
            
            # 获取总数
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) sub"
            cur.execute(count_query, params[:-2])  # 排除 limit 和 offset
            total = cur.fetchone()['total']
            
            # 获取五行统计
            stats_query = """
                SELECT primary_element, COUNT(*) as count
                FROM user_wardrobe
                WHERE user_id = %s AND is_active = TRUE
                GROUP BY primary_element
            """
            cur.execute(stats_query, [user_id])
            stats_rows = cur.fetchall()
    
    items = [WardrobeItemResponse(**dict(row)) for row in rows]
    element_stats = {row['primary_element']: row['count'] for row in stats_rows}
    
    return WardrobeItemListResponse(
        items=items,
        total=total,
        element_stats=element_stats
    )


@router.get("/items/{item_id}", response_model=WardrobeItemResponse)
async def get_wardrobe_item(
    item_id: int,
    user: dict = Depends(get_current_user)
):
    """获取单个衣物详情"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    query = """
        SELECT id, user_id, item_code, name, category, image_url,
               primary_element, secondary_element, attributes_detail,
               is_custom, is_active, wear_count, last_worn_date,
               is_favorite, notes, created_at, updated_at,
               gender, applicable_weather, applicable_seasons,
               temperature_range, functionality, thickness_level, energy_intensity
        FROM user_wardrobe
        WHERE id = %s AND user_id = %s AND is_active = TRUE
    """
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [item_id, user_id])
            row = cur.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="衣物不存在或无权访问"
        )
    
    return WardrobeItemResponse(**dict(row))


@router.patch("/items/{item_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    item_id: int,
    request: WardrobeItemUpdate,
    user: dict = Depends(get_current_user)
):
    """
    更新衣物信息
    
    用于修正 AI 识别错误
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    # 构建动态更新
    updates = []
    params = []
    
    if request.name is not None:
        updates.append("name = %s")
        params.append(request.name)
    if request.category is not None:
        updates.append("category = %s")
        params.append(request.category)
    if request.primary_element is not None:
        updates.append("primary_element = %s")
        params.append(request.primary_element)
    if request.secondary_element is not None:
        updates.append("secondary_element = %s")
        params.append(request.secondary_element)
    if request.attributes_detail is not None:
        updates.append("attributes_detail = %s")
        params.append(json.dumps(request.attributes_detail))
    if request.image_url is not None:
        updates.append("image_url = %s")
        params.append(request.image_url)
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有需要更新的字段"
        )
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.extend([item_id, user_id])
    
    query = f"""
        UPDATE user_wardrobe
        SET {', '.join(updates)}
        WHERE id = %s AND user_id = %s AND is_active = TRUE
        RETURNING id, user_id, item_code, name, category, image_url,
                  primary_element, secondary_element, attributes_detail,
                  is_custom, is_active, wear_count, last_worn_date,
                  is_favorite, notes, created_at, updated_at,
                  gender, applicable_weather, applicable_seasons,
                  temperature_range, functionality, thickness_level, energy_intensity
    """
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="衣物不存在或无权访问"
        )
    
    return WardrobeItemResponse(**dict(row))


@router.delete("/items/{item_id}")
async def delete_wardrobe_item(
    item_id: int,
    user: dict = Depends(get_current_user)
):
    """删除衣物（软删除）"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    query = """
        UPDATE user_wardrobe
        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND user_id = %s AND is_active = TRUE
    """
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [item_id, user_id])
            affected = cur.rowcount
            conn.commit()
    
    if affected == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="衣物不存在或无权访问"
        )
    
    return {"message": "删除成功"}


@router.get("/stats")
async def get_wardrobe_stats(
    user: dict = Depends(get_current_user)
):
    """获取衣橱统计信息"""
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    query = """
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_custom = TRUE) as custom_count,
            COUNT(*) FILTER (WHERE is_custom = FALSE) as referenced_count,
            json_object_agg(primary_element, element_count) as element_stats
        FROM (
            SELECT 
                primary_element,
                COUNT(*) as element_count,
                is_custom
            FROM user_wardrobe
            WHERE user_id = %s AND is_active = TRUE
            GROUP BY primary_element, is_custom
        ) sub
        CROSS JOIN (SELECT 1) dummy
        GROUP BY element_stats
    """
    
    # 简化查询
    stats_query = """
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_custom = TRUE) as custom_count,
            COUNT(*) FILTER (WHERE is_custom = FALSE) as referenced_count
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
    """
    
    element_query = """
        SELECT primary_element, COUNT(*) as count
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
        GROUP BY primary_element
    """
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(stats_query, [user_id])
            stats = cur.fetchone()
            
            cur.execute(element_query, [user_id])
            element_rows = cur.fetchall()
    
    element_stats = {row['primary_element']: row['count'] for row in element_rows}
    
    return {
        "total": stats['total'],
        "custom_count": stats['custom_count'],
        "referenced_count": stats['referenced_count'],
        "element_stats": element_stats
    }


# ========== 反馈接口 ==========

@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    request: FeedbackCreate,
    user: dict = Depends(get_current_user)
):
    """
    创建推荐反馈
    
    用户对推荐结果点赞/点踩
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    query = """
        INSERT INTO feedback_logs (
            user_id, session_id, item_id, item_code, item_source, action, feedback_reason
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, user_id, action, created_at
    """
    
    params = [
        user_id,
        request.session_id,
        request.item_id,
        request.item_code,
        request.item_source,
        request.action,
        request.feedback_reason
    ]
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()
    
    return FeedbackResponse(**dict(row))
