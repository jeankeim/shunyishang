#!/usr/bin/env python3
"""
WuXing AI Stylist - 交互式穿搭推荐（Week 3 升级版）
支持：规则优先+LLM兜底、八字计算、加权排序、千问生成理由

运行方式：
  source .venv/bin/activate
  export HF_ENDPOINT=https://hf-mirror.com
  export HF_HUB_OFFLINE=1
  python scripts/recommend.py
"""

import os
import sys
import time
import json
import psycopg2
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import torch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.utils.bazi_calculator import (
    calculate_bazi,
    infer_elements_from_text,
    merge_recommendations,
)
from packages.utils.scene_mapper import extract_scene_from_text, get_color_by_element
from apps.api.core.config import settings

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}
MODEL_NAME = "BAAI/bge-m3"
TOP_K = 5

ELEMENT_DESC = {
    "金": "✦ 金 — 利落干练、收敛优雅",
    "木": "✦ 木 — 自然清新、生机蓬勃",
    "水": "✦ 水 — 智慧深沉、灵动流转",
    "火": "✦ 火 — 热情张扬、光彩耀眼",
    "土": "✦ 土 — 稳重包容、踏实温暖",
}

ELEMENT_EMOJI = {"金": "⚪", "木": "🟢", "水": "🔵", "火": "🔴", "土": "🟡"}

# 全局模型
_model = None
_conn = None


def load_model() -> SentenceTransformer:
    """加载 embedding 模型"""
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  正在加载模型（设备: {device}）...")
        os.environ['HF_HUB_OFFLINE'] = '1'
        _model = SentenceTransformer(MODEL_NAME)
        _model = _model.to(device)
    return _model


def connect_db() -> psycopg2.extensions.connection:
    """连接数据库"""
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(**DB_CONFIG)
    return _conn


def analyze_intent(query: str) -> Dict:
    """
    意图分析：规则优先 + LLM兜底
    """
    print(f"  🔍 分析意图...", end=" ", flush=True)
    
    # 1. 规则推断
    intent_result = infer_elements_from_text(query)
    scene = extract_scene_from_text(query)
    
    if intent_result["method"] == "rule":
        print(f"✅ 规则命中: {intent_result['elements']}")
        target_elements = intent_result["elements"]
        search_query = _build_search_query(target_elements, scene, query)
        reasoning = intent_result["reasoning"]
    else:
        # 2. LLM兜底
        print(f"🤖 LLM兜底分析...")
        target_elements, search_query, reasoning = _llm_analyze(query, scene)
    
    return {
        "target_elements": target_elements,
        "scene": scene,
        "search_query": search_query,
        "reasoning": reasoning,
        "method": intent_result["method"],
    }


def _build_search_query(elements: List[str], scene: Optional[str], query: str) -> str:
    """构建搜索查询"""
    parts = []
    for elem in elements[:2]:
        colors = get_color_by_element(elem)
        if colors:
            parts.append(colors[0])
    if scene:
        parts.append(scene)
    parts.append(query[:30])
    return " ".join(parts)


def _llm_analyze(query: str, scene: Optional[str]) -> tuple:
    """LLM兜底分析"""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        prompt = f"""你是一位精通中国五行理论的时尚顾问。

用户需求：{query}
场景：{scene or '未指定'}

请分析这个需求的五行倾向，返回格式：
目标五行：[金/木/水/火/土 中选1-2个]
搜索关键词：[包含颜色和风格的搜索词，20字以内]
推理：[简要说明为什么]

只返回上述三行，不要其他内容。"""

        response = client.chat.completions.create(
            model=settings.qwen_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        
        content = response.choices[0].message.content.strip()
        
        # 解析返回
        elements = []
        search_query = query
        reasoning = "LLM分析"
        
        for line in content.split('\n'):
            if '目标五行：' in line or '目标五行:' in line:
                # 提取五行字符
                for wx in ['金', '木', '水', '火', '土']:
                    if wx in line:
                        elements.append(wx)
            elif '搜索关键词：' in line or '搜索关键词:' in line:
                search_query = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            elif '推理：' in line or '推理:' in line:
                reasoning = line.split('：', 1)[-1].split(':', 1)[-1].strip()
        
        if not elements:
            elements = ['金']  # 默认
        if not search_query:
            search_query = query
            
        return elements, search_query, reasoning
        
    except Exception as e:
        print(f"⚠️ LLM失败: {e}")
        return ['金'], query, "默认推荐"


def search_with_weight(query: str, target_elements: List[str], top_k: int = TOP_K):
    """
    加权搜索：语义×0.6 + 五行×0.4
    """
    model = load_model()
    conn = connect_db()
    
    # 生成查询向量
    embedding = model.encode([query], normalize_embeddings=True)[0]
    
    # 向量搜索 Top 20
    sql = """
        SELECT
            item_code,
            name,
            primary_element,
            secondary_element,
            category,
            attributes_detail,
            1 - (embedding <=> %s::vector) AS semantic_score
        FROM items
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT 20
    """
    
    cur = conn.cursor()
    t0 = time.time()
    cur.execute(sql, (embedding.tolist(), embedding.tolist()))
    rows = cur.fetchall()
    
    # 加权排序
    scored_items = []
    for row in rows:
        item_code, name, primary, secondary, category, attrs, semantic_score = row
        
        # 计算五行匹配分
        wuxing_score = 0.0
        if primary in target_elements:
            wuxing_score += 0.6
        if secondary and secondary in target_elements:
            wuxing_score += 0.3
        
        # 加权最终分数
        final_score = semantic_score * 0.6 + wuxing_score * 0.4
        
        scored_items.append({
            "item_code": item_code,
            "name": name,
            "primary_element": primary,
            "secondary_element": secondary,
            "category": category,
            "attributes": attrs,
            "semantic_score": semantic_score,
            "wuxing_score": wuxing_score,
            "final_score": final_score,
        })
    
    # 按分数排序，取 Top K
    scored_items.sort(key=lambda x: x["final_score"], reverse=True)
    top_items = scored_items[:top_k]
    
    elapsed = (time.time() - t0) * 1000
    cur.close()
    
    return top_items, elapsed


def generate_reason(query: str, items: List[Dict], target_elements: List[str], method: str) -> str:
    """生成推荐理由（简化版）"""
    if method == "rule":
        # 规则命中，本地生成
        element_str = "、".join(target_elements)
        item_names = "、".join([i["name"] for i in items[:3]])
        return f"根据您的需求，推荐以「{element_str}」为主的穿搭。{item_names} 等衣物符合您的气场。"
    else:
        # LLM兜底，调用千问生成
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.dashscope_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            items_desc = "\n".join([f"- {i['name']}（{i['category']}，五行{i['primary_element']}）" for i in items[:3]])
            
            prompt = f"""用户需求：{query}
推荐五行：{'、'.join(target_elements)}
推荐衣物：
{items_desc}

请生成一段100字以内的穿搭建议，解释为什么这些衣物适合用户需求。语气亲切。"""

            response = client.chat.completions.create(
                model=settings.qwen_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"推荐穿搭：{items[0]['name']} 等，符合您的需求。"


def print_result(analysis: Dict, items: List[Dict], reason: str, elapsed: float):
    """打印结果"""
    print()
    print("━" * 60)
    print(f"  🔍 原始需求：{analysis.get('original_query', '')}")
    print(f"  🎯 目标五行：{' '.join([ELEMENT_EMOJI.get(e, '') + e for e in analysis['target_elements']])}")
    print(f"  📍 识别场景：{analysis.get('scene', '无')}")
    print(f"  🔎 搜索查询：{analysis['search_query']}")
    print(f"  ⚙️  推断方式：{'规则命中' if analysis['method'] == 'rule' else 'LLM兜底'}")
    print(f"  ⏱️  耗时：{elapsed:.1f}ms")
    print("━" * 60)
    
    # 五行分布
    elements = [i["primary_element"] for i in items]
    element_count = {}
    for e in elements:
        element_count[e] = element_count.get(e, 0) + 1
    
    print("  📊 推荐五行分布：", end="  ")
    for e, cnt in element_count.items():
        print(f"{ELEMENT_EMOJI.get(e, '●')}{e}×{cnt}", end="  ")
    print("\n")
    
    # 物品列表
    for i, item in enumerate(items, 1):
        primary = item["primary_element"]
        secondary = item.get("secondary_element")
        sec_str = f" / {secondary}" if secondary else ""
        
        # 解析属性
        try:
            attrs = item["attributes"] if isinstance(item["attributes"], dict) else json.loads(item["attributes"])
            color = attrs.get("颜色", {}).get("名称", "—")
            fabric = attrs.get("面料", {}).get("名称", "—")
        except:
            color, fabric = "—", "—"
        
        print(f"  [{i}] {item['name']}")
        print(f"       类型：{item['category']}　　颜色：{color}　　面料：{fabric}")
        print(f"       五行：{ELEMENT_EMOJI.get(primary, '')}{primary}{sec_str}")
        print(f"       分数：语义{item['semantic_score']:.3f} + 五行{item['wuxing_score']:.1f} = {item['final_score']:.3f}")
        print()
    
    # 推荐理由
    print("  💡 推荐理由：")
    print(f"     {reason}")
    print("━" * 60)


def main():
    print()
    print("┌─────────────────────────────────────────────────────────┐")
    print("│       🌿 五行智能衣橱 — Week 3 升级版推荐系统 🌿          │")
    print("│  支持：规则+LLM兜底、加权排序、千问生成理由               │")
    print("│  输入你的穿搭需求，按 Enter 获取推荐                      │")
    print("│  输入 q 或 quit 退出                                     │")
    print("└─────────────────────────────────────────────────────────┘")
    
    print("\n  正在初始化...")
    load_model()
    connect_db()
    print("  ✅ 准备就绪！\n")
    
    # 测试用例
    print("  💡 测试用例：")
    print("     1. 规则命中：明天要去面试，显得专业干练")
    print("     2. LLM兜底：想要一种量子纠缠的感觉")
    print("     3. 含八字：周末公园散步（会提示输入八字）")
    print()
    
    while True:
        try:
            query = input("💬 输入需求 › ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  👋 再见！")
            break
        
        if not query:
            continue
        if query.lower() in ("q", "quit", "exit", "退出"):
            print("\n  👋 再见！")
            break
        
        # 执行推荐流程
        start = time.time()
        
        # 1. 意图分析
        analysis = analyze_intent(query)
        analysis["original_query"] = query
        
        # 2. 加权搜索
        items, search_elapsed = search_with_weight(
            analysis["search_query"],
            analysis["target_elements"]
        )
        
        if not items:
            print("  ⚠️ 未找到匹配结果")
            continue
        
        # 3. 生成理由
        reason = generate_reason(
            query, items, analysis["target_elements"], analysis["method"]
        )
        
        total_elapsed = (time.time() - start) * 1000
        
        # 4. 打印结果
        print_result(analysis, items, reason, total_elapsed)


if __name__ == "__main__":
    main()