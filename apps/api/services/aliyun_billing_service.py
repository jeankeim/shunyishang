"""
后台管理 - 阿里云费用账单服务

通过阿里云 BSS OpenAPI 按天拉取全产品账单落库并提供汇总查询：
1. QueryAccountBill(is_group_by_product=True)  → aliyun_daily_bills（产品粒度）
2. DescribeInstanceBill(is_billing_item=True)   → aliyun_daily_bill_items（计费项粒度）
   拆到「实例规格 / 存储 / 大模型文本消耗量」这一层，含单价与服务周期，
   用于回答"每天的钱具体花在哪台机器上"以及按量与包年包月孰优孰劣。

AK 要求：RAM 子账号仅授予 AliyunBSSReadOnlyAccess 只读权限即可。
账单延迟说明：阿里云当天账单通常次日才出全，因此同步范围默认截至 D-1，
且每次同步回刷最近 3 天以覆盖延迟更新。
计费项明细属增强数据：拉取失败仅告警并计入 errors，不影响产品级账单主链路。
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_BSS_ENDPOINT = "business.aliyuncs.com"

# 月均折算基准天数（取 365/12，避免按 30/31 天波动导致跨月不可比）
_DAYS_PER_MONTH = 365 / 12

# 单日同主键多行合并时，描述件跟随“金额最大的一笔”（金额类字段是累加）
_DESCRIPTIVE_FIELDS = (
    "product_name", "instance_spec", "nick_name", "region", "instance_config",
    "list_price", "list_price_unit", "usage_unit", "service_period",
    "service_period_unit", "service_months",
)


def _to_float(value: Any, default: float = 0.0) -> float:
    """BSS 返回字段多为字符串且可能为空，统一安全转 float"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    """同上，用于 service_period 这类"数值+单位"中的数值部分"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _build_client():
    """懒加载构建 BSS 客户端（未安装 SDK 或未配置 AK 时抛出明确异常）"""
    if not settings.billing_configured:
        raise RuntimeError("未配置阿里云账单 AK（ALIYUN_BILLING_ACCESS_KEY_ID/SECRET）")
    try:
        from alibabacloud_bssopenapi20171214.client import Client as BssClient
        from alibabacloud_tea_openapi import models as open_api_models
    except ImportError as e:
        raise RuntimeError(
            "缺少阿里云账单 SDK，请先安装: pip install alibabacloud_bssopenapi20171214"
        ) from e

    config = open_api_models.Config(
        access_key_id=settings.aliyun_billing_access_key_id,
        access_key_secret=settings.aliyun_billing_access_key_secret,
        endpoint=_BSS_ENDPOINT,
    )
    return BssClient(config)


def _query_day_bills(client, bill_date: date) -> List[Dict[str, Any]]:
    """查询指定日期的全产品账单（PageNum/PageSize 分页自动翻页）"""
    from alibabacloud_bssopenapi20171214 import models as bss_models

    results: List[Dict[str, Any]] = []
    page_num = 1
    page_size = 300
    while True:
        request = bss_models.QueryAccountBillRequest(
            billing_cycle=bill_date.strftime("%Y-%m"),
            granularity="DAILY",
            billing_date=bill_date.isoformat(),
            is_group_by_product=True,
            page_num=page_num,
            page_size=page_size,
        )
        resp = client.query_account_bill(request)
        data = resp.body.data
        if data is None or data.items is None:
            break
        for it in data.items.item or []:
            results.append(
                {
                    "product_code": it.product_code or "unknown",
                    "product_name": it.product_name or "",
                    "subscription_type": it.subscription_type or "",
                    "pretax_amount": float(it.pretax_amount or 0),
                    "payment_amount": float(it.payment_amount or 0),
                    "deducted_by_coupons": float(it.deducted_by_coupons or 0),
                }
            )
        # 翻页判断：已拉取条数 ≥ 总条数则结束
        total_count = getattr(data, "total_count", None) or 0
        if len(results) >= total_count or not (data.items.item):
            break
        page_num += 1
    return results


def _upsert_day_bills(bill_date: date, rows: List[Dict[str, Any]]) -> int:
    """UPSERT 单日账单，返回写入行数"""
    if not rows:
        return 0
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO aliyun_daily_bills
                        (bill_date, product_code, product_name, subscription_type,
                         pretax_amount, payment_amount, deducted_by_coupons, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (bill_date, product_code, subscription_type) DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        pretax_amount = EXCLUDED.pretax_amount,
                        payment_amount = EXCLUDED.payment_amount,
                        deducted_by_coupons = EXCLUDED.deducted_by_coupons,
                        updated_at = NOW()
                    """,
                    (
                        bill_date,
                        row["product_code"],
                        row["product_name"],
                        row["subscription_type"],
                        row["pretax_amount"],
                        row["payment_amount"],
                        row["deducted_by_coupons"],
                    ),
                )
        conn.commit()
    return len(rows)


def _query_day_bill_items(client, bill_date: date) -> List[Dict[str, Any]]:
    """
    按计费项/实例粒度查询单日账单（NextToken 分页）

    同一主键（产品+订阅类型+实例+计费项）被 API 拆成多行时（如百炼多个模型、
    同实例多档用量、预付费新购+退款）在内存合并金额，避免逐行写库放大行数。
    """
    from alibabacloud_bssopenapi20171214 import models as bss_models

    merged: Dict[tuple, Dict[str, Any]] = {}
    next_token = None
    while True:
        request = bss_models.DescribeInstanceBillRequest(
            billing_cycle=bill_date.strftime("%Y-%m"),
            granularity="DAILY",
            billing_date=bill_date.isoformat(),
            is_billing_item=True,
            max_results=300,
            next_token=next_token,
        )
        resp = client.describe_instance_bill(request)
        data = resp.body.data
        items = getattr(data, "items", None) or []
        for it in items:
            row = {
                "product_code": it.product_code or "unknown",
                "product_name": it.product_name or "",
                "subscription_type": it.subscription_type or "",
                "instance_id": (it.instance_id or "")[:160],
                "billing_item_code": (it.billing_item_code or "")[:48],
                "billing_item": (it.billing_item or "")[:96],
                "instance_spec": (it.instance_spec or "")[:64],
                "nick_name": (it.nick_name or "")[:128],
                "region": (it.region or "")[:64],
                "instance_config": it.instance_config or "",
                "list_price": str(it.list_price or "")[:32],
                "list_price_unit": (it.list_price_unit or "")[:32],
                "usage_qty": _to_float(it.usage),
                "usage_unit": (it.usage_unit or "")[:32],
                "service_period": _to_int(it.service_period),
                "service_period_unit": (it.service_period_unit or "")[:16],
                "service_months": _to_months(
                    _to_int(it.service_period), it.service_period_unit or ""
                ),
                "pretax_amount": _to_float(it.pretax_amount),
                "payment_amount": _to_float(it.payment_amount),
                "deducted_by_coupons": _to_float(it.deducted_by_coupons),
            }
            # 单笔金额先行落定，后续合并只取更大的那一笔
            row["max_single_amount"] = row["pretax_amount"]
            key = (
                row["product_code"],
                row["subscription_type"],
                row["instance_id"],
                row["billing_item_code"],
                row["billing_item"],
            )
            exist = merged.get(key)
            if exist is None:
                merged[key] = row
                continue
            for field in ("usage_qty", "pretax_amount", "payment_amount", "deducted_by_coupons"):
                exist[field] += row[field]
            # 描述件取“金额最大的一笔”：退款行的单价为空、服务周期是
            # 退订剩余天数，混进来会把折算月均带偏
            if row["max_single_amount"] > exist["max_single_amount"]:
                exist["max_single_amount"] = row["max_single_amount"]
                for field in _DESCRIPTIVE_FIELDS:
                    exist[field] = row[field]
        next_token = getattr(data, "next_token", None)
        if not items or not next_token:
            break
    return list(merged.values())


def _upsert_day_bill_items(bill_date: date, rows: List[Dict[str, Any]]) -> int:
    """UPSERT 单日计费项明细，返回写入行数"""
    if not rows:
        return 0
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO aliyun_daily_bill_items
                        (bill_date, product_code, product_name, subscription_type,
                         instance_id, billing_item_code, billing_item,
                         instance_spec, nick_name, region, instance_config,
                         list_price, list_price_unit, usage_qty, usage_unit,
                         service_period, service_period_unit, service_months,
                         pretax_amount, max_single_amount,
                         payment_amount, deducted_by_coupons, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (bill_date, product_code, subscription_type,
                                 instance_id, billing_item_code, billing_item) DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        instance_spec = EXCLUDED.instance_spec,
                        nick_name = EXCLUDED.nick_name,
                        region = EXCLUDED.region,
                        instance_config = EXCLUDED.instance_config,
                        list_price = EXCLUDED.list_price,
                        list_price_unit = EXCLUDED.list_price_unit,
                        usage_qty = EXCLUDED.usage_qty,
                        usage_unit = EXCLUDED.usage_unit,
                        service_period = EXCLUDED.service_period,
                        service_period_unit = EXCLUDED.service_period_unit,
                        service_months = EXCLUDED.service_months,
                        pretax_amount = EXCLUDED.pretax_amount,
                        max_single_amount = EXCLUDED.max_single_amount,
                        payment_amount = EXCLUDED.payment_amount,
                        deducted_by_coupons = EXCLUDED.deducted_by_coupons,
                        updated_at = NOW()
                    """,
                    (
                        bill_date,
                        row["product_code"],
                        row["product_name"],
                        row["subscription_type"],
                        row["instance_id"],
                        row["billing_item_code"],
                        row["billing_item"],
                        row["instance_spec"],
                        row["nick_name"],
                        row["region"],
                        row["instance_config"],
                        row["list_price"],
                        row["list_price_unit"],
                        row["usage_qty"],
                        row["usage_unit"],
                        row["service_period"],
                        row["service_period_unit"],
                        row["service_months"],
                        row["pretax_amount"],
                        row["max_single_amount"],
                        row["payment_amount"],
                        row["deducted_by_coupons"],
                    ),
                )
        conn.commit()
    return len(rows)


def sync_bills(days: int = 3) -> Dict[str, Any]:
    """
    从阿里云拉取最近 N 天账单并落库（幂等 UPSERT）

    默认回刷 D-1 ~ D-N（当天账单未出），手动触发可传更大 days 做历史回填。
    每天先同步产品级账单（主链路），成功后再同步计费项明细（增强链路）。
    """
    client = _build_client()
    today = today_cn()
    synced_days = 0
    synced_rows = 0
    synced_item_rows = 0
    errors: List[str] = []

    for i in range(1, days + 1):
        d = today - timedelta(days=i)
        try:
            rows = _query_day_bills(client, d)
            _upsert_day_bills(d, rows)
            synced_days += 1
            synced_rows += len(rows)
        except Exception as e:
            logger.error(f"[AliyunBill] 同步 {d} 账单失败: {e}")
            errors.append(f"{d.isoformat()}: {str(e)[:200]}")
            continue

        # 计费项下钻独立容错：失败不回退已成功的账单主数据
        try:
            item_rows = _query_day_bill_items(client, d)
            synced_item_rows += _upsert_day_bill_items(d, item_rows)
        except Exception as e:
            logger.warning(f"[AliyunBill] 同步 {d} 计费项明细失败（不影响账单主数据）: {e}")
            errors.append(f"{d.isoformat()} 计费项明细: {str(e)[:150]}")

    return {
        "synced_days": synced_days,
        "synced_rows": synced_rows,
        "synced_item_rows": synced_item_rows,
        "errors": errors,
        "synced_at": today_cn().isoformat(),
    }


def get_bill_summary(days: int = 31) -> Dict[str, Any]:
    """账单汇总：近 N 天总额 + 按产品分类 + 每日趋势"""
    days = max(1, min(days, 366))
    today = today_cn()
    start = today - timedelta(days=days - 1)

    configured = settings.billing_configured
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            # 最后同步时间（取表内最大 updated_at）
            cur.execute("SELECT MAX(updated_at) FROM aliyun_daily_bills")
            row = cur.fetchone()
            last_sync_at = str(row[0]) if row and row[0] else None

            # 区间内按产品聚合
            cur.execute(
                """
                SELECT product_code,
                       MAX(product_name) AS product_name,
                       SUM(pretax_amount)::float AS pretax_amount,
                       SUM(payment_amount)::float AS payment_amount,
                       SUM(deducted_by_coupons)::float AS deducted_by_coupons
                FROM aliyun_daily_bills
                WHERE bill_date >= %s AND bill_date <= %s
                GROUP BY product_code
                ORDER BY SUM(pretax_amount) DESC
                """,
                (start, today),
            )
            by_product = [
                {
                    "product_code": r[0],
                    "product_name": r[1] or r[0],
                    "pretax_amount": round(r[2] or 0, 4),
                    "payment_amount": round(r[3] or 0, 4),
                    "deducted_by_coupons": round(r[4] or 0, 4),
                }
                for r in cur.fetchall()
            ]

            # 每日趋势
            cur.execute(
                """
                SELECT bill_date,
                       SUM(pretax_amount)::float,
                       SUM(payment_amount)::float
                FROM aliyun_daily_bills
                WHERE bill_date >= %s AND bill_date <= %s
                GROUP BY bill_date
                ORDER BY bill_date
                """,
                (start, today),
            )
            daily_map = {r[0]: (r[1] or 0, r[2] or 0) for r in cur.fetchall()}

    total_pretax = round(sum(p["pretax_amount"] for p in by_product), 4)
    total_payment = round(sum(p["payment_amount"] for p in by_product), 4)

    # 占比（按应付金额）
    for p in by_product:
        p["percentage"] = round(p["pretax_amount"] / total_pretax * 100, 1) if total_pretax else 0

    daily = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "pretax_amount": round(daily_map.get(start + timedelta(days=i), (0, 0))[0], 4),
            "payment_amount": round(daily_map.get(start + timedelta(days=i), (0, 0))[1], 4),
        }
        for i in range(days)
    ]

    return {
        "configured": configured,
        "range": {"start": start.isoformat(), "end": today.isoformat(), "days": days},
        "total_pretax": total_pretax,
        "total_payment": total_payment,
        "by_product": by_product,
        "daily": daily,
        "last_sync_at": last_sync_at,
    }


def _to_months(service_period: int, unit: str) -> float:
    """预付费服务周期折算为月数（单位无法识别时返回 0，表示不可折算）"""
    if service_period <= 0:
        return 0.0
    u = (unit or "").strip()
    low = u.lower()
    if "秒" in u or low in ("second", "s"):
        return service_period / 86400.0 / _DAYS_PER_MONTH
    if "天" in u or low in ("day", "d"):
        return service_period / _DAYS_PER_MONTH
    if "月" in u or low in ("month", "m"):
        return float(service_period)
    if "年" in u or low in ("year", "y"):
        return service_period * 12.0
    return 0.0


def _monthly_cost(
    *,
    subscription_type: str,
    pretax_amount: float,
    max_single_amount: float,
    service_months: float,
    recent_amount: float,
    recent_divisor: int,
) -> float:
    """
    折算月均成本（元/月）—— 回答“照现在的用法，这项一个月要花多少”

    - 预付费：单笔最大支付额 ÷ 服务月数（两者均已在入库时按“金额最大的一笔”对齐）。
      不取区间净额，是因为退订会在同一天留下负数行：RDS 包月新购 +156 元与退款
      -150.98 元合并后只剩 5.02 元，会把 156 元/月的真实合同价算成几元。
    - 按量：取最近窗口日均 × 月基准天数。用近期窗口而非整个查询区间，是因为
      区间里混着已停项与一次性跑批（如 8-23 生图 45 元只出账 1 天），按区间
      摊分会同时出现“停掉的项还算出月成本”和“跑批被夸大成月成本”两类错误。
    """
    if subscription_type == "Subscription":
        amount = max_single_amount if max_single_amount > 0 else pretax_amount
        return round(amount / service_months, 2) if service_months > 0 and amount > 0 else 0.0
    if recent_amount <= 0:
        return 0.0
    return round(recent_amount / max(recent_divisor, 1) * _DAYS_PER_MONTH, 2)


def _instance_label(nick_name: str, instance_id: str) -> str:
    """
    提炼实例的可读标识

    优先取实例别名（如 RDS 的 wuxingclothes）；无别名时取 instance_id 中末尾
    最多两段“非纯数字”段——百炼形如
    `2296674;llm-5tn5lih7ge4pzzxy;qwen-plus;input_token;;0`，拼出
    `qwen-plus · input_token`（模型名 + token 类型，正好是计费区分维度）；
    OSS `cn-hangzhou;standard-zrs` → `cn-hangzhou · standard-zrs`；
    ECS `i-bp17448hpb5wvq5d64hc` → 原值。
    """
    if nick_name:
        return nick_name
    parts = [p for p in (instance_id or "").split(";") if p and not p.isdigit()]
    return " · ".join(parts[-2:]) if parts else (instance_id or "")


# 区间内按「产品 × 订阅类型 × 实例 × 计费项」聚合（billing_item_code 与计费项名一一对应）
_BILL_ITEMS_SQL = """
    SELECT product_code,
           MAX(product_name)                AS product_name,
           subscription_type,
           instance_id,
           billing_item_code,
           MAX(billing_item)                AS billing_item,
           MAX(instance_spec)               AS instance_spec,
           MAX(nick_name)                   AS nick_name,
           MAX(region)                      AS region,
           MAX(list_price)                  AS list_price,
           MAX(list_price_unit)             AS list_price_unit,
           SUM(usage_qty)::float            AS usage_qty,
           MAX(usage_unit)                  AS usage_unit,
           SUM(pretax_amount)::float        AS pretax_amount,
           MAX(max_single_amount)::float    AS max_single_amount,
           -- 只取“当日有正额支付”那些天的周期：若退款单独成天（周期是退订剩余
           -- 天数），直接 MAX 会把 1 月合同算成 1.05 月而压低月均
           COALESCE(MAX(service_months) FILTER (WHERE max_single_amount > 0), 0)::float
                                            AS service_months,
           SUM(payment_amount)::float       AS payment_amount,
           SUM(deducted_by_coupons)::float  AS deducted_by_coupons,
           COUNT(DISTINCT bill_date)        AS bill_days
    FROM aliyun_daily_bill_items
    WHERE bill_date >= %s AND bill_date <= %s
    GROUP BY product_code, subscription_type, instance_id, billing_item_code
    ORDER BY SUM(pretax_amount) DESC
"""

# 按量月折算的近期窗口天数（截至昨日，当天账单未出全）
_RECENT_WINDOW_DAYS = 7


def _item_key(row: Dict[str, Any]) -> tuple:
    """主查询与近期窗口查询的对齐键（与 GROUP BY 列一致）"""
    return (
        row["product_code"],
        row["subscription_type"] or "",
        row["instance_id"] or "",
        row["billing_item_code"] or "",
    )


def get_bill_items(days: int = 31) -> Dict[str, Any]:
    """
    计费项下钻明细：区间内按产品分组展示到实例/计费项粒度

    Returns:
        {range, has_detail, covered_days, monthly_basis_days,
         products[{product_code, product_name, pretax_amount,
         items[{...计费项字段, bill_days, monthly_cost, percentage}]}]}
        percentage 为该计费项占所属产品应付金额的比例；monthly_cost 是“按最近
        monthly_basis_days 天用法折算的月成本”，已停项与一次性跑批会为 0；
        covered_days 为区间内明细实际覆盖天数；has_detail=False 表示明细表在
        该区间无数据（早于上线的历史区间），前端据此提示回填。
    """
    days = max(1, min(days, 366))
    today = today_cn()
    start = today - timedelta(days=days - 1)
    recent_start = today - timedelta(days=_RECENT_WINDOW_DAYS)
    recent_end = today - timedelta(days=1)

    with DatabasePool.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_BILL_ITEMS_SQL, (start, today))
            rows = cur.fetchall()

            cur.execute(
                "SELECT COUNT(DISTINCT bill_date) AS covered FROM aliyun_daily_bill_items "
                "WHERE bill_date >= %s AND bill_date <= %s",
                (start, today),
            )
            covered_days = int((cur.fetchone() or {}).get("covered") or 0)

            # 按量月折算基准：最近窗口内各计费项的金额。窗口实际覆盖天数不足 7 天
            # 时按实际天数作分母，避免刚回填（只有 3 天明细）时用 7 除把成本算低
            cur.execute(
                "SELECT product_code, subscription_type, instance_id, billing_item_code, "
                "       SUM(pretax_amount)::float AS recent_amount, "
                "       COUNT(DISTINCT bill_date) AS recent_covered "
                "FROM aliyun_daily_bill_items "
                "WHERE bill_date >= %s AND bill_date <= %s "
                "GROUP BY 1, 2, 3, 4",
                (recent_start, recent_end),
            )
            recent_rows = cur.fetchall()

    recent_map: Dict[tuple, float] = {}
    recent_covered = 0
    for r in recent_rows:
        recent_map[_item_key(r)] = r["recent_amount"] or 0.0
        recent_covered = max(recent_covered, int(r["recent_covered"] or 0))
    recent_divisor = min(max(recent_covered, 1), _RECENT_WINDOW_DAYS)

    groups: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        code = r["product_code"]
        pretax = round(r["pretax_amount"] or 0, 4)
        subscription_type = r["subscription_type"] or ""
        # 服务周期直接用入库时已按代表行归一好的月数：原始“数值 + 单位”两列独立
        # 取 MAX 可能把新购的「1 月」和退款的「32 天」错位配成「32 月」
        service_months = round(r["service_months"] or 0, 4)
        bill_days = int(r["bill_days"] or 0)

        group = groups.get(code)
        if group is None:
            group = groups[code] = {
                "product_code": code,
                "product_name": r["product_name"] or code,
                "pretax_amount": 0.0,
                "items": [],
            }
        group["pretax_amount"] += pretax
        group["items"].append(
            {
                "subscription_type": subscription_type,
                "instance_id": r["instance_id"] or "",
                "instance_label": _instance_label(r["nick_name"] or "", r["instance_id"] or ""),
                "billing_item": r["billing_item"] or r["billing_item_code"] or "整单",
                "billing_item_code": r["billing_item_code"] or "",
                "instance_spec": r["instance_spec"] or "",
                "nick_name": r["nick_name"] or "",
                "region": r["region"] or "",
                "list_price": r["list_price"] or "",
                "list_price_unit": r["list_price_unit"] or "",
                "usage_qty": round(r["usage_qty"] or 0, 4),
                "usage_unit": r["usage_unit"] or "",
                "service_months": service_months,
                "pretax_amount": pretax,
                "payment_amount": round(r["payment_amount"] or 0, 4),
                "deducted_by_coupons": round(r["deducted_by_coupons"] or 0, 4),
                "bill_days": bill_days,
                "monthly_cost": _monthly_cost(
                    subscription_type=subscription_type,
                    pretax_amount=pretax,
                    max_single_amount=round(r["max_single_amount"] or 0, 4),
                    service_months=service_months,
                    recent_amount=recent_map.get(_item_key(r), 0.0),
                    recent_divisor=recent_divisor,
                ),
            }
        )

    products: List[Dict[str, Any]] = []
    for group in groups.values():
        total = group["pretax_amount"]
        for item in group["items"]:
            item["percentage"] = round(item["pretax_amount"] / total * 100, 1) if total > 0 else 0
        group["pretax_amount"] = round(total, 4)
        products.append(group)
    products.sort(key=lambda g: -g["pretax_amount"])

    return {
        "range": {"start": start.isoformat(), "end": today.isoformat(), "days": days},
        "has_detail": bool(rows),
        "covered_days": covered_days,
        "monthly_basis_days": recent_divisor,
        "products": products,
    }
