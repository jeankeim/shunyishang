-- =====================================================
-- Migration 25: 用户大模型调用明细表（后台管理第三个子页）
-- 每次真实大模型调用落一条（缓存命中不记录），
-- usage_date 为北京自然日，支持按天筛选与按用户分组聚合。
-- =====================================================

CREATE TABLE IF NOT EXISTS user_daily_llm_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_date DATE NOT NULL,                     -- 北京自然日（便于按天筛选）
    scene VARCHAR(50) NOT NULL,                   -- agent/fortune/fortune_report/wardrobe_ai/diary_ai
    query_text TEXT,                              -- 查询词 / 衣物描述
    result_summary TEXT,                          -- 返回结果摘要（推荐件数/关键内容）
    image_cost NUMERIC(10,4) NOT NULL DEFAULT 0,  -- 图片生成成本（元，预留字段）
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_date ON user_daily_llm_usage(usage_date);
CREATE INDEX IF NOT EXISTS idx_llm_usage_user ON user_daily_llm_usage(user_id, usage_date);

COMMENT ON TABLE user_daily_llm_usage IS '用户大模型调用明细（后台管理-大模型调用明细页数据源）';
COMMENT ON COLUMN user_daily_llm_usage.scene IS 'agent=推荐Agent, fortune=每日运势AI叙事, fortune_report=年度报告, wardrobe_ai=衣橱AI打标, diary_ai=日记AI分析';

-- 历史回填：近 30 天推荐日志（agent 实时计算路径，真实调用 LLM）转为明细，页面上线即可见数据
INSERT INTO user_daily_llm_usage (user_id, usage_date, scene, query_text, result_summary, image_cost, created_at)
SELECT user_id,
       (created_at AT TIME ZONE 'Asia/Shanghai')::date,
       'agent',
       query_text,
       '推荐 ' || item_count || ' 件物品（历史回填）',
       0,
       created_at
FROM recommend_logs
WHERE source = 'agent'
  AND user_id IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days';

-- 历史回填：近 30 天已完成 AI 增强的每日运势（ai_narrative 非 pending = 真实调用过 LLM）
INSERT INTO user_daily_llm_usage (user_id, usage_date, scene, query_text, result_summary, image_cost, created_at)
SELECT user_id,
       fortune_date,
       'fortune',
       NULL,
       '每日运势 AI 叙事（历史回填）',
       0,
       NOW()
FROM daily_fortune
WHERE fortune_date >= CURRENT_DATE - 30
  AND ai_narrative IS NOT NULL
  AND NOT COALESCE(ai_narrative ? '_pending', FALSE);
