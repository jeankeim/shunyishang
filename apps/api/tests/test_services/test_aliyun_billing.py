"""
aliyun_billing_service 计费项下钻纯函数单测

这些口径都是从真实账单里踩出来的，用例即回归防线：
- _monthly_cost：预付费退款让区间净额失真（同日 +156 新购与 -150.98 退款合并成 5.02）、
  已停项与一次性跑批不该再有月成本
- _to_months：服务周期单位杂多（秒/天/月/年 + 英文缩写）
- _instance_label：百炼 instance_id 末段是 0/1 标志，直接取末段会得到 "0"
"""

from apps.api.services.aliyun_billing_service import (
    _instance_label,
    _monthly_cost,
    _to_float,
    _to_int,
    _to_months,
)


class TestToFloatInt:
    def test_bss_string_fields(self):
        # BSS 字段多为字符串，偶发空串
        assert _to_float("0.326") == 0.326
        assert _to_float("") == 0.0
        assert _to_float(None, default=-1.0) == -1.0
        assert _to_float("abc") == 0.0

    def test_to_int_accepts_decimal_string(self):
        assert _to_int("727") == 727
        assert _to_int("1.9") == 1
        assert _to_int(None) == 0
        assert _to_int("", default=5) == 5


class TestToMonths:
    def test_chinese_units(self):
        assert _to_months(1, "月") == 1.0
        assert _to_months(2, "年") == 24.0
        assert _to_months(31, "天") == 31 / (365 / 12)
        assert _to_months(62812800, "秒") == 727 / (365 / 12)

    def test_english_units_case_insensitive(self):
        assert _to_months(12, "Month") == 12.0
        assert _to_months(1, "year") == 12.0
        assert _to_months(365, "d") == 365 / (365 / 12)

    def test_unresolvable_returns_zero(self):
        # 返回 0 表示不可折算，调用方据此兜底而不是给出错误月价
        assert _to_months(1, "小时") == 0.0
        assert _to_months(0, "月") == 0.0
        assert _to_months(-1, "月") == 0.0
        assert _to_months(12, "") == 0.0
        assert _to_months(12, None) == 0.0


class TestMonthlyCostSubscription:
    def test_refund_does_not_distort_monthly_price(self):
        """RDS 包月退订：同日 +156 与 -150.98 合并后区间净额只有 5.02，
        月价必须按单笔最大 156 算"""
        assert _monthly_cost(
            subscription_type="Subscription",
            pretax_amount=5.02,
            max_single_amount=156.0,
            service_months=1.0,
            recent_amount=0,
            recent_divisor=7,
        ) == 156.0

    def test_multi_year_prepaid_amortizes(self):
        """ECS 622.14 元 / 727 天预付 → 约 26 元/月"""
        assert _monthly_cost(
            subscription_type="Subscription",
            pretax_amount=622.14,
            max_single_amount=622.14,
            service_months=727 / (365 / 12),
            recent_amount=0,
            recent_divisor=7,
        ) == 26.03

    def test_falls_back_to_net_when_no_positive_single(self):
        """纯退款行（单笔最大 <= 0）退回区间值，为负时直接不折算"""
        assert _monthly_cost(
            subscription_type="Subscription",
            pretax_amount=5.02,
            max_single_amount=0,
            service_months=1.0,
            recent_amount=0,
            recent_divisor=7,
        ) == 5.02
        assert _monthly_cost(
            subscription_type="Subscription",
            pretax_amount=-199.36,
            max_single_amount=0,
            service_months=1.0,
            recent_amount=0,
            recent_divisor=7,
        ) == 0.0

    def test_unresolvable_period_returns_zero(self):
        assert _monthly_cost(
            subscription_type="Subscription",
            pretax_amount=206.0,
            max_single_amount=206.0,
            service_months=0,
            recent_amount=0,
            recent_divisor=7,
        ) == 0.0


class TestMonthlyCostPayAsYouGo:
    def test_recent_window_amortizes(self):
        """RDS 按量最近 7 天 72.44 元 → 约 314.77 元/月"""
        assert _monthly_cost(
            subscription_type="PayAsYouGo",
            pretax_amount=320.82,
            max_single_amount=10.35,
            service_months=0,
            recent_amount=72.44,
            recent_divisor=7,
        ) == 314.77

    def test_stopped_item_has_no_monthly_cost(self):
        """已停项：区间内有消费但最近窗口为 0，月均必须归 0 而不是摊出成本"""
        assert _monthly_cost(
            subscription_type="PayAsYouGo",
            pretax_amount=156.82,
            max_single_amount=51.36,
            service_months=0,
            recent_amount=0,
            recent_divisor=7,
        ) == 0.0

    def test_one_off_batch_not_exaggerated(self):
        """一次性跑批（8-23 生图 45.76 只出账 1 天）同理不被夸大成月成本"""
        assert _monthly_cost(
            subscription_type="PayAsYouGo",
            pretax_amount=45.76,
            max_single_amount=45.76,
            service_months=0,
            recent_amount=0,
            recent_divisor=7,
        ) == 0.0

    def test_divisor_never_below_one(self):
        """窗口只有 1 天出账时也不能除 0"""
        assert _monthly_cost(
            subscription_type="PayAsYouGo",
            pretax_amount=1.0,
            max_single_amount=1.0,
            service_months=0,
            recent_amount=10.0,
            recent_divisor=0,
        ) == round(10 * 365 / 12, 2)


class TestInstanceLabel:
    def test_nickname_wins(self):
        assert _instance_label("wuxingclothes", "rm-bp1abc") == "wuxingclothes"

    def test_dashscope_skips_numeric_flag(self):
        """百炼末段是 0/1 计费标志，取末两段得到 模型 · token 类型"""
        assert _instance_label(
            "", "2296674;llm-5tn5lih7ge4pzzxy;qwen-plus;input_token;;0"
        ) == "qwen-plus · input_token"
        assert _instance_label(
            "", "2296674;llm-5tn5lih7ge4pzzxy;qwen-max;output_token;;1"
        ) == "qwen-max · output_token"

    def test_oss_region_and_storage_class(self):
        assert _instance_label("", "cn-hangzhou;standard-zrs") == "cn-hangzhou · standard-zrs"

    def test_plain_instance_id_unchanged(self):
        assert _instance_label("", "i-bp17448hpb5wvq5d64hc") == "i-bp17448hpb5wvq5d64hc"

    def test_all_numeric_falls_back_to_raw(self):
        assert _instance_label("", "1;2;3") == "1;2;3"
        assert _instance_label("", "") == ""
