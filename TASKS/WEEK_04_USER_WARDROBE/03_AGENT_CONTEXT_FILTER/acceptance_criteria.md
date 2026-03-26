# 验收标准: Agent 上下文过滤 (03_AGENT_CONTEXT_FILTER)

**任务**: Agent 上下文过滤  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 状态扩展验证

- [ ] AgentState 包含 `retrieval_mode` 字段
- [ ] AgentState 包含 `user_id` 字段
- [ ] AgentState 包含 `item_sources` 字段

---

### 2. 模式 A（公共库）验证

- [ ] `retrieval_mode='public'` 时仅从公共库检索
- [ ] 返回物品 `source='public'`

**验证命令**：
```bash
curl -N http://localhost:8000/api/v1/recommend/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "面试穿什么", "retrieval_mode": "public"}'
```

**预期**：返回公共库物品，语气为"建议您..."

---

### 3. 模式 B（私有衣橱）验证

- [ ] `retrieval_mode='wardrobe'` 时仅从用户衣橱检索
- [ ] 衣橱为空时返回友好提示

**验证命令**：
```bash
curl -N http://localhost:8000/api/v1/recommend/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "明天开会穿什么", "retrieval_mode": "wardrobe"}'
```

**预期**：返回用户衣橱物品，语气为"您可以穿您拥有的..."

---

### 4. 模式 C（混合推荐）验证

- [ ] 优先返回用户衣橱物品
- [ ] 衣橱不足时补充公共库
- [ ] 清晰区分"自有"和"建议购入"

---

### 5. 场景测试：用户衣橱仅有白衬衫

**预期**：Agent 推荐白衬衫，**不能**推荐用户没有的"紫色礼服"

---

### 6. 权限隔离验证

- [ ] 用户 A 的衣橱数据不会泄露给用户 B

**SQL 权限验证**：
```bash
docker exec -it wuxing-db psql -U wuxing_user -d wuxing_db -c \
  "EXPLAIN ANALYZE 
   SELECT * FROM user_wardrobe 
   WHERE user_id = 'xxx' AND embedding IS NOT NULL 
   ORDER BY embedding <=> '[0.1,...]'::vector LIMIT 5;"
```

**预期**：查询计划使用 `idx_wardrobe_user` 索引

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 状态字段扩展 | ⬜ | |
| 模式 A 正常 | ⬜ | |
| 模式 B 正常 | ⬜ | |
| 空衣橱提示 | ⬜ | |
| 模式 C 混合 | ⬜ | |
| 自有/建议区分 | ⬜ | |
| 权限隔离 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**签字**: ________________ **日期**: ________________
