"""
LLM 调用重试模块
使用 Tenacity 实现指数退避重试，提高服务稳定性
"""

import logging
from functools import wraps
from typing import Callable, Any, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
    before_sleep_log,
)

from apps.api.core.config import settings

logger = logging.getLogger(__name__)

# LLM 调用相关异常
class LLMServiceError(Exception):
    """LLM 服务异常基类"""
    pass


class LLMRateLimitError(LLMServiceError):
    """LLM 速率限制错误"""
    pass


class LLMTimeoutError(LLMServiceError):
    """LLM 超时错误"""
    pass


class LLMConnectionError(LLMServiceError):
    """LLM 连接错误"""
    pass


def get_llm_retry_config(max_attempts: int = 3, min_wait: float = 2.0, max_wait: float = 10.0):
    """
    获取 LLM 重试配置（指数退避）
    
    Args:
        max_attempts: 最大重试次数
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）
    
    Returns:
        tenacity 配置字典
    """
    return {
        "stop": stop_after_attempt(max_attempts),
        "wait": wait_exponential(min=min_wait, max=max_wait, multiplier=2),
        "retry": retry_if_exception_type((LLMRateLimitError, LLMConnectionError, TimeoutError)),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,
    }


# LLM 调用重试装饰器工厂
def llm_retry(
    max_attempts: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 10.0,
    fallback: Optional[Any] = None
):
    """
    LLM 调用重试装饰器
    
    使用指数退避策略，自动重试失败的 LLM 调用。
    
    Args:
        max_attempts: 最大重试次数（默认3次：1次原始 + 2次重试）
        min_wait: 最小等待时间（秒）
        max_wait: 最大等待时间（秒）
        fallback: 重试失败后的降级返回值
    
    Example:
        @llm_retry(max_attempts=3)
        def call_llm():
            return openai.ChatCompletion.create(...)
    """
    def decorator(func: Callable) -> Callable:
        # 基础重试装饰器
        base_retry = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(min=min_wait, max=max_wait, multiplier=2),
            retry=retry_if_exception_type((LLMRateLimitError, LLMConnectionError, TimeoutError, Exception)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=False,  # 我们自己处理异常
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return base_retry(func)(*args, **kwargs)
            except RetryError as e:
                logger.error(f"[LLM Retry] 重试 {max_attempts} 次后仍然失败: {e.last_attempt.exception()}")
                if fallback is not None:
                    return fallback
                raise LLMServiceError(f"LLM 调用失败: {e.last_attempt.exception()}")
            except Exception as e:
                logger.error(f"[LLM Retry] 非重试异常: {e}")
                if fallback is not None:
                    return fallback
                raise
        
        return wrapper
    return decorator


# 流式 LLM 调用重试（用于 SSE）
def llm_stream_with_retry(
    llm_call_func: Callable,
    max_attempts: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 10.0
):
    """
    流式 LLM 调用带重试
    
    Args:
        llm_call_func: 返回生成器的 LLM 调用函数
        max_attempts: 最大重试次数
        min_wait: 最小等待时间
        max_wait: 最大等待时间
    
    Yields:
        流式响应内容
    """
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            for chunk in llm_call_func():
                yield chunk
            return  # 成功完成
        except (LLMRateLimitError, LLMConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < max_attempts:
                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                logger.warning(
                    f"[LLM Retry] 第 {attempt}/{max_attempts} 次尝试失败，"
                    f"等待 {wait_time:.1f} 秒后重试: {e}"
                )
                import time
                time.sleep(wait_time)
            continue
        except Exception as e:
            last_error = e
            logger.error(f"[LLM Retry] 非重试异常: {e}")
            break
    
    # 所有重试都失败
    logger.error(f"[LLM Retry] 流式调用重试 {max_attempts} 次后失败")
    yield f"抱歉，服务暂时不可用，请稍后再试。"


def check_rate_limit_error(exception: Exception) -> bool:
    """
    检测是否为速率限制错误
    
    Args:
        exception: 异常对象
    
    Returns:
        是否为速率限制错误
    """
    error_msg = str(exception).lower()
    
    # 常见的速率限制关键词
    rate_limit_keywords = [
        "rate limit",
        "rate_limit",
        "too many requests",
        "429",
        "quota",
        "exceeded",
        "限流",
        "请求过于频繁",
    ]
    
    return any(keyword in error_msg for keyword in rate_limit_keywords)


def check_timeout_error(exception: Exception) -> bool:
    """
    检测是否为超时错误
    
    Args:
        exception: 异常对象
    
    Returns:
        是否为超时错误
    """
    error_msg = str(exception).lower()
    
    timeout_keywords = [
        "timeout",
        "timed out",
        "request timeout",
        "connection timeout",
        "504",
        "超时",
    ]
    
    return any(keyword in error_msg for keyword in timeout_keywords)
