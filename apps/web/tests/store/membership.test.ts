import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useMembershipStore } from '@/store/membership'

vi.mock('@/lib/api', () => ({
  getPushSettings: vi.fn(),
  updatePushSettings: vi.fn(),
  getPushHistory: vi.fn(),
  getUnreadCount: vi.fn(),
  markNotificationRead: vi.fn(),
}))

import {
  getPushSettings,
  updatePushSettings,
  getPushHistory,
  getUnreadCount,
  markNotificationRead,
} from '@/lib/api'

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

  describe('membership functions (个人备案版: no-op)', () => {
    it('fetchStatus should be no-op', async () => {
      await useMembershipStore.getState().fetchStatus()
      expect(useMembershipStore.getState().status).toBeNull()
    })

    it('fetchPlans should be no-op', async () => {
      await useMembershipStore.getState().fetchPlans()
      expect(useMembershipStore.getState().plans).toEqual([])
    })

    it('subscribe should be no-op', async () => {
      await useMembershipStore.getState().subscribe('monthly', 'wechat')
      // no error thrown, no state change
    })

    it('cancel should be no-op', async () => {
      await useMembershipStore.getState().cancel(123)
      // no error thrown, no state change
    })

    it('upgrade should be no-op', async () => {
      await useMembershipStore.getState().upgrade('yearly')
      // no error thrown, no state change
    })

    it('renew should be no-op', async () => {
      await useMembershipStore.getState().renew('alipay')
      // no error thrown, no state change
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
