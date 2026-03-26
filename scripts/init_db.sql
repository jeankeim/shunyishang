-- =====================================================
-- WuXing AI Stylist - Database Initialization Script
-- Version: 2.0
-- Description: 完整的五行智能衣橱数据库表结构（包含Week 4所有扩展）
-- =====================================================

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- 1. 五行配置表 (five_element_configs)
-- 存储金木水火土的基础定义和颜色/材质/款式映射
-- =====================================================
CREATE TABLE five_element_configs (
    id SERIAL PRIMARY KEY,
    element_name VARCHAR(10) NOT NULL UNIQUE,  -- 金、木、水、火、土
    colors JSONB,                               -- 颜色映射列表
    materials JSONB,                            -- 材质映射列表
    styles JSONB,                               -- 款式映射列表
    energy_description TEXT,                    -- 能量描述
    energy_strength_range JSONB,                -- 能量强度范围 [min, max]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. 物品表 (items) - 公共种子库
-- 存储公共衣橱物品信息及向量嵌入
-- =====================================================
CREATE TABLE items (
    item_code VARCHAR(20) PRIMARY KEY,          -- 物品编码 (ITEM_001)
    name VARCHAR(255) NOT NULL,                 -- 物品名称
    category VARCHAR(50),                       -- 分类 (上装/下装/外套/裙装/鞋履/配饰)
    primary_element VARCHAR(10),                -- 主五行
    secondary_element VARCHAR(10),              -- 次五行
    energy_intensity FLOAT,                     -- 能量强度 (0.0-1.0)
    gender VARCHAR(10) DEFAULT '中性',          -- 适用性别 (男/女/中性)
    attributes_detail JSONB,                    -- 完整属性详情
    embedding VECTOR(1024),                     -- 语义向量 (BGE-M3 维度)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 3. 用户表 (users) - 增强版
-- =====================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_code VARCHAR(36) UNIQUE NOT NULL,      -- 用户唯一标识 (UUID)
    phone VARCHAR(20) UNIQUE,                   -- 手机号 (登录用)
    email VARCHAR(255) UNIQUE,                  -- 邮箱 (登录用)
    password_hash VARCHAR(255),                 -- 密码哈希
    nickname VARCHAR(100),                      -- 昵称
    avatar_url VARCHAR(500),                    -- 头像URL
    gender VARCHAR(10),                         -- 性别
    birth_date DATE,                            -- 出生日期
    birth_time TIME,                            -- 出生时间
    birth_location VARCHAR(200),                -- 出生地点
    preferred_city VARCHAR(100),                -- 常驻城市
    bazi JSONB,                                 -- 八字信息缓存
    xiyong_elements JSONB,                      -- 喜用神缓存
    preferred_elements JSONB,                   -- 偏好五行
    is_active BOOLEAN DEFAULT TRUE,             -- 账户状态
    last_login_at TIMESTAMP,                    -- 最后登录时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 4. 用户衣橱表 (user_wardrobe) - Week 4 完整版
-- 支持用户自定义衣物 + 向量搜索 + 天气感知
-- =====================================================
CREATE TABLE user_wardrobe (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_code VARCHAR(20) REFERENCES items(item_code),  -- 可为NULL（自定义衣物）
    
    -- 基础信息
    name VARCHAR(255),                          -- 自定义名称
    category VARCHAR(50),                       -- 分类：上装/下装/外套/鞋履/配饰
    image_url VARCHAR(500),                     -- 图片URL
    
    -- 五行属性
    primary_element VARCHAR(10),                -- 主五行：金/木/水/火/土
    secondary_element VARCHAR(10),              -- 次五行
    energy_intensity DOUBLE PRECISION,          -- 能量强度 0.0-1.0
    
    -- AI分析结果
    attributes_detail JSONB DEFAULT '{}',       -- {"color": "红色", "material": "丝绸", ...}
    embedding VECTOR(1024),                     -- 向量嵌入，用于语义搜索
    
    -- 天气/场景适配（Week 4 新增）
    gender VARCHAR(10) DEFAULT '中性',          -- 性别适配：男/女/中性
    applicable_weather JSONB DEFAULT '[]',      -- 适用天气：["晴", "多云", "阴"]
    applicable_seasons JSONB DEFAULT '[]',      -- 适用季节：["春", "夏", "秋", "冬"]
    temperature_range JSONB DEFAULT '{}',       -- 温度范围：{"min": 15, "max": 25}
    functionality JSONB DEFAULT '[]',           -- 功能场景：["面试", "约会", "商务"]
    thickness_level VARCHAR(20),                -- 厚度：轻薄/适中/加厚/厚重
    
    -- 状态标记
    is_custom BOOLEAN DEFAULT FALSE,            -- TRUE=自定义，FALSE=引用公共库
    is_active BOOLEAN DEFAULT TRUE,             -- 软删除标记
    
    -- 使用统计
    purchase_date DATE,                         -- 购买日期
    wear_count INTEGER DEFAULT 0,               -- 穿着次数
    last_worn_date DATE,                        -- 最后穿着日期
    is_favorite BOOLEAN DEFAULT FALSE,          -- 是否收藏
    notes TEXT,                                 -- 备注
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 5. 反馈日志表 (feedback_logs) - Week 4 新增
-- 存储用户对推荐结果的反馈
-- =====================================================
CREATE TABLE feedback_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 推荐上下文
    session_id VARCHAR(36),                     -- 推荐会话ID
    query_text TEXT,                            -- 用户查询
    scene VARCHAR(50),                          -- 场景
    
    -- 反馈内容
    item_id INTEGER,                            -- user_wardrobe.id
    item_code VARCHAR(20),                      -- 或公共库物品 item_code
    item_source VARCHAR(20),                    -- 'wardrobe' 或 'public'
    action VARCHAR(10) NOT NULL,                -- 'like' 或 'dislike'
    feedback_reason TEXT,                       -- 反馈原因（可选）
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 6. 创建索引
-- =====================================================

-- items 表索引
CREATE UNIQUE INDEX idx_items_item_code ON items(item_code);
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_items_primary_element ON items(primary_element);
CREATE INDEX idx_items_gender ON items(gender);
CREATE INDEX idx_items_embedding ON items 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- users 表索引
CREATE INDEX idx_users_user_code ON users(user_code);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_email ON users(email);

-- user_wardrobe 表索引
CREATE INDEX idx_wardrobe_user_element ON user_wardrobe(user_id, primary_element);
CREATE INDEX idx_wardrobe_user_active ON user_wardrobe(user_id, is_active);
CREATE INDEX idx_wardrobe_user_custom ON user_wardrobe(user_id, is_custom);
CREATE INDEX idx_wardrobe_gender ON user_wardrobe(gender);
CREATE INDEX idx_wardrobe_applicable_weather ON user_wardrobe USING gin(applicable_weather);
CREATE INDEX idx_wardrobe_applicable_seasons ON user_wardrobe USING gin(applicable_seasons);
CREATE INDEX idx_wardrobe_functionality ON user_wardrobe USING gin(functionality);
CREATE INDEX idx_wardrobe_embedding ON user_wardrobe 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- feedback_logs 表索引
CREATE INDEX idx_feedback_user ON feedback_logs(user_id);
CREATE INDEX idx_feedback_session ON feedback_logs(session_id);
CREATE INDEX idx_feedback_item ON feedback_logs(item_id, item_source);

-- =====================================================
-- 7. 添加字段注释
-- =====================================================

COMMENT ON COLUMN user_wardrobe.is_custom IS 'TRUE=用户自定义衣物，FALSE=引用公共库物品';
COMMENT ON COLUMN user_wardrobe.embedding IS '向量嵌入，用于语义搜索';
COMMENT ON COLUMN user_wardrobe.attributes_detail IS 'AI分析结果: {"color": "红色", "material": "丝绸", "style": "正式", "season": ["夏"], "tags": ["商务"]}';
COMMENT ON COLUMN user_wardrobe.gender IS '性别适配: 男/女/中性';
COMMENT ON COLUMN user_wardrobe.applicable_weather IS '适用天气: ["晴", "多云", "阴", "雨", "雪", "霾"]';
COMMENT ON COLUMN user_wardrobe.applicable_seasons IS '适用季节: ["春", "夏", "秋", "冬"]';
COMMENT ON COLUMN user_wardrobe.temperature_range IS '温度范围: {"min": 15, "max": 25}';
COMMENT ON COLUMN user_wardrobe.functionality IS '功能场景: ["面试", "约会", "商务", "日常", "运动", "派对", "居家", "旅行"]';
COMMENT ON COLUMN user_wardrobe.thickness_level IS '厚度等级: 轻薄/适中/加厚/厚重';
COMMENT ON COLUMN user_wardrobe.energy_intensity IS '能量强度(0.0-1.0)，用于八字喜用神匹配';

COMMENT ON TABLE feedback_logs IS '推荐反馈记录表';
COMMENT ON COLUMN feedback_logs.item_source IS 'wardrobe=私有衣橱物品，public=公共库物品';
COMMENT ON COLUMN feedback_logs.action IS 'like=点赞，dislike=点踩';

-- =====================================================
-- 8. 插入基础五行配置数据
-- =====================================================
INSERT INTO five_element_configs (element_name, colors, materials, styles, energy_description, energy_strength_range) VALUES
(
    '金',
    '["白色", "金色", "银色", "米白", "香槟金", "乳白", "象牙白", "银灰", "玫瑰金", "纯白", "珍珠白", "白金", "亮银", "香槟", "深灰", "烟灰", "铁灰", "枪灰", "炭灰", "钛灰", "米灰"]'::jsonb,
    '["金属", "皮革", "牛仔", "亮片", "缎面", "雪纺", "亚麻", "帆布", "羊毛", "棉", "锦缎", "蕾丝", "网纱"]'::jsonb,
    '["正方", "圆形", "对称", "利落"]'::jsonb,
    '果断、坚毅、收敛，代表收敛与净化的能量',
    '[0.7, 1.0]'::jsonb
),
(
    '木',
    '["绿色", "青色", "翠绿", "墨绿", "薄荷绿", "草绿", "橄榄绿", "蓝绿", "军绿", "帝王绿", "竹绿", "苔藓绿", "松绿", "森林绿", "荧光绿"]'::jsonb,
    '["棉麻", "亚麻", "棉", "灯芯绒", "针织", "羊毛", "绒布", "网纱", "粗花呢", "摇粒绒"]'::jsonb,
    '["长方", "竖条", "自然", "宽松"]'::jsonb,
    '生长、仁慈、创新，代表生发与舒展的能量',
    '[0.7, 1.0]'::jsonb
),
(
    '水',
    '["黑色", "蓝色", "深蓝", "藏青", "海军蓝", "宝蓝", "靛蓝", "午夜蓝", "冰川蓝", "银蓝", "湖蓝", "群青", "天蓝", "水洗蓝", "灰蓝", "孔雀蓝", "雾霾蓝", "普鲁士蓝", "矢车菊蓝", "深青", "青绿", "纯黑", "炭黑", "亮黑", "哑光黑", "水洗黑", "幻彩黑"]'::jsonb,
    '["真丝", "丝绸", "雪纺", "网纱", "天鹅绒", "丝绒", "蕾丝", "涤纶", "人造丝", "莫代尔", "醋酸", "仿真丝", "缎面", "乔其纱", "欧根纱"]'::jsonb,
    '["波浪", "弧形", "流动", "不规则"]'::jsonb,
    '智慧、灵动、深沉，代表润下与收藏的能量',
    '[0.7, 1.0]'::jsonb
),
(
    '火',
    '["正红", "红色", "紫色", "橙色", "粉色", "酒红", "粉红", "橙红", "紫红", "珊瑚色", "朱红", "砖红", "玫红", "樱花粉", "珊瑚粉", "藕粉", "香芋紫", "薰衣草紫", "电光紫", "深紫", "紫罗兰", "酱紫", "亮橙", "铁锈红", "鸽血红", "赤褐", "深紫褐", "干枯玫瑰"]'::jsonb,
    '["真丝", "丝绸", "天鹅绒", "丝绒", "蕾丝", "针织", "羊毛", "灯芯绒", "皮草", "人造革", "麂皮", "磨毛", "植绒", "提花", "泡泡纱"]'::jsonb,
    '["三角", "尖角", "放射", "张扬"]'::jsonb,
    '热情、活力、光明，代表炎上与发散的能量',
    '[0.8, 1.0]'::jsonb
),
(
    '土',
    '["黄色", "棕色", "米色", "卡其色", "驼色", "咖啡色", "杏色", "土黄", "沙色", "军卡其", "卡其", "麦秆", "原木", "蜜糖琥珀", "米棕", "赭石", "咖啡棕", "巧克力", "深咖", "姜黄", "奶油黄", "鹅黄", "明黄", "古铜"]'::jsonb,
    '["棉", "麻", "羊毛", "呢料", "灯芯绒", "绒布", "粗花呢", "针织", "摇粒绒", "法兰绒", "羊绒", "马海毛", "牦牛毛", "仿皮草", "毛呢"]'::jsonb,
    '["正方", "稳重", "对称", "厚实"]'::jsonb,
    '稳重、包容、信任，代表承载与稳定的能量',
    '[0.7, 1.0]'::jsonb
);

-- =====================================================
-- 9. 创建更新时间触发器函数
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为各表创建触发器
CREATE TRIGGER update_five_element_configs_updated_at
    BEFORE UPDATE ON five_element_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_wardrobe_updated_at
    BEFORE UPDATE ON user_wardrobe
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 初始化完成
-- =====================================================
