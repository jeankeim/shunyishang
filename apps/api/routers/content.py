"""
五行穿搭百科内容路由
提供五行穿搭知识百科 API
"""

import json
import logging
import random
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query

from packages.utils.wuxing_rules import TIANGAN_WUXING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

# ============================================================
# 启动时加载百科数据到内存
# ============================================================
_SEED_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seeds" / "wuxing_wiki.json"

_WIKI_DATA: List[dict] = []
_WIKI_BY_ELEMENT: dict = {}


def _load_wiki_data() -> None:
    """加载五行穿搭百科数据到模块级变量"""
    global _WIKI_DATA, _WIKI_BY_ELEMENT
    try:
        with open(_SEED_PATH, "r", encoding="utf-8") as f:
            _WIKI_DATA = json.load(f)
        # 按五行分组索引
        _WIKI_BY_ELEMENT = {}
        for item in _WIKI_DATA:
            elem = item.get("element", "")
            _WIKI_BY_ELEMENT.setdefault(elem, []).append(item)
        logger.info(f"五行穿搭百科数据加载成功: {len(_WIKI_DATA)} 条, 覆盖五行: {list(_WIKI_BY_ELEMENT.keys())}")
    except Exception as e:
        logger.error(f"五行穿搭百科数据加载失败: {e}")
        _WIKI_DATA = []
        _WIKI_BY_ELEMENT = {}


_load_wiki_data()


def _get_today_element(target_date: Optional[date] = None) -> str:
    """
    根据日期的日柱天干推算当日五行

    使用 cnlunar 获取当天日柱干支，取天干查 TIANGAN_WUXING 映射。
    """
    if target_date is None:
        target_date = date.today()

    try:
        import cnlunar
        dt = datetime(target_date.year, target_date.month, target_date.day, 12)
        lunar = cnlunar.Lunar(dt, godType='8char')
        day_gz = lunar.day8Char  # 日柱干支，如 "甲子"
        day_stem = day_gz[0]      # 日柱天干，如 "甲"
        element = TIANGAN_WUXING.get(day_stem, "土")
        logger.debug(f"日期 {target_date} 日柱={day_gz}, 天干={day_stem}, 五行={element}")
        return element
    except Exception as e:
        logger.warning(f"cnlunar 日柱计算失败，回退到 day_of_year 轮转: {e}")
        # 回退方案：按一年中的第几天轮转
        elements = ["木", "火", "土", "金", "水"]
        day_of_year = target_date.timetuple().tm_yday
        return elements[day_of_year % 5]


@router.get("/wuxing-tips")
async def get_wuxing_tips(
    date: Optional[str] = Query(None, description="日期，格式 YYYY-MM-DD，默认今天"),
    element: Optional[str] = Query(None, description="指定五行元素（木/火/土/金/水），覆盖自动推算"),
):
    """
    获取今日五行穿搭百科知识

    根据当日日柱天干推算五行，返回1条匹配的百科知识。
    也可通过 element 参数直接指定五行元素。
    """
    # 解析日期
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "日期格式错误，请使用 YYYY-MM-DD 格式"}

    # 确定五行元素
    if element and element in _WIKI_BY_ELEMENT:
        today_element = element
    else:
        today_element = _get_today_element(target_date)

    # 从该五行的百科中随机选1条
    candidates = _WIKI_BY_ELEMENT.get(today_element, [])
    if not candidates:
        # 兜底：从所有数据中随机选
        candidates = _WIKI_DATA if _WIKI_DATA else [{"message": "暂无数据"}]

    selected = random.choice(candidates)

    return {
        "date": (target_date or date.today()).isoformat(),
        "element": today_element,
        **selected,
    }


@router.get("/wuxing-tips/all")
async def get_all_wuxing_tips(
    element: Optional[str] = Query(None, description="筛选五行元素（木/火/土/金/水）"),
):
    """获取全部五行穿搭百科知识"""
    if element and element in _WIKI_BY_ELEMENT:
        return {"element": element, "tips": _WIKI_BY_ELEMENT[element]}
    return {"tips": _WIKI_DATA}
