import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FortunePage from '../page'

vi.mock('framer-motion', () => ({
  motion: {
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

vi.mock('@/components/features/fortune/FortuneCard', () => ({
  FortuneCard: ({ fortune }: any) => <div data-testid="fortune-card">{fortune.overall_score}</div>,
}))

vi.mock('@/components/features/fortune/FortuneRadar', () => ({
  FortuneRadar: ({ scores }: any) => <div data-testid="fortune-radar">{JSON.stringify(scores)}</div>,
}))

vi.mock('@/components/features/fortune/LuckyElements', () => ({
  LuckyElements: ({ luckyElements }: any) => <div data-testid="lucky-elements">{JSON.stringify(luckyElements)}</div>,
}))

let mockFortuneStore: any = {}
let mockUserStore: any = {}

vi.mock('@/store/fortune', () => ({
  useFortuneStore: () => mockFortuneStore,
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => mockUserStore,
}))

describe('FortunePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFortuneStore = {
      todayFortune: null,
      isLoading: false,
      error: null,
      fetchTodayFortune: vi.fn(),
      regenerateFortune: vi.fn(),
      clearError: vi.fn(),
    }
    mockUserStore = { isAuthenticated: false }
  })

  it('should show login prompt when not authenticated', () => {
    render(<FortunePage />)
    expect(screen.getByText('🔮')).toBeInTheDocument()
    expect(screen.getByText('每日运势')).toBeInTheDocument()
    expect(screen.getByText('登录后即可查看基于您八字的专属运势分析')).toBeInTheDocument()
  })

  it('should show loading spinner when loading and no fortune', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.isLoading = true
    const { container } = render(<FortunePage />)
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('should call fetchTodayFortune on mount when authenticated', () => {
    mockUserStore.isAuthenticated = true
    render(<FortunePage />)
    expect(mockFortuneStore.fetchTodayFortune).toHaveBeenCalled()
  })

  it('should not call fetchTodayFortune when not authenticated', () => {
    render(<FortunePage />)
    expect(mockFortuneStore.fetchTodayFortune).not.toHaveBeenCalled()
  })

  it('should call clearError on unmount', () => {
    mockUserStore.isAuthenticated = true
    const { unmount } = render(<FortunePage />)
    unmount()
    expect(mockFortuneStore.clearError).toHaveBeenCalled()
  })

  it('should render fortune data when available', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = {
      overall_score: 85,
      scores: { health: 80, wealth: 90 },
      lucky_elements: { colors: ['红色'], materials: [], directions: [], elements: [] },
    }
    render(<FortunePage />)
    expect(screen.getByTestId('fortune-card')).toBeInTheDocument()
    expect(screen.getByTestId('fortune-radar')).toBeInTheDocument()
    expect(screen.getByTestId('lucky-elements')).toBeInTheDocument()
  })

  it('should show regenerate button', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = { overall_score: 85, scores: {} }
    render(<FortunePage />)
    expect(screen.getByText('重新生成')).toBeInTheDocument()
  })

  it('should call regenerateFortune when button is clicked', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = { overall_score: 85, scores: {} }
    render(<FortunePage />)
    fireEvent.click(screen.getByText('重新生成'))
    expect(mockFortuneStore.regenerateFortune).toHaveBeenCalled()
  })

  it('should show loading text on button when isLoading', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = { overall_score: 85, scores: {} }
    mockFortuneStore.isLoading = true
    render(<FortunePage />)
    expect(screen.getByText('生成中...')).toBeInTheDocument()
  })

  it('should show no data message when fortune is null', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = null
    render(<FortunePage />)
    expect(screen.getByText('暂无运势数据')).toBeInTheDocument()
  })

  it('should show error message when error exists', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.error = '网络错误'
    render(<FortunePage />)
    expect(screen.getByText('网络错误')).toBeInTheDocument()
  })

  it('should render bazi snapshot when available', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = {
      overall_score: 85,
      scores: {},
      bazi_snapshot: { pillars: ['甲子', '乙丑', '丙寅', '丁卯'] },
    }
    render(<FortunePage />)
    expect(screen.getByText('八字分析依据')).toBeInTheDocument()
    expect(screen.getByText('年柱')).toBeInTheDocument()
    expect(screen.getByText('甲子')).toBeInTheDocument()
  })

  it('should render "-" for missing pillar data', () => {
    mockUserStore.isAuthenticated = true
    mockFortuneStore.todayFortune = {
      overall_score: 85,
      scores: {},
      bazi_snapshot: { pillars: ['甲子', null, null, null] },
    }
    render(<FortunePage />)
    expect(screen.getAllByText('-').length).toBeGreaterThan(0)
  })
})
