import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { NotificationBell } from '../NotificationBell'
import type { PushNotification } from '@/types'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, onClick, ...props }: any) => <button onClick={onClick} {...props}>{children}</button>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Bell: () => <span data-testid="bell-icon" />,
  X: () => <span data-testid="x-icon" />,
  Check: () => <span data-testid="check-icon" />,
}))

// Configurable mock store
let mockStoreData: any = {}

vi.mock('@/store/membership', () => ({
  useMembershipStore: () => mockStoreData,
}))

const mockNotifications: PushNotification[] = [
  {
    id: 1,
    type: 'fortune_daily',
    title: '今日运势已更新',
    body: '点击查看今日穿搭建议',
    data: {},
    sent_at: '2026-01-15T08:00:00Z',
    read_at: undefined,
  },
  {
    id: 2,
    type: 'diary_reminder',
    title: '别忘了记录今日穿搭',
    body: '坚持记录，提升穿搭品味',
    data: {},
    sent_at: '2026-01-14T21:00:00Z',
    read_at: '2026-01-14T21:30:00Z',
  },
  {
    id: 3,
    type: 'marketing',
    title: '会员特惠活动',
    body: '限时8折优惠',
    data: {},
    sent_at: '2026-01-13T10:00:00Z',
    read_at: undefined,
  },
]

describe('NotificationBell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStoreData = {
      notifications: mockNotifications,
      unreadCount: 2,
      fetchNotifications: vi.fn(),
      fetchUnreadCount: vi.fn(),
      markAsRead: vi.fn().mockResolvedValue(undefined),
    }
  })

  it('should call fetchUnreadCount and fetchNotifications on mount', () => {
    render(<NotificationBell />)
    expect(mockStoreData.fetchUnreadCount).toHaveBeenCalled()
    expect(mockStoreData.fetchNotifications).toHaveBeenCalled()
  })

  it('should render bell button', () => {
    render(<NotificationBell />)
    expect(screen.getByLabelText(/通知/)).toBeInTheDocument()
  })

  it('should render unread count badge', () => {
    render(<NotificationBell />)
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('should not render badge when unreadCount is 0', () => {
    mockStoreData.unreadCount = 0
    render(<NotificationBell />)
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('should show 99+ when unreadCount exceeds 99', () => {
    mockStoreData.unreadCount = 150
    render(<NotificationBell />)
    expect(screen.getByText('99+')).toBeInTheDocument()
  })

  it('should open dropdown when bell is clicked', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('通知')).toBeInTheDocument()
  })

  it('should render notification titles in dropdown', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('今日运势已更新')).toBeInTheDocument()
    expect(screen.getByText('别忘了记录今日穿搭')).toBeInTheDocument()
    expect(screen.getByText('会员特惠活动')).toBeInTheDocument()
  })

  it('should render "暂无通知" when notifications is empty', () => {
    mockStoreData.notifications = []
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('暂无通知')).toBeInTheDocument()
  })

  it('should render notification type labels', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('每日运势')).toBeInTheDocument()
    expect(screen.getByText('日记提醒')).toBeInTheDocument()
    expect(screen.getByText('活动通知')).toBeInTheDocument()
  })

  it('should call markAsRead when read button is clicked', async () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    const readButtons = screen.getAllByTitle('标记已读')
    fireEvent.click(readButtons[0])
    await waitFor(() => {
      expect(mockStoreData.markAsRead).toHaveBeenCalledWith(1)
    })
  })

  it('should render unread count in header', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('2 未读')).toBeInTheDocument()
  })

  it('should close dropdown when close button is clicked', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('通知')).toBeInTheDocument()
    
    // Find the close button by its X icon
    const closeBtn = screen.getAllByRole('button').find(btn => btn.querySelector('[data-testid="x-icon"]'))
    expect(closeBtn).toBeDefined()
    if (closeBtn) {
      fireEvent.click(closeBtn)
    }
  })

  it('should render "查看会员中心" link when notifications exist', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('查看会员中心 →')).toBeInTheDocument()
  })

  it('should not render "查看会员中心" when no notifications', () => {
    mockStoreData.notifications = []
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.queryByText('查看会员中心 →')).not.toBeInTheDocument()
  })

  it('should render notification body text', () => {
    render(<NotificationBell />)
    fireEvent.click(screen.getByLabelText(/通知/))
    expect(screen.getByText('点击查看今日穿搭建议')).toBeInTheDocument()
    expect(screen.getByText('坚持记录，提升穿搭品味')).toBeInTheDocument()
  })
})
