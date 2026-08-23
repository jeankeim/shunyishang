import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { FontSizeId, DEFAULT_FONT_SIZE } from '@/lib/font-sizes'

interface FontSizeState {
  fontSize: FontSizeId
  setFontSize: (size: FontSizeId) => void
}

/**
 * 字体大小选择持久化存储（适老化）
 * skipHydration: true — 与其它 store 一致，由 ThemeProvider 手动 rehydrate，避免 SSR 不一致
 */
export const useFontSizeStore = create<FontSizeState>()(
  persist(
    (set) => ({
      fontSize: DEFAULT_FONT_SIZE,
      setFontSize: (fontSize) => set({ fontSize }),
    }),
    {
      name: 'wuxing-font-size-storage',
      skipHydration: true,
    }
  )
)
