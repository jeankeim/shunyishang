/**
 * 每日运势状态管理
 */
import { create } from 'zustand'
import { getTodayFortune, generateFortune as apiGenerateFortune } from '@/lib/api'
import type { DailyFortune } from '@/types'

interface FortuneState {
  todayFortune: DailyFortune | null
  isLoading: boolean
  error: string | null

  fetchTodayFortune: () => Promise<void>
  regenerateFortune: () => Promise<void>
  clearError: () => void
}

export const useFortuneStore = create<FortuneState>()((set) => ({
  todayFortune: null,
  isLoading: false,
  error: null,

  fetchTodayFortune: async () => {
    set({ isLoading: true, error: null })
    try {
      const fortune = await getTodayFortune()
      set({ todayFortune: fortune, isLoading: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '获取运势失败', isLoading: false })
    }
  },

  regenerateFortune: async () => {
    set({ isLoading: true, error: null })
    try {
      const fortune = await apiGenerateFortune()
      set({ todayFortune: fortune, isLoading: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '生成运势失败', isLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
