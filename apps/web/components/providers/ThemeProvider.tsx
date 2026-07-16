'use client'

import { useEffect } from 'react'
import { useWuxingTheme } from '@/hooks/useWuxingTheme'
import { useUserStore } from '@/store/user'
import { useChatStore } from '@/store/chat'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { element, solarTerm } = useWuxingTheme()
  const initAuth = useUserStore((state) => state.initAuth)

  useEffect(() => {
    // 手动 rehydrate（skipHydration: true 防止 SSR 不一致）
    useUserStore.persist.rehydrate()
    useChatStore.persist.rehydrate()
    // 初始化认证状态（恢复token并验证状态一致性）
    initAuth()
  }, [initAuth])

  // 主题切换已通过 useWuxingTheme hook 自动设置 data-element 属性
  // CSS 变量通过 globals.css 中的 [data-element] 选择器自动应用

  return <>{children}</>
}
