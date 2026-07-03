import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiaryDetail } from '../DiaryDetail'
import type { OutfitDiary, DiaryOutfitItem } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
}))

const mockItem1: DiaryOutfitItem = {
  id: 1, diary_id: 1, item_source: 'wardrobe', name: '白色T恤', category: '上衣', primary_element: '金', image_url: 'http://example.com/1.jpg', created_at: '2026-01-15T00:00:00Z',
}
const mockItem2: DiaryOutfitItem = {
  id: 2, diary_id: 1, item_source: 'seed', name: '牛仔裤', category: '裤子', primary_element: '水', image_url: undefined, created_at: '2026-01-15T00:00:00Z',
}

const mockDiary: OutfitDiary = {
  id: 1,
  user_id: 1,
  diary_date: '2026-01-15',
  mood: 'happy',
  occasion: '上班',
  rating: 4,
  notes: '今天穿搭很满意',
  items: [mockItem1, mockItem2],
  ai_review: { score: 85, comment: '搭配协调', suggestions: ['可以加个配饰', '颜色更搭配'] },
  image_urls: [],
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

describe('DiaryDetail', () => {
  it('should render full date string', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('2026年1月15日')).toBeInTheDocument()
  })

  it('should render mood emoji', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('😊')).toBeInTheDocument()
  })

  it('should render occasion', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('上班')).toBeInTheDocument()
  })

  it('should render rating stars', () => {
    render(<DiaryDetail diary={mockDiary} />)
    const goldStars = screen.getAllByText('★').filter(s => s.className.includes('amber'))
    expect(goldStars).toHaveLength(4)
  })

  it('should render notes', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('今天穿搭很满意')).toBeInTheDocument()
  })

  it('should render items section with count', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText(/今日穿搭.*2件/)).toBeInTheDocument()
  })

  it('should render item names', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('白色T恤')).toBeInTheDocument()
    expect(screen.getByText('牛仔裤')).toBeInTheDocument()
  })

  it('should render AI review section', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('AI 穿搭点评')).toBeInTheDocument()
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('搭配协调')).toBeInTheDocument()
  })

  it('should render AI review suggestions', () => {
    render(<DiaryDetail diary={mockDiary} />)
    expect(screen.getByText('改进建议:')).toBeInTheDocument()
    expect(screen.getByText('可以加个配饰')).toBeInTheDocument()
    expect(screen.getByText('颜色更搭配')).toBeInTheDocument()
  })

  it('should render "重新点评" when ai_review has score', () => {
    const onTriggerReview = vi.fn()
    render(<DiaryDetail diary={mockDiary} onTriggerReview={onTriggerReview} />)
    expect(screen.getByText('重新点评')).toBeInTheDocument()
  })

  it('should render "生成点评" when ai_review has no score', () => {
    const diary = { ...mockDiary, ai_review: undefined }
    const onTriggerReview = vi.fn()
    render(<DiaryDetail diary={diary} onTriggerReview={onTriggerReview} />)
    expect(screen.getByText('生成点评')).toBeInTheDocument()
    expect(screen.getByText('暂无 AI 点评，点击上方按钮生成')).toBeInTheDocument()
  })

  it('should call onEdit when edit button is clicked', () => {
    const onEdit = vi.fn()
    render(<DiaryDetail diary={mockDiary} onEdit={onEdit} />)
    fireEvent.click(screen.getByText('编辑'))
    expect(onEdit).toHaveBeenCalled()
  })

  it('should call onDelete when delete button is clicked', () => {
    const onDelete = vi.fn()
    render(<DiaryDetail diary={mockDiary} onDelete={onDelete} />)
    fireEvent.click(screen.getByText('删除'))
    expect(onDelete).toHaveBeenCalled()
  })

  it('should call onBack when back button is clicked', () => {
    const onBack = vi.fn()
    render(<DiaryDetail diary={mockDiary} onBack={onBack} />)
    const backBtn = screen.getByRole('button', { name: '' })
    // Find the back button (first button in the header area)
    const allButtons = screen.getAllByRole('button')
    fireEvent.click(allButtons[0])
    expect(onBack).toHaveBeenCalled()
  })

  it('should call onTriggerReview when review button is clicked', () => {
    const onTriggerReview = vi.fn()
    render(<DiaryDetail diary={mockDiary} onTriggerReview={onTriggerReview} />)
    fireEvent.click(screen.getByText('重新点评'))
    expect(onTriggerReview).toHaveBeenCalled()
  })

  it('should render default emoji when mood is null', () => {
    const diary = { ...mockDiary, mood: undefined } as OutfitDiary
    render(<DiaryDetail diary={diary} />)
    expect(screen.getByText('📝')).toBeInTheDocument()
  })

  it('should not render items section when items is empty', () => {
    const diary = { ...mockDiary, items: [] }
    render(<DiaryDetail diary={diary} />)
    expect(screen.queryByText(/今日穿搭/)).not.toBeInTheDocument()
  })

  it('should not render notes when absent', () => {
    const diary = { ...mockDiary, notes: undefined }
    render(<DiaryDetail diary={diary} />)
    expect(screen.queryByText('今天穿搭很满意')).not.toBeInTheDocument()
  })

  it('should render item element badge', () => {
    render(<DiaryDetail diary={mockDiary} />)
    // "水" appears in both placeholder and badge for item without image
    expect(screen.getAllByText('水').length).toBeGreaterThan(0)
    expect(screen.getByText('金')).toBeInTheDocument()
  })
})
