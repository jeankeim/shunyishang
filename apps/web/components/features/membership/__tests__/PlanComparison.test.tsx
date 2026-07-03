import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { PlanComparison } from '../PlanComparison'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Check: () => <span data-testid="check" />,
  X: () => <span data-testid="x" />,
}))

// Configurable mock store
let mockStoreData: any = {
  plans: [],
  fetchPlans: vi.fn(),
  status: null,
  subscribe: vi.fn(),
  upgrade: vi.fn(),
  isLoading: false,
}

vi.mock('@/store/membership', () => ({
  useMembershipStore: () => mockStoreData,
}))

const mockPlans = [
  {
    plan_key: 'free',
    name: '免费版',
    price_monthly: 0,
    price_yearly: 0,
    features: ['每日1次推荐', '基础衣橱管理'],
  },
  {
    plan_key: 'monthly',
    name: '月度会员',
    price_monthly: 29,
    price_yearly: 299,
    features: ['无限推荐', 'AI穿搭点评', '日记AI分析'],
  },
  {
    plan_key: 'yearly',
    name: '年度会员',
    price_monthly: 29,
    price_yearly: 299,
    features: ['无限推荐', 'AI穿搭点评', '日记AI分析', '专属顾问'],
  },
]

describe('PlanComparison', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStoreData = {
      plans: mockPlans,
      fetchPlans: vi.fn(),
      status: { plan: 'free', status: 'active' },
      subscribe: vi.fn().mockResolvedValue(undefined),
      upgrade: vi.fn().mockResolvedValue(undefined),
      isLoading: false,
    }
  })

  it('should call fetchPlans on mount', () => {
    render(<PlanComparison />)
    expect(mockStoreData.fetchPlans).toHaveBeenCalled()
  })

  it('should render all plan names', () => {
    render(<PlanComparison />)
    expect(screen.getByText('免费版')).toBeInTheDocument()
    expect(screen.getByText('月度会员')).toBeInTheDocument()
    expect(screen.getByText('年度会员')).toBeInTheDocument()
  })

  it('should render "最划算" badge for yearly plan', () => {
    render(<PlanComparison />)
    expect(screen.getByText('最划算')).toBeInTheDocument()
  })

  it('should render "免费" for free plan price', () => {
    render(<PlanComparison />)
    expect(screen.getByText('免费')).toBeInTheDocument()
  })

  it('should render monthly price with /月', () => {
    render(<PlanComparison />)
    expect(screen.getByText('¥29')).toBeInTheDocument()
    expect(screen.getByText('/月')).toBeInTheDocument()
  })

  it('should render yearly price with /年', () => {
    render(<PlanComparison />)
    expect(screen.getByText('/年')).toBeInTheDocument()
  })

  it('should render plan features', () => {
    render(<PlanComparison />)
    expect(screen.getByText('每日1次推荐')).toBeInTheDocument()
    expect(screen.getAllByText('无限推荐')).toHaveLength(2)
    expect(screen.getByText('专属顾问')).toBeInTheDocument()
  })

  it('should show "当前套餐" for current plan', () => {
    render(<PlanComparison />)
    expect(screen.getByText('当前套餐')).toBeInTheDocument()
  })

  it('should show "立即订阅" for upgradeable plans when current is free', () => {
    render(<PlanComparison />)
    const subscribeButtons = screen.getAllByText('立即订阅')
    expect(subscribeButtons).toHaveLength(2)
  })

  it('should call subscribe when subscribe button is clicked', async () => {
    render(<PlanComparison />)
    const subscribeButtons = screen.getAllByText('立即订阅')
    fireEvent.click(subscribeButtons[0])
    await waitFor(() => {
      expect(mockStoreData.subscribe).toHaveBeenCalledWith('monthly', 'mock')
    })
  })

  it('should call upgrade when yearly upgrade is clicked from monthly', () => {
    mockStoreData.status = { plan: 'monthly', status: 'active' }
    render(<PlanComparison />)
    const upgradeBtn = screen.getByText('立即升级')
    fireEvent.click(upgradeBtn)
    expect(mockStoreData.upgrade).toHaveBeenCalledWith('yearly')
  })

  it('should render empty when no plans', () => {
    mockStoreData.plans = []
    const { container } = render(<PlanComparison />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('should show "无需操作" for non-upgradeable paid plans', () => {
    mockStoreData.status = { plan: 'yearly', status: 'active' }
    render(<PlanComparison />)
    const noActionTexts = screen.getAllByText('无需操作')
    expect(noActionTexts.length).toBeGreaterThan(0)
  })
})
