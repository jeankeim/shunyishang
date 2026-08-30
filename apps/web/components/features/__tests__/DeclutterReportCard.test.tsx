import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import type { DeclutterReport } from '@/lib/api'
import { getDeclutterReport, undoDeclutterWardrobeItem } from '@/lib/api'
import { WARDROBE_ACTIVE_CHANGED } from '@/lib/wardrobe-display'
import { toast } from '@/components/ui'
import { DeclutterReportCard } from '../DeclutterReportCard'

vi.mock('@/lib/api', () => ({
  getDeclutterReport: vi.fn(),
  undoDeclutterWardrobeItem: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))
vi.mock('@/components/ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui')>()
  return { ...actual, toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }
})

const CURRENT_YEAR = new Date().getFullYear()

function makeReport(overrides: Partial<DeclutterReport> = {}): DeclutterReport {
  return {
    year: CURRENT_YEAR,
    total_processed: 3,
    by_action: [
      { action: 'donate', label: '捐赠', count: 2 },
      { action: 'sell', label: '转让', count: 1 },
      { action: 'discard', label: '舍弃', count: 0 },
    ],
    released_count: 3,
    max_idle_days: 400,
    element_breakdown: [
      { element: '木', count: 2 },
      { element: '火', count: 1 },
    ],
    avoided_purchase_count: 3,
    processed_items: [
      {
        id: 11,
        name: '白色衬衫',
        category: '上装',
        primary_element: '金',
        action: 'donate',
        action_label: '捐赠',
        acted_date: `${CURRENT_YEAR}-06-01`,
        idle_days_at_action: 400,
      },
      {
        id: 12,
        name: '黑色西装裤',
        category: '下装',
        action: 'sell',
        action_label: '转让',
        acted_date: `${CURRENT_YEAR}-07-02`,
        idle_days_at_action: 120,
      },
    ],
    summary: `${CURRENT_YEAR} 年你处理了 3 件衣物，以捐赠为主，最久的一件已闲置 400 天，相当于少买 3 件`,
    ...overrides,
  }
}

describe('DeclutterReportCard', () => {
  beforeEach(() => {
    vi.mocked(getDeclutterReport).mockReset()
    vi.mocked(undoDeclutterWardrobeItem).mockReset()
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it('战报摘要与三个关键数字始终可见，清单默认折叠', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(makeReport())
    render(<DeclutterReportCard />)

    await waitFor(() => expect(screen.getByText('断舍离 · 年度战报')).toBeInTheDocument())
    expect(screen.getByText(`给衣橱减了 ${3} 件负担`)).toBeInTheDocument()
    expect(screen.getByText(/以捐赠为主/)).toBeInTheDocument()
    // 「让出的位置」与「相当于少买」同为 3 件
    expect(screen.getAllByText('3 件')).toHaveLength(2)
    expect(screen.getByText('400 天')).toBeInTheDocument()
    expect(screen.getByText('衣橱让出的位置')).toBeInTheDocument()
    expect(screen.getByText('最久的一件闲置')).toBeInTheDocument()
    expect(screen.getByText('相当于少买')).toBeInTheDocument()
    // 折叠态不渲染清单与分布
    expect(screen.queryByText('白色衬衫')).not.toBeInTheDocument()
    expect(screen.queryByText('处理方式')).not.toBeInTheDocument()
  })

  it('展开后看到三态分布、五行构成与可撤销清单', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(makeReport())
    render(<DeclutterReportCard />)
    await waitFor(() => expect(screen.getByText('断舍离 · 年度战报')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /展开/ }))
    await waitFor(() => expect(screen.getByText('处理方式')).toBeInTheDocument())
    expect(screen.getByText(`${CURRENT_YEAR} 年处理清单`)).toBeInTheDocument()
    expect(screen.getByText('白色衬衫')).toBeInTheDocument()
    expect(screen.getByText(/当时已闲置 400 天/)).toBeInTheDocument()
    expect(screen.getByText('放下的多是哪一行')).toBeInTheDocument()
    // 计划要求：战报卡需说明处理可撤销
    expect(screen.getByText(/点「撤销」即可放回衣橱/)).toBeInTheDocument()
  })

  it('撤销：调接口、刷新战报并广播活跃衣橱变更', async () => {
    const listener = vi.fn()
    document.addEventListener(WARDROBE_ACTIVE_CHANGED, listener)
    vi.mocked(getDeclutterReport).mockResolvedValue(makeReport())
    vi.mocked(undoDeclutterWardrobeItem).mockResolvedValue()
    render(<DeclutterReportCard />)
    await waitFor(() => expect(screen.getByText('断舍离 · 年度战报')).toBeInTheDocument())
    expect(getDeclutterReport).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: /展开/ }))
    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())
    fireEvent.click(screen.getAllByRole('button', { name: '撤销' })[0])

    await waitFor(() => expect(undoDeclutterWardrobeItem).toHaveBeenCalledWith(11))
    expect(listener).toHaveBeenCalledTimes(1)
    // 刷新由广播驱动（本卡自监听），因此只多发一次请求
    await waitFor(() => expect(getDeclutterReport).toHaveBeenCalledTimes(2))
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('已回到衣橱'))
    document.removeEventListener(WARDROBE_ACTIVE_CHANGED, listener)
  })

  it('撤销失败时提示错误', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(makeReport())
    vi.mocked(undoDeclutterWardrobeItem).mockRejectedValue(new Error('这件衣物没有被标记处理'))
    render(<DeclutterReportCard />)
    await waitFor(() => expect(screen.getByText('断舍离 · 年度战报')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /展开/ }))
    await waitFor(() => expect(screen.getByText('白色衬衫')).toBeInTheDocument())
    fireEvent.click(screen.getAllByRole('button', { name: '撤销' })[0])

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('这件衣物没有被标记处理'))
  })

  it('切换年份带参请求，当年时下一年禁用', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(makeReport({ year: CURRENT_YEAR - 1 }))
    render(<DeclutterReportCard />)
    await waitFor(() => expect(screen.getByText('断舍离 · 年度战报')).toBeInTheDocument())

    expect(screen.getByRole('button', { name: '下一年' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: '上一年' }))
    await waitFor(() => expect(getDeclutterReport).toHaveBeenCalledWith(CURRENT_YEAR - 1))
  })

  it('当年无处理记录时不占位', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(
      makeReport({
        total_processed: 0,
        by_action: [
          { action: 'donate', label: '捐赠', count: 0 },
          { action: 'sell', label: '转让', count: 0 },
          { action: 'discard', label: '舍弃', count: 0 },
        ],
        released_count: 0,
        max_idle_days: 0,
        element_breakdown: [],
        avoided_purchase_count: 0,
        processed_items: [],
      }),
    )
    const { container } = render(<DeclutterReportCard />)
    await waitFor(() => expect(getDeclutterReport).toHaveBeenCalled())
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('接口失败时静默不渲染', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(null)
    const { container } = render(<DeclutterReportCard />)
    await waitFor(() => expect(getDeclutterReport).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('收到闲置卡广播后重新拉取战报', async () => {
    vi.mocked(getDeclutterReport).mockResolvedValue(makeReport())
    render(<DeclutterReportCard />)
    await waitFor(() => expect(getDeclutterReport).toHaveBeenCalledTimes(1))

    // 广播来自其他组件，需包在 act 里（会触发本卡 setState）
    act(() => {
      document.dispatchEvent(new CustomEvent(WARDROBE_ACTIVE_CHANGED))
    })
    await waitFor(() => expect(getDeclutterReport).toHaveBeenCalledTimes(2))
  })
})
