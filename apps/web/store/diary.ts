/**
 * 穿搭日记状态管理
 */
import { create } from 'zustand'
import {
  getDiaries,
  createDiary,
  getDiaryById,
  updateDiary,
  deleteDiary,
  getDiaryCalendar,
  getDiaryStats,
  triggerDiaryReview,
  CreateDiaryRequest,
  UpdateDiaryRequest,
} from '@/lib/api'
import type { OutfitDiary, DiaryCalendarEntry, DiaryStats } from '@/types'

interface DiaryState {
  diaries: OutfitDiary[]
  total: number
  page: number
  calendar: DiaryCalendarEntry[]
  calendarYear: number
  calendarMonth: number
  stats: DiaryStats | null
  currentDiary: OutfitDiary | null
  isLoading: boolean
  error: string | null

  fetchDiaries: (params?: { page?: number; size?: number; mood?: string }) => Promise<void>
  fetchDiary: (id: number) => Promise<void>
  createNewDiary: (data: CreateDiaryRequest) => Promise<OutfitDiary>
  updateExistingDiary: (id: number, data: UpdateDiaryRequest) => Promise<void>
  deleteExistingDiary: (id: number) => Promise<void>
  fetchCalendar: (year: number, month: number) => Promise<void>
  fetchStats: () => Promise<void>
  triggerReview: (diaryId: number) => Promise<void>
  clearError: () => void
}

export const useDiaryStore = create<DiaryState>()((set, get) => ({
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

  fetchDiaries: async (params) => {
    set({ isLoading: true, error: null })
    try {
      const res = await getDiaries(params)
      set({ diaries: res.diaries, total: res.total, page: res.page, isLoading: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '获取日记失败', isLoading: false })
    }
  },

  fetchDiary: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const diary = await getDiaryById(id)
      set({ currentDiary: diary, isLoading: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '获取日记详情失败', isLoading: false })
    }
  },

  createNewDiary: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const diary = await createDiary(data)
      set((s) => ({ diaries: [diary, ...s.diaries], total: s.total + 1, isLoading: false }))
      return diary
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '创建日记失败', isLoading: false })
      throw e
    }
  },

  updateExistingDiary: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await updateDiary(id, data)
      set((s) => ({
        diaries: s.diaries.map((d) => (d.id === id ? updated : d)),
        currentDiary: s.currentDiary?.id === id ? updated : s.currentDiary,
        isLoading: false,
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '更新日记失败', isLoading: false })
      throw e
    }
  },

  deleteExistingDiary: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await deleteDiary(id)
      set((s) => ({
        diaries: s.diaries.filter((d) => d.id !== id),
        total: s.total - 1,
        isLoading: false,
      }))
    } catch (e) {
      set({ error: e instanceof Error ? e.message : '删除日记失败', isLoading: false })
      throw e
    }
  },

  fetchCalendar: async (year, month) => {
    try {
      const res = await getDiaryCalendar(year, month)
      set({ calendar: res.entries, calendarYear: year, calendarMonth: month })
    } catch (e) {
      console.error('获取日历失败', e)
    }
  },

  fetchStats: async () => {
    try {
      const res = await getDiaryStats()
      set({ stats: res })
    } catch (e) {
      console.error('获取统计失败', e)
    }
  },

  triggerReview: async (diaryId) => {
    try {
      const res = await triggerDiaryReview(diaryId)
      set((s) => ({
        currentDiary: s.currentDiary?.id === diaryId
          ? { ...s.currentDiary, ai_review: res.ai_review }
          : s.currentDiary,
      }))
    } catch (e) {
      console.error('AI点评失败', e)
    }
  },

  clearError: () => set({ error: null }),
}))
