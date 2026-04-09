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
from apps.api.routers import recommend, bazi, weather, auth, wardrobe, poster

# 初始化日志系统
init_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("应用启动中...")
    
    # 启动时初始化连接池（添加重试机制）
    max_retries = 5
    retry_delay = 2  # 秒
    
    for attempt in range(max_retries):
        try:
            DatabasePool.init_pool()
            
            # 验证数据库连接
            if check_db_health():
                logger.info("数据库连接成功")
                break
            else:
                raise Exception("数据库连接检查失败")
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                logger.info(f"等待 {retry_delay} 秒后重试...")
                import asyncio
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"数据库连接失败，已达到最大重试次数: {e}")
                raise
    
    # 注意：Embedding 模型已改用 DashScope API，无需预热
    # 之前加载本地 BGE-M3 模型会占用大量内存（~400MB），导致 OOM
    
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
app.include_router(poster.router, tags=["poster"])

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
