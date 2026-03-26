# 验收标准: 数据库扩展 (01_DB_SCHEMA_UPDATE)

**任务**: 数据库扩展  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 迁移脚本验证

- [ ] `scripts/migrations/01_extend_wardrobe_tables.sql` 文件存在
- [ ] 脚本语法正确，无 SQL 错误

**验证命令**：
```bash
cat scripts/migrations/01_extend_wardrobe_tables.sql | head -20
```

---

### 2. user_wardrobe 表扩展验证

- [ ] 新增字段已添加成功
- [ ] `embedding` vector(1024) 字段存在
- [ ] `item_code` 已改为可空

**验证命令**：
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "\d user_wardrobe"
```

**预期输出包含新字段**：
```
                Table "public.user_wardrobe"
     Column       |            Type             
------------------+-----------------------------
 id               | integer                     -- 原有主键
 user_id          | integer                     -- 原有
 item_code        | character varying(20)       -- 改为可空
 name             | character varying(255)      -- 新增
 category         | character varying(50)       -- 新增
 image_url        | character varying(500)      -- 新增
 primary_element  | character varying(10)       -- 新增
 secondary_element| character varying(10)       -- 新增
 attributes_detail| jsonb                       -- 新增
 embedding        | vector(1024)                -- 新增
 is_custom        | boolean                     -- 新增
 is_active        | boolean                     -- 新增
 wear_count       | integer                     -- 原有
 ...
```

---

### 3. feedback_logs 表验证

- [ ] `feedback_logs` 表创建成功
- [ ] 外键约束正确

**验证命令**：
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "\d feedback_logs"
```

**预期输出**：
```
              Table "public.feedback_logs"
     Column       |            Type             
------------------+-----------------------------
 id               | integer                     -- SERIAL 主键
 user_id          | integer                     -- 外键
 session_id       | character varying(36)
 query_text       | text
 scene            | character varying(50)
 item_id          | integer
 item_code        | character varying(20)
 item_source      | character varying(20)
 action           | character varying(10)       -- NOT NULL
 feedback_reason  | text
 created_at       | timestamp
```

---

### 4. 索引验证

- [ ] `user_wardrobe` 表有 HNSW 向量索引
- [ ] `user_wardrobe` 表有 user_id 相关索引
- [ ] `feedback_logs` 表有相关索引

**验证命令**：
```bash
# 检查 user_wardrobe 索引
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "SELECT indexname FROM pg_indexes WHERE tablename = 'user_wardrobe';"
```

**预期输出包含**：
```
idx_wardrobe_user_element
idx_wardrobe_user_active
idx_wardrobe_user_custom
idx_wardrobe_embedding  (USING hnsw)
```

---

### 5. 数据兼容性验证

- [ ] 现有数据不受影响
- [ ] 新字段默认值正确

**验证命令**：
```bash
# 检查现有数据是否完整
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM user_wardrobe;"

# 检查新字段默认值
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "SELECT is_custom, is_active FROM user_wardrobe LIMIT 5;"
# 预期：is_custom = false, is_active = true
```

---

### 6. 向量列验证

- [ ] 可以插入向量数据
- [ ] 向量搜索语法正确

**验证命令**：
```bash
# 插入带向量的测试数据（自定义衣物）
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "INSERT INTO user_wardrobe (user_id, name, primary_element, embedding, is_custom)
   SELECT id, '向量测试衣物', '火', 
          '[' || repeat('0.1,', 1023) || '0.1]'::vector, true
   FROM users LIMIT 1;"

# 验证向量搜索
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "SELECT name, is_custom, 1 - (embedding <=> '[0.1,...]'::vector) as similarity 
   FROM user_wardrobe WHERE embedding IS NOT NULL LIMIT 5;"

# 清理测试数据
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "DELETE FROM user_wardrobe WHERE name = '向量测试衣物';"
```

---

### 7. ORM 模型验证

- [ ] `apps/api/models/wardrobe.py` 文件存在
- [ ] 模型可以正常导入
- [ ] 模型字段与数据库表匹配

**验证命令**：
```bash
source .venv/bin/activate
python3 -c "
from apps.api.models.wardrobe import User, UserWardrobeItem, FeedbackLog

# 验证 User 模型
print('User fields:', [c.name for c in User.__table__.columns])
assert 'id' in [c.name for c in User.__table__.columns]
assert 'user_code' in [c.name for c in User.__table__.columns]

# 验证 UserWardrobeItem 模型
print('UserWardrobeItem fields:', [c.name for c in UserWardrobeItem.__table__.columns])
assert 'id' in [c.name for c in UserWardrobeItem.__table__.columns]
assert 'item_code' in [c.name for c in UserWardrobeItem.__table__.columns]
assert 'name' in [c.name for c in UserWardrobeItem.__table__.columns]
assert 'embedding' in [c.name for c in UserWardrobeItem.__table__.columns]
assert 'is_custom' in [c.name for c in UserWardrobeItem.__table__.columns]

print('ORM Model OK')
"
```

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 迁移脚本存在 | ⬜ | |
| user_wardrobe 扩展正确 | ⬜ | |
| embedding 字段存在 | ⬜ | |
| item_code 可空 | ⬜ | |
| feedback_logs 表正确 | ⬜ | |
| 向量索引存在 | ⬜ | |
| 现有数据完整 | ⬜ | |
| 向量搜索可用 | ⬜ | |
| ORM 模型可导入 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________