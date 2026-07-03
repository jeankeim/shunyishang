"""
retry 模块测试
测试 LLM 调用重试逻辑、异常分类、错误检测函数
"""

import pytest
from unittest.mock import patch, MagicMock
from apps.api.core.retry import (
    LLMServiceError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMConnectionError,
    get_llm_retry_config,
    llm_retry,
    llm_stream_with_retry,
    check_rate_limit_error,
    check_timeout_error,
)


class TestCheckRateLimitError:
    """测试速率限制错误检测"""

    def test_rate_limit_keyword(self):
        """rate limit 关键词"""
        assert check_rate_limit_error(Exception("rate limit exceeded")) is True

    def test_rate_limit_underscore(self):
        """rate_limit 关键词"""
        assert check_rate_limit_error(Exception("rate_limit")) is True

    def test_too_many_requests(self):
        """too many requests 关键词"""
        assert check_rate_limit_error(Exception("Too Many Requests")) is True

    def test_429_status(self):
        """429 状态码"""
        assert check_rate_limit_error(Exception("Error 429")) is True

    def test_quota_exceeded(self):
        """quota exceeded 关键词"""
        assert check_rate_limit_error(Exception("quota exceeded")) is True

    def test_chinese_keyword(self):
        """中文关键词 - 限流"""
        assert check_rate_limit_error(Exception("请求被限流")) is True

    def test_chinese_too_frequent(self):
        """中文关键词 - 请求过于频繁"""
        assert check_rate_limit_error(Exception("请求过于频繁")) is True

    def test_non_rate_limit_error(self):
        """非速率限制错误"""
        assert check_rate_limit_error(Exception("internal server error")) is False

    def test_empty_message(self):
        """空消息"""
        assert check_rate_limit_error(Exception("")) is False

    def test_case_insensitive(self):
        """大小写不敏感"""
        assert check_rate_limit_error(Exception("RATE LIMIT")) is True
        assert check_rate_limit_error(Exception("QUOTA Exceeded")) is True


class TestCheckTimeoutError:
    """测试超时错误检测"""

    def test_timeout_keyword(self):
        """timeout 关键词"""
        assert check_timeout_error(Exception("request timeout")) is True

    def test_timed_out(self):
        """timed out 关键词"""
        assert check_timeout_error(Exception("timed out")) is True

    def test_connection_timeout(self):
        """connection timeout 关键词"""
        assert check_timeout_error(Exception("connection timeout")) is True

    def test_504_status(self):
        """504 状态码"""
        assert check_timeout_error(Exception("Error 504")) is True

    def test_chinese_timeout(self):
        """中文超时关键词"""
        assert check_timeout_error(Exception("请求超时")) is True

    def test_non_timeout_error(self):
        """非超时错误"""
        assert check_timeout_error(Exception("internal server error")) is False

    def test_empty_message(self):
        """空消息"""
        assert check_timeout_error(Exception("")) is False


class TestGetLLMRetryConfig:
    """测试 LLM 重试配置"""

    def test_default_config(self):
        """默认配置"""
        config = get_llm_retry_config()
        assert config is not None
        assert "stop" in config
        assert "wait" in config
        assert "retry" in config
        assert "before_sleep" in config
        assert config["reraise"] is True

    def test_custom_config(self):
        """自定义配置"""
        config = get_llm_retry_config(max_attempts=5, min_wait=1.0, max_wait=30.0)
        assert config is not None
        assert config["reraise"] is True


class TestLLMRetryDecorator:
    """测试 llm_retry 装饰器"""

    def test_success_no_retry(self):
        """成功调用不重试"""
        call_count = 0

        @llm_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_then_success(self):
        """重试后成功"""
        call_count = 0

        @llm_retry(max_attempts=3, min_wait=0.01, max_wait=0.05)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMRateLimitError("rate limited")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count >= 2

    def test_retry_exhausted_with_fallback(self):
        """重试耗尽，返回 fallback"""
        call_count = 0

        @llm_retry(max_attempts=2, min_wait=0.01, max_wait=0.05, fallback="fallback_value")
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise LLMConnectionError("connection failed")

        result = always_fail()
        assert result == "fallback_value"

    def test_retry_exhausted_no_fallback_raises(self):
        """重试耗尽，无 fallback 抛出异常"""
        @llm_retry(max_attempts=2, min_wait=0.01, max_wait=0.05)
        def always_fail():
            raise LLMConnectionError("connection failed")

        with pytest.raises((LLMServiceError, LLMConnectionError, Exception)):
            always_fail()

    def test_non_retry_exception_with_fallback(self):
        """非重试异常，有 fallback"""
        @llm_retry(max_attempts=2, min_wait=0.01, max_wait=0.05, fallback="fallback")
        def raise_value_error():
            raise ValueError("not a retry error")

        result = raise_value_error()
        assert result == "fallback"

    def test_non_retry_exception_no_fallback_reraises(self):
        """非重试异常，无 fallback 重新抛出"""
        @llm_retry(max_attempts=2, min_wait=0.01, max_wait=0.05)
        def raise_value_error():
            raise ValueError("not a retry error")

        with pytest.raises((ValueError, LLMServiceError, Exception)):
            raise_value_error()


class TestLLMStreamWithRetry:
    """测试流式 LLM 调用重试"""

    def test_stream_success(self):
        """流式调用成功"""
        def gen():
            for chunk in ["hello", "world"]:
                yield chunk

        result = list(llm_stream_with_retry(gen, max_attempts=2, min_wait=0.01, max_wait=0.05))
        assert "hello" in result
        assert "world" in result

    def test_stream_retry_then_success(self):
        """流式调用重试后成功"""
        call_count = 0

        def gen():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMConnectionError("connection failed")
            yield "success"

        result = list(llm_stream_with_retry(gen, max_attempts=3, min_wait=0.01, max_wait=0.05))
        assert "success" in result
        assert call_count >= 2

    def test_stream_all_fail_returns_error_message(self):
        """流式调用全部失败，返回错误消息"""
        def gen():
            raise LLMConnectionError("connection failed")
            yield  # 使函数成为生成器

        result = list(llm_stream_with_retry(gen, max_attempts=2, min_wait=0.01, max_wait=0.05))
        # 失败后返回错误消息
        assert len(result) > 0
        assert "不可用" in result[-1] or "稍后" in result[-1]

    def test_stream_non_retry_exception_breaks(self):
        """流式调用非重试异常中断"""
        call_count = 0

        def gen():
            nonlocal call_count
            call_count += 1
            raise ValueError("not a retry error")
            yield  # 使函数成为生成器

        result = list(llm_stream_with_retry(gen, max_attempts=3, min_wait=0.01, max_wait=0.05))
        assert call_count == 1  # 非重试异常不重试
        assert len(result) > 0  # 返回错误消息


class TestLLMExceptions:
    """测试 LLM 异常类层次"""

    def test_llm_service_error_base(self):
        """LLMServiceError 是 Exception 子类"""
        exc = LLMServiceError("test")
        assert isinstance(exc, Exception)

    def test_llm_rate_limit_is_service_error(self):
        """LLMRateLimitError 是 LLMServiceError 子类"""
        exc = LLMRateLimitError("test")
        assert isinstance(exc, LLMServiceError)

    def test_llm_timeout_is_service_error(self):
        """LLMTimeoutError 是 LLMServiceError 子类"""
        exc = LLMTimeoutError("test")
        assert isinstance(exc, LLMServiceError)

    def test_llm_connection_is_service_error(self):
        """LLMConnectionError 是 LLMServiceError 子类"""
        exc = LLMConnectionError("test")
        assert isinstance(exc, LLMServiceError)
