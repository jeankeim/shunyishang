import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MembershipCard } from '../MembershipCard'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Crown: () => <span data-testid="crown" />,
  Calendar: () => <span data-testid="calendar" />,
  Zap: () => <span data-testid="zap" />,
}))

// Mock store
const mockFetchStatus = vi.fn()
vi.mock('@/store/membership', () => ({
  useMembershipStore: () => ({
    status: null,
    fetchStatus: mockFetchStatus,
  }),
}))

describe('MembershipCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should call fetchStatus on mount', () => {
    render(<MembershipCard />)
    expect(mockFetchStatus).toHaveBeenCalled()
  })

  it('should render free plan by default when status is null', () => {
    render(<MembershipCard />)
    expect(screen.getByText('免费版')).toBeInTheDocument()
    expect(screen.getByText('升级会员解锁无限推荐、AI点评等高级功能')).toBeInTheDocument()
  })

  it('should render free plan icon', () => {
    render(<MembershipCard />)
    expect(screen.getByText('🌱')).toBeInTheDocument()
  })

  it('should render "未激活" when status is not active', () => {
    render(<MembershipCard />)
    expect(screen.getByText('未激活')).toBeInTheDocument()
  })
})
