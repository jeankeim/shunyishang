# Task 01: Next.js 骨架与基础配置

## 目标
初始化前端项目，配置 Tailwind CSS、Shadcn/UI 组件库及 SSE API 客户端。

## 执行步骤

### 1. 目录初始化
```bash
cd /Users/mingyang/Desktop/shunyishang/apps
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

### 2. 初始化 Shadcn/UI
```bash
cd web
npx shadcn-ui@latest init --yes --template next --base-color slate
```

### 3. 安装依赖
```bash
# 核心依赖
npm install recharts lucide-react framer-motion zustand

# Shadcn 组件
npx shadcn-ui@latest add button card dialog input textarea avatar separator scroll-area badge radio-group label
```

### 4. 目录结构
```
apps/web/
├── app/
│   ├── layout.tsx          # 根布局（深色模式 + 节气主题）
│   ├── page.tsx            # 首页 Dashboard
│   ├── globals.css         # 全局样式 + CSS 变量
│   └── providers.tsx       # Provider 组合
├── components/
│   ├── ui/                 # Shadcn 组件
│   └── features/           # 业务组件
│       ├── FiveElementRadar.tsx
│       ├── ChatInterface.tsx
│       ├── Sidebar.tsx
│       └── TypewriterText.tsx
├── lib/
│   ├── api.ts              # SSE 客户端
│   ├── utils.ts            # CN 工具函数
│   ├── constants.ts        # 24 节气映射
│   └── theme.ts            # 主题工具
├── store/
│   └── chat.ts             # Zustand 状态管理
├── types/
│   └── index.ts            # TypeScript 类型
├── public/
│   └── images/
├── .env.local
├── next.config.js
├── tailwind.config.ts
└── package.json
```

### 5. SSE 客户端 (lib/api.ts)
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface RecommendRequest {
  query: string;
  scene?: string;
  bazi?: {
    birth_year: number;
    birth_month: number;
    birth_day: number;
    birth_hour: number;
    gender: '男' | '女';
  };
  top_k?: number;
}

export interface SSEEvent {
  type: 'analysis' | 'items' | 'token' | 'done' | 'error';
  data: any;
}

/**
 * 流式推荐请求 - 返回 AsyncGenerator
 */
export async function* streamRecommendation(
  request: RecommendRequest
): AsyncGenerator<SSEEvent, void, unknown> {
  const response = await fetch(`${API_BASE}/api/v1/recommend/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(request),
  });

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: SSEEvent = JSON.parse(line.slice(6));
          yield event;
        } catch (e) {
          console.error('Parse error:', e);
        }
      }
    }
  }
}

/**
 * 健康检查
 */
export async function checkHealth(): Promise<{ status: string; db: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
}
```

### 6. 环境变量 (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=五行智能衣橱
```

### 7. 全局样式 (globals.css)
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* 五行色 */
  --wuxing-metal: #E5E7EB;
  --wuxing-wood: #4ADE80;
  --wuxing-water: #60A5FA;
  --wuxing-fire: #F87171;
  --wuxing-earth: #D97706;
  
  /* 深色模式默认 */
  --background: 222 47% 6%;
  --foreground: 210 40% 98%;
}

[data-element="wood"] { --primary: 142 76% 36%; }
[data-element="fire"] { --primary: 0 84% 60%; }
[data-element="earth"] { --primary: 35 92% 33%; }
[data-element="metal"] { --primary: 45 93% 47%; }
[data-element="water"] { --primary: 217 91% 60%; }
```

## 验收动作

1. **启动验证**
```bash
npm run dev
```
访问 http://localhost:3000 看到 Shadcn 首页。

2. **SSE 测试**
在浏览器控制台执行：
```javascript
import { streamRecommendation } from './lib/api';

(async () => {
  for await (const event of streamRecommendation({ query: '明天面试' })) {
    console.log(event);
  }
})();
```
确认能接收到后端发送的 chunk 数据。

## 验收标准
- [ ] `npm run dev` 启动成功，端口 3000
- [ ] 首页显示 Shadcn 默认样式（深色模式）
- [ ] `lib/api.ts` 中的 `streamRecommendation` 能正确解析 SSE 流
- [ ] 控制台能看到 `analysis` → `items` → `token` → `done` 各阶段数据
- [ ] 项目目录结构符合规范
