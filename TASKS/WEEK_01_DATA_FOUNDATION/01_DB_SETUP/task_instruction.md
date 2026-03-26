# 任务 1: 数据库环境搭建 (01_DB_SETUP)

**优先级**: 🔴 高  
**预估时间**: 1-2 小时  
**依赖**: 无

---

## 📋 任务目标

搭建支持 `pgvector` 扩展的 PostgreSQL 数据库环境，创建必要的表结构和索引。

---

## 🔧 执行步骤

### 步骤 1: 生成 `docker-compose.yml` (项目根目录)

**服务配置要求**:

| 配置项 | 值 |
|:---|:---|
| 服务名 | `db` |
| 镜像 | `pgvector/pgvector:pg16` |
| 环境变量 | `POSTGRES_USER=wuxing_user` |
| | `POSTGRES_PASSWORD=wuxing_password` |
| | `POSTGRES_DB=wuxing_db` |
| 端口映射 | `5432:5432` |
| 数据卷 | `./data/postgres` → `/var/lib/postgresql/data` |
| 初始化脚本 | `./scripts/init_db.sql` → `/docker-entrypoint-initdb.d/init_db.sql` |

**(可选) 添加 pgadmin 服务**:
- 镜像: `dpage/pgadmin4`
- 端口: `5050:80`
- 用于可视化调试

### 步骤 2: 生成 `scripts/init_db.sql`

**必须包含的内容**:

1. **启用扩展**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **创建表 `five_element_configs`**:
   - 存储金木水火土的基础定义和颜色映射
   - 字段: `id`, `element_name`, `colors` (JSONB), `materials` (JSONB), `styles` (JSONB), `description`

3. **创建表 `items`**:
   | 字段 | 类型 | 说明 |
   |:---|:---|:---|
   | `item_code` | VARCHAR(20) | PK, 物品编码 (ITEM_001) |
   | `name` | VARCHAR(255) | 物品名称 |
   | `category` | VARCHAR(50) | 分类 (上装/下装/外套/裙装/鞋履/配饰) |
   | `primary_element` | VARCHAR(10) | 主五行 |
   | `secondary_element` | VARCHAR(10) | 次五行 |
   | `energy_intensity` | FLOAT | 能量强度 (0.0-1.0) |
   | `attributes_detail` | JSONB | 完整属性详情 |
   | `embedding` | VECTOR(1024) | 语义向量 (BGE-M3 维度) |
   | `created_at` | TIMESTAMP | 创建时间 |

4. **创建预留表**:
   - `users`: 用户表 (预留字段)
   - `user_wardrobe`: 用户衣橱 (预留字段)
   - `recommendation_logs`: 推荐日志 (预留字段)

5. **创建索引**:
   ```sql
   -- 唯一索引
   CREATE UNIQUE INDEX idx_items_item_code ON items(item_code);
   
   -- HNSW 向量索引 (关键!)
   CREATE INDEX idx_items_embedding ON items 
   USING hnsw (embedding vector_cosine_ops)
   WITH (m = 16, ef_construction = 64);
   ```

6. **插入基础五行配置数据**:
   - 至少 5 条记录: 金, 木, 水, 火, 土

---

## 📁 输出文件

| 文件路径 | 说明 |
|:---|:---|
| `/docker-compose.yml` | Docker 编排文件 |
| `/scripts/init_db.sql` | 数据库初始化脚本 |

---

## ⚠️ 注意事项

1. 向量维度必须设为 **1024** 以匹配 BGE-M3 模型
2. HNSW 索引参数 `m=16, ef_construction=64` 适合中小规模数据
3. 数据卷挂载确保数据持久化
4. 初始化脚本只在容器首次创建时执行
