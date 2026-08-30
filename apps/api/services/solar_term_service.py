"""
节气换装提醒服务
- 24节气列表及五行属性
- 使用 cnlunar 获取精确节气日期
- 根据节气五行 + 用户八字生成个性化换装建议
- 换季开柜仪式：按下一节气给出「该收 / 该拿」清单与宜忌
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cnlunar
from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn
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

# ============================================================
# 换季开柜仪式（批次三 3.3）
# ============================================================

# 节气所属季节（按六节划分：立春/立夏/立秋/立冬为四季之始）
TERM_SEASON: Dict[str, str] = {
    "小寒": "冬", "大寒": "冬",
    "立春": "春", "雨水": "春", "惊蛰": "春", "春分": "春", "清明": "春", "谷雨": "春",
    "立夏": "夏", "小满": "夏", "芒种": "夏", "夏至": "夏", "小暑": "夏", "大暑": "夏",
    "立秋": "秋", "处暑": "秋", "白露": "秋", "秋分": "秋", "寒露": "秋", "霜降": "秋",
    "立冬": "冬", "小雪": "冬", "大雪": "冬", "冬至": "冬",
}

# 各季节适配的厚度档位（衣橱 thickness_level 词表：轻薄/适中/加厚/厚重）
# 春秋为过渡季，共用"适中"，因此能明确区分出该收与该拿
SEASON_THICKNESS: Dict[str, Tuple[str, ...]] = {
    "春": ("适中", "轻薄"),
    "夏": ("轻薄",),
    "秋": ("适中", "加厚"),
    "冬": ("加厚", "厚重"),
}

# 下一季能穿却这么久没上身，就值得拿出来穿一次打个卡
RITUAL_IDLE_DAYS = 90
RITUAL_LIST_LIMIT = 8

# 节气名 → 定义（外部传入的节气 dict 字段不全时用它补齐）
TERM_META: Dict[str, Dict[str, str]] = {t["name"]: t for t in SOLAR_TERMS}

# 月份 → 季节（仅在传入的节气名不在 24 节气表里时兜底用）
_MONTH_SEASON: Dict[int, str] = {
    1: "冬", 2: "春", 3: "春", 4: "春", 5: "夏", 6: "夏",
    7: "夏", 8: "秋", 9: "秋", 10: "秋", 11: "冬", 12: "冬",
}


class SolarTermService:
    """节气换装提醒服务"""

    def _year_terms(self, year: int) -> List[Dict[str, Any]]:
        """某公历年的 24 节气精确日期（cnlunar），按日期升序"""
        lunar = cnlunar.Lunar(datetime(year, 1, 1), godType="8char")
        terms_dic = lunar.thisYearSolarTermsDic  # {"小寒": (1, 5), ...}

        terms: List[Dict[str, Any]] = []
        for term_def in SOLAR_TERMS:
            name = term_def["name"]
            if name not in terms_dic:
                continue
            month, day = terms_dic[name]
            try:
                term_date = date(year, month, day)
            except ValueError:
                logger.warning(f"[SolarTerm] {year} 年节气日期异常: {name} {month}-{day}")
                continue
            terms.append({
                "name": name,
                "date": term_date,
                "element": term_def["element"],
                "description": term_def["description"],
                "outfit_hint": term_def["outfit_hint"],
            })
        terms.sort(key=lambda t: t["date"])
        return terms

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
        term_dates = self._year_terms(today.year)

        # 跨年边界（如12月下旬）要把次年 1 月的节气一并纳入
        if today.month >= 11:
            try:
                term_dates = term_dates + self._year_terms(today.year + 1)
            except Exception as e:
                logger.warning(f"[SolarTerm] 查询次年节气失败: {e}")
        term_dates.sort(key=lambda t: t["date"])

        for term in term_dates:
            delta = (term["date"] - today).days
            if 0 <= delta <= days_ahead:
                term["days_until"] = delta
                return term

        return None

    def get_term_pair(self, today: Optional[date] = None) -> Tuple[Optional[dict], Optional[dict]]:
        """
        当前所处节气与下一个节气。

        三年节气表拼接后按日期定位，因此冬至→小寒的跨年边界与交节当天
        （当天即算已交节，current 就是它）都不会落到空档里。
        """
        ref = today or today_cn()
        terms: List[Dict[str, Any]] = []
        for year in (ref.year - 1, ref.year, ref.year + 1):
            try:
                terms.extend(self._year_terms(year))
            except Exception as e:
                logger.warning(f"[SolarTerm] {year} 年节气表生成失败: {e}")
        if not terms:
            return None, None

        terms.sort(key=lambda t: t["date"])
        current: Optional[dict] = None
        upcoming: Optional[dict] = None
        for term in terms:
            if term["date"] > ref:
                upcoming = term
                break
            current = term
        return current, upcoming

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

    # ── 换季开柜仪式 ────────────────────────────────────────────────────────

    def get_wardrobe_ritual(
        self,
        user_id: int,
        solar_term: Optional[Dict[str, Any]] = None,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        换季开柜仪式：以「下一个节气」为参照给出该收 / 该拿两张清单与宜忌提示。

        - 该收：applicable_seasons 明确不含下一季，且 thickness_level 不在下一季适配档位
        - 该拿：下一季能穿，却近 RITUAL_IDLE_DAYS 天没上身
                （last_worn_date 缺失按 created_at 兜底，引导走既有穿着打卡端点）
        - 宜忌：沿用 get_outfit_suggestion 的节气 + 八字穿搭提示，并附衣橱五行缺口元素

        清单只做"穿哪件 / 收哪件"的搭配组织，文案不含吉凶断言与价格信息。
        """
        ref = today or today_cn()
        current_term, upcoming_term = self.get_term_pair(ref)
        term = dict(solar_term or upcoming_term or current_term or {})
        term_name = str(term.get("name") or "")
        next_season = TERM_SEASON.get(term_name) or _MONTH_SEASON.get(ref.month, "")
        expected_thickness = SEASON_THICKNESS.get(next_season, ())

        store_items: List[Dict[str, Any]] = []
        store_total = 0
        take_items: List[Dict[str, Any]] = []
        take_total = 0
        if next_season:
            try:
                store_items, store_total = _store_away_query(
                    user_id, next_season, list(expected_thickness), ref
                )
            except Exception as e:
                logger.error(f"[SolarTerm] 该收清单查询失败 user={user_id}: {e}")
            try:
                take_items, take_total = _take_out_query(user_id, next_season, ref)
            except Exception as e:
                logger.error(f"[SolarTerm] 该拿清单查询失败 user={user_id}: {e}")

        current_season = TERM_SEASON.get(str((current_term or {}).get("name") or ""))
        return {
            "solar_term": self._shape_term(term, ref),
            "current_term": (
                {
                    "name": current_term["name"],
                    "date": str(current_term["date"]),
                    "season": current_season,
                }
                if current_term else None
            ),
            "next_season": next_season,
            "expected_thickness": list(expected_thickness),
            # 下一节气是否真的换季：换季时卡片是"开柜仪式"，季中则是常规检查
            "is_season_boundary": bool(next_season and current_season and current_season != next_season),
            "store_away": {
                "items": store_items,
                "total": store_total,
                "reason": (
                    f"{term_name or '换季'}后转{next_season}季，这些单品用不到{next_season}季，"
                    "厚度也不搭，可以先收进柜子深处"
                ),
            },
            "take_out": {
                "items": take_items,
                "total": take_total,
                "reason": (
                    f"这些能穿到{next_season}季的单品已经 {RITUAL_IDLE_DAYS} 天以上没上身，"
                    "拿出来穿一次打个卡，比添新衣更划算"
                ),
            },
            "yi_ji": self._ritual_yi_ji(user_id, term or (upcoming_term or {})),
            "has_action": bool(store_items or take_items),
        }

    @staticmethod
    def _shape_term(term: Dict[str, Any], ref: date) -> Optional[Dict[str, Any]]:
        """节气输出：date 一律转 ISO（要进 JSON 缓存），缺失字段用 24 节气表补齐"""
        if not term or not term.get("name"):
            return None
        name = str(term["name"])
        meta = TERM_META.get(name, {})
        raw = term.get("date")
        term_date: Optional[date] = None
        if isinstance(raw, datetime):
            term_date = raw.date()
        elif isinstance(raw, date):
            term_date = raw
        elif isinstance(raw, str) and raw:
            try:
                term_date = date.fromisoformat(raw[:10])
            except ValueError:
                term_date = None
        return {
            "name": name,
            "date": str(term_date) if term_date else None,
            "element": term.get("element") or meta.get("element", ""),
            "description": term.get("description") or meta.get("description", ""),
            "outfit_hint": term.get("outfit_hint") or meta.get("outfit_hint", ""),
            "season": TERM_SEASON.get(name, ""),
            "days_until": (term_date - ref).days if term_date else None,
        }

    def _ritual_yi_ji(self, user_id: int, term: Dict[str, Any]) -> Dict[str, Any]:
        """宜（节气 + 八字穿搭建议）与衣橱五行缺口元素（复用平衡仪表盘，失败不阻断）"""
        advice = ""
        try:
            from apps.api.services.user_service import get_user_bazi

            advice = self.get_outfit_suggestion(term, get_user_bazi(user_id) or {})
        except Exception as e:
            logger.warning(f"[SolarTerm] 节气宜忌生成失败 user={user_id}: {e}")
            hint = term.get("outfit_hint") or ""
            colors = "、".join(ELEMENT_COLOR_MAP.get(term.get("element") or "", [])[:2])
            advice = f"{term.get('name') or '换季'}前后，建议选{hint}" + (f"，多穿{colors}色系。" if colors else "。")

        gap_elements: List[Dict[str, Any]] = []
        try:
            from apps.api.services.wardrobe_analytics_service import get_element_balance

            balance = get_element_balance(user_id)
            gap_elements = [
                {"element": a.get("element"), "headline": a.get("headline")}
                for a in (balance.get("advice") or [])[:2]
            ]
        except Exception as e:
            logger.warning(f"[SolarTerm] 五行缺口获取失败 user={user_id}: {e}")

        return {"advice": advice, "gap_elements": gap_elements}


# ─────────────────────────────────────────────────────────────────────────────
# 开柜仪式数据库查询（模块级，便于单测打桩）
# ─────────────────────────────────────────────────────────────────────────────

def _as_date(value: Any) -> Optional[date]:
    """DATE / TIMESTAMP / 字符串统一转 date"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _shape_ritual_item(row: Dict[str, Any], ref: date) -> Dict[str, Any]:
    """清单条目输出：闲置天数按北京时间参照日计算，last_worn 缺失时以 created_at 兜底"""
    seasons = row.get("applicable_seasons")
    if isinstance(seasons, str):
        try:
            seasons = json.loads(seasons)
        except (TypeError, ValueError):
            seasons = []
    last_worn = _as_date(row.get("last_worn_date"))
    # 从没穿过的新物按入橱时间算闲置，但 last_worn 要留空，前端才写得出"还没穿过"
    base = last_worn or _as_date(row.get("created_at"))
    return {
        "id": row["id"],
        "name": row.get("name") or "未命名衣物",
        "category": row.get("category"),
        "image_url": row.get("image_url"),
        "primary_element": row.get("primary_element"),
        "thickness_level": row.get("thickness_level"),
        "seasons": list(seasons or []),
        "wear_count": int(row.get("wear_count") or 0),
        "last_worn": str(last_worn) if last_worn else None,
        "idle_days": max(0, (ref - base).days) if base else None,
    }


def _fetch_rows(query: str, params: List[Any]) -> List[Dict[str, Any]]:
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


def _store_away_query(
    user_id: int,
    next_season: str,
    expected_thickness: Sequence[str],
    ref: date,
    limit: int = RITUAL_LIST_LIMIT,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    该收：季节标签明确没有下一季，且厚度不在下一季适配档位。

    季节为空（未标注）或厚度未知的都不进清单——宁缺毋滥，不想误伤常穿单品。
    total_matched 用窗口函数一次带回，前端可提示"共 N 件，先看这几件"。
    """
    query = """
        SELECT id, name, category, image_url, primary_element, thickness_level,
               applicable_seasons, wear_count, last_worn_date, created_at,
               COUNT(*) OVER () AS total_matched
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
          AND COALESCE(applicable_seasons, '[]'::jsonb) <> '[]'::jsonb
          AND NOT (COALESCE(applicable_seasons, '[]'::jsonb) @> %s::jsonb)
          AND thickness_level IS NOT NULL
          AND NOT (thickness_level = ANY(%s))
        ORDER BY wear_count DESC NULLS LAST, id
        LIMIT %s
    """
    params = [
        user_id,
        json.dumps([next_season], ensure_ascii=False),
        list(expected_thickness),
        limit,
    ]
    rows = _fetch_rows(query, params)
    total = int(rows[0].get("total_matched") or 0) if rows else 0
    return [_shape_ritual_item(r, ref) for r in rows], total


def _take_out_query(
    user_id: int,
    next_season: str,
    ref: date,
    idle_days: int = RITUAL_IDLE_DAYS,
    limit: int = RITUAL_LIST_LIMIT,
) -> Tuple[List[Dict[str, Any]], int]:
    """该拿：下一季适用但近 idle_days 天没上身，最久没穿的排在前面"""
    query = """
        SELECT id, name, category, image_url, primary_element, thickness_level,
               applicable_seasons, wear_count, last_worn_date, created_at,
               COUNT(*) OVER () AS total_matched
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
          AND COALESCE(applicable_seasons, '[]'::jsonb) @> %s::jsonb
          AND COALESCE(last_worn_date, created_at)::date <= %s::date - %s
        ORDER BY COALESCE(last_worn_date, created_at)::date ASC
        LIMIT %s
    """
    params = [
        user_id,
        json.dumps([next_season], ensure_ascii=False),
        ref,
        idle_days,
        limit,
    ]
    rows = _fetch_rows(query, params)
    total = int(rows[0].get("total_matched") or 0) if rows else 0
    return [_shape_ritual_item(r, ref) for r in rows], total


# 模块级单例
solar_term_service = SolarTermService()
