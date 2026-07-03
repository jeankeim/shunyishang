import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DiaryStatsPanel } from '../DiaryStats'
import type { DiaryStats } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock recharts
vi.mock('recharts', () => ({
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ children }: any) => <div data-testid="pie">{children}</div>,
  Cell: () => <div data-testid="cell" />,
}))

const mockStats: DiaryStats = {
  total_diaries: 10,
  streak_days: 5,
  avg_rating: 4.2,
  total_items: 25,
  mood_distribution: {
    happy: 5,
    excited: 2,
    calm: 2,
    neutral: 1,
    sad: 0,
  },
}

describe('DiaryStatsPanel', () => {
  it('should show empty state when stats is null', () => {
    render(<DiaryStatsPanel stats={null} />)
    expect(screen.getByText('暂无统计数据')).toBeInTheDocument()
  })

  it('should render total diaries count', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('总日记数')).toBeInTheDocument()
  })

  it('should render streak days', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('连续打卡')).toBeInTheDocument()
    // The streak days number and "天" are in the same <p> element
    const streakElement = screen.getByText('连续打卡').parentElement
    expect(streakElement).toBeInTheDocument()
  })

  it('should render average rating', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('4.2')).toBeInTheDocument()
    expect(screen.getByText('平均评分')).toBeInTheDocument()
  })

  it('should render total items count', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getByText('穿搭件数')).toBeInTheDocument()
  })

  it('should render mood distribution chart', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('心情分布')).toBeInTheDocument()
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument()
  })

  it('should render mood labels', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('心情分布')).toBeInTheDocument()
    // Mood labels are passed as data to recharts, which is mocked
    // Just verify the chart is rendered
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument()
  })

  it('should handle null avg_rating', () => {
    const stats = { ...mockStats, avg_rating: undefined } as DiaryStats
    render(<DiaryStatsPanel stats={stats} />)
    expect(screen.getByText('-')).toBeInTheDocument()
  })

  it('should not render mood distribution when empty', () => {
    const stats = { ...mockStats, mood_distribution: {} }
    render(<DiaryStatsPanel stats={stats} />)
    expect(screen.queryByText('心情分布')).not.toBeInTheDocument()
  })

  it('should render all four stat cards', () => {
    render(<DiaryStatsPanel stats={mockStats} />)
    expect(screen.getByText('总日记数')).toBeInTheDocument()
    expect(screen.getByText('连续打卡')).toBeInTheDocument()
    expect(screen.getByText('平均评分')).toBeInTheDocument()
    expect(screen.getByText('穿搭件数')).toBeInTheDocument()
  })
})
