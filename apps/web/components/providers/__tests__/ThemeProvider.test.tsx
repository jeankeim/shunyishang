import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { ThemeProvider } from '../ThemeProvider'

const mockInitAuth = vi.fn()
const mockUseTheme = vi.fn()

vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => mockUseTheme(),
}))

const mockUserState = { initAuth: mockInitAuth }
vi.mock('@/store/user', () => ({
  useUserStore: (selector?: any) => selector ? selector(mockUserState) : mockUserState,
}))

describe('ThemeProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.style.setProperty('--primary', '')
    document.documentElement.style.setProperty('--ring', '')
    mockUseTheme.mockReturnValue({
      currentTerm: null,
      mounted: false,
    })
  })

  it('should render children', () => {
    mockUseTheme.mockReturnValue({
      currentTerm: null,
      mounted: true,
    })
    const { container } = render(
      <ThemeProvider>
        <div data-testid="child">Hello</div>
      </ThemeProvider>
    )
    expect(container.querySelector('[data-testid="child"]')).toBeInTheDocument()
  })

  it('should call initAuth on mount', () => {
    render(
      <ThemeProvider>
        <div>Children</div>
      </ThemeProvider>
    )
    expect(mockInitAuth).toHaveBeenCalled()
  })

  it('should set CSS variables when currentTerm exists', () => {
    mockUseTheme.mockReturnValue({
      currentTerm: { cssVariable: '#3DA35D', name: 'spring' },
      mounted: true,
    })
    render(
      <ThemeProvider>
        <div>Children</div>
      </ThemeProvider>
    )
    expect(document.documentElement.style.getPropertyValue('--primary')).toBe('#3DA35D')
    expect(document.documentElement.style.getPropertyValue('--ring')).toBe('#3DA35D')
  })

  it('should not set CSS variables when currentTerm is null', () => {
    mockUseTheme.mockReturnValue({
      currentTerm: null,
      mounted: true,
    })
    render(
      <ThemeProvider>
        <div>Children</div>
      </ThemeProvider>
    )
    expect(document.documentElement.style.getPropertyValue('--primary')).toBe('')
  })
})
