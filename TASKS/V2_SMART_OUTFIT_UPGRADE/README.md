# V2 智能穿搭功能六周改造

**周期**: V2 Week 1-5 (2026-07-18 完成)  
**主题**: 智能穿搭核心能力升级  
**状态**: ✅ 全部完成  
**依赖**: Week 1-16 基础功能全部就绪

---

## 🎯 改造目标

基于已有基础设施（AI Agent推荐、天气集成、八字运势、用户偏好、衣橱管理、日记系统），实现从"被动问答"到"主动智能"的升级：用户无需输入即可获得个性化穿搭建议。

---

## 📋 完成清单

### Week 1: 智能每日穿搭建议 ✅

| 序号 | 任务 | 状态 | 关键文件 |
|:---:|------|:---:|---------|
| 01 | 每日穿搭核心服务 | ✅ | `apps/api/services/daily_outfit_service.py` (新建) |
| 02 | `/recommend/daily-outfit` API | ✅ | `apps/api/routers/recommend.py` |
| 03 | `DailyOutfitCard.tsx` 前端组件 | ✅ | `apps/web/components/features/DailyOutfitCard.tsx` (新建) |
| 04 | 首页集成 + `getDailyOutfit` API | ✅ | `apps/web/app/page.tsx`, `apps/web/lib/api.ts` |

**核心能力**: 聚合八字/天气/季节/偏好/衣橱的多维度加权评分（五行30%+天气25%+偏好20%+季节15%+多样性10%），Redis 缓存当日结果。

### Week 2: 智能衣橱分析管理 ✅

| 序号 | 任务 | 状态 | 关键文件 |
|:---:|------|:---:|---------|
| 01 | 衣橱分析服务 | ✅ | `apps/api/services/wardrobe_analytics_service.py` (新建) |
| 02 | `/wardrobe/analytics` + `/idle-items` API | ✅ | `apps/api/routers/wardrobe.py` |
| 03 | `WardrobeInsights.tsx` 四Tab面板 | ✅ | `apps/web/components/features/WardrobeInsights.tsx` (新建) |
| 04 | `IdleItemsCard.tsx` 闲置提醒 | ✅ | `apps/web/components/features/IdleItemsCard.tsx` (新建) |
| 05 | 日记打卡自动更新 `wear_count` | ✅ | `apps/api/routers/diary.py` |

**核心能力**: 穿着频率分析（高/低频+冗余检测）、季节模式、天气适应性、长期闲置识别（>180天）+ 公益捐赠建议文案。

### Week 3: 品类扩展 - 传统文化饰品 ✅

| 序号 | 任务 | 状态 | 关键文件 |
|:---:|------|:---:|---------|
| 01 | 25件传统文化饰品种子数据 | ✅ | `data/seeds/seed_data_accessories.json` (新建) |
| 02 | 饰品数据导入数据库 (ITEM_151-175) | ✅ | `scripts/import_accessories_seed.py` |
| 03 | AI 打标增强（饰品/文玩识别） | ✅ | `apps/api/services/ai_tagging_service.py` |
| 04 | 推荐逻辑适配（品类限制+五行加分） | ✅ | `packages/ai_agents/nodes.py` |
| 05 | 25张商品图片生成+R2上传 | ✅ | `scripts/generate_accessory_images.py` |

**品类覆盖**: 水晶(白/紫/黄/粉/绿幽灵)、玛瑙(红/黑/南红)、黑曜石、虎眼石、紫檀、沉香、菩提、和田玉、翡翠、银饰、碧玺、青金石、金丝楠、蜜蜡、崖柏、石榴石、黄龙玉。

### Week 4: 用户审美画像 ✅

| 序号 | 任务 | 状态 | 关键文件 |
|:---:|------|:---:|---------|
| 01 | DB迁移（审美字段） | ✅ | `scripts/migrations/12_user_aesthetic_profile.sql` (新建) |
| 02 | 后端审美字段查询/更新 | ✅ | `apps/api/routers/auth.py` |
| 03 | `UserProfile.tsx` 审美偏好采集UI | ✅ | `apps/web/components/features/UserProfile.tsx` |
| 04 | 肤色-颜色适配加分 | ✅ | `packages/ai_agents/nodes.py` |

**核心能力**: 肤色选择器(冷白皮/暖白皮/自然色/小麦色/黑皮)、风格偏好多选(12种)、体型选择。推荐算法融合 `_SKIN_TONE_COLOR_FIT` 映射表。

### Week 5: 主动智能推送 + 行为闭环 ✅

| 序号 | 任务 | 状态 | 关键文件 |
|:---:|------|:---:|---------|
| 01 | 季节转换触发器 | ✅ | `apps/api/services/smart_reminder_service.py` |
| 02 | 运势变化触发器 | ✅ | `apps/api/services/smart_reminder_service.py` |
| 03 | LLM 推送文案生成 | ✅ | `apps/api/services/push_service.py` |
| 04 | 行为反馈端点 | ✅ | `apps/api/routers/push.py` |
| 05 | 前端推送反馈 API | ✅ | `apps/web/lib/api.ts` |

**核心能力**: 季节转换(立春/立夏/立秋/立冬±3天)、运势触发(≥80分)、推送限流(3条/日)、行为抑制(关闭类型30天不推)、反馈闭环(click→正向/ignore→中性/close→负向→偏好更新)。

---

## 🗄️ 数据库变更

```sql
-- 迁移12: 用户审美画像
ALTER TABLE users ADD COLUMN skin_tone VARCHAR(20);
ALTER TABLE users ADD COLUMN style_preference VARCHAR(50);
ALTER TABLE users ADD COLUMN body_type VARCHAR(20);
ALTER TABLE users ADD COLUMN aesthetic_tags JSONB;
ALTER TABLE users ADD COLUMN aesthetic_updated_at TIMESTAMP;

-- 饰品数据: ITEM_151-175 (25件) 已导入 items 表
-- 含五行属性/分类/材质/图片URL
```

---

## 📁 新增/修改文件清单

### 新建文件 (8个)
- `apps/api/services/daily_outfit_service.py` - 每日穿搭核心服务 (620行)
- `apps/api/services/wardrobe_analytics_service.py` - 衣橱分析服务 (721行)
- `apps/web/components/features/DailyOutfitCard.tsx` - 每日穿搭卡片
- `apps/web/components/features/WardrobeInsights.tsx` - 衣橱洞察面板 (386行)
- `apps/web/components/features/IdleItemsCard.tsx` - 闲置提醒卡片 (183行)
- `scripts/migrations/12_user_aesthetic_profile.sql` - 审美画像DB迁移
- `data/seeds/seed_data_accessories.json` - 25件传统文化饰品 (778行)
- `scripts/generate_accessory_images.py` - 饰品图片生成脚本 (281行)

### 修改文件 (12个)
- `apps/api/routers/recommend.py` - 新增 daily-outfit 端点
- `apps/api/routers/wardrobe.py` - 新增 analytics/idle-items 端点
- `apps/api/routers/diary.py` - 打卡自动更新 wear_count
- `apps/api/routers/auth.py` - 审美字段查询/更新
- `apps/api/routers/push.py` - 行为反馈端点 + smart-check
- `apps/api/services/smart_reminder_service.py` - 季节/运势触发器
- `apps/api/services/push_service.py` - 行为闭环+限流+抑制
- `apps/api/services/ai_tagging_service.py` - 饰品AI打标
- `packages/ai_agents/nodes.py` - 品类多样性+肤色加分+饰品加分
- `apps/web/lib/api.ts` - 新增接口(每日穿搭/分析/闲置/反馈)
- `apps/web/components/features/UserProfile.tsx` - 审美偏好采集UI
- `apps/web/app/wardrobe/page.tsx` - 集成洞察+闲置组件

---

## 🔧 技术亮点

1. **多维度加权评分**: 五行+天气+偏好+季节+多样性五维融合
2. **肤色-颜色适配**: `_SKIN_TONE_COLOR_FIT` 映射表实现个性化审美
3. **品类多样性约束**: 点缀类(配饰/饰品/文玩)统一随机化+数量限制
4. **行为闭环**: 推送反馈→偏好学习→推荐优化→推送策略调整
5. **curl 绕过 SSL**: Python SSL 受限时用 subprocess+curl 调 DashScope API

---

## ⚠️ 注意事项

1. 饰品数据当前 embedding 为 NULL（需网络恢复后运行 `scripts/run_import_accessories.py` 补充）
2. 日记打卡 wear_count 更新依赖名称匹配，可能不够精准
3. 推送行为反馈的偏好更新为轻量级实现，后续可引入更精细的权重调整
