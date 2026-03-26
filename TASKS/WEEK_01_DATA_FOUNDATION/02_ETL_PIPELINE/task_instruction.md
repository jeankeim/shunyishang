# 任务 2: ETL 流水线 (02_ETL_PIPELINE)

**优先级**: 🔴 高  
**预估时间**: 2-3 小时  
**依赖**: 任务 1 (数据库环境搭建完成)

---

## 📋 任务目标

编写 Python 脚本将静态 JSON 数据转化为向量数据存入数据库，完成 100 条种子数据的向量化导入。

---

## 🔧 执行步骤

### 步骤 1: 依赖安装

**提示用户安装以下依赖**:
```bash
pip install psycopg2-binary sentence-transformers pandas python-dotenv
```

| 包名 | 用途 |
|:---|:---|
| `psycopg2-binary` | PostgreSQL 数据库连接 |
| `sentence-transformers` | 加载 BGE-M3 模型生成向量 |
| `pandas` | 数据处理 |
| `python-dotenv` | 环境变量管理 |

---

### 步骤 2: 模型加载

**配置要求**:
```python
from sentence_transformers import SentenceTransformer

# 加载模型
model = SentenceTransformer('BAAI/bge-m3')

# 设备选择
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)
```

---

### 步骤 3: 数据读取

**读取文件**: `data/seeds/seed_data_100.json`

```python
import json

with open('data/seeds/seed_data_100.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"读取 {len(items)} 条数据")
```

---

### 步骤 4: 文本构建策略 (关键)

**编写函数 `build_context_text(item)`**:

将物品信息拼接成通顺的自然语言描述：

```python
def build_context_text(item: dict) -> str:
    """
    构建用于向量化的文本描述
    
    Args:
        item: 物品数据字典
    
    Returns:
        自然语言描述文本
    """
    # 提取字段
    name = item.get('物品名称', '')
    category = item.get('分类', '')
    
    # 颜色信息
    color_info = item.get('属性详情', {}).get('颜色', {})
    color_name = color_info.get('名称', '')
    color_element = color_info.get('主五行', '')
    energy = color_info.get('能量强度', 0)
    
    # 面料信息
    fabric_info = item.get('属性详情', {}).get('面料', {})
    fabric_name = fabric_info.get('名称', '')
    fabric_element = fabric_info.get('主五行', '')
    
    # 款式信息
    style_info = item.get('属性详情', {}).get('款式', {})
    shape = style_info.get('形状', '')
    details = ', '.join(style_info.get('细节', []))
    
    # 适用标签
    tags = ', '.join(item.get('适用标签', []))
    
    # 拼接描述
    text = f"这是一件{name}，属于{category}类别。"
    text += f"颜色是{color_name}，五行属{color_element}，能量强度{energy}。"
    text += f"面料为{fabric_name}，五行属{fabric_element}。"
    
    if shape:
        text += f"款式呈{shape}形。"
    if details:
        text += f"细节包括：{details}。"
    if tags:
        text += f"适合场景：{tags}。"
    
    return text
```

**示例输出**:
```
这是一件正红色真丝衬衫，属于上装类别。颜色是正红，五行属火，能量强度1.0。面料为真丝，五行属火。款式呈长方形。细节包括：V 领, 珍珠扣。适合场景：正式, 旺桃花, 强补火。
```

---

### 步骤 5: 向量化与写入

**批量处理逻辑**:

```python
from psycopg2.extras import execute_values

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='wuxing_db',
    user='wuxing_user',
    password='wuxing_password'
)

# 批量大小
BATCH_SIZE = 20

# 处理数据
for i in range(0, len(items), BATCH_SIZE):
    batch = items[i:i+BATCH_SIZE]
    
    # 构建文本
    texts = [build_context_text(item) for item in batch]
    
    # 生成向量
    embeddings = model.encode(texts, normalize_embeddings=True)
    
    # 准备数据
    values = []
    for item, emb in zip(batch, embeddings):
        values.append((
            item['物品 ID'],
            item['物品名称'],
            item['分类'],
            item['属性详情']['颜色']['主五行'],
            item['属性详情']['颜色'].get('次五行'),
            item['属性详情']['颜色']['能量强度'],
            json.dumps(item['属性详情'], ensure_ascii=False),
            emb.tolist()
        ))
    
    # 批量插入
    sql = """
    INSERT INTO items (item_code, name, category, primary_element, secondary_element, 
                       energy_intensity, attributes_detail, embedding)
    VALUES %s
    ON CONFLICT (item_code) DO UPDATE SET
        embedding = EXCLUDED.embedding,
        attributes_detail = EXCLUDED.attributes_detail
    """
    execute_values(cur, sql, values)
    
    print(f"已处理 {min(i+BATCH_SIZE, len(items))}/{len(items)} 条")
```

---

### 步骤 6: 日志输出

**输出格式**:
```
[INFO] 加载模型: BAAI/bge-m3
[INFO] 设备: cuda / cpu
[INFO] 读取数据: 100 条
[INFO] 开始向量化...
[INFO] 已处理 20/100 条
[INFO] 已处理 40/100 条
[INFO] 已处理 60/100 条
[INFO] 已处理 80/100 条
[INFO] 已处理 100/100 条
[SUCCESS] 导入完成: 100 条成功, 0 条失败
[INFO] 总耗时: XX 秒
```

---

## 📁 输出文件

| 文件路径 | 说明 |
|:---|:---|
| `scripts/import_seed.py` | ETL 导入脚本 |

---

## ⚠️ 注意事项

1. **向量归一化**: 使用 `normalize_embeddings=True` 确保向量归一化
2. **批量插入**: 使用 `execute_values` 提高性能
3. **错误处理**: 捕获异常并记录失败的条目
4. **幂等性**: 使用 `ON CONFLICT` 支持重复执行
