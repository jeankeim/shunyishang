-- Migration 09: 付费运势报告
-- 年度运势详批报告（AI 生成 + 展示页）

-- ========== 付费报告表 ==========
CREATE TABLE IF NOT EXISTS paid_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_type VARCHAR(30) NOT NULL,              -- 报告类型: annual_fortune / monthly_detail / love_fortune
    report_year INTEGER,                           -- 报告年份（年度报告用）
    title VARCHAR(200) NOT NULL,                   -- 报告标题
    content JSONB NOT NULL,                        -- 报告内容（结构化 JSON）
    summary TEXT,                                  -- 摘要（用于列表展示）
    price_cents INTEGER NOT NULL DEFAULT 0,        -- 价格（分），0=免费
    status VARCHAR(20) DEFAULT 'generated',        -- generated / paid / delivered
    paid_at TIMESTAMP,                             -- 支付时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paid_reports_user ON paid_reports(user_id, report_type);
CREATE INDEX IF NOT EXISTS idx_paid_reports_status ON paid_reports(user_id, status);

COMMENT ON TABLE paid_reports IS '付费运势报告表，存储 AI 生成的运势详批';
COMMENT ON COLUMN paid_reports.content IS '结构化 JSON: {overall, career, wealth, love, health, monthly_breakdown, lucky_months, advice}';
