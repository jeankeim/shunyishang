# Task 01: 布局与导航适配

## 任务概述
重构主布局系统，实现移动端友好的导航和布局切换。

## 当前问题
- ❌ 侧边栏在移动端固定显示，遮挡主内容
- ❌ 缺少移动端顶部导航
- ❌ 主内容区未响应式调整

## 目标
实现断点响应式布局：
- **< 768px**: 移动端 (抽屉式侧边栏 + 顶部导航)
- **768px - 1024px**: 平板端 (可收起侧边栏)
- **> 1024px**: 桌面端 (固定侧边栏)

## 实现步骤

### 1. 创建移动端导航组件

**文件**: `apps/web/components/layout/MobileNavbar.tsx`

**功能**:
- Hamburger 菜单按钮
- 快速导航链接 (推荐/衣橱)
- 用户头像下拉
- Sticky 定位

**技术要求**:
```tsx
'use client'

import { useState } from 'react'
import { Menu, Home, Shirt, User } from 'lucide-react'
import { useRouter } from 'next/navigation'

export function MobileNavbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const router = useRouter()
  
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-stone-200 md:hidden">
      <div className="flex items-center justify-between px-4 h-14">
        {/* Logo */}
        <div className="text-lg font-bold text-stone-800">
          顺衣尚
        </div>
        
        {/* Hamburger */}
        <button 
          onClick={() => setMenuOpen(!menuOpen)}
          className="p-2 touch-feedback"
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>
      
      {/* 下拉菜单 */}
      {menuOpen && (
        <div className="absolute top-14 left-0 right-0 bg-white border-b border-stone-200 shadow-lg">
          <div className="p-4 space-y-3">
            <button 
              onClick={() => { router.push('/'); setMenuOpen(false) }}
              className="flex items-center gap-3 w-full p-3 rounded-lg hover:bg-stone-50"
            >
              <Home className="w-5 h-5" />
              <span>智能推荐</span>
            </button>
            <button 
              onClick={() => { router.push('/wardrobe'); setMenuOpen(false) }}
              className="flex items-center gap-3 w-full p-3 rounded-lg hover:bg-stone-50"
            >
              <Shirt className="w-5 h-5" />
              <span>我的衣橱</span>
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
```

### 2. 重构侧边栏组件

**文件**: `apps/web/components/layout/Sidebar.tsx` (更新)

**改造**:
```tsx
'use client'

import { useState } from 'react'
import { Drawer, DrawerContent, DrawerTrigger } from '@/components/ui/drawer'

export function Sidebar() {
  const isMobile = useMediaQuery('(max-width: 768px)')
  
  if (isMobile) {
    // 移动端使用 Drawer
    return (
      <Drawer>
        <DrawerTrigger asChild>
          <button className="fixed bottom-4 right-4 z-50 p-3 bg-primary rounded-full shadow-lg">
            <Menu className="w-6 h-6 text-white" />
          </button>
        </DrawerTrigger>
        <DrawerContent className="max-h-[80vh]">
          <div className="p-4 overflow-y-auto">
            {/* 移动端侧边栏内容 */}
          </div>
        </DrawerContent>
      </Drawer>
    )
  }
  
  // 桌面端保持原有布局
  return (
    <aside className="w-64 fixed left-0 top-0 h-full border-r border-stone-200 bg-white">
      {/* 桌面端侧边栏内容 */}
    </aside>
  )
}
```

### 3. 更新主布局

**文件**: `apps/web/app/layout.tsx`

**修改**:
```tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-stone-50">
        <MobileNavbar />
        <div className="flex">
          <Sidebar />
          <main className="flex-1 md:ml-64 mt-14 md:mt-0">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
```

### 4. 安装必要依赖

```bash
cd apps/web
npm install @radix-ui/react-dialog lucide-react
```

## 断点设计

```css
/* 自定义断点 (Tailwind 默认) */
/* sm: 640px   - 大手机 */
/* md: 768px   - 平板 */
/* lg: 1024px  - 小桌面 */
/* xl: 1280px  - 桌面 */
/* 2xl: 1536px - 大桌面 */
```

## 验收标准

### 功能测试
- [ ] 桌面端 (> 1024px) 侧边栏固定显示
- [ ] 平板端 (768px-1024px) 侧边栏可收起
- [ ] 移动端 (< 768px) 顶部导航栏显示
- [ ] 移动端侧边栏以 Drawer 形式弹出
- [ ] 导航切换流畅，无闪烁

### 视觉测试
- [ ] 移动端顶部导航栏不遮挡内容
- [ ] 主内容区 `margin-top: 56px` (移动端)
- [ ] 主内容区 `margin-left: 256px` (桌面端)
- [ ] 断点切换平滑

### 交互测试
- [ ] Hamburger 按钮点击响应 < 100ms
- [ ] Drawer 动画流畅
- [ ] 点击遮罩层关闭菜单
- [ ] 滑动关闭 Drawer (可选)

## 预估工时
- 组件开发: 2小时
- 布局重构: 2小时
- 测试调试: 1小时
- **总计: 5小时**

## 注意事项
1. 保持桌面端现有功能不受影响
2. 使用渐进增强策略
3. 避免布局抖动 (CLS)
4. 确保导航可访问性 (键盘/屏幕阅读器)
