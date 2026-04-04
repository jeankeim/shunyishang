# Week 5 - Task 01: 图片上传与Embedding

## 任务概述
实现用户上传衣物图片功能，支持图片存储与访问。

## 背景与目标
当前系统需要支持用户上传衣物图片，用于衣橱管理和展示。本任务将实现图片上传、存储和访问功能。

## 技术要求

### 前端
- 图片上传组件（支持拖拽、预览、进度显示）
- 图片格式验证（JPG/PNG，最大 5MB）
- 上传进度反馈

### 后端
- 图片接收与临时存储
- 图片持久化存储（本地文件系统）
- 图片访问接口

### 数据库
- items 表添加 image_url 字段（如不存在）

## 实现步骤

### 1. 后端实现

#### 1.1 安装依赖
```bash
pip install transformers torch Pillow
```

#### 1.2 创建图片上传服务
文件: `apps/api/services/image_upload_service.py`

核心功能:
- 图片格式验证
- 图片大小验证
- 文件存储管理
- URL 生成

#### 1.3 图片上传路由
文件: `apps/api/routers/wardrobe.py` (已实现)

接口:
- `POST /api/v1/wardrobe/upload-image` - 上传图片
- `GET /uploads/wardrobe/{user_id}/{filename}` - 获取图片（通过静态文件服务）

#### 1.4 图片存储
- 本地存储路径: `data/uploads/images/`
- 文件名: `{uuid}.{ext}`
- 访问URL: `/static/images/{filename}`

### 2. 前端实现

#### 2.1 图片上传组件
文件: `apps/web/components/features/ImageUploader.tsx`

功能:
- 拖拽上传
- 图片预览
- 上传进度
- 格式/大小验证

#### 2.2 图片预览与展示
在现有衣橱组件中集成图片显示功能

功能:
- 图片预览
- 图片列表展示
- 图片加载优化

#### 2.3 API 封装
文件: `apps/web/lib/api.ts` (已实现)

添加:
- `uploadImage(file: File): Promise<{image_url: string}>`

## 验收标准

### 功能验收
- [ ] 支持 JPG/PNG 格式图片上传，最大 5MB
- [ ] 图片上传后正确存储到本地文件系统
- [ ] 图片可通过 URL 正常访问
- [ ] 上传进度反馈正常
- [ ] 图片格式/大小验证有效

### 性能验收
- [ ] 图片上传响应时间 < 2秒
- [ ] 图片访问响应时间 < 200ms
- [ ] 支持并发上传（5个并发）

### 代码质量
- [ ] 代码通过类型检查
- [ ] 添加错误处理
- [ ] 添加日志记录
- [ ] 单元测试覆盖率 > 60%

## 交付物

### 后端文件
- `apps/api/routers/wardrobe.py` - 图片上传路由（已实现）
- `apps/api/core/config.py` - 添加图片配置

### 前端文件
- `apps/web/components/features/AddWardrobeModal.tsx` - 图片上传组件（已实现）
- `apps/web/lib/api.ts` - 上传API封装（已实现）

### 配置文件
- 更新 `apps/web/next.config.js` - 配置静态文件服务
- 创建 `apps/web/public/uploads` 符号链接

## 参考资源

- FastAPI 文件上传: https://fastapi.tiangolo.com/tutorial/request-files/
- Next.js 静态文件: https://nextjs.org/docs/basic-features/static-file-serving

## 预估工时
- 后端开发: 2小时
- 前端开发: 2小时
- 测试调试: 1小时
- **总计: 5小时**

## 依赖任务
- Week 1: 数据库基础设施
- Week 2: 后端服务架构
- Week 4: 用户衣橱系统（已有图片上传基础）
