# 生产环境性能优化报告

> **测试时间**: 2026-04-13  
> **测试环境**: 生产环境 (Vercel + Zeabur + R2 + Upstash)  
> **优化目标**: 推荐接口 P95 < 2s, 缓存命中率 > 80%

---

## 📊 性能现状

### 历史优化成果（Week 6）

| 优化项 | 优化前 | 优化后 | 提升 |
|:---|:---|:---|:---|
| 推荐接口（公开）平均响应 | 6.74s | 1.21s | ↓ 82% |
| 推荐接口（带八字）平均响应 | 7.32s | 0.92s | ↓ 87% |
| 八字计算缓存 | 无 | Redis TTL 24h | 首次后 < 0.1s |
| 数据库索引 | 基础索引 | 16个 HNSW + GIN | 查询 ↓ 90% |

### 当前性能瓶颈分析

1. **大模型调用**（占比 60-70%）
   - 千问 qwen-plus 生成推荐理由
   - 超时设置：15s
   - max_tokens：200
   
2. **向量搜索**（占比 15-20%）
   - pgvector HNSW 索引
   - 余弦相似度检索 Top20
   
3. **数据库查询**（占比 10-15%）
   - 衣橱查询
   - 用户资料查询
   
4. **网络延迟**（占比 5-10%）
   - Vercel → Zeabur → 数据库
   - 跨区域访问

---

## ✅ 已完成优化

### 1. 数据库索引优化（Week 6）

**文件**: `scripts/optimize_indexes.sql`

**创建的索引**（16个）:

#### 向量搜索索引
- ✅ `idx_items_embedding_hnsw` - HNSW 向量索引（m=16, ef_construction=64）

#### 单字段索引
- ✅ `idx_items_category` - 类别查询
- ✅ `idx_items_primary_element` - 五行元素查询
- ✅ `idx_items_source` - 数据源查询
- ✅ `idx_user_wardrobe_user_id` - 用户衣橱查询
- ✅ `idx_user_wardrobe_item_id` - 物品查询
- ✅ `idx_users_email` - 邮箱查询
- ✅ `idx_users_user_code` - 用户编号查询

#### 复合索引
- ✅ `idx_user_wardrobe_composite` - (user_id, item_id)
- ✅ `idx_items_category_element` - (category, primary_element)
- ✅ `idx_items_source_category` - (source, category)

#### JSONB 索引
- ✅ `idx_items_functionality` - GIN 索引（功能属性查询）

**效果**: 向量搜索从 O(n) 降至 O(log n)，查询速度提升 90%+

---

### 2. Redis 缓存集成（Week 6）

**文件**: `apps/api/core/cache.py`

**缓存策略**:

| 缓存类型 | 缓存键 | TTL | 命中率目标 |
|:---|:---|:---|:---|
| 八字计算 | `bazi:{birth_info_hash}` | 24h | > 90% |
| 天气数据 | `weather:{location}` | 30min | > 80% |
| 推荐结果 | `recommend:{query_hash}` | 5min | > 70% |
| 衣橱检查 | `wardrobe_empty:{user_id}` | 60s | > 85% |

**性能提升**:
- 八字计算：首次 0.5s → 缓存命中 < 0.01s
- 天气查询：首次 0.3s → 缓存命中 < 0.01s
- 推荐结果：避免重复 LLM 调用

---

### 3. LLM 调用优化（Week 6）

**文件**: `packages/ai_agents/nodes.py`

**优化项**:
- ✅ 超时时间：60s → 15s
- ✅ 重试次数：3次 → 1次
- ✅ 重试等待：1-5s → 1-3s
- ✅ max_tokens：300 → 200

**效果**: LLM 调用失败率降低，平均响应时间缩短

---

### 4. 缓存命中路径优化（Week 6）

**文件**: `apps/api/routers/recommend.py`

**优化项**:
- ✅ 移除 `asyncio.sleep`（人为延迟 ~150ms）
- ✅ 移除逐字符流式返回
- ✅ 改为一次性返回完整推荐理由

**效果**: 缓存命中时响应时间从 0.30s → 0.26s（↓ 13%）

---

## 🔍 待优化项

### P0 - 高优先级

#### 1. 生产环境 404 问题排查
**问题**: 所有接口返回 404  
**可能原因**:
- Zeabur 服务未正常启动
- 路由配置问题
- 环境变量缺失

**排查步骤**:
```bash
# 1. 检查 Zeabur 服务状态
# 访问: https://zeabur.com/dashboard

# 2. 查看服务日志
# Zeabur Dashboard → Logs

# 3. 检查环境变量
# 确认: DATABASE_URL, DASHSCOPE_API_KEY, UPSTASH_REDIS_* 等

# 4. 测试健康检查
curl https://shunyishang-api.zeabur.app/health
```

**预估时间**: 1-2 小时

---

#### 2. 慢查询分析与优化
**目标**: 识别并优化慢查询（> 100ms）

**步骤**:
```sql
-- 1. 启用 pg_stat_statements 扩展
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 2. 查看最慢的查询
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 3. 查看未使用索引的表
SELECT 
    schemaname,
    tablename,
    seq_scan,
    idx_scan,
    seq_tup_read
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC
LIMIT 10;
```

**优化策略**:
- 为高频查询添加索引
- 优化复杂查询（JOIN、子查询）
- 使用 EXPLAIN ANALYZE 分析查询计划

**预估时间**: 2-3 小时

---

### P1 - 中优先级

#### 3. Redis 缓存命中率提升
**当前状态**: 待检测  
**目标**: > 80%

**优化策略**:
- 增加推荐缓存 TTL（5min → 10min）
- 添加衣橱列表缓存（TTL 60s）
- 缓存五行雷达图计算结果

**监控方法**:
```bash
# 查看应用日志
grep "\[Cache\]" logs/backend.log | tail -100

# 统计命中率
grep "缓存命中" logs/backend.log | wc -l
grep "缓存未命中" logs/backend.log | wc -l
```

**预估时间**: 1-2 小时

---

#### 4. 连接池优化
**当前配置**: 待确认  
**目标**: 减少连接等待时间

**优化策略**:
```python
# psycopg2 连接池配置
DB_POOL_CONFIG = {
    "minconn": 2,      # 最小连接数
    "maxconn": 10,     # 最大连接数（Zeabur 限制）
    "timeout": 30,     # 连接超时
}
```

**监控指标**:
- 活跃连接数
- 等待连接数
- 连接创建频率

**预估时间**: 1 小时

---

### P2 - 低优先级

#### 5. 向量搜索优化
**当前索引**: HNSW (m=16, ef_construction=64)  
**优化空间**: 调整 HNSW 参数

**优化策略**:
```sql
-- 提高搜索精度（增加 ef_search）
SET hnsw.ef_search = 128;  -- 默认 40

-- 或调整索引参数
DROP INDEX idx_items_embedding_hnsw;
CREATE INDEX idx_items_embedding_hnsw 
ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 128);
```

**权衡**: 精度 ↑ vs 速度 ↓

**预估时间**: 1 小时

---

#### 6. 静态资源 CDN 加速
**当前状态**: R2 自带 CDN  
**优化空间**: 前端资源 CDN

**优化策略**:
- Next.js 图片优化（WebP/AVIF）
- 静态资源缓存策略（Cache-Control）
- 启用 Gzip/Brotli 压缩

**预估时间**: 2-3 小时

---

## 📈 性能目标

| 指标 | 当前值 | 目标值 | 优先级 |
|:---|:---|:---|:---|
| 推荐接口 P95 | 待测试 | < 2s | P0 |
| 缓存命中率 | 待检测 | > 80% | P1 |
| 数据库查询 P95 | 待测试 | < 50ms | P0 |
| 向量搜索 P95 | ~80ms | < 100ms | P2 |
| 并发用户 | 待测试 | 100+ | P1 |

---

## 🛠️ 优化行动计划

### 第一阶段：问题诊断（1-2 小时）
- [ ] 排查生产环境 404 问题
- [ ] 启用 pg_stat_statements
- [ ] 收集慢查询数据
- [ ] 检查 Redis 缓存命中率

### 第二阶段：数据库优化（2-3 小时）
- [ ] 分析慢查询，添加缺失索引
- [ ] 优化复杂查询
- [ ] 调整连接池配置
- [ ] 验证优化效果

### 第三阶段：缓存优化（1-2 小时）
- [ ] 增加缓存 TTL
- [ ] 添加新缓存策略
- [ ] 监控命中率变化
- [ ] 调整缓存策略

### 第四阶段：压力测试（1-2 小时）
- [ ] 执行并发测试
- [ ] 监控资源使用
- [ ] 识别瓶颈点
- [ ] 生成最终报告

---

## 📝 监控与告警

### 关键指标监控

| 指标 | 告警阈值 | 监控方式 |
|:---|:---|:---|
| API P95 响应时间 | > 3s | Zeabur Metrics |
| 错误率 | > 1% | 应用日志 |
| 数据库连接数 | > 8 | pg_stat_activity |
| Redis 命中率 | < 70% | 应用日志统计 |
| 内存使用 | > 80% | Zeabur Dashboard |

### 定期性能测试

```bash
# 每周运行一次性能测试
python scripts/perf_test_production.py

# 保存报告
mv scripts/perf_test_report.json reports/perf_$(date +%Y%m%d).json
```

---

## 🔗 相关文档

- [索引优化脚本](../../scripts/optimize_indexes.sql)
- [性能测试脚本](../../scripts/perf_test_production.py)
- [缓存服务](../../apps/api/core/cache.py)
- [推荐接口](../../apps/api/routers/recommend.py)
- [Week 6 性能基准测试](../../TASKS/WEEK_06_DEPLOY_OPTIMIZE/01_PERF_TUNING/performance_baseline.md)

---

**报告生成时间**: 2026-04-13  
**下次审查时间**: 2026-04-20  
**负责人**: Ming Yang
