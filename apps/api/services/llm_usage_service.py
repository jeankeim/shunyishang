"""
后台管理 - 用户大模型调用明细服务

职责：
1. 大模型调用日志落库（user_daily_llm_usage，usage_date 按北京自然日）
2. 明细查询：按用户分组聚合，支持近 N 天 / 单日 / 昵称·ID 关键词过滤
3. 成本核算：捕获 DashScope 返回的 token usage，按模型单价折算调用成本

埋点原则：仅在真实发起大模型调用的路径记录（缓存命中不记录）。
成本 = token 用量 × 模型单价（MODEL_PRICING_PER_1K）；图片生成成本
image_cost 为预留字段（当前在线链路无付费图片生成，wanx 文生图仅离线脚本）。
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# DashScope wanx2.1-t2i-turbo 文生图单价（元/张，参考官网定价，调整时同步更新）
IMAGE_COST_PER_WANX_IMAGE = 0.14

# DashScope 模型单价（元/千 token，参考阿里云百炼官网国内定价，调整时同步更新）
MODEL_PRICING_PER_1K: Dict[str, Tuple[float, float]] = {
    "qwen-max": (0.0024, 0.0096),
    "qwen-plus": (0.0008, 0.002),
    "qwen-turbo": (0.0003, 0.0006),
    "qwen-vl-max": (0.0016, 0.004),
    "qwen-vl-plus": (0.0008, 0.002),
}
# 未知模型兜底单价（按 qwen-plus 计）
DEFAULT_PRICING_PER_1K: Tuple[float, float] = (0.0008, 0.002)


def _pricing_for_model(model: Optional[str]) -> Tuple[float, float]:
    """按模型名取单价（兼容带日期后缀的模型 ID，如 qwen-plus-2025-12-01）"""
    if model:
        if model in MODEL_PRICING_PER_1K:
            return MODEL_PRICING_PER_1K[model]
        for prefix, pricing in MODEL_PRICING_PER_1K.items():
            if model.startswith(prefix):
                return pricing
    return DEFAULT_PRICING_PER_1K


def calc_llm_cost(
    model: Optional[str],
    input_tokens: Optional[int],
    output_tokens: Optional[int],
) -> float:
    """按模型单价折算调用成本（元），无 token 用量时为 0"""
    it = int(input_tokens or 0)
    ot = int(output_tokens or 0)
    if it <= 0 and ot <= 0:
        return 0.0
    pi, po = _pricing_for_model(model)
    return round((it * pi + ot * po) / 1000.0, 6)


def extract_llm_usage(response: Any) -> Optional[Dict[str, Any]]:
    """
    从 DashScope/OpenAI 响应（含流式 chunk）安全提取 token 用量。

    Returns:
        {model, input_tokens, output_tokens}；无 usage 或字段非整数时返回 None
    """
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        if not isinstance(prompt, int) or not isinstance(completion, int):
            return None
        model = getattr(response, "model", None)
        return {
            "model": str(model) if model else None,
            "input_tokens": prompt,
            "output_tokens": completion,
        }
    except Exception:
        return None


def merge_llm_usage(
    prev: Optional[Dict[str, Any]],
    usage: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """累加多次调用的 token 用量（同一次请求内多个 LLM 调用合计）"""
    if not usage:
        return dict(prev) if prev else None
    merged = dict(prev) if prev else {}
    merged["input_tokens"] = int(merged.get("input_tokens") or 0) + int(usage.get("input_tokens") or 0)
    merged["output_tokens"] = int(merged.get("output_tokens") or 0) + int(usage.get("output_tokens") or 0)
    if not merged.get("model") and usage.get("model"):
        merged["model"] = usage["model"]
    return merged


def log_llm_usage(
    user_id: Optional[int],
    scene: str,
    query_text: Optional[str] = None,
    result_summary: Optional[str] = None,
    image_cost: float = 0.0,
    usage: Optional[Dict[str, Any]] = None,
) -> None:
    """记录一次大模型调用（失败静默，绝不影响主流程）

    Args:
        usage: extract_llm_usage 提取的 {model, input_tokens, output_tokens}，
               用于折算 llm_cost；缺失时成本记 0
    """
    if not user_id:
        return
    usage = usage or {}
    model = usage.get("model")
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    llm_cost = calc_llm_cost(model, input_tokens, output_tokens)
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_daily_llm_usage
                        (user_id, usage_date, scene, query_text, result_summary,
                         image_cost, model, input_tokens, output_tokens, llm_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        today_cn(),
                        (scene or "")[:50] or None,
                        (query_text or "")[:500] or None,
                        (result_summary or "")[:500] or None,
                        image_cost or 0,
                        (model or "")[:50] or None,
                        int(input_tokens) if isinstance(input_tokens, int) else None,
                        int(output_tokens) if isinstance(output_tokens, int) else None,
                        llm_cost,
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.debug(f"[LLMUsage] 调用日志写入失败（静默）: {e}")


def get_llm_usage(
    days: int = 7,
    date_str: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Dict[str, Any]:
    """
    查询大模型调用明细（按用户分组）

    Args:
        days: 默认近 N 天（含今天）
        date_str: 单日筛选 YYYY-MM-DD（优先于 days）
        keyword: 按昵称模糊 / 用户ID精确 过滤

    Returns:
        {range, totals{call_count,user_count,llm_cost,image_cost,cost},
         users[{...用户信息, cost, records[]}]}（cost = llm_cost + image_cost）
    """
    today = today_cn()
    if date_str:
        try:
            start = end = date.fromisoformat(date_str)
        except ValueError:
            start = end = today
    else:
        end = today
        start = today - timedelta(days=max(1, min(days, 90)) - 1)

    params: List[Any] = [start, end]
    user_filter = ""
    kw = (keyword or "").strip()
    if kw:
        user_filter = " AND (u.nickname ILIKE %s OR u.id::text = %s)"
        params.extend([f"%{kw}%", kw])

    query = f"""
        SELECT l.id, l.user_id, l.usage_date, l.scene, l.query_text,
               l.result_summary, l.image_cost, l.created_at,
               l.model, l.input_tokens, l.output_tokens, l.llm_cost,
               u.nickname, u.created_at AS user_created_at, u.preferred_city
        FROM user_daily_llm_usage l
        JOIN users u ON u.id = l.user_id
        WHERE l.usage_date BETWEEN %s AND %s{user_filter}
        ORDER BY l.created_at DESC, l.id DESC
    """

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    # 按用户分组聚合
    groups: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        uid = row["user_id"]
        g = groups.get(uid)
        if g is None:
            g = groups[uid] = {
                "user_id": uid,
                "nickname": row["nickname"] or f"用户{uid}",
                "created_at": row["user_created_at"].isoformat() if row["user_created_at"] else None,
                "city": row["preferred_city"] or None,
                "call_count": 0,
                "image_cost": 0.0,
                "llm_cost": 0.0,
                "cost": 0.0,
                "scenes": set(),
                "records": [],
            }
        g["call_count"] += 1
        row_llm_cost = float(row["llm_cost"] or 0)
        row_image_cost = float(row["image_cost"] or 0)
        g["image_cost"] += row_image_cost
        g["llm_cost"] += row_llm_cost
        g["cost"] += row_llm_cost + row_image_cost
        g["scenes"].add(row["scene"])
        g["records"].append({
            "id": row["id"],
            "date": row["usage_date"].isoformat(),
            "scene": row["scene"],
            "query_text": row["query_text"],
            "result_summary": row["result_summary"],
            "image_cost": row_image_cost,
            "model": row["model"],
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "llm_cost": row_llm_cost,
            "cost": round(row_llm_cost + row_image_cost, 6),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    users = sorted(groups.values(), key=lambda g: (-g["call_count"], g["user_id"]))
    for g in users:
        g["image_cost"] = round(g["image_cost"], 4)
        g["llm_cost"] = round(g["llm_cost"], 4)
        g["cost"] = round(g["cost"], 4)
        g["scenes"] = sorted(g["scenes"])

    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "totals": {
            "call_count": len(rows),
            "user_count": len(users),
            "llm_cost": round(sum(g["llm_cost"] for g in users), 4),
            "image_cost": round(sum(g["image_cost"] for g in users), 4),
            "cost": round(sum(g["cost"] for g in users), 4),
        },
        "users": users,
    }
