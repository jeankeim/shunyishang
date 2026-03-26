# 任务 3: 语义搜索验证 (03_VECTOR_TEST)

**优先级**: 🔴 高  
**预估时间**: 1 小时  
**依赖**: 任务 2 (ETL 流水线完成)

---

## 📋 任务目标

编写测试脚本验证向量库的语义搜索能力，确保搜索结果符合人类直觉。

---

## 🔧 执行步骤

### 步骤 1: 模型复用

**加载与 ETL 阶段相同的模型**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-m3')
```

---

### 步骤 2: 测试用例设计

**定义三个查询场景**:

| 场景 | 类型 | 查询词 | 预期命中 |
|:---|:---|:---|:---|
| A | 模糊语义 | `"想要一点神秘高贵的感觉"` | 深紫色、酒红色、丝绒材质 |
| B | 五行互补 | `"我很浮躁，需要冷静沉稳的衣服"` | 黑色、蓝色、属水或金 |
| C | 场景匹配 | `"春天去公园野餐穿什么"` | 绿色、浅色系、棉麻材质 |

---

### 步骤 3: 搜索逻辑实现

**SQL 查询**:
```python
def semantic_search(query_text: str, top_k: int = 3):
    """
    执行语义搜索
    
    Args:
        query_text: 查询文本
        top_k: 返回结果数量
    
    Returns:
        搜索结果列表
    """
    # 向量化查询
    query_embedding = model.encode([query_text], normalize_embeddings=True)[0]
    
    # SQL 查询 (使用余弦距离)
    sql = """
    SELECT 
        item_code,
        name,
        primary_element,
        secondary_element,
        category,
        1 - (embedding <=> %s::vector) as similarity_score
    FROM items
    ORDER BY embedding <=> %s::vector
    LIMIT %s
    """
    
    cur.execute(sql, (query_embedding.tolist(), query_embedding.tolist(), top_k))
    results = cur.fetchall()
    
    return results
```

---

### 步骤 4: 结果展示

**格式化输出**:
```python
def print_results(scenario_name: str, query: str, results: list):
    print(f"\n{'='*60}")
    print(f"场景: {scenario_name}")
    print(f"查询: \"{query}\"")
    print(f"{'='*60}")
    
    for i, row in enumerate(results, 1):
        item_code, name, primary, secondary, category, score = row
        print(f"\nTop {i}:")
        print(f"  物品ID: {item_code}")
        print(f"  名称: {name}")
        print(f"  分类: {category}")
        print(f"  主五行: {primary}")
        print(f"  次五行: {secondary or '无'}")
        print(f"  相似度: {score:.4f}")
```

---

### 步骤 5: 完整测试脚本结构

```python
"""
scripts/test_semantic_search.py
语义搜索验证脚本
"""

import psycopg2
from sentence_transformers import SentenceTransformer

# 测试场景
TEST_SCENARIOS = [
    {
        "name": "场景A - 模糊语义",
        "query": "想要一点神秘高贵的感觉",
        "expected_elements": ["火", "水"],
        "expected_colors": ["紫", "酒红", "黑"]
    },
    {
        "name": "场景B - 五行互补",
        "query": "我很浮躁，需要冷静沉稳的衣服",
        "expected_elements": ["水", "金"],
        "expected_colors": ["黑", "蓝", "白", "银"]
    },
    {
        "name": "场景C - 场景匹配",
        "query": "春天去公园野餐穿什么",
        "expected_elements": ["木", "火"],
        "expected_colors": ["绿", "粉", "浅"]
    }
]

def main():
    # 加载模型
    print("加载模型...")
    model = SentenceTransformer('BAAI/bge-m3')
    
    # 连接数据库
    conn = psycopg2.connect(...)
    
    # 执行测试
    for scenario in TEST_SCENARIOS:
        results = semantic_search(scenario["query"], model, conn)
        print_results(scenario["name"], scenario["query"], results)
    
    conn.close()
    print("\n测试完成!")

if __name__ == "__main__":
    main()
```

---

## 📁 输出文件

| 文件路径 | 说明 |
|:---|:---|
| `scripts/test_semantic_search.py` | 语义搜索验证脚本 |

---

## ⚠️ 注意事项

1. **向量归一化**: 查询向量也需要归一化
2. **距离计算**: 使用 `<=>` (余弦距离) 或 `<->` (L2距离)
3. **分数范围**: 余弦相似度 = 1 - 余弦距离，范围 [0, 1]
4. **性能**: 单次查询应 < 200ms
