import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useMediaQuery } from '@/hooks/useMediaQuery'

function setupMatchMedia(matches: boolean) {
  const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: matchMediaMock,
  })

  return { matchMediaMock }
}

describe('useMediaQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should return false initially', () => {
    setupMatchMedia(false)
    const { result } = renderHook(() => useMediaQuery('(min-width: 768px)'))
    expect(result.current).toBe(false)
  })

  it('should update to true when media matches', () => {
    setupMatchMedia(true)
    const { result, rerender } = renderHook(() => useMediaQuery('(min-width: 768px)'))

    act(() => {
      rerender()
    })

    expect(result.current).toBe(true)
  })

  it('should call matchMedia with the query', () => {
    const { matchMediaMock } = setupMatchMedia(false)
    renderHook(() => useMediaQuery('(min-width: 1024px)'))
    expect(matchMediaMock).toHaveBeenCalledWith('(min-width: 1024px)')
  })
})
