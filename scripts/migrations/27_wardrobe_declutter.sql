-- 27: 断舍离三态记录
-- 闲置衣物的处理动作（捐赠 / 转让 / 丢弃）单独成表，不删 user_wardrobe 行，
-- 仅置 is_active = FALSE，保留历史日记外键与穿戴计数。
-- 同一件衣物只保留一条最新处理记录（UNIQUE 约束 + upsert，撤销时删除该行）。

CREATE TABLE IF NOT EXISTS wardrobe_item_actions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  wardrobe_item_id INTEGER NOT NULL REFERENCES user_wardrobe(id) ON DELETE CASCADE,
  action VARCHAR(10) NOT NULL CHECK (action IN ('donate','sell','discard')),
  note VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, wardrobe_item_id)
);

CREATE INDEX IF NOT EXISTS idx_wia_user ON wardrobe_item_actions(user_id, created_at DESC);
