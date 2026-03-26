#!/usr/bin/env python3
"""
WuXing AI Stylist - ETL 导入脚本
将种子数据向量化并导入 PostgreSQL 数据库
"""

import json
import time
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
import torch

# 配置
# 使用增强后的数据文件（绝对路径）
SEED_DATA_PATH_ENHANCED = Path("/Users/mingyang/Desktop/shunyishang/data/seeds/seed_data_100_enhanced.json")
SEED_DATA_PATH = Path("/Users/mingyang/Desktop/shunyishang/data/seeds/seed_data_100.json")
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}
BATCH_SIZE = 20
# 使用本地缓存的模型
MODEL_NAME = "/Users/mingyang/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"


def log(level: str, message: str):
    """打印日志"""
    print(f"[{level}] {message}")


def build_context_text(item: dict) -> str:
    """
    构建用于向量化的文本描述
    
    Args:
        item: 物品数据字典
    
    Returns:
        自然语言描述文本
    """
    # 提取字段
    name = item.get("物品名称", "")
    category = item.get("分类", "")
    
    # 颜色信息
    color_info = item.get("属性详情", {}).get("颜色", {})
    color_name = color_info.get("名称", "")
    color_element = color_info.get("主五行", "")
    energy = color_info.get("能量强度", 0)
    
    # 面料信息
    fabric_info = item.get("属性详情", {}).get("面料", {})
    fabric_name = fabric_info.get("名称", "")
    fabric_element = fabric_info.get("主五行", "")
    
    # 款式信息
    style_info = item.get("属性详情", {}).get("款式", {})
    shape = style_info.get("形状", "")
    details = ", ".join(style_info.get("细节", []))
    
    # 适用标签
    tags = ", ".join(item.get("适用标签", []))
    
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


def load_model():
    """加载 BGE-M3 模型"""
    log("INFO", f"加载模型: {MODEL_NAME}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log("INFO", f"设备: {device}")
    
    model = SentenceTransformer(MODEL_NAME)
    model = model.to(device)
    
    return model


def load_seed_data():
    """读取种子数据"""
    # 优先使用增强后的数据文件
    data_path = SEED_DATA_PATH_ENHANCED if SEED_DATA_PATH_ENHANCED.exists() else SEED_DATA_PATH
    log("INFO", f"读取数据: {data_path}")
    
    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    
    log("INFO", f"读取数据: {len(items)} 条")
    return items


def connect_db():
    """连接数据库"""
    log("INFO", "连接数据库...")
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def import_data(model, items, conn):
    """导入数据到数据库"""
    log("INFO", "开始向量化...")
    
    cur = conn.cursor()
    total = len(items)
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    for i in range(0, total, BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        
        try:
            # 构建文本
            texts = [build_context_text(item) for item in batch]
            
            # 生成向量
            embeddings = model.encode(texts, normalize_embeddings=True)
            
            # 准备数据
            values = []
            for item, emb in zip(batch, embeddings):
                values.append((
                    item["物品 ID"],
                    item["物品名称"],
                    item["分类"],
                    item["属性详情"]["颜色"]["主五行"],
                    item["属性详情"]["颜色"].get("次五行"),
                    item["属性详情"]["颜色"]["能量强度"],
                    item.get("适用性别", "中性"),
                    json.dumps(item["属性详情"], ensure_ascii=False),
                    emb.tolist(),
                    # 天气相关字段
                    json.dumps(item.get("适用天气", []), ensure_ascii=False),
                    json.dumps(item.get("适用季节", []), ensure_ascii=False),
                    json.dumps(item.get("适用温度范围", {}), ensure_ascii=False),
                    json.dumps(item.get("功能性", {}), ensure_ascii=False),
                    item.get("厚度等级", "适中")
                ))
            
            # 批量插入
            sql = """
            INSERT INTO items (item_code, name, category, primary_element, secondary_element, 
                               energy_intensity, gender, attributes_detail, embedding,
                               applicable_weather, applicable_seasons, temperature_range, 
                               functionality, thickness_level)
            VALUES %s
            ON CONFLICT (item_code) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                attributes_detail = EXCLUDED.attributes_detail,
                gender = EXCLUDED.gender,
                applicable_weather = EXCLUDED.applicable_weather,
                applicable_seasons = EXCLUDED.applicable_seasons,
                temperature_range = EXCLUDED.temperature_range,
                functionality = EXCLUDED.functionality,
                thickness_level = EXCLUDED.thickness_level,
                updated_at = CURRENT_TIMESTAMP
            """
            execute_values(cur, sql, values)
            conn.commit()
            
            success_count += len(batch)
            
        except Exception as e:
            log("ERROR", f"处理批次 {i//BATCH_SIZE + 1} 失败: {e}")
            fail_count += len(batch)
            conn.rollback()
        
        # 每 10 条打印进度
        if (i + BATCH_SIZE) % 20 == 0 or (i + BATCH_SIZE) >= total:
            log("INFO", f"已处理 {min(i + BATCH_SIZE, total)}/{total} 条")
    
    cur.close()
    elapsed = time.time() - start_time
    
    log("SUCCESS", f"导入完成: {success_count} 条成功, {fail_count} 条失败")
    log("INFO", f"总耗时: {elapsed:.1f} 秒")
    
    return success_count, fail_count


def verify_import(conn):
    """验证导入结果"""
    cur = conn.cursor()
    
    # 检查总记录数
    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]
    log("INFO", f"数据库记录数: {count}")
    
    # 检查向量非空
    cur.execute("SELECT COUNT(*) FROM items WHERE embedding IS NULL")
    null_count = cur.fetchone()[0]
    log("INFO", f"空向量记录数: {null_count}")
    
    # 检查向量维度
    cur.execute("SELECT item_code, vector_dims(embedding) as dims FROM items LIMIT 1")
    row = cur.fetchone()
    if row:
        log("INFO", f"向量维度: {row[1]} (预期: 1024)")
    
    cur.close()
    
    return count, null_count


def main():
    """主函数"""
    log("INFO", "=" * 50)
    log("INFO", "WuXing AI Stylist - ETL 导入脚本")
    log("INFO", "=" * 50)
    
    try:
        # 1. 加载模型
        model = load_model()
        
        # 2. 读取数据
        items = load_seed_data()
        
        # 3. 连接数据库
        conn = connect_db()
        
        # 4. 导入数据
        success, fail = import_data(model, items, conn)
        
        # 5. 验证结果
        log("INFO", "-" * 50)
        log("INFO", "验证导入结果...")
        count, null_count = verify_import(conn)
        
        # 6. 关闭连接
        conn.close()
        
        # 7. 最终状态
        log("INFO", "-" * 50)
        if fail == 0 and null_count == 0:
            log("SUCCESS", "ETL 流程完成，所有数据导入成功！")
            return 0
        else:
            log("WARNING", f"ETL 流程完成，但有 {fail} 条失败，{null_count} 条向量为空")
            return 1
            
    except Exception as e:
        log("ERROR", f"ETL 流程失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
