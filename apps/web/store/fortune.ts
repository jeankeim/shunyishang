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

  fetchTodayFortune: (silent?: boolean) => Promise<void>
  regenerateFortune: () => Promise<void>
  clearError: () => void
}

// AI 叙事后台增强期间的静默重试策略：5s / 12s / 20s 各重试一次
const PENDING_RETRY_DELAYS = [5000, 12000, 20000]
let pendingRetryTimer: ReturnType<typeof setTimeout> | null = null
let pendingRetryCount = 0

function schedulePendingRetry() {
  if (pendingRetryCount >= PENDING_RETRY_DELAYS.length) return
  const delay = PENDING_RETRY_DELAYS[pendingRetryCount]
  pendingRetryCount += 1
  if (pendingRetryTimer) clearTimeout(pendingRetryTimer)
  pendingRetryTimer = setTimeout(() => {
    pendingRetryTimer = null
    useFortuneStore.getState().fetchTodayFortune(true)
  }, delay)
}

function clearPendingRetry() {
  pendingRetryCount = 0
  if (pendingRetryTimer) {
    clearTimeout(pendingRetryTimer)
    pendingRetryTimer = null
  }
}

export const useFortuneStore = create<FortuneState>()((set) => ({
  todayFortune: null,
  isLoading: false,
  error: null,

  fetchTodayFortune: async (silent = false) => {
    // silent 模式：不展示 loading 骨架屏，用于 AI 叙事增强完成后的无感刷新
    if (!silent) set({ isLoading: true, error: null })
    try {
      const fortune = await getTodayFortune()
      set({ todayFortune: fortune, isLoading: false })
      // AI 叙事仍在后台生成：稍后静默重试拿取最终版；否则清理重试状态
      if (fortune?.ai_pending) {
        schedulePendingRetry()
      } else {
        clearPendingRetry()
      }
    } catch (e) {
      if (silent) {
        set({ isLoading: false })
      } else {
        set({ error: e instanceof Error ? e.message : '获取运势失败', isLoading: false })
      }
    }
  },

  regenerateFortune: async () => {
    clearPendingRetry()
    set({ isLoading: true, error: null })
    try {
      const fortune = await apiGenerateFortune()
      set({ todayFortune: fortune, isLoading: false })
      if (fortune?.ai_pending) {
        schedulePendingRetry()
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '生成运势失败', isLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
