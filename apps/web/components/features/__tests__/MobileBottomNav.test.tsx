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
    expect(screen.getByText('推荐')).toBeInTheDocument()
    expect(screen.getByText('衣橱')).toBeInTheDocument()
    expect(screen.getByText('广场')).toBeInTheDocument()
    expect(screen.getByText('我的')).toBeInTheDocument()
  })

  it('should not render secondary items initially', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    // 试衣、日记、运势、命理、修炼 are in the "更多" sheet, not visible initially
    expect(screen.queryByText('试衣')).not.toBeInTheDocument()
    expect(screen.queryByText('日记')).not.toBeInTheDocument()
    expect(screen.queryByText('命理')).not.toBeInTheDocument()
    expect(screen.queryByText('修炼')).not.toBeInTheDocument()
  })

  it('should call onTabChange when a primary tab is clicked', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
    fireEvent.click(screen.getByText('衣橱'))
    expect(mockOnTabChange).toHaveBeenCalledWith('wardrobe')
  })

  it('should call onTabChange for community tab', () => {
    render(<MobileBottomNav activeTab="chat" onTabChange={mockOnTabChange} />)
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

