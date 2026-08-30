import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { IdleItem, IdleItemsResponse } from '@/lib/api'
import { declutterWardrobeItem, getIdleItems } from '@/lib/api'
import { WARDROBE_ACTIVE_CHANGED } from '@/lib/wardrobe-display'
import { toast } from '@/components/ui'
import { IdleItemsCard } from '../IdleItemsCard'

vi.mock('@/lib/api', () => ({
  getIdleItems: vi.fn(),
  declutterWardrobeItem: vi.fn(),
  undoDeclutterWardrobeItem: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))
// 保留真实 ConfirmDialog，只把 toast 换成 spy
vi.mock('@/components/ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui')>()
  return { ...actual, toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }
})

function makeItem(overrides: Partial<IdleItem> = {}): IdleItem {
  return {
    id: 1,
    name: '白色衬衫',
    category: '上装',
    primary_element: '金',
    wear_count: 1,
    days_since_worn: 420,
    days_owned: 800,
    donation_suggestion: '白衬衫状态不错，可以捐给社区旧衣回收点',
    ...overrides,
  }
}

function makeResponse(items: IdleItem[]): IdleItemsResponse {
  return { idle_items: items, total_count: items.length, message: '有 1 件衣物超过一年没穿了' }
}

describe('IdleItemsCard', () => {
  beforeEach(() => {
    vi.mocked(getIdleItems).mockReset()
    vi.mocked(declutterWardrobeItem).mockReset()
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it('渲染闲置列表与三态小键', async () => {
    vi.mocked(getIdleItems).mockResolvedValue(makeResponse([makeItem()]))
    render(<IdleItemsCard />)

    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())
    expect(screen.getByText('1 件')).toBeInTheDocument()
    expect(screen.getByText('420 天前')).toBeInTheDocument()
    // 捐 / 卖 / 丢 三个小键，无障碍标签带衣物名
    expect(screen.getByRole('button', { name: '让它找新主人：白色衬衫' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '挂出去转让：白色衬衫' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '正式告别：白色衬衫' })).toBeInTheDocument()
  })

  it('点击行展开公益建议文案', async () => {
    vi.mocked(getIdleItems).mockResolvedValue(makeResponse([makeItem()]))
    render(<IdleItemsCard />)
    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())

    expect(screen.queryByText(/社区旧衣回收点/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('穿着 1 次'))
    await waitFor(() => expect(screen.getByText(/社区旧衣回收点/)).toBeInTheDocument())
  })

  it('点「捐」先出二次确认，未确认不调接口', async () => {
    vi.mocked(getIdleItems).mockResolvedValue(makeResponse([makeItem()]))
    render(<IdleItemsCard />)
    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '让它找新主人：白色衬衫' }))
    await waitFor(() => expect(screen.getByText('把「白色衬衫」让它找新主人？')).toBeInTheDocument())
    expect(declutterWardrobeItem).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '取消' }))
    await waitFor(() => expect(screen.queryByText('把「白色衬衫」让它找新主人？')).not.toBeInTheDocument())
    expect(declutterWardrobeItem).not.toHaveBeenCalled()
  })

  it('确认后写入三态、行消失并广播活跃衣橱变更', async () => {
    const listener = vi.fn()
    document.addEventListener(WARDROBE_ACTIVE_CHANGED, listener)
    vi.mocked(getIdleItems).mockResolvedValue(
      makeResponse([makeItem(), makeItem({ id: 2, name: '黑色西装裤', category: '下装' })]),
    )
    vi.mocked(declutterWardrobeItem).mockResolvedValue({
      item_id: 1,
      action: 'donate',
      action_label: '捐赠',
      is_active: false,
      updated: false,
    })
    render(<IdleItemsCard />)
    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '让它找新主人：白色衬衫' }))
    await waitFor(() => expect(screen.getByRole('button', { name: '确认捐赠' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '确认捐赠' }))

    await waitFor(() => expect(declutterWardrobeItem).toHaveBeenCalledWith(1, 'donate'))
    await waitFor(() => expect(screen.queryByText('白色衬衫')).not.toBeInTheDocument())
    expect(screen.getByText('黑色西装裤')).toBeInTheDocument()
    expect(screen.getByText('1 件')).toBeInTheDocument()
    expect(listener).toHaveBeenCalledTimes(1)
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('捐赠'))
    document.removeEventListener(WARDROBE_ACTIVE_CHANGED, listener)
  })

  it('接口失败时提示错误且行保留', async () => {
    vi.mocked(getIdleItems).mockResolvedValue(makeResponse([makeItem()]))
    vi.mocked(declutterWardrobeItem).mockRejectedValue(new Error('这件衣物不属于当前用户'))
    render(<IdleItemsCard />)
    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: '挂出去转让：白色衬衫' }))
    await waitFor(() => expect(screen.getByRole('button', { name: '确认转让' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '确认转让' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('这件衣物不属于当前用户'))
    expect(screen.getByText('白色衬衫')).toBeInTheDocument()
    expect(screen.getByText('1 件')).toBeInTheDocument()
  })

  it('无闲置衣物时不占位', async () => {
    vi.mocked(getIdleItems).mockResolvedValue(makeResponse([]))
    const { container } = render(<IdleItemsCard />)
    await waitFor(() => expect(getIdleItems).toHaveBeenCalled())
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('接口失败时静默不渲染', async () => {
    vi.mocked(getIdleItems).mockResolvedValue(null)
    const { container } = render(<IdleItemsCard />)
    await waitFor(() => expect(getIdleItems).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
