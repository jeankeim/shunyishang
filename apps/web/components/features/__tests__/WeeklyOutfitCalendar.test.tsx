import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { WeekOutfit, WeekOutfitDay, DailyOutfit } from '@/lib/api'
import { getWeekOutfit, postWeekPoster } from '@/lib/api'
import { hasTodayDiary, logOutfitAsDiary, loggedFlagKey, todayISO } from '@/lib/outfit-diary'
import { WeeklyOutfitCalendar } from '../WeeklyOutfitCalendar'

vi.mock('@/lib/api', () => ({
  getWeekOutfit: vi.fn(),
  postWeekPoster: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))
vi.mock('@/lib/outfit-diary', async () => {
  const actual = await vi.importActual<typeof import('@/lib/outfit-diary')>('@/lib/outfit-diary')
  return {
    ...actual,
    hasTodayDiary: vi.fn(),
    logOutfitAsDiary: vi.fn(),
  }
})
vi.mock('@/components/ui/Toast', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))
vi.mock('@/store/user', () => ({
  useUserStore: (sel: (s: { user: unknown }) => unknown) => sel({ user: { nickname: '小明' } }),
}))
// 单品详情弹窗内部依赖较多，一周日历只需验证「点击缩略图会打开它」
vi.mock('../ItemDetailModal', () => ({
  ItemDetailModal: ({ item }: { item: { name: string } }) => (
    <div data-testid="item-detail-modal">{item.name}</div>
  ),
}))

/** 生成相对今天的日期（ISO），用于构造「今天列 / 未来列」 */
function dateOffset(days: number): string {
  const base = new Date(`${todayISO()}T12:00:00+08:00`)
  base.setDate(base.getDate() + days)
  return base.toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' })
}

function makeDay(offset: number, overrides: Partial<WeekOutfitDay> = {}): WeekOutfitDay {
  return {
    date: dateOffset(offset),
    weekday: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][offset % 7],
    temp_min: 12,
    temp_max: 22,
    weather: '晴',
    lucky_elements: ['木'],
    lucky_colors: ['绿色'],
    outfit_items: [
      { id: 1, name: '棉麻白衬衫', category: '上装', primary_element: '金', image_url: '/img/1.png', match_score: 88, wear_count: 0, is_favorite: false },
      { id: 2, name: '直筒牛仔裤', category: '下装', primary_element: '木', image_url: '/img/2.png', match_score: 80, wear_count: 3, is_favorite: true },
    ],
    completeness: { has_top: true, has_bottom_or_dress: true, has_shoes: false, has_accessory: false, missing: ['鞋履'] },
    match_score: 86,
    reasoning: '今天适合以浅色系的金、水单品稳住气场',
    ...overrides,
  }
}

function makeWeek(count = 7, startOffset = 0): WeekOutfit {
  return {
    city: '杭州',
    start_date: dateOffset(startOffset),
    days: Array.from({ length: count }, (_, i) => makeDay(i + startOffset)),
    is_empty: false,
  }
}

/** 单日「换一套」返回体（与 daily 接口同构） */
function makeDaily(date: string): DailyOutfit {
  return {
    date,
    outfit_items: [
      { id: 99, name: '替换后的外套', category: '外套', primary_element: '水', match_score: 70, wear_count: 0, is_favorite: false },
    ],
    reasoning: '换一批的结果',
    weather_summary: { city: '杭州', temperature: 20, weather: '多云', element: '水' },
    fortune_summary: { lucky_elements: ['水'], lucky_colors: ['黑色'], overall_score: 72 },
    style_tip: '试试深色系',
    match_score: 70,
    completeness: { has_top: true, has_bottom_or_dress: false, has_shoes: false, has_accessory: false, missing: ['下装'] },
  }
}

/** 整周 + 单日双模式的 getWeekOutfit mock */
function mockWeekAndDaily() {
  vi.mocked(getWeekOutfit).mockImplementation(async (_city?: string, date?: string) =>
    date ? makeDaily(date) : makeWeek()
  )
}

describe('WeeklyOutfitCalendar', () => {
  beforeEach(() => {
    vi.mocked(getWeekOutfit).mockReset()
    vi.mocked(postWeekPoster).mockReset()
    vi.mocked(hasTodayDiary).mockReset().mockResolvedValue(false)
    vi.mocked(logOutfitAsDiary).mockReset()
    localStorage.clear()
  })

  it('未登录时不渲染', () => {
    const { container } = render(<WeeklyOutfitCalendar isAuthenticated={false} />)
    expect(container).toBeEmptyDOMElement()
    expect(getWeekOutfit).not.toHaveBeenCalled()
  })

  it('加载完成后渲染 7 列与匹配分', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    await waitFor(() => expect(screen.getByText('一周穿搭')).toBeInTheDocument())
    expect(getWeekOutfit).toHaveBeenCalledWith('杭州')
    expect(screen.getAllByText('86分')).toHaveLength(7)
    expect(screen.getByText('今天')).toBeInTheDocument()
    expect(screen.getByText('杭州 · 按每天天气与运势预先排好')).toBeInTheDocument()
  })

  it('衣橱为空时整块静默隐藏', async () => {
    const week = makeWeek()
    week.days = []
    vi.mocked(getWeekOutfit).mockResolvedValue(week)
    const { container } = render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    await waitFor(() => expect(getWeekOutfit).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('接口异常时不崩且不展示列', async () => {
    vi.mocked(getWeekOutfit).mockRejectedValue(new Error('network'))
    const { container } = render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    await waitFor(() => expect(getWeekOutfit).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('点击某一列展开当日整套与缺口占位', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    const column = await screen.findByLabelText(new RegExp(dateOffset(2)))
    fireEvent.click(column)
    await waitFor(() => expect(screen.getByText('棉麻白衬衫')).toBeInTheDocument())
    expect(screen.getByText('直筒牛仔裤')).toBeInTheDocument()
    // completeness.missing → 「衣橱缺」占位
    expect(screen.getByText(/鞋履/)).toBeInTheDocument()
  })

  it('再次点击同一列收起', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    const column = await screen.findByLabelText(new RegExp(dateOffset(2)))
    fireEvent.click(column)
    await waitFor(() => expect(screen.getByText('棉麻白衬衫')).toBeInTheDocument())
    fireEvent.click(column)
    await waitFor(() => expect(screen.queryByText('棉麻白衬衫')).not.toBeInTheDocument())
  })

  it('「今天就穿它」只出现在今天那一列', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    const todayColumn = await screen.findByLabelText(new RegExp(` ${dateOffset(0)} 的穿搭`))
    fireEvent.click(todayColumn)
    await waitFor(() => expect(screen.getByText('今天就穿它')).toBeInTheDocument())

    fireEvent.click(todayColumn) // 收起
    const tomorrowColumn = await screen.findByLabelText(new RegExp(dateOffset(1)))
    fireEvent.click(tomorrowColumn)
    await waitFor(() => expect(screen.getByText('换一套')).toBeInTheDocument())
    expect(screen.queryByText('今天就穿它')).not.toBeInTheDocument()
  })

  it('今天就穿它走共享日记链路并写入本地回显标记', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    vi.mocked(logOutfitAsDiary).mockResolvedValue({ ok: true })
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    fireEvent.click(await screen.findByLabelText(new RegExp(` ${dateOffset(0)} 的穿搭`)))
    fireEvent.click(await screen.findByText('今天就穿它'))
    await waitFor(() =>
      expect(logOutfitAsDiary).toHaveBeenCalledWith([
        { id: 1, category: '上装' },
        { id: 2, category: '下装' },
      ])
    )
    expect(localStorage.getItem(loggedFlagKey())).toBe('1')
  })

  it('服务端已有今日日记时按钮显示已记入态', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    vi.mocked(hasTodayDiary).mockResolvedValue(true)
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    fireEvent.click(await screen.findByLabelText(new RegExp(` ${dateOffset(0)} 的穿搭`)))
    await waitFor(() => expect(screen.getByText(/今日已记入 · 去日记/)).toBeInTheDocument())
  })

  it('单日换一套按批次请求并只覆盖当天', async () => {
    mockWeekAndDaily()
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    fireEvent.click(await screen.findByLabelText(new RegExp(dateOffset(2))))
    await waitFor(() => expect(screen.getByText('棉麻白衬衫')).toBeInTheDocument())

    fireEvent.click(screen.getByText('换一套'))
    await waitFor(() => expect(getWeekOutfit).toHaveBeenLastCalledWith('杭州', dateOffset(2), 1))
    await waitFor(() => expect(screen.getByText('替换后的外套')).toBeInTheDocument())
    expect(screen.queryByText('棉麻白衬衫')).not.toBeInTheDocument()
  })

  it('换一套批次在 0-2 之间循环', async () => {
    mockWeekAndDaily()
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    fireEvent.click(await screen.findByLabelText(new RegExp(dateOffset(2))))
    const swap = () => screen.getByText('换一套')
    fireEvent.click(swap())
    await waitFor(() => expect(getWeekOutfit).toHaveBeenLastCalledWith('杭州', dateOffset(2), 1))
    fireEvent.click(swap())
    await waitFor(() => expect(getWeekOutfit).toHaveBeenLastCalledWith('杭州', dateOffset(2), 2))
    fireEvent.click(swap())
    await waitFor(() => expect(getWeekOutfit).toHaveBeenLastCalledWith('杭州', dateOffset(2), 0))
  })

  it('生成海报按所见即所得传当日覆盖结果', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    vi.mocked(postWeekPoster).mockResolvedValue({ image: 'ZmFrZQ==', filename: '一周穿搭海报.png', size: 8 })
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    await screen.findByText('一周穿搭')
    fireEvent.click(screen.getByText('生成一周穿搭海报'))
    await waitFor(() => expect(postWeekPoster).toHaveBeenCalled())
    const payload = vi.mocked(postWeekPoster).mock.calls[0][0]
    expect(payload.days).toHaveLength(7)
    expect(payload.days[0].items).toHaveLength(2)
    expect(payload.days[0].items[0]).toEqual({
      name: '棉麻白衬衫',
      category: '上装',
      image_url: '/img/1.png',
      primary_element: '金',
    })
    expect(payload.theme).toBe('wood')
    expect(payload.username).toBe('小明')
    expect(payload.city).toBe('杭州')
    await waitFor(() => expect(screen.getByAltText('一周穿搭海报')).toHaveAttribute('src', 'data:image/png;base64,ZmFrZQ=='))
  })

  it('海报接口返回空时提示失败且不预览', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    vi.mocked(postWeekPoster).mockResolvedValue(null)
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    await screen.findByText('一周穿搭')
    fireEvent.click(screen.getByText('生成一周穿搭海报'))
    await waitFor(() => expect(screen.queryByAltText('一周穿搭海报')).not.toBeInTheDocument())
    expect(screen.getByText('生成一周穿搭海报')).toBeInTheDocument()
  })

  it('点击缩略图打开单品详情弹窗', async () => {
    vi.mocked(getWeekOutfit).mockResolvedValue(makeWeek())
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    fireEvent.click(await screen.findByLabelText(new RegExp(dateOffset(2))))
    await waitFor(() => expect(screen.getByText('棉麻白衬衫')).toBeInTheDocument())
    fireEvent.click(screen.getByText('棉麻白衬衫'))
    await waitFor(() => expect(screen.getByTestId('item-detail-modal')).toHaveTextContent('棉麻白衬衫'))
  })

  it('首次加载中展示 7 个骨架列', () => {
    vi.mocked(getWeekOutfit).mockReturnValue(new Promise(() => {}))
    render(<WeeklyOutfitCalendar isAuthenticated city="杭州" />)
    expect(screen.getByText('一周穿搭')).toBeInTheDocument()
    expect(document.querySelectorAll('.animate-pulse')).toHaveLength(7)
  })
})
