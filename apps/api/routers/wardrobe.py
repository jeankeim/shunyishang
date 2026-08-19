"""
衣橱管理路由模块
提供衣橱 CRUD 和 AI 打标接口
"""

import logging
import json
import os
import re
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
    BatchRecognizeRequest,
    BatchRecognizeResponse,
    BatchRecognizeResultItem,
    BatchWuxingAnalysisRequest,
    BatchWuxingAnalysisResponse,
    BatchWuxingResultItem,
    BatchAddItem,
    BatchAddItemsRequest,
    BatchAddItemsResponse,
    BatchAddFailedItem,
)
from apps.api.services.ai_tagging_service import ai_tagging_service
from apps.api.services.llm_usage_service import log_llm_usage
from apps.api.services.embedding_service import embedding_service, build_wardrobe_embedding_text
from apps.api.services.storage import get_storage_service
from apps.api.services.wuxing_analysis_service import wuxing_analysis_service
from packages.ai_agents.wardrobe_tagging import run_batch_tagging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


# ========== 常量配置 ==========
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "data" / "uploads" / "wardrobe"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_BATCH_SIZE = 5  # 批量上传每批上限


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
    上传衣物图片到对象存储（OSS/R2）
    
    **源码位置**: `apps/api/routers/wardrobe.py:upload_wardrobe_image()`
    
    **核心逻辑**:
    1. 验证文件类型（JPG/PNG/WebP）和大小（≤5MB）
    2. 生成唯一文件名：{user_id}_{timestamp}_{uuid}_{filename}
    3. 上传到对象存储：uploads/wardrobe/{user_id}/
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
        
        # 3. 生成唯一文件名（对象名仅保留 ASCII 安全字符：
        #    中文/空格等非 ASCII 字符会进入 R2 URL，导致下游（如 AI 视觉模型下载图片）拉取失败）
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        original_filename = file.filename or "image.jpg"
        # 拆出扩展名并校验，非法则按 content_type 兜底
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }.get(file.content_type, ".jpg")
        # 文件名主体：仅保留 ASCII 字母数字/下划线/连字符，其余（中文、空格等）替换为下划线
        stem = os.path.splitext(original_filename)[0]
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")[:40] or "image"
        safe_filename = f"{user_id}_{timestamp}_{unique_id}_{safe_stem}{ext}"
        
        # 4. 上传到对象存储
        storage_service = get_storage_service()
        from io import BytesIO
        
        image_url = storage_service.upload_file(
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
        # 大模型调用明细埋点（AI 打标预览）
        log_llm_usage(
            user.get("id"), "wardrobe_ai", request.description,
            f"AI 打标：主五行 {result.get('primary_element', '')}",
            usage=result.pop("_llm_usage", None),
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


# ========== 入库公共逻辑 ==========

_WARDROBE_RETURNING_FIELDS = """id, user_id, item_code, name, category, image_url,
               primary_element, secondary_element, attributes_detail,
               is_custom, is_active, wear_count, last_worn_date,
               is_favorite, notes, created_at, updated_at,
               gender, applicable_weather, applicable_seasons,
               temperature_range, functionality, thickness_level, energy_intensity"""


def _insert_wardrobe_item(cur, user_id: int, data: dict) -> dict:
    """衣橱入库 INSERT 公共逻辑（单件添加与批量添加共用）

    Args:
        cur: 数据库游标（调用方负责 commit）
        user_id: 用户 ID
        data: 必含 item_code/name/category/image_url/primary_element/secondary_element/
              attributes_detail(dict)/is_custom/embedding/gender/applicable_weather/
              applicable_seasons/temperature_range/functionality/thickness_level/
              energy_intensity/style

    Returns:
        dict: RETURNING 行数据
    """
    query = f"""
        INSERT INTO user_wardrobe (
            user_id, item_code, name, category, image_url,
            primary_element, secondary_element, attributes_detail,
            is_custom, embedding,
            gender, applicable_weather, applicable_seasons,
            temperature_range, functionality, thickness_level, energy_intensity,
            style
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {_WARDROBE_RETURNING_FIELDS}
    """

    params = [
        user_id,
        data.get("item_code"),
        data["name"],
        data.get("category"),
        data.get("image_url"),
        data.get("primary_element"),
        data.get("secondary_element"),
        json.dumps(data.get("attributes_detail") or {}),
        data.get("is_custom", True),
        data.get("embedding"),
        data.get("gender"),
        json.dumps(data.get("applicable_weather") or []),
        json.dumps(data.get("applicable_seasons") or []),
        json.dumps(data["temperature_range"]) if data.get("temperature_range") else None,
        json.dumps(data.get("functionality") or []),
        data.get("thickness_level"),
        data.get("energy_intensity"),
        data.get("style"),
    ]

    cur.execute(query, params)
    row = cur.fetchone()
    return dict(row)


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
            if ai_result:
                # 大模型调用明细埋点（添加衣物 AI 打标）
                log_llm_usage(
                    user_id, "wardrobe_ai", request.description or request.name,
                    f"AI 打标：主五行 {ai_result.get('primary_element', '')}",
                    usage=ai_result.pop("_llm_usage", None),
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
        
        # 从 AI 结果或请求中获取天气/场景信息
        applicable_weather = request.applicable_weather or (ai_result.get("applicable_weather", []) if ai_result else [])
        applicable_seasons = request.applicable_seasons or (ai_result.get("applicable_seasons", []) if ai_result else [])
        temperature_range = request.temperature_range or (ai_result.get("temperature_range") if ai_result else None)
        functionality = request.functionality or (ai_result.get("functionality", []) if ai_result else [])
        thickness_level = request.thickness_level or (ai_result.get("thickness_level") if ai_result else None)
        energy_intensity = request.energy_intensity or (ai_result.get("energy_intensity") if ai_result else None)
        style = ai_result.get("style") if ai_result else None
        
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
        
        # 4. 存入数据库（与批量添加共用 INSERT 逻辑）
        insert_data = {
            "item_code": request.item_code,
            "name": name,
            "category": request.category,
            "image_url": request.image_url,
            "primary_element": primary_element,
            "secondary_element": secondary_element,
            "attributes_detail": attributes_detail,
            "is_custom": request.item_code is None,
            "embedding": embedding,
            "gender": request.gender,
            "applicable_weather": applicable_weather,
            "applicable_seasons": applicable_seasons,
            "temperature_range": temperature_range,
            "functionality": functionality,
            "thickness_level": thickness_level,
            "energy_intensity": request.energy_intensity,
            "style": style,
        }
        
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                row = _insert_wardrobe_item(cur, user_id, insert_data)
                conn.commit()
        
        return WardrobeItemResponse(**row)
        
    except Exception as e:
        logger.error(f"添加衣物失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加衣物失败: {str(e)}"
        )


# ========== 批量上传 ==========


def _get_user_xiyong(user_id: int):
    """读取用户喜用神与忌讳五行

    Returns:
        (xiyong_elements, avoid_elements)，查询失败或无八字资料时返回空列表。
        喜用神仅用于只读比对，严禁篡改。
    """
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT xiyong_elements, bazi FROM users WHERE id = %s", [user_id])
                row = cur.fetchone()
        if not row:
            return [], []
        xiyong = row[0] if isinstance(row[0], list) else []
        bazi = row[1] if isinstance(row[1], dict) else {}
        avoid = bazi.get("avoid_elements") if isinstance(bazi.get("avoid_elements"), list) else []
        return xiyong, avoid
    except Exception as e:
        logger.warning(f"[批量上传] 读取用户喜用神失败: {e}")
        return [], []


@router.post("/batch/recognize", response_model=BatchRecognizeResponse)
async def batch_recognize_items(
    request: BatchRecognizeRequest,
    user: dict = Depends(get_current_user)
):
    """
    批量识别衣物图片（第一阶段：基础属性）

    **核心逻辑**:
    1. 校验每批上限 5 件
    2. 调用 LangGraph 工作流 `run_batch_tagging`：VL 并行识别 + 词表归一化
    3. 单件失败不阻断批次，该件置 needs_manual_review=true 由前端引导手动填写
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")

    if len(request.items) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"每批最多识别 {MAX_BATCH_SIZE} 件"
        )

    try:
        final_state = await run_batch_tagging([it.image_url for it in request.items])
    except Exception as e:
        logger.error(f"批量识别工作流异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="批量识别服务暂时不可用，请稍后重试"
        )

    # 大模型调用明细埋点（批量识别，用量已在工作流内汇总）
    log_llm_usage(
        user_id, "wardrobe_batch_recognize",
        f"批量识别 {len(request.items)} 件衣物",
        final_state.get("error") or "批量识别完成",
        usage=final_state.get("llm_token_usage"),
    )

    results_state = final_state.get("results") or []
    if not results_state:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=final_state.get("error") or "识别失败，请稍后重试"
        )

    results = []
    for i, item_in in enumerate(request.items):
        r = results_state[i] if i < len(results_state) else {}
        results.append(BatchRecognizeResultItem(
            index=item_in.index,
            image_url=item_in.image_url,
            suggested_name=r.get("suggested_name") or "",
            description=r.get("description") or "",
            category=r.get("category"),
            gender=r.get("gender"),
            applicable_seasons=r.get("applicable_seasons") or [],
            functionality=r.get("functionality") or [],
            color=r.get("color") or "",
            material=r.get("material") or "",
            style=r.get("style"),
            confidence=r.get("confidence") or 0.0,
            needs_manual_review=bool(r.get("needs_manual_review") or r.get("error")),
            error=r.get("error"),
        ))

    logger.info(f"用户 {user_id} 批量识别完成: {len(results)} 件")
    return BatchRecognizeResponse(results=results)


@router.post("/batch/wuxing-analysis", response_model=BatchWuxingAnalysisResponse)
async def batch_wuxing_analysis(
    request: BatchWuxingAnalysisRequest,
    user: dict = Depends(get_current_user)
):
    """
    五行与材质深度分析（第二阶段：规则引擎 + 喜用神比对）

    **核心逻辑**:
    1. 读取用户喜用神/忌讳五行（users 表，只读）
    2. 规则引擎基于 data/standards 映射表计算颜色/材质/风格五行与主五行
    3. 喜用神比对输出 xiyong_match 标签与建议文案（无 LLM 调用，确定性结果）
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")

    if len(request.items) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"每批最多分析 {MAX_BATCH_SIZE} 件"
        )

    xiyong, avoid = _get_user_xiyong(user_id)
    items = [it.model_dump() for it in request.items]
    analyses = wuxing_analysis_service.analyze_batch(items, xiyong, avoid)

    results = [
        BatchWuxingResultItem(index=item_in.index, **analysis)
        for item_in, analysis in zip(request.items, analyses)
    ]

    logger.info(f"用户 {user_id} 五行深度分析完成: {len(results)} 件, 喜用={xiyong or '无'}")
    return BatchWuxingAnalysisResponse(results=results, xiyong_elements=xiyong or [])


def _build_batch_item_data(item: BatchAddItem) -> dict:
    """将批量入库输入组装为 `_insert_wardrobe_item` 的 data（含 attributes_detail 与 Embedding）"""
    # attributes_detail 与单件添加的中文键结构对齐，追加命理适配键
    attributes_detail = {
        "颜色": {
            "名称": item.color,
            "主五行": item.color_element,
            "能量强度": item.energy_intensity,
        },
        "面料": {
            "名称": item.material,
            "主五行": item.material_element,
        },
        "款式": {
            "形状": item.shape,
            "细节": item.details,
            "风格": item.style,
        },
        "season": item.season,
        "tags": item.tags,
        "ai_confidence": item.confidence,
    }
    if item.xiyong_match:
        attributes_detail["命理适配"] = {
            "喜用匹配": item.xiyong_match,
            "建议": item.xiyong_advice,
        }

    # Embedding 生成（失败降级 NULL 向量，不阻断入库）
    embedding = None
    try:
        embedding_text = build_wardrobe_embedding_text(
            name=item.name,
            category=item.category,
            ai_result=None,
            description=item.description
        )
        embedding = embedding_service.generate_embedding(embedding_text)
    except Exception as e:
        logger.warning(f"[批量上传] Embedding 生成失败，以 NULL 向量入库: {e}")

    return {
        "item_code": None,
        "name": item.name,
        "category": item.category,
        "image_url": item.image_url,
        "primary_element": item.primary_element or "金",
        "secondary_element": item.secondary_element,
        "attributes_detail": attributes_detail,
        "is_custom": True,
        "embedding": embedding,
        "gender": item.gender,
        "applicable_weather": item.applicable_weather,
        "applicable_seasons": item.applicable_seasons,
        "temperature_range": item.temperature_range,
        "functionality": item.functionality,
        "thickness_level": item.thickness_level,
        "energy_intensity": item.energy_intensity,
        "style": item.style,
    }


@router.post("/batch/items", response_model=BatchAddItemsResponse)
async def batch_add_wardrobe_items(
    request: BatchAddItemsRequest,
    user: dict = Depends(get_current_user)
):
    """
    批量衣物入库（部分成功语义）

    逐件写入 user_wardrobe 表（与单件添加同一表结构），单件异常捕获后
    计入 failed，不中断同批其他件；成功项随响应返回供前端刷新列表。
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户未登录")

    if len(request.items) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"每批最多入库 {MAX_BATCH_SIZE} 件"
        )

    created = []
    failed = []

    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for idx, item in enumerate(request.items):
                    try:
                        row = _insert_wardrobe_item(cur, user_id, _build_batch_item_data(item))
                        created.append(WardrobeItemResponse(**row))
                    except Exception as e:
                        logger.error(f"[批量上传] 第 {idx} 件 ({item.name}) 入库失败: {e}")
                        failed.append(BatchAddFailedItem(index=idx, reason=str(e)))
                conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量入库事务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量入库失败：{str(e)}"
        )

    logger.info(f"[批量上传] 用户 {user_id} 入库完成: 成功 {len(created)} 件, 失败 {len(failed)} 件")
    return BatchAddItemsResponse(created=created, failed=failed)


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
    element_stats = {row['primary_element']: row['count'] for row in stats_rows if row['primary_element'] is not None}
    
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
    
    用户对推荐结果点赞/点踩，同时更新用户偏好学习
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

    # 偏好学习：根据反馈更新用户偏好
    try:
        from apps.api.services.preference_service import preference_service
        item_attrs = _get_item_attributes(request.item_id, request.item_code, request.item_source)
        if item_attrs:
            preference_service.update_preference(user_id, item_attrs, request.action)
    except Exception as e:
        logger.warning(f"[Feedback] 偏好学习失败: {e}")
    
    # 点踩时同步写入不喜欢物品表（硬性排除，后续推荐不再出现）
    if request.action == "dislike" and request.item_code:
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_disliked_items (user_id, item_code, reason)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, item_code) DO NOTHING
                    """, [user_id, request.item_code, request.feedback_reason])
                    conn.commit()
            logger.info(f"[Feedback] 不喜欢物品已记录: user={user_id} item={request.item_code}")
        except Exception as e:
            logger.warning(f"[Feedback] 不喜欢物品记录失败: {e}")
    
    return FeedbackResponse(**dict(row))


@router.delete("/feedback")
async def cancel_feedback(
    item_code: str = Query(..., description="物品编码"),
    item_id: Optional[int] = Query(None, description="物品ID"),
    user: dict = Depends(get_current_user)
):
    """
    撤销推荐反馈
    
    用户可以撤销之前的点赞/点踩操作，同时移除不喜欢物品记录
    """
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未登录"
        )
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            # 删除反馈记录（取最近一条）
            cur.execute("""
                DELETE FROM feedback_logs
                WHERE id = (
                    SELECT id FROM feedback_logs
                    WHERE user_id = %s AND (item_code = %s OR item_id = %s)
                    ORDER BY created_at DESC LIMIT 1
                )
            """, [user_id, item_code, item_id])
            
            # 同时移除不喜欢物品记录（如果是点踩撤销）
            if item_code:
                cur.execute("""
                    DELETE FROM user_disliked_items
                    WHERE user_id = %s AND item_code = %s
                """, [user_id, item_code])
            
            conn.commit()
    
    logger.info(f"[Feedback] 反馈已撤销: user={user_id} item={item_code or item_id}")
    return {"success": True, "message": "反馈已撤销"}


def _get_item_attributes(item_id, item_code, item_source) -> dict:
    """获取物品属性用于偏好学习（6维）"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if item_source == 'wardrobe' and item_id:
                    # 衣橱物品存在 user_wardrobe 表（items 表没有 id 列）
                    cur.execute(
                        """SELECT name, category, primary_element, attributes_detail,
                                  color, style, material, thickness_level
                           FROM user_wardrobe WHERE id = %s""",
                        [item_id]
                    )
                elif item_code:
                    cur.execute(
                        """SELECT name, category, primary_element, attributes_detail,
                                  color, style, material, thickness_level
                           FROM items WHERE item_code = %s""",
                        [item_code]
                    )
                else:
                    return {}
                row = cur.fetchone()
        
        if not row:
            return {}
        
        attrs = dict(row)
        # 从 attributes_detail 提取补充属性
        detail = attrs.get('attributes_detail', {})
        if isinstance(detail, str):
            detail = json.loads(detail)
        
        color = attrs.get('color') or (
            detail.get('颜色', {}).get('主色', '') if isinstance(detail.get('颜色'), dict) else ''
        )
        
        return {
            'color': color,
            'primary_element': attrs.get('primary_element', ''),
            'category': attrs.get('category', ''),
            'style': attrs.get('style') or detail.get('style', ''),
            'material': attrs.get('material') or detail.get('material', ''),
            'thickness_level': attrs.get('thickness_level') or detail.get('thickness_level', ''),
        }
    except Exception as e:
        logger.debug(f"[Feedback] 获取物品属性失败: {e}")
        return {}


# ========== 用户行为追踪 ==========

class BehaviorRequest(BaseModel):
    """用户行为上报请求"""
    user_id: Optional[int] = None
    item_id: str
    action: str = Field(..., description="行为类型: view/click/expand/image_click/dwell")
    item_source: str = Field('public', description="物品来源: public/wardrobe")
    dwell_duration: Optional[int] = Field(None, description="停留时长（秒）")
    session_id: Optional[str] = None


@router.post("/behavior")
async def report_behavior(request: BehaviorRequest):
    """记录用户行为（隐性反馈）"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO user_behaviors
                       (user_id, item_id, item_source, action, dwell_duration, session_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    [
                        request.user_id,
                        request.item_id,
                        request.item_source,
                        request.action,
                        request.dwell_duration,
                        request.session_id,
                    ],
                )
                conn.commit()
    except Exception as e:
        # 行为追踪失败不影响用户体验，静默处理
        logger.debug(f"[Behavior] 记录失败: {e}")

    return {"status": "ok"}


# ========== 用户偏好可视化 ==========

# 6维偏好维度的中文标签与图标
PREFERENCE_DIMENSIONS = {
    "color": {"label": "颜色", "icon": "🎨"},
    "element": {"label": "五行", "icon": "☯️"},
    "category": {"label": "品类", "icon": "👔"},
    "style": {"label": "风格", "icon": "✨"},
    "material": {"label": "材质", "icon": "🧵"},
    "thickness": {"label": "厚度", "icon": "🌡️"},
}


@router.get("/preference-summary", summary="获取用户偏好画像")
async def get_preference_summary(
    user: dict = Depends(get_current_user),
):
    """
    获取用户6维偏好画像摘要，供前端雷达图/偏好面板展示。

    返回结构：
    - dimensions: 6个维度的摘要（维度名、标签、偏好度分数、top3偏好项）
    - overall_score: 总体偏好学习深度（0~1，越高表示系统越了解用户）
    - feedback_count: 总反馈次数
    """
    user_id = user.get("id") or user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    from apps.api.services.preference_service import preference_service

    try:
        prefs = preference_service.get_user_preferences(user_id)
    except Exception as e:
        logger.warning(f"[Preference] 获取偏好失败: {e}")
        prefs = {}

    dimensions = []
    total_feedback = 0
    dimension_scores = []

    for dim_key, meta in PREFERENCE_DIMENSIONS.items():
        dim_data = prefs.get(dim_key, {})
        if not dim_data:
            dimensions.append({
                "key": dim_key,
                "label": meta["label"],
                "icon": meta["icon"],
                "score": 0.0,
                "top_items": [],
                "has_data": False,
            })
            dimension_scores.append(0.0)
            continue

        # 按权重绝对值排序取 top3
        sorted_items = sorted(dim_data.items(), key=lambda x: abs(x[1]), reverse=True)
        top_items = [
            {"name": k, "weight": round(v, 2), "direction": "喜欢" if v > 0 else "不喜欢"}
            for k, v in sorted_items[:3]
        ]

        # 维度偏好强度：top1 权重的归一化值（0~1）
        max_abs = abs(sorted_items[0][1]) if sorted_items else 0
        score = min(1.0, max_abs / 10.0)  # 权重10以上视为满分
        total_feedback += sum(1 for _ in dim_data)
        dimension_scores.append(score)

        dimensions.append({
            "key": dim_key,
            "label": meta["label"],
            "icon": meta["icon"],
            "score": round(score, 2),
            "top_items": top_items,
            "has_data": True,
        })

    # 总体了解度：6维分数的均值
    overall_score = round(sum(dimension_scores) / len(dimension_scores), 2) if dimension_scores else 0.0

    return {
        "dimensions": dimensions,
        "overall_score": overall_score,
        "feedback_count": total_feedback,
    }


# ========== 衣橱智能分析 ==========


@router.get("/analytics")
async def get_wardrobe_analytics(
    current_user: dict = Depends(get_current_user),
):
    """
    衣橱智能分析

    返回穿着频率分析、季节穿着模式、天气适应性、总体统计。
    数据基于 user_wardrobe + outfit_diaries + diary_outfit_items 综合分析。
    """
    from apps.api.services.wardrobe_analytics_service import get_wardrobe_analytics as _analytics

    user_id = current_user.get("id") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    # 优先从 Redis 缓存获取（分析数据变化不频繁，缓存 2 小时）
    try:
        from apps.api.core.config import settings as _settings
        if _settings.redis_enabled:
            from apps.api.core.cache import cache as redis_cache
            cache_key = f"wardrobe_analytics:{user_id}"
            cached = redis_cache.get_sync(cache_key)
            if cached:
                return cached
    except Exception:
        pass

    result = _analytics(int(user_id))

    # 写入缓存（2小时 TTL）
    try:
        if _settings.redis_enabled:
            redis_cache.set_sync(cache_key, result, ttl=7200)
    except Exception:
        pass

    return result


@router.get("/idle-items")
async def get_idle_items(
    current_user: dict = Depends(get_current_user),
):
    """
    获取长期闲置衣物 + 公益建议

    闲置条件（满足任一）:
    - last_worn_date 距今 > 180天
    - wear_count = 0 且 created_at 距今 > 90天

    返回闲置物品列表，每件附带温和的公益捐赠建议文案。
    """
    from apps.api.services.wardrobe_analytics_service import get_idle_items as _idle

    user_id = current_user.get("id") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="用户未登录")

    items = _idle(int(user_id))
    return {
        "idle_items": items,
        "total_count": len(items),
        "message": f"你有 {len(items)} 件衣物已经很久没穿了，考虑让它们找到新主人 🌱" if items else "你的衣橱管理得很好，没有长期闲置物品 ✨",
    }
