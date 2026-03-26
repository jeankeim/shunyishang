# Task 03: 主界面布局与 24 节气主题

## 目标
构建类 ChatGPT 的侧边栏布局，集成 24 节气自适应主题系统。

## 布局结构
```
┌─────────────────────────────────────────────────────────┐
│  🌿 五行衣橱    首页  衣橱  设置              [节气图标]  │  ← Header (60px)
├────────┬────────────────────────────────────────────────┤
│        │                                                │
│ 对话   │     五行能量雷达图 (左侧固定 400px)             │
│ 历史   │     ┌──────────────────┐                       │
│ 列表   │     │    ⚪金  🔴火     │                       │
│        │     │  🔵水    🟡土    │                       │
│ ─────  │     │      🟢木        │                       │
│ + 新建 │     └──────────────────┘                       │
│        │                                                │
│        │  ┌────────────────────────────────────────┐    │
│        │  │  💬 对话区域                            │    │
│        │  │  用户：明天面试...                      │    │
│        │  │  AI：推荐白色... [typing]               │    │
│        │  │  [卡片] [卡片] [卡片]                   │    │
│        │  └────────────────────────────────────────┘    │
│        │                                                │
│        │  [输入框...] [发送] [📅八字]                   │
│        │                                                │
└────────┴────────────────────────────────────────────────┘
     260px                    自适应
```

## 24 节气主题系统

### 节气→五行→色彩映射
| 节气 | 五行 | 主色 | 深色背景 | CSS 变量 |
|:---:|:---:|:---:|:---:|:---|
| 立春/雨水/惊蛰 | 木 | `#22c55e` | `#0f172a` | `--primary: 142 76% 36%` |
| 春分/清明/谷雨 | 木 | `#16a34a` | `#0f1f17` | `--primary: 142 71% 45%` |
| 立夏/小满/芒种 | 火 | `#ef4444` | `#1a0f0f` | `--primary: 0 84% 60%` |
| 夏至/小暑/大暑 | 火 | `#dc2626` | `#1f0f0f` | `--primary: 0 72% 51%` |
| 立秋/处暑/白露 | 金 | `#eab308` | `#0f0f1a` | `--primary: 48 96% 53%` |
| 秋分/寒露/霜降 | 金 | `#ca8a04` | `#0f0f14` | `--primary: 45 93% 47%` |
| 立冬/小雪/大雪 | 水 | `#3b82f6` | `#0a0f1a` | `--primary: 217 91% 60%` |
| 冬至/小寒/大寒 | 水 | `#2563eb` | `#0a0f1f` | `--primary: 221 83% 53%` |
| 四季月 | 土 | `#a16207` | `#1a150f` | `--primary: 35 92% 33%` |

## 执行步骤

### 1. 节气工具 (lib/theme.ts)
```typescript
export interface SolarTerm {
  name: string;
  element: 'wood' | 'fire' | 'earth' | 'metal' | 'water';
  primaryColor: string;
  bgColor: string;
  cssVariable: string;
}

// 24 节气数据
const SOLAR_TERMS: Array<{ name: string; month: number; day: number; element: string }> = [
  { name: '立春', month: 2, day: 4, element: 'wood' },
  { name: '雨水', month: 2, day: 19, element: 'wood' },
  { name: '惊蛰', month: 3, day: 6, element: 'wood' },
  // ... 完整 24 节气
];

const ELEMENT_THEME: Record<string, SolarTerm> = {
  wood: {
    name: '木',
    element: 'wood',
    primaryColor: '#22c55e',
    bgColor: '#0f172a',
    cssVariable: '142 76% 36%',
  },
  fire: {
    name: '火',
    element: 'fire',
    primaryColor: '#ef4444',
    bgColor: '#1a0f0f',
    cssVariable: '0 84% 60%',
  },
  earth: {
    name: '土',
    element: 'earth',
    primaryColor: '#a16207',
    bgColor: '#1a150f',
    cssVariable: '35 92% 33%',
  },
  metal: {
    name: '金',
    element: 'metal',
    primaryColor: '#eab308',
    bgColor: '#0f0f1a',
    cssVariable: '48 96% 53%',
  },
  water: {
    name: '水',
    element: 'water',
    primaryColor: '#3b82f6',
    bgColor: '#0a0f1a',
    cssVariable: '217 91% 60%',
  },
};

/**
 * 获取当前节气
 */
export function getCurrentSolarTerm(date = new Date()): SolarTerm {
  const month = date.getMonth() + 1;
  const day = date.getDate();

  // 简化版：根据月份判断
  if (month >= 2 && month <= 4) return ELEMENT_THEME.wood;
  if (month >= 5 && month <= 7) return ELEMENT_THEME.fire;
  if (month >= 8 && month <= 10) return ELEMENT_THEME.metal;
  if (month >= 11 || month === 1) return ELEMENT_THEME.water;
  return ELEMENT_THEME.earth;
}
```

### 2. 主题 Hook (hooks/useTheme.ts)
```typescript
'use client';

import { useState, useEffect } from 'react';
import { getCurrentSolarTerm, SolarTerm } from '@/lib/theme';

export function useTheme() {
  const [currentTerm, setCurrentTerm] = useState<SolarTerm | null>(null);

  useEffect(() => {
    setCurrentTerm(getCurrentSolarTerm());
  }, []);

  return {
    currentTerm,
    isDark: true, // 默认深色模式
    cssVariable: currentTerm?.cssVariable || '142 76% 36%',
  };
}
```

### 3. 侧边栏组件 (components/features/Sidebar.tsx)
```typescript
'use client';

import { useState } from 'react';
import { Plus, MessageSquare, Settings, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/store/chat';

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { conversations, currentConversationId, setCurrentConversation, createConversation } = useChatStore();
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div className={cn("flex flex-col h-full bg-card border-r", className)}>
      {/* Logo */}
      <div className="p-4 border-b">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <span className="text-2xl">🌿</span>
          <span>五行衣橱</span>
        </div>
      </div>

      {/* 新建对话 */}
      <div className="p-3">
        <Button
          onClick={createConversation}
          className="w-full justify-start gap-2"
          variant="outline"
        >
          <Plus className="h-4 w-4" />
          新建对话
        </Button>
      </div>

      {/* 对话列表 */}
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setCurrentConversation(conv.id)}
              onMouseEnter={() => setHoveredId(conv.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left transition",
                currentConversationId === conv.id
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-muted"
              )}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <span className="truncate">{conv.title}</span>
            </button>
          ))}
        </div>
      </ScrollArea>

      {/* 底部：用户信息 */}
      <div className="p-4 border-t space-y-3">
        <button className="w-full flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition">
          <Settings className="h-4 w-4" />
          设置
        </button>
        <div className="flex items-center gap-2 text-sm">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="h-4 w-4" />
          </div>
          <span className="truncate">用户</span>
        </div>
      </div>
    </div>
  );
}
```

### 4. 主布局 (components/features/MainLayout.tsx)
```typescript
'use client';

import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { cn } from '@/lib/utils';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar className="w-[260px] shrink-0" />
      <main className="flex-1 flex flex-col min-w-0">
        <Header />
        <div className="flex-1 overflow-hidden">
          {children}
        </div>
      </main>
    </div>
  );
}
```

### 5. Header 组件 (components/features/Header.tsx)
```typescript
'use client';

import { useTheme } from '@/hooks/useTheme';
import { Leaf } from 'lucide-react';

export function Header() {
  const { currentTerm } = useTheme();

  return (
    <header className="h-[60px] border-b flex items-center justify-between px-6 bg-card/50 backdrop-blur">
      <div className="flex items-center gap-4">
        <h1 className="font-semibold">首页</h1>
      </div>

      {currentTerm && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Leaf className="h-4 w-4" style={{ color: currentTerm.primaryColor }} />
          <span>当前节气: {currentTerm.name}</span>
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: currentTerm.primaryColor }}
          />
        </div>
      )}
    </header>
  );
}
```

### 6. 根布局更新 (app/layout.tsx)
```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { MainLayout } from '@/components/features/MainLayout';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: '五行智能衣橱',
  description: '基于八字与五行的智能穿搭推荐',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={inter.className}>
        <ThemeProvider>
          <MainLayout>{children}</MainLayout>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

## 验收动作

1. **布局验证**
   - 侧边栏宽度 260px，固定不滚动
   - Header 高度 60px
   - 主内容区自适应剩余空间

2. **主题验证**
   - 修改系统时间，观察 Header 节气标识变化
   - 检查 CSS 变量 `--primary` 是否随节气变化

## 验收标准
- [ ] 三栏布局：侧边栏(260px) + Header(60px) + 主内容区
- [ ] 侧边栏包含：Logo、新建对话、历史列表、用户信息
- [ ] Header 显示当前节气名称和五行色指示器
- [ ] 深色模式为默认主题
- [ ] 24 节气 CSS 变量自动切换
- [ ] 桌面端 ≥1280px 显示正常
- [ ] 新建对话按钮能创建新会话
