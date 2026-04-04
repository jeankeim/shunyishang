# Week 5 - Task 03: 分享海报生成

## 任务概述
实现穿搭分享海报生成功能，用户可以将推荐结果生成精美的分享海报，支持一键下载和分享。

## 背景与目标
用户希望将AI推荐的穿搭结果分享到社交媒体。本任务提供多种海报模板，支持自定义文字、配色，生成高清海报图片。

## 技术要求

### 前端
- html2canvas 图片生成
- Canvas 绘图
- 海报模板设计
- 文字排版
- 图片合成

### 后端
- 提供海报数据接口
- 可选：服务端生成海报

### 设计
- 3+ 种海报模板
- 符合五行主题的设计风格
- 响应式布局

## 实现步骤

### 1. 前端实现

#### 1.1 创建海报生成器组件
文件: `apps/web/components/features/PosterGenerator.tsx`

核心功能:
- 模板选择
- 内容编辑
- 实时预览
- 图片生成

#### 1.2 设计海报模板
模板类型:
- 模板1: 简约风格 - 突出穿搭单品
- 模板2: 五行风格 - 融入五行元素设计
- 模板3: 卡片风格 - 类似社交媒体卡片

#### 1.3 实现图片生成
- html2canvas 配置优化
- 高清输出 (2x 分辨率)
- 跨域图片处理

#### 1.4 编辑功能
- 自定义标题
- 编辑推荐文案
- 调整配色主题
- 添加个人签名

### 2. 后端实现（可选）

#### 2.1 海报数据接口
- 获取推荐详情
- 获取衣物图片

#### 2.2 服务端生成（可选）
- Puppeteer 截图
- 更高质量输出

### 3. 模板设计

#### 模板1: 简约风格
```
┌─────────────────────────┐
│                         │
│      [穿搭图片]          │
│                         │
│   今日五行穿搭推荐        │
│   ━━━━━━━━━━━━━━        │
│   红色真丝衬衫           │
│   黑色西装裤             │
│   金色配饰               │
│                         │
│   喜用神：火             │
│   适宜：商务会议          │
│                         │
│   —— 顺衣尚          │
│                         │
└─────────────────────────┘
```

#### 模板2: 五行风格
```
┌─────────────────────────┐
│  ┌─────┐                │
│  │ 火  │  今日穿搭        │
│  └─────┘                │
│                         │
│      [穿搭图片]          │
│                         │
│   五行相生，运势亨通      │
│                         │
│   红色上衣 · 火          │
│   黑色裤子 · 水          │
│                         │
│   [二维码]               │
│   扫码获取你的五行穿搭    │
└─────────────────────────┘
```

#### 模板3: 卡片风格
```
┌─────────────────────────┐
│ 👤 @用户名               │
│                         │
│ 今天适合穿红色，旺事业！   │
│                         │
│ ┌─────────┐ ┌─────────┐ │
│ │  单品1   │ │  单品2   │ │
│ └─────────┘ └─────────┘ │
│ ┌─────────┐ ┌─────────┐ │
│ │  单品3   │ │  单品4   │ │
│ └─────────┘ └─────────┘ │
│                         │
│ ❤️ 128  💬 32  ↗️ 分享   │
│                         │
│ #五行穿搭 #AI推荐        │
└─────────────────────────┘
```

## 验收标准

### 功能验收
- [ ] 提供 3+ 种海报模板
- [ ] 支持自定义标题
- [ ] 支持编辑推荐文案
- [ ] 支持调整配色主题
- [ ] 支持添加个人签名
- [ ] 生成高清海报 (1080x1920)
- [ ] 支持一键下载
- [ ] 支持直接分享（调用系统分享）

### 性能验收
- [ ] 海报生成时间 < 3秒
- [ ] 预览实时更新
- [ ] 图片质量清晰

### 设计验收
- [ ] 海报美观大方
- [ ] 配色和谐
- [ ] 文字清晰可读
- [ ] 符合五行主题

## 交付物

### 前端文件
- `apps/web/components/features/PosterGenerator.tsx` - 海报生成器
- `apps/web/components/features/PosterTemplate.tsx` - 模板组件
- `apps/web/components/features/PosterEditor.tsx` - 编辑器
- `apps/web/lib/poster-templates.ts` - 模板配置
- `apps/web/lib/html2canvas-utils.ts` - 生成工具
- `apps/web/hooks/usePoster.ts` - Poster Hook

### 样式文件
- `apps/web/styles/poster-templates.css` - 模板样式

### 资源文件
- `apps/web/public/poster/assets/` - 海报素材

## 接口设计

### 获取海报数据
```http
GET /api/v1/poster/data?recommendation_id=xxx

Response:
{
  "title": "今日五行穿搭",
  "items": [
    {
      "name": "红色真丝衬衫",
      "image_url": "...",
      "element": "火",
      "color": "红色"
    }
  ],
  "xiyong": ["火", "木"],
  "scene": "商务会议",
  "quote": "火生土，今日事业运旺"
}
```

## 技术细节

### html2canvas 配置
```typescript
const config = {
  scale: 2, // 高清输出
  useCORS: true, // 跨域支持
  allowTaint: true,
  backgroundColor: null, // 透明背景
  logging: false,
  width: 540, // 设计稿宽度
  height: 960,
};
```

### 模板配置
```typescript
interface PosterTemplate {
  id: string;
  name: string;
  thumbnail: string;
  style: {
    background: string;
    primaryColor: string;
    secondaryColor: string;
    fontFamily: string;
  };
  layout: 'simple' | 'wuxing' | 'card';
}
```

## 参考资源

- html2canvas: https://html2canvas.hertzen.com/
- Canvas API: https://developer.mozilla.org/zh-CN/docs/Web/API/Canvas_API
- 设计参考: 小红书、Instagram 分享卡片

## 预估工时
- 前端开发: 6小时
- 模板设计: 3小时
- 测试调试: 2小时
- **总计: 11小时**

## 依赖任务
- Week 3: 前端核心界面（已有推荐结果展示）
- Week 4: 用户衣橱系统（可选，用于自定义海报内容）

## 注意事项
1. 跨域图片需要特殊处理（useCORS: true）
2. 中文字体需要预加载或内嵌
3. 移动端分享需要调用原生分享API
4. 考虑添加水印或品牌标识
