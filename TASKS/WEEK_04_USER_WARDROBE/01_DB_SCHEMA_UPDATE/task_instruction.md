# 任务 1: 数据库扩展 (01_DB_SCHEMA_UPDATE)

**优先级**: 🔴 高  
**预估时间**: 1.5-2 小时  
**依赖**: Week 1-3 已完成，PostgreSQL + pgvector 可用

---

## 📋 任务目标

**扩展现有数据库表**，支持用户自定义衣物存储和反馈记录：

| 表名 | 现状 | 本次操作 |
|:---|:---|:---|
| `users` | ✅ 已存在（Week 1 创建） | 无需修改 |
| `user_wardrobe` | ⚠️ 已存在但功能有限 | **扩展字段**：添加自定义衣物支持 + embedding |
| `feedback_logs` | ❌ 不存在 | **新建**：推荐反馈记录 |

---

## 📊 现有表结构分析

### users 表（已存在，无需修改）

```sql
-- scripts/init_db.sql 中已定义
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_code VARCHAR(36) UNIQUE NOT NULL,  -- UUID
    phone VARCHAR(20) UNIQUE,
    nickname VARCHAR(100),
    avatar_url VARCHAR(500),
    bazi JSONB,                    -- 八字信息缓存
    xiyong_elements JSONB,         -- 喜用神缓存
    ...
);
```

### user_wardrobe 表（已存在，需扩展）

```sql
-- 现有结构：仅支持引用公共库物品
CREATE TABLE user_wardrobe (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    item_code VARCHAR(20) REFERENCES items(item_code),  -- 仅公共库物品
    wear_count INTEGER DEFAULT 0,
    ...
    -- ❌ 缺少: 自定义衣物名称、embedding、五行属性等
);
```

---

## 🔧 执行步骤

### 步骤 1: 创建迁移脚本目录

```bash
mkdir -p scripts/migrations
```

---

### 步骤 2: 创建迁移脚本（扩展 + 新建）

创建 `scripts/migrations/01_extend_wardrobe_tables.sql`：

```sql
-- ============================================
-- Week 4: 扩展用户衣橱 + 新建反馈表
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

-- ============================================
-- 4. 更新触发器（如果不存在）
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
-- 验证迁移
-- ============================================
-- 运行后执行以下命令验证：
-- \d user_wardrobe
-- \d feedback_logs
-- 确认新列和索引存在
```

---

### 步骤 3: 执行迁移

```bash
# 确保 PostgreSQL 容器运行
docker compose up -d db

# 执行迁移脚本
docker exec -i wuxing-db psql -U wuxing_user -d wuxing_db < scripts/migrations/01_extend_wardrobe_tables.sql
```

---

### 步骤 4: 更新 ORM 模型

创建 `apps/api/models/wardrobe.py`，**匹配现有表结构**：

```python
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """用户表 - 匹配现有结构"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)  # SERIAL 主键
    user_code = Column(String(36), unique=True, nullable=True)
    phone = Column(String(20), unique=True)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255))
    nickname = Column(String(100))
    avatar_url = Column(String(500))
    gender = Column(String(10))
    birth_date = Column(DateTime)
    birth_time = Column(DateTime)
    birth_location = Column(String(200))
    bazi = Column(JSONB)               # 八字信息缓存
    xiyong_elements = Column(JSONB)    # 喜用神缓存
    preferred_elements = Column(JSONB)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    wardrobe_items = relationship("UserWardrobeItem", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("FeedbackLog", back_populates="user", cascade="all, delete-orphan")


class UserWardrobeItem(Base):
    """用户衣橱表 - 扩展后结构"""
    __tablename__ = "user_wardrobe"
    
    id = Column(Integer, primary_key=True)  # SERIAL 主键
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # 原有字段（引用公共库物品）
    item_code = Column(String(20), ForeignKey("items.item_code"), nullable=True)  # 改为可空
    purchase_date = Column(DateTime)
    wear_count = Column(Integer, default=0)
    last_worn_date = Column(DateTime)
    is_favorite = Column(Boolean, default=False)
    notes = Column(Text)
    
    # 新增字段（自定义衣物支持）
    name = Column(String(255))                # 自定义名称
    category = Column(String(50))              # 分类
    image_url = Column(String(500))            # 图片URL
    primary_element = Column(String(10))       # 主五行
    secondary_element = Column(String(10))     # 次五行
    attributes_detail = Column(JSONB)          # AI分析结果
    embedding = Column(Vector(1024))           # 向量嵌入
    is_custom = Column(Boolean, default=False) # 是否自定义
    is_active = Column(Boolean, default=True)  # 软删除
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="wardrobe_items")


class FeedbackLog(Base):
    """推荐反馈表 - 新建"""
    __tablename__ = "feedback_logs"
    
    id = Column(Integer, primary_key=True)  # SERIAL 主键
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # 推荐上下文
    session_id = Column(String(36))           # 会话ID
    query_text = Column(Text)                 # 用户查询
    scene = Column(String(50))                # 场景
    
    # 反馈内容
    item_id = Column(Integer)                 # user_wardrobe.id
    item_code = Column(String(20))            # 或公共库物品 item_code
    item_source = Column(String(20))          # 'wardrobe' 或 'public'
    action = Column(String(10), nullable=False)  # 'like' 或 'dislike'
    feedback_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="feedbacks")
```

---

### 步骤 5: 创建 `apps/api/models/__init__.py`

```python
from .wardrobe import User, UserWardrobeItem, FeedbackLog

__all__ = ["User", "UserWardrobeItem", "FeedbackLog"]
```

---

## 📁 输出文件清单

| 文件路径 | 操作 |
|:---|:---|
| `scripts/migrations/01_extend_wardrobe_tables.sql` | 新建 |
| `apps/api/models/wardrobe.py` | 新建 |
| `apps/api/models/__init__.py` | 新建 |

---

## ⚠️ 注意事项

1. **扩展而非重建**: 使用 `ALTER TABLE` 扩展现有表，不删除任何数据
2. **向量维度一致性**: `user_wardrobe.embedding` 必须与公共库 `items.embedding` 维度一致（1024）
3. **级联删除**: 用户删除时，衣橱和反馈记录自动删除（外键约束）
4. **权限控制**: 向量搜索必须在 WHERE 子句中强制加上 `user_id = ?`，防止数据越权
5. **主键类型**: 现有表使用 `SERIAL` (Integer)，新 ORM 模型需匹配
6. **双模式支持**: `user_wardrobe` 同时支持引用公共库物品 (`item_code`) 和自定义衣物 (`name`, `embedding`)
