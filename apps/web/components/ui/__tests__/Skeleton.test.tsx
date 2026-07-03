import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Skeleton, SkeletonCard, SkeletonList } from '../Skeleton'

describe('Skeleton', () => {
  it('should render with default props', () => {
    const { container } = render(<Skeleton />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton).toBeInTheDocument()
    expect(skeleton.className).toContain('animate-pulse')
    expect(skeleton.className).toContain('rounded-lg')
  })

  it('should apply custom className', () => {
    const { container } = render(<Skeleton className="h-10 w-full" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).toContain('h-10')
    expect(skeleton.className).toContain('w-full')
  })

  it('should render circular variant with rounded-full', () => {
    const { container } = render(<Skeleton variant="circular" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).toContain('rounded-full')
  })

  it('should render text variant with h-4', () => {
    const { container } = render(<Skeleton variant="text" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).toContain('h-4')
  })

  it('should render rectangular variant with rounded-lg (default)', () => {
    const { container } = render(<Skeleton variant="rectangular" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).toContain('rounded-lg')
  })

  it('should apply pulse animation', () => {
    const { container } = render(<Skeleton animation="pulse" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).toContain('animate-pulse')
  })

  it('should apply wave animation', () => {
    const { container } = render(<Skeleton animation="wave" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).toContain('overflow-hidden')
  })

  it('should not apply animation when set to none', () => {
    const { container } = render(<Skeleton animation="none" />)
    const skeleton = container.firstChild as HTMLElement
    expect(skeleton.className).not.toContain('animate-pulse')
  })
})

describe('SkeletonCard', () => {
  it('should render with image by default', () => {
    const { container } = render(<SkeletonCard />)
    const skeletons = container.querySelectorAll('[class*="animate"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('should render without image when showImage is false', () => {
    const { container } = render(<SkeletonCard showImage={false} />)
    // Without image, there should be fewer skeleton elements
    const h40 = container.querySelector('.h-40')
    expect(h40).toBeNull()
  })

  it('should render multiple lines', () => {
    const { container } = render(<SkeletonCard lines={3} showImage={false} />)
    const skeletons = container.querySelectorAll('[class*="animate"]')
    expect(skeletons.length).toBeGreaterThanOrEqual(3)
  })

  it('should apply custom className', () => {
    const { container } = render(<SkeletonCard className="custom-card" />)
    const card = container.firstChild as HTMLElement
    expect(card.className).toContain('custom-card')
  })
})

describe('SkeletonList', () => {
  it('should render default count of 4 cards', () => {
    const { container } = render(<SkeletonList />)
    const cards = container.querySelector('div')?.children
    expect(cards?.length).toBe(4)
  })

  it('should render custom count of cards', () => {
    const { container } = render(<SkeletonList count={6} />)
    const cards = container.querySelector('div')?.children
    expect(cards?.length).toBe(6)
  })

  it('should render without images when showImage is false', () => {
    const { container } = render(<SkeletonList count={2} showImage={false} />)
    const h40 = container.querySelector('.h-40')
    expect(h40).toBeNull()
  })

  it('should apply custom className', () => {
    const { container } = render(<SkeletonList className="custom-list" />)
    const list = container.firstChild as HTMLElement
    expect(list.className).toContain('custom-list')
  })
})
