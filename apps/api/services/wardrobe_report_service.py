"""
衣橱年度报告服务（批次三 3.2）

先把一年的穿着事实用 SQL 聚合出来（穿得最多的一件、最久未动的一件、今年新增 vs
今年穿过、本命色、五行变迁、断舍离摘要），再让 LLM 基于这些事实写一次文案。
LLM 只负责"怎么说"，不负责"有什么"，因此数字永远来自数据库，失败可降级为规则文案。

个人备案版：报告完全免费，无价格与支付字段；每年生成次数与年度运势报告同样限 3 次。
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from openai import OpenAI
from psycopg2.extras import RealDictCursor

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.core.retry import llm_retry
from apps.api.core.time_utils import today_cn
from apps.api.services.llm_usage_service import extract_llm_usage, log_llm_usage

logger = logging.getLogger(__name__)

# 每年最多生成次数（与 fortune 路由的 ANNUAL_REPORT_YEARLY_LIMIT 对齐）
WARDROBE_REPORT_YEARLY_LIMIT = 3

_MONTH_LABELS = [
    "一月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月",
]


@llm_retry(max_attempts=2, min_wait=1.0, max_wait=3.0)
def _chat_with_retry(client: OpenAI, model: str, prompt: str):
    """带指数退避重试的报告文案调用（网络抖动/限流重试 1 次，仍失败交由上层降级）"""
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1200,
    )


def _year_bounds(year: int) -> tuple[date, date]:
    """[当年 1 月 1 日, 次年 1 月 1 日)，用半开区间替代 EXTRACT 以便走索引"""
    return date(year, 1, 1), date(year + 1, 1, 1)


def _count_query(user_id: int, start: date, end: date) -> Dict[str, Any]:
    """衣橱总量 + 今年新增 + 收藏数（只统计活跃衣物，断舍离处理过的不计入）"""
    query = """
        SELECT
            COUNT(*) AS total_items,
            COUNT(*) FILTER ( WHERE created_at >= %s AND created_at < %s ) AS new_this_year,
            COUNT(*) FILTER ( WHERE wear_count > 0 ) AS ever_worn_items,
            COUNT(*) FILTER ( WHERE is_favorite ) AS favorite_items
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [start, end, user_id])
            row = cur.fetchone()
    return dict(row) if row else {}


def _top_worn_query(user_id: int, start: date, end: date) -> Optional[Dict[str, Any]]:
    """当年日记里出现次数最多的一件（穿着事实以 outfit_diaries 为唯一通路）"""
    query = """
        SELECT w.id, w.name, w.category, w.image_url, w.primary_element,
               COUNT(*) AS wear_times
        FROM diary_outfit_items doi
        JOIN outfit_diaries od ON od.id = doi.diary_id
        JOIN user_wardrobe w ON w.id = doi.wardrobe_item_id
        WHERE od.user_id = %s AND od.diary_date >= %s AND od.diary_date < %s
          AND doi.wardrobe_item_id IS NOT NULL
        GROUP BY w.id, w.name, w.category, w.image_url, w.primary_element
        ORDER BY wear_times DESC, w.id ASC
        LIMIT 1
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id, start, end])
            row = cur.fetchone()
    return dict(row) if row else None


def _worn_span_query(user_id: int, start: date, end: date) -> Dict[str, Any]:
    """当年记录套数、涉及单品件数、最常记录的场合"""
    query = """
        SELECT
            COUNT(*) AS diary_count,
            COUNT(DISTINCT doi.wardrobe_item_id) AS worn_item_count,
            MODE() WITHIN GROUP ( ORDER BY od.occasion ) AS top_occasion
        FROM outfit_diaries od
        LEFT JOIN diary_outfit_items doi ON doi.diary_id = od.id
        WHERE od.user_id = %s AND od.diary_date >= %s AND od.diary_date < %s
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id, start, end])
            row = cur.fetchone()
    return dict(row) if row else {}


def _idle_item_query(user_id: int) -> Optional[Dict[str, Any]]:
    """最久未动的一件：按 last_worn_date（缺失回落 created_at）升序取第一"""
    query = """
        SELECT id, name, category, image_url, primary_element, wear_count,
               last_worn_date, created_at
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE
        ORDER BY COALESCE(last_worn_date, created_at)::date ASC
        LIMIT 1
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id])
            row = cur.fetchone()
    return dict(row) if row else None


def _element_wear_query(user_id: int, start: date, end: date) -> List[Dict[str, Any]]:
    """当年各五行穿着次数（本命色依据）；无日记时由调用方回落累计 wear_count"""
    query = """
        SELECT w.primary_element AS element, COUNT(*) AS times
        FROM diary_outfit_items doi
        JOIN outfit_diaries od ON od.id = doi.diary_id
        JOIN user_wardrobe w ON w.id = doi.wardrobe_item_id
        WHERE od.user_id = %s AND od.diary_date >= %s AND od.diary_date < %s
          AND doi.wardrobe_item_id IS NOT NULL AND w.primary_element IS NOT NULL
        GROUP BY w.primary_element
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id, start, end])
            return [dict(r) for r in cur.fetchall()]


def _element_stock_query(user_id: int) -> List[Dict[str, Any]]:
    """活跃衣橱各五行累计穿着次数（日记为空时的兜底权重）"""
    query = """
        SELECT primary_element AS element, COALESCE(SUM(wear_count), 0) AS times
        FROM user_wardrobe
        WHERE user_id = %s AND is_active = TRUE AND primary_element IS NOT NULL
        GROUP BY primary_element
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id])
            return [dict(r) for r in cur.fetchall()]


def _monthly_element_query(user_id: int, start: date, end: date) -> List[Dict[str, Any]]:
    """按月 × 五行的穿着次数（五行变迁曲线）"""
    query = """
        SELECT EXTRACT(MONTH FROM od.diary_date)::int AS month,
               w.primary_element AS element,
               COUNT(*) AS times
        FROM diary_outfit_items doi
        JOIN outfit_diaries od ON od.id = doi.diary_id
        JOIN user_wardrobe w ON w.id = doi.wardrobe_item_id
        WHERE od.user_id = %s AND od.diary_date >= %s AND od.diary_date < %s
          AND doi.wardrobe_item_id IS NOT NULL AND w.primary_element IS NOT NULL
        GROUP BY month, w.primary_element
        ORDER BY month ASC
    """
    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [user_id, start, end])
            return [dict(r) for r in cur.fetchall()]


def collect_stats(user_id: int, year: int) -> Dict[str, Any]:
    """
    聚合某年度的穿着事实（全部为数据库真值，LLM 不参与计算）

    单条 SQL 失败不影响其他指标：每段查询独立 try/except，缺项用空值占位，
    这样某张表异常时报告仍能生成，而不是整体失败。
    """
    start, end = _year_bounds(year)
    today = today_cn()

    stats: Dict[str, Any] = {
        "year": year,
        "total_items": 0,
        "new_this_year": 0,
        "ever_worn_items": 0,
        "favorite_items": 0,
        "diary_count": 0,
        "worn_this_year": 0,
        "top_occasion": None,
        "top_worn_item": None,
        "idle_item": None,
        "lucky_element": None,
        "lucky_element_times": 0,
        "element_weights": [],
        "monthly_elements": [],
        "declutter": {"total_processed": 0, "summary": ""},
        "is_empty": True,
    }

    try:
        counts = _count_query(user_id, start, end)
        stats["total_items"] = int(counts.get("total_items") or 0)
        stats["new_this_year"] = int(counts.get("new_this_year") or 0)
        stats["ever_worn_items"] = int(counts.get("ever_worn_items") or 0)
        stats["favorite_items"] = int(counts.get("favorite_items") or 0)
    except Exception as e:
        logger.error(f"[WardrobeReport] 衣橱总量聚合失败: {e}")

    try:
        span = _worn_span_query(user_id, start, end)
        stats["diary_count"] = int(span.get("diary_count") or 0)
        stats["worn_this_year"] = int(span.get("worn_item_count") or 0)
        occasion = span.get("top_occasion")
        stats["top_occasion"] = occasion or None
    except Exception as e:
        logger.error(f"[WardrobeReport] 年度跨度聚合失败: {e}")

    try:
        top = _top_worn_query(user_id, start, end)
        if top:
            stats["top_worn_item"] = {
                "id": top["id"],
                "name": top.get("name") or "未命名衣物",
                "category": top.get("category"),
                "image_url": top.get("image_url"),
                "primary_element": top.get("primary_element"),
                "wear_times": int(top.get("wear_times") or 0),
            }
    except Exception as e:
        logger.error(f"[WardrobeReport] 最常穿单品查询失败: {e}")

    try:
        idle = _idle_item_query(user_id)
        if idle:
            base = idle.get("last_worn_date") or idle.get("created_at")
            base_date = _to_date(base)
            stats["idle_item"] = {
                "id": idle["id"],
                "name": idle.get("name") or "未命名衣物",
                "category": idle.get("category"),
                "image_url": idle.get("image_url"),
                "primary_element": idle.get("primary_element"),
                "wear_count": int(idle.get("wear_count") or 0),
                "last_worn": str(base_date) if base_date else None,
                "idle_days": max(0, (today - base_date).days) if base_date else None,
            }
    except Exception as e:
        logger.error(f"[WardrobeReport] 最久未动单品查询失败: {e}")

    try:
        weights = _element_wear_query(user_id, start, end)
        source = "diary"
        if not weights:
            # 当年没记日记时退回累计穿着次数，避免本命色整块空白
            weights = _element_stock_query(user_id)
            source = "wardrobe"
        weights = [w for w in weights if int(w.get("times") or 0) > 0]
        weights.sort(key=lambda w: int(w["times"]), reverse=True)
        stats["element_weights"] = [
            {"element": w["element"], "times": int(w["times"])} for w in weights
        ]
        stats["element_source"] = source
        if weights:
            stats["lucky_element"] = weights[0]["element"]
            stats["lucky_element_times"] = int(weights[0]["times"])
    except Exception as e:
        logger.error(f"[WardrobeReport] 本命色聚合失败: {e}")

    try:
        rows = _monthly_element_query(user_id, start, end)
        by_month: Dict[int, Dict[str, int]] = {}
        for row in rows:
            month = int(row["month"])
            bucket = by_month.setdefault(month, {})
            bucket[row["element"]] = int(row["times"])
        stats["monthly_elements"] = [
            {
                "month": month,
                "label": _MONTH_LABELS[month - 1],
                "elements": bucket,
                "dominant": max(bucket.items(), key=lambda kv: kv[1])[0] if bucket else None,
            }
            for month, bucket in sorted(by_month.items())
        ]
    except Exception as e:
        logger.error(f"[WardrobeReport] 五行变迁聚合失败: {e}")

    try:
        from apps.api.services.wardrobe_analytics_service import get_declutter_report
        report = get_declutter_report(user_id, year)
        stats["declutter"] = {
            "total_processed": report["total_processed"],
            "max_idle_days": report["max_idle_days"],
            "summary": report["summary"],
        }
    except Exception as e:
        logger.error(f"[WardrobeReport] 断舍离摘要取数失败: {e}")

    stats["is_empty"] = (
        stats["total_items"] == 0
        and stats["diary_count"] == 0
        and stats["declutter"]["total_processed"] == 0
    )
    return stats


class WardrobeReportService:
    """衣橱年度报告生成服务"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )
        self.model = settings.qwen_model

    # ── 限频 / 任务占位 ──────────────────────────────────────────────────────

    def get_quota(self, user_id: int, year: int) -> Dict[str, Any]:
        """当年已用次数与剩余额度（供前端按钮文案与 GET 报告返回）"""
        query = "SELECT generate_count FROM wardrobe_reports WHERE user_id = %s AND report_year = %s"
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [user_id, year])
                    row = cur.fetchone()
        except Exception as e:
            logger.error(f"[WardrobeReport] 额度查询失败: {e}")
            row = None
        used = int(row[0]) if row else 0
        return {
            "year": year,
            "used": used,
            "limit": WARDROBE_REPORT_YEARLY_LIMIT,
            "remaining": max(0, WARDROBE_REPORT_YEARLY_LIMIT - used),
        }

    def acquire_quota(self, user_id: int, year: int) -> Optional[int]:
        """
        占用当年一次生成额度并把记录置为 pending（upsert，覆盖当年内容）。

        额度判定写在 ON CONFLICT ... WHERE 里，检查与自增同一事务完成，避免并发超发。
        返回 None 表示当年额度已用完。
        """
        query = """
            INSERT INTO wardrobe_reports (user_id, report_year, title, content, status, generate_count)
            VALUES (%s, %s, %s, '{}'::jsonb, 'pending', 1)
            ON CONFLICT (user_id, report_year) DO UPDATE
            SET title = EXCLUDED.title,
                status = 'pending',
                generate_count = wardrobe_reports.generate_count + 1,
                updated_at = NOW()
            WHERE wardrobe_reports.generate_count < %s
            RETURNING id
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [user_id, year, f"{year} 年衣橱年度报告", WARDROBE_REPORT_YEARLY_LIMIT])
                row = cur.fetchone()
                conn.commit()
        return int(row[0]) if row else None

    def release_quota(self, user_id: int, year: int) -> None:
        """生成任务入队失败时回退一次额度（不阻断主流程）"""
        query = """
            UPDATE wardrobe_reports
            SET generate_count = GREATEST(generate_count - 1, 0), status = 'failed', updated_at = NOW()
            WHERE user_id = %s AND report_year = %s
        """
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [user_id, year])
                    conn.commit()
        except Exception as e:
            logger.error(f"[WardrobeReport] 额度回退失败: {e}")

    def mark_failed(self, user_id: int, year: int) -> None:
        """worker 生成失败时标记（额度不回退，因为 LLM 调用确实已发生）"""
        query = """
            UPDATE wardrobe_reports SET status = 'failed', updated_at = NOW()
            WHERE user_id = %s AND report_year = %s
        """
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, [user_id, year])
                    conn.commit()
        except Exception as e:
            logger.error(f"[WardrobeReport] 失败状态回写异常: {e}")

    # ── 查询 ────────────────────────────────────────────────────────────────

    def get_report(self, user_id: int, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """取某年度报告（含 pending / failed，前端按 status 决定展示形态）"""
        target_year = int(year) if year else today_cn().year
        query = """
            SELECT id, report_year, title, content, summary, status, generate_count, created_at, updated_at
            FROM wardrobe_reports
            WHERE user_id = %s AND report_year = %s
        """
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, [user_id, target_year])
                    row = cur.fetchone()
        except Exception as e:
            logger.error(f"[WardrobeReport] 报告查询失败: {e}")
            return None
        if not row:
            return None

        content = row["content"]
        if not isinstance(content, dict):
            try:
                content = json.loads(content or "{}")
            except (TypeError, ValueError):
                content = {}
        return {
            "id": row["id"],
            "year": row["report_year"],
            "title": row["title"],
            "content": content,
            "summary": row.get("summary"),
            "status": row["status"],
            "generated": row["status"] == "ready",
            "updated_at": str(row.get("updated_at") or ""),
        }

    # ── 生成（worker 调用） ──────────────────────────────────────────────────

    def generate_report(self, user_id: int, year: int) -> Dict[str, Any]:
        """聚合事实 → 一次 LLM 文案 → 落库为 ready"""
        stats = collect_stats(user_id, year)
        narrative = self._build_narrative(user_id, stats)
        content = {"year": year, "stats": stats, "narrative": narrative}
        title = narrative.get("title") or f"{year} 年衣橱年度报告"
        summary = (narrative.get("overall") or "")[:120]
        report_id = self._save_ready(user_id, year, title, content, summary)
        return {
            "id": report_id,
            "year": year,
            "title": title,
            "content": content,
            "summary": summary,
            "status": "ready",
        }

    def _build_narrative(self, user_id: int, stats: Dict[str, Any]) -> Dict[str, str]:
        """一次 LLM 调用产出文案；空衣橱或调用失败均走规则文案（不记 LLM 成本）"""
        if stats["is_empty"]:
            return self._fallback_narrative(stats)

        prompt = self._build_prompt(stats)
        try:
            response = _chat_with_retry(self.client, self.model, prompt)
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[:-3]
            narrative = json.loads(raw)
            ai_usage = extract_llm_usage(response)
        except Exception as e:
            logger.error(f"[WardrobeReport] AI 文案生成失败，降级规则文案: {e}")
            return self._fallback_narrative(stats)

        if not isinstance(narrative, dict) or not narrative.get("overall"):
            logger.warning("[WardrobeReport] AI 返回结构不可用，降级规则文案")
            return self._fallback_narrative(stats)

        merged = {
            **self._fallback_narrative(stats),
            **{key: str(val).strip() for key, val in narrative.items() if val},
        }
        # 大模型调用明细埋点（仅成功路径，降级不记录）
        log_llm_usage(user_id, "wardrobe_report", None, f"{stats['year']} 年衣橱年度报告", usage=ai_usage)
        return merged

    def _build_prompt(self, stats: Dict[str, Any]) -> str:
        year = stats["year"]
        top = stats["top_worn_item"] or {}
        idle = stats["idle_item"] or {}
        trend = "、".join(
            f"{m['label']}偏{m['dominant']}" for m in stats["monthly_elements"] if m.get("dominant")
        ) or "全年没有明显的元素偏向变化"
        facts = f"""- 活跃衣橱 {stats['total_items']} 件，其中 {year} 年新增 {stats['new_this_year']} 件
- {year} 年记录了 {stats['diary_count']} 套穿搭日记，涉及 {stats['worn_this_year']} 件不同单品
- 今年穿得最多的一件：{top.get('name') or '（无日记记录）'}（{top.get('wear_times', 0)} 次，{top.get('category') or '未分类'}）
- 最久没动的一件：{idle.get('name') or '（衣橱为空）'}（已 {idle.get('idle_days') or 0} 天）
- 本命色（按穿着加权五行 Top1）：{stats['lucky_element'] or '暂无'}（{stats['lucky_element_times']} 次）
- 各五行穿着权重：{json.dumps(stats['element_weights'], ensure_ascii=False)}
- 月度五行变迁：{trend}
- 断舍离：{stats['declutter']['summary']}
- 最常记录的场合：{stats['top_occasion'] or '未标注'}"""

        return f"""你是一位写作用克制、温暖的衣橱编辑。下面是用户 {year} 年的真实穿搭数据，请据此写一份衣橱年度报告文案。

## 数据事实（只能引用这些数字，不得新增或推算任何未给出的数值）
{facts}

## 输出要求
返回 JSON，键名固定为：
- title：12 字以内的报告标题，不要带年份数字
- overall：120 字以内的年度总述，点出这一年的穿搭节奏与本命色
- top_item：60 字以内，写"穿得最多的一件"为什么被反复选择，语气具体不空泛
- idle_item：60 字以内，给"最久没动的一件"一个体面的去处建议（继续穿 / 断舍离二选一，不要劝买新的）
- element_story：80 字以内，围绕本命色说清这一年的色彩偏好，可关联传统五行文化的搭配说法
- trend：60 字以内，概括月度元素变迁读出的一年变化
- advice：80 字以内，给明年一条可执行的小建议（优先"多穿已有"而不是"再添新衣"）

文风约束：表述为生活习惯观察与传统文化参考，不作任何吉凶、健康、运势断言；不出现价格、金额、品牌与购买链接；不使用"亲爱的用户"这类称呼。

直接返回 JSON，不要加 markdown 代码块标记。"""

    def _fallback_narrative(self, stats: Dict[str, Any]) -> Dict[str, str]:
        """AI 不可用时的规则文案（同样可读，数字全部来自 stats）"""
        year = stats["year"]
        if stats["is_empty"]:
            return {
                "title": "衣橱故事还没开始",
                "overall": f"{year} 年还没有留下穿搭记录。先在衣橱里添几件常穿的衣服，或把今天的搭配记一笔，明年这时就有了一份属于你自己的年度报告。",
                "top_item": "还没有记录到反复穿的单品。",
                "idle_item": "衣橱还是空的，谈不上闲置。",
                "element_story": "五行色彩偏好会在你开始记录后逐渐显形。",
                "trend": "暂无月度元素变化可读。",
                "advice": "先从每天出门前记一笔今天穿了什么开始。",
            }

        top = stats["top_worn_item"]
        idle = stats["idle_item"]
        pieces = [f"{year} 年你在衣橱里留下了 {stats['diary_count']} 套穿搭记录"]
        if stats["worn_this_year"]:
            pieces.append(f"真正上身的有 {stats['worn_this_year']} 件")
        if stats["new_this_year"]:
            pieces.append(f"其中 {stats['new_this_year']} 件是今年新添的")
        overall = "，".join(pieces) + "。"
        if stats["lucky_element"]:
            overall += f"穿着加权最高的一行是{stats['lucky_element']}，这也是你今年最顺手的颜色气质。"

        return {
            "title": f"{year} 年的穿搭节奏",
            "overall": overall,
            "top_item": (
                f"「{top['name']}」今年出现了 {top['wear_times']} 次，是你最信得过的选择。"
                if top else "今年还没有单件被反复记录，说明你更偏爱不断轮换。"
            ),
            "idle_item": (
                f"「{idle['name']}」已经 {idle['idle_days']} 天没被动过，再穿一次或者正式告别，都是个体面的选择。"
                if idle and idle.get("idle_days") else "没有一件衣物长期被冷落，衣橱被你照顾得不错。"
            ),
            "element_story": (
                f"本命色落在{stats['lucky_element']}（{stats['lucky_element_times']} 次穿着），"
                "传统五行文化里这一行常被联想到生长与条达，放在穿搭上就是你偏爱的色彩气质。"
                if stats["lucky_element"] else "本命色还需要更多日记记录才能显形。"
            ),
            "trend": (
                "月度元素变迁：" + "、".join(f"{m['label']}偏{m['dominant']}" for m in stats["monthly_elements"] if m.get("dominant")) + "。"
                if stats["monthly_elements"] else "全年元素分布比较平稳，没有明显的季节偏向。"
            ),
            "advice": (
                f"明年可以先把「{top['name']}」之外的常穿件轮换起来，"
                "处理掉长期未动的那件，衣柜会显得比添新衣更满。"
                if top else "明年试着让常穿的几件轮换得更均匀一些。"
            ),
        }

    def _save_ready(
        self, user_id: int, year: int, title: str, content: Dict[str, Any], summary: str
    ) -> Optional[int]:
        """回写报告内容并置为 ready（generate_count 不动，保留限频计数）"""
        query = """
            UPDATE wardrobe_reports
            SET title = %s, content = %s::jsonb, summary = %s, status = 'ready', updated_at = NOW()
            WHERE user_id = %s AND report_year = %s
            RETURNING id
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    [title, json.dumps(content, ensure_ascii=False), summary, user_id, year],
                )
                row = cur.fetchone()
                conn.commit()
        return int(row[0]) if row else None


def _to_date(value: Any) -> Optional[date]:
    """DATE / TIMESTAMP / 字符串统一转 date（timestamp 按北京时间切日）"""
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


# 模块级单例
wardrobe_report_service = WardrobeReportService()
