-- ============================================
-- Week 4: 扩展用户衣橱 + 新建反馈表
-- 版本: 1.0
-- 日期: 2024-03-25
-- 说明: 扩展现有 user_wardrobe 表支持自定义衣物，新建 feedback_logs 表
-- ============================================

-- ============================================
-- 1. 扩展 user_wardrobe 表
-- 支持用户自定义衣物 + 向量搜索
-- ============================================

-- 添加自定义衣物字段
ALTER TABLE user_wardrobe 
ADD COLUMN IF NOT EXISTS name VARCHAR(255),           -- 自定义名称
ADD COLUMN IF NOT EXISTS category VARCHAR(50),        -- 分类
ADD COLUMN IF NOT EXISTS image_url VARCHAR(500),      -- 图片URL
ADD COLUMN IF NOT EXISTS primary_element VARCHAR(10), -- 主五行
ADD COLUMN IF NOT EXISTS secondary_element VARCHAR(10), -- 次五行
ADD COLUMN IF NOT EXISTS attributes_detail JSONB DEFAULT '{}', -- AI分析结果
ADD COLUMN IF NOT EXISTS embedding vector(1024),      -- 向量嵌入
ADD COLUMN IF NOT EXISTS is_custom BOOLEAN DEFAULT FALSE, -- 是否自定义物品
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;   -- 软删除标记

-- 修改 item_code 为可空（自定义衣物没有 item_code）
ALTER TABLE user_wardrobe 
ALTER COLUMN item_code DROP NOT NULL;

-- 添加注释
COMMENT ON COLUMN user_wardrobe.is_custom IS 'TRUE=用户自定义衣物，FALSE=引用公共库物品';
COMMENT ON COLUMN user_wardrobe.embedding IS '向量嵌入，用于语义搜索';
COMMENT ON COLUMN user_wardrobe.attributes_detail IS 'AI分析结果: {"color": "红色", "material": "丝绸", "style": "正式", "season": ["夏"], "tags": ["商务"]}';

-- ============================================
-- 2. 添加索引
-- ============================================

-- 用户+五行索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_element 
ON user_wardrobe(user_id, primary_element);

-- 用户+状态索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_active 
ON user_wardrobe(user_id, is_active);

-- 用户+自定义标记索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_custom 
ON user_wardrobe(user_id, is_custom);

-- 向量索引（HNSW，复用 Week 1 的配置）
CREATE INDEX IF NOT EXISTS idx_wardrobe_embedding 
ON user_wardrobe 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================
-- 3. 新建 feedback_logs 表（推荐反馈记录）
-- ============================================

CREATE TABLE IF NOT EXISTS feedback_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 推荐上下文
    session_id VARCHAR(36),               -- 推荐会话ID (UUID字符串)
    query_text TEXT,                      -- 用户查询
    scene VARCHAR(50),                    -- 场景
    
    -- 反馈内容
    item_id INTEGER,                      -- user_wardrobe.id
    item_code VARCHAR(20),                -- 或公共库物品 item_code
    item_source VARCHAR(20),              -- 'wardrobe' 或 'public'
    action VARCHAR(10) NOT NULL,          -- 'like' 或 'dislike'
    feedback_reason TEXT,                 -- 反馈原因（可选）
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 反馈表索引
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_item ON feedback_logs(item_id, item_source);

-- 反馈表注释
COMMENT ON TABLE feedback_logs IS '推荐反馈记录表';
COMMENT ON COLUMN feedback_logs.item_source IS 'wardrobe=私有衣橱物品，public=公共库物品';
COMMENT ON COLUMN feedback_logs.action IS 'like=点赞，dislike=点踩';

-- ============================================
-- 4. 确保触发器函数存在
-- ============================================

-- 确保 updated_at 触发器函数存在
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================
-- 迁移完成
-- ============================================
-- 验证命令:
-- \d user_wardrobe
-- \d feedback_logs
-- SELECT indexname FROM pg_indexes WHERE tablename = 'user_wardrobe';
-- SELECT indexname FROM pg_indexes WHERE tablename = 'feedback_logs';
