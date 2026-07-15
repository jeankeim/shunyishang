-- =====================================================
-- Week 10: VIP 会员体系与推送通知系统
-- Version: 1.0
-- =====================================================

-- subscriptions: 会员订阅表
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(20) NOT NULL DEFAULT 'free',  -- free/monthly/yearly
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active/cancelled/expired/suspended
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    payment_method VARCHAR(20),  -- wechat/alipay/mock
    auto_renew BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- payment_records: 支付记录表
CREATE TABLE IF NOT EXISTS payment_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    payment_method VARCHAR(20) NOT NULL,  -- wechat/alipay/mock
    transaction_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/completed/failed/refunded
    paid_at TIMESTAMPTZ,
    refund_amount DECIMAL(10,2),
    refunded_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- push_notifications: 推送记录表
CREATE TABLE IF NOT EXISTS push_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(30) NOT NULL,  -- fortune_daily/diary_reminder/marketing/system
    title VARCHAR(200) NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}',
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- user_push_settings: 用户推送设置
CREATE TABLE IF NOT EXISTS user_push_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    fortune_push BOOLEAN DEFAULT TRUE,
    fortune_push_time TIME DEFAULT '08:00:00',
    diary_reminder BOOLEAN DEFAULT TRUE,
    diary_reminder_time TIME DEFAULT '21:00:00',
    marketing BOOLEAN DEFAULT FALSE,
    vibrate BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_payment_records_user ON payment_records(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_records_subscription ON payment_records(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_records_transaction ON payment_records(transaction_id);
CREATE INDEX IF NOT EXISTS idx_push_notifications_user ON push_notifications(user_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_push_notifications_type ON push_notifications(type);

-- updated_at 触发器
DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions;
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
DROP TRIGGER IF EXISTS update_user_push_settings_updated_at ON user_push_settings;
CREATE TRIGGER update_user_push_settings_updated_at BEFORE UPDATE ON user_push_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
