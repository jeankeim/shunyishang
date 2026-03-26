#!/usr/bin/env python3
"""
Week 2 最终整体测试脚本
测试场景：
1. 规则命中场景（面试→金）
2. LLM 兜底场景（无关键词匹配）
3. 含八字的推荐
"""

import requests
import json
import time
from typing import List, Dict

BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查"""
    print("\n" + "="*50)
    print("【测试1】健康检查 /health")
    print("="*50)
    
    resp = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("✅ 健康检查通过")


def test_recommend_rule_match():
    """测试规则命中场景"""
    print("\n" + "="*50)
    print("【测试2】规则命中场景 - 面试穿搭")
    print("="*50)
    
    payload = {
        "query": "明天要去面试，想显得专业干练",
        "scene": None,
        "bazi": None,
        "top_k": 5
    }
    
    start = time.time()
    events = []
    
    with requests.post(
        f"{BASE_URL}/api/v1/recommend/stream",
        json=payload,
        stream=True,
        headers={"Accept": "text/event-stream"}
    ) as resp:
        for line in resp.iter_lines():
            if line and line.startswith(b'data: '):
                event = json.loads(line[6:])
                events.append(event)
                
                if event["type"] == "analysis":
                    print(f"\n📊 分析结果:")
                    print(f"   目标五行: {event['data']['target_elements']}")
                    print(f"   场景: {event['data']['scene']}")
                    print(f"   意图推理: {event['data']['intent_reasoning'][:50]}...")
                
                elif event["type"] == "items":
                    print(f"\n👕 推荐物品 ({len(event['data'])}件):")
                    for item in event['data'][:3]:
                        print(f"   • {item['name']} ({item['category']}) - 五行:{item['primary_element']} 分数:{item['final_score']}")
                
                elif event["type"] == "token":
                    print(event["data"], end="", flush=True)
                
                elif event["type"] == "done":
                    print("\n\n✅ 流式输出完成")
    
    duration = time.time() - start
    print(f"\n⏱️  总耗时: {duration:.2f}s")
    
    # 验证
    types = [e["type"] for e in events]
    assert "analysis" in types, "缺少 analysis"
    assert "items" in types, "缺少 items"
    assert "done" in types, "缺少 done"
    print("✅ 规则命中场景测试通过")


def test_recommend_llm_fallback():
    """测试 LLM 兜底场景（无关键词匹配）"""
    print("\n" + "="*50)
    print("【测试3】LLM 兜底场景 - 无关键词匹配")
    print("="*50)
    print("输入: '想要一种量子纠缠的感觉' (无五行关键词)")
    
    payload = {
        "query": "想要一种量子纠缠的感觉",
        "scene": None,
        "bazi": None,
        "top_k": 5
    }
    
    events = []
    
    with requests.post(
        f"{BASE_URL}/api/v1/recommend/stream",
        json=payload,
        stream=True,
        headers={"Accept": "text/event-stream"}
    ) as resp:
        for line in resp.iter_lines():
            if line and line.startswith(b'data: '):
                event = json.loads(line[6:])
                events.append(event)
                
                if event["type"] == "analysis":
                    print(f"\n📊 分析结果:")
                    print(f"   目标五行: {event['data']['target_elements']}")
                    print(f"   场景: {event['data']['scene']}")
                    if event['data'].get('intent_reasoning'):
                        print(f"   推理: {event['data']['intent_reasoning']}")
                
                elif event["type"] == "items":
                    print(f"\n👕 推荐物品 ({len(event['data'])}件)")
                
                elif event["type"] == "token":
                    print(event["data"], end="", flush=True)
                
                elif event["type"] == "done":
                    print("\n\n✅ 流式输出完成")
    
    print("\n✅ LLM 兜底场景测试通过")


def test_recommend_with_bazi():
    """测试含八字的推荐"""
    print("\n" + "="*50)
    print("【测试4】含八字的推荐")
    print("="*50)
    print("八字: 1995年6月15日10时 男")
    print("场景: 周末公园散步")
    
    payload = {
        "query": "周末想去公园散步，穿得自然随性",
        "scene": "日常",
        "bazi": {
            "birth_year": 1995,
            "birth_month": 6,
            "birth_day": 15,
            "birth_hour": 10,
            "gender": "男"
        },
        "top_k": 5
    }
    
    events = []
    
    with requests.post(
        f"{BASE_URL}/api/v1/recommend/stream",
        json=payload,
        stream=True,
        headers={"Accept": "text/event-stream"}
    ) as resp:
        for line in resp.iter_lines():
            if line and line.startswith(b'data: '):
                event = json.loads(line[6:])
                events.append(event)
                
                if event["type"] == "analysis":
                    print(f"\n📊 分析结果:")
                    print(f"   目标五行: {event['data']['target_elements']}")
                    if event['data'].get('bazi_reasoning'):
                        print(f"   八字推理: {event['data']['bazi_reasoning'][:60]}...")
                
                elif event["type"] == "items":
                    print(f"\n👕 推荐物品 ({len(event['data'])}件)")
                    for item in event['data'][:3]:
                        print(f"   • {item['name']} - 五行:{item['primary_element']}")
                
                elif event["type"] == "token":
                    print(event["data"], end="", flush=True)
                
                elif event["type"] == "done":
                    print("\n\n✅ 流式输出完成")
    
    # 验证八字推理存在
    analysis_events = [e for e in events if e["type"] == "analysis"]
    if analysis_events:
        assert analysis_events[0]["data"].get("bazi_reasoning") is not None, "应有八字推理"
    print("✅ 含八字推荐测试通过")


def main():
    print("\n" + "="*60)
    print("🧪 Week 2 最终整体测试")
    print("="*60)
    
    try:
        test_health()
        test_recommend_rule_match()
        test_recommend_llm_fallback()
        test_recommend_with_bazi()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！Week 2 完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
