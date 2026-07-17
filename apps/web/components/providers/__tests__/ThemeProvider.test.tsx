import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { ThemeProvider } from '../ThemeProvider'

// Use vi.hoisted to define mocks that are available when vi.mock factories run
const { mockInitAuth, mockUserStore, mockChatStore } = vi.hoisted(() => {
  const mockInitAuth = vi.fn()
  const mockUserStore: any = Object.assign(
    (selector?: any) => selector ? selector({ initAuth: mockInitAuth }) : { initAuth: mockInitAuth },
    { persist: { rehydrate: vi.fn() } }
  )
  const mockChatStore: any = { persist: { rehydrate: vi.fn() } }
  return { mockInitAuth, mockUserStore, mockChatStore }
})

vi.mock('@/hooks/useWuxingTheme', () => ({
  useWuxingTheme: () => ({ element: '', solarTerm: null }),
}))

vi.mock('@/store/user', () => ({
  useUserStore: mockUserStore,
}))

vi.mock('@/store/chat', () => ({
  useChatStore: mockChatStore,
}))

describe('ThemeProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render children', () => {
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

  it('should rehydrate user and chat stores on mount', () => {
    render(
      <ThemeProvider>
        <div>Children</div>
      </ThemeProvider>
    )
    expect(mockUserStore.persist.rehydrate).toHaveBeenCalled()
    expect(mockChatStore.persist.rehydrate).toHaveBeenCalled()
  })
})
