#!/usr/bin/env python3
"""
性能基准测试 - 推荐接口
测试缓存命中和未命中的性能差异
"""

import requests
import json
import time
import statistics

BASE_URL = "http://localhost:8000/api/v1"


def test_recommend_stream(query, bazi=None, iterations=3):
    """测试推荐接口性能"""
    print(f"\n{'='*60}")
    print(f"测试查询: {query}")
    print(f"{'='*60}")
    
    response_times = []
    
    for i in range(iterations):
        print(f"\n  第 {i+1} 次请求...")
        
        data = {
            "query": query,
            "user_id": 1,
            "top_k": 10
        }
        
        if bazi:
            data["bazi"] = bazi
        
        start = time.time()
        
        try:
            response = requests.post(
                f"{BASE_URL}/recommend/stream",
                json=data,
                stream=True,
                timeout=30
            )
            
            # 读取完整响应
            full_response = b""
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    full_response += chunk
            
            elapsed = time.time() - start
            response_times.append(elapsed)
            
            # 解析最后一条消息
            lines = full_response.decode('utf-8').strip().split('\n\n')
            last_line = lines[-1] if lines else ""
            if last_line.startswith("data: "):
                try:
                    event = json.loads(last_line[6:])
                    if event.get("type") == "done":
                        status = "✅"
                    else:
                        status = "⚠️"
                except:
                    status = "❌"
            else:
                status = "❌"
            
            print(f"    耗时: {elapsed:.2f}s {status}")
            
        except Exception as e:
            elapsed = time.time() - start
            response_times.append(elapsed)
            print(f"    耗时: {elapsed:.2f}s ❌ 错误: {e}")
    
    # 统计结果
    if response_times:
        avg = statistics.mean(response_times)
        p50 = statistics.median(response_times)
        p95 = max(response_times)
        
        print(f"\n  📊 统计结果:")
        print(f"    平均: {avg:.2f}s")
        print(f"    P50:  {p50:.2f}s")
        print(f"    P95:  {p95:.2f}s")
        
        return avg


if __name__ == "__main__":
    print("="*60)
    print("🚀 推荐接口性能基准测试")
    print("="*60)
    
    # 测试场景1：无八字（首次）
    avg1 = test_recommend_stream(
        "推荐一套穿搭",
        iterations=3
    )
    
    # 等待 2 秒
    time.sleep(2)
    
    # 测试场景2：无八字（缓存命中）
    avg2 = test_recommend_stream(
        "推荐一套穿搭",
        iterations=3
    )
    
    # 计算提升
    if avg1 and avg2:
        improvement = ((avg1 - avg2) / avg1) * 100
        print(f"\n{'='*60}")
        print("📈 性能提升总结")
        print(f"{'='*60}")
        print(f"  无八字 - 首次: {avg1:.2f}s")
        print(f"  无八字 - 缓存: {avg2:.2f}s")
        print(f"  性能提升: {improvement:.1f}%")
        print(f"  节省时间: {avg1 - avg2:.2f}s")
