'use client'

import { useEffect } from 'react'
import { useTheme } from '@/hooks/useTheme'
import { useUserStore } from '@/store/user'
import { useChatStore } from '@/store/chat'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { currentTerm, mounted } = useTheme()
  const initAuth = useUserStore((state) => state.initAuth)

  useEffect(() => {
    // 手动 rehydrate（skipHydration: true 防止 SSR 不一致）
    useUserStore.persist.rehydrate()
    useChatStore.persist.rehydrate()
    // 初始化认证状态（恢复token并验证状态一致性）
    initAuth()
  }, [initAuth])

  useEffect(() => {
    if (currentTerm) {
      document.documentElement.style.setProperty('--primary', currentTerm.cssVariable)
      document.documentElement.style.setProperty('--ring', currentTerm.cssVariable)
    }
  }, [currentTerm])

  return <>{children}</>
}
