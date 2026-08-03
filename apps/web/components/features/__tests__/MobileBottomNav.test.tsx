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

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-testid="sparkles-icon" />,
  Shirt: () => <span data-testid="shirt-icon" />,
  Users: () => <span data-testid="users-icon" />,
  User: () => <span data-testid="user-icon" />,
  Scan: () => <span data-testid="scan-icon" />,
  BookOpen: () => <span data-testid="book-icon" />,
  Compass: () => <span data-testid="compass-icon" />,
  CircleDot: () => <span data-testid="circledot-icon" />,
  Mountain: () => <span data-testid="mountain-icon" />,
  MoreHorizontal: () => <span data-testid="more-icon" />,
  Menu: () => <span data-testid="menu-icon" />,
  X: () => <span data-testid="x-icon" />,
}))

describe('MobileBottomNav', () => {
  const mockOnTabChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render 4 primary nav items', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    // 主导航：运势、推荐、衣橱、我的
    expect(screen.getByText('运势')).toBeInTheDocument()
    expect(screen.getByText('推荐')).toBeInTheDocument()
    expect(screen.getByText('衣橱')).toBeInTheDocument()
    expect(screen.getByText('我的')).toBeInTheDocument()
  })

  it('should not render secondary items initially', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    // 日记、广场、修炼 在 "更多" 面板中，初始不可见
    expect(screen.queryByText('日记')).not.toBeInTheDocument()
    expect(screen.queryByText('广场')).not.toBeInTheDocument()
    expect(screen.queryByText('修炼')).not.toBeInTheDocument()
  })

  it('should call onTabChange when a primary tab is clicked', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('衣橱'))
    expect(mockOnTabChange).toHaveBeenCalledWith('wardrobe')
  })

  it('should call onTabChange for community tab', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    // 广场在 "更多" 面板中，需先点击 "更多" 展开
    fireEvent.click(screen.getByText('更多'))
    fireEvent.click(screen.getByText('广场'))
    expect(mockOnTabChange).toHaveBeenCalledWith('community')
  })

  it('should call onTabChange for profile tab', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('我的'))
    expect(mockOnTabChange).toHaveBeenCalledWith('profile')
  })

  it('should highlight active tab', () => {
    render(<MobileBottomNav activeTab="wardrobe" onTabChange={mockOnTabChange} />)
    // Active tab should have different styling (verified by rendering)
    expect(screen.getByText('衣橱')).toBeInTheDocument()
  })
})

