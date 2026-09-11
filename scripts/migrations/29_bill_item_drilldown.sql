-- =====================================================
-- Migration 29: 阿里云账单计费项下钻明细
--
-- 背景：aliyun_daily_bills 由 QueryAccountBill(is_group_by_product=True) 生成，
-- 只到「产品」粒度。排查"每天 10 元花在哪"时无法区分同一产品内是实例规格费
-- 还是存储费、是数据库还是大模型，只能手动调 BSS API 才能定位。
--
-- 本表由 DescribeInstanceBill(is_billing_item=True) 按天落库，粒度到
-- 「产品 × 订阅类型 × 实例 × 计费项」，并保留单价/用量/服务周期，
-- 用于判断按量与包年包月哪个更划算、以及哪个实例在产生费用。
-- =====================================================

CREATE TABLE IF NOT EXISTS aliyun_daily_bill_items (
    bill_date DATE NOT NULL,
    product_code VARCHAR(64) NOT NULL,              -- rds/ecs/oss/sfm...
    product_name VARCHAR(128) NOT NULL DEFAULT '',
    subscription_type VARCHAR(32) NOT NULL DEFAULT '',  -- PayAsYouGo / Subscription
    instance_id VARCHAR(160) NOT NULL DEFAULT '',   -- pgm-xxx;cn-hangzhou / 含模型名的百炼实例
    billing_item_code VARCHAR(48) NOT NULL DEFAULT '',  -- ClassCode / 空（预付费整单无计费项）
    billing_item VARCHAR(96) NOT NULL DEFAULT '',   -- 规格 / 存储空间 / 大模型文本消耗量

    -- 实例画像：定位"哪台机器 / 哪个模型"在花钱
    instance_spec VARCHAR(64) NOT NULL DEFAULT '',  -- pg.n2.2c.1m / ecs.e-c1m4.large
    nick_name VARCHAR(128) NOT NULL DEFAULT '',     -- wuxingclothes
    region VARCHAR(64) NOT NULL DEFAULT '',
    instance_config TEXT NOT NULL DEFAULT '',       -- 完整配置串（核数/存储/版本/系列）

    -- 计费口径：单价 × 用量，用于判断按量是否比包月划算
    list_price VARCHAR(32) NOT NULL DEFAULT '',     -- API 原样返回的字符串，不做数值化
    list_price_unit VARCHAR(32) NOT NULL DEFAULT '', -- 元/小时、元/(GB*小时)
    usage_qty NUMERIC(18,4) NOT NULL DEFAULT 0,
    usage_unit VARCHAR(32) NOT NULL DEFAULT '',
    service_period BIGINT NOT NULL DEFAULT 0,       -- 预付费服务周期数值（展示用，取自当日金额最大的一笔）
    service_period_unit VARCHAR(16) NOT NULL DEFAULT '',  -- 秒/天/月/年

    -- 折算月均用的两个归一化字段。必须在此落库而不是查询时再算：同一台预付费实例
    -- 在退订当天会同时出现「新购 +156 元(周期 1 月)」与「退款 -150.98 元(周期 32 天)」
    -- 两行，合并成一行后区间求和只剩 5.02 元，独立取 MAX 又可能把「32」和「月」配成
    -- 一对错周期。故按「金额最大的一笔」取代表行，在服务端一次性归一。
    max_single_amount NUMERIC(14,4) NOT NULL DEFAULT 0,  -- 当日单笔最大应付（退款负数行不掩盖真实价）
    service_months NUMERIC(10,4) NOT NULL DEFAULT 0,     -- 代表行服务周期折算月数（无法识别为 0）

    pretax_amount NUMERIC(14,4) NOT NULL DEFAULT 0,     -- 应付金额（含退款负数行）
    payment_amount NUMERIC(14,4) NOT NULL DEFAULT 0,
    deducted_by_coupons NUMERIC(14,4) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (bill_date, product_code, subscription_type,
                 instance_id, billing_item_code, billing_item)
);

CREATE INDEX IF NOT EXISTS idx_aliyun_bill_items_date_product
    ON aliyun_daily_bill_items(bill_date, product_code);

COMMENT ON TABLE aliyun_daily_bill_items IS '阿里云账单计费项下钻明细（BSS DescribeInstanceBill 按天，随主账单同步）';
