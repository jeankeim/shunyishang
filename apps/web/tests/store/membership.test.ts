import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useMembershipStore } from '@/store/membership'

vi.mock('@/lib/api', () => ({
  getMembershipStatus: vi.fn(),
  getPlans: vi.fn(),
  subscribe: vi.fn(),
  cancelSubscription: vi.fn(),
  upgradeMembership: vi.fn(),
  renewMembership: vi.fn(),
  getPushSettings: vi.fn(),
  updatePushSettings: vi.fn(),
  getPushHistory: vi.fn(),
  getUnreadCount: vi.fn(),
  markNotificationRead: vi.fn(),
}))

import {
  getMembershipStatus,
  getPlans,
  subscribe,
  cancelSubscription,
  upgradeMembership,
  renewMembership,
  getPushSettings,
  updatePushSettings,
  getPushHistory,
  getUnreadCount,
  markNotificationRead,
} from '@/lib/api'

const mockStatus = {
  plan: 'free' as const,
  status: 'active' as const,
  auto_renew: false,
}

const mockPlans = {
  plans: [
    {
      name: '月度会员',
      plan_key: 'monthly',
      price_monthly: 29,
      price_yearly: 299,
      features: ['无限推荐'],
      limits: {},
    },
  ],
}

const mockPushSettings = {
  enabled: true,
  fortune_push: true,
  fortune_push_time: '08:00',
  diary_reminder: false,
  diary_reminder_time: '20:00',
  marketing: false,
  vibrate: true,
}

describe('useMembershipStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useMembershipStore.setState({
      status: null,
      plans: [],
      pushSettings: null,
      notifications: [],
      unreadCount: 0,
      isLoading: false,
      error: null,
    })
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useMembershipStore.getState()
      expect(state.status).toBeNull()
      expect(state.plans).toEqual([])
      expect(state.pushSettings).toBeNull()
      expect(state.notifications).toEqual([])
      expect(state.unreadCount).toBe(0)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('fetchStatus', () => {
    it('should fetch membership status successfully', async () => {
      vi.mocked(getMembershipStatus).mockResolvedValue(mockStatus)

      await useMembershipStore.getState().fetchStatus()

      expect(getMembershipStatus).toHaveBeenCalled()
      expect(useMembershipStore.getState().status).toEqual(mockStatus)
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getMembershipStatus).mockRejectedValue(new Error('获取失败'))

      await useMembershipStore.getState().fetchStatus()

      expect(useMembershipStore.getState().error).toBe('获取失败')
    })
  })

  describe('fetchPlans', () => {
    it('should fetch plans successfully', async () => {
      vi.mocked(getPlans).mockResolvedValue(mockPlans)

      await useMembershipStore.getState().fetchPlans()

      expect(getPlans).toHaveBeenCalled()
      expect(useMembershipStore.getState().plans).toEqual(mockPlans.plans)
    })

    it('should handle null plans in response', async () => {
      vi.mocked(getPlans).mockResolvedValue({ plans: null })

      await useMembershipStore.getState().fetchPlans()

      expect(useMembershipStore.getState().plans).toEqual([])
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getPlans).mockRejectedValue(new Error('获取套餐失败'))

      await useMembershipStore.getState().fetchPlans()

      expect(useMembershipStore.getState().error).toBe('获取套餐失败')
    })
  })

  describe('subscribe', () => {
    it('should subscribe successfully and refresh status', async () => {
      vi.mocked(subscribe).mockResolvedValue({})
      vi.mocked(getMembershipStatus).mockResolvedValue(mockStatus)

      await useMembershipStore.getState().subscribe('monthly', 'wechat')

      expect(subscribe).toHaveBeenCalledWith({ plan: 'monthly', payment_method: 'wechat' })
      expect(getMembershipStatus).toHaveBeenCalled()
      expect(useMembershipStore.getState().isLoading).toBe(false)
    })

    it('should set error on subscribe failure', async () => {
      vi.mocked(subscribe).mockRejectedValue(new Error('订阅失败'))

      await expect(useMembershipStore.getState().subscribe('monthly', 'wechat')).rejects.toThrow('订阅失败')

      expect(useMembershipStore.getState().error).toBe('订阅失败')
      expect(useMembershipStore.getState().isLoading).toBe(false)
    })
  })

  describe('cancel', () => {
    it('should cancel subscription successfully', async () => {
      vi.mocked(cancelSubscription).mockResolvedValue({})
      vi.mocked(getMembershipStatus).mockResolvedValue(mockStatus)

      await useMembershipStore.getState().cancel(123)

      expect(cancelSubscription).toHaveBeenCalledWith(123)
      expect(getMembershipStatus).toHaveBeenCalled()
    })

    it('should set error on cancel failure', async () => {
      vi.mocked(cancelSubscription).mockRejectedValue(new Error('取消失败'))

      await expect(useMembershipStore.getState().cancel(123)).rejects.toThrow('取消失败')

      expect(useMembershipStore.getState().error).toBe('取消失败')
    })
  })

  describe('upgrade', () => {
    it('should upgrade successfully', async () => {
      vi.mocked(upgradeMembership).mockResolvedValue({})
      vi.mocked(getMembershipStatus).mockResolvedValue(mockStatus)

      await useMembershipStore.getState().upgrade('yearly')

      expect(upgradeMembership).toHaveBeenCalledWith({ new_plan: 'yearly' })
      expect(getMembershipStatus).toHaveBeenCalled()
    })

    it('should set error on upgrade failure', async () => {
      vi.mocked(upgradeMembership).mockRejectedValue(new Error('升级失败'))

      await expect(useMembershipStore.getState().upgrade('yearly')).rejects.toThrow('升级失败')

      expect(useMembershipStore.getState().error).toBe('升级失败')
    })
  })

  describe('renew', () => {
    it('should renew successfully', async () => {
      vi.mocked(renewMembership).mockResolvedValue({})
      vi.mocked(getMembershipStatus).mockResolvedValue(mockStatus)

      await useMembershipStore.getState().renew('alipay')

      expect(renewMembership).toHaveBeenCalledWith({ payment_method: 'alipay' })
      expect(getMembershipStatus).toHaveBeenCalled()
    })

    it('should set error on renew failure', async () => {
      vi.mocked(renewMembership).mockRejectedValue(new Error('续费失败'))

      await expect(useMembershipStore.getState().renew('alipay')).rejects.toThrow('续费失败')

      expect(useMembershipStore.getState().error).toBe('续费失败')
    })
  })

  describe('fetchPushSettings', () => {
    it('should fetch push settings successfully', async () => {
      vi.mocked(getPushSettings).mockResolvedValue(mockPushSettings)

      await useMembershipStore.getState().fetchPushSettings()

      expect(useMembershipStore.getState().pushSettings).toEqual(mockPushSettings)
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getPushSettings).mockRejectedValue(new Error('获取推送设置失败'))

      await useMembershipStore.getState().fetchPushSettings()

      expect(useMembershipStore.getState().error).toBe('获取推送设置失败')
    })
  })

  describe('updatePushSettings', () => {
    it('should update push settings successfully', async () => {
      const updated = { ...mockPushSettings, vibrate: false }
      vi.mocked(updatePushSettings).mockResolvedValue(updated)

      await useMembershipStore.getState().updatePushSettings({ vibrate: false })

      expect(updatePushSettings).toHaveBeenCalledWith({ vibrate: false })
      expect(useMembershipStore.getState().pushSettings).toEqual(updated)
    })

    it('should set error on update failure', async () => {
      vi.mocked(updatePushSettings).mockRejectedValue(new Error('更新失败'))

      await expect(useMembershipStore.getState().updatePushSettings({})).rejects.toThrow('更新失败')

      expect(useMembershipStore.getState().error).toBe('更新失败')
    })
  })

  describe('fetchNotifications', () => {
    it('should fetch notifications successfully', async () => {
      const mockNotifs = [
        { id: 1, type: 'fortune', title: '今日运势', data: {}, sent_at: '2024-01-15T08:00:00Z' },
      ]
      vi.mocked(getPushHistory).mockResolvedValue({ notifications: mockNotifs, total: 1, page: 1, size: 50 })

      await useMembershipStore.getState().fetchNotifications()

      expect(getPushHistory).toHaveBeenCalledWith(1, 50)
      expect(useMembershipStore.getState().notifications).toEqual(mockNotifs)
    })

    it('should handle null notifications in response', async () => {
      vi.mocked(getPushHistory).mockResolvedValue({ notifications: null })

      await useMembershipStore.getState().fetchNotifications()

      expect(useMembershipStore.getState().notifications).toEqual([])
    })

    it('should set error on fetch failure', async () => {
      vi.mocked(getPushHistory).mockRejectedValue(new Error('获取推送历史失败'))

      await useMembershipStore.getState().fetchNotifications()

      expect(useMembershipStore.getState().error).toBe('获取推送历史失败')
    })
  })

  describe('markAsRead', () => {
    it('should mark notification as read', async () => {
      useMembershipStore.setState({
        notifications: [
          { id: 1, type: 'fortune', title: 'Test', data: {}, sent_at: '2024-01-15', read_at: undefined },
          { id: 2, type: 'diary', title: 'Test2', data: {}, sent_at: '2024-01-15', read_at: undefined },
        ],
        unreadCount: 2,
      })
      vi.mocked(markNotificationRead).mockResolvedValue(undefined)

      await useMembershipStore.getState().markAsRead(1)

      expect(markNotificationRead).toHaveBeenCalledWith(1)
      const state = useMembershipStore.getState()
      expect(state.notifications[0].read_at).toBeDefined()
      expect(state.notifications[1].read_at).toBeUndefined()
      expect(state.unreadCount).toBe(1)
    })

    it('should not go below 0 unread count', async () => {
      useMembershipStore.setState({
        notifications: [],
        unreadCount: 0,
      })
      vi.mocked(markNotificationRead).mockResolvedValue(undefined)

      await useMembershipStore.getState().markAsRead(1)

      expect(useMembershipStore.getState().unreadCount).toBe(0)
    })

    it('should not set error on failure (silent fail)', async () => {
      vi.mocked(markNotificationRead).mockRejectedValue(new Error('Failed'))

      await useMembershipStore.getState().markAsRead(1)

      expect(useMembershipStore.getState().error).toBeNull()
    })
  })

  describe('fetchUnreadCount', () => {
    it('should fetch unread count successfully', async () => {
      vi.mocked(getUnreadCount).mockResolvedValue({ count: 5 })

      await useMembershipStore.getState().fetchUnreadCount()

      expect(getUnreadCount).toHaveBeenCalled()
      expect(useMembershipStore.getState().unreadCount).toBe(5)
    })

    it('should not set error on failure (silent fail)', async () => {
      vi.mocked(getUnreadCount).mockRejectedValue(new Error('Failed'))

      await useMembershipStore.getState().fetchUnreadCount()

      expect(useMembershipStore.getState().error).toBeNull()
    })
  })

  describe('clearError', () => {
    it('should clear error', () => {
      useMembershipStore.setState({ error: 'some error' })
      useMembershipStore.getState().clearError()
      expect(useMembershipStore.getState().error).toBeNull()
    })
  })
})
