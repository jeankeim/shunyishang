-- 28: 衣橱年度报告
-- 参照 paid_reports 形态，但个人备案版完全免费，无 price_cents / paid_at 字段。
-- 每个用户每一年只保留一份报告（UNIQUE(user_id, report_year)），重复生成覆盖当年内容；
-- generate_count 记录当年已消耗的生成次数，用于与年度运势报告一致的每年 3 次限频。

CREATE TABLE IF NOT EXISTS wardrobe_reports (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  report_year INTEGER NOT NULL,
  title VARCHAR(200) NOT NULL,
  content JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending=任务排队中 / ready=已生成 / failed=生成失败
  generate_count INTEGER NOT NULL DEFAULT 0,       -- 当年已发起的生成次数（限频依据）
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, report_year)
);

CREATE INDEX IF NOT EXISTS idx_wr_user ON wardrobe_reports(user_id, report_year DESC);

COMMENT ON TABLE wardrobe_reports IS '衣橱年度报告（免费），content 存 {stats, narrative} 结构化结果';
COMMENT ON COLUMN wardrobe_reports.status IS 'pending=异步任务未回写, ready=可展示, failed=生成失败可重看';
