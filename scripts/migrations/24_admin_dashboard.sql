-- =====================================================
-- Migration 24: 后台管理模块统计表
-- 1. recommend_logs        推荐请求日志（精确统计推荐次数）
-- 2. daily_api_stats       接口调用量按天聚合（中间件内存计数定时 flush）
-- 3. daily_dashboard_stats 运营看板每日聚合快照（DAU/新增/业务量）
-- 4. aliyun_daily_bills    阿里云账单按天按产品落库（BSS API 同步）
-- =====================================================

-- 1. 推荐请求日志：每次推荐（含缓存命中/每日精选）落一条
CREATE TABLE IF NOT EXISTS recommend_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,                            -- 游客为 NULL
    scene VARCHAR(50),                          -- 场景（日常/面试/旅行等）
    query_text TEXT,                            -- 用户查询文本
    source VARCHAR(20) DEFAULT 'agent',         -- agent=实时计算 / cache=缓存命中 / daily_pick=每日精选
    item_count INTEGER DEFAULT 0,               -- 返回物品数
    duration_ms INTEGER,                        -- 处理耗时（缓存命中接近0）
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_recommend_logs_created ON recommend_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_recommend_logs_user ON recommend_logs(user_id, created_at);

COMMENT ON TABLE recommend_logs IS '推荐请求日志（后台管理-运营看板数据源）';
COMMENT ON COLUMN recommend_logs.source IS 'agent=实时计算, cache=缓存命中, daily_pick=每日精选';

-- 2. 接口调用量按天聚合（endpoint_group 按路由前缀分组）
CREATE TABLE IF NOT EXISTS daily_api_stats (
    stat_date DATE NOT NULL,
    endpoint_group VARCHAR(50) NOT NULL,        -- recommend/fortune/wardrobe/diary/auth/...
    request_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    PRIMARY KEY (stat_date, endpoint_group)
);

COMMENT ON TABLE daily_api_stats IS '接口调用量按天聚合（中间件内存计数定时落库）';

-- 3. 运营看板每日聚合快照（定时任务生成，当天数据实时计算）
CREATE TABLE IF NOT EXISTS daily_dashboard_stats (
    stat_date DATE PRIMARY KEY,
    dau INTEGER DEFAULT 0,                      -- 日活跃用户数
    new_users INTEGER DEFAULT 0,                -- 新增注册
    recommend_count INTEGER DEFAULT 0,          -- 推荐次数
    api_requests INTEGER DEFAULT 0,             -- 接口调用总量
    diary_count INTEGER DEFAULT 0,              -- 新增穿搭日记
    fortune_count INTEGER DEFAULT 0,            -- 运势查询数
    like_count INTEGER DEFAULT 0,               -- 点赞数
    dislike_count INTEGER DEFAULT 0,            -- 点踩数
    wardrobe_added INTEGER DEFAULT 0,           -- 新增衣橱衣物
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE daily_dashboard_stats IS '运营看板每日聚合快照（每日 00:35 定时生成）';

-- 4. 阿里云账单按天按产品落库
CREATE TABLE IF NOT EXISTS aliyun_daily_bills (
    bill_date DATE NOT NULL,
    product_code VARCHAR(64) NOT NULL,          -- 产品代码 ecs/rds/oss/cdn/dashscope...
    product_name VARCHAR(128) DEFAULT '',       -- 产品名称（云服务器 ECS 等）
    subscription_type VARCHAR(32) DEFAULT '',   -- SubscriptionType 订阅/按量
    pretax_amount NUMERIC(14,4) DEFAULT 0,      -- 应付金额
    payment_amount NUMERIC(14,4) DEFAULT 0,     -- 现金支付金额
    deducted_by_coupons NUMERIC(14,4) DEFAULT 0,-- 优惠券抵扣
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (bill_date, product_code, subscription_type)
);
CREATE INDEX IF NOT EXISTS idx_aliyun_bills_date ON aliyun_daily_bills(bill_date);

COMMENT ON TABLE aliyun_daily_bills IS '阿里云账单按天按产品明细（BSS QueryAccountBill 同步）';
