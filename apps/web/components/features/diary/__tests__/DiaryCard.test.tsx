import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DiaryCard } from '../DiaryCard'
import type { OutfitDiary, DiaryOutfitItem } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
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
  ai_review: { score: 85, comment: '搭配协调', suggestions: ['可以加个配饰'] },
  image_urls: [],
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

describe('DiaryCard', () => {
  it('should render date string', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText('1月15日')).toBeInTheDocument()
  })

  it('should render mood emoji', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText('😊')).toBeInTheDocument()
  })

  it('should render occasion', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText('上班')).toBeInTheDocument()
  })

  it('should render rating stars', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText('★★★★☆')).toBeInTheDocument()
  })

  it('should render notes', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText('今天穿搭很满意')).toBeInTheDocument()
  })

  it('should render AI review score', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText(/AI 85分/)).toBeInTheDocument()
  })

  it('should render AI review comment', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByText('搭配协调')).toBeInTheDocument()
  })

  it('should render item thumbnails', () => {
    render(<DiaryCard diary={mockDiary} />)
    expect(screen.getByAltText('白色T恤')).toBeInTheDocument()
    expect(screen.getByText('水')).toBeInTheDocument()
  })

  it('should call onClick when card is clicked', () => {
    const onClick = vi.fn()
    render(<DiaryCard diary={mockDiary} onClick={onClick} />)
    fireEvent.click(screen.getByText('1月15日'))
    expect(onClick).toHaveBeenCalled()
  })

  it('should call onDelete and stop propagation when delete is clicked', () => {
    const onDelete = vi.fn()
    const onClick = vi.fn()
    render(<DiaryCard diary={mockDiary} onClick={onClick} onDelete={onDelete} />)
    const deleteBtn = screen.getByLabelText('删除日记')
    fireEvent.click(deleteBtn)
    expect(onDelete).toHaveBeenCalled()
    expect(onClick).not.toHaveBeenCalled()
  })

  it('should render default emoji when mood is null', () => {
    const diary = { ...mockDiary, mood: undefined } as OutfitDiary
    render(<DiaryCard diary={diary} />)
    expect(screen.getByText('📝')).toBeInTheDocument()
  })

  it('should render default emoji for unknown mood', () => {
    const diary = { ...mockDiary, mood: 'unknown_mood' } as unknown as OutfitDiary
    render(<DiaryCard diary={diary} />)
    expect(screen.getByText('😐')).toBeInTheDocument()
  })

  it('should show +N when items exceed 4', () => {
    const diary = {
      ...mockDiary,
      items: [
        ...mockDiary.items,
        { id: 3, diary_id: 1, item_source: 'seed' as const, name: 'item3', category: 'cat', primary_element: '木', image_url: undefined, created_at: '2026-01-15T00:00:00Z' },
        { id: 4, diary_id: 1, item_source: 'seed' as const, name: 'item4', category: 'cat', primary_element: '火', image_url: undefined, created_at: '2026-01-15T00:00:00Z' },
        { id: 5, diary_id: 1, item_source: 'seed' as const, name: 'item5', category: 'cat', primary_element: '土', image_url: undefined, created_at: '2026-01-15T00:00:00Z' },
      ],
    }
    render(<DiaryCard diary={diary} />)
    expect(screen.getByText('+1')).toBeInTheDocument()
  })
})
