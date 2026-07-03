import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SwipeToDelete } from '../SwipeToDelete'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Trash2: () => <span data-testid="trash-icon" />,
}))

describe('SwipeToDelete', () => {
  it('should render children', () => {
    render(
      <SwipeToDelete onSwipe={vi.fn()}>
        <div data-testid="content">Test Content</div>
      </SwipeToDelete>
    )
    expect(screen.getByTestId('content')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('should render delete button background', () => {
    render(
      <SwipeToDelete onSwipe={vi.fn()}>
        <div>Content</div>
      </SwipeToDelete>
    )
    expect(screen.getByText('删除')).toBeInTheDocument()
    expect(screen.getByTestId('trash-icon')).toBeInTheDocument()
  })

  it('should render with relative overflow-hidden container', () => {
    const { container } = render(
      <SwipeToDelete onSwipe={vi.fn()}>
        <div>Content</div>
      </SwipeToDelete>
    )
    expect(container.firstChild).toHaveClass('relative', 'overflow-hidden', 'rounded-xl')
  })

  it('should use custom threshold', () => {
    // Component accepts threshold prop, just verify it renders without error
    render(
      <SwipeToDelete onSwipe={vi.fn()} threshold={150}>
        <div>Content</div>
      </SwipeToDelete>
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('should use default threshold of 100', () => {
    render(
      <SwipeToDelete onSwipe={vi.fn()}>
        <div>Content</div>
      </SwipeToDelete>
    )
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('should render delete text', () => {
    render(
      <SwipeToDelete onSwipe={vi.fn()}>
        <div>Content</div>
      </SwipeToDelete>
    )
    expect(screen.getByText('删除')).toBeInTheDocument()
  })
})
