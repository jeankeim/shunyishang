"""
性能基准测试脚本
测试当前系统性能，建立基准线
"""

import time
import requests
import statistics
from typing import Dict, List
from datetime import datetime

# 配置
BASE_URL = "http://192.168.3.78:8000"
TEST_COUNT = 5  # 每个接口测试次数

# 测试数据
TEST_CASES = {
    "推荐接口_public": {
        "url": f"{BASE_URL}/api/v1/recommend/stream",
        "method": "POST",
        "data": {
            "query": "明天要去三亚海边游泳",
            "weather_element": "木",
            "weather": {
                "temperature": 30,
                "weather_desc": "晴天",
                "humidity": 70,
                "wind_level": 2
            },
            "gender": "女",
            "retrieval_mode": "public",
            "top_k": 5
        },
        "stream": True
    },
    "推荐接口_带八字": {
        "url": f"{BASE_URL}/api/v1/recommend/stream",
        "method": "POST",
        "data": {
            "query": "下周要去北京出差开会",
            "weather_element": "金",
            "weather": {
                "temperature": 15,
                "weather_desc": "多云",
                "humidity": 40,
                "wind_level": 3
            },
            "bazi": {
                "birth_year": 1990,
                "birth_month": 5,
                "birth_day": 15,
                "birth_hour": 10,
                "gender": "女"
            },
            "retrieval_mode": "public",
            "top_k": 5
        },
        "stream": True
    }
}


def test_streaming_api(url: str, data: Dict, test_name: str) -> Dict:
    """测试流式API性能"""
    print(f"\n🧪 测试: {test_name}")
    print(f"   URL: {url}")
    
    times = []
    success_count = 0
    
    for i in range(TEST_COUNT):
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                json=data,
                stream=True,
                timeout=30
            )
            
            # 读取完整响应
            full_response = ""
            for line in response.iter_lines():
                if line:
                    full_response += line.decode('utf-8')
            
            end_time = time.time()
            elapsed = end_time - start_time
            times.append(elapsed)
            success_count += 1
            
            print(f"   测试 {i+1}/{TEST_COUNT}: {elapsed:.2f}s ✅")
            
        except Exception as e:
            print(f"   测试 {i+1}/{TEST_COUNT}: 失败 - {e} ❌")
    
    # 统计结果
    if times:
        avg_time = statistics.mean(times)
        p50 = statistics.median(times)
        p95 = max(times) if len(times) < 20 else sorted(times)[int(len(times) * 0.95)]
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📊 {test_name} 统计结果:")
        print(f"   成功次数: {success_count}/{TEST_COUNT}")
        print(f"   平均响应时间: {avg_time:.2f}s")
        print(f"   P50 响应时间: {p50:.2f}s")
        print(f"   P95 响应时间: {p95:.2f}s")
        print(f"   最小响应时间: {min_time:.2f}s")
        print(f"   最大响应时间: {max_time:.2f}s")
        
        return {
            "test_name": test_name,
            "success_count": success_count,
            "avg": avg_time,
            "p50": p50,
            "p95": p95,
            "min": min_time,
            "max": max_time,
            "times": times
        }
    
    return {"test_name": test_name, "success_count": 0}


def test_health_check() -> Dict:
    """测试健康检查接口"""
    print(f"\n🏥 测试: 健康检查")
    url = f"{BASE_URL}/health"
    
    times = []
    for i in range(10):
        start_time = time.time()
        try:
            response = requests.get(url, timeout=5)
            elapsed = time.time() - start_time
            times.append(elapsed)
            print(f"   测试 {i+1}/10: {elapsed*1000:.0f}ms ✅")
        except Exception as e:
            print(f"   测试 {i+1}/10: 失败 - {e} ❌")
    
    if times:
        avg = statistics.mean(times) * 1000
        print(f"\n📊 健康检查平均响应: {avg:.0f}ms")
        return {"avg_ms": avg}
    
    return {"avg_ms": 0}


def generate_report(results: List[Dict]) -> str:
    """生成性能报告"""
    report = f"""
# 性能基准测试报告

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试环境**: 本地开发环境 (192.168.3.78:8000)
**测试次数**: {TEST_COUNT} 次/接口

---

## 📊 测试结果汇总

"""
    
    for result in results:
        if "avg" in result:
            report += f"""
### {result['test_name']}
- **平均响应时间**: {result['avg']:.2f}s
- **P50 响应时间**: {result['p50']:.2f}s
- **P95 响应时间**: {result['p95']:.2f}s
- **最小/最大**: {result['min']:.2f}s / {result['max']:.2f}s
- **成功率**: {result['success_count']}/{TEST_COUNT}
"""
    
    report += f"""
---

## 🎯 性能目标

| 指标 | 目标值 | 当前值 | 状态 |
|:---|:---|:---|:---|
| API P95 | < 200ms | - | ⏳ 待测试 |
| 推荐接口整体 | < 2s | - | ⏳ 待测试 |
| 向量搜索 | < 100ms | - | ⏳ 待测试 |
| 数据库查询 | < 50ms | - | ⏳ 待测试 |

---

## 🔍 瓶颈分析

根据历史经验，推荐流程的性能瓶颈主要来自：
1. **大模型调用**（约1.7s）
   - 八字分析
   - Embedding生成
   - 推荐理由生成
2. **向量搜索**（约100-200ms）
3. **数据库查询**（约50-100ms）

---

## 📝 优化建议

1. **优先级 P0**: 优化大模型调用（缓存八字结果、并行处理）
2. **优先级 P0**: 数据库索引优化
3. **优先级 P1**: Redis 缓存策略
4. **优先级 P1**: 连接池调优

---

**下一步**: 根据测试结果，针对性优化瓶颈环节
"""
    
    return report


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 性能基准测试开始")
    print("=" * 60)
    
    all_results = []
    
    # 1. 健康检查
    health_result = test_health_check()
    
    # 2. 测试各个接口
    for test_name, test_config in TEST_CASES.items():
        result = test_streaming_api(
            test_config["url"],
            test_config["data"],
            test_name
        )
        all_results.append(result)
    
    # 3. 生成报告
    report = generate_report(all_results)
    
    # 4. 保存报告
    report_file = "TASKS/WEEK_06_DEPLOY_OPTIMIZE/01_PERF_TUNING/performance_baseline.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n📄 报告已保存: {report_file}")
    print("\n" + "=" * 60)
    print("✅ 性能基准测试完成")
    print("=" * 60)
