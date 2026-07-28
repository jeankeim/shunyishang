-- 18_tasks.sql
-- 异步任务表：支持长耗时操作（如年度报告生成）任务化
-- 队列语义依赖 FOR UPDATE SKIP LOCKED，无需额外中间件

CREATE TABLE IF NOT EXISTS tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type   VARCHAR(50) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'running', 'done', 'failed')),
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    result      JSONB,
    error       TEXT,
    retries     INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

-- worker 认领扫描索引（仅覆盖待处理任务）
CREATE INDEX IF NOT EXISTS idx_tasks_claim
    ON tasks (created_at)
    WHERE status = 'pending';

-- 用户查询自己的任务
CREATE INDEX IF NOT EXISTS idx_tasks_user
    ON tasks (user_id, created_at DESC);
