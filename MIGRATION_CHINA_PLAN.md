# 顺衣尚 · 国内部署迁移完整计划

> 目标：将生产环境从海外服务（Vercel + Zeabur + R2 + Upstash）全面迁移至阿里云国内基础设施，确保国内用户秒级访问。

---

## 目录

- [一、现状诊断：为什么要迁移](#一现状诊断为什么要迁移)
- [二、前置条件（迁移前必须完成）](#二前置条件迁移前必须完成)
- [三、迁移任务总览](#三迁移任务总览)
- [四、详细迁移步骤](#四详细迁移步骤)
  - [Task 1：阿里云基础资源开通](#task-1阿里云基础资源开通)
  - [Task 2：数据库迁移（Zeabur PG → 阿里云 RDS）](#task-2数据库迁移zeabur-pg--阿里云-rds)
  - [Task 3：图片存储迁移（Cloudflare R2 → 阿里云 OSS）](#task-3图片存储迁移cloudflare-r2--阿里云-oss)
  - [Task 4：缓存迁移（Upstash Redis → 阿里云 Redis）](#task-4缓存迁移upstash-redis--阿里云-redis)
  - [Task 5：大模型端点切换（国际端点 → 国内端点）](#task-5大模型端点切换国际端点--国内端点)
  - [Task 6：后端部署（Zeabur → 阿里云 ECS）](#task-6后端部署zeabur--阿里云-ecs)
  - [Task 7：前端部署（Vercel → 阿里云 OSS + CDN）](#task-7前端部署vercel--阿里云-oss--cdn)
  - [Task 8：域名解析与 SSL 证书](#task-8域名解析与-ssl-证书)
  - [Task 9：全链路验证](#task-9全链路验证)
- [五、回滚方案](#五回滚方案)
- [六、费用估算](#六费用估算)
- [七、迁移检查清单](#七迁移检查清单)

---

## 一、现状诊断：为什么要迁移

### 1.1 当前架构问题

当前生产环境完全部署在海外基础设施上：

```
国内用户 → [GFW] → Vercel(前端,海外CDN) → Zeabur(后端,海外) → R2(图片,海外) → Upstash(缓存,海外)
```

每一层都跨越 GFW，导致：

| 环节 | 当前服务 | 国内访问表现 | 根因 |
|------|---------|-------------|------|
| 前端页面 | Vercel CDN | 3-8秒加载或超时 | Vercel CDN 节点在海外，DNS 解析后需跨境回源 |
| API 请求 | Zeabur | 2-5秒响应 | 后端服务器在海外，每次请求跨境往返 |
| 图片加载 | Cloudflare R2 | 图片空白或极慢 | Cloudflare 在国内被 ISP 干扰，连接不稳定 |
| 缓存读写 | Upstash REST API | 200-500ms 延迟 | REST API 走 HTTPS 到海外，失去缓存加速意义 |
| 大模型调用 | DashScope 国际端点 | 2-3秒延迟 | 使用 `dashscope-intl.aliyuncs.com`（新加坡节点），跨境绕路 |

### 1.2 迁移后目标架构

```
国内用户 → 阿里云CDN(全国2000+节点) → 阿里云OSS(前端静态)
                                      → 阿里云SLB → 阿里云ECS(后端)
                                                     ├─ 阿里云Redis(内网,<1ms)
                                                     ├─ 阿里云RDS PostgreSQL(内网,<2ms)
                                                     ├─ 阿里云OSS(图片存储)
                                                     ├─ DashScope国内端点(0.25s)
                                                     └─ 和风天气API(国内服务)
```

**核心改善**：所有服务在同一阿里云 VPC 内网通信，用户请求只需到达最近的 CDN 边缘节点。

---

## 二、前置条件（迁移前必须完成）

### 2.1 域名与 ICP 备案

**操作**：在阿里云注册域名并完成 ICP 备案。

**原因**：中国法律规定，面向中国大陆用户提供服务的网站必须完成 ICP 备案。未备案域名无法通过阿里云解析，阿里云 CDN/OSS 也会拒绝未备案域名的绑定。备案通常需要 3-22 个工作日，是整个迁移的关键路径。

#### 2.1.1 个人备案 vs 企业备案：如何选择

| 对比维度 | 个人备案 | 企业备案 |
|---------|---------|---------|
| **适用群体** | 个人 | 企业、社会团体、政府机关、事业单位、律师事务所等 |
| **备案主体显示** | 备案负责人姓名全称 | 备案主体单位全称 |
| **所需证件材料** | 个人身份证件 | 营业执照 + 法人身份证 + 网站负责人身份证 |
| **网站可显示内容** | 仅限个人内容分享（博客、个人作品展示等） | 产品推广、售卖交易、行业信息、企业宣传等 |
| **内容限制** | **不可涉及企业、行业、交易等商业化内容** | 不得超出营业执照经营范围以外的内容 |
| **经营性业务** | 不允许 | 需额外申请 ICP 经营许可证（经营性备案） |
| **变更限制** | 不可变更为其他个人；部分地区若个人是企业法人可转为企业备案 | 可变更企业信息 |
| **备案号格式** | 沪ICP备2026XXXXXX号 | 沪ICP备2026XXXXXX号（相同格式） |

**顺衣尚项目建议**：

本项目当前阶段（AI 穿搭推荐 + 用户衣橱 + 海报生成）具备以下特征：
- 有用户注册/登录功能（JWT 认证）
- 有用户数据存储（衣橱 CRUD）
- 未来规划含商业化功能（VIP 会员、支付集成、电商导流）

**结论**：如果当前仅为个人项目展示、无收费功能，可先用**个人备案**快速上线。但考虑到 V2 路线图明确包含 VIP 会员和支付，建议直接进行**企业备案**（需营业执照），避免后续变更备案的麻烦（个人转企业备案部分地区不支持）。

#### 2.1.2 阿里云 ICP 备案详细流程

备案整体流程分为 5 个阶段，预计耗时 3-22 个工作日：

```
填写备案订单 → 阿里云初审(1-2天) → 工信部短信核验(24小时内) → 管局审核(1-20天) → 备案完成
```

**前提条件**（缺一不可）：
1. **阿里云账号已实名认证**
   - 个人备案：支付宝扫码实名即可
   - 企业备案：企业实名 + 上传营业执照
2. **域名已注册并完成实名认证**
   - 建议在阿里云直接注册域名（省去域名转入等待 2-3 天）
   - 域名后缀须为工信部批准的顶级域（.com / .cn / .net 等均可）
3. **已购买阿里云中国内地服务器**
   - ECS 实例须为**包年包月**计费方式（按量付费不支持备案）
   - 须分配公网 IP
   - 每个 ECS 实例可申请 5 个免费备案服务码

**详细步骤**：

**Step 1：填写备案订单**

1. 登录 [阿里云 ICP 代备案管理系统](https://beian.aliyun.com/)，点击「开始备案」
2. **基础信息校验**：填写主办者信息（个人填姓名+身份证号，企业填企业名称+统一社会信用代码）和网站域名，系统自动校验是否具备备案条件
3. **填写主办者信息**：
   - 个人备案：姓名、身份证号、联系方式、通讯地址
   - 企业备案：企业名称、统一社会信用代码、企业住所、法定代表人信息、网站负责人信息
4. **填写网站信息**：
   - 网站名称：不能含「中国」「中华」等敏感词，建议用「顺衣尚」
   - 网站备注：简述网站用途，如「基于五行理论的 AI 穿搭推荐平台」
   - 服务器信息：选择已购买的 ECS 实例（通过实例 ID 搜索）
5. **上传资料及真实性核验**：
   - 个人备案：上传身份证正反面照片
   - 企业备案：上传营业执照、法人身份证、网站负责人身份证
   - 发现实人核验链接到手机 → 点击短信链接 → 进行人脸核验（阿里云 App 扫脸）
6. 确认信息无误 → 提交初审

**Step 2：阿里云初审（1-2 个工作日）**

- 阿里云审核专员会**电话确认**备案真实性（请保持手机畅通）
- 常见驳回原因：
  - 网站名称含敏感词
  - 证件照片不清晰
  - 通讯地址不详细（需精确到门牌号）
  - 网站内容描述与备案性质不符（如个人备案写了「产品推广」）
- 初审通过后，收到短信「备案订单已提交管局」

**Step 3：工信部短信核验（收到短信后 24 小时内）**

- 收到工信部发送的核验短信（含验证码）
- 登录 [工信部备案管理系统](https://beian.miit.gov.cn/) → 首页「短信核验」
- 填写手机号、验证码、短信验证码 → 提交
- **注意**：超过 24 小时未核验，订单将被退回，需重新提交

**Step 4：管局审核（1-20 个工作日，各省不同）**

- 各省管局审核时长不同（参考：上海约 3-7 天，广东约 1-3 天，北京约 10-20 天）
- 审核期间域名不可解析到服务器（否则提示「未备案」无法访问）
- 审核通过后收到短信和邮件通知，包含 ICP 备案号和网站开通日期

**Step 5：备案后处理**

1. **悬挂备案号**：在网站首页底部添加 ICP 备案号，并链接到工信部网站：
   ```html
   <p><a href="https://beian.miit.gov.cn/" target="_blank">沪ICP备2026XXXXXX号</a></p>
   ```
   不悬挂备案号会被核查处罚。
2. **公安联网备案**（网站开通 30 天内必须完成）：
   - 登录 [全国互联网安全管理服务平台](https://www.mpsbeian.gov.cn/)
   - 提交公安备案申请（需 ICP 备案号）
   - 审核通过后获得公安备案号，同样需在网站底部展示
3. **（可选）ICP 经营许可证**：如果网站涉及收费、交易等经营性业务，需额外申请经营性 ICP 许可证（需企业资质）

#### 2.1.3 备案注意事项

- **备案期间不可开站**：备案通过前，域名不可解析到中国内地服务器，否则会被拦截并可能导致备案被驳回
- **一个阿里云账号只能有一个备案中的订单**：必须等当前订单结束后才能提交下一个
- **备案订单有效期 45 天**：超期未完成自动删除，需重新提交
- **ECS 须包年包月**：按量付费实例不支持备案（建议买 3 个月以上包月）
- **域名须在工信部认可的顶级域列表内**：.com / .cn / .net 等主流后缀均可
- **网站底部必须展示备案号**：ICP 备案号 + 公安备案号都要展示
- **服务器地域须为中国内地**：阿里云香港/海外服务器无需备案，但也无法用于国内备案

### 2.2 阿里云账号与区域选择

**操作**：注册阿里云账号，选择部署区域。

**原因**：区域决定 ECS/RDS/OSS/Redis 的物理位置。华东1（杭州）和华北2（北京）是网络质量最好的两个区域，覆盖全国用户延迟最低（<30ms）。

**建议**：选择 **华东1（杭州）**，因为：
- 阿里云核心基础设施最完善的区域
- 到达全国主要城市的网络延迟均衡
- DashScope 大模型服务在杭州有节点，内网调用延迟极低

### 2.3 安装阿里云 CLI 工具

**操作**：
```bash
# 安装阿里云 CLI
brew install aliyun-cli

# 配置 AccessKey
aliyun configure
```

**原因**：后续开通资源、配置 CDN 等操作可通过 CLI 批量执行，比控制台手动操作更可靠且可重复。

---

## 三、迁移任务总览

| Task | 内容 | 预估工时 | 依赖 | 风险等级 |
|------|------|---------|------|---------|
| 1 | 阿里云基础资源开通 | 2h | 前置条件完成 | 低 |
| 2 | 数据库迁移 | 3h | Task 1 | 高（数据丢失风险） |
| 3 | 图片存储迁移 | 4h | Task 1 | 中（需改代码） |
| 4 | 缓存迁移 | 2h | Task 1 | 低（已有双模式支持） |
| 5 | 大模型端点切换 | 1h | 无 | 低（改配置即可） |
| 6 | 后端部署 | 3h | Task 1-5 | 中（Docker 部署） |
| 7 | 前端部署 | 3h | Task 6, 备案完成 | 中（静态导出配置） |
| 8 | 域名解析与 SSL | 1h | Task 6-7, 备案完成 | 低 |
| 9 | 全链路验证 | 2h | Task 1-8 | — |
| **合计** | | **~21h** | | |

---

## 四、详细迁移步骤

### Task 1：阿里云基础资源开通

**目标**：创建迁移所需的全部阿里云资源。

#### 1.1 创建 VPC 和交换机

**操作**：
```bash
# 创建 VPC
aliyun vpc CreateVpc --VpcName shunyishang-vpc --CidrBlock 172.16.0.0/12

# 创建交换机（华东1 杭州可用区H）
aliyun vpc CreateVSwitch --VpcId <vpc-id> --ZoneId cn-hangzhou-h --CidrBlock 172.16.0.0/24
```

**原因**：VPC（虚拟私有云）是阿里云的隔离网络环境。ECS、RDS、Redis 都需在同一 VPC 内，通过内网通信。内网延迟 <2ms 且不产生公网流量费，这是迁移后性能提升的核心保障。

#### 1.2 创建 RDS PostgreSQL 实例

**操作**：在阿里云控制台创建 RDS PostgreSQL，选择：
- 数据库类型：PostgreSQL 15
- 版本：兼容 PostgreSQL 15，支持 pgvector 扩展
- 规格：2核4G（入门级，后续可弹性升级）
- 存储：50G SSD
- 网络：选择上一步创建的 VPC 和交换机

**原因**：RDS 提供自动备份、主备切换、监控告警等能力，省去自建 PG 的运维成本。pgvector 扩展需在 RDS 控制台手动开启（「参数设置」中添加 `shared_preload_libraries = vector`）。

**注意**：阿里云 RDS PostgreSQL 原生支持 pgvector，但需确认实例规格 ≥ 2核4G（1核1G 不支持扩展管理）。

#### 1.3 创建 Redis 实例

**操作**：在阿里云控制台创建云数据库 Redis：
- 版本：Redis 6.0
- 架构：标准版（单副本即可，个人项目）
- 规格：1G
- 网络：同一 VPC

**原因**：云 Redis 与 ECS 内网通信延迟 <1ms，而 Upstash REST API 跨境延迟 200-500ms。当前项目 `cache.py` 已内置双模式支持（Upstash REST + 传统 Redis），切换后性能直接提升 200 倍。

#### 1.4 创建 OSS Bucket（两个）

**操作**：
```bash
# 前端静态资源 Bucket
aliyun oss mb oss://shunyishang-web --region cn-hangzhou

# 图片存储 Bucket
aliyun oss mb oss://shunyishang-images --region cn-hangzhou
```

**原因**：
- `shunyishang-web`：存放 Next.js 静态导出的前端文件，配合 CDN 加速
- `shunyishang-images`：替代 Cloudflare R2，存放用户上传的衣物图片和 AI 生成的图片

两个 Bucket 分离的原因：前端资源是只读静态文件，可设置全量 CDN 缓存；图片资源涉及上传和删除，需要不同的权限策略和缓存规则。

#### 1.5 创建 ECS 实例

**操作**：
```bash
aliyun ecs RunInstances \
  --InstanceName shunyishang-api \
  --ImageId centos_7_9_x64_20G_alibase_20240226.vhd \
  --InstanceType ecs.t6-c1m2.large \
  --SecurityGroupId <sg-id> \
  --VSwitchId <vsw-id> \
  --SystemDisk.Size 40 \
  --SystemDisk.Category cloud_ssd
```

**原因**：ECS 是后端 FastAPI 应用的运行环境。选择 `t6-c1m2.large`（2核4G）因为 Gunicorn 配置了 4 个 worker，每个 worker 约需 800MB 内存，2核4G 是最低可用配置。后续可通过弹性升级扩容。

**安全组配置**：仅开放 80（HTTP）、443（HTTPS）、22（SSH）端口，8000 端口不对外暴露（由 Nginx 反代）。

---

### Task 2：数据库迁移（Zeabur PG → 阿里云 RDS）

**目标**：将 Zeabur 上的 PostgreSQL 数据完整迁移到阿里云 RDS，包括 pgvector 向量数据。

#### 2.1 开启 RDS pgvector 扩展

**操作**：在 RDS 控制台 → 参数设置，将 `shared_preload_libraries` 设为 `vector`，重启实例。然后通过 DMS（数据管理）执行：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**原因**：pgvector 不是 PostgreSQL 内置扩展，必须通过 `shared_preload_libraries` 预加载。不执行此步骤，所有涉及向量字段的 SQL 都会报错 `type "vector" does not exist`。

#### 2.2 从 Zeabur 导出数据

**操作**：
```bash
# 使用 pg_dump 全量导出（包含数据和结构）
pg_dump \
  --host=163.7.19.105 \
  --port=30395 \
  --username=root \
  --dbname=zeabur \
  --format=custom \
  --file=shunyishang_db.dump
```

**原因**：`--format=custom` 生成压缩的二进制格式，比纯 SQL 更快且支持选择性恢复。`pg_dump` 是 PostgreSQL 官方工具，能保证数据类型（包括 vector 类型）的完整导出。

**注意**：Zeabur 的 PostgreSQL 可能有连接数限制，建议在低峰期导出。如果 Zeabur 不允许外部连接，可在 Zeabur 控制台使用 `pg_dump` 命令导出后下载。

#### 2.3 导入到阿里云 RDS

**操作**：
```bash
# 使用 pg_restore 恢复到 RDS
pg_restore \
  --host=<rds-connection-string>.rds.aliyuncs.com \
  --port=5432 \
  --username=<rds-user> \
  --dbname=<rds-db> \
  --no-owner \
  --no-privileges \
  shunyishang_db.dump
```

**原因**：`--no-owner` 忽略原数据库的 owner 信息（Zeabur 的 root 用户与 RDS 用户不同），`--no-privileges` 跳过权限设置（RDS 会自动处理），避免因用户不匹配导致的恢复失败。

#### 2.4 验证数据完整性

**操作**：
```sql
-- 检查各表行数
SELECT 'items' as tbl, count(*) FROM items
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'user_wardrobe', count(*) FROM user_wardrobe;

-- 检查向量索引是否存在
SELECT indexname FROM pg_indexes WHERE tablename = 'items' AND indexname LIKE '%embedding%';

-- 验证向量搜索可用
SELECT item_code, item_name FROM items ORDER BY embedding <=> '[0.1,0.2,...]'::vector LIMIT 5;
```

**原因**：数据迁移最常见的失败是向量索引丢失和编码错误。行数对比确保数据量一致，向量搜索测试确保 pgvector 功能正常。如果向量索引缺失，需手动执行 `CREATE INDEX ... USING hnsw` 重建。

#### 2.5 更新数据库连接配置

**操作**：修改 `.env.production`：
```env
# 旧（Zeabur）
# DATABASE_URL=postgresql://root:xxx@163.7.19.105:30395/zeabur

# 新（阿里云 RDS）
DATABASE_URL=postgresql://<rds-user>:<rds-password>@<rds-host>.rds.aliyuncs.com:5432/<rds-db>
```

**原因**：`config.py` 的 `Settings` 类通过 `DATABASE_URL` 环境变量读取连接信息。RDS 内网地址仅在阿里云 VPC 内可访问，外部无法连接，这既是安全措施也保证了内网通信速度。

---

### Task 3：图片存储迁移（Cloudflare R2 → 阿里云 OSS）

**目标**：将 R2 中的图片迁移到 OSS，并修改代码使用 OSS SDK。

#### 3.1 从 R2 导出现有图片

**操作**：
```bash
# 使用 aws-cli 从 R2 下载所有图片
# R2 兼容 S3 协议，可用 aws-cli 访问
export AWS_ACCESS_KEY_ID=171aa90ebdccbefcf326674d996690b5
export AWS_SECRET_ACCESS_KEY=9602c58b441ceae1ab3bab12c431f52129389b0fef47e4c6f682ca68309c6d70

aws s3 sync \
  s3://wuxing-wardrobe/ \
  ./r2-backup/ \
  --endpoint-url=https://e79f49e5f684d41d722a3dfe3d42a1af.r2.cloudflarestorage.com
```

**原因**：R2 兼容 S3 协议，`aws s3 sync` 是最可靠的批量下载工具。导出的图片后续需上传到 OSS，保留原始目录结构（`uploads/`、`thumbnails/`）确保 URL 路径不变。

#### 3.2 上传图片到 OSS

**操作**：
```bash
# 使用 ossutil 批量上传
ossutil cp -r ./r2-backup/ oss://shunyishang-images/ --update
```

**原因**：`ossutil` 是阿里云 OSS 官方命令行工具，支持断点续传和批量操作。`--update` 参数仅上传 OSS 中不存在或已变更的文件，避免重复上传。

#### 3.3 配置 OSS 公开访问

**操作**：在 OSS 控制台 → 读写权限，设为「公共读」。绑定自定义域名 `images.shunyishang.cn`。

**原因**：用户上传的衣物图片需要通过 URL 公开访问（前端 `<img src>` 引用）。设为公共读后，任何人都可通过 URL 访问图片。绑定自定义域名后可配合 CDN 加速，且便于后续配置 HTTPS。

#### 3.4 修改后端代码：r2_storage.py → oss_storage.py

**操作**：创建 `apps/api/services/oss_storage.py` 替代 `apps/api/services/r2_storage.py`。

**改动要点**：
- `boto3`（S3 SDK）→ `oss2`（阿里云 OSS SDK）
- endpoint: `https://{account_id}.r2.cloudflarestorage.com` → `https://oss-cn-hangzhou.aliyuncs.com`
- 认证方式：AWS Access Key → OSS AccessKeyId + AccessKeySecret
- URL 生成：`https://{bucket}.r2.dev/{key}` → `https://{bucket}.oss-cn-hangzhou.aliyuncs.com/{key}` 或绑定 CDN 域名

**原因**：虽然 OSS 也兼容 S3 协议（可继续用 boto3），但使用官方 `oss2` SDK 有三个优势：
1. **性能更好**：oss2 内置连接池和自动重试，针对阿里云内网优化
2. **功能完整**：支持 OSS 特有的图片处理（缩略图、水印），可替代当前 PIL 缩略图逻辑
3. **内网免流量费**：oss2 自动识别内网 endpoint（`oss-cn-hangzhou-internal.aliyuncs.com`），ECS 访问 OSS 不产生公网流量费

**关键代码结构**（保持接口一致，调用方无需改动）：
```python
import oss2

class OSSStorageService:
    """阿里云 OSS 对象存储服务"""

    def __init__(self):
        self.access_key_id = settings.oss_access_key_id
        self.access_key_secret = settings.oss_access_key_secret
        self.bucket_name = settings.oss_bucket_name
        self.endpoint = settings.oss_endpoint  # 内网: oss-cn-hangzhou-internal.aliyuncs.com
        self.public_url = settings.oss_public_url  # https://images.shunyishang.cn

        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

    def upload_file_with_thumbnail(self, file_data, file_name, folder, content_type):
        # 逻辑与 R2 版本一致，仅 SDK 调用方式不同
        # oss2.Bucket.put_object 替代 boto3.client.put_object
        ...
```

**注意**：所有调用 `get_r2_service()` 的地方需改为 `get_oss_service()`，但返回的对象接口保持一致（`upload_file`、`upload_file_with_thumbnail`、`delete_file`、`file_exists`）。

#### 3.5 更新 config.py 配置

**操作**：在 `Settings` 类中添加 OSS 配置，移除 R2 配置：
```python
# === 阿里云 OSS 对象存储配置 ===
oss_access_key_id: str = ""
oss_access_key_secret: str = ""
oss_bucket_name: str = "shunyishang-images"
oss_endpoint: str = "https://oss-cn-hangzhou-internal.aliyuncs.com"  # ECS内网
oss_public_url: str = ""  # https://images.shunyishang.cn
```

**原因**：使用 `internal` endpoint 确保 ECS 与 OSS 之间走内网，不产生公网流量费且延迟更低。`public_url` 是用户访问图片的公网地址（通过 CDN 加速）。

#### 3.6 更新 requirements.txt

**操作**：
```txt
# 移除（如果无其他依赖）
# boto3==1.34.0
# botocore==1.34.0

# 新增
oss2==2.18.0
```

**原因**：移除 boto3 减少镜像体积约 60MB。oss2 是纯 Python 包，安装体积仅 2MB。

---

### Task 4：缓存迁移（Upstash Redis → 阿里云 Redis）

**目标**：将缓存从 Upstash REST API 切换到阿里云 Redis 原生协议。

#### 4.1 分析现有代码的双模式架构

**现状**：`apps/api/core/cache.py` 的 `RedisCache` 类已内置双模式支持：
- `use_upstash = True` → 走 Upstash REST API（当前生产环境）
- `use_upstash = False` → 走传统 redis-py（当前本地开发）

**原因**：这意味着切换到阿里云 Redis **几乎不需要改代码**，只需修改环境变量配置即可。这是当初设计时的前瞻性决策。

#### 4.2 更新环境变量配置

**操作**：修改 `.env.production`：
```env
# 旧（Upstash）
# UPSTASH_REDIS_REST_URL=https://free-seagull-72571.upstash.io
# UPSTASH_REDIS_REST_TOKEN=gQAAAA...

# 新（阿里云 Redis）
REDIS_URL=redis://<redis-user>:<redis-password>@<redis-host>.rds.aliyuncs.com:6379/0
REDIS_ENABLED=true
```

**原因**：
- 不设置 `UPSTASH_REDIS_REST_URL` 和 `UPSTASH_REDIS_REST_TOKEN` → `use_upstash` 自动变为 `False`
- 设置 `REDIS_URL` → `cache.py` 的 `_init_client()` 方法使用 `redis.from_url()` 初始化传统 Redis 客户端
- 阿里云 Redis 支持标准 Redis 协议，redis-py 可直接连接

#### 4.3 更新 config.py 的自动启用逻辑

**操作**：修改 `_auto_enable_redis` 方法：
```python
def _auto_enable_redis(self):
    """自动启用 Redis"""
    # 优先检测传统 Redis（阿里云）
    if self.redis_url and self.redis_url != "redis://localhost:6379/0":
        if not self.redis_enabled:
            self.redis_enabled = True
            print("[配置] 检测到 Redis 配置，自动启用缓存")
    # 兼容旧版 Upstash（过渡期保留）
    elif self.upstash_redis_rest_url and self.upstash_redis_rest_token:
        if not self.redis_enabled:
            self.redis_enabled = True
            print("[配置] 检测到 Upstash Redis 配置，自动启用缓存")
```

**原因**：保持向后兼容，过渡期两种 Redis 配置都能工作。优先检测传统 Redis URL，避免同时配置时冲突。

#### 4.4 更新 requirements.txt

**操作**：
```txt
# 确保已安装（本地开发可能已有）
redis==5.0.0
```

**原因**：`cache.py` 的传统 Redis 模式依赖 `redis-py` 库。当前代码用 `try: import redis` 做了容错处理，但生产环境必须确保安装。

#### 4.5 更新 upstash_redis.py 引用

**操作**：检查所有 `get_upstash_redis()` 的调用点，改为使用 `cache.py` 的统一 `RedisCache`。

**原因**：项目中存在两个 Redis 客户端（`upstash_redis.py` 和 `cache.py`），功能重叠。迁移后统一使用 `cache.py`，移除 `upstash_redis.py` 避免混淆。搜索代码中所有 `from apps.api.services.upstash_redis import` 并替换为 `from apps.api.core.cache import cache`。

---

### Task 5：大模型端点切换（国际端点 → 国内端点）

**目标**：将 DashScope API 从国际端点切换到国内端点，降低延迟 10 倍。

#### 5.1 修改 config.py 端点配置

**操作**：修改 `Settings` 类：
```python
# 旧（国际端点，新加坡）
# dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
# qwen_model: str = "qwen-flash"  # 国际端点使用 qwen-flash

# 新（国内端点，杭州）
dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
qwen_model: str = "qwen-plus"  # 国内端点使用 qwen-plus
```

**原因**：
- 当前使用 `dashscope-intl.aliyuncs.com`（新加坡节点），从国内调用需跨境绕路，延迟 2-3 秒
- 切换到 `dashscope.aliyuncs.com`（杭州节点），从阿里云 ECS 内网调用延迟仅 0.25 秒
- 国际端点只支持 `qwen-flash`，国内端点支持完整的 `qwen-plus` 模型，生成质量更高
- 这是单个配置变更带来最大性能提升的改动

#### 5.2 确认 API Key 兼容性

**操作**：在阿里云百炼控制台确认当前 API Key 支持国内端点。

**原因**：阿里云百炼的国内版和国际版 API Key 是分开创建的。当前 `.env.production` 中的 `DASHSCOPE_API_KEY` 可能是国际版 Key，需确认或重新创建国内版 Key。如果 Key 不兼容，需在百炼控制台重新创建并更新配置。

---

### Task 6：后端部署（Zeabur → 阿里云 ECS）

**目标**：将 FastAPI 后端部署到阿里云 ECS，通过 Docker 容器化运行。

#### 6.1 准备 ECS 服务器环境

**操作**：
```bash
# SSH 连接 ECS
ssh root@<ecs-public-ip>

# 安装 Docker
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io
systemctl start docker
systemctl enable docker

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

**原因**：ECS 默认是纯净系统，需手动安装 Docker。使用官方 Docker 源而非阿里云镜像源，确保版本最新。安装 Docker Compose 用于管理容器生命周期。

#### 6.2 构建 Docker 镜像

**操作**：在项目根目录执行：
```bash
# 构建镜像
docker build -f apps/api/Dockerfile -t shunyishang-api:latest .

# 测试运行
docker run -d --name api-test \
  --env-file .env.production \
  -p 8000:8000 \
  shunyishang-api:latest

# 验证
curl http://localhost:8000/health
```

**原因**：现有 `apps/api/Dockerfile` 已是生产级配置（多阶段构建、非 root 用户、Gunicorn 4 worker、健康检查），无需修改。本地测试通过后再推送到 ECS。

#### 6.3 配置 Nginx 反向代理

**操作**：在 ECS 上安装 Nginx 并配置：
```nginx
# /etc/nginx/conf.d/shunyishang.conf
server {
    listen 80;
    server_name api.shunyishang.cn;

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # API 反代
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 长连接支持（关键！）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
    }
}
```

**原因**：
- Nginx 作为反向代理，将 80/443 端口的请求转发到 Docker 容器的 8000 端口
- `proxy_buffering off` 是 SSE 流式响应的**关键配置**：默认 Nginx 会缓冲响应体再发送，这会导致 SSE 流式输出退化为"等待全部完成后一次性返回"，破坏打字机效果
- `proxy_read_timeout 300s` 避免 AI 生成耗时较长时 Nginx 主动断开连接

#### 6.4 配置 Docker 容器自动重启

**操作**：创建 `docker-compose.prod.yml`：
```yaml
version: '3.8'
services:
  api:
    image: shunyishang-api:latest
    container_name: shunyishang-api
    restart: always
    env_file: .env.production
    ports:
      - "127.0.0.1:8000:8000"  # 仅监听本地，由 Nginx 反代
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

**原因**：
- `restart: always` 确保容器崩溃或 ECS 重启后自动恢复
- `127.0.0.1:8000` 仅绑定本地地址，外部无法直接访问 8000 端口，必须通过 Nginx
- `logging` 限制日志文件大小，避免磁盘写满（这是 Docker 常见坑）

#### 6.5 更新 CORS 配置

**操作**：修改 `.env.production`：
```env
# 旧
# CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN.vercel.app

# 新
CORS_ORIGINS=https://shunyishang.cn,https://www.shunyishang.cn
```

**原因**：`config.py` 的 `cors_origins_list` 属性在生产环境下强制要求具体域名（禁止 `*`）。CORS 必须与前端实际访问域名完全匹配，否则浏览器会拦截 API 请求。

---

### Task 7：前端部署（Vercel → 阿里云 OSS + CDN）

**目标**：将 Next.js 前端从 Vercel 迁移到阿里云 OSS 静态托管 + CDN 加速。

#### 7.1 修改 Next.js 配置为静态导出

**操作**：修改 `apps/web/next.config.js`：
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 静态导出模式
  output: 'export',

  // 图片优化在静态导出中需禁用
  images: {
    unoptimized: true,
  },

  // API 代理不再需要（前端和后端分离部署）
  // 开发环境通过 .env.local 的 NEXT_PUBLIC_API_URL 指定后端地址

  // 资源路径（如果部署在 OSS 根目录则为空）
  // 如果部署在子目录则配置 basePath
  trailingSlash: true,
}

module.exports = nextConfig
```

**原因**：
- `output: 'export'` 让 Next.js 在构建时生成纯静态 HTML/CSS/JS 文件，可直接放到 OSS 上托管
- Vercel 的 SSR 功能在静态导出后不可用，但本项目的页面（首页推荐、衣橱管理）都是客户端渲染（CSR），不依赖 SSR
- `images.unoptimized: true` 因为静态导出不支持 Next.js Image Optimization API（需服务端处理）
- `trailingSlash: true` 让 OSS 静态托管能正确解析目录 URL（如 `/wardrobe/` → `/wardrobe/index.html`）

#### 7.2 修改前端 API 地址配置

**操作**：修改 `apps/web/lib/api.ts` 或环境变量配置：
```env
# apps/web/.env.production
NEXT_PUBLIC_API_URL=https://api.shunyishang.cn
NEXT_PUBLIC_OSS_IMAGES_URL=https://images.shunyishang.cn
```

**原因**：
- Vercel 部署时通过 `rewrites` 将 `/api/*` 代理到后端，静态导出后此功能失效
- 前端需直接请求后端域名 `api.shunyishang.cn`，通过 `NEXT_PUBLIC_API_URL` 环境变量注入
- `NEXT_PUBLIC_` 前缀的变量会在构建时被注入到客户端代码中

#### 7.3 构建并上传到 OSS

**操作**：
```bash
cd apps/web

# 安装依赖
npm install

# 构建静态文件
npm run build

# 上传到 OSS
ossutil cp -r out/ oss://shunyishang-web/ --update
```

**原因**：
- `npm run build` 在 `output: 'export'` 模式下生成 `out/` 目录，内含所有静态文件
- `ossutil cp -r` 递归上传，`--update` 仅上传变更文件，提升部署速度

#### 7.4 配置 OSS 静态网站托管

**操作**：在 OSS 控制台 → 静态页面：
- 默认首页：`index.html`
- 默认 404 页：`404.html`（或 `index.html` 作为 SPA 回退）
- 绑定自定义域名：`shunyishang.cn` 和 `www.shunyishang.cn`

**原因**：OSS 静态网站托管功能让 OSS Bucket 像 Web 服务器一样响应 HTTP 请求，自动返回 `index.html`。绑定自定义域名后才能配置 HTTPS 和 CDN。

#### 7.5 配置 CDN 加速

**操作**：在阿里云 CDN 控制台：
1. 添加加速域名 `shunyishang.cn`，源站为 `shunyishang-web.oss-cn-hangzhou.aliyuncs.com`
2. 加速类型：全站加速
3. 缓存配置：
   - HTML 文件：缓存 10 分钟
   - `_next/static/` 目录：缓存 30 天（带 hash，内容变更后 URL 自动变化）
   - 图片文件：缓存 30 天
4. HTTPS 配置：开启，申请免费 SSL 证书

**原因**：
- CDN 在全国 2000+ 节点缓存静态资源，用户访问最近的节点，延迟 <10ms
- `_next/static/` 目录下的文件名带 hash（如 `chunk-abc123.js`），内容变更后文件名变化，可安全设置长缓存
- HTML 文件缓存 10 分钟确保用户能及时看到更新

---

### Task 8：域名解析与 SSL 证书

**目标**：配置域名解析，确保所有服务通过 HTTPS 访问。

#### 8.1 配置 DNS 解析

**操作**：在阿里云 DNS 控制台添加解析记录：

| 记录类型 | 主机记录 | 记录值 | 说明 |
|---------|---------|-------|------|
| CNAME | @ | shunyishang-web.cdn.aliyuncs.com | 前端（CDN） |
| CNAME | www | shunyishang-web.cdn.aliyuncs.com | 前端（CDN） |
| A | api | <ECS公网IP> | 后端 API |
| CNAME | images | shunyishang-images.cdn.aliyuncs.com | 图片（CDN） |

**原因**：
- `@` 和 `www` 指向 CDN 的 CNAME，CDN 回源到 OSS
- `api` 指向 ECS 公网 IP（A 记录），用户直接访问 ECS 上的 Nginx
- `images` 指向图片 CDN，加速图片分发

#### 8.2 申请 SSL 证书

**操作**：在阿里云 SSL 证书控制台申请免费证书（DV 免费版）：
1. 为 `shunyishang.cn` 和 `www.shunyishang.cn` 申请证书
2. 为 `api.shunyishang.cn` 申请证书
3. 为 `images.shunyishang.cn` 申请证书

**原因**：
- HTTPS 是现代 Web 应用的标配，浏览器会对 HTTP 网站标记"不安全"
- 阿里云提供免费的 DV（Domain Validation）证书，有效期 1 年，自动续期
- CDN 的 HTTPS 证书在 CDN 控制台配置，ECS 的证书在 Nginx 中配置

#### 8.3 配置 Nginx HTTPS

**操作**：更新 Nginx 配置：
```nginx
server {
    listen 80;
    server_name api.shunyishang.cn;
    return 301 https://$server_name$request_uri;  # HTTP 强制跳转 HTTPS
}

server {
    listen 443 ssl;
    server_name api.shunyishang.cn;

    ssl_certificate /etc/nginx/ssl/api.shunyishang.cn.pem;
    ssl_certificate_key /etc/nginx/ssl/api.shunyishang.cn.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
    }
}
```

**原因**：
- 80 端口 301 重定向到 443，强制所有流量走 HTTPS
- `X-Forwarded-Proto` 告诉 FastAPI 当前是 HTTPS 请求，用于生成正确的回调 URL
- TLS 1.2+ 是现代浏览器要求的最低安全标准

---

### Task 9：全链路验证

**目标**：确保迁移后所有功能正常工作。

#### 9.1 基础连通性测试

**操作**：
```bash
# 1. 前端可访问
curl -I https://shunyishang.cn
# 期望: 200 OK, HTTPS

# 2. 后端健康检查
curl https://api.shunyishang.cn/health
# 期望: {"status": "healthy"}

# 3. 图片可访问
curl -I https://images.shunyishang.cn/uploads/test.jpg
# 期望: 200 OK

# 4. CORS 验证
curl -H "Origin: https://shunyishang.cn" \
     -I https://api.shunyishang.cn/api/v1/recommend/stream
# 期望: 响应头包含 Access-Control-Allow-Origin: https://shunyishang.cn
```

**原因**：逐层验证确保每个服务独立可用，便于定位问题。

#### 9.2 核心功能验证

**操作**：在浏览器中测试完整流程：

| 测试项 | 操作 | 预期结果 | 验证点 |
|--------|------|---------|--------|
| 首页加载 | 访问 `shunyishang.cn` | 2秒内完成首屏 | CDN 缓存生效 |
| 八字输入 | 输入出生日期，提交 | 五行雷达图正确显示 | 大模型国内端点正常 |
| 推荐请求 | 输入场景"今天面试穿什么" | SSE 流式输出推荐 | Nginx SSE 配置正确 |
| 衣橱上传 | 上传衣物图片 | 图片显示缩略图 | OSS 上传 + CDN 正常 |
| 海报生成 | 点击生成海报 | 1080x1920 海报下载 | Pillow 字体在 Docker 中可用 |
| 用户登录 | 注册/登录 | JWT token 正常 | HTTPS + JWT 配置正确 |

#### 9.3 性能基准测试

**操作**：
```bash
# API 响应时间
curl -w "@curl-format.txt" -o /dev/null -s https://api.shunyishang.cn/api/v1/recommend/stream

# curl-format.txt 内容:
# time_namelookup:  %{time_namelookup}\n
# time_connect:     %{time_connect}\n
# time_appconnect:  %{time_appconnect}\n
# time_pretransfer: %{time_pretransfer}\n
# time_starttransfer: %{time_starttransfer}\n
# time_total:       %{time_total}\n
```

**预期指标**：

| 指标 | 迁移前 | 迁移后目标 |
|------|--------|-----------|
| 首屏加载 | 3-8s | <1.5s |
| API P95 响应 | 2-5s | <500ms |
| 大模型首字延迟 | 2-3s | <300ms |
| 图片加载 | 超时/5s+ | <200ms |
| 缓存命中延迟 | 200-500ms | <5ms |

---

## 五、回滚方案

如果在迁移过程中出现严重问题，可按以下步骤回滚：

### 5.1 DNS 回滚（最快）

**操作**：将 DNS 解析改回原配置：
- `shunyishang.cn` → Vercel CNAME
- `api.shunyishang.cn` → Zeabur 地址

**原因**：DNS 切换是可逆的，TTL 设为 60 秒可在 1 分钟内全球生效。

### 5.2 数据库回滚

**操作**：Zeabur 上的 PostgreSQL 仍保留 7 天，期间可切回。

**原因**：不立即删除 Zeabur 服务，保留作为热备。确认新环境稳定运行 7 天后再下线旧服务。

### 5.3 代码回滚

**操作**：`git revert` 迁移相关的提交，重新部署到 Zeabur。

**原因**：所有代码改动通过 Git 提交追踪，可精确回滚单个模块（如仅回滚 OSS 改动，保留 Redis 迁移）。

---

## 六、费用估算

### 6.1 阿里云月度费用

| 服务 | 规格 | 月费（估算） | 说明 |
|------|------|------------|------|
| ECS | 2核4G | ¥60-120 | 按量/包月 |
| RDS PostgreSQL | 2核4G 50G | ¥80-150 | 含备份 |
| Redis | 1G 标准版 | ¥30-50 | |
| OSS | 20G + 流量 | ¥10-20 | 图片+前端 |
| CDN | 100GB流量 | ¥20-30 | |
| SSL | 免费版 | ¥0 | DV 证书 |
| 域名 | .cn | ¥35/年 | |
| **合计** | | **¥200-370/月** | |

### 6.2 对比当前

| 项目 | 当前（海外） | 迁移后（国内） |
|------|------------|--------------|
| 前端 | Vercel 免费 | ¥10-20/月 |
| 后端 | Zeabur ~$5 | ¥60-120/月 |
| 数据库 | Zeabur 内置 | ¥80-150/月 |
| Redis | Upstash 免费 | ¥30-50/月 |
| 存储 | R2 免费 | ¥10-20/月 |
| CDN | Vercel 内置 | ¥20-30/月 |
| **月合计** | **~¥35** | **¥200-370** |

**结论**：国内方案费用约为当前的 6-10 倍，但换来的是国内用户从"3-8秒或超时"到"秒级访问"的体验质变。对于面向国内客户的产品，这是必要的投入。

---

## 七、迁移检查清单

### 前置条件
- [ ] 阿里云账号已注册
- [ ] 域名已注册且 ICP 备案通过
- [ ] 阿里云 CLI 已安装配置

### Task 1：资源开通
- [ ] VPC 和交换机已创建（华东1杭州）
- [ ] RDS PostgreSQL 已创建（含 pgvector 扩展）
- [ ] Redis 已创建（同一 VPC）
- [ ] OSS Bucket 已创建（web + images）
- [ ] ECS 已创建（同一 VPC）
- [ ] 安全组规则已配置

### Task 2：数据库迁移
- [ ] pgvector 扩展已开启
- [ ] 数据已从 Zeabur 导出
- [ ] 数据已导入 RDS
- [ ] 表行数验证通过
- [ ] 向量搜索验证通过
- [ ] `.env.production` DATABASE_URL 已更新

### Task 3：存储迁移
- [ ] R2 图片已下载
- [ ] 图片已上传到 OSS
- [ ] OSS 公开访问已配置
- [ ] `oss_storage.py` 已创建
- [ ] 所有 `r2_storage` 引用已替换
- [ ] `config.py` OSS 配置已添加
- [ ] `requirements.txt` 已更新（oss2）
- [ ] 图片上传功能测试通过

### Task 4：缓存迁移
- [ ] `.env.production` Redis 配置已更新
- [ ] Upstash 配置已移除
- [ ] `config.py` 自动启用逻辑已更新
- [ ] `redis-py` 已加入 requirements.txt
- [ ] `upstash_redis.py` 引用已清理
- [ ] 缓存读写测试通过

### Task 5：大模型端点
- [ ] DashScope 端点已切换为国内
- [ ] API Key 兼容性已确认
- [ ] 模型名称已更新（qwen-plus）
- [ ] AI 推荐功能测试通过

### Task 6：后端部署
- [ ] ECS Docker 环境已安装
- [ ] Docker 镜像构建成功
- [ ] 容器健康检查通过
- [ ] Nginx 反代配置完成（含 SSE）
- [ ] CORS 配置已更新
- [ ] `docker-compose.prod.yml` 已配置
- [ ] 容器自动重启已验证

### Task 7：前端部署
- [ ] `next.config.js` 静态导出已配置
- [ ] API 地址环境变量已更新
- [ ] `npm run build` 成功生成 `out/`
- [ ] 文件已上传到 OSS
- [ ] OSS 静态托管已配置
- [ ] CDN 加速已配置
- [ ] 前端页面访问正常

### Task 8：域名与 SSL
- [ ] DNS 解析记录已添加
- [ ] SSL 证书已申请（3个域名）
- [ ] Nginx HTTPS 已配置
- [ ] HTTP→HTTPS 强制跳转已验证

### Task 9：全链路验证
- [ ] 前端 HTTPS 访问正常
- [ ] 后端健康检查通过
- [ ] 八字分析功能正常
- [ ] 推荐流式输出正常（打字机效果）
- [ ] 衣橱图片上传正常
- [ ] 海报生成正常
- [ ] 用户登录/JWT 正常
- [ ] 性能基准达标（首屏<1.5s, API<500ms）

### 收尾
- [ ] 旧服务保留 7 天作为热备
- [ ] 7 天后下线 Vercel/Zeabur/R2/Upstash
- [ ] `.env.production` 敏感信息已检查
- [ ] 本迁移文档已归档

---

> 文档版本：v1.0 | 创建日期：2026-06-27 | 适用项目：顺衣尚 v1.0 生产环境
