# 验收标准: 八字与五行计算工具库 (02_UTILS_BAZI)

**任务**: 八字与五行计算工具库  
**验收人**: _______  
**验收日期**: _______

---

## ✅ 验收清单

### 1. 文件结构验证

- [ ] `packages/utils/` 下所有文件存在

**验证命令**：
```bash
ls packages/utils/
# 预期：__init__.py  bazi_calculator.py  wuxing_rules.py  scene_mapper.py
```

---

### 2. 已知案例验证（四柱正确性）

- [ ] 输入已知生日，四柱输出符合传统八字排盘结果

**验证命令**：
```bash
source .venv/bin/activate
PYTHONPATH=. python3 -c "
from packages.utils.bazi_calculator import calculate_bazi
result = calculate_bazi(1995, 6, 15, 10, '男')
print('四柱:', result['pillars'])
print('八字:', result['eight_chars'])
print('五行统计:', result['five_elements_count'])
print('日元:', result['day_master'])
print('喜用神:', result['suggested_elements'])
print('推理:', result['reasoning'])
"
```

**验收标准**：
- [ ] `pillars` 包含年柱、月柱、日柱、时柱（非空字符串）
- [ ] `eight_chars` 长度 = 8
- [ ] `five_elements_count` 包含金木水火土五个键，数值之和 = 8
- [ ] `suggested_elements` 非空列表
- [ ] `reasoning` 包含日元和季节信息的中文说明

---

### 3. 喜用神逻辑验证（抑强扶弱原则）

- [ ] 日元弱时，推荐生扶日元的五行

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.utils.bazi_calculator import calculate_bazi

# 夏天出生（火旺）的木日元，应喜水
result = calculate_bazi(1990, 7, 15, 12, '女')
print('夏木案例:', result['day_master'], result['month_element'])
print('喜用神:', result['suggested_elements'])
assert '水' in result['suggested_elements'] or '木' in result['suggested_elements'], \
    '夏木应喜水或木'

# 冬天出生（水旺）的火日元，应喜木
result2 = calculate_bazi(1988, 12, 20, 14, '男')
print('冬火案例:', result2['day_master'], result2['month_element'])
print('喜用神:', result2['suggested_elements'])
print('逻辑验证通过')
"
```

---

### 4. 无八字降级验证

- [ ] `bazi=None` 时，仅基于场景和文本推断，不报错

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.utils.bazi_calculator import merge_recommendations
result = merge_recommendations(
    bazi_result=None,
    intent_result={'elements': ['金'], 'method': 'rule'},
    scene_result={'primary': ['金'], 'secondary': ['水']}
)
print('无八字推荐五行:', result)
assert len(result) > 0, '结果不应为空'
print('降级逻辑 OK')
"
```

---

### 5. 关键词意图推断验证

- [ ] 规则命中时返回 `method="rule"`
- [ ] 无命中时返回 `method="llm_needed"`

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.utils.bazi_calculator import infer_elements_from_text

# 规则命中案例
r1 = infer_elements_from_text('明天要去面试，想显得专业干练')
print('面试案例:', r1)
assert r1['method'] == 'rule', '应命中规则'
assert '金' in r1['elements'], '面试应推断金属性'

# 无命中案例（生僻词）
r2 = infer_elements_from_text('想要一种量子纠缠的感觉')
print('无命中案例:', r2)
assert r2['method'] == 'llm_needed', '无关键词应触发 LLM 兜底'
print('意图推断 OK')
"
```

---

### 6. 场景五行映射验证

- [ ] 所有预定义场景都能正确返回五行

**验证命令**：
```bash
PYTHONPATH=. python3 -c "
from packages.utils.scene_mapper import get_color_by_element, extract_scene_from_text

# 颜色映射
for elem in ['金', '木', '水', '火', '土']:
    colors = get_color_by_element(elem)
    assert len(colors) > 0, f'{elem}颜色列表不应为空'
    print(f'{elem}→', colors)

# 场景提取
scene = extract_scene_from_text('明天要去参加面试')
print('提取场景:', scene)
assert scene in ['面试', None], '应提取面试或返回None'
print('场景工具 OK')
"
```

---

### 7. 单元测试验证

- [ ] `tests/test_bazi.py` 存在
- [ ] 所有测试用例通过

**验证命令**：
```bash
PYTHONPATH=. python3 -m pytest tests/test_bazi.py -v
```

**预期输出**：所有测试 `PASSED`，无 `FAILED`

**tests/test_bazi.py 必须包含的测试用例**：
- `test_bazi_four_pillars`：四柱格式正确
- `test_five_elements_sum_equals_eight`：五行统计之和=8
- `test_suggested_elements_not_empty`：喜用神非空
- `test_keyword_rule_match`：规则关键词匹配
- `test_no_bazi_fallback`：无八字降级不报错

---

## 📊 验收结果

| 检查项 | 状态 | 备注 |
|:---|:---:|:---|
| 文件结构完整 | ⬜ | |
| 四柱计算正确 | ⬜ | |
| 喜用神逻辑合理 | ⬜ | |
| 无八字降级正常 | ⬜ | |
| 关键词意图推断 | ⬜ | |
| 场景五行映射 | ⬜ | |
| 单元测试全通过 | ⬜ | |

---

## ✍️ 验收签字

**验收结论**: ⬜ 通过 / ⬜ 不通过

**问题记录**:
```
(如有问题请在此记录)
```

**签字**: ________________ **日期**: ________________
