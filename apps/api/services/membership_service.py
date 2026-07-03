"""
会员服务层
处理订阅、取消、升级、续费、配额检查等操作
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from apps.api.core.database import DatabasePool
from apps.api.schemas.membership import (
    MembershipStatusResponse,
    PlanInfo,
    PlansListResponse,
    SubscribeResponse,
    CancelResponse,
    UpgradeResponse,
    RenewResponse,
    QuotaResponse,
)
from apps.api.services.payment_service import payment_service

logger = logging.getLogger(__name__)

# 套餐定义
PLAN_DEFINITIONS = {
    "free": {
        "name": "免费版",
        "plan_key": "free",
        "price_monthly": 0.0,
        "price_yearly": 0.0,
        "features": ["每日3次推荐", "基础运势", "基础衣橱管理"],
        "limits": {"daily_recommendations": 3, "ai_review": False, "advanced_fortune": False, "priority_display": False},
    },
    "monthly": {
        "name": "月度会员",
        "plan_key": "monthly",
        "price_monthly": 19.9,
        "price_yearly": 19.9 * 12,
        "features": ["无限推荐", "AI穿搭点评", "高级运势分析", "穿搭日记无限"],
        "limits": {"daily_recommendations": -1, "ai_review": True, "advanced_fortune": True, "priority_display": False},
    },
    "yearly": {
        "name": "年度会员",
        "plan_key": "yearly",
        "price_monthly": 168.0 / 12,
        "price_yearly": 168.0,
        "features": ["月度会员全部权益", "穿搭广场优先展示", "专属客服", "优先体验新功能"],
        "limits": {"daily_recommendations": -1, "ai_review": True, "advanced_fortune": True, "priority_display": True},
    },
}

# 等级层级
PLAN_HIERARCHY = {"free": 0, "monthly": 1, "yearly": 2}

# 订阅时长
PLAN_DURATION = {
    "monthly": timedelta(days=30),
    "yearly": timedelta(days=365),
}


class MembershipService:
    """会员服务"""

    @staticmethod
    def get_membership_status(user_id: int) -> MembershipStatusResponse:
        """获取当前会员状态"""
        query = """
            SELECT id, plan, status, started_at, expires_at, auto_renew
            FROM subscriptions
            WHERE user_id = %s AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [user_id])
                row = cur.fetchone()

        if not row:
            return MembershipStatusResponse(plan="free", status="active")

        # 检查是否过期
        now = datetime.utcnow()
        expires_at = row.get("expires_at")
        if expires_at:
            if hasattr(expires_at, 'replace'):
                expires_naive = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
            else:
                expires_naive = expires_at
            if expires_naive < now:
                # 标记过期
                MembershipService._expire_subscription(row["id"])
                return MembershipStatusResponse(plan="free", status="active")

        days_remaining = None
        if expires_at:
            if hasattr(expires_at, 'replace'):
                expires_naive = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
            else:
                expires_naive = expires_at
            delta = expires_naive - now
            days_remaining = max(0, delta.days)

        return MembershipStatusResponse(
            plan=row["plan"],
            status=row["status"],
            started_at=row["started_at"],
            expires_at=row["expires_at"],
            auto_renew=row.get("auto_renew", False),
            days_remaining=days_remaining,
        )

    @staticmethod
    def _expire_subscription(subscription_id: int):
        """将订阅标记为过期"""
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE subscriptions SET status = 'expired', updated_at = NOW() WHERE id = %s",
                        [subscription_id],
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"标记订阅过期失败: {e}")

    @staticmethod
    def get_available_plans() -> PlansListResponse:
        """获取可用套餐列表"""
        plans = []
        for key, definition in PLAN_DEFINITIONS.items():
            plans.append(PlanInfo(**definition))
        return PlansListResponse(plans=plans)

    @staticmethod
    def subscribe(user_id: int, plan: str, payment_method: str) -> SubscribeResponse:
        """创建订阅"""
        definition = PLAN_DEFINITIONS.get(plan)
        if not definition:
            raise ValueError(f"无效套餐: {plan}")

        # 获取价格
        amount = definition["price_monthly"] if plan == "monthly" else definition["price_yearly"]
        duration = PLAN_DURATION.get(plan, timedelta(days=30))

        # 创建支付订单
        order = payment_service.create_order(amount, f"{definition['name']}订阅", payment_method)
        transaction_id = order["transaction_id"]

        # 创建订阅记录
        now = datetime.utcnow()
        expires_at = now + duration

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 先将该用户之前的活跃订阅设为取消
                cur.execute(
                    "UPDATE subscriptions SET status = 'cancelled', cancelled_at = NOW() WHERE user_id = %s AND status = 'active'",
                    [user_id],
                )

                # 创建新订阅
                cur.execute(
                    """
                    INSERT INTO subscriptions (user_id, plan, status, started_at, expires_at, payment_method, auto_renew)
                    VALUES (%s, %s, 'active', %s, %s, %s, TRUE)
                    RETURNING id
                    """,
                    [user_id, plan, now, expires_at, payment_method],
                )
                sub_id = cur.fetchone()["id"]

                # 创建支付记录
                cur.execute(
                    """
                    INSERT INTO payment_records (user_id, subscription_id, amount, payment_method, transaction_id, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    """,
                    [user_id, sub_id, amount, payment_method, transaction_id],
                )
                conn.commit()

        # Mock 环境自动完成支付
        payment_service.verify_payment(transaction_id)
        MembershipService._complete_payment(transaction_id)

        return SubscribeResponse(
            subscription_id=sub_id,
            status="active",
            payment_url=order.get("payment_url"),
        )

    @staticmethod
    def _complete_payment(transaction_id: str):
        """标记支付完成"""
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE payment_records SET status = 'completed', paid_at = NOW() WHERE transaction_id = %s",
                        [transaction_id],
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"标记支付完成失败: {e}")

    @staticmethod
    def cancel_subscription(user_id: int, subscription_id: int) -> CancelResponse:
        """取消订阅"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, expires_at FROM subscriptions
                    WHERE id = %s AND user_id = %s AND status = 'active'
                    """,
                    [subscription_id, user_id],
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("订阅不存在或已取消")

                cur.execute(
                    """
                    UPDATE subscriptions
                    SET status = 'cancelled', cancelled_at = NOW(), auto_renew = FALSE, updated_at = NOW()
                    WHERE id = %s
                    """,
                    [subscription_id],
                )
                conn.commit()

        return CancelResponse(status="cancelled", expires_at=row["expires_at"])

    @staticmethod
    def upgrade(user_id: int, new_plan: str) -> UpgradeResponse:
        """升级套餐"""
        new_def = PLAN_DEFINITIONS.get(new_plan)
        if not new_def:
            raise ValueError(f"无效套餐: {new_plan}")

        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取当前活跃订阅
                cur.execute(
                    """
                    SELECT id, plan, expires_at, started_at
                    FROM subscriptions
                    WHERE user_id = %s AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    [user_id],
                )
                current = cur.fetchone()

                if not current:
                    raise ValueError("没有活跃订阅可升级")

                current_plan = current["plan"]
                if PLAN_HIERARCHY.get(new_plan, 0) <= PLAN_HIERARCHY.get(current_plan, 0):
                    raise ValueError("只能升级到更高级的套餐")

                # 计算差价（简化：按剩余天数比例计算）
                now = datetime.utcnow()
                expires_at = current.get("expires_at")
                if expires_at:
                    if hasattr(expires_at, 'replace'):
                        expires_naive = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
                    else:
                        expires_naive = expires_at
                    remaining_days = max(1, (expires_naive - now).days)
                else:
                    remaining_days = 30

                # 当前套餐日均价
                current_price = PLAN_DEFINITIONS[current_plan]["price_monthly"] if current_plan == "monthly" else PLAN_DEFINITIONS[current_plan]["price_yearly"]
                current_duration = 30 if current_plan == "monthly" else 365
                daily_current = current_price / current_duration

                # 新套餐日均价
                new_price = new_def["price_monthly"] if new_plan == "monthly" else new_def["price_yearly"]
                new_duration = 30 if new_plan == "monthly" else 365
                daily_new = new_price / new_duration

                price_diff = round((daily_new - daily_current) * remaining_days, 2)
                price_diff = max(0, price_diff)

                # 更新订阅
                cur.execute(
                    """
                    UPDATE subscriptions
                    SET plan = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                    """,
                    [new_plan, current["id"]],
                )
                sub_id = cur.fetchone()["id"]
                conn.commit()

        return UpgradeResponse(
            subscription_id=sub_id,
            plan=new_plan,
            status="active",
            price_diff=price_diff,
        )

    @staticmethod
    def renew(user_id: int, payment_method: str = "mock") -> RenewResponse:
        """续费"""
        with DatabasePool.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, plan, expires_at
                    FROM subscriptions
                    WHERE user_id = %s AND status IN ('active', 'expired')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    [user_id],
                )
                current = cur.fetchone()

                if not current:
                    raise ValueError("没有可续费的订阅")

                plan = current["plan"]
                definition = PLAN_DEFINITIONS.get(plan)
                if not definition or plan == "free":
                    raise ValueError("免费用户请直接订阅")

                amount = definition["price_monthly"] if plan == "monthly" else definition["price_yearly"]
                duration = PLAN_DURATION.get(plan, timedelta(days=30))

                # 创建支付订单
                order = payment_service.create_order(amount, f"{definition['name']}续费", payment_method)

                # 计算新的过期时间
                now = datetime.utcnow()
                old_expires = current.get("expires_at")
                if old_expires:
                    if hasattr(old_expires, 'replace'):
                        old_expires_naive = old_expires.replace(tzinfo=None) if old_expires.tzinfo else old_expires
                    else:
                        old_expires_naive = old_expires
                    base_time = max(now, old_expires_naive)
                else:
                    base_time = now
                new_expires = base_time + duration

                # 更新订阅
                cur.execute(
                    """
                    UPDATE subscriptions
                    SET status = 'active', expires_at = %s, cancelled_at = NULL, updated_at = NOW()
                    WHERE id = %s
                    """,
                    [new_expires, current["id"]],
                )

                # 记录支付
                cur.execute(
                    """
                    INSERT INTO payment_records (user_id, subscription_id, amount, payment_method, transaction_id, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    """,
                    [user_id, current["id"], amount, payment_method, order["transaction_id"]],
                )
                conn.commit()

        # Mock 自动完成
        payment_service.verify_payment(order["transaction_id"])
        MembershipService._complete_payment(order["transaction_id"])

        return RenewResponse(
            subscription_id=current["id"],
            status="active",
            expires_at=new_expires,
            payment_url=order.get("payment_url"),
        )

    @staticmethod
    def check_quota(user_id: int, feature_name: str) -> QuotaResponse:
        """检查功能配额"""
        status = MembershipService.get_membership_status(user_id)
        plan = status.plan
        definition = PLAN_DEFINITIONS.get(plan, PLAN_DEFINITIONS["free"])
        limits = definition.get("limits", {})

        # 定义各功能的配额
        feature_limits = {
            "daily_recommendations": {"limit": limits.get("daily_recommendations", 3), "type": "count"},
            "ai_review": {"limit": limits.get("ai_review", False), "type": "bool"},
            "advanced_fortune": {"limit": limits.get("advanced_fortune", False), "type": "bool"},
            "priority_display": {"limit": limits.get("priority_display", False), "type": "bool"},
        }

        feature_config = feature_limits.get(feature_name)
        if not feature_config:
            return QuotaResponse(feature=feature_name, allowed=True)

        if feature_config["type"] == "bool":
            allowed = bool(feature_config["limit"])
            plan_required = None
            if not allowed:
                # 找出哪个套餐有此功能
                for pkey, pdef in PLAN_DEFINITIONS.items():
                    if pdef.get("limits", {}).get(feature_name):
                        plan_required = pkey
                        break
            return QuotaResponse(feature=feature_name, allowed=allowed, plan_required=plan_required)

        # count 类型
        limit_val = feature_config["limit"]
        if limit_val == -1:
            return QuotaResponse(feature=feature_name, allowed=True, used=0, limit=None)

        # 查询今日使用次数（简化：查询推荐记录）
        used = 0
        try:
            with DatabasePool.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*) as cnt FROM feedback_logs
                        WHERE user_id = %s AND created_at >= CURRENT_DATE
                        """,
                        [user_id],
                    )
                    row = cur.fetchone()
                    used = row["cnt"] if row else 0
        except Exception:
            pass

        allowed = used < limit_val if limit_val else False
        plan_required = None
        if not allowed:
            for pkey, pdef in PLAN_DEFINITIONS.items():
                p_limit = pdef.get("limits", {}).get(feature_name, 0)
                if p_limit == -1 or (isinstance(p_limit, int) and p_limit > limit_val):
                    plan_required = pkey
                    break

        return QuotaResponse(feature=feature_name, allowed=allowed, used=used, limit=limit_val, plan_required=plan_required)

    @staticmethod
    def process_payment_callback(transaction_id: str, status: str) -> Dict[str, Any]:
        """处理支付回调"""
        if status == "completed":
            payment_service.verify_payment(transaction_id)
            MembershipService._complete_payment(transaction_id)
            return {"status": "processed", "transaction_id": transaction_id}
        elif status == "failed":
            try:
                with DatabasePool.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE payment_records SET status = 'failed' WHERE transaction_id = %s",
                            [transaction_id],
                        )
                        conn.commit()
            except Exception as e:
                logger.error(f"处理支付失败回调: {e}")
            return {"status": "failed", "transaction_id": transaction_id}

        return {"status": "unknown", "transaction_id": transaction_id}


membership_service = MembershipService()
