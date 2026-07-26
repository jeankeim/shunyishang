"""
用户八字信息服务
提供统一的用户八字数据获取接口，供 diary/fortune/destiny 等模块共享使用
"""

import json
import logging
from datetime import date
from typing import Optional

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.pii_crypto import decrypt_date

logger = logging.getLogger(__name__)


def get_user_bazi(user_id: int, include_extended: bool = False) -> dict:
    """
    获取用户八字信息。

    Args:
        user_id: 用户ID
        include_extended: 是否包含扩展字段(gender, birth_date 等)

    Returns:
        基础模式: {day_master, suggested_elements, avoid_elements, pillars}
        扩展模式: 基础 + {gender, _birth_year, _birth_month, _birth_day,
                  eight_chars, dominant_element, lacking_element,
                  month_element, reasoning}
    """
    if include_extended:
        query = "SELECT bazi, xiyong_elements, gender, birth_date FROM users WHERE id = %s"
    else:
        query = "SELECT bazi, xiyong_elements FROM users WHERE id = %s"

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id])
            row = cur.fetchone()

    if not row or not row.get('bazi'):
        result = {
            "day_master": "土",
            "suggested_elements": [],
            "avoid_elements": [],
            "pillars": {},
        }
        if include_extended:
            result["gender"] = "男"
        return result

    bazi = row['bazi']
    if isinstance(bazi, str):
        bazi = json.loads(bazi)

    result = {
        "day_master": bazi.get("day_master", "土"),
        "suggested_elements": bazi.get("suggested_elements", []),
        "avoid_elements": bazi.get("avoid_elements", []),
        "pillars": bazi.get("pillars", {}),
    }

    if include_extended:
        gender = row.get('gender', '男')
        # 敏感字段解密（兼容明文历史数据）
        birth_date = decrypt_date(row.get('birth_date'))

        # 解析出生日期
        _birth_year = None
        _birth_month = None
        _birth_day = None
        if birth_date:
            _birth_year = birth_date.year
            _birth_month = birth_date.month
            _birth_day = birth_date.day

        result.update({
            "eight_chars": bazi.get("eight_chars", []),
            "dominant_element": bazi.get("dominant_element", "土"),
            "lacking_element": bazi.get("lacking_element"),
            "month_element": bazi.get("month_element", "土"),
            "reasoning": bazi.get("reasoning", ""),
            "gender": gender,
            "_birth_year": _birth_year,
            "_birth_month": _birth_month,
            "_birth_day": _birth_day,
        })

    return result
