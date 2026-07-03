import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFortuneStore } from '@/store/fortune'

vi.mock('@/lib/api', () => ({
  getTodayFortune: vi.fn(),
  generateFortune: vi.fn(),
}))

import { getTodayFortune, generateFortune } from '@/lib/api'

const mockFortune = {
  id: 1,
  user_id: 1,
  fortune_date: '2024-01-15',
  scores: { career: 80, wealth: 70, love: 90, health: 85, study: 75 },
  overall_score: 80,
  advice_text: '今天适合穿绿色',
  lucky_elements: {
    colors: ['green'],
    materials: ['cotton'],
    directions: ['east'],
    elements: ['木'],
  },
  created_at: '2024-01-15T00:00:00Z',
}

describe('useFortuneStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFortuneStore.setState({
      todayFortune: null,
      isLoading: false,
      error: null,
    })
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useFortuneStore.getState()
      expect(state.todayFortune).toBeNull()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('fetchTodayFortune', () => {
    it('should fetch today fortune successfully', async () => {
      vi.mocked(getTodayFortune).mockResolvedValue(mockFortune)

      await useFortuneStore.getState().fetchTodayFortune()

      expect(getTodayFortune).toHaveBeenCalled()
      const state = useFortuneStore.getState()
      expect(state.todayFortune).toEqual(mockFortune)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getTodayFortune).mockRejectedValue(new Error('获取运势失败'))

      await useFortuneStore.getState().fetchTodayFortune()

      const state = useFortuneStore.getState()
      expect(state.todayFortune).toBeNull()
      expect(state.error).toBe('获取运势失败')
      expect(state.isLoading).toBe(false)
    })

    it('should set generic error for non-Error throws', async () => {
      vi.mocked(getTodayFortune).mockRejectedValue('fail')

      await useFortuneStore.getState().fetchTodayFortune()

      expect(useFortuneStore.getState().error).toBe('获取运势失败')
    })
  })

  describe('regenerateFortune', () => {
    it('should regenerate fortune successfully', async () => {
      const newFortune = { ...mockFortune, overall_score: 90 }
      vi.mocked(generateFortune).mockResolvedValue(newFortune)

      await useFortuneStore.getState().regenerateFortune()

      expect(generateFortune).toHaveBeenCalled()
      const state = useFortuneStore.getState()
      expect(state.todayFortune).toEqual(newFortune)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on regenerate failure', async () => {
      vi.mocked(generateFortune).mockRejectedValue(new Error('生成失败'))

      await useFortuneStore.getState().regenerateFortune()

      const state = useFortuneStore.getState()
      expect(state.error).toBe('生成失败')
      expect(state.isLoading).toBe(false)
    })

    it('should set generic error for non-Error throws', async () => {
      vi.mocked(generateFortune).mockRejectedValue('fail')

      await useFortuneStore.getState().regenerateFortune()

      expect(useFortuneStore.getState().error).toBe('生成运势失败')
    })
  })

  describe('clearError', () => {
    it('should clear error', () => {
      useFortuneStore.setState({ error: 'some error' })
      useFortuneStore.getState().clearError()
      expect(useFortuneStore.getState().error).toBeNull()
    })
  })
})
