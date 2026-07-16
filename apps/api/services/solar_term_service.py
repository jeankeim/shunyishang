"""
节气换装提醒服务
- 24节气列表及五行属性
- 使用 cnlunar 获取精确节气日期
- 根据节气五行 + 用户八字生成个性化换装建议
"""

import logging
from datetime import date, datetime
from typing import Optional

import cnlunar

from packages.utils.wuxing_rules import (
    ELEMENT_COLOR_MAP,
    WUXING_SHENG,
    WUXING_KE,
    WUXING_BEI_SHENG,
)

logger = logging.getLogger(__name__)

# ============================================================
# 24节气定义：名称、五行属性、换装建议
# ============================================================
SOLAR_TERMS = [
    {"name": "小寒", "element": "水", "description": "寒气渐盛，宜保暖御寒",
     "outfit_hint": "厚外套、羽绒服、围巾"},
    {"name": "大寒", "element": "水", "description": "一年最冷时节，重在保暖",
     "outfit_hint": "羊毛大衣、加厚毛衣、保暖内衣"},
    {"name": "立春", "element": "木", "description": "春回大地，木气渐旺",
     "outfit_hint": "轻薄外套、针织开衫、棉麻单品"},
    {"name": "雨水", "element": "水", "description": "雨水增多，湿气渐重",
     "outfit_hint": "防水外套、风衣、雨靴"},
    {"name": "惊蛰", "element": "木", "description": "万物复苏，气温回升",
     "outfit_hint": "春季夹克、卫衣、休闲裤"},
    {"name": "春分", "element": "木", "description": "昼夜平分，春暖花开",
     "outfit_hint": "轻薄风衣、衬衫、针织衫"},
    {"name": "清明", "element": "木", "description": "天清地明，适宜踏青",
     "outfit_hint": "户外夹克、运动装、棉麻衬衫"},
    {"name": "谷雨", "element": "土", "description": "雨生百谷，湿气较重",
     "outfit_hint": "防水风衣、透气棉质衣物"},
    {"name": "立夏", "element": "火", "description": "夏季开始，火气渐旺",
     "outfit_hint": "短袖T恤、薄款连衣裙、透气面料"},
    {"name": "小满", "element": "火", "description": "小得盈满，暑气渐增",
     "outfit_hint": "棉麻短袖、宽松短裤、凉鞋"},
    {"name": "芒种", "element": "火", "description": "仲夏时节，炎热将至",
     "outfit_hint": "防晒衣、冰丝T恤、宽松阔腿裤"},
    {"name": "夏至", "element": "火", "description": "一年最长白昼，炎热盛极",
     "outfit_hint": "真丝衬衫、棉麻连衣裙、遮阳帽"},
    {"name": "小暑", "element": "火", "description": "暑气正盛，闷热潮湿",
     "outfit_hint": "冰丝T恤、速干裤、透气凉鞋"},
    {"name": "大暑", "element": "火", "description": "一年最热时节，注意防暑",
     "outfit_hint": "薄透短袖、防晒服、遮阳伞"},
    {"name": "立秋", "element": "金", "description": "秋季开始，金气渐旺",
     "outfit_hint": "薄款外套、衬衫、长裤"},
    {"name": "处暑", "element": "金", "description": "暑气消退，秋凉渐至",
     "outfit_hint": "薄风衣、针织背心、牛仔外套"},
    {"name": "白露", "element": "金", "description": "白露凝霜，秋意渐浓",
     "outfit_hint": "长袖衬衫、薄款毛衣、西装外套"},
    {"name": "秋分", "element": "金", "description": "昼夜平分，秋高气爽",
     "outfit_hint": "风衣、夹克、针织衫"},
    {"name": "寒露", "element": "水", "description": "寒气渐重，露水凝霜",
     "outfit_hint": "羊毛衫、皮夹克、加厚外套"},
    {"name": "霜降", "element": "土", "description": "初霜降临，寒意渐深",
     "outfit_hint": "呢料大衣、厚毛衣、围巾手套"},
    {"name": "立冬", "element": "水", "description": "冬季开始，水气渐旺",
     "outfit_hint": "羽绒服、羊毛大衣、保暖围巾"},
    {"name": "小雪", "element": "水", "description": "初雪飘落，寒冷加深",
     "outfit_hint": "加厚羽绒服、皮草、保暖靴"},
    {"name": "大雪", "element": "水", "description": "大雪纷飞，严寒时节",
     "outfit_hint": "长款羽绒服、羊绒衫、加厚保暖裤"},
    {"name": "冬至", "element": "水", "description": "一阳初生，阴极阳生",
     "outfit_hint": "厚棉服、毛呢大衣、围巾手套"},
]


class SolarTermService:
    """节气换装提醒服务"""

    def get_upcoming_solar_term(self, days_ahead: int = 3) -> Optional[dict]:
        """
        获取即将到来的节气（N天内）。

        使用 cnlunar 库精确计算当年节气日期，
        返回距离今天最近且在未来 days_ahead 天内的节气信息。

        Returns:
            {"name", "date", "element", "description", "outfit_hint", "days_until"}
            或 None（无即将到来的节气）
        """
        today = date.today()
        year = today.year

        # 使用 cnlunar 获取当年精确节气日期
        lunar = cnlunar.Lunar(datetime(year, today.month, today.day), godType="8char")
        terms_dic = lunar.thisYearSolarTermsDic  # {"小寒": (1, 5), ...}

        # 构建节气日期列表，包含完整 date 对象
        term_dates = []
        for term_def in SOLAR_TERMS:
            name = term_def["name"]
            if name not in terms_dic:
                continue
            month, day = terms_dic[name]
            term_date = date(year, month, day)
            term_dates.append({
                "name": name,
                "date": term_date,
                "element": term_def["element"],
                "description": term_def["description"],
                "outfit_hint": term_def["outfit_hint"],
            })

        # 按日期排序
        term_dates.sort(key=lambda x: x["date"])

        # 查找未来 days_ahead 天内最近的节气
        for term in term_dates:
            delta = (term["date"] - today).days
            if 0 <= delta <= days_ahead:
                term["days_until"] = delta
                return term

        # 检查次年节气（跨年边界情况，如12月下旬）
        if today.month >= 11:
            try:
                next_year_lunar = cnlunar.Lunar(
                    datetime(year + 1, 1, 1), godType="8char"
                )
                next_terms_dic = next_year_lunar.thisYearSolarTermsDic
                for term_def in SOLAR_TERMS:
                    name = term_def["name"]
                    if name not in next_terms_dic:
                        continue
                    month, day = next_terms_dic[name]
                    term_date = date(year + 1, month, day)
                    delta = (term_date - today).days
                    if 0 <= delta <= days_ahead:
                        return {
                            "name": name,
                            "date": term_date,
                            "element": term_def["element"],
                            "description": term_def["description"],
                            "outfit_hint": term_def["outfit_hint"],
                            "days_until": delta,
                        }
            except Exception as e:
                logger.warning(f"[SolarTerm] 查询次年节气失败: {e}")

        return None

    def get_outfit_suggestion(self, solar_term: dict, user_bazi: dict) -> str:
        """
        根据节气五行和用户八字生成个性化换装建议。

        逻辑：
        - 节气五行与用户喜用神（suggested_elements）相生 → 强调穿该色系
        - 节气五行与用户忌神（avoid_elements）相合 → 建议避免或中和
        - 其他情况 → 给出中性建议

        Args:
            solar_term: get_upcoming_solar_term 返回的节气 dict
            user_bazi: get_user_bazi 返回的用户八字 dict

        Returns:
            换装建议文案（100字以内）
        """
        term_element = solar_term.get("element", "土")
        term_name = solar_term.get("name", "")
        description = solar_term.get("description", "")
        outfit_hint = solar_term.get("outfit_hint", "")

        suggested = user_bazi.get("suggested_elements", [])
        avoid = user_bazi.get("avoid_elements", [])

        term_colors = ELEMENT_COLOR_MAP.get(term_element, [])
        color_text = "、".join(term_colors[:2]) if term_colors else ""

        # 判断节气五行与用户喜用神关系
        if term_element in suggested:
            # 节气五行正是喜用神 → 强烈推荐
            suggestion = (
                f"{term_name}将至，{description}。"
                f"节气属{term_element}，恰合您的喜用神，"
                f"宜多穿{color_text}色系，顺应天时增运势。"
            )
        elif term_element in avoid:
            # 节气五行是忌神 → 建议中和
            # 找生喜用神的元素来中和
            neutral_element = None
            for elem in suggested:
                if WUXING_BEI_SHENG.get(elem) and WUXING_BEI_SHENG[elem] != term_element:
                    neutral_element = WUXING_BEI_SHENG[elem]
                    break
            if neutral_element:
                neutral_colors = ELEMENT_COLOR_MAP.get(neutral_element, [])
                neutral_text = "、".join(neutral_colors[:2]) if neutral_colors else ""
                suggestion = (
                    f"{term_name}将至，{description}。"
                    f"节气属{term_element}与您的忌神相近，"
                    f"建议搭配{neutral_text}色系中和，"
                    f"可选{outfit_hint}。"
                )
            else:
                suggestion = (
                    f"{term_name}将至，{description}。"
                    f"建议选{outfit_hint}，搭配亮色系点缀提气。"
                )
        elif any(WUXING_SHENG.get(term_element) == s for s in suggested):
            # 节气五行生喜用神 → 有利
            suggestion = (
                f"{term_name}将至，{description}。"
                f"节气属{term_element}生助您的喜用神，"
                f"适合穿{color_text}色系，建议选{outfit_hint}。"
            )
        else:
            # 一般情况 → 给通用建议
            suggestion = (
                f"{term_name}将至，{description}。"
                f"建议选{outfit_hint}，"
                f"搭配{color_text}色系服饰，顺应节气养生。"
            )

        return suggestion[:120]


# 模块级单例
solar_term_service = SolarTermService()
