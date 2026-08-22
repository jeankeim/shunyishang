/**
 * 命理分析状态管理
 * 十神格局、大运流年、高级八字分析
 */
import { create } from 'zustand'
import { getTenGods, getAnnualLuck, getMajorLuck, getAdvancedBazi } from '@/lib/api'

// ========== 类型定义 ==========

export interface ShenShaInfo {
  name: string
  category: '吉' | '中性' | '煞' | string
  positions: string[]
  duanyu: string
}

export interface TenGodsData {
  pillars: Record<string, { stem: string; ganzhi: string; ten_god: string }>
  hidden_gods: Array<{ pillar: string; hidden_stem: string; ten_god: string }>
  dominant_gods: string[]
  weak_gods: string[]
  god_distribution: Record<string, number>
  analysis: string
  shen_sha?: ShenShaInfo[]
  shen_sha_note?: string
}

export interface LuckPeriod {
  start_age: number
  end_age: number
  heavenly_stem: string
  earthly_branch: string
  ganzhi: string
  element: string
  luck_level: string
}

export interface AnnualLuckData {
  annual_luck: {
    year: number
    heavenly_stem: string
    earthly_branch: string
    ganzhi: string
    element: string
    relationship: string
    advice: string
  }
  scores: Record<string, number>
  overall_score: number
  lucky_colors: string[]
  lucky_materials: string[]
  lucky_directions: string[]
  lucky_elements: string[]
  outfit_advice: string
}

export interface NayinItem {
  ganzhi: string
  nayin_name: string
  nayin_element: string
  nayin_description: string
}

export interface HiddenStemItem {
  stem: string
  element: string
  is_main: boolean
}

export interface AdvancedBaziData {
  pillars: Record<string, string>
  nayin: Record<string, NayinItem>
  hidden_stems: Record<string, HiddenStemItem[]>
  chong: { has_chong: boolean; pairs: Array<{ branch_a: string; branch_b: string; description: string }>; count: number }
  xing: { has_xing: boolean; groups: Array<{ type: string; branches: string[]; description: string }>; count: number }
  hai: { has_hai: boolean; pairs: Array<{ branch_a: string; branch_b: string; description: string }>; count: number }
  he: { has_he: boolean; sanhe: Array<{ type: string; branches: string[]; element: string; description: string }>; liuhe: Array<{ branch_a: string; branch_b: string; element: string; description: string }>; count: number }
  analysis: string
}

// ========== Store ==========

interface DestinyState {
  // 十神格局
  tenGods: TenGodsData | null
  isTenGodsLoading: boolean
  tenGodsError: string | null

  // 大运周期
  majorLuck: { luck_periods: LuckPeriod[]; current_luck: LuckPeriod | null } | null
  isMajorLuckLoading: boolean
  majorLuckError: string | null

  // 流年运势
  annualLuck: AnnualLuckData | null
  isAnnualLuckLoading: boolean
  annualLuckError: string | null

  // 高级八字分析
  advancedBazi: AdvancedBaziData | null
  isAdvancedBaziLoading: boolean
  advancedBaziError: string | null

  // Actions
  fetchTenGods: () => Promise<void>
  fetchMajorLuck: () => Promise<void>
  fetchAnnualLuck: (year?: number) => Promise<void>
  fetchAdvancedBazi: () => Promise<void>
  fetchAll: () => Promise<void>
  clearErrors: () => void
}

export const useDestinyStore = create<DestinyState>()((set, get) => ({
  // 十神
  tenGods: null,
  isTenGodsLoading: false,
  tenGodsError: null,

  // 大运
  majorLuck: null,
  isMajorLuckLoading: false,
  majorLuckError: null,

  // 流年
  annualLuck: null,
  isAnnualLuckLoading: false,
  annualLuckError: null,

  // 高级八字
  advancedBazi: null,
  isAdvancedBaziLoading: false,
  advancedBaziError: null,

  fetchTenGods: async () => {
    set({ isTenGodsLoading: true, tenGodsError: null })
    try {
      set({ tenGods: await getTenGods(), isTenGodsLoading: false })
    } catch (e) {
      set({ tenGodsError: e instanceof Error ? e.message : '获取十神格局失败', isTenGodsLoading: false })
    }
  },

  fetchMajorLuck: async () => {
    set({ isMajorLuckLoading: true, majorLuckError: null })
    try {
      set({ majorLuck: await getMajorLuck(), isMajorLuckLoading: false })
    } catch (e) {
      set({ majorLuckError: e instanceof Error ? e.message : '获取大运周期失败', isMajorLuckLoading: false })
    }
  },

  fetchAnnualLuck: async (year?: number) => {
    set({ isAnnualLuckLoading: true, annualLuckError: null })
    try {
      set({ annualLuck: await getAnnualLuck(year || new Date().getFullYear()), isAnnualLuckLoading: false })
    } catch (e) {
      set({ annualLuckError: e instanceof Error ? e.message : '获取流年运势失败', isAnnualLuckLoading: false })
    }
  },

  fetchAdvancedBazi: async () => {
    set({ isAdvancedBaziLoading: true, advancedBaziError: null })
    try {
      set({ advancedBazi: await getAdvancedBazi(), isAdvancedBaziLoading: false })
    } catch (e) {
      set({ advancedBaziError: e instanceof Error ? e.message : '获取高级八字分析失败', isAdvancedBaziLoading: false })
    }
  },

  fetchAll: async () => {
    const { fetchTenGods, fetchMajorLuck, fetchAnnualLuck, fetchAdvancedBazi } = get()
    fetchTenGods()
    fetchMajorLuck()
    fetchAnnualLuck()
    fetchAdvancedBazi()
  },

  clearErrors: () => set({
    tenGodsError: null,
    majorLuckError: null,
    annualLuckError: null,
    advancedBaziError: null,
  }),
}))
