import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { RitualItem, SolarTermRitual } from '@/lib/api'
import { getSolarTermRitual, wearItem } from '@/lib/api'
import { toast } from '@/components/ui'
import { SolarTermRitualCard } from '../SolarTermRitualCard'

vi.mock('@/lib/api', () => ({
  getSolarTermRitual: vi.fn(),
  wearItem: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url?: string | null) => url || undefined,
}))
vi.mock('@/components/ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/ui')>()
  return { ...actual, toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }
})

function makeItem(
  id: number,
  name: string,
  overrides: Partial<RitualItem> = {},
): RitualItem {
  return {
    id,
    name,
    category: '上装',
    image_url: null,
    primary_element: '木',
    thickness_level: '适中',
    seasons: ['春'],
    wear_count: 2,
    last_worn: '2025-11-01',
    idle_days: 100,
    ...overrides,
  }
}

function makeRitual(overrides: Partial<SolarTermRitual> = {}): SolarTermRitual {
  return {
    solar_term: {
      name: '立春', date: '2026-02-04', element: '木', description: '春回大地',
      outfit_hint: '轻薄外套', season: '春', days_until: 3,
    },
    current_term: { name: '大寒', date: '2026-01-20', season: '冬' },
    next_season: '春',
    expected_thickness: ['适中', '轻薄'],
    is_season_boundary: true,
    store_away: {
      items: [
        makeItem(1, '羊毛大衣', { category: '外套', thickness_level: '厚重', seasons: ['冬'], wear_count: 9, last_worn: '2026-01-18', idle_days: 15 }),
        makeItem(2, '加绒卫衣', { category: '上装', thickness_level: '厚重', seasons: ['冬'], wear_count: 4, last_worn: '2026-01-10', idle_days: 20 }),
      ],
      total: 12,
      reason: '立春后转春季，这些单品用不到春季，厚度也不搭',
    },
    take_out: {
      items: [makeItem(3, '白衬衫', { idle_days: 126, last_worn: '2025-10-01' })],
      total: 3,
      reason: '这些能穿到春季的单品已经 90 天以上没上身',
    },
    yi_ji: {
      advice: '立春将至，春回大地。节气属木，恰合您的喜用神，宜多穿绿色系。',
      gap_elements: [{ element: '木', headline: '木气缺口最大' }],
    },
    has_action: true,
    ...overrides,
  }
}

describe('SolarTermRitualCard', () => {
  beforeEach(() => {
    vi.mocked(getSolarTermRitual).mockReset()
    vi.mocked(wearItem).mockReset()
    vi.mocked(toast.success).mockReset()
    vi.mocked(toast.error).mockReset()
  })

  it('接口不可用时整卡不渲染', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(null)
    const { container } = render(<SolarTermRitualCard />)
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('定位不到节气时不渲染（没有参照的清单没有意义）', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual({ solar_term: null }))
    const { container } = render(<SolarTermRitualCard />)
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('跨季时抬头写「换季开柜」，并给出当前节气走向与天数', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual())
    render(<SolarTermRitualCard />)
    expect(await screen.findByText('换季开柜 · 迎接立春')).toBeInTheDocument()
    expect(screen.getByText('大寒 → 立春 · 3 天后交节')).toBeInTheDocument()
    expect(screen.getByText('衣橱 · 开柜仪式')).toBeInTheDocument()
  })

  it('季中检查用另一种口径，交节当天写「今天交节」', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual({
      is_season_boundary: false,
      solar_term: { name: '雨水', date: '2026-02-18', element: '水', description: '雨水增多', outfit_hint: '风衣', season: '春', days_until: 0 },
      current_term: { name: '立春', date: '2026-02-04', season: '春' },
    }))
    render(<SolarTermRitualCard />)
    expect(await screen.findByText('雨水前的衣橱检查')).toBeInTheDocument()
    expect(screen.getByText('立春 → 雨水 · 今天交节')).toBeInTheDocument()
  })

  it('宜忌一行 + 下一季厚度参考 + 缺口元素胶囊', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual())
    render(<SolarTermRitualCard />)
    expect(await screen.findByText(/立春将至/)).toBeInTheDocument()
    expect(screen.getByText(/厚度参考/)).toHaveTextContent('适中 / 轻薄')
    expect(screen.getByTitle('木气缺口最大')).toHaveTextContent('衣橱缺木')
  })

  it('缺口胶囊点击后按元素筛选', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual())
    const onApplyFilter = vi.fn()
    render(<SolarTermRitualCard onApplyFilter={onApplyFilter} />)
    fireEvent.click(await screen.findByText('衣橱缺木'))
    expect(onApplyFilter).toHaveBeenCalledWith({ element: '木' })
  })

  it('该收按出现最多的厚度筛选，该拿按下一季筛选', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual({
      store_away: {
        items: [
          makeItem(1, '羊毛大衣', { thickness_level: '厚重', seasons: ['冬'] }),
          makeItem(2, '加绒卫衣', { thickness_level: '厚重', seasons: ['冬'] }),
          makeItem(3, '薄风衣', { thickness_level: '加厚', seasons: ['秋', '冬'] }),
        ],
        total: 3,
        reason: '收起来',
      },
    }))
    const onApplyFilter = vi.fn()
    render(<SolarTermRitualCard onApplyFilter={onApplyFilter} />)
    fireEvent.click(await screen.findByText('只看厚重的'))
    expect(onApplyFilter).toHaveBeenCalledWith({ thickness: '厚重' })
    fireEvent.click(screen.getByText('只看春季'))
    expect(onApplyFilter).toHaveBeenLastCalledWith({ season: '春' })
  })

  it('该拿行内打卡：成功后提示并从清单摘掉，同时通知衣橱刷新', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual())
    vi.mocked(wearItem).mockResolvedValue({ diary_id: 88, already_logged: false, wear_count: 3, last_worn_date: '2026-02-01' })
    const activeChanged = vi.fn()
    document.addEventListener('wardrobe-active-changed', activeChanged)

    render(<SolarTermRitualCard />)
    fireEvent.click(await screen.findByRole('button', { name: '穿白衬衫打卡' }))
    await waitFor(() => expect(wearItem).toHaveBeenCalledWith(3))
    expect(toast.success).toHaveBeenCalledWith('「白衬衫」已记进今天的穿搭日记')
    expect(screen.queryByText('白衬衫')).not.toBeInTheDocument()
    expect(activeChanged).toHaveBeenCalledTimes(1)
    document.removeEventListener('wardrobe-active-changed', activeChanged)
  })

  it('今天已打过卡时提示口径不同，但同样从当日清单划掉', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual())
    vi.mocked(wearItem).mockResolvedValue({ diary_id: 88, already_logged: true, wear_count: 3, last_worn_date: '2026-02-01' })
    render(<SolarTermRitualCard />)
    fireEvent.click(await screen.findByRole('button', { name: '穿白衬衫打卡' }))
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('「白衬衫」今天已经打过卡了'))
    expect(screen.queryByText('白衬衫')).not.toBeInTheDocument()
  })

  it('打卡失败时保留条目并透出后端原因', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual())
    vi.mocked(wearItem).mockRejectedValue(new Error('今日打卡次数已用完'))
    render(<SolarTermRitualCard />)
    fireEvent.click(await screen.findByRole('button', { name: '穿白衬衫打卡' }))
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('今日打卡次数已用完'))
    expect(screen.getByText('白衬衫')).toBeInTheDocument()
  })

  it('从没穿过的新品写「入橱后还没穿过」而不是编一个上次日期', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual({
      take_out: {
        items: [makeItem(7, '棉麻衬衫', { last_worn: null, idle_days: 40, wear_count: 0 })],
        total: 1,
        reason: '拿出来穿一次',
      },
    }))
    render(<SolarTermRitualCard />)
    expect(await screen.findByText('入橱后还没穿过')).toBeInTheDocument()
    expect(screen.queryByText('40 天没上身')).not.toBeInTheDocument()
  })

  it('两张清单都空时给安心文案，且不给筛选入口', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual({
      store_away: { items: [], total: 0, reason: '没有要收的' },
      take_out: { items: [], total: 0, reason: '没有要拿的' },
      has_action: false,
    }))
    render(<SolarTermRitualCard />)
    expect(await screen.findByText('没有明显过季的单品，柜子保持原样就好。')).toBeInTheDocument()
    expect(screen.getByText('下一季能穿的单品最近都有上身。')).toBeInTheDocument()
    expect(screen.queryByText(/^只看/)).not.toBeInTheDocument()
  })

  it('超过 3 件收起，点「看更多」后全部展开', async () => {
    vi.mocked(getSolarTermRitual).mockResolvedValue(makeRitual({
      store_away: {
        items: Array.from({ length: 5 }, (_, i) => makeItem(20 + i, `大衣${i + 1}`)),
        total: 5,
        reason: '收起来',
      },
    }))
    render(<SolarTermRitualCard />)
    await screen.findByText('大衣1')
    expect(screen.queryByText('大衣5')).not.toBeInTheDocument()
    // 收起态按总数提示"还有更多"
    expect(screen.getByText('共 5 件')).toBeInTheDocument()
    fireEvent.click(screen.getByText(/看更多（该收 5 件 · 该拿 3 件）/))
    expect(await screen.findByText('大衣5')).toBeInTheDocument()
    expect(screen.getByText('5 件')).toBeInTheDocument()
    fireEvent.click(screen.getByText('收起'))
    expect(screen.queryByText('大衣5')).not.toBeInTheDocument()
  })
})
