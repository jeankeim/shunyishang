"""
生产环境性能基准测试脚本
目标: 建立系统当前性能基线,识别瓶颈

测试项目:
1. 健康检查接口
2. 推荐接口 (公开模式)
3. 推荐接口 (带八字)
4. 衣橱查询接口
5. 数据库索引检查
6. Redis 缓存命中率

执行方式:
  source .venv/bin/activate
  python scripts/perf_test_production.py
"""

import time
import requests
import statistics
import json
from datetime import datetime
from typing import Dict, List

# 配置
API_BASE_URL = "https://shunyishang-wuxing.zeabur.app"  # 生产环境
# API_BASE_URL = "http://localhost:8000"  # 本地测试

TEST_CONFIG = {
    "warmup_requests": 3,  # 预热请求数
    "test_requests": 10,   # 测试请求数
    "timeout": 30,         # 请求超时时间(秒)
}


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = {}
        
    def test_endpoint(self, name: str, method: str, url: str, **kwargs) -> Dict:
        """测试单个接口"""
        print(f"\n🔍 测试: {name}")
        print(f"   URL: {method.upper()} {url}")
        
        times = []
        success_count = 0
        error_count = 0
        errors = []
        
        # 预热
        for i in range(TEST_CONFIG["warmup_requests"]):
            try:
                if method == "GET":
                    requests.get(url, timeout=TEST_CONFIG["timeout"], **kwargs)
                elif method == "POST":
                    requests.post(url, timeout=TEST_CONFIG["timeout"], **kwargs)
            except:
                pass
            time.sleep(0.5)
        
        # 正式测试
        for i in range(TEST_CONFIG["test_requests"]):
            try:
                start = time.time()
                
                if method == "GET":
                    response = requests.get(url, timeout=TEST_CONFIG["timeout"], **kwargs)
                elif method == "POST":
                    response = requests.post(url, timeout=TEST_CONFIG["timeout"], **kwargs)
                
                elapsed = time.time() - start
                times.append(elapsed)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"   ✓ 请求 {i+1}: {elapsed:.3f}s (状态码: {response.status_code})")
                else:
                    error_count += 1
                    errors.append(f"请求 {i+1}: 状态码 {response.status_code}")
                    print(f"   ✗ 请求 {i+1}: {elapsed:.3f}s (状态码: {response.status_code})")
                    
            except Exception as e:
                error_count += 1
                errors.append(f"请求 {i+1}: {str(e)}")
                print(f"   ✗ 请求 {i+1}: 错误 - {str(e)}")
            
            time.sleep(0.5)  # 避免请求过快
        
        # 统计结果
        if times:
            result = {
                "name": name,
                "url": url,
                "total_requests": len(times) + error_count,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": f"{success_count/len(times)*100:.1f}%",
                "avg_time": f"{statistics.mean(times):.3f}s",
                "median_time": f"{statistics.median(times):.3f}s",
                "p95_time": f"{sorted(times)[int(len(times)*0.95)]:.3f}s" if len(times) > 1 else f"{times[0]:.3f}s",
                "min_time": f"{min(times):.3f}s",
                "max_time": f"{max(times):.3f}s",
                "errors": errors[:5],  # 只显示前5个错误
            }
            
            print(f"\n📊 结果:")
            print(f"   成功率: {result['success_rate']}")
            print(f"   平均响应: {result['avg_time']}")
            print(f"   中位数: {result['median_time']}")
            print(f"   P95: {result['p95_time']}")
            print(f"   最小: {result['min_time']} / 最大: {result['max_time']}")
            
            return result
        else:
            return {"name": name, "error": "所有请求都失败了"}
    
    def test_health_check(self):
        """测试健康检查"""
        return self.test_endpoint(
            "健康检查",
            "GET",
            f"{self.base_url}/health"
        )
    
    def test_recommend_public(self):
        """测试公开推荐接口"""
        return self.test_endpoint(
            "推荐接口 (公开)",
            "POST",
            f"{self.base_url}/api/v1/recommend/stream",
            json={
                "query": "明天要去海边游泳",
                "mode": "public"
            }
        )
    
    def test_recommend_with_bazi(self):
        """测试带八字的推荐接口"""
        return self.test_endpoint(
            "推荐接口 (带八字)",
            "POST",
            f"{self.base_url}/api/v1/recommend/stream",
            json={
                "query": "明天要去面试",
                "mode": "public",
                "birth_info": {
                    "year": 1990,
                    "month": 5,
                    "day": 15,
                    "hour": 10
                }
            }
        )
    
    def test_wardrobe_query(self):
        """测试衣橱查询接口"""
        # 需要先登录获取 token
        print("\n⚠️  衣橱查询需要登录,跳过测试")
        return {"name": "衣橱查询", "skipped": True, "reason": "需要登录"}
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🚀 生产环境性能基准测试")
        print(f"📍 API地址: {self.base_url}")
        print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        tests = [
            self.test_health_check,
            self.test_recommend_public,
            self.test_recommend_with_bazi,
            self.test_wardrobe_query,
        ]
        
        for test in tests:
            result = test()
            self.results[test.__doc__ or test.__name__] = result
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成性能报告"""
        print("\n" + "=" * 60)
        print("📊 性能测试报告")
        print("=" * 60)
        
        for name, result in self.results.items():
            print(f"\n{name}:")
            if "error" in result:
                print(f"   ❌ 错误: {result['error']}")
            elif "skipped" in result:
                print(f"   ⏭️  跳过: {result.get('reason', '')}")
            else:
                print(f"   ✅ 成功率: {result.get('success_rate', 'N/A')}")
                print(f"   ⏱️  平均响应: {result.get('avg_time', 'N/A')}")
                print(f"   📈 P95: {result.get('p95_time', 'N/A')}")
        
        # 性能评估
        print("\n" + "=" * 60)
        print("🎯 性能评估")
        print("=" * 60)
        
        recommend_result = self.results.get("测试公开推荐接口")
        if recommend_result and "avg_time" in recommend_result:
            avg_time = float(recommend_result["avg_time"].replace("s", ""))
            
            if avg_time < 2.0:
                print("✅ 推荐接口性能优秀 (< 2s)")
            elif avg_time < 3.0:
                print("⚠️  推荐接口性能良好 (2-3s)")
            elif avg_time < 5.0:
                print("⚠️  推荐接口性能一般 (3-5s),建议优化")
            else:
                print("❌ 推荐接口性能较差 (> 5s),需要立即优化")
        
        # 保存报告
        report = {
            "test_time": datetime.now().isoformat(),
            "api_url": self.base_url,
            "results": self.results,
        }
        
        report_file = "scripts/perf_test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 报告已保存到: {report_file}")
        print("=" * 60)


def check_database_indexes():
    """检查数据库索引状态"""
    print("\n" + "=" * 60)
    print("🔍 数据库索引检查")
    print("=" * 60)
    print("\n⚠️  需要直接连接数据库执行以下SQL:")
    print("""
-- 查看所有索引
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('items', 'user_wardrobe', 'users')
ORDER BY tablename, indexname;

-- 查看索引使用情况
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('items', 'user_wardrobe', 'users')
ORDER BY idx_scan DESC;

-- 查看缺失索引的查询
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_tables
WHERE tablename IN ('items', 'user_wardrobe', 'users')
ORDER BY seq_scan DESC;
""")


def check_redis_cache():
    """检查 Redis 缓存状态"""
    print("\n" + "=" * 60)
    print("🔍 Redis 缓存检查")
    print("=" * 60)
    print("\n⚠️  需要检查以下内容:")
    print("""
1. Redis 连接状态
   - 检查环境变量 UPSTASH_REDIS_REST_URL 和 UPSTASH_REDIS_REST_TOKEN
   - 测试 Redis 连接: curl $UPSTASH_REDIS_REST_URL/ping -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN"

2. 缓存命中率
   - 查看应用日志中的 [Cache] 关键字
   - 统计缓存命中 vs 缓存未命中的比例
   - 目标: 缓存命中率 > 80%

3. 缓存键分布
   - recommend:* (推荐缓存)
   - bazi:* (八字缓存)
   - weather:* (天气缓存)
   
4. 缓存大小
   - 检查 Redis 内存使用: INFO memory
   - 检查键数量: DBSIZE
""")


if __name__ == "__main__":
    print("🚀 开始生产环境性能测试\n")
    
    # 创建测试器
    tester = PerformanceTester(API_BASE_URL)
    
    # 运行所有测试
    tester.run_all_tests()
    
    # 检查数据库索引
    check_database_indexes()
    
    # 检查 Redis 缓存
    check_redis_cache()
    
    print("\n✅ 性能测试完成!")
    print("\n📝 后续优化建议:")
    print("1. 如果推荐接口 > 3s,检查 Redis 缓存是否正常工作")
    print("2. 如果数据库查询慢,检查索引是否创建")
    print("3. 如果 LLM 调用慢,考虑降低 max_tokens 或超时时间")
    print("4. 定期运行此脚本,监控性能变化")
