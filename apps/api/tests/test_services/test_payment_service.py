"""
支付服务测试
"""

import pytest
from apps.api.services.payment_service import MockPaymentService


class TestMockPaymentService:
    """Mock 支付服务测试"""

    @pytest.fixture
    def service(self):
        """创建支付服务实例"""
        svc = MockPaymentService()
        svc._orders = {}  # 清空共享状态
        return svc

    def test_create_order(self, service):
        """测试创建订单"""
        result = service.create_order(19.9, "月度会员", "mock")
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("MOCK-")
        assert result["amount"] == 19.9
        assert result["status"] == "pending"
        assert "payment_url" in result

    def test_create_order_wechat(self, service):
        """测试微信支付订单"""
        result = service.create_order(168.0, "年度会员", "wechat")
        assert result["payment_method"] == "wechat"
        assert result["amount"] == 168.0

    def test_create_order_alipay(self, service):
        """测试支付宝订单"""
        result = service.create_order(19.9, "月度会员", "alipay")
        assert result["payment_method"] == "alipay"

    def test_verify_payment_success(self, service):
        """测试支付验证成功"""
        order = service.create_order(19.9, "月度会员", "mock")
        tx_id = order["transaction_id"]

        result = service.verify_payment(tx_id)
        assert result["status"] == "completed"
        assert result["transaction_id"] == tx_id
        assert "paid_at" in result

    def test_verify_payment_unknown(self, service):
        """测试验证未知交易"""
        result = service.verify_payment("UNKNOWN-TX")
        assert result["status"] == "completed"  # Mock 环境默认成功

    def test_refund(self, service):
        """测试退款"""
        order = service.create_order(19.9, "月度会员", "mock")
        tx_id = order["transaction_id"]

        result = service.refund(tx_id, 19.9)
        assert result["status"] == "refunded"
        assert result["refund_amount"] == 19.9
        assert "refunded_at" in result

    def test_refund_unknown_transaction(self, service):
        """测试退款未知交易"""
        result = service.refund("UNKNOWN-TX", 10.0)
        assert result["status"] == "refunded"

    def test_order_lifecycle(self, service):
        """测试完整订单生命周期"""
        # 创建
        order = service.create_order(19.9, "月度会员", "mock")
        tx_id = order["transaction_id"]
        assert order["status"] == "pending"

        # 验证支付
        verify = service.verify_payment(tx_id)
        assert verify["status"] == "completed"

        # 退款
        refund = service.refund(tx_id, 19.9)
        assert refund["status"] == "refunded"

    def test_multiple_orders(self, service):
        """测试多个订单"""
        o1 = service.create_order(19.9, "月度会员", "mock")
        o2 = service.create_order(168.0, "年度会员", "mock")
        assert o1["transaction_id"] != o2["transaction_id"]
