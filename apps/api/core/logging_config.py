"""
日志配置模块
提供统一的日志格式和级别管理
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from apps.api.core.config import settings


# 日志格式定义
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 易经风格日志前缀
YIJING_PREFIXES = {
    "DEBUG": "🔍",      # 观 - 观察
    "INFO": "✅",       # 吉 - 吉祥
    "WARNING": "⚠️",    # 咎 - 警示
    "ERROR": "❌",      # 凶 - 凶险
    "CRITICAL": "🚨",   # 大凶 - 严重
}


class YiJingFormatter(logging.Formatter):
    """易经风格日志格式化器"""
    
    def format(self, record):
        # 添加易经风格前缀
        prefix = YIJING_PREFIXES.get(record.levelname, "")
        record.message = f"{prefix} {record.getMessage()}" if prefix else record.getMessage()
        
        # 使用父类格式化
        return super().format(record)


def setup_logging(
    level: str = None,
    log_file: str = None,
    use_yijing_style: bool = True
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径（可选）
        use_yijing_style: 是否使用易经风格格式
    
    Returns:
        根日志记录器
    """
    # 确定日志级别
    log_level = level or ("DEBUG" if settings.app_debug else "INFO")
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 选择格式化器
    formatter_class = YiJingFormatter if use_yijing_style else logging.Formatter
    formatter = formatter_class(LOG_FORMAT, DATE_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 模块名称（通常使用 __name__）
    
    Returns:
        日志记录器实例
    
    Example:
        logger = get_logger(__name__)
        logger.info("操作成功")
    """
    return logging.getLogger(name)


# 初始化日志系统（延迟到首次使用）
_logger_initialized = False


def init_logging():
    """初始化日志系统（在应用启动时调用）"""
    global _logger_initialized
    
    if _logger_initialized:
        return
    
    setup_logging(
        level="DEBUG" if settings.app_debug else "INFO",
        log_file=None,  # 可配置为文件路径
        use_yijing_style=True
    )
    
    _logger_initialized = True
    
    # 输出启动日志
    logger = get_logger("wuxing")
    logger.info(f"五行AI衣橱启动 | 环境: {settings.app_env} | 调试模式: {settings.app_debug}")
