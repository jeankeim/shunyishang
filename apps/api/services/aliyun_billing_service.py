"""
后台管理 - 阿里云费用账单服务

通过阿里云 BSS OpenAPI（QueryAccountBill, 按天粒度）拉取全产品账单
（ECS / RDS / OSS / CDN / 百炼大模型等），按天按产品落库 aliyun_daily_bills，
并提供汇总查询。

AK 要求：RAM 子账号仅授予 AliyunBSSReadOnlyAccess 只读权限即可。
账单延迟说明：阿里云当天账单通常次日才出全，因此同步范围默认截至 D-1，
且每次同步回刷最近 3 天以覆盖延迟更新。
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

from apps.api.core.config import settings
from apps.api.core.database import DatabasePool
from apps.api.core.time_utils import today_cn

logger = logging.getLogger(__name__)

_BSS_ENDPOINT = "business.aliyuncs.com"


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


def sync_bills(days: int = 3) -> Dict[str, Any]:
    """
    从阿里云拉取最近 N 天账单并落库（幂等 UPSERT）

    默认回刷 D-1 ~ D-N（当天账单未出），手动触发可传更大 days 做历史回填。
    """
    client = _build_client()
    today = today_cn()
    synced_days = 0
    synced_rows = 0
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

    return {
        "synced_days": synced_days,
        "synced_rows": synced_rows,
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
