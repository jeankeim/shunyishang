# Week 6 - Task 01: 性能调优

## 任务概述
全面优化系统性能，包括数据库查询优化、缓存策略优化、应用性能调优，确保系统能够支持生产环境的高并发访问。

## 背景与目标
随着功能完善，系统需要面对更高的并发访问和更大的数据量。本任务通过性能分析、瓶颈识别和针对性优化，确保系统在生产环境下的稳定性和高性能。

## 技术要求

### 数据库优化
- 慢查询分析
- 索引优化
- 查询重写
- 连接池调优

### 缓存优化
- Redis 缓存策略
- 缓存预热
- 缓存失效策略
- 多级缓存

### 应用优化
- 异步处理
- 并发控制
- 内存管理
- 代码优化

## 实现步骤

### 1. 性能分析

#### 1.1 数据库慢查询分析
```sql
-- 开启慢查询日志
ALTER SYSTEM SET log_min_duration_statement = '100ms';

-- 查看慢查询
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 20;
```

#### 1.2 API 性能监控
- 添加接口响应时间监控
- 记录 P50/P95/P99 延迟
- 识别慢接口

#### 1.3 负载测试
使用 Locust 或 k6 进行压力测试：
```python
# locustfile.py
from locust import HttpUser, task

class WuxingUser(HttpUser):
    @task
    def recommend(self):
        self.client.post("/api/v1/recommend", json={
            "query": "今天穿什么",
            "user_id": "test_user"
        })
```

### 2. 数据库优化

#### 2.1 索引优化
文件: `scripts/optimize_indexes.sql`

```sql
-- 向量搜索索引优化
CREATE INDEX CONCURRENTLY idx_items_embedding_hnsw 
ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 常用查询字段索引
CREATE INDEX CONCURRENTLY idx_items_category ON items(category);
CREATE INDEX CONCURRENTLY idx_items_primary_element ON items(primary_element);
CREATE INDEX CONCURRENTLY idx_user_wardrobe_user_id ON user_wardrobe(user_id);

-- 复合索引
CREATE INDEX CONCURRENTLY idx_items_category_element ON items(category, primary_element);
```

#### 2.2 查询优化
文件: `packages/db/query_optimizer.py`

优化方向:
- 减少 N+1 查询
- 使用 JOIN 替代子查询
- 分页查询优化
- 向量搜索参数调优

#### 2.3 连接池调优
文件: `apps/api/core/database.py`

```python
# 连接池配置优化
DATABASE_CONFIG = {
    'minconn': 5,          # 最小连接数
    'maxconn': 20,         # 最大连接数（根据并发调整）
    'max_overflow': 10,    # 溢出连接
    'pool_timeout': 30,    # 连接超时
    'pool_recycle': 3600,  # 连接回收时间
}
```

### 3. 缓存优化

#### 3.1 Redis 缓存策略
文件: `apps/api/core/cache.py`

```python
# 缓存策略配置
CACHE_STRATEGIES = {
    'user_profile': {'ttl': 3600, 'key': 'user:{user_id}'},
    'bazi_result': {'ttl': 86400, 'key': 'bazi:{user_id}'},
    'weather_data': {'ttl': 1800, 'key': 'weather:{city}'},
    'recommend_result': {'ttl': 300, 'key': 'rec:{user_id}:{scene}'},
}
```

#### 3.2 缓存预热
文件: `apps/api/services/cache_warmup.py`

```python
# 服务启动时预热缓存
async def warmup_cache():
    # 预热热门数据
    await warmup_popular_items()
    await warmup_user_profiles()
    await warmup_weather_data()
```

#### 3.3 缓存失效策略
- 主动失效：数据更新时清除缓存
- 被动失效：TTL 过期
- 批量失效：使用 Redis Pipeline

### 4. 应用优化

#### 4.1 异步处理
文件: `apps/api/services/async_processor.py`

```python
# 异步任务处理
async def process_recommendation_async(user_id: str, params: dict):
    # 使用后台任务处理耗时操作
    await background_tasks.add_task(
        generate_recommendation, user_id, params
    )
```

#### 4.2 并发控制
```python
# 使用 Semaphore 控制并发
import asyncio

semaphore = asyncio.Semaphore(10)

async def limited_request():
    async with semaphore:
        return await make_request()
```

#### 4.3 代码优化
- 减少不必要的对象创建
- 使用生成器替代列表
- 避免重复计算
- 使用 lru_cache

## 验收标准

### 性能指标
```
API 平均响应时间:     P95 < 200ms
向量搜索响应时间:     P95 < 100ms
数据库查询时间:       P95 < 50ms
图片上传接口:         P95 < 3000ms
```

### 并发能力
```
支持并发用户:         100+
QPS (查询/秒):        500+
并发上传:             10
```

### 资源使用
```
数据库连接池利用率:    > 80%
Redis 内存使用:        < 1GB
后端服务内存:          < 2GB
CPU 使用率:            < 70%
```

## 交付物

### 配置文件
- `scripts/optimize_indexes.sql` - 索引优化脚本
- `apps/api/core/cache.py` - 缓存配置
- `apps/api/core/database.py` - 连接池配置（更新）

### 服务文件
- `apps/api/services/cache_warmup.py` - 缓存预热服务
- `apps/api/services/query_optimizer.py` - 查询优化器
- `apps/api/services/async_processor.py` - 异步处理器
- `apps/api/middleware/performance.py` - 性能监控中间件

### 测试文件
- `scripts/performance_test.py` - 性能测试脚本
- `locustfile.py` - 负载测试配置
- `k6/load_test.js` - K6 负载测试

### 文档
- `docs/PERFORMANCE_REPORT.md` - 性能测试报告
- `docs/OPTIMIZATION_GUIDE.md` - 优化指南

## 监控指标

### 应用指标
- 接口响应时间 (P50/P95/P99)
- 错误率
- 吞吐量 (QPS)
- 并发连接数

### 数据库指标
- 查询执行时间
- 连接池使用率
- 慢查询数量
- 缓存命中率

### 系统指标
- CPU 使用率
- 内存使用率
- 磁盘 I/O
- 网络带宽

## 工具推荐

### 性能测试
- Locust: Python 负载测试
- k6: 现代负载测试工具
- Apache Bench: 简单压测

### 监控工具
- Prometheus + Grafana: 指标监控
- Jaeger: 分布式追踪
- pgAdmin: 数据库监控

### 分析工具
- Explain Analyze: SQL 分析
- cProfile: Python 性能分析
- memory_profiler: 内存分析

## 预估工时
- 性能分析: 3小时
- 数据库优化: 4小时
- 缓存优化: 3小时
- 应用优化: 3小时
- 测试验证: 3小时
- **总计: 16小时**

## 依赖任务
- Week 1-4: 所有基础功能
- Week 6-02: Docker 生产配置（优化后部署）

## 注意事项
1. 优化前务必备份数据
2. 索引创建使用 CONCURRENTLY 避免锁表
3. 逐步优化，每次优化后测试
4. 保留优化前后的性能对比数据
