# Week 5 - Task 01: 图片上传与Embedding

## 任务概述
实现用户上传衣物图片功能，使用 CLIP 模型生成图片 Embedding，支持以图搜图功能。

## 背景与目标
当前系统仅支持文本描述搜索，用户希望能够通过上传图片来搜索相似衣物。本任务将引入多模态能力，使用 CLIP 模型将图片转换为向量，实现图片语义搜索。

## 技术要求

### 前端
- 图片上传组件（支持拖拽、预览、进度显示）
- 图片格式验证（JPG/PNG，最大 5MB）
- 上传进度反馈
- 以图搜图界面

### 后端
- 图片接收与临时存储
- CLIP 模型集成（openai/clip-vit-base-patch32）
- 图片 Embedding 生成（512维向量）
- 向量相似度搜索
- 图片持久化存储（本地文件系统）

### 数据库
- items 表添加 image_url 字段（如不存在）
- 可选：添加 image_embedding 向量字段

## 实现步骤

### 1. 后端实现

#### 1.1 安装依赖
```bash
pip install transformers torch Pillow
```

#### 1.2 创建图片 Embedding 服务
文件: `apps/api/services/image_embedding_service.py`

核心功能:
- 加载 CLIP 模型（单例模式）
- 图片预处理（resize, normalize）
- 生成图片 Embedding
- 文本-图片相似度计算

#### 1.3 创建图片搜索路由
文件: `apps/api/routers/image_search.py`

接口:
- `POST /api/v1/image/upload` - 上传图片并生成 Embedding
- `POST /api/v1/image/search` - 以图搜图
- `GET /api/v1/image/{image_id}` - 获取图片

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

#### 2.2 以图搜图界面
文件: `apps/web/components/features/ImageSearch.tsx`

功能:
- 上传图片搜索
- 显示相似衣物结果
- 相似度分数展示

#### 2.3 API 封装
文件: `apps/web/lib/api.ts`

添加:
- `uploadImage(file: File): Promise<ImageUploadResult>`
- `searchByImage(imageId: string): Promise<SearchResult[]>`

## 验收标准

### 功能验收
- [ ] 支持 JPG/PNG 格式图片上传，最大 5MB
- [ ] 图片上传后自动生成 512维图片 Embedding
- [ ] 支持以图搜图功能（根据上传图片搜索相似衣物）
- [ ] 搜索结果按相似度排序
- [ ] 图片正确存储并可访问

### 性能验收
- [ ] 图片 Embedding 生成时间 < 2秒
- [ ] 以图搜图响应时间 < 500ms
- [ ] 支持并发上传（5个并发）

### 代码质量
- [ ] 代码通过类型检查
- [ ] 添加错误处理
- [ ] 添加日志记录
- [ ] 单元测试覆盖率 > 60%

## 交付物

### 后端文件
- `apps/api/services/image_embedding_service.py` - CLIP模型服务
- `apps/api/routers/image_search.py` - 图片搜索路由
- `apps/api/schemas/image.py` - 图片相关Schema

### 前端文件
- `apps/web/components/features/ImageUploader.tsx` - 图片上传组件
- `apps/web/components/features/ImageSearch.tsx` - 以图搜图组件
- `apps/web/hooks/useImageUpload.ts` - 上传Hook

### 配置文件
- 更新 `apps/api/main.py` - 注册路由
- 更新 `apps/api/core/config.py` - 添加图片配置
- 更新 `docker-compose.yml` - 添加图片卷映射

## 参考资源

- CLIP 模型: https://huggingface.co/openai/clip-vit-base-patch32
- CLIP 论文: https://arxiv.org/abs/2103.00020
- FastAPI 文件上传: https://fastapi.tiangolo.com/tutorial/request-files/

## 预估工时
- 后端开发: 6小时
- 前端开发: 4小时
- 测试调试: 2小时
- **总计: 12小时**

## 依赖任务
- Week 1: 数据库基础设施
- Week 2: 后端服务架构
- Week 4: 用户衣橱系统（已有图片上传基础）
