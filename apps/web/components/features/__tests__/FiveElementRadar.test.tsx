import { describe, it, expect, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { FiveElementRadar } from '../FiveElementRadar'

// Mock recharts to avoid rendering issues in jsdom
vi.mock('recharts', () => ({
  Radar: () => null,
  RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  Legend: () => null,
}))

describe('FiveElementRadar', () => {
  it('should render chart after mount', async () => {
    await act(async () => {
      render(<FiveElementRadar />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.queryByText('加载中...')).not.toBeInTheDocument()
    expect(screen.getByText('五行能量分布')).toBeInTheDocument()
  })

  it('should render xiyongShen label when provided', async () => {
    await act(async () => {
      render(<FiveElementRadar xiyongShen={['木', '水']} />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.getByText(/喜用神/)).toBeInTheDocument()
    expect(screen.getByText(/木、水/)).toBeInTheDocument()
  })

  it('should not render xiyongShen label when empty', async () => {
    await act(async () => {
      render(<FiveElementRadar />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.queryByText(/喜用神/)).not.toBeInTheDocument()
  })

  it('should render all five element labels after mount', async () => {
    await act(async () => {
      render(<FiveElementRadar />)
      await new Promise((r) => setTimeout(r, 0))
    })

    // The element labels are rendered in the grid below the chart
    const elements = screen.getAllByText(/^(金|木|水|火|土)$/)
    expect(elements.length).toBeGreaterThanOrEqual(5)
  })

  it('should render pillars section when pillars prop is provided', async () => {
    const pillars = {
      year: '甲子',
      month: '乙丑',
      day: '丙寅',
      hour: '丁卯',
    }
    await act(async () => {
      render(<FiveElementRadar pillars={pillars} />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.getByText('八字排盘')).toBeInTheDocument()
    expect(screen.getByText('年柱')).toBeInTheDocument()
    expect(screen.getByText('月柱')).toBeInTheDocument()
    expect(screen.getByText('日柱')).toBeInTheDocument()
    expect(screen.getByText('时柱')).toBeInTheDocument()
    expect(screen.getByText('甲子')).toBeInTheDocument()
  })

  it('should render day master when provided', async () => {
    const pillars = { year: '甲子', month: '乙丑', day: '丙寅', hour: '丁卯' }
    await act(async () => {
      render(<FiveElementRadar pillars={pillars} dayMaster="丙" />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.getByText('日元:')).toBeInTheDocument()
    expect(screen.getByText('丙')).toBeInTheDocument()
  })

  it('should render eight chars when provided', async () => {
    const pillars = { year: '甲子', month: '乙丑', day: '丙寅', hour: '丁卯' }
    const eightChars = ['甲', '子', '乙', '丑', '丙', '寅', '丁', '卯']
    await act(async () => {
      render(<FiveElementRadar pillars={pillars} eightChars={eightChars} />)
      await new Promise((r) => setTimeout(r, 0))
    })

    // All eight chars should be rendered
    for (const char of eightChars) {
      expect(screen.getAllByText(char).length).toBeGreaterThan(0)
    }
  })

  it('should show element counts when data is available', async () => {
    const currentData = { '金': 20, '木': 40, '水': 30, '火': 10, '土': 20 }
    const elementCounts = { '金': 1, '木': 3, '水': 2, '火': 1, '土': 1 }
    await act(async () => {
      render(<FiveElementRadar currentData={currentData} elementCounts={elementCounts} />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.getByText('3个')).toBeInTheDocument()
    expect(screen.getByText('2个')).toBeInTheDocument()
  })

  it('should apply custom className', async () => {
    await act(async () => {
      render(<FiveElementRadar className="custom-class" />)
      await new Promise((r) => setTimeout(r, 0))
    })

    const container = screen.getByText('五行能量分布').closest('div')
    expect(container?.className).toContain('custom-class')
  })

  it('should not render pillars section when pillars prop is not provided', async () => {
    await act(async () => {
      render(<FiveElementRadar />)
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(screen.queryByText('八字排盘')).not.toBeInTheDocument()
  })
})
