import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { SkinId, DEFAULT_SKIN } from '@/lib/skins'

interface SkinState {
  skin: SkinId
  setSkin: (skin: SkinId) => void
}

/**
 * 皮肤选择持久化存储
 * skipHydration: true — 与其它 store 一致，由 ThemeProvider 手动 rehydrate，避免 SSR 不一致
 */
export const useSkinStore = create<SkinState>()(
  persist(
    (set) => ({
      skin: DEFAULT_SKIN,
      setSkin: (skin) => set({ skin }),
    }),
    {
      name: 'wuxing-skin-storage',
      skipHydration: true,
    }
  )
)
