import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { WardrobeItem } from '@/lib/api'
import { AddWardrobeModal } from '../AddWardrobeModal'

const mocks = vi.hoisted(() => ({
  addItem: vi.fn(),
  updateItem: vi.fn(),
  fetchTaggingPreview: vi.fn(),
  clearTaggingPreview: vi.fn(),
}))

vi.mock('@/store/wardrobe', () => ({
  useWardrobeStore: () => ({
    addItem: mocks.addItem,
    updateItem: mocks.updateItem,
    taggingPreview: null,
    isTaggingLoading: false,
    fetchTaggingPreview: mocks.fetchTaggingPreview,
    clearTaggingPreview: mocks.clearTaggingPreview,
  }),
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({ isAuthenticated: true }),
}))

const STORY_PLACEHOLDER = /毕业旅行买的/

function makeItem(overrides: Partial<WardrobeItem> = {}): WardrobeItem {
  return {
    id: 3,
    user_id: 1,
    name: '白衬衫',
    category: '上装',
    primary_element: '金',
    is_custom: true,
    is_active: true,
    wear_count: 1,
    is_favorite: false,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AddWardrobeModal 它的故事', () => {
  it('编辑时回填已有故事，长度上限与后端一致', () => {
    render(
      <AddWardrobeModal isOpen onClose={vi.fn()} onSuccess={vi.fn()} editItem={makeItem({ notes: '毕业旅行买的' })} />,
    )
    const box = screen.getByPlaceholderText(STORY_PLACEHOLDER)
    expect(box).toHaveValue('毕业旅行买的')
    expect(box).toHaveAttribute('maxlength', '100')

    fireEvent.change(box, { target: { value: '毕业后那次旅行买的' } })
    expect(screen.getByText('9/100')).toBeInTheDocument()
  })

  it('保存编辑时把故事一并提交', async () => {
    const onSuccess = vi.fn()
    render(
      <AddWardrobeModal isOpen onClose={vi.fn()} onSuccess={onSuccess} editItem={makeItem()} />,
    )
    fireEvent.change(screen.getByPlaceholderText(STORY_PLACEHOLDER), { target: { value: '面试穿的那件' } })
    fireEvent.click(screen.getByText('确认添加'))

    await waitFor(() =>
      expect(mocks.updateItem).toHaveBeenCalledWith(3, expect.objectContaining({ notes: '面试穿的那件' })),
    )
    expect(onSuccess).toHaveBeenCalled()
  })

  it('第一步只要描述与图片，故事留到确认步骤再写', () => {
    render(<AddWardrobeModal isOpen onClose={vi.fn()} onSuccess={vi.fn()} />)
    expect(screen.queryByPlaceholderText(STORY_PLACEHOLDER)).not.toBeInTheDocument()
  })
})
