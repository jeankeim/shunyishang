"""
FastAPI 应用入口
"""

# --- 本地开发环境代理修复（必须在任何 HTTP 客户端创建前执行）---
# 背景：macOS 的系统代理（如 ClashX/Surge 等 VPN）会被 Python 的 httpx / requests
# 通过 urllib.request.getproxies() 自动识别并使用。但该代理无法访问国内
# DashScope（阿里云）端点，导致 SSL 握手超时、推荐/Embedding 接口全部失败。
# 这里将 aliyuncs.com 等域名加入 no_proxy 直连，同时保留系统代理供其他域名使用。
# 生产环境（Zeabur/Linux）无系统代理，getproxies() 返回空，此逻辑自动跳过，无副作用。
import os as _os
import urllib.request as _urlreq


def _configure_proxy_bypass() -> None:
    sys_proxies = _urlreq.getproxies()
    # 仅当检测到系统/环境代理时才处理
    if not (sys_proxies.get("http") or sys_proxies.get("https")):
        return
    # 将系统代理显式导出为环境变量，使 no_proxy 生效
    # （getproxies 优先读取环境变量；若仅存在系统配置，则 no_proxy 会被忽略）
    if sys_proxies.get("http"):
        _os.environ.setdefault("http_proxy", sys_proxies["http"])
        _os.environ.setdefault("HTTP_PROXY", sys_proxies["http"])
    if sys_proxies.get("https"):
        _os.environ.setdefault("https_proxy", sys_proxies["https"])
        _os.environ.setdefault("HTTPS_PROXY", sys_proxies["https"])
    bypass = "localhost,127.0.0.1,::1,aliyuncs.com,.aliyuncs.com"
    existing = _os.environ.get("no_proxy", "")
    merged = ",".join(dict.fromkeys(filter(None, existing.split(",") + bypass.split(","))))
    _os.environ["no_proxy"] = merged
    _os.environ["NO_PROXY"] = merged


_configure_proxy_bypass()

import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool, check_db_health
from apps.api.core.cache import cache
from apps.api.core.rate_limit import check_rate_limit, get_client_ip
from apps.api.core.logging_config import init_logging, get_logger
from apps.api.schemas.response import HealthResponse
from apps.api.routers import recommend, bazi, weather, auth, wardrobe, poster, diary, fortune, membership, travel, destiny, community, cultivation, content, tasks
from apps.api.routers.push import router as push_router, payment_router

# 初始化日志系统
init_logging()
logger = get_logger(__name__)

# 初始化 Sentry 错误监控（未配置 DSN 时跳过，开发环境零影响）
if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            # PIPL 合规：不上报用户 IP/Cookie 等默认 PII
            send_default_pii=False,
        )
        logger.info(f"Sentry 错误监控已启用 (env={settings.app_env})")
    except Exception as e:
        logger.warning(f"Sentry 初始化失败（不影响启动）: {e}")


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
    
    # 执行数据库自动迁移（补齐缺失的功能表，如 outfit_diaries、运势、报告等）
    try:
        from apps.api.core.migrations import run_migrations
        run_migrations()
    except Exception as e:
        logger.error(f"数据库迁移执行异常（不中断启动）: {e}")
    
    # 启动推送调度器
    from apps.api.services.push_scheduler import push_scheduler
    await push_scheduler.start()
    
    logger.info("应用启动完成")
    
    yield
    
    # 停止推送调度器
    await push_scheduler.stop()
    
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

# GZip 压缩中间件（压缩 >1KB 的响应，减少网络传输）
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.debug(f"{request.method} {request.url.path} → {response.status_code} ({duration:.3f}s)")
    return response


# 全局 API 限流中间件（每 IP 每分钟，健康检查/文档/静态资源豁免）
_RATE_LIMIT_EXEMPT_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json", "/static", "/uploads")


@app.middleware("http")
async def global_rate_limit(request: Request, call_next):
    """全局限流：超限返回 429 + Retry-After"""
    path = request.url.path
    if not path.startswith(_RATE_LIMIT_EXEMPT_PREFIXES):
        ip = get_client_ip(request)
        allowed, retry_after = await check_rate_limit(
            f"rl:global:{ip}", settings.rate_limit_global_per_minute, 60
        )
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试"},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


# 挂载路由
app.include_router(recommend.router, prefix="/api/v1", tags=["recommend"])
app.include_router(bazi.router, prefix="/api/v1/bazi", tags=["bazi"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["weather"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(wardrobe.router, prefix="/api/v1", tags=["wardrobe"])
app.include_router(poster.router, tags=["poster"])
app.include_router(diary.router, prefix="/api/v1", tags=["diary"])
app.include_router(fortune.router, prefix="/api/v1", tags=["fortune"])
# 个人备案版：禁用会员/支付路由，所有功能免费开放
# app.include_router(membership.router, prefix="/api/v1", tags=["membership"])
app.include_router(push_router, prefix="/api/v1", tags=["push"])
# app.include_router(payment_router, prefix="/api/v1", tags=["payments"])
app.include_router(travel.router, prefix="/api/v1", tags=["travel"])
app.include_router(destiny.router, prefix="/api/v1", tags=["destiny"])
# 广场社区路由临时关闭：个人备案合规改造，暂不提供用户发帖/评论等交互UGC功能
# app.include_router(community.router, prefix="/api/v1", tags=["community"])
app.include_router(cultivation.router, prefix="/api/v1", tags=["cultivation"])
app.include_router(content.router, prefix="/api/v1", tags=["content"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])

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
    
    检查服务状态、数据库连接和缓存连接
    """
    db_connected = check_db_health()
    cache_connected = cache.check_health()
    
    cache_status = "connected" if cache_connected else ("disabled" if not cache.enabled else "disconnected")
    
    if db_connected:
        return HealthResponse(
            status="ok",
            db="connected",
            cache=cache_status,
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
                cache=cache_status,
                env=settings.app_env
            ).model_dump()
        )


@app.get("/debug/config", tags=["debug"])
async def debug_config():
    """调试接口：检查配置加载状态（仅开发环境）"""
    if settings.app_env != "development":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only available in development")
    
    return {
        "app_env": settings.app_env,
        "dashscope_api_key": "已配置" if settings.dashscope_api_key else "未加载",
        "qwen_model": settings.qwen_model,
        "database_url": "已配置" if settings.database_url else "未配置",
        "cors_origins": settings.cors_origins_list
    }
