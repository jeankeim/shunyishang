"""
统一时间工具

生产容器默认 UTC 时区，date.today() / datetime.now() 在北京时间 00:00~08:00
会落后一天，导致每日运势、每日仪式等按日期缓存的功能展示前一天内容。
所有按"用户自然日"计算的业务逻辑必须使用本模块的北京时间。
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

# 用户均为国内用户，统一按北京时间（东八区）计算自然日
CN_TZ = ZoneInfo("Asia/Shanghai")


def today_cn() -> date:
    """当前北京时间的日期（自然日）"""
    return datetime.now(CN_TZ).date()


def now_cn() -> datetime:
    """当前北京时间（带时区信息的 datetime）"""
    return datetime.now(CN_TZ)


def seconds_until_end_of_day_cn(min_ttl: int = 600) -> int:
    """
    距北京时间今日 23:59:59 的秒数，用于"按自然日失效"的缓存 TTL。

    min_ttl 兜底：临近午夜时不给 0 秒，否则缓存写了等于没写。
    """
    now = datetime.now(CN_TZ)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return max(min_ttl, int((end_of_day - now).total_seconds()))
