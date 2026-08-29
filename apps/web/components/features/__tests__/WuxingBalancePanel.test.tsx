import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { ElementBalance } from '@/lib/api'
import { WuxingBalancePanel } from '../WuxingBalancePanel'
import { requestChatInputAutofill } from '@/lib/chatAutofill'

vi.mock('@/lib/api', () => ({
  getElementBalance: vi.fn(),
}))
vi.mock('@/lib/chatAutofill', () => ({
  requestChatInputAutofill: vi.fn(),
}))
vi.mock('@/lib/image', () => ({
  getImageUrl: (url: string) => url,
}))

import { getElementBalance } from '@/lib/api'

function makeBalance(overrides: Partial<ElementBalance> = {}): ElementBalance {
  return {
    elements: [
      { element: '金', count: 3, actual_pct: 17.2, target_pct: 10, gap_pct: -7.2, status: 'surplus' },
      { element: '木', count: 2, actual_pct: 12.9, target_pct: 40, gap_pct: 27.1, status: 'deficient' },
      { element: '水', count: 6, actual_pct: 37.6, target_pct: 25, gap_pct: -12.6, status: 'surplus' },
      { element: '火', count: 1, actual_pct: 5.4, target_pct: 11.7, gap_pct: 6.3, status: 'deficient' },
      { element: '土', count: 4, actual_pct: 26.9, target_pct: 10, gap_pct: -16.9, status: 'balanced' },
    ],
    lucky_elements: ['木', '水'],
    avoid_elements: ['土'],
    advice: [
      {
        element: '木',
        headline: '木属性单品偏少（参考缺口 27%）· 可补 1-2 件鞋履',
        gap_pct: 27.1,
        want: { category: '鞋履', colors: ['绿色', '青色'], seasons: ['夏'] },
        items: [
          { item_code: 'ITEM_038', name: '荧光绿跑鞋', category: '鞋履', color: '荧光绿', image_url: 'http://img/38.png', element_role: 'primary' },
        ],
      },
    ],
    total_items: 16,
    is_empty: false,
    temperature: 30,
    season: '夏',
    ...overrides,
  }
}

describe('WuxingBalancePanel', () => {
  beforeEach(() => {
    vi.mocked(getElementBalance).mockReset()
    vi.mocked(requestChatInputAutofill).mockReset()
  })

  it('渲染五行占比与缺口小标', async () => {
    vi.mocked(getElementBalance).mockResolvedValue(makeBalance())
    render(<WuxingBalancePanel />)

    await waitFor(() => expect(screen.getByText('五行穿搭平衡')).toBeInTheDocument())
    expect(screen.getByText('共 16 件')).toBeInTheDocument()
    expect(screen.getByText(/^喜用/)).toHaveTextContent('喜用 木·水')
    // 缺口与超出小标
    expect(screen.getByText('缺 27%')).toBeInTheDocument()
    expect(screen.getByText('多 7%')).toBeInTheDocument()
    // 目标刻度线（每行一条）
    expect(screen.getAllByTitle(/目标/)).toHaveLength(5)
    // 忌神行标记
    expect(screen.getByTitle('该五行为命理忌神，占比越低越理想')).toBeInTheDocument()
    // 参考口径说明，不作吉凶断言
    expect(screen.getByText(/传统文化参考口径/)).toBeInTheDocument()
  })

  it('补运建议点击「看看这类」带上元素与品类语境跳推荐', async () => {
    vi.mocked(getElementBalance).mockResolvedValue(makeBalance())
    render(<WuxingBalancePanel />)

    const button = await screen.findByRole('button', { name: '看看这类' })
    fireEvent.click(button)
    expect(requestChatInputAutofill).toHaveBeenCalledWith('推荐一件木属性的鞋履')
  })

  it('空衣橱不占位', async () => {
    vi.mocked(getElementBalance).mockResolvedValue(makeBalance({ is_empty: true, elements: [], total_items: 0 }))
    const { container } = render(<WuxingBalancePanel />)
    await waitFor(() => expect(getElementBalance).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('接口失败时静默不渲染', async () => {
    vi.mocked(getElementBalance).mockResolvedValue(null)
    const { container } = render(<WuxingBalancePanel />)
    await waitFor(() => expect(getElementBalance).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
