"""
数据库连接池测试
"""
import pytest
from unittest.mock import patch, MagicMock
from apps.api.core.database import DatabasePool, get_connection, check_db_health


class TestDatabasePool:
    """数据库连接池测试"""

    def test_init_pool_creates_pool(self):
        DatabasePool._pool = None
        mock_pool = MagicMock()
        with patch("apps.api.core.database.ThreadedConnectionPool", return_value=mock_pool) as mock_ctor:
            DatabasePool.init_pool()
            assert mock_ctor.called
            assert DatabasePool._pool is mock_pool
        DatabasePool._pool = None

    def test_init_pool_already_exists(self):
        existing = MagicMock()
        DatabasePool._pool = existing
        DatabasePool.init_pool()
        assert DatabasePool._pool is existing
        DatabasePool._pool = None

    def test_close_pool(self):
        DatabasePool._pool = MagicMock()
        DatabasePool.close_pool()
        assert DatabasePool._pool is None

    def test_close_pool_no_pool(self):
        DatabasePool._pool = None
        DatabasePool.close_pool()
        assert DatabasePool._pool is None

    def test_get_connection_auto_init(self):
        DatabasePool._pool = None
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.execute.return_value = None
        mock_cur.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        with patch("apps.api.core.database.ThreadedConnectionPool", return_value=mock_pool):
            with DatabasePool.get_connection() as conn:
                assert conn is mock_conn
            mock_pool.putconn.assert_called_once()
        DatabasePool._pool = None

    def test_get_connection_health_check_retry(self):
        """连接健康检查失败后重试"""
        DatabasePool._pool = MagicMock()
        bad_conn = MagicMock()
        bad_conn.cursor.return_value.__enter__ = MagicMock(return_value=MagicMock())
        bad_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        bad_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("conn dead")

        good_conn = MagicMock()
        good_cur = MagicMock()
        good_cur.fetchone.return_value = (1,)
        good_conn.cursor.return_value.__enter__ = MagicMock(return_value=good_cur)
        good_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        DatabasePool._pool.getconn.side_effect = [bad_conn, good_conn]

        with DatabasePool.get_connection() as conn:
            assert conn is good_conn
        DatabasePool._pool = None

    def test_check_health_success(self):
        DatabasePool._pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        DatabasePool._pool.getconn.return_value = mock_conn

        assert DatabasePool.check_health() is True
        DatabasePool._pool = None

    def test_check_health_fail(self):
        DatabasePool._pool = MagicMock()
        DatabasePool._pool.getconn.side_effect = Exception("fail")
        assert DatabasePool.check_health() is False
        DatabasePool._pool = None

    def test_get_connection_helper(self):
        """便捷函数 get_connection"""
        gen = get_connection()
        assert gen is not None

    def test_check_db_health_helper(self):
        """便捷函数 check_db_health"""
        DatabasePool._pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        DatabasePool._pool.getconn.return_value = mock_conn

        assert check_db_health() is True
        DatabasePool._pool = None
