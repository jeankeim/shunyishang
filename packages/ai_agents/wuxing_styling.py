"""
五行穿搭百科Agent - WuxingStylingAgent
提供基于五行命理的智能穿搭百科知识推荐
"""

import json
import logging
import random
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from packages.utils.wuxing_rules import TIANGAN_WUXING

logger = logging.getLogger(__name__)

# ============================================================
# 百科数据加载（模块级单例）
# ============================================================
_SEED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "seeds" / "wuxing_wiki.json"

_WIKI_DATA: list = []
_WIKI_BY_ELEMENT: dict = {}


def _ensure_wiki_loaded() -> None:
    """懒加载百科数据，确保只加载一次"""
    global _WIKI_DATA, _WIKI_BY_ELEMENT
    if _WIKI_DATA:
        return
    try:
        with open(_SEED_PATH, "r", encoding="utf-8") as f:
            _WIKI_DATA = json.load(f)
        for item in _WIKI_DATA:
            elem = item.get("element", "")
            _WIKI_BY_ELEMENT.setdefault(elem, []).append(item)
        logger.info(f"WuxingStylingAgent: 百科数据加载成功, {len(_WIKI_DATA)} 条")
    except Exception as e:
        logger.error(f"WuxingStylingAgent: 百科数据加载失败: {e}")
        _WIKI_DATA = []
        _WIKI_BY_ELEMENT = {}


# ============================================================
# 日柱天干→五行推算
# ============================================================
def get_today_element(target_date: Optional[date] = None) -> str:
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
        day_gz = lunar.day8Char
        day_stem = day_gz[0]
        element = TIANGAN_WUXING.get(day_stem, "土")
        logger.debug(f"日期 {target_date} 日柱={day_gz}, 天干={day_stem}, 五行={element}")
        return element
    except Exception as e:
        logger.warning(f"cnlunar 日柱计算失败，回退到 day_of_year 轮转: {e}")
        elements = ["木", "火", "土", "金", "水"]
        day_of_year = target_date.timetuple().tm_yday
        return elements[day_of_year % 5]


# ============================================================
# WuxingStylingAgent
# ============================================================
class WuxingStylingAgent:
    """
    五行穿搭百科Agent

    功能：根据当日五行属性，推荐穿搭建议。
    数据源：data/seeds/wuxing_wiki.json（启动时加载到内存）
    """

    def __init__(self):
        """初始化Agent，加载百科数据"""
        _ensure_wiki_loaded()
        self.wiki_data = _WIKI_DATA
        self.wiki_by_element = _WIKI_BY_ELEMENT

    def get_today_tip(self, target_date: Optional[date] = None, element: Optional[str] = None) -> dict:
        """
        获取当日五行穿搭建议

        Args:
            target_date: 指定日期，默认今天
            element: 指定五行元素（木/火/土/金/水），覆盖自动推算

        Returns:
            dict: 包含 date, element, tip 的穿搭建议
        """
        if target_date is None:
            target_date = date.today()

        # 确定五行元素
        if element and element in self.wiki_by_element:
            today_element = element
        else:
            today_element = get_today_element(target_date)

        # 从该五行的百科中随机选1条
        candidates = self.wiki_by_element.get(today_element, [])
        if not candidates:
            candidates = self.wiki_data if self.wiki_data else [{"message": "暂无数据"}]

        selected = random.choice(candidates)

        return {
            "date": target_date.isoformat(),
            "element": today_element,
            "tip": selected,
        }

    def get_all_tips(self, element: Optional[str] = None) -> dict:
        """
        获取百科知识列表

        Args:
            element: 筛选五行元素，None 返回全部

        Returns:
            dict: 百科知识列表
        """
        if element and element in self.wiki_by_element:
            return {"element": element, "tips": self.wiki_by_element[element]}
        return {"tips": self.wiki_data}

    def get_tips_by_category(self, category: str, element: Optional[str] = None) -> list:
        """
        按类别获取百科知识

        Args:
            category: 类别名称（如"颜色搭配"、"材质推荐"等）
            element: 筛选五行元素

        Returns:
            list: 匹配的百科条目
        """
        if element and element in self.wiki_by_element:
            pool = self.wiki_by_element[element]
        else:
            pool = self.wiki_data

        return [item for item in pool if item.get("category") == category]
