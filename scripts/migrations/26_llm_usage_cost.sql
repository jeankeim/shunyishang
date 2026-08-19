-- 26: 用户大模型调用明细 - 成本核算
-- 新增模型 / token 用量 / 折算成本列；历史数据按场景平均 token 估算回填。
-- 单价（元/千token，参考阿里云百炼官网国内定价）：
--   qwen-plus: 入 0.0008 / 出 0.002；qwen-vl-plus: 入 0.0008 / 出 0.002

ALTER TABLE user_daily_llm_usage
    ADD COLUMN IF NOT EXISTS model VARCHAR(50),
    ADD COLUMN IF NOT EXISTS input_tokens INTEGER,
    ADD COLUMN IF NOT EXISTS output_tokens INTEGER,
    ADD COLUMN IF NOT EXISTS llm_cost NUMERIC(10,6) NOT NULL DEFAULT 0;

-- 历史回填：上线前埋点未捕获 usage，按场景平均 token 估算（含 agent 内多次调用合计）
-- 仅回填 input_tokens 为 NULL 的旧行，新写入行不受影响
UPDATE user_daily_llm_usage l
SET model = v.model,
    input_tokens = v.it,
    output_tokens = v.ot,
    llm_cost = ROUND((v.it * v.pi + v.ot * v.po) / 1000.0, 6)
FROM (VALUES
    -- agent: 上下文提取+查询增强+理由生成 合计约 2400 入 / 300 出
    ('agent', 'qwen-plus', 2400, 300, 0.0008, 0.002),
    -- fortune: 每日运势 AI 叙事 约 1000 入 / 450 出
    ('fortune', 'qwen-plus', 1000, 450, 0.0008, 0.002),
    -- fortune_report: 年度详批 约 1200 入 / 1600 出
    ('fortune_report', 'qwen-plus', 1200, 1600, 0.0008, 0.002),
    -- wardrobe_ai: 视觉打标为主 约 1600 入(含图) / 260 出
    ('wardrobe_ai', 'qwen-vl-plus', 1600, 260, 0.0008, 0.002),
    -- diary_ai: 打卡穿搭分析 约 1600 入(含图) / 260 出
    ('diary_ai', 'qwen-vl-plus', 1600, 260, 0.0008, 0.002)
) AS v(scene, model, it, ot, pi, po)
WHERE l.scene = v.scene
  AND l.input_tokens IS NULL;
