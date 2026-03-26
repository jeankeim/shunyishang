# 验收标准: ETL 流水线 (02_ETL_PIPELINE)

**任务**: ETL 流水线  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 脚本运行状态

- [ ] **无异常**: 执行 `python scripts/import_seed.py` 全程无 Python 异常
- [ ] **日志完整**: 显示进度日志，最终输出成功条数

**验证命令**:
```bash
python scripts/import_seed.py
```

**预期输出包含**:
```
[SUCCESS] 导入完成: 100 条成功, 0 条失败
```

---

### 2. 数据总量验证

- [ ] **记录数正确**: 数据库中 `items` 表记录数为 **100**

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT count(*) FROM items;"
```

**预期输出**:
```
 count
-------
   100
```

---

### 3. 向量非空验证

- [ ] **无空向量**: 所有记录的 `embedding` 字段均非空

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT count(*) FROM items WHERE embedding IS NULL;"
```

**预期输出**:
```
 count
-------
     0
```

---

### 4. 内容完整性验证

- [ ] **JSONB 完整**: `attributes_detail` 字段保留了原始 JSON 结构
- [ ] **结构化字段正确**: `primary_element`, `category` 等字段已正确提取

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT item_code, name, primary_element, category FROM items LIMIT 3;"
```

**预期输出示例**:
```
 item_code |      name       | primary_element | category
-----------+-----------------+-----------------+----------
 ITEM_001  | 正红色真丝衬衫   | 火              | 上装
 ITEM_002  | 藏青色羊毛西装外套 | 水            | 外套
 ITEM_003  | 草绿色棉麻连衣裙 | 木              | 裙装
```

---

### 5. 向量维度验证

- [ ] **维度正确**: 向量维度为 1024

**验证命令**:
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c "SELECT item_code, vector_dims(embedding) as dims FROM items LIMIT 1;"
```

**预期输出**:
```
 item_code | dims
-----------+------
 ITEM_001  | 1024
```

---

### 6. 性能验证

- [ ] **处理时间**: 100 条数据的处理时间应在 1-2 分钟内 (取决于 CPU/GPU)

**验证方法**:
```bash
time python scripts/import_seed.py
```

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 脚本运行 | ⬜ | |
| 数据总量 (100条) | ⬜ | |
| 向量非空 | ⬜ | |
| JSONB 完整 | ⬜ | |
| 结构化字段 | ⬜ | |
| 向量维度 (1024) | ⬜ | |
| 性能 (1-2分钟) | ⬜ | |

---

## 📝 数据抽查记录

**随机抽查物品 ID**: ________________

| 字段 | 预期值 | 实际值 | 状态 |
|:---|:---|:---|:---:|
| name | | | ⬜ |
| primary_element | | | ⬜ |
| category | | | ⬜ |
| attributes_detail | | | ⬜ |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________
