#!/usr/bin/env python3
"""
WuXing AI Stylist - 语义搜索验证脚本
验证向量库的语义搜索能力
"""

import time
import sys
from pathlib import Path

import psycopg2
from sentence_transformers import SentenceTransformer
import torch

# 配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}
MODEL_NAME = "BAAI/bge-m3"
TOP_K = 3

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


def log(level: str, message: str):
    """打印日志"""
    print(f"[{level}] {message}")


def load_model():
    """加载 BGE-M3 模型"""
    log("INFO", f"加载模型: {MODEL_NAME}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log("INFO", f"设备: {device}")
    
    model = SentenceTransformer(MODEL_NAME)
    model = model.to(device)
    
    return model


def connect_db():
    """连接数据库"""
    log("INFO", "连接数据库...")
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def semantic_search(query_text: str, model, conn, top_k: int = TOP_K):
    """
    执行语义搜索
    
    Args:
        query_text: 查询文本
        model: SentenceTransformer 模型
        conn: 数据库连接
        top_k: 返回结果数量
    
    Returns:
        搜索结果列表和查询耗时(ms)
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
    
    cur = conn.cursor()
    
    start_time = time.time()
    cur.execute(sql, (query_embedding.tolist(), query_embedding.tolist(), top_k))
    results = cur.fetchall()
    elapsed_ms = (time.time() - start_time) * 1000
    
    cur.close()
    
    return results, elapsed_ms


def print_results(scenario_name: str, query: str, results: list, elapsed_ms: float):
    """格式化打印结果"""
    print(f"\n{'='*60}")
    print(f"场景: {scenario_name}")
    print(f"查询: \"{query}\"")
    print(f"耗时: {elapsed_ms:.2f}ms")
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


def validate_results(results: list, expected_elements: list, expected_colors: list) -> dict:
    """
    验证搜索结果是否符合预期
    
    Args:
        results: 搜索结果
        expected_elements: 预期五行
        expected_colors: 预期颜色关键词
    
    Returns:
        验证结果字典
    """
    # 统计主五行分布
    elements = [row[2] for row in results]  # primary_element
    element_match = sum(1 for e in elements if e in expected_elements)
    
    # 检查名称中是否包含预期颜色
    names = [row[1] for row in results]
    color_match = 0
    for name in names:
        for color in expected_colors:
            if color in name:
                color_match += 1
                break
    
    # 检查相似度分数
    scores = [row[5] for row in results]
    avg_score = sum(scores) / len(scores)
    # BGE-M3 在中文语义搜索上的相似度通常在 0.4-0.7 之间
    score_valid = avg_score >= 0.4
    
    return {
        "element_match": element_match,
        "element_total": len(results),
        "color_match": color_match,
        "color_total": len(results),
        "avg_score": avg_score,
        "score_valid": score_valid
    }


def print_validation(validation: dict, scenario_name: str):
    """打印验证结果"""
    print(f"\n验证结果:")
    print(f"  五行匹配: {validation['element_match']}/{validation['element_total']}")
    print(f"  颜色匹配: {validation['color_match']}/{validation['color_total']}")
    print(f"  平均相似度: {validation['avg_score']:.4f}")
    
    # 判定是否通过
    passed = (
        validation['element_match'] >= 1 and
        validation['score_valid']
    )
    
    status = "✅ 通过" if passed else "⚠️ 需检查"
    print(f"  状态: {status}")
    
    return passed


def main():
    """主函数"""
    log("INFO", "=" * 60)
    log("INFO", "WuXing AI Stylist - 语义搜索验证")
    log("INFO", "=" * 60)
    
    try:
        # 1. 加载模型
        model = load_model()
        
        # 2. 连接数据库
        conn = connect_db()
        
        # 3. 执行测试场景
        all_passed = True
        total_time = 0
        
        for scenario in TEST_SCENARIOS:
            results, elapsed_ms = semantic_search(
                scenario["query"], model, conn
            )
            total_time += elapsed_ms
            
            # 打印结果
            print_results(
                scenario["name"],
                scenario["query"],
                results,
                elapsed_ms
            )
            
            # 验证结果
            validation = validate_results(
                results,
                scenario["expected_elements"],
                scenario["expected_colors"]
            )
            passed = print_validation(validation, scenario["name"])
            
            if not passed:
                all_passed = False
        
        # 4. 关闭连接
        conn.close()
        
        # 5. 最终状态
        log("INFO", "-" * 60)
        log("INFO", f"总测试场景: {len(TEST_SCENARIOS)}")
        log("INFO", f"平均查询耗时: {total_time / len(TEST_SCENARIOS):.2f}ms")
        
        if all_passed:
            log("SUCCESS", "所有场景验证通过！向量库语义搜索能力正常。")
            return 0
        else:
            log("WARNING", "部分场景需要检查，请查看详细结果。")
            return 1
            
    except Exception as e:
        log("ERROR", f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
