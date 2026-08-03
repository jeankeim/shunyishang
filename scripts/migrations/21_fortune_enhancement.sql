-- ============================================================
-- 21_fortune_enhancement.sql
-- 每日运势增强：增加黄历数据 + AI 叙事字段
-- ============================================================

-- 黄历数据（宜忌/冲煞/吉神凶煞/节气/十二时辰吉凶）
ALTER TABLE daily_fortune ADD COLUMN IF NOT EXISTS huangli JSONB DEFAULT '{}';

-- AI 生成的个性化运势叙事
ALTER TABLE daily_fortune ADD COLUMN IF NOT EXISTS ai_narrative JSONB DEFAULT '{}';

COMMENT ON COLUMN daily_fortune.huangli IS '黄历数据：{yi, ji, chong_sha, ji_shen, xiong_sha, solar_term, hour_luck}';
COMMENT ON COLUMN daily_fortune.ai_narrative IS 'AI叙事：{overview, career_tip, love_tip, health_tip, lucky_action, avoid_action}';