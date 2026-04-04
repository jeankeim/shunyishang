"""
FastAPI 应用入口
"""

import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool, check_db_health
from apps.api.core.logging_config import init_logging, get_logger
from apps.api.schemas.response import HealthResponse
from apps.api.routers import recommend, bazi, weather, auth, wardrobe

# 初始化日志系统
init_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("应用启动中...")
    
    # 启动时初始化连接池
    DatabasePool.init_pool()
    
    # 预热 Embedding 模型（避免首次请求延迟）
    logger.info("正在预热 Embedding 模型...")
    try:
        from packages.ai_agents.nodes import _get_embedding_model
        _get_embedding_model()
        logger.info("Embedding 模型预热完成")
    except Exception as e:
        logger.warning(f"Embedding 模型预热失败: {e}")
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时清理连接池
    DatabasePool.close_pool()
    logger.info("应用已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="WuXing AI Stylist API",
    description="五行时尚 AI 衣橱后端服务",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 挂载 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    return response


# 挂载路由
app.include_router(recommend.router, prefix="/api/v1", tags=["recommend"])
app.include_router(bazi.router, prefix="/api/v1/bazi", tags=["bazi"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["weather"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(wardrobe.router, prefix="/api/v1", tags=["wardrobe"])

# 挂载静态文件服务（图片上传）
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/", include_in_schema=False)
async def root():
    """根路径重定向到文档"""
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    健康检查接口
    
    检查服务状态和数据库连接
    """
    db_connected = check_db_health()
    
    if db_connected:
        return HealthResponse(
            status="ok",
            db="connected",
            env=settings.app_env
        )
    else:
        # 返回 503 状态码
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=HealthResponse(
                status="error",
                db="disconnected",
                env=settings.app_env
            ).model_dump()
        )
