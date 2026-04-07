-- =====================================================
-- WuXing AI Stylist - Zeabur Database Initialization Script
-- Version: 3.0 (匹配实际生产数据库结构)
-- Description: 适配 Zeabur PostgreSQL 的数据库初始化脚本
-- =====================================================
-- 使用说明：
-- 1. Zeabur PostgreSQL 已预装 pgvector，无需 CREATE EXTENSION
-- 2. Zeabur 使用 zeabur 数据库，无需创建新数据库
-- 3. 直接在 Zeabur Console 或通过 psql 执行此脚本
-- =====================================================

-- 注意：Zeabur 已预装 pgvector，如果报错请跳过此行
-- CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- 1. 五行配置表 (five_element_configs)
-- =====================================================
CREATE TABLE IF NOT EXISTS five_element_configs (
    id SERIAL PRIMARY KEY,
    element_name VARCHAR(10) NOT NULL UNIQUE,
    colors JSONB,
    materials JSONB,
    styles JSONB,
    energy_description TEXT,
    energy_strength_range JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. 物品表 (items) - 公共种子库
-- =====================================================
CREATE TABLE IF NOT EXISTS items (
    item_code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    primary_element VARCHAR(10),
    secondary_element VARCHAR(10),
    energy_intensity DOUBLE PRECISION,
    gender VARCHAR(10) DEFAULT '中性',
    attributes_detail JSONB,
    embedding VECTOR,
    applicable_weather JSONB DEFAULT '[]',
    applicable_seasons JSONB DEFAULT '[]',
    temperature_range JSONB DEFAULT '{}',
    functionality JSONB DEFAULT '{}',
    thickness_level VARCHAR(20),
    image_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 3. 用户表 (users)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_code VARCHAR(36) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    nickname VARCHAR(100),
    avatar_url VARCHAR(500),
    gender VARCHAR(10),
    birth_date DATE,
    birth_time TIME,
    birth_location VARCHAR(200),
    preferred_city VARCHAR(100),
    bazi JSONB,
    xiyong_elements JSONB,
    preferred_elements JSONB,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 4. 用户衣橱表 (user_wardrobe)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_wardrobe (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_code VARCHAR(20) REFERENCES items(item_code),
    name VARCHAR(255),
    category VARCHAR(50),
    image_url VARCHAR(500),
    primary_element VARCHAR(10),
    secondary_element VARCHAR(10),
    energy_intensity DOUBLE PRECISION,
    attributes_detail JSONB DEFAULT '{}',
    embedding VECTOR,
    gender VARCHAR(10) DEFAULT '中性',
    applicable_weather JSONB DEFAULT '[]',
    applicable_seasons JSONB DEFAULT '[]',
    temperature_range JSONB DEFAULT '{}',
    functionality JSONB DEFAULT '[]',
    thickness_level VARCHAR(20),
    is_custom BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    purchase_date DATE,
    wear_count INT DEFAULT 0,
    last_worn_date DATE,
    is_favorite BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 5. 反馈日志表 (feedback_logs)
-- =====================================================
CREATE TABLE IF NOT EXISTS feedback_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(36),
    query_text TEXT,
    scene VARCHAR(50),
    item_id INT,
    item_code VARCHAR(20),
    item_source VARCHAR(20),
    action VARCHAR(10) NOT NULL,
    feedback_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 索引创建
-- =====================================================

-- 物品表索引
CREATE INDEX IF NOT EXISTS idx_items_item_code ON items(item_code);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_primary_element ON items(primary_element);
CREATE INDEX IF NOT EXISTS idx_items_gender ON items(gender);
CREATE INDEX IF NOT EXISTS idx_items_embedding ON items USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64');

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_user_code ON users(user_code);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 用户衣橱表索引
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_element ON user_wardrobe(user_id, primary_element);
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_active ON user_wardrobe(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_custom ON user_wardrobe(user_id, is_custom);
CREATE INDEX IF NOT EXISTS idx_wardrobe_gender ON user_wardrobe(gender);
CREATE INDEX IF NOT EXISTS idx_wardrobe_applicable_weather ON user_wardrobe USING gin (applicable_weather);
CREATE INDEX IF NOT EXISTS idx_wardrobe_applicable_seasons ON user_wardrobe USING gin (applicable_seasons);
CREATE INDEX IF NOT EXISTS idx_wardrobe_functionality ON user_wardrobe USING gin (functionality);
CREATE INDEX IF NOT EXISTS idx_wardrobe_embedding ON user_wardrobe USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64');

-- 反馈日志表索引
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_item ON feedback_logs(item_id, item_source);

-- =====================================================
-- 插入五行基础配置数据
-- =====================================================
INSERT INTO five_element_configs (element_name, colors, materials, styles, energy_description, energy_strength_range)
VALUES 
    ('金', 
     '["白色", "银色", "金色", "米色"]',
     '["金属", "丝绸", "化纤"]',
     '["修身", "简约", "利落"]',
     '金代表收敛、肃杀、变革的能量。金属性的衣物通常具有简洁利落的线条、冷色调或金属光泽。',
     '[0.0, 1.0]'
    ),
    ('木',
     '["绿色", "青色", "翠色"]',
     '["棉麻", "植物纤维", "竹纤维"]',
     '["宽松", "自然", "休闲"]',
     '木代表生长、舒展、向上的能量。木属性的衣物通常采用天然面料，颜色以绿色系为主，款式宽松舒适。',
     '[0.0, 1.0]'
    ),
    ('水',
     '["黑色", "深蓝色", "灰色"]',
     '["皮革", "防水面料", "丝绒"]',
     '["流动", "飘逸", "垂坠"]',
     '水代表流动、渗透、变化的能量。水属性的衣物通常具有流动的线条，颜色深沉，材质柔软。',
     '[0.0, 1.0]'
    ),
    ('火',
     '["红色", "紫色", "粉色", "橙色"]',
     '["羊毛", "羽绒", "发热纤维"]',
     '["夸张", "醒目", "装饰性强"]',
     '火代表热情、光明、向上的能量。火属性的衣物颜色鲜艳，款式夸张醒目，具有强烈的视觉冲击力。',
     '[0.0, 1.0]'
    ),
    ('土',
     '["黄色", "棕色", "卡其色", "大地色"]',
     '["棉", "麻", "毛呢", "灯芯绒"]',
     '["稳重", "厚实", "舒适"]',
     '土代表稳定、包容、承载的能量。土属性的衣物颜色以大地色系为主，材质厚实舒适，款式稳重。',
     '[0.0, 1.0]'
    )
ON CONFLICT (element_name) DO NOTHING;

-- =====================================================
-- 完成提示
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE '✅ 数据库初始化完成！';
    RAISE NOTICE '已创建表: five_element_configs, items, users, user_wardrobe, feedback_logs';
    RAISE NOTICE '已插入五行基础配置数据';
    RAISE NOTICE '已创建所有必要索引（包括 HNSW 向量索引和 GIN JSONB 索引）';
END $$;
