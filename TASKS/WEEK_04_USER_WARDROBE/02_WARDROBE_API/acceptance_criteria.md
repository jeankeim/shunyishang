# 验收标准: 衣橱 CRUD 与 AI 自动打标 (02_WARDROBE_API)

**任务**: 衣橱 CRUD 与 AI 自动打标  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. AI 打标预览验证

- [ ] `POST /api/v1/wardrobe/items/preview-tagging` 接口正常
- [ ] AI 能正确识别五行属性
- [ ] 返回完整的分析结果

**验证命令**：
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","password":"test123456"}' | jq -r '.access_token')

curl -s -X POST http://localhost:8000/api/v1/wardrobe/items/preview-tagging \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "一件黑色的丝绸衬衫"}' | python3 -m json.tool
```

**预期输出**：
```json
{
  "primary_element": "水",
  "secondary_element": "木",
  "color": "黑色",
  "material": "丝绸",
  "style": "正式",
  "season": ["春", "夏", "秋"],
  "tags": ["商务", "正式"],
  "suggested_name": "黑色丝绸衬衫"
}
```

---

### 2. 添加衣物验证

- [ ] `POST /api/v1/wardrobe/items` 接口正常
- [ ] 数据库记录正确创建
- [ ] embedding 向量已生成

**验证命令**：
```bash
curl -s -X POST http://localhost:8000/api/v1/wardrobe/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "红色羊毛大衣"}' | python3 -m json.tool
```

---

### 3. 获取列表验证

- [ ] `GET /api/v1/wardrobe/items` 接口正常
- [ ] 五行筛选正常
- [ ] 分类筛选正常

---

### 4. 更新衣物验证

- [ ] `PATCH /api/v1/wardrobe/items/{id}` 接口正常
- [ ] 可修正 AI 识别错误

---

### 5. 删除衣物验证

- [ ] `DELETE /api/v1/wardrobe/items/{id}` 软删除生效

---

### 6. AI 打标准确性测试

| 描述 | 预期主五行 | 实际结果 | 是否正确 |
|:---|:---:|:---:|:---:|
| 红色真丝衬衫 | 火 | | ⬜ |
| 黑色羊毛大衣 | 水 | | ⬜ |
| 白色棉麻T恤 | 金/木 | | ⬜ |

**验收标准**: 准确率 > 80%

---

### 7. 用户隔离验证

- [ ] 用户 A 看不到用户 B 的衣橱
- [ ] 用户 A 不能操作用户 B 的物品

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| AI 打标预览 | ⬜ | |
| 添加衣物 | ⬜ | |
| embedding 生成 | ⬜ | |
| 获取列表 | ⬜ | |
| 更新衣物 | ⬜ | |
| 删除衣物 | ⬜ | |
| AI 准确率 > 80% | ⬜ | |
| 用户隔离 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**签字**: ________________ **日期**: ________________
