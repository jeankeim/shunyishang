import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FortuneRadar } from '../FortuneRadar'
import type { FortuneScores } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock recharts
vi.mock('recharts', () => ({
  RadarChart: ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  Radar: () => <div data-testid="radar" />,
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: () => <div data-testid="polar-angle-axis" />,
  PolarRadiusAxis: () => <div data-testid="polar-radius-axis" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
}))

const mockScores: FortuneScores = {
  career: 90,
  wealth: 70,
  love: 80,
  health: 85,
  study: 75,
}

describe('FortuneRadar', () => {
  it('should render the radar chart title', () => {
    render(<FortuneRadar scores={mockScores} />)
    expect(screen.getByText('五维度运势雷达')).toBeInTheDocument()
  })

  it('should render chart components', () => {
    render(<FortuneRadar scores={mockScores} />)
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument()
    expect(screen.getByTestId('radar')).toBeInTheDocument()
    expect(screen.getByTestId('polar-grid')).toBeInTheDocument()
    expect(screen.getByTestId('polar-angle-axis')).toBeInTheDocument()
    expect(screen.getByTestId('polar-radius-axis')).toBeInTheDocument()
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('should use default size of 240', () => {
    render(<FortuneRadar scores={mockScores} />)
    const container = screen.getByTestId('responsive-container').parentElement
    expect(container?.style.height).toBe('240px')
  })

  it('should use custom size when provided', () => {
    render(<FortuneRadar scores={mockScores} size={300} />)
    const container = screen.getByTestId('responsive-container').parentElement
    expect(container?.style.height).toBe('300px')
  })

  it('should handle zero scores', () => {
    const zeroScores: FortuneScores = {
      career: 0,
      wealth: 0,
      love: 0,
      health: 0,
      study: 0,
    }
    render(<FortuneRadar scores={zeroScores} />)
    expect(screen.getByText('五维度运势雷达')).toBeInTheDocument()
  })
})
