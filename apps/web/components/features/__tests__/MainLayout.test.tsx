import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MainLayout } from '../MainLayout'

// Mock Sidebar
vi.mock('../Sidebar', () => ({
  Sidebar: ({ collapsed, onToggle }: any) => (
    <div data-testid="sidebar" data-collapsed={collapsed}>
      <button onClick={onToggle} data-testid="sidebar-toggle">toggle</button>
    </div>
  ),
}))

// Mock Header
vi.mock('../Header', () => ({
  Header: ({ sidebarCollapsed, onToggleSidebar }: any) => (
    <div data-testid="header" data-collapsed={sidebarCollapsed}>
      <button onClick={onToggleSidebar} data-testid="header-toggle">toggle</button>
    </div>
  ),
}))

// Mock useTheme
vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({
    currentTerm: { element: '水', name: '小寒' },
    mounted: true,
  }),
}))

// Mock cn
vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

describe('MainLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render sidebar and header', () => {
    render(<MainLayout><div>Content</div></MainLayout>)
    expect(screen.getByTestId('sidebar')).toBeInTheDocument()
    expect(screen.getByTestId('header')).toBeInTheDocument()
  })

  it('should render children content', () => {
    render(<MainLayout><div data-testid="child">Test Content</div></MainLayout>)
    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('should toggle sidebar when header toggle is clicked', () => {
    render(<MainLayout><div>Content</div></MainLayout>)
    
    // Initially collapsed (default true)
    expect(screen.getByTestId('sidebar')).toHaveAttribute('data-collapsed', 'true')
    
    // Click header toggle to expand
    fireEvent.click(screen.getByTestId('header-toggle'))
    expect(screen.getByTestId('sidebar')).toHaveAttribute('data-collapsed', 'false')
    
    // Click again to collapse
    fireEvent.click(screen.getByTestId('header-toggle'))
    expect(screen.getByTestId('sidebar')).toHaveAttribute('data-collapsed', 'true')
  })

  it('should toggle sidebar when sidebar toggle is clicked', () => {
    render(<MainLayout><div>Content</div></MainLayout>)
    
    // Click sidebar toggle
    fireEvent.click(screen.getByTestId('sidebar-toggle'))
    expect(screen.getByTestId('sidebar')).toHaveAttribute('data-collapsed', 'false')
  })

  it('should set data-element attribute when mounted', () => {
    const { container } = render(<MainLayout><div>Content</div></MainLayout>)
    const rootDiv = container.firstChild as HTMLElement
    expect(rootDiv.getAttribute('data-element')).toBe('水')
  })

  it('should add margin-left when sidebar is expanded', () => {
    render(<MainLayout><div>Content</div></MainLayout>)
    
    // Expand sidebar
    fireEvent.click(screen.getByTestId('header-toggle'))
    
    const main = screen.getByTestId('header').parentElement
    expect(main?.className).toContain('ml-[360px]')
  })
})
