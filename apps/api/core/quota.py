"""
LLM 日配额模块

按身份（登录用户 ID 优先，游客按 IP）限制每日 LLM 调用次数，
防止推荐接口被刷导致 DashScope 费用失控。

计数复用 rate_limit.incr_counter（Redis 优先，内存兜底），
key 带日期后缀，自然按天滚动。
"""

import logging
from datetime import datetime

from fastapi import HTTPException, Request, status

from apps.api.core.config import settings
from apps.api.core.rate_limit import get_client_ip, incr_counter
from apps.api.core.security import decode_access_token

logger = logging.getLogger(__name__)

# 计数 key 保留略大于一天的 TTL，跨天后 key 变化自动重新计数
_QUOTA_TTL_SECONDS = 86400 + 3600


def _resolve_identity(request: Request) -> str:
    """
    解析配额主体：优先登录用户 ID，游客回退到客户端 IP

    注意：此处仅解码 JWT 不查库（配额检查在热路径上，避免额外 DB 往返）；
    token 无效时按游客处理，不阻断请求。
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub") or payload.get("user_id")
            if user_id is not None:
                return f"u:{user_id}"
    return f"ip:{get_client_ip(request)}"


async def llm_daily_quota(request: Request) -> None:
    """
    FastAPI 依赖：LLM 日配额检查（超限返回 429）

    Usage:
        @router.post("/recommend/stream", dependencies=[Depends(llm_daily_quota)])
    """
    if not settings.llm_quota_enabled:
        return

    identity = _resolve_identity(request)
    today = datetime.now().strftime("%Y%m%d")
    key = f"llmquota:{identity}:{today}"

    count, _ = await incr_counter(key, _QUOTA_TTL_SECONDS)
    if count > settings.llm_daily_quota:
        logger.warning(f"LLM 日配额超限: {identity} 今日第 {count} 次请求")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日 AI 推荐次数已用完（每日 {settings.llm_daily_quota} 次），请明天再来",
        )
