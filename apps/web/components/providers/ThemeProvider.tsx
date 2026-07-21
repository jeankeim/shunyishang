'use client'

import { useEffect } from 'react'
import { useWuxingTheme } from '@/hooks/useWuxingTheme'
import { useUserStore } from '@/store/user'
import { useChatStore } from '@/store/chat'
import { useSkinStore } from '@/store/skin'
import { applySkin } from '@/lib/skins'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { element, solarTerm } = useWuxingTheme()
  const initAuth = useUserStore((state) => state.initAuth)
  const skin = useSkinStore((state) => state.skin)

  useEffect(() => {
    // 手动 rehydrate（skipHydration: true 防止 SSR 不一致）
    useUserStore.persist.rehydrate()
    useChatStore.persist.rehydrate()
    useSkinStore.persist.rehydrate()
    // 初始化认证状态（恢复token并验证状态一致性）
    initAuth()
  }, [initAuth])

  // 用户选定皮肤后应用到 <html>（data-skin + .dark），全站生效
  // 选 auto 时回落到 useWuxingTheme 的节气自动主题
  useEffect(() => {
    applySkin(skin)
  }, [skin])

  return <>{children}</>
}
