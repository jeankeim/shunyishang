import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from '@testing-library/react'
import { TypewriterText } from '../TypewriterText'

describe('TypewriterText', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should render empty span initially', () => {
    const { container } = render(<TypewriterText text="Hello" speed={10} />)
    const span = container.querySelector('span')
    expect(span).toBeInTheDocument()
    expect(span?.textContent).toBe('')
  })

  it('should display text character by character', () => {
    const { container } = render(<TypewriterText text="Hi" speed={10} />)

    // First character
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(container.querySelector('span')?.textContent).toBe('H')

    // Second character
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(container.querySelector('span')?.textContent).toBe('Hi')
  })

  it('should call onComplete when typing is finished', () => {
    const onComplete = vi.fn()
    render(<TypewriterText text="Hi" speed={10} onComplete={onComplete} />)

    // First character (10ms)
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(onComplete).not.toHaveBeenCalled()

    // Second character (20ms)
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(onComplete).not.toHaveBeenCalled()

    // Complete (30ms) - index >= text.length triggers onComplete
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(onComplete).toHaveBeenCalledTimes(1)
  })

  it('should use default speed of 20ms', () => {
    const { container } = render(<TypewriterText text="A" />)
    
    // After 19ms, nothing should appear
    act(() => {
      vi.advanceTimersByTime(19)
    })
    expect(container.querySelector('span')?.textContent).toBe('')

    // After 20ms, first character should appear
    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(container.querySelector('span')?.textContent).toBe('A')
  })

  it('should handle empty text', () => {
    const { container } = render(<TypewriterText text="" speed={10} />)
    expect(container.querySelector('span')?.textContent).toBe('')
  })

  it('should clean up timer on unmount', () => {
    const { unmount } = render(<TypewriterText text="Hello" speed={10} />)
    
    // Should not throw when unmounting
    expect(() => unmount()).not.toThrow()
  })
})
