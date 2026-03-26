# Week 5 - Task 02: 虚拟试衣Mock

## 任务概述
实现模拟试衣功能，通过 Canvas 图片合成技术，让用户可以预览衣物搭配效果。

## 背景与目标
用户希望能够在购买或搭配前预览衣物穿着效果。本任务实现一个轻量级的虚拟试衣功能，使用 Canvas 进行图片合成，支持拖拽、缩放、旋转等操作。

## 技术要求

### 前端
- Canvas 图片合成
- 拖拽交互
- 缩放和旋转
- 图层管理
- 导出图片

### 后端
- 提供衣物图片（透明背景优先）
- 提供人体模特图片
- 可选：人体姿态检测

### 图片资源
- 人体模特图片（不同体型）
- 衣物图片（透明背景 PNG）

## 实现步骤

### 1. 前端实现

#### 1.1 创建 Canvas 画布组件
文件: `apps/web/components/features/VirtualTryOn.tsx`

核心功能:
- Canvas 初始化
- 图片加载与绘制
- 图层管理（人体、衣物）

#### 1.2 实现交互功能
- 鼠标/触摸事件监听
- 拖拽移动
- 滚轮缩放
- 旋转控制

#### 1.3 衣物选择面板
- 从衣橱中选择衣物
- 分类筛选
- 缩略图展示

#### 1.4 导出功能
- 生成试衣效果图
- 下载图片
- 分享功能

### 2. 后端实现

#### 2.1 图片处理服务
文件: `apps/api/services/image_process_service.py`

功能:
- 图片格式转换
- 背景透明化（可选）
- 图片压缩

#### 2.2 图片资源接口
- 获取人体模特列表
- 获取衣物图片

### 3. 图片资源准备

#### 3.1 人体模特
- 准备 3-5 个不同体型的人体模特
- 格式: PNG 透明背景
- 分辨率: 1024x1536

#### 3.2 衣物素材
- 从现有 items 中筛选有图片的
- 处理为透明背景（可选）
- 统一分辨率

## 验收标准

### 功能验收
- [ ] 支持选择人体模特
- [ ] 支持从衣橱选择衣物
- [ ] 支持拖拽调整衣物位置
- [ ] 支持缩放衣物（0.5x - 2x）
- [ ] 支持旋转衣物（-180° ~ 180°）
- [ ] 支持多图层（可叠加多件衣物）
- [ ] 支持导出试衣效果图
- [ ] 支持重置画布

### 性能验收
- [ ] Canvas 渲染流畅（60fps）
- [ ] 图片加载时间 < 2秒
- [ ] 导出图片时间 < 3秒

### 用户体验
- [ ] 操作流畅，无明显卡顿
- [ ] 有操作提示（快捷键、按钮）
- [ ] 支持撤销/重做
- [ ] 响应式设计（适配不同屏幕）

## 交付物

### 前端文件
- `apps/web/components/features/VirtualTryOn.tsx` - 主组件
- `apps/web/components/features/TryOnCanvas.tsx` - Canvas画布
- `apps/web/components/features/ClothSelector.tsx` - 衣物选择器
- `apps/web/lib/canvas-utils.ts` - Canvas工具函数
- `apps/web/hooks/useCanvas.ts` - Canvas Hook

### 后端文件
- `apps/api/routers/virtual_tryon.py` - 试衣相关接口
- `apps/api/services/image_process_service.py` - 图片处理服务

### 资源文件
- `apps/web/public/models/` - 人体模特图片
- `data/tryon_assets/` - 试衣素材

## 接口设计

### 获取人体模特列表
```http
GET /api/v1/tryon/models

Response:
{
  "models": [
    {
      "id": "model_1",
      "name": "标准体型",
      "image_url": "/models/standard.png",
      "gender": "female"
    }
  ]
}
```

### 获取可试衣衣物
```http
GET /api/v1/tryon/clothes?category=上装

Response:
{
  "items": [
    {
      "id": "uuid",
      "name": "红色衬衫",
      "image_url": "/static/images/...",
      "category": "上装"
    }
  ]
}
```

## 技术细节

### Canvas 操作
```typescript
// 绘制顺序
1. 清空画布
2. 绘制人体模特（底层）
3. 绘制衣物（可拖拽图层）
4. 绘制装饰/文字（顶层）

// 变换操作
ctx.save();
ctx.translate(x, y);
ctx.scale(scale, scale);
ctx.rotate(rotation);
ctx.drawImage(image, -width/2, -height/2);
ctx.restore();
```

### 交互逻辑
```typescript
// 拖拽逻辑
onMouseDown: 记录起始位置，检测是否点击衣物
onMouseMove: 计算偏移量，更新衣物位置
onMouseUp: 结束拖拽

// 缩放逻辑
onWheel: 根据滚轮方向调整 scale

// 旋转逻辑
提供旋转滑块或按钮，调整 rotation 角度
```

## 参考资源

- Canvas API: https://developer.mozilla.org/zh-CN/docs/Web/API/Canvas_API
- Fabric.js (可选): http://fabricjs.com/
- html2canvas: https://html2canvas.hertzen.com/

## 预估工时
- 前端开发: 8小时
- 后端开发: 2小时
- 图片资源准备: 2小时
- 测试调试: 2小时
- **总计: 14小时**

## 依赖任务
- Week 4: 用户衣橱系统（需要衣物数据）
- Week 5-01: 图片上传（可选，用于上传自定义衣物）

## 注意事项
1. 本任务为 Mock 级别，不涉及真实 3D 试衣
2. 衣物图片最好有透明背景，效果更真实
3. 考虑移动端触摸操作的支持
4. 导出图片分辨率建议 1080x1920
