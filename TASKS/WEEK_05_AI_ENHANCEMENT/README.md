# Week 5: AI 多模态增强

## 概述
Week 5 专注于引入多模态AI能力，提升用户体验。通过图片上传与Embedding、虚拟试衣、分享海报等功能，让穿搭推荐更加直观和有趣。

## 任务列表

### 01. 图片上传与Embedding 🔴 高优先级
**目标**: 支持用户上传衣物图片，使用 CLIP 模型生成图片 Embedding，实现以图搜图功能。

**核心功能**:
- 图片上传（拖拽/点击）
- CLIP 模型生成 512维向量
- 以图搜图（相似度匹配）
- 图片存储与访问

**技术栈**:
- CLIP (openai/clip-vit-base-patch32)
- Transformers
- FastAPI 文件上传
- Canvas 图片预览

**交付物**:
- `apps/api/services/image_embedding_service.py`
- `apps/api/routers/image_search.py`
- `apps/web/components/features/ImageUploader.tsx`
- `apps/web/components/features/ImageSearch.tsx`

**预估工时**: 12小时

---

### 02. 虚拟试衣Mock 🟡 中优先级
**目标**: 实现模拟试衣功能，通过 Canvas 图片合成让用户预览搭配效果。

**核心功能**:
- Canvas 画布交互
- 人体模特选择
- 衣物拖拽/缩放/旋转
- 多图层叠加
- 导出效果图

**技术栈**:
- HTML5 Canvas
- React Hooks
- 图片合成算法

**交付物**:
- `apps/web/components/features/VirtualTryOn.tsx`
- `apps/web/components/features/TryOnCanvas.tsx`
- `apps/web/lib/canvas-utils.ts`
- 人体模特素材

**预估工时**: 14小时

---

### 03. 分享海报生成 🟡 中优先级
**目标**: 生成精美穿搭分享海报，支持一键下载和社交分享。

**核心功能**:
- 3+ 种海报模板
- 自定义编辑（标题/文案/签名）
- 配色主题切换
- 高清图片生成 (1080x1920)
- 一键下载/分享

**技术栈**:
- html2canvas
- Canvas 绘图
- 响应式设计

**交付物**:
- `apps/web/components/features/PosterGenerator.tsx`
- `apps/web/lib/poster-templates.ts`
- 海报模板样式

**预估工时**: 11小时

---

## 开发计划

| 天数 | 任务 | 内容 |
|------|------|------|
| Day 1-2 | W5-01 | 后端 CLIP 服务 + 图片上传接口 |
| Day 3 | W5-01 | 前端上传组件 + 以图搜图界面 |
| Day 4 | W5-02 | 虚拟试衣 Canvas 基础 + 交互 |
| Day 5 | W5-02 | 衣物选择器 + 导出功能 |
| Day 6 | W5-03 | 海报模板设计 + 生成器 |
| Day 7 | W5-03 | 编辑功能 + 分享功能 + 测试 |

## 依赖关系

```
W5-01 图片上传与Embedding
  └── 依赖: Week 4 用户衣橱系统

W5-02 虚拟试衣Mock
  └── 依赖: Week 4 用户衣橱系统
  └── 可选依赖: W5-01 图片上传

W5-03 分享海报生成
  └── 依赖: Week 3 前端核心界面
  └── 可选依赖: Week 4 用户衣橱系统
```

## 技术选型

### 图片Embedding
- **模型**: openai/clip-vit-base-patch32
- **维度**: 512维
- **推理时间**: < 2秒
- **内存占用**: ~800MB

### Canvas 操作
- **方案**: 原生 Canvas API
- **备选**: Fabric.js（复杂场景）
- **导出**: html2canvas

### 图片生成
- **方案**: html2canvas
- **分辨率**: 2x 高清
- **格式**: PNG

## 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| CLIP 模型加载慢 | 高 | 单例模式 + 服务启动预热 |
| 模型内存占用大 | 中 | 考虑使用更小模型或量化版本 |
| Canvas 性能问题 | 中 | 优化渲染，使用 requestAnimationFrame |
| 跨域图片问题 | 低 | 配置 CORS 或代理 |
| 移动端兼容性 | 中 | 充分测试，提供降级方案 |

## 验收标准

### W5-01 图片上传与Embedding
- [ ] 支持 JPG/PNG 上传，最大 5MB
- [ ] 生成 512维图片 Embedding
- [ ] 以图搜图响应时间 < 500ms
- [ ] 支持并发上传

### W5-02 虚拟试衣Mock
- [ ] 支持拖拽/缩放/旋转
- [ ] 60fps 流畅交互
- [ ] 支持导出高清图片
- [ ] 响应式设计

### W5-03 分享海报生成
- [ ] 3+ 种海报模板
- [ ] 生成时间 < 3秒
- [ ] 分辨率 1080x1920
- [ ] 支持一键下载

## 相关文档

- [Task 01 详细说明](./01_IMAGE_UPLOAD_EMBED/task_instruction.md)
- [Task 01 验收标准](./01_IMAGE_UPLOAD_EMBED/acceptance_criteria.md)
- [Task 02 详细说明](./02_VIRTUAL_TRYON_MOCK/task_instruction.md)
- [Task 02 验收标准](./02_VIRTUAL_TRYON_MOCK/acceptance_criteria.md)
- [Task 03 详细说明](./03_SHARE_POSTER/task_instruction.md)
- [Task 03 验收标准](./03_SHARE_POSTER/acceptance_criteria.md)
