import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Header } from '../Header'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, ...props }: any) => <div onClick={onClick} {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Leaf: () => <span data-testid="leaf" />,
  User: () => <span data-testid="user" />,
  LogOut: () => <span data-testid="logout" />,
  Settings: () => <span data-testid="settings" />,
  X: () => <span data-testid="x" />,
  Menu: () => <span data-testid="menu" />,
  Crown: () => <span data-testid="crown" />,
}))

// Mock useTheme
vi.mock('@/hooks/useTheme', () => ({
  useTheme: () => ({
    currentTerm: { name: '小寒', element: '水', primaryColor: '#4A90C4' },
    mounted: true,
  }),
}))

// Configurable mock user store
let mockUserStoreData: any = {}

vi.mock('@/store/user', () => ({
  useUserStore: () => mockUserStoreData,
}))

// Mock NotificationBell
vi.mock('../membership/NotificationBell', () => ({
  NotificationBell: () => <div data-testid="notification-bell" />,
}))

// Mock lazy AuthModal - must export default for React.lazy
vi.mock('../AuthModal', () => ({
  AuthModal: ({ isOpen, onClose }: any) =>
    isOpen ? <div data-testid="auth-modal"><button onClick={onClose}>close</button></div> : null,
}))

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUserStoreData = {
      user: null,
      isAuthenticated: false,
      logout: vi.fn().mockResolvedValue(undefined),
      fetchUserInfo: vi.fn(),
    }
  })

  it('should render logo text "我的个人衣橱"', () => {
    render(<Header />)
    expect(screen.getAllByText('我的个人衣橱').length).toBeGreaterThan(0)
  })

  it('should render menu button', () => {
    render(<Header />)
    expect(screen.getByLabelText('切换侧边栏')).toBeInTheDocument()
  })

  it('should render login button when not authenticated', () => {
    render(<Header />)
    expect(screen.getByText('登录')).toBeInTheDocument()
  })

  it('should not render notification bell when not authenticated', () => {
    render(<Header />)
    expect(screen.queryByTestId('notification-bell')).not.toBeInTheDocument()
  })

  it('should render notification bell when authenticated', () => {
    mockUserStoreData.isAuthenticated = true
    render(<Header />)
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument()
  })

  it('should render user menu button when authenticated with user', () => {
    mockUserStoreData.isAuthenticated = true
    mockUserStoreData.user = { nickname: 'TestUser', phone: '13800000000' }
    render(<Header />)
    expect(screen.getByText('TestUser')).toBeInTheDocument()
  })

  it('should show auth modal when login button is clicked', () => {
    render(<Header />)
    fireEvent.click(screen.getByText('登录'))
    // AuthModal should be shown (via lazy/Suspense)
  })

  it('should call onToggleSidebar when menu button is clicked', () => {
    const onToggleSidebar = vi.fn()
    render(<Header onToggleSidebar={onToggleSidebar} />)
    fireEvent.click(screen.getByLabelText('切换侧边栏'))
    expect(onToggleSidebar).toHaveBeenCalled()
  })

  it('should render current solar term', () => {
    render(<Header />)
    expect(screen.getByText(/当前节气/)).toBeInTheDocument()
    expect(screen.getByText(/小寒/)).toBeInTheDocument()
  })

  it('should show user menu dropdown when user button is clicked', () => {
    mockUserStoreData.isAuthenticated = true
    mockUserStoreData.user = { nickname: 'TestUser', phone: '13800000000' }
    render(<Header />)
    
    fireEvent.click(screen.getByText('TestUser'))
    
    expect(screen.getByText('个人中心')).toBeInTheDocument()
    expect(screen.getByText('穿搭日记')).toBeInTheDocument()
    expect(screen.getByText('每日运势')).toBeInTheDocument()
    expect(screen.getByText('退出登录')).toBeInTheDocument()
  })

  it('should call logout when logout is clicked', async () => {
    mockUserStoreData.isAuthenticated = true
    mockUserStoreData.user = { nickname: 'TestUser', phone: '13800000000' }
    render(<Header />)
    
    fireEvent.click(screen.getByText('TestUser'))
    fireEvent.click(screen.getByText('退出登录'))
    
    await waitFor(() => {
      expect(mockUserStoreData.logout).toHaveBeenCalled()
    })
  })

  it('should display user nickname when available', () => {
    mockUserStoreData.isAuthenticated = true
    mockUserStoreData.user = { nickname: 'MyNickname', phone: '13800000000' }
    render(<Header />)
    expect(screen.getByText('MyNickname')).toBeInTheDocument()
  })

  it('should display phone when nickname is not available', () => {
    mockUserStoreData.isAuthenticated = true
    mockUserStoreData.user = { nickname: null, phone: '13800000000' }
    render(<Header />)
    expect(screen.getByText('13800000000')).toBeInTheDocument()
  })
})
