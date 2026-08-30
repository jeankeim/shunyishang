import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { WardrobeItem } from '@/lib/api'
import { WardrobeItemViewer } from '../WardrobeItemViewer'

// 放大层用 createPortal 渲染到 body，测试里直接渲染到容器即可
vi.mock('react-dom', async () => {
  const actual = await vi.importActual<typeof import('react-dom')>('react-dom')
  return { ...actual, createPortal: (node: React.ReactNode) => node }
})

const mocks = vi.hoisted(() => ({
  updateWardrobeItem: vi.fn(),
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

vi.mock('@/lib/api', () => ({
  updateWardrobeItem: mocks.updateWardrobeItem,
  wearItem: vi.fn(),
  unwearItem: vi.fn(),
}))

vi.mock('@/components/ui/Toast', () => ({ toast: mocks.toast }))

function makeItem(overrides: Partial<WardrobeItem> = {}): WardrobeItem {
  return {
    id: 7,
    user_id: 1,
    name: '白衬衫',
    category: '上装',
    primary_element: '金',
    is_custom: true,
    is_active: true,
    wear_count: 3,
    is_favorite: false,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    ...overrides,
  }
}

function renderItem(item: Partial<WardrobeItem> = {}, onNotesSaved?: (id: number, notes: string | null) => void) {
  const onClose = vi.fn()
  render(<WardrobeItemViewer item={makeItem(item)} onClose={onClose} onNotesSaved={onNotesSaved} />)
  return { onClose }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('WardrobeItemViewer 它的故事', () => {
  it('展示已写好的故事，点击回填到编辑框', () => {
    renderItem({ notes: '毕业旅行买的' })
    fireEvent.click(screen.getByText('毕业旅行买的'))
    const box = screen.getByLabelText('编辑它的故事')
    expect(box).toHaveValue('毕业旅行买的')
  })

  it('没写过时给出可点的占位引导，长度上限与后端一致', () => {
    renderItem()
    fireEvent.click(screen.getByText(/还没写点什么/))
    const box = screen.getByLabelText('编辑它的故事')
    expect(box).toHaveValue('')
    expect(box).toHaveAttribute('maxlength', '100')
  })

  it('失焦即保存，成功后就地展示新故事并通知上层', async () => {
    const onNotesSaved = vi.fn()
    renderItem({ notes: undefined }, onNotesSaved)
    mocks.updateWardrobeItem.mockResolvedValue(makeItem({ notes: '妈妈送的第一件' }))

    fireEvent.click(screen.getByText(/还没写点什么/))
    const box = screen.getByLabelText('编辑它的故事')
    fireEvent.change(box, { target: { value: '妈妈送的第一件' } })
    fireEvent.blur(box)

    await waitFor(() => expect(mocks.updateWardrobeItem).toHaveBeenCalledWith(7, { notes: '妈妈送的第一件' }))
    expect(screen.getByText('妈妈送的第一件')).toBeInTheDocument()
    expect(mocks.toast.success).toHaveBeenCalledWith('故事已记下')
    expect(onNotesSaved).toHaveBeenCalledWith(7, '妈妈送的第一件')
  })

  it('删空内容保存后回到占位引导', async () => {
    renderItem({ notes: '旧故事' })
    mocks.updateWardrobeItem.mockResolvedValue(makeItem({ notes: undefined }))

    fireEvent.click(screen.getByText('旧故事'))
    const box = screen.getByLabelText('编辑它的故事')
    fireEvent.change(box, { target: { value: '' } })
    fireEvent.blur(box)

    // 清空走同一个 PATCH，传空串由后端落 NULL
    await waitFor(() => expect(mocks.updateWardrobeItem).toHaveBeenCalledWith(7, { notes: '' }))
    expect(screen.getByText(/还没写点什么/)).toBeInTheDocument()
    expect(mocks.toast.success).toHaveBeenCalledWith('故事已清空')
  })

  it('内容没动时不打无谓的 PATCH', () => {
    renderItem({ notes: '懒得改' })
    fireEvent.click(screen.getByText('懒得改'))
    fireEvent.blur(screen.getByLabelText('编辑它的故事'))
    expect(mocks.updateWardrobeItem).not.toHaveBeenCalled()
    expect(mocks.toast.success).not.toHaveBeenCalled()
  })

  it('保存失败保留草稿，再次点击可接着写', async () => {
    renderItem({ notes: '旧故事' })
    mocks.updateWardrobeItem.mockRejectedValue(new Error('网络异常，保存失败'))

    fireEvent.click(screen.getByText('旧故事'))
    const box = screen.getByLabelText('编辑它的故事')
    fireEvent.change(box, { target: { value: '写到一半的故事' } })
    fireEvent.blur(box)

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalledWith('网络异常，保存失败'))
    // 展示的仍是已保存的旧故事，草稿没丢
    expect(screen.getByText('旧故事')).toBeInTheDocument()
    fireEvent.click(screen.getByText('旧故事'))
    expect(screen.getByLabelText('编辑它的故事')).toHaveValue('写到一半的故事')
  })

  it('编辑中按 Esc 只退回展示态，不关掉放大层', () => {
    const { onClose } = renderItem({ notes: '毕业旅行买的' })
    fireEvent.click(screen.getByText('毕业旅行买的'))
    expect(screen.getByLabelText('编辑它的故事')).toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByLabelText('编辑它的故事')).not.toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
  })
})
