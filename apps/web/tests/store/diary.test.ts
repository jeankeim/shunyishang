import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useDiaryStore } from '@/store/diary'
import type { OutfitDiary } from '@/types'

vi.mock('@/lib/api', () => ({
  getDiaries: vi.fn(),
  createDiary: vi.fn(),
  getDiaryById: vi.fn(),
  updateDiary: vi.fn(),
  deleteDiary: vi.fn(),
  getDiaryCalendar: vi.fn(),
  getDiaryStats: vi.fn(),
  triggerDiaryReview: vi.fn(),
}))

import {
  getDiaries,
  createDiary,
  getDiaryById,
  updateDiary,
  deleteDiary,
  getDiaryCalendar,
  getDiaryStats,
  triggerDiaryReview,
} from '@/lib/api'

const mockDiary: OutfitDiary = {
  id: 1,
  user_id: 1,
  diary_date: '2024-01-15',
  mood: 'happy',
  occasion: '工作',
  notes: '今天穿得很舒服',
  rating: 5,
  items: [],
  created_at: '2024-01-15T00:00:00Z',
  updated_at: '2024-01-15T00:00:00Z',
}

describe('useDiaryStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDiaryStore.setState({
      diaries: [],
      total: 0,
      page: 1,
      calendar: [],
      calendarYear: new Date().getFullYear(),
      calendarMonth: new Date().getMonth() + 1,
      stats: null,
      currentDiary: null,
      isLoading: false,
      error: null,
    })
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useDiaryStore.getState()
      expect(state.diaries).toEqual([])
      expect(state.total).toBe(0)
      expect(state.page).toBe(1)
      expect(state.calendar).toEqual([])
      expect(state.stats).toBeNull()
      expect(state.currentDiary).toBeNull()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('should have current year and month for calendar', () => {
      const state = useDiaryStore.getState()
      expect(state.calendarYear).toBe(new Date().getFullYear())
      expect(state.calendarMonth).toBe(new Date().getMonth() + 1)
    })
  })

  describe('fetchDiaries', () => {
    it('should fetch diaries successfully', async () => {
      vi.mocked(getDiaries).mockResolvedValue({
        diaries: [mockDiary],
        total: 1,
        page: 1,
      })

      await useDiaryStore.getState().fetchDiaries({ page: 1, size: 10 })

      expect(getDiaries).toHaveBeenCalledWith({ page: 1, size: 10 })
      const state = useDiaryStore.getState()
      expect(state.diaries).toEqual([mockDiary])
      expect(state.total).toBe(1)
      expect(state.page).toBe(1)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getDiaries).mockRejectedValue(new Error('获取失败'))

      await useDiaryStore.getState().fetchDiaries()

      const state = useDiaryStore.getState()
      expect(state.error).toBe('获取失败')
      expect(state.isLoading).toBe(false)
    })

    it('should set generic error for non-Error throws', async () => {
      vi.mocked(getDiaries).mockRejectedValue('fail')

      await useDiaryStore.getState().fetchDiaries()

      expect(useDiaryStore.getState().error).toBe('获取日记失败')
    })
  })

  describe('fetchDiary', () => {
    it('should fetch single diary successfully', async () => {
      vi.mocked(getDiaryById).mockResolvedValue(mockDiary)

      await useDiaryStore.getState().fetchDiary(1)

      expect(getDiaryById).toHaveBeenCalledWith(1)
      const state = useDiaryStore.getState()
      expect(state.currentDiary).toEqual(mockDiary)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getDiaryById).mockRejectedValue(new Error('获取详情失败'))

      await useDiaryStore.getState().fetchDiary(1)

      expect(useDiaryStore.getState().error).toBe('获取详情失败')
    })
  })

  describe('createNewDiary', () => {
    it('should create diary successfully', async () => {
      vi.mocked(createDiary).mockResolvedValue(mockDiary)

      const result = await useDiaryStore.getState().createNewDiary({
        diary_date: '2024-01-15',
        mood: 'happy',
      })

      expect(createDiary).toHaveBeenCalledWith({ diary_date: '2024-01-15', mood: 'happy' })
      expect(result).toEqual(mockDiary)
      const state = useDiaryStore.getState()
      expect(state.diaries).toEqual([mockDiary])
      expect(state.total).toBe(1)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on create failure', async () => {
      vi.mocked(createDiary).mockRejectedValue(new Error('创建失败'))

      await expect(useDiaryStore.getState().createNewDiary({ diary_date: '2024-01-15' })).rejects.toThrow('创建失败')

      expect(useDiaryStore.getState().error).toBe('创建失败')
    })
  })

  describe('updateExistingDiary', () => {
    it('should update diary successfully', async () => {
      useDiaryStore.setState({ diaries: [mockDiary], currentDiary: mockDiary })
      const updated = { ...mockDiary, notes: 'Updated notes' }
      vi.mocked(updateDiary).mockResolvedValue(updated)

      await useDiaryStore.getState().updateExistingDiary(1, { notes: 'Updated notes' })

      expect(updateDiary).toHaveBeenCalledWith(1, { notes: 'Updated notes' })
      const state = useDiaryStore.getState()
      expect(state.diaries[0]).toEqual(updated)
      expect(state.currentDiary).toEqual(updated)
      expect(state.isLoading).toBe(false)
    })

    it('should not update currentDiary if different id', async () => {
      const otherDiary = { ...mockDiary, id: 2 }
      useDiaryStore.setState({ diaries: [mockDiary, otherDiary], currentDiary: mockDiary })
      const updated = { ...otherDiary, notes: 'Updated' }
      vi.mocked(updateDiary).mockResolvedValue(updated)

      await useDiaryStore.getState().updateExistingDiary(2, { notes: 'Updated' })

      const state = useDiaryStore.getState()
      expect(state.currentDiary).toEqual(mockDiary)
    })

    it('should set error on update failure', async () => {
      vi.mocked(updateDiary).mockRejectedValue(new Error('更新失败'))

      await expect(useDiaryStore.getState().updateExistingDiary(1, {})).rejects.toThrow('更新失败')

      expect(useDiaryStore.getState().error).toBe('更新失败')
    })
  })

  describe('deleteExistingDiary', () => {
    it('should delete diary successfully', async () => {
      useDiaryStore.setState({ diaries: [mockDiary, { ...mockDiary, id: 2 }], total: 2 })
      vi.mocked(deleteDiary).mockResolvedValue(undefined)

      await useDiaryStore.getState().deleteExistingDiary(1)

      expect(deleteDiary).toHaveBeenCalledWith(1)
      const state = useDiaryStore.getState()
      expect(state.diaries).toHaveLength(1)
      expect(state.diaries[0].id).toBe(2)
      expect(state.total).toBe(1)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on delete failure', async () => {
      vi.mocked(deleteDiary).mockRejectedValue(new Error('删除失败'))

      await expect(useDiaryStore.getState().deleteExistingDiary(1)).rejects.toThrow('删除失败')

      expect(useDiaryStore.getState().error).toBe('删除失败')
    })
  })

  describe('fetchCalendar', () => {
    it('should fetch calendar successfully', async () => {
      const calendarEntries = [
        { date: '2024-01-15', mood: 'happy', rating: 5, has_items: true },
      ]
      vi.mocked(getDiaryCalendar).mockResolvedValue({ entries: calendarEntries })

      await useDiaryStore.getState().fetchCalendar(2024, 1)

      expect(getDiaryCalendar).toHaveBeenCalledWith(2024, 1)
      const state = useDiaryStore.getState()
      expect(state.calendar).toEqual(calendarEntries)
      expect(state.calendarYear).toBe(2024)
      expect(state.calendarMonth).toBe(1)
    })

    it('should not set error on fetch calendar failure (console.error only)', async () => {
      vi.mocked(getDiaryCalendar).mockRejectedValue(new Error('Calendar fetch failed'))

      await useDiaryStore.getState().fetchCalendar(2024, 1)

      expect(useDiaryStore.getState().error).toBeNull()
    })
  })

  describe('fetchStats', () => {
    it('should fetch stats successfully', async () => {
      const mockStats = {
        total_diaries: 10,
        avg_rating: 4.5,
        mood_distribution: { happy: 5, neutral: 3, sad: 2 },
        streak_days: 5,
        total_items: 20,
      }
      vi.mocked(getDiaryStats).mockResolvedValue(mockStats)

      await useDiaryStore.getState().fetchStats()

      expect(useDiaryStore.getState().stats).toEqual(mockStats)
    })

    it('should not set error on fetch stats failure', async () => {
      vi.mocked(getDiaryStats).mockRejectedValue(new Error('Stats fetch failed'))

      await useDiaryStore.getState().fetchStats()

      expect(useDiaryStore.getState().error).toBeNull()
    })
  })

  describe('triggerReview', () => {
    it('should trigger review and update currentDiary', async () => {
      useDiaryStore.setState({ currentDiary: mockDiary })
      const reviewResult = { score: 90, comment: 'Great outfit!' }
      vi.mocked(triggerDiaryReview).mockResolvedValue({ ai_review: reviewResult })

      await useDiaryStore.getState().triggerReview(1)

      expect(triggerDiaryReview).toHaveBeenCalledWith(1)
      const state = useDiaryStore.getState()
      expect(state.currentDiary?.ai_review).toEqual(reviewResult)
    })

    it('should not update currentDiary if different id', async () => {
      const otherDiary = { ...mockDiary, id: 2 }
      useDiaryStore.setState({ currentDiary: otherDiary })
      vi.mocked(triggerDiaryReview).mockResolvedValue({ ai_review: { score: 90 } })

      await useDiaryStore.getState().triggerReview(1)

      const state = useDiaryStore.getState()
      expect(state.currentDiary?.ai_review).toBeUndefined()
    })

    it('should not set error on trigger review failure', async () => {
      vi.mocked(triggerDiaryReview).mockRejectedValue(new Error('Review failed'))

      await useDiaryStore.getState().triggerReview(1)

      expect(useDiaryStore.getState().error).toBeNull()
    })
  })

  describe('clearError', () => {
    it('should clear error', () => {
      useDiaryStore.setState({ error: 'some error' })
      useDiaryStore.getState().clearError()
      expect(useDiaryStore.getState().error).toBeNull()
    })
  })
})
