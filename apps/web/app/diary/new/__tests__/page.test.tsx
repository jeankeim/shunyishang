import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import NewDiaryPage from '../page'

const mockPush = vi.fn()
const mockBack = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  useSearchParams: () => ({
    get: vi.fn((key: string) => (key === 'date' ? '2026-07-02' : null)),
  }),
}))

vi.mock('framer-motion', () => ({
  motion: {
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
}))

vi.mock('@/components/features/diary/DiaryForm', () => ({
  DiaryForm: ({ initialData, onSubmit, onCancel }: any) => (
    <div data-testid="diary-form">
      <span data-testid="initial-date">{initialData?.diary_date || 'none'}</span>
      <button onClick={() => onSubmit({ diary_date: '2026-07-02', mood: 'happy' })}>submit</button>
      <button onClick={onCancel}>cancel</button>
    </div>
  ),
}))

let mockDiaryStore: any = {}

vi.mock('@/store/diary', () => ({
  useDiaryStore: () => mockDiaryStore,
}))

describe('NewDiaryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDiaryStore = {
      createNewDiary: vi.fn().mockResolvedValue({ id: 123 }),
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    }
  })

  it('should render page title', () => {
    render(<NewDiaryPage />)
    expect(screen.getByText('新建日记')).toBeInTheDocument()
  })

  it('should render subtitle', () => {
    render(<NewDiaryPage />)
    expect(screen.getByText('记录今日穿搭与心情')).toBeInTheDocument()
  })

  it('should render DiaryForm', () => {
    render(<NewDiaryPage />)
    expect(screen.getByTestId('diary-form')).toBeInTheDocument()
  })

  it('should pass date param to DiaryForm', () => {
    render(<NewDiaryPage />)
    expect(screen.getByTestId('initial-date').textContent).toBe('2026-07-02')
  })

  it('should call createNewDiary and navigate on submit', async () => {
    render(<NewDiaryPage />)
    fireEvent.click(screen.getByText('submit'))
    await waitFor(() => {
      expect(mockDiaryStore.createNewDiary).toHaveBeenCalledWith({ diary_date: '2026-07-02', mood: 'happy' })
      expect(mockPush).toHaveBeenCalledWith('/diary/123')
    })
  })

  it('should go back on cancel', () => {
    render(<NewDiaryPage />)
    fireEvent.click(screen.getByText('cancel'))
    expect(mockBack).toHaveBeenCalled()
  })

  it('should go back on back button click', () => {
    render(<NewDiaryPage />)
    const backBtn = screen.getByRole('button', { name: '' })
    fireEvent.click(backBtn)
    expect(mockBack).toHaveBeenCalled()
  })

  it('should show error message when error exists', () => {
    mockDiaryStore.error = '创建失败'
    render(<NewDiaryPage />)
    expect(screen.getByText('创建失败')).toBeInTheDocument()
  })

  it('should call clearError on unmount', () => {
    const { unmount } = render(<NewDiaryPage />)
    unmount()
    expect(mockDiaryStore.clearError).toHaveBeenCalled()
  })
})
