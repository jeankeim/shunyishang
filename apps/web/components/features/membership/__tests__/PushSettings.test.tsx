import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { PushSettings } from '../PushSettings'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Bell: () => <span data-testid="bell" />,
  Clock: () => <span data-testid="clock" />,
  BookOpen: () => <span data-testid="book" />,
  Sparkles: () => <span data-testid="sparkles" />,
  Megaphone: () => <span data-testid="megaphone" />,
}))

// Configurable mock store
let mockStoreData: any = {}

vi.mock('@/store/membership', () => ({
  useMembershipStore: () => mockStoreData,
}))

const mockPushSettings = {
  enabled: true,
  fortune_push: true,
  fortune_push_time: '08:30:00',
  diary_reminder: false,
  diary_reminder_time: '21:00:00',
  marketing: true,
}

describe('PushSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStoreData = {
      pushSettings: mockPushSettings,
      fetchPushSettings: vi.fn(),
      updatePushSettings: vi.fn(),
    }
  })

  it('should call fetchPushSettings on mount', () => {
    render(<PushSettings />)
    expect(mockStoreData.fetchPushSettings).toHaveBeenCalled()
  })

  it('should show loading skeleton when pushSettings is null', () => {
    mockStoreData.pushSettings = null
    const { container } = render(<PushSettings />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('should render all setting labels', () => {
    render(<PushSettings />)
    expect(screen.getByText('推送通知')).toBeInTheDocument()
    expect(screen.getByText('每日运势')).toBeInTheDocument()
    expect(screen.getByText('日记提醒')).toBeInTheDocument()
    expect(screen.getByText('活动通知')).toBeInTheDocument()
  })

  it('should render setting descriptions', () => {
    render(<PushSettings />)
    expect(screen.getByText('接收所有推送通知')).toBeInTheDocument()
    expect(screen.getByText(/每天 08:30 推送运势/)).toBeInTheDocument()
    expect(screen.getByText(/每天 21:00 提醒记录穿搭/)).toBeInTheDocument()
    expect(screen.getByText('接收优惠活动和功能更新')).toBeInTheDocument()
  })

  it('should render toggle switches', () => {
    render(<PushSettings />)
    const toggles = screen.getAllByRole('button')
    expect(toggles).toHaveLength(4)
  })

  it('should show enabled state for toggle that is on', () => {
    render(<PushSettings />)
    const toggles = screen.getAllByRole('button')
    // First toggle (enabled) should have bg-emerald-500
    expect(toggles[0].className).toContain('bg-emerald-500')
    // Third toggle (diary_reminder=false) should have bg-stone-300
    expect(toggles[2].className).toContain('bg-stone-300')
  })

  it('should call updatePushSettings when toggle is clicked', () => {
    render(<PushSettings />)
    const toggles = screen.getAllByRole('button')
    fireEvent.click(toggles[0]) // Toggle enabled
    expect(mockStoreData.updatePushSettings).toHaveBeenCalledWith({ enabled: false })
  })

  it('should call updatePushSettings with correct key for each toggle', () => {
    render(<PushSettings />)
    const toggles = screen.getAllByRole('button')
    
    fireEvent.click(toggles[1]) // fortune_push
    expect(mockStoreData.updatePushSettings).toHaveBeenCalledWith({ fortune_push: false })
    
    fireEvent.click(toggles[2]) // diary_reminder
    expect(mockStoreData.updatePushSettings).toHaveBeenCalledWith({ diary_reminder: true })
    
    fireEvent.click(toggles[3]) // marketing
    expect(mockStoreData.updatePushSettings).toHaveBeenCalledWith({ marketing: false })
  })

  it('should use default times when not set', () => {
    mockStoreData.pushSettings = {
      ...mockPushSettings,
      fortune_push_time: undefined,
      diary_reminder_time: undefined,
    }
    render(<PushSettings />)
    expect(screen.getByText(/每天 08:00 推送运势/)).toBeInTheDocument()
    expect(screen.getByText(/每天 21:00 提醒记录穿搭/)).toBeInTheDocument()
  })
})
