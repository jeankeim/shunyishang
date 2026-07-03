import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MobileBottomNav } from '../MobileBottomNav'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

describe('MobileBottomNav', () => {
  const mockOnTabChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render 5 primary nav items', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    expect(screen.getByText('推荐')).toBeInTheDocument()
    expect(screen.getByText('衣橱')).toBeInTheDocument()
    expect(screen.getByText('试衣')).toBeInTheDocument()
    expect(screen.getByText('运势')).toBeInTheDocument()
    expect(screen.getByText('更多')).toBeInTheDocument()
  })

  it('should render primary icons', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    expect(screen.getByText('✨')).toBeInTheDocument()
    expect(screen.getByText('👔')).toBeInTheDocument()
    expect(screen.getByText('👗')).toBeInTheDocument()
    expect(screen.getByText('🔮')).toBeInTheDocument()
    expect(screen.getByText('☰')).toBeInTheDocument()
  })

  it('should not render secondary items initially', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    // 日记、命理、广场、修炼 are in the "更多" sheet, not visible initially
    expect(screen.queryByText('日记')).not.toBeInTheDocument()
    expect(screen.queryByText('命理')).not.toBeInTheDocument()
    expect(screen.queryByText('广场')).not.toBeInTheDocument()
    expect(screen.queryByText('修炼')).not.toBeInTheDocument()
  })

  it('should not have profile tab', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    expect(screen.queryByText('我的')).not.toBeInTheDocument()
    expect(screen.queryByText('👤')).not.toBeInTheDocument()
  })

  it('should call onTabChange when a primary tab is clicked', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('衣橱'))
    expect(mockOnTabChange).toHaveBeenCalledWith('wardrobe')
  })

  it('should call onTabChange for fortune tab', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('运势'))
    expect(mockOnTabChange).toHaveBeenCalledWith('fortune')
  })

  it('should call onTabChange for tryon tab', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('试衣'))
    expect(mockOnTabChange).toHaveBeenCalledWith('tryon')
  })

  it('should mark active tab with aria-current', () => {
    render(<MobileBottomNav activeTab="wardrobe" onTabChange={mockOnTabChange} />)
    const activeBtn = screen.getByLabelText('切换到衣橱页面')
    expect(activeBtn).toHaveAttribute('aria-current', 'page')
  })

  it('should not mark inactive tabs with aria-current', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    const inactiveBtn = screen.getByLabelText('切换到衣橱页面')
    expect(inactiveBtn).not.toHaveAttribute('aria-current', 'page')
  })

  it('should open more sheet when 更多 is clicked', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('更多'))
    // Secondary items should now be visible
    expect(screen.getByText('日记')).toBeInTheDocument()
    expect(screen.getByText('命理')).toBeInTheDocument()
    expect(screen.getByText('广场')).toBeInTheDocument()
    expect(screen.getByText('修炼')).toBeInTheDocument()
  })

  it('should call onTabChange for diary when clicked from more sheet', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('更多'))
    fireEvent.click(screen.getByText('日记'))
    expect(mockOnTabChange).toHaveBeenCalledWith('diary')
  })

  it('should call onTabChange for community when clicked from more sheet', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('更多'))
    fireEvent.click(screen.getByText('广场'))
    expect(mockOnTabChange).toHaveBeenCalledWith('community')
  })

  it('should mark 更多 as active when secondary tab is active', () => {
    render(<MobileBottomNav activeTab="diary" onTabChange={mockOnTabChange} />)
    const moreBtn = screen.getByLabelText('更多功能')
    expect(moreBtn).toHaveAttribute('aria-current', 'page')
  })

  it('should close more sheet when a primary tab is clicked', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    // Open sheet
    fireEvent.click(screen.getByText('更多'))
    expect(screen.getByText('日记')).toBeInTheDocument()
    // Click a primary tab
    fireEvent.click(screen.getByText('推荐'))
    // Sheet should close
    expect(screen.queryByText('日记')).not.toBeInTheDocument()
  })

  it('should have navigation role', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })
})
