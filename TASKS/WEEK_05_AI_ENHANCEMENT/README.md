# Week 5: AI 多模态增强

## 概述
Week 5 专注于引入多模态AI能力，提升用户体验。通过图片上传与存储、分享海报等功能，让穿搭推荐更加直观和有趣。

> 注：虚拟试衣功能已调整到 Week 7

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
