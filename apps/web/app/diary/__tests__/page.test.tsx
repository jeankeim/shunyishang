import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import DiaryPage from '../page'

const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('framer-motion', () => ({
  motion: {
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('@/components/features/diary/DiaryCard', () => ({
  DiaryCard: ({ diary, onClick, onDelete }: any) => (
    <div data-testid={`diary-card-${diary.id}`}>
      <span>{diary.id}</span>
      <button onClick={onClick}>view</button>
      <button onClick={onDelete}>delete</button>
    </div>
  ),
}))

vi.mock('@/components/features/diary/DiaryCalendar', () => ({
  DiaryCalendar: ({ year, month, onPrevMonth, onNextMonth }: any) => (
    <div data-testid="diary-calendar">
      <span>{year}-{month}</span>
      <button onClick={onPrevMonth}>prev</button>
      <button onClick={onNextMonth}>next</button>
    </div>
  ),
}))

vi.mock('@/components/features/diary/DiaryStats', () => ({
  DiaryStatsPanel: ({ stats }: any) => <div data-testid="diary-stats">{JSON.stringify(stats)}</div>,
}))

let mockDiaryStore: any = {}

vi.mock('@/store/diary', () => ({
  useDiaryStore: () => mockDiaryStore,
}))

// Mock confirm
global.confirm = vi.fn(() => true)

describe('DiaryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDiaryStore = {
      diaries: [],
      total: 0,
      page: 1,
      calendar: [],
      calendarYear: 2026,
      calendarMonth: 7,
      stats: null,
      isLoading: false,
      error: null,
      fetchDiaries: vi.fn(),
      fetchCalendar: vi.fn(),
      fetchStats: vi.fn(),
      deleteExistingDiary: vi.fn().mockResolvedValue(undefined),
    }
  })

  it('should render page title', () => {
    render(<DiaryPage />)
    expect(screen.getByText('穿搭日记')).toBeInTheDocument()
  })

  it('should render new diary button', () => {
    render(<DiaryPage />)
    expect(screen.getByText('+ 新日记')).toBeInTheDocument()
  })

  it('should navigate to new diary page on button click', () => {
    render(<DiaryPage />)
    fireEvent.click(screen.getByText('+ 新日记'))
    expect(mockPush).toHaveBeenCalledWith('/diary/new')
  })

  it('should render view tabs', () => {
    render(<DiaryPage />)
    expect(screen.getByText('列表')).toBeInTheDocument()
    expect(screen.getByText('日历')).toBeInTheDocument()
    expect(screen.getByText('统计')).toBeInTheDocument()
  })

  it('should show empty state when no diaries', () => {
    render(<DiaryPage />)
    expect(screen.getByText('还没有穿搭日记')).toBeInTheDocument()
  })

  it('should show loading state', () => {
    mockDiaryStore.isLoading = true
    render(<DiaryPage />)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('should render diary cards when diaries exist', () => {
    mockDiaryStore.diaries = [
      { id: 1, diary_date: '2026-07-01', mood: 'happy' },
      { id: 2, diary_date: '2026-07-02', mood: 'calm' },
    ]
    mockDiaryStore.total = 2
    render(<DiaryPage />)
    expect(screen.getByTestId('diary-card-1')).toBeInTheDocument()
    expect(screen.getByTestId('diary-card-2')).toBeInTheDocument()
  })

  it('should call fetchDiaries on mount', () => {
    render(<DiaryPage />)
    expect(mockDiaryStore.fetchDiaries).toHaveBeenCalled()
  })

  it('should switch to calendar view when tab is clicked', () => {
    render(<DiaryPage />)
    fireEvent.click(screen.getByText('日历'))
    expect(screen.getByTestId('diary-calendar')).toBeInTheDocument()
  })

  it('should switch to stats view when tab is clicked', () => {
    render(<DiaryPage />)
    fireEvent.click(screen.getByText('统计'))
    expect(screen.getByTestId('diary-stats')).toBeInTheDocument()
  })

  it('should render mood filter buttons', () => {
    render(<DiaryPage />)
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('😊开心')).toBeInTheDocument()
  })

  it('should show error message', () => {
    mockDiaryStore.error = '加载失败'
    render(<DiaryPage />)
    expect(screen.getByText('加载失败')).toBeInTheDocument()
  })

  it('should navigate to diary detail on card click', () => {
    mockDiaryStore.diaries = [{ id: 1, diary_date: '2026-07-01', mood: 'happy' }]
    mockDiaryStore.total = 1
    render(<DiaryPage />)
    fireEvent.click(screen.getByText('view'))
    expect(mockPush).toHaveBeenCalledWith('/diary/1')
  })

  it('should delete diary when delete is confirmed', async () => {
    mockDiaryStore.diaries = [{ id: 1, diary_date: '2026-07-01', mood: 'happy' }]
    mockDiaryStore.total = 1
    render(<DiaryPage />)
    fireEvent.click(screen.getByText('delete'))
    expect(global.confirm).toHaveBeenCalled()
    await waitFor(() => {
      expect(mockDiaryStore.deleteExistingDiary).toHaveBeenCalledWith(1)
    })
  })

  it('should show load more button when more diaries exist', () => {
    mockDiaryStore.diaries = [{ id: 1, diary_date: '2026-07-01', mood: 'happy' }]
    mockDiaryStore.total = 5
    render(<DiaryPage />)
    expect(screen.getByText(/加载更多/)).toBeInTheDocument()
  })
})
