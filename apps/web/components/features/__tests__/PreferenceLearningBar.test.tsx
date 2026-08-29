import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { PreferenceSummary } from '@/lib/api'
import { PreferenceLearningBar } from '../PreferenceLearningBar'

vi.mock('@/lib/api', () => ({
  getPreferenceSummary: vi.fn(),
}))
vi.mock('../PreferenceRadar', () => ({
  PreferenceRadar: () => <div data-testid="radar" />,
}))

import { getPreferenceSummary } from '@/lib/api'

function makeSummary(overrides: Partial<PreferenceSummary> = {}): PreferenceSummary {
  return {
    dimensions: [
      { key: 'color', label: '颜色', icon: '🎨', score: 0.8, top_items: [], has_data: true },
      { key: 'element', label: '五行', icon: '☯️', score: 0.5, top_items: [], has_data: true },
      { key: 'category', label: '品类', icon: '👔', score: 0, top_items: [], has_data: false },
      { key: 'style', label: '风格', icon: '✨', score: 0, top_items: [], has_data: false },
      { key: 'material', label: '材质', icon: '🧵', score: 0, top_items: [], has_data: false },
      { key: 'thickness', label: '厚度', icon: '🌡️', score: 0, top_items: [], has_data: false },
    ],
    overall_score: 0.22,
    feedback_count: 14,
    learning_signals: {
      diary_count_30d: 6,
      wear_checkin_count_30d: 18,
      top_changed_dimensions: [{ key: 'color', label: '颜色', delta: 8 }],
      window_days: 30,
    },
    ...overrides,
  }
}

describe('PreferenceLearningBar', () => {
  beforeEach(() => {
    vi.mocked(getPreferenceSummary).mockReset()
  })

  it('一行说清记录套数、已学维度与学习深度', async () => {
    vi.mocked(getPreferenceSummary).mockResolvedValue(makeSummary())
    render(<PreferenceLearningBar />)

    // 数字用 <span> 强调，按整行文本断言（getByText 只看直接文本子节点）
    const trigger = await screen.findByRole('button', { expanded: false })
    expect(trigger.textContent).toContain('近 30 天你记了 6 套穿搭')
    expect(trigger.textContent).toContain('推荐已按 2 个维度更懂你')
    expect(trigger.textContent).toContain('学习深度 22%')
    expect(screen.getByText(/颜色/)).toHaveTextContent('颜色 +8')
  })

  it('点击展开复用偏好画像雷达', async () => {
    vi.mocked(getPreferenceSummary).mockResolvedValue(makeSummary())
    render(<PreferenceLearningBar />)

    expect(screen.queryByTestId('radar')).not.toBeInTheDocument()
    const trigger = await screen.findByRole('button', { expanded: false })
    fireEvent.click(trigger)
    await waitFor(() => expect(screen.getByTestId('radar')).toBeInTheDocument())
  })

  it('零记录且零反馈时整条不渲染', async () => {
    vi.mocked(getPreferenceSummary).mockResolvedValue(makeSummary({
      overall_score: 0,
      feedback_count: 0,
      dimensions: [],
      learning_signals: {
        diary_count_30d: 0,
        wear_checkin_count_30d: 0,
        top_changed_dimensions: [],
        window_days: 30,
      },
    }))
    const { container } = render(<PreferenceLearningBar />)
    await waitFor(() => expect(getPreferenceSummary).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
