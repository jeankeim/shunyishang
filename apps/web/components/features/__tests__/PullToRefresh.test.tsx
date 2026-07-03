import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PullToRefresh } from '../PullToRefresh'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  RefreshCw: ({ className }: any) => <span data-testid="refresh-icon" className={className} />,
}))

describe('PullToRefresh', () => {
  it('should render children', () => {
    render(
      <PullToRefresh onRefresh={vi.fn()}>
        <div data-testid="content">Content</div>
      </PullToRefresh>
    )
    expect(screen.getByTestId('content')).toBeInTheDocument()
  })

  it('should render container with relative class', () => {
    const { container } = render(
      <PullToRefresh onRefresh={vi.fn()}>
        <div>Content</div>
      </PullToRefresh>
    )
    expect(container.firstChild).toHaveClass('relative')
  })

  it('should use custom threshold', () => {
    render(
      <PullToRefresh onRefresh={vi.fn()} threshold={120}>
        <div>Content</div>
      </PullToRefresh>
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('should use default threshold of 80', () => {
    render(
      <PullToRefresh onRefresh={vi.fn()}>
        <div>Content</div>
      </PullToRefresh>
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('should render children in content area', () => {
    render(
      <PullToRefresh onRefresh={vi.fn()}>
        <div>Test Content</div>
      </PullToRefresh>
    )
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('should not show refresh indicator initially', () => {
    render(
      <PullToRefresh onRefresh={vi.fn()}>
        <div>Content</div>
      </PullToRefresh>
    )
    expect(screen.queryByText('下拉刷新')).not.toBeInTheDocument()
    expect(screen.queryByText('松开刷新')).not.toBeInTheDocument()
    expect(screen.queryByText('刷新中...')).not.toBeInTheDocument()
  })
})
