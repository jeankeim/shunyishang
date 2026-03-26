'use client'

import { useState, useEffect } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const { currentTerm, mounted } = useTheme()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true) // 默认折叠

  // 响应式：小屏幕自动收起 sidebar
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarCollapsed(true)
      }
    }
    
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  return (
    <div
      className={cn('flex h-screen bg-background')}
      data-element={mounted ? currentTerm?.element : undefined}
    >
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={toggleSidebar}
      />
      <main 
        className={cn(
          'flex-1 flex flex-col min-w-0 overflow-hidden transition-all duration-300',
          !sidebarCollapsed && 'ml-[360px]'
        )}
      >
        <Header 
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={toggleSidebar}
        />
        <div className="flex-1 overflow-hidden">{children}</div>
      </main>
    </div>
  )
}
