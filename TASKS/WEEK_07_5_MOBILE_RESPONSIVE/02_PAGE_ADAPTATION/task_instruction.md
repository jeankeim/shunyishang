# Task 02: 核心页面移动端适配

## 任务概述
适配所有核心页面在移动端的显示和交互。

## 依赖
- ✅ Task 01: 布局与导航适配 (必须完成)

## 目标页面清单

### 1. 首页/推荐页面 (`app/page.tsx`)
**优先级**: 🔴 P0

#### 需要调整的元素:

##### A. 五行雷达图
```tsx
// 方案: 移动端改为列表展示,桌面端保持雷达图

'use client'

import { useMediaQuery } from '@/hooks/useMediaQuery'
import { FiveElementRadar } from '@/components/features/FiveElementRadar'
import { FiveElementList } from '@/components/features/FiveElementList'

export function WuxingDisplay({ data }) {
  const isMobile = useMediaQuery('(max-width: 640px)')
  
  return (
    <div className="w-full">
      {isMobile ? (
        <FiveElementList data={data} />
      ) : (
        <FiveElementRadar data={data} className="w-[300px] h-[300px]" />
      )}
    </div>
  )
}
```

**新建文件**: `apps/web/components/features/FiveElementList.tsx`
```tsx
interface FiveElementListProps {
  data: {
    metal: number
    wood: number
    water: number
    fire: number
    earth: number
  }
}

export function FiveElementList({ data }: FiveElementListProps) {
  const elements = [
    { name: '金', key: 'metal', color: 'bg-wuxing-metal', value: data.metal },
    { name: '木', key: 'wood', color: 'bg-wuxing-wood', value: data.wood },
    { name: '水', key: 'water', color: 'bg-wuxing-water', value: data.water },
    { name: '火', key: 'fire', color: 'bg-wuxing-fire', value: data.fire },
    { name: '土', key: 'earth', color: 'bg-wuxing-earth', value: data.earth },
  ]
  
  return (
    <div className="space-y-3 p-4 bg-white rounded-lg shadow-sm">
      <h3 className="text-sm font-semibold text-stone-700">五行分析</h3>
      {elements.map(el => (
        <div key={el.key} className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-stone-600">{el.name}</span>
            <span className="font-medium">{Math.round(el.value * 100)}%</span>
          </div>
          <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
            <div 
              className={`h-full ${el.color} transition-all duration-500`}
              style={{ width: `${el.value * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
```

##### B. 推荐卡片网格
```tsx
// 响应式网格: 1列 → 2列 → 4列
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
  {items.map(item => (
    <RecommendCard key={item.id} {...item} />
  ))}
</div>
```

##### C. 聊天输入框
```tsx
// 移动端底部固定,避免键盘遮挡
<div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t border-stone-200 md:static md:border-0">
  <div className="flex gap-2">
    <input 
      className="flex-1 px-4 py-3 text-base border rounded-lg focus:ring-2"
      placeholder="描述你的场景..."
      inputMode="text"
      enterKeyHint="send"
    />
    <button className="px-6 py-3 bg-primary text-white rounded-lg font-medium touch-feedback">
      发送
    </button>
  </div>
</div>
```

##### D. 流式文本显示
```tsx
// 移动端字体自适应
<div className="text-sm sm:text-base leading-relaxed sm:leading-loose">
  {streamingText}
</div>
```

---

### 2. 衣橱页面 (`app/wardrobe/page.tsx`)
**优先级**: 🔴 P0

#### 需要调整的元素:

##### A. 图片网格
```tsx
// 2列 → 3列 → 5列
<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 sm:gap-3">
  {items.map(item => (
    <WardrobeItem key={item.id} {...item} />
  ))}
</div>
```

##### B. 筛选器
```tsx
// 移动端横向滚动标签
<div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
  {categories.map(cat => (
    <button
      key={cat}
      className={`px-4 py-2 rounded-full whitespace-nowrap text-sm touch-feedback ${
        selected === cat 
          ? 'bg-primary text-white' 
          : 'bg-stone-100 text-stone-700'
      }`}
    >
      {cat}
    </button>
  ))}
</div>
```

##### C. 添加按钮 (FAB)
```tsx
// 移动端浮动操作按钮
<button 
  className="fixed bottom-6 right-6 w-14 h-14 bg-primary text-white rounded-full shadow-lg flex items-center justify-center touch-feedback md:hidden"
  onClick={handleAdd}
>
  <Plus className="w-6 h-6" />
</button>
```

---

### 3. 海报编辑器 (`components/features/PosterEditor.tsx`)
**优先级**: 🟡 P1

#### 需要调整的元素:

##### A. Canvas 预览
```tsx
// 移动端全屏预览
<div className="relative w-full h-[calc(100vh-200px)] md:h-[600px]">
  <canvas 
    ref={canvasRef}
    className="w-full h-full object-contain"
  />
</div>
```

##### B. 工具栏
```tsx
// 移动端底部固定,横向滚动
<div className="fixed bottom-0 left-0 right-0 bg-white border-t border-stone-200 p-4 md:static md:border-0">
  <div className="flex gap-3 overflow-x-auto pb-2">
    {tools.map(tool => (
      <button
        key={tool.id}
        className="flex-shrink-0 p-3 rounded-lg bg-stone-100 touch-feedback"
        onClick={() => handleTool(tool)}
      >
        <tool.icon className="w-5 h-5" />
      </button>
    ))}
  </div>
</div>
```

---

## 实施步骤

### Step 1: 创建通用 Hooks

**文件**: `apps/web/hooks/useMediaQuery.ts`
```tsx
'use client'

import { useState, useEffect } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)
  
  useEffect(() => {
    const media = window.matchMedia(query)
    setMatches(media.matches)
    
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches)
    media.addEventListener('change', listener)
    
    return () => media.removeEventListener('change', listener)
  }, [query])
  
  return matches
}
```

### Step 2: 更新首页

**文件**: `apps/web/app/page.tsx`

**修改清单**:
1. 五行雷达图响应式 (使用 `FiveElementList`)
2. 推荐卡片网格 (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`)
3. 聊天输入框移动端优化
4. 流式文本字体自适应

### Step 3: 更新衣橱页面

**文件**: `apps/web/app/wardrobe/page.tsx`

**修改清单**:
1. 图片网格响应式 (`grid-cols-2 sm:grid-cols-3 md:grid-cols-5`)
2. 筛选器横向滚动
3. 添加 FAB 按钮
4. 图片懒加载优化

### Step 4: 更新海报编辑器

**文件**: `apps/web/components/features/PosterEditor.tsx`

**修改清单**:
1. Canvas 全屏预览
2. 工具栏底部固定
3. 模板选择横向滑动
4. 触摸手势支持

### Step 5: 添加 CSS 工具类

**文件**: `apps/web/app/globals.css`

```css
/* 隐藏滚动条但保持功能 */
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

/* 触摸反馈 */
.touch-feedback {
  @apply active:scale-95 transition-transform duration-100;
}

/* 安全区域适配 */
.safe-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
```

---

## 响应式设计原则

### 1. Mobile-First 策略
```css
/* 先写移动端样式,再逐步增强 */
.card {
  padding: 1rem;      /* 移动端 */
}

@media (min-width: 640px) {
  .card {
    padding: 1.5rem;  /* 平板端 */
  }
}

@media (min-width: 1024px) {
  .card {
    padding: 2rem;    /* 桌面端 */
  }
}
```

### 2. 流体排版
```css
/* 使用 clamp() 实现流体字体 */
.title {
  font-size: clamp(1.25rem, 4vw, 2rem);
}
```

### 3. 相对单位
```css
/* 使用 rem/em 而非 px */
.container {
  padding: 1rem;      /* 16px */
  gap: 0.75rem;       /* 12px */
}
```

---

## 验收标准

### 首页测试
- [ ] 五行列表在移动端清晰可读
- [ ] 推荐卡片在手机上单列显示
- [ ] 输入框在键盘弹出时不被遮挡
- [ ] 流式文本字体大小合适

### 衣橱页面测试
- [ ] 图片网格在手机上2列显示
- [ ] 筛选器可横向滚动
- [ ] FAB 按钮位置合理,不遮挡内容
- [ ] 图片加载无布局偏移

### 海报编辑器测试
- [ ] Canvas 在移动端可全屏查看
- [ ] 工具栏按钮尺寸 ≥ 44x44px
- [ ] 模板选择可横向滑动
- [ ] 双指缩放正常工作

### 通用测试
- [ ] 所有页面在 375px 宽度正常显示
- [ ] 所有页面在 768px 宽度正常显示
- [ ] 触摸反馈可见
- [ ] 无水平滚动条

---

## 预估工时
- 首页适配: 2小时
- 衣橱页面适配: 2小时
- 海报编辑器适配: 2小时
- 测试调试: 2小时
- **总计: 8小时**

---

## 注意事项

1. **渐进式重构**: 保持桌面端功能不受影响
2. **性能优先**: 图片懒加载,避免重渲染
3. **触摸友好**: 所有交互元素 ≥ 44x44px
4. **可访问性**: 键盘导航,屏幕阅读器支持
5. **测试覆盖**: 多设备测试,避免遗漏
