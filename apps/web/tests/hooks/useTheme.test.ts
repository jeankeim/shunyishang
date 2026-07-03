import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTheme } from '@/hooks/useTheme'

vi.mock('@/lib/theme', () => ({
  getCurrentSolarTerm: vi.fn(() => ({
    name: '木',
    element: 'wood',
    primaryColor: '#22c55e',
    bgColor: '#0f172a',
    cssVariable: '142 76% 36%',
  })),
}))

describe('useTheme', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should set currentTerm and mounted after mount', async () => {
    const { result } = renderHook(() => useTheme())

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(result.current.currentTerm).not.toBeNull()
    expect(result.current.currentTerm?.element).toBe('wood')
    expect(result.current.mounted).toBe(true)
  })

  it('should always have isDark as true', async () => {
    const { result } = renderHook(() => useTheme())

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(result.current.isDark).toBe(true)
  })

  it('should return cssVariable from currentTerm after mount', async () => {
    const { result } = renderHook(() => useTheme())

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0))
    })

    expect(result.current.cssVariable).toBe('142 76% 36%')
  })

  it('should return default cssVariable before mount', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.cssVariable).toBe('142 76% 36%')
  })
})
