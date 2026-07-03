import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skeleton } from '../Skeleton'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

describe('Skeleton', () => {
  it('should render card skeleton by default', () => {
    const { container } = render(<Skeleton />)
    expect(container.querySelector('.bg-white.rounded-2xl')).toBeInTheDocument()
  })

  it('should render card skeleton with type="card"', () => {
    const { container } = render(<Skeleton type="card" />)
    expect(container.querySelector('.bg-white.rounded-2xl')).toBeInTheDocument()
  })

  it('should render list skeleton with type="list"', () => {
    const { container } = render(<Skeleton type="list" count={3} />)
    const items = container.querySelectorAll('.flex.items-center.gap-3.p-3.bg-white.rounded-xl')
    expect(items.length).toBe(3)
  })

  it('should render list skeleton with custom count', () => {
    const { container } = render(<Skeleton type="list" count={5} />)
    const items = container.querySelectorAll('.flex.items-center.gap-3.p-3.bg-white.rounded-xl')
    expect(items.length).toBe(5)
  })

  it('should render text skeleton with type="text"', () => {
    const { container } = render(<Skeleton type="text" />)
    const items = container.querySelectorAll('.h-4.bg-stone-200.rounded.animate-pulse')
    expect(items.length).toBeGreaterThan(0)
  })

  it('should render image skeleton with type="image"', () => {
    const { container } = render(<Skeleton type="image" />)
    expect(container.querySelector('.aspect-square')).toBeInTheDocument()
  })

  it('should render recommend skeleton with type="recommend"', () => {
    const { container } = render(<Skeleton type="recommend" />)
    expect(container.querySelector('.bg-white\\/90')).toBeInTheDocument()
  })

  it('should render null for unknown type', () => {
    const { container } = render(<Skeleton type={'unknown' as any} />)
    expect(container.innerHTML).toBe('')
  })

  it('should use default count of 3 for list', () => {
    const { container } = render(<Skeleton type="list" />)
    const items = container.querySelectorAll('.flex.items-center.gap-3.p-3.bg-white.rounded-xl')
    expect(items.length).toBe(3)
  })
})
