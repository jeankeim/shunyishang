# Week 5: AI 多模态增强

**状态**: ✅ 已完成（2026-07-01）+ 🔄 持续优化（2026-07-04）

## 概述
Week 5 专注于引入多模态AI能力，提升用户体验。通过图片上传与存储、分享海报等功能，让穿搭推荐更加直观和有趣。

> 注：虚拟试衣功能已调整到 Week 7

> 注：推荐系统22项核心优化已追加至本Week（见 Task 03）

## 任务列表

### 01. 图片上传与存储 🔴 高优先级
**目标**: 支持用户上传衣物图片，实现图片存储与访问功能。

**核心功能**:
- 图片上传（拖拽/点击）
- 图片格式验证（JPG/PNG）
- 本地文件系统存储
- 图片访问接口

**技术栈**:
- FastAPI 文件上传
- Next.js 静态文件服务
- Canvas 图片预览

**交付物**:
- `apps/api/routers/wardrobe.py` (图片上传路由，已实现)
- `apps/web/components/features/AddWardrobeModal.tsx` (已实现)
- `apps/web/public/uploads` (符号链接)

**预估工时**: 5小时

---

### 02. 分享海报生成 🟡 中优先级 ✅ 已完成
**目标**: 生成精美穿搭分享海报，支持一键下载和社交分享。

**核心功能**:
- ✅ 3+ 种海报模板（简约风格、五行风格、卡片风格）
- ✅ 自定义编辑（标题/文案/签名）
- ✅ 配色主题切换（五行配色）
- ✅ 高清图片生成 (1080x1920)
- ✅ 一键下载/分享

**技术栈**:
- html2canvas
- Canvas 绘图
- 响应式设计

**交付物**:
- ✅ `apps/web/components/features/PosterGenerator.tsx` - 海报生成器主组件
- ✅ `apps/web/components/features/PosterTemplate.tsx` - 海报模板组件
- ✅ `apps/web/components/features/PosterEditor.tsx` - 海报编辑器
- ✅ `apps/web/lib/poster-templates.ts` - 模板配置
- ✅ `apps/web/lib/html2canvas-utils.ts` - 生成工具函数
- ✅ `apps/web/hooks/usePoster.ts` - Poster Hook

**预估工时**: 11小时

---

## 开发计划

| 天数 | 任务 | 内容 |
|------|------|------|
| Day 1-2 | W5-01 | 图片上传功能完善 + 静态文件服务配置 |
| Day 3-4 | W5-02 | 海报模板设计 + 生成器 |
| Day 5 | W5-02 | 编辑功能 + 分享功能 + 测试 |

## 依赖关系

```
W5-01 图片上传与存储
  └── 依赖: Week 4 用户衣橱系统

W5-02 分享海报生成
  └── 依赖: Week 3 前端核心界面
  └── 可选依赖: Week 4 用户衣橱系统
```

## 技术选型

### 图片存储
- **方案**: 本地文件系统
- **路径**: `data/uploads/wardrobe/{user_id}/`
- **访问**: Next.js 静态文件服务

### Canvas 操作
- **方案**: 原生 Canvas API
- **导出**: html2canvas

### 图片生成
- **方案**: html2canvas
- **分辨率**: 2x 高清
- **格式**: PNG

## 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 图片格式问题 | 低 | 前端验证 + 后端校验 |
| 跨域图片问题 | 低 | 配置 CORS 或代理 |
| 移动端兼容性 | 中 | 充分测试，提供降级方案 |

## 验收标准

### W5-01 图片上传与存储
- [x] 支持 JPG/PNG 上传，最大 5MB
- [x] 图片正确存储到本地文件系统
- [x] 图片可通过 URL 正常访问
- [x] 上传进度反馈正常

### W5-02 分享海报生成
- [x] 3+ 种海报模板（简约、五行、卡片）
- [x] 生成时间 < 3秒
- [x] 分辨率 1080x1920
- [x] 支持一键下载
- [x] 支持移动端分享
- [x] 支持自定义标题、文案、签名
- [x] 支持五行配色主题切换

## 相关文档

- [Task 01 详细说明](./01_IMAGE_UPLOAD_EMBED/task_instruction.md)
- [Task 01 验收标准](./01_IMAGE_UPLOAD_EMBED/acceptance_criteria.md)
- [Task 02 详细说明](./03_SHARE_POSTER/task_instruction.md)
- [Task 02 验收标准](./03_SHARE_POSTER/acceptance_criteria.md)

## 已调整任务

### W5-02 虚拟试衣Mock ➡️ Week 7 Task 01
- **原因**: 优先级调整，延后开发
- **新位置**: `TASKS/WEEK_07/01_VIRTUAL_TRYON/`
- **状态**: 待开发

---

### 03. 推荐系统22项核心优化 ✅ 已完成（2026-07-04）
**目标**: 全面优化推荐系统的准确性、合理性和用户体验，经过4轮迭代测试达到100%通过率。

**测试结果演进**:
- 基线测试: ~70% 通过率（多个维度 FAIL）
- 第一轮优化后: 95% (63/66)
- 第二轮优化后: 98% (65/66)
- **最终: 100% (66/66)** ✅

#### 第一轮优化（12项，Fix 1-12）

| 编号 | 优化项 | 文件 | 说明 |
|------|--------|------|------|
| #1 | 旅行规划物品池扩大 | `nodes.py` | 物品池 5→20件，确保多天行程有足够选择 |
| #2 | 温度评分重写 | `travel_planner.py` | 32°C推荐厚重衣物扣0.5分，温度适配合理化 |
| #3 | 场景排除规则扩展 | `scene_mapping.py` | 运动/婚礼/旅行/出差场景 excluded_keywords 全面补充 |
| #4 | 复用间隔+新品加分 | `travel_planner.py` | 复用间隔 1→2天，FRESH_ITEM_BONUS=0.3 |
| #5 | 性别默认过滤 | `nodes.py` | 无性别时默认排除 gender='女' 的物品 |
| #6 | count变量bug修复 | `wardrobe_client.py` | line 275 未定义变量 count→has_items |
| #7 | run_agent旅行参数 | `graph.py` | 同步版增加 _extract_context_from_query 调用 |
| #8 | excluded_keywords惩罚加强 | `scene_mapping.py` | 每个关键词匹配扣 0.15→0.5 |
| #9 | format_output包含travel_plan | `nodes.py` | 行程规划结果写入 final_response |
| #10 | 温度过滤名称矛盾检测 | `nodes.py` | 名称含"羽绒"等时强制 thickness="厚重" |
| #11 | 出差场景排除关键词 | `scene_mapping.py` | 增加领带/羽绒服/棉袄/大衣 |
| #12 | 数据标注矛盾覆盖 | `nodes.py` | 名称优先级高于DB标注的thickness_level |

#### 第二轮优化（5项，Fix 13-17）

| 编号 | 优化项 | 文件 | 说明 |
|------|--------|------|------|
| #13 | DB数据质量治理 | 数据库 | 修正 ITEM_028/057/068 羽绒服 thickness_level 和 temperature_range |
| #14 | 度假场景细化 | `scene_mapping.py` | excluded_keywords 增加 8 项（领带/高跟鞋/皮鞋/羽绒服/棉袄/大衣/丝绸/方巾） |
| #15 | 天气一致性优化 | `nodes.py` | 用户指定天气优先于行程API天气预报 |
| #16 | 温度分层过滤 | `nodes.py` | 建立 ≥30°C/≥25°C/≤0°C/≤10°C 四级阈值 |
| #17 | 推荐理由增强 | `nodes.py` | 物品特性覆盖 5个物品+材质/功能维度 |

#### 第三轮优化（5项，P0+P1）

| 编号 | 优化项 | 文件 | 说明 |
|------|--------|------|------|
| #18 | 权重计算配置化 | `nodes.py` | `_WEIGHT_PRESETS` 预设表 + `_compute_recommend_weights` 函数替代原 120 行 if-else 链，代码量减少 60% |
| #19 | 场景过滤规则统一 | `nodes.py` | `_build_scene_filter` 从 `SCENE_MAPPING` 动态读取规则，消除硬编码 `scene_exclusions` 字典与 `scene_mapping.py` 的不同步 |
| #20 | Embedding LRU缓存 | `nodes.py` | `_encode_text_with_dashscope` 增加 256 条 LRU 缓存，相同文本不重复调 DashScope API |
| #21 | 五行多样性约束 | `nodes.py` | `_ensure_wuxing_diversity` 确保 top-k 至少覆盖 2 种五行属性，避免全推荐同一五行 |
| #22 | 数据格式统一治理 | `scene_mapping.py` + 数据库 | temperature_range 键名从英文 min/max 统一为中文 最低/最高，Python 代码兼容两种格式 |

**涉及核心文件**:
- ✅ `packages/ai_agents/nodes.py` — 权重配置化、场景过滤统一、Embedding缓存、五行多样性、温度过滤
- ✅ `packages/ai_agents/graph.py` — 旅行参数提取
- ✅ `packages/utils/scene_mapping.py` — 场景规则配置、温度范围键名兼容
- ✅ `packages/utils/travel_planner.py` — 温度评分、复用间隔
- ✅ `packages/ai_agents/wardrobe_client.py` — bug修复

**测试用例覆盖**（10个场景，66项检查）:
- ✅ TC01: 出差2天（上海，32°C高温）
- ✅ TC02: 约会场景（有八字）
- ✅ TC03: 商务会议（冬季寒冷）
- ✅ TC04: 运动场景（跑步）
- ✅ TC05: 面试场景（女性）
- ✅ TC06: 旅行5天（三亚，夏季）
- ✅ TC07: 居家场景
- ✅ TC08: 婚礼场景（秋季）
- ✅ TC09: 无八字无场景（纯五行推荐）
- ✅ TC10: 出差3天（北京，冬季寒冷）

**完成时间**: 2026-07-04
