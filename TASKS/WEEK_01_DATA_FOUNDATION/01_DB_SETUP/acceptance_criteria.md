# 验收标准: 数据库环境搭建 (01_DB_SETUP)

**任务**: 数据库环境搭建  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 容器运行状态

- [ ] **启动无报错**: 执行 `docker-compose up -d` 无错误输出
- [ ] **容器状态正常**: `docker ps` 显示 `db` 容器状态为 `Up`

**验证命令**:
```bash
docker-compose up -d
docker ps | grep db
```

---

### 2. pgvector 扩展激活

- [ ] **扩展已安装**: 查询 `pg_extension` 表返回 `vector` 记录

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**预期输出**:
```
 extname | extversion | ...
---------+------------+-----
 vector  | 0.x        | ...
```

---

### 3. 表结构验证

- [ ] **核心表存在**: `\dt` 显示 `items`, `five_element_configs` 等表

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "\dt"
```

- [ ] **向量列类型正确**: `embedding` 列类型为 `vector(1024)`

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "\d items"
```

**预期输出包含**:
```
 embedding | vector(1024) |
```

---

### 4. 索引验证

- [ ] **唯一索引存在**: `idx_items_item_code` 或类似名称
- [ ] **向量索引存在**: HNSW 索引已创建

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'items';"
```

---

### 5. 基础数据验证

- [ ] **五行配置数据**: `five_element_configs` 表至少 5 条记录

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT element_name FROM five_element_configs;"
```

**预期输出**:
```
 element_name
--------------
 金
 木
 水
 火
 土
```

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 容器运行 | ⬜ | |
| 扩展激活 | ⬜ | |
| 表结构 | ⬜ | |
| 向量列类型 | ⬜ | |
| 索引创建 | ⬜ | |
| 基础数据 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________
