import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LuckyElements } from '../LuckyElements'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

describe('LuckyElements', () => {
  const mockLuckyElements = {
    colors: ['红色', '紫色'],
    materials: ['棉', '丝'],
    directions: ['东南'],
    elements: ['木', '火'],
  }

  it('should render all sections with data', () => {
    render(<LuckyElements luckyElements={mockLuckyElements} />)
    expect(screen.getByText('今日幸运元素')).toBeInTheDocument()
    expect(screen.getByText('幸运颜色')).toBeInTheDocument()
    expect(screen.getByText('推荐材质')).toBeInTheDocument()
    expect(screen.getByText('吉利方位')).toBeInTheDocument()
    expect(screen.getByText('五行元素')).toBeInTheDocument()
  })

  it('should render color items', () => {
    render(<LuckyElements luckyElements={mockLuckyElements} />)
    expect(screen.getByText('红色')).toBeInTheDocument()
    expect(screen.getByText('紫色')).toBeInTheDocument()
  })

  it('should render material items', () => {
    render(<LuckyElements luckyElements={mockLuckyElements} />)
    expect(screen.getByText('棉')).toBeInTheDocument()
    expect(screen.getByText('丝')).toBeInTheDocument()
  })

  it('should render direction items', () => {
    render(<LuckyElements luckyElements={mockLuckyElements} />)
    expect(screen.getByText('东南')).toBeInTheDocument()
  })

  it('should render element items', () => {
    render(<LuckyElements luckyElements={mockLuckyElements} />)
    expect(screen.getByText('木')).toBeInTheDocument()
    expect(screen.getByText('火')).toBeInTheDocument()
  })

  it('should show empty state when no data', () => {
    render(<LuckyElements luckyElements={{ colors: [], materials: [], directions: [], elements: [] }} />)
    expect(screen.getByText('暂无幸运元素数据')).toBeInTheDocument()
  })

  it('should render partially when some sections have data', () => {
    render(<LuckyElements luckyElements={{ colors: ['红色'], materials: [], directions: [], elements: [] }} />)
    expect(screen.getByText('幸运颜色')).toBeInTheDocument()
    expect(screen.getByText('红色')).toBeInTheDocument()
    expect(screen.queryByText('推荐材质')).not.toBeInTheDocument()
  })

  it('should render emojis for sections', () => {
    render(<LuckyElements luckyElements={mockLuckyElements} />)
    expect(screen.getByText('🎨')).toBeInTheDocument()
    expect(screen.getByText('🧵')).toBeInTheDocument()
    expect(screen.getByText('🧭')).toBeInTheDocument()
    expect(screen.getByText('✨')).toBeInTheDocument()
  })
})
