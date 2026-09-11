#!/usr/bin/env python3
"""
离线脚本的数据库连接入口（唯一应该使用的 connect 工厂）

为什么需要这个文件
------------------
本仓库的离线脚本历史上直接调用 psycopg2.connect()，并且只在"正常跑完"的出口
close()。一旦被 Ctrl-C、被 kill、SSH 断连或抛出未捕获异常，服务端的会话就会
永久停在 idle in transaction 状态：

- psycopg2 默认非 autocommit，任何一次 execute 都会隐式 BEGIN；
- PostgreSQL 的 idle_in_transaction_session_timeout 默认为 0（永不超时），RDS 沿用默认；
- 于是"客户端早就没了、服务端还开着事务"的会话会一直存在。

后果有两层，第二层最贵：
1. 白占 max_connections 名额（小规格实例上限只有几十）；
2. 长事务钉住全局 xmin，autovacuum 无法回收其后产生的死元组 → 表与索引持续膨胀，
   表现为磁盘使用率远高于实际数据量（生产实例上实测日均 18 个 idle in transaction
   会话、活跃连接 0，业务数据仅百 MB 而实例目录占到 2.2 GB）。

apps/api/core/database.py 的连接池已带同一份守卫；本文件覆盖的是**绕过连接池**的
脚本路径。两处常量保持一致。

用法
----
    from db_connect import db_connect

    conn = db_connect(os.environ.get("DATABASE_URL"))
    conn = db_connect(get_prod_url(), connect_timeout=10)

脚本位于 scripts/ 下时，Python 会把 scripts/ 放进 sys.path，直接 import 即可；
子目录（如 scripts/collection/）需先把 scripts/ 加入 sys.path。
"""

from __future__ import annotations

from typing import Any

import psycopg2

# 与 apps/api/core/database.py 的 _SESSION_GUARD 保持一致，改动需同步两处。
SESSION_GUARD = (
    "-c idle_in_transaction_session_timeout=60s "
    "-c tcp_keepalives_idle=60 "
    "-c tcp_keepalives_interval=10 "
    "-c tcp_keepalives_count=5"
)


def db_connect(dsn: str | None = None, **kwargs: Any):
    """带会话守卫的 psycopg2.connect。

    调用方仍可显式传 options 覆盖（例如需要更长的超时做大批量写入）。
    """
    kwargs.setdefault("options", SESSION_GUARD)
    if dsn is not None:
        return psycopg2.connect(dsn, **kwargs)
    return psycopg2.connect(**kwargs)
