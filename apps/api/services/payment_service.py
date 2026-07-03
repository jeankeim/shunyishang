"""
支付服务（Mock 实现）
生产环境需要真实商户资质，此处用 Mock 实现完整流程
"""

import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PaymentService(ABC):
    """支付服务抽象基类"""

    @abstractmethod
    def create_order(self, amount: float, description: str, payment_method: str) -> Dict[str, Any]:
        """创建支付订单，返回支付信息"""
        pass

    @abstractmethod
    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """验证支付状态"""
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: float) -> Dict[str, Any]:
        """发起退款"""
        pass


class MockPaymentService(PaymentService):
    """Mock 支付服务实现"""

    # 内存中存储 mock 订单（生产环境应持久化）
    _orders: Dict[str, Dict[str, Any]] = {}

    def create_order(self, amount: float, description: str, payment_method: str) -> Dict[str, Any]:
        """
        创建 Mock 支付订单
        
        Returns:
            {"transaction_id": str, "payment_url": str, "amount": float, "status": str}
        """
        transaction_id = f"MOCK-{uuid.uuid4().hex[:16].upper()}"
        
        # 模拟支付链接
        payment_url = f"https://mock-payment.example.com/pay/{transaction_id}?amount={amount}&method={payment_method}"
        
        order = {
            "transaction_id": transaction_id,
            "payment_url": payment_url,
            "amount": amount,
            "description": description,
            "payment_method": payment_method,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._orders[transaction_id] = order
        logger.info(f"[MockPayment] 创建订单: {transaction_id}, 金额: ¥{amount}")
        
        return order

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        模拟支付验证（Mock 环境下直接返回成功）
        
        Returns:
            {"transaction_id": str, "status": str, "paid_at": str}
        """
        order = self._orders.get(transaction_id)
        
        if not order:
            # 即使找不到也模拟成功（方便测试回调流程）
            return {
                "transaction_id": transaction_id,
                "status": "completed",
                "paid_at": datetime.utcnow().isoformat(),
                "amount": 0,
            }
        
        # Mock: 自动标记为已支付
        order["status"] = "completed"
        order["paid_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"[MockPayment] 验证支付成功: {transaction_id}")
        
        return {
            "transaction_id": transaction_id,
            "status": "completed",
            "paid_at": order["paid_at"],
            "amount": order["amount"],
        }

    def refund(self, transaction_id: str, amount: float) -> Dict[str, Any]:
        """
        模拟退款
        
        Returns:
            {"transaction_id": str, "refund_amount": float, "status": str}
        """
        order = self._orders.get(transaction_id)
        
        if order:
            order["status"] = "refunded"
            order["refund_amount"] = amount
            order["refunded_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"[MockPayment] 退款成功: {transaction_id}, 金额: ¥{amount}")
        
        return {
            "transaction_id": transaction_id,
            "refund_amount": amount,
            "status": "refunded",
            "refunded_at": datetime.utcnow().isoformat(),
        }


# 全局支付服务实例
payment_service = MockPaymentService()
