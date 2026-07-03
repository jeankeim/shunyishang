# Week 6: 部署与优化

**状态**: ✅ 已完成（2026-07-01）  
**完成日期**: 2026-07-01

## 概述
Week 6 专注于系统性能优化和生产环境部署。通过数据库优化、缓存策略、Docker 容器化和自动化部署，确保系统可以在生产环境稳定、高效地运行。

**实际部署方案**: Vercel（前端）+ Zeabur（后端）+ R2（图片）+ Upstash（缓存）

## 任务列表

### 01. 性能调优 🔴 高优先级
**目标**: 全面优化系统性能，包括数据库查询优化、缓存策略优化、应用性能调优。

**核心功能**:
- 慢查询分析与优化
- 索引优化
- Redis 缓存策略
- 连接池调优
- 异步处理优化

**技术栈**:
- PostgreSQL 性能优化
- Redis 缓存
- 异步编程
- 性能监控 (Prometheus)

**交付物**:
- `scripts/optimize_indexes.sql`
- `apps/api/core/cache.py`
- `apps/api/services/cache_warmup.py`
- 性能测试报告

**预估工时**: 16小时

---

### 02. Docker Compose 生产配置 🔴 高优先级
**目标**: 创建生产级 Docker Compose 配置，包括多阶段构建、镜像优化、安全加固。

**核心功能**:
- 多阶段 Docker 构建
- 镜像体积优化
- 安全加固（非root用户）
- 健康检查配置
- 资源限制

**技术栈**:
- Docker 多阶段构建
- Nginx 反向代理
- Docker Compose

**交付物**:
- `apps/api/Dockerfile.prod`
- `apps/web/Dockerfile.prod`
- `docker-compose.prod.yml`
- `scripts/deploy.sh`

**预估工时**: 11小时

---

### 03. 生产部署 🔴 高优先级
**目标**: 完成生产环境的完整部署，包括云服务器、域名、HTTPS、监控告警、自动化备份。

**核心功能**:
- 云服务器配置
- 域名与 HTTPS
- 监控告警 (Prometheus + Grafana)
- 自动化备份
- CI/CD 配置

**技术栈**:
- Let's Encrypt
- Prometheus + Grafana
- GitHub Actions
- 云服务器

**交付物**:
- 生产环境部署
- 监控面板
- 备份系统
- CI/CD 流水线

**预估工时**: 13小时

---

## 开发计划

| 天数 | 任务 | 内容 |
|------|------|------|
| Day 1 | W6-01 | 慢查询分析 + 索引优化 |
| Day 2 | W6-01 | 缓存策略 + 连接池调优 |
| Day 3 | W6-01 | 应用优化 + 性能测试 |
| Day 4 | W6-02 | Dockerfile 多阶段构建 |
| Day 5 | W6-02 | Docker Compose 生产配置 |
| Day 6 | W6-03 | 云服务器 + 域名 + HTTPS |
| Day 7 | W6-03 | 监控告警 + 备份 + CI/CD |

## 依赖关系

```
W6-01 性能调优
  └── 依赖: Week 1-5 所有功能

W6-02 Docker Compose 生产配置
  └── 依赖: W6-01 性能调优
  └── 依赖: Week 1-5 所有功能

W6-03 生产部署
  └── 依赖: W6-02 Docker Compose 生产配置
```

## 技术选型

### 性能监控
- **Prometheus**: 指标收集
- **Grafana**: 可视化面板
- **Alertmanager**: 告警管理

### 部署工具
- **Vercel**: 前端自动部署（Next.js 官方平台）
- **Zeabur**: 后端容器部署（PaaS 平台）
- **Docker**: 后端容器化
- **Cloudflare R2**: 图片对象存储
- **Upstash**: Serverless Redis 缓存

### CI/CD
- **Vercel Git Integration**: 前端自动部署（push to main）
- **Zeabur Git Integration**: 后端自动部署（push to main）
- **GitHub Actions**: 自动化测试

## 性能目标

### 响应时间
```
API P95: ~150ms（实际达标）
向量搜索: < 100ms
数据库查询: < 50ms
```

### 并发能力
```
并发用户: 100+
QPS: 500+
错误率: < 0.1%
```

### 资源使用
```
后端内存: < 2GB（Zeabur容器限制）
Redis内存: < 1GB（Upstash）
数据库连接: < 20
缓存命中率: ~85%
```

## 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 性能优化效果不明显 | 高 | 充分分析瓶颈，针对性优化 |
| 生产环境问题 | 高 | 先在测试环境验证 |
| 部署失败 | 高 | 保留回滚方案 |
| 证书过期 | 中 | 配置自动续期 |
| 数据丢失 | 高 | 定期备份，异地备份 |

## 验收标准

### W6-01 性能调优
- [x] API P95 < 200ms（实际 ~150ms）
- [x] 支持 100+ 并发
- [x] 缓存命中率 > 80%（实际 ~85%）
- [x] 性能测试报告

### W6-02 Docker Compose 生产配置
- [x] 后端镜像 < 500MB
- [x] 前端镜像 < 100MB
- [x] 安全扫描通过
- [x] 健康检查配置

### W6-03 生产部署
- [x] 域名 + HTTPS 正常（Vercel自动HTTPS）
- [x] 监控告警正常
- [x] 自动备份正常
- [x] CI/CD 正常（Vercel/Zeabur自动部署）

## 相关文档

- [Task 01 详细说明](./01_PERF_TUNING/task_instruction.md)
- [Task 01 验收标准](./01_PERF_TUNING/acceptance_criteria.md)
- [Task 02 详细说明](./02_DOCKER_COMPOSE/task_instruction.md)
- [Task 02 验收标准](./02_DOCKER_COMPOSE/acceptance_criteria.md)
- [Task 03 详细说明](./03_PROD_DEPLOY/task_instruction.md)
- [Task 03 验收标准](./03_PROD_DEPLOY/acceptance_criteria.md)

## 生产环境架构

### 实际部署方案

| 服务 | 平台 | 说明 |
|:---|:---|:---|
| **前端部署** | Vercel | Next.js 自动部署，全球 CDN，自动 HTTPS |
| **后端部署** | Zeabur | Docker 容器，gunicorn+uvicorn worker |
| **图片存储** | Cloudflare R2 | S3 兼容对象存储，零出口流量费 |
| **缓存** | Upstash Redis | REST API 模式，Serverless 友好 |
| **数据库** | Zeabur 内置 PostgreSQL | pgvector 扩展已激活 |

```
┌─────────────────────────────────────────────────────────────┐
│                         用户                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vercel (前端部署)                          │
│              Next.js 14 + 全球 CDN                           │
│              自动 HTTPS + 自动部署                            │
│              图片优化 + 静态资源缓存                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Zeabur (后端部署)                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Docker 容器                                            ││
│  │  - gunicorn + uvicorn workers                          ││
│  │  - FastAPI 后端服务                                     ││
│  │  - AI 推理（DashScope API）                             ││
│  │  - 健康检查 + 自动重启                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                              │                              │
│          ┌───────────────────┼───────────────────┐          │
│          ▼                                       ▼          │
│  ┌───────────────┐                   ┌───────────────┐      │
│  │  PostgreSQL   │                   │  Upstash Redis│      │
│  │  + pgvector   │                   │  - REST API   │      │
│  │  (Zeabur内置)  │                   │  - 缓存       │      │
│  └───────────────┘                   └───────────────┘      │
│                              │                              │
│                              ▼                              │
│                   ┌───────────────────┐                      │
│                   │  Cloudflare R2    │                      │
│                   │  - 图片存储        │                      │
│                   │  - S3兼容API      │                      │
│                   └───────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### 技术选型说明

1. **Vercel（前端）**：Next.js 官方平台，零配置部署，Edge Network 全球加速
2. **Zeabur（后端）**：PaaS 平台，Docker 容器化部署，自动域名和 HTTPS
3. **Cloudflare R2（图片存储）**：S3 兼容 API，零出口流量费用，与 Cloudflare CDN 集成
4. **Upstash Redis（缓存）**：Serverless Redis，REST API 模式适合无状态部署
5. **Zeabur PostgreSQL（数据库）**：内置 pgvector 扩展，HNSW 索引

## 部署检查清单

### 部署前
- [x] 代码已合并到 main 分支
- [x] 所有测试通过
- [x] 配置文件已更新
- [x] 密钥已配置（环境变量）

### 部署中
- [x] 数据库备份
- [x] 服务健康检查
- [x] 流量切换（Vercel/Zeabur自动）
- [x] 监控验证

### 部署后
- [x] 功能验证
- [x] 性能验证
- [x] 日志检查
- [x] 告警验证
