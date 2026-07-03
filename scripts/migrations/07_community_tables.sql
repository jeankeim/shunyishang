-- Migration 07: 穿搭广场社区 MVP
-- 三张核心表: community_posts, post_likes, post_comments

-- ========== 社区帖子表 ==========
CREATE TABLE IF NOT EXISTS community_posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    diary_id INTEGER,                            -- 关联日记（可选，从日记一键发布）
    content TEXT NOT NULL,                        -- 帖子正文
    image_urls TEXT[] DEFAULT '{}',               -- 图片URL列表
    tags TEXT[] DEFAULT '{}',                     -- 标签（如 #木系穿搭 #通勤）
    element VARCHAR(10),                          -- 主五行属性（可选）
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',          -- active / hidden / deleted
    is_featured BOOLEAN DEFAULT FALSE,            -- 是否精选
    published_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_posts_user ON community_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON community_posts(status, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_element ON community_posts(element) WHERE element IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_posts_featured ON community_posts(is_featured, published_at DESC) WHERE is_featured = TRUE;

COMMENT ON TABLE community_posts IS '穿搭广场帖子表';

-- ========== 点赞表 ==========
CREATE TABLE IF NOT EXISTS post_likes (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_likes_post ON post_likes(post_id);
CREATE INDEX IF NOT EXISTS idx_likes_user ON post_likes(user_id);

COMMENT ON TABLE post_likes IS '帖子点赞表';

-- ========== 评论表 ==========
CREATE TABLE IF NOT EXISTS post_comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_id INTEGER REFERENCES post_comments(id) ON DELETE CASCADE,  -- 回复评论
    status VARCHAR(20) DEFAULT 'active',          -- active / hidden / deleted
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_post ON post_comments(post_id, created_at);
CREATE INDEX IF NOT EXISTS idx_comments_user ON post_comments(user_id);

COMMENT ON TABLE post_comments IS '帖子评论表（支持嵌套回复）';
