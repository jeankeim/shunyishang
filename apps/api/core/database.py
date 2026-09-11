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

# 连接级安全参数，随池内每一条连接一起建立，不依赖 RDS 实例参数、也不依赖调用方自觉收尾。
#
# idle_in_transaction_session_timeout 是这里唯一不能省的一条：psycopg2 默认非 autocommit，
# 任何一次 execute 都会隐式 BEGIN；若客户端在事务中途被 kill / Ctrl-C / SSH 断连而没走到
# rollback，服务端的会话会永久停在 idle in transaction（PostgreSQL 该参数默认为 0=永不超时，
# RDS 沿用默认），既钉住全局 xmin 让 autovacuum 无法回收死元组（表现为表与索引持续膨胀、
# 磁盘使用率远高于实际数据量），又长期占用 max_connections 名额。生产实例上实测出现过
# 日均 18 个 idle in transaction 会话、活跃连接 0 的情况，即为此类残留。
#
# tcp_keepalives_* 让客户端已消失而服务端未察觉的"半开连接"在 ~60s 内被内核探活回收。
_SESSION_GUARD = (
    "-c idle_in_transaction_session_timeout=60s "
    "-c tcp_keepalives_idle=60 "
    "-c tcp_keepalives_interval=10 "
    "-c tcp_keepalives_count=5"
)


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
            options=_SESSION_GUARD,
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
        自动归还连接到连接池，并在获取时验证连接健康
        
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
            # 连接健康检查：验证连接可用
            try:
                with conn.cursor() as check_cur:
                    check_cur.execute("SELECT 1")
            except Exception:
                # 连接失效，关闭并重新获取
                logger.warning("连接健康检查失败，尝试重新获取连接")
                try:
                    conn.close()
                except Exception:
                    pass
                cls._pool.putconn(conn, close=True)
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
