"""
数据库连接池模块
使用 psycopg2.pool.ThreadedConnectionPool 管理连接
"""

import atexit
import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from apps.api.core.config import settings

logger = logging.getLogger(__name__)


class DatabasePool:
    """数据库连接池管理器"""
    
    _pool: ThreadedConnectionPool | None = None
    
    @classmethod
    def init_pool(cls) -> None:
        """初始化连接池"""
        if cls._pool is not None:
            return
        
        cls._pool = ThreadedConnectionPool(
            minconn=2,
            maxconn=settings.database_pool_size,
            dsn=settings.database_url,
        )
        logger.info(f"连接池已初始化 (maxconn={settings.database_pool_size})")
    
    @classmethod
    def close_pool(cls) -> None:
        """关闭连接池"""
        if cls._pool is not None:
            cls._pool.closeall()
            cls._pool = None
            logger.info("连接池已关闭")
    
    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator:
        """
        获取数据库连接的上下文管理器
        自动归还连接到连接池
        
        Usage:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM items")
        """
        if cls._pool is None:
            cls.init_pool()
        
        conn = None
        try:
            conn = cls._pool.getconn()
            yield conn
        finally:
            if conn is not None:
                cls._pool.putconn(conn)
    
    @classmethod
    def check_health(cls) -> bool:
        """
        检查数据库连接健康状态
        执行 SELECT 1 验证连接
        
        Returns:
            bool: 连接正常返回 True，否则返回 False
        """
        try:
            with cls.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False


# 应用退出时自动关闭连接池
atexit.register(DatabasePool.close_pool)


# 便捷函数导出
def get_connection() -> Generator:
    """获取数据库连接的便捷函数"""
    return DatabasePool.get_connection()


def check_db_health() -> bool:
    """检查数据库健康的便捷函数"""
    return DatabasePool.check_health()
