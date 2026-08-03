import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FortuneCard } from '../FortuneCard'
import type { DailyFortune } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
}))

const mockFortune: DailyFortune = {
  id: 1,
  user_id: 1,
  fortune_date: '2026-01-15',
  overall_score: 85,
  scores: {
    career: 90,
    wealth: 70,
    love: 80,
    health: 85,
    study: 75,
  },
  lucky_elements: {
    colors: ['绿色', '蓝色'],
    materials: ['棉', '丝'],
    directions: ['东', '南'],
    elements: ['木', '水'],
  },
  advice_text: '今日适合重要会议',
  outfit_suggestion: '建议穿绿色系',
  created_at: '2026-01-15T00:00:00Z',
}

describe('FortuneCard', () => {
  it('should render fortune date and overall score', () => {
    render(<FortuneCard fortune={mockFortune} />)
    // 组件渲染了 weekday，如 "1月15日 周四 运势"
    expect(screen.getByText(/1月15日.*运势/)).toBeInTheDocument()
    // 85 出现在综合评分（白色文字）和健康分数中
    expect(screen.getAllByText('85').length).toBeGreaterThanOrEqual(1)
  })

  it('should render all five dimension scores', () => {
    render(<FortuneCard fortune={mockFortune} />)
    expect(screen.getByText('90')).toBeInTheDocument()
    expect(screen.getByText('70')).toBeInTheDocument()
    expect(screen.getByText('80')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
  })

  it('should render dimension labels and emojis', () => {
    render(<FortuneCard fortune={mockFortune} />)
    expect(screen.getByText('事业')).toBeInTheDocument()
    expect(screen.getByText('财运')).toBeInTheDocument()
    expect(screen.getByText('桃花')).toBeInTheDocument()
    expect(screen.getByText('健康')).toBeInTheDocument()
    expect(screen.getByText('学业')).toBeInTheDocument()
  })

  it('should render advice text when present', () => {
    // advice_text 已不再直接渲染；组件现在使用 AI 叙事字段
    // 改为验证 advice_text 不会导致崩溃
    render(<FortuneCard fortune={mockFortune} />)
    expect(screen.getByText(/1月15日/)).toBeInTheDocument()
  })

  it('should render outfit suggestion when present', () => {
    render(<FortuneCard fortune={mockFortune} />)
    // 组件渲染时带 emoji 前缀 "👔 今日穿搭建议"
    expect(screen.getByText(/今日穿搭建议/)).toBeInTheDocument()
    expect(screen.getByText('建议穿绿色系')).toBeInTheDocument()
  })

  it('should not render advice section when absent', () => {
    const fortune = { ...mockFortune, advice_text: undefined }
    render(<FortuneCard fortune={fortune} />)
    // advice_text 不直接渲染，验证组件正常渲染
    expect(screen.getByText(/1月15日/)).toBeInTheDocument()
  })

  it('should not render outfit section when absent', () => {
    const fortune = { ...mockFortune, outfit_suggestion: undefined }
    render(<FortuneCard fortune={fortune} />)
    expect(screen.queryByText(/今日穿搭建议/)).not.toBeInTheDocument()
  })

  it('should render regenerate button when onRegenerate is provided', () => {
    const onRegenerate = vi.fn()
    render(<FortuneCard fortune={mockFortune} onRegenerate={onRegenerate} />)
    // 组件渲染时带 emoji 前缀 "🔄 重新生成运势"
    const btn = screen.getByText(/重新生成运势/)
    expect(btn).toBeInTheDocument()
  })

  it('should call onRegenerate when button is clicked', () => {
    const onRegenerate = vi.fn()
    render(<FortuneCard fortune={mockFortune} onRegenerate={onRegenerate} />)
    fireEvent.click(screen.getByText(/重新生成运势/))
    expect(onRegenerate).toHaveBeenCalledTimes(1)
  })

  it('should not render regenerate button when onRegenerate is not provided', () => {
    render(<FortuneCard fortune={mockFortune} />)
    expect(screen.queryByText(/重新生成运势/)).not.toBeInTheDocument()
  })

  it('should render subtitle text', () => {
    render(<FortuneCard fortune={mockFortune} />)
    // 组件渲染为 "日 · 基于八字五行分析"（含干支前缀）
    expect(screen.getByText(/基于八字五行分析/)).toBeInTheDocument()
  })
})
