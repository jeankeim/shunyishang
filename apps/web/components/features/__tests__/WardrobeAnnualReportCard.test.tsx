import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { WardrobeReport, WardrobeReportStats } from '@/lib/api'
import { generateWardrobeReport, getWardrobeReport, postPosterBase64 } from '@/lib/api'
import { toast } from '@/components/ui'
import { WardrobeAnnualReportCard } from '../WardrobeAnnualReportCard'

vi.mock('@/lib/api', () => ({
  getWardrobeReport: vi.fn(),
  generateWardrobeReport: vi.fn(),
  postPosterBase64: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))
vi.mock('@/components/ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui')>()
  return { ...actual, toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }
})
vi.mock('@/store/user', () => ({
  useUserStore: (sel: (s: { user: unknown }) => unknown) => sel({ user: { nickname: '小明' } }),
}))
// 灯箱内部有图片预加载与遮罩动画，这里只关心「海报出来了没有」
vi.mock('../ImageLightbox', () => ({
  ImageLightbox: ({ alt }: { alt?: string }) => <div data-testid="lightbox">{alt}</div>,
}))

const CURRENT_YEAR = new Date().getFullYear()

function makeStats(overrides: Partial<WardrobeReportStats> = {}): WardrobeReportStats {
  return {
    year: CURRENT_YEAR,
    total_items: 42,
    new_this_year: 6,
    ever_worn_items: 30,
    favorite_items: 3,
    diary_count: 18,
    worn_this_year: 15,
    top_occasion: '通勤',
    top_worn_item: {
      id: 11, name: '白色衬衫', category: '上装', image_url: '/img/shirt.png', primary_element: '金', wear_times: 9,
    },
    idle_item: {
      id: 12, name: '黑色风衣', category: '外套', image_url: null, primary_element: '水',
      wear_count: 0, last_worn: `${CURRENT_YEAR}-01-05`, idle_days: 230,
    },
    lucky_element: '木',
    lucky_element_times: 21,
    element_weights: [
      { element: '木', times: 21 },
      { element: '金', times: 9 },
    ],
    element_source: 'diary',
    monthly_elements: [
      { month: 1, label: '1月', elements: { 木: 5, 金: 2 }, dominant: '木' },
      { month: 2, label: '2月', elements: { 火: 3 }, dominant: '火' },
    ],
    declutter: { total_processed: 3, max_idle_days: 400, summary: `${CURRENT_YEAR} 年你处理了 3 件衣物` },
    is_empty: false,
    ...overrides,
  }
}

function makeReport(overrides: Partial<WardrobeReport> = {}): WardrobeReport {
  const stats = makeStats()
  return {
    id: 1,
    year: CURRENT_YEAR,
    title: `${CURRENT_YEAR} 年的穿搭节奏`,
    content: {
      year: CURRENT_YEAR,
      stats,
      narrative: {
        title: `${CURRENT_YEAR} 年的穿搭节奏`,
        overall: `${CURRENT_YEAR} 年你留下了 18 套穿搭记录，最顺手的是木行。`,
        top_item: '「白色衬衫」今年出现了 9 次。',
        idle_item: '「黑色风衣」已经 230 天没被动过。',
        element_story: '本命色落在木（21 次穿着）。',
        trend: '月度元素变迁：1月偏木、2月偏火。',
        advice: '明年先把已有单品轮换起来。',
      },
    },
    summary: `${CURRENT_YEAR} 年你留下了 18 套穿搭记录`,
    status: 'ready',
    generated: true,
    updated_at: `${CURRENT_YEAR}-12-31T10:00:00+08:00`,
    ...overrides,
  }
}

function mockPayload(report: WardrobeReport | null, used = 1) {
  vi.mocked(getWardrobeReport).mockResolvedValue({
    year: CURRENT_YEAR,
    report,
    quota: { year: CURRENT_YEAR, used, limit: 3, remaining: 3 - used },
  })
}

describe('WardrobeAnnualReportCard', () => {
  beforeEach(() => {
    vi.mocked(getWardrobeReport).mockReset()
    vi.mocked(generateWardrobeReport).mockReset()
    vi.mocked(postPosterBase64).mockReset()
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it('未生成时给出年度入口与剩余额度', async () => {
    mockPayload(null, 1)
    render(<WardrobeAnnualReportCard />)

    expect(await screen.findByText('衣橱 · 年度报告')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: new RegExp(`生成 ${CURRENT_YEAR} 年衣橱报告`) })).toBeEnabled()
    expect(screen.getByText('免费 · 本年还可生成 2 / 3 次')).toBeInTheDocument()
    expect(screen.getByText(`${CURRENT_YEAR} 年的衣橱故事`)).toBeInTheDocument()
  })

  it('额度用完时按钮禁用并说明原因', async () => {
    mockPayload(null, 3)
    render(<WardrobeAnnualReportCard />)

    const btn = await screen.findByRole('button', { name: new RegExp(`生成 ${CURRENT_YEAR} 年衣橱报告`) })
    expect(btn).toBeDisabled()
    expect(screen.getByText(`本年 3 次机会已用完`)).toBeInTheDocument()

    fireEvent.click(btn)
    expect(generateWardrobeReport).not.toHaveBeenCalled()
  })

  it('pending 行显示生成中并禁用入口', async () => {
    mockPayload(makeReport({ status: 'pending', generated: false, summary: null }), 1)
    render(<WardrobeAnnualReportCard />)

    const btn = await screen.findByRole('button', { name: '正在盘点你的衣橱…' })
    expect(btn).toBeDisabled()
    expect(screen.queryByText('查看完整报告')).not.toBeInTheDocument()
  })

  it('已生成时展示标题与摘要，点开可见分段正文与事实数字', async () => {
    mockPayload(makeReport())
    render(<WardrobeAnnualReportCard />)

    expect(await screen.findByText(`${CURRENT_YEAR} 年的穿搭节奏`)).toBeInTheDocument()
    expect(screen.getByText(`${CURRENT_YEAR} 年你留下了 18 套穿搭记录`)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '查看完整报告' }))

    expect(await screen.findByText('年度总览')).toBeInTheDocument()
    expect(screen.getByText('穿得最多的一件')).toBeInTheDocument()
    expect(screen.getByText('给明年的一条建议')).toBeInTheDocument()
    expect(screen.getByText('「白色衬衫」今年出现了 9 次。')).toBeInTheDocument()
    // 事实网格与断舍离、月度元素都来自 stats
    expect(screen.getByText('42 件')).toBeInTheDocument()
    expect(screen.getByText(`${CURRENT_YEAR} 年新增`)).toBeInTheDocument()
    expect(screen.getByText('已 230 天没被动过')).toBeInTheDocument()
    expect(screen.getByText(`${CURRENT_YEAR} 年你处理了 3 件衣物`)).toBeInTheDocument()
    expect(screen.getByText('每个月偏哪一行')).toBeInTheDocument()
    expect(screen.getAllByText('木').length).toBeGreaterThan(0)
    // 只渲染有 dominant 的月份
    expect(screen.getByText('2月')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '关闭报告' }))
    await waitFor(() => expect(screen.queryByText('年度总览')).not.toBeInTheDocument())
  })

  it('生成年月切换会带年份重新取数', async () => {
    mockPayload(null)
    render(<WardrobeAnnualReportCard />)

    await screen.findByRole('button', { name: new RegExp(`生成 ${CURRENT_YEAR} 年衣橱报告`) })
    expect(getWardrobeReport).toHaveBeenLastCalledWith(CURRENT_YEAR)

    fireEvent.click(screen.getByLabelText('上一年'))
    await waitFor(() => expect(getWardrobeReport).toHaveBeenLastCalledWith(CURRENT_YEAR - 1))

    // 切到下一年回到当年后禁用，不会生成未来年份的报告
    const next = screen.getByLabelText('下一年')
    expect(next).toBeEnabled()
    fireEvent.click(next)
    await waitFor(() => expect(getWardrobeReport).toHaveBeenLastCalledWith(CURRENT_YEAR))
    await waitFor(() => expect(screen.getByLabelText('下一年')).toBeDisabled())
  })

  it('生成成功后回查服务端状态并提示', async () => {
    mockPayload(null, 1)
    vi.mocked(generateWardrobeReport).mockResolvedValue({
      id: 1, year: CURRENT_YEAR, title: '新报告', content: makeReport().content, summary: '摘要', status: 'ready',
    })
    render(<WardrobeAnnualReportCard />)

    fireEvent.click(await screen.findByRole('button', { name: new RegExp(`生成 ${CURRENT_YEAR} 年衣橱报告`) }))
    await waitFor(() => expect(generateWardrobeReport).toHaveBeenCalledWith(CURRENT_YEAR))

    expect(toast.success).toHaveBeenCalledWith(`${CURRENT_YEAR} 年衣橱报告已生成`)
    // 初次加载 + 生成后回查
    await waitFor(() => expect(getWardrobeReport).toHaveBeenCalledTimes(2))
    expect(getWardrobeReport).toHaveBeenLastCalledWith(CURRENT_YEAR)
  })

  it('生成失败提示后端原因并回查状态', async () => {
    mockPayload(null, 1)
    vi.mocked(generateWardrobeReport).mockRejectedValue(new Error('已达本年生成上限'))
    render(<WardrobeAnnualReportCard />)

    fireEvent.click(await screen.findByRole('button', { name: new RegExp(`生成 ${CURRENT_YEAR} 年衣橱报告`) }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('已达本年生成上限'))
    // 失败也可能是轮询超时，仍回查一次服务端状态
    await waitFor(() => expect(getWardrobeReport).toHaveBeenCalledTimes(2))
  })

  it('分享海报按本命色取五行主题并复用通用海报接口', async () => {
    mockPayload(makeReport())
    vi.mocked(postPosterBase64).mockResolvedValue({ image: 'BASE64', filename: 'x.png', size: 100 })
    render(<WardrobeAnnualReportCard />)

    fireEvent.click(await screen.findByRole('button', { name: '生成分享海报' }))

    await waitFor(() => expect(postPosterBase64).toHaveBeenCalledTimes(1))
    expect(postPosterBase64).toHaveBeenCalledWith(expect.objectContaining({
      layout: 'wuxing',
      title: `${CURRENT_YEAR} 年的穿搭节奏`,
      theme: 'wood',
      xiyong_elements: ['木'],
      quote: `${CURRENT_YEAR} 年你留下了 18 套穿搭记录，最顺手的是木行。`,
      username: '小明',
    }))
    // 两个主角单品进海报，图片用原始相对路径交给服务端回落
    const { items } = vi.mocked(postPosterBase64).mock.calls[0][0]
    expect(items).toHaveLength(2)
    expect(items[0]).toMatchObject({ name: '白色衬衫', image_url: '/img/shirt.png' })
    expect(items[1]).toMatchObject({ name: '黑色风衣', image_url: null })

    expect(await screen.findByTestId('lightbox')).toHaveTextContent(`${CURRENT_YEAR} 年衣橱年度报告海报`)
  })

  it('海报生成失败时提示且不开灯箱', async () => {
    mockPayload(makeReport())
    vi.mocked(postPosterBase64).mockResolvedValue(null)
    render(<WardrobeAnnualReportCard />)

    fireEvent.click(await screen.findByRole('button', { name: '生成分享海报' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('海报生成失败，请稍后重试'))
    expect(screen.queryByTestId('lightbox')).not.toBeInTheDocument()
  })

  it('接口不可用时整卡不渲染', async () => {
    vi.mocked(getWardrobeReport).mockResolvedValue(null)
    const { container } = render(<WardrobeAnnualReportCard />)

    await waitFor(() => expect(container).toBeEmptyDOMElement())
    expect(screen.queryByText('衣橱 · 年度报告')).not.toBeInTheDocument()
  })
})
