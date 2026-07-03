/**
 * 会员状态管理
 */
import { create } from 'zustand'
import type { MembershipStatus, PlanInfo, PushSettings, PushNotification } from '@/types'
import {
  getMembershipStatus,
  getPlans,
  subscribe as apiSubscribe,
  cancelSubscription as apiCancelSubscription,
  upgradeMembership as apiUpgrade,
  renewMembership as apiRenew,
  getPushSettings,
  updatePushSettings as apiUpdatePushSettings,
  getPushHistory,
  getUnreadCount,
  markNotificationRead as apiMarkRead,
} from '@/lib/api'

interface MembershipState {
  status: MembershipStatus | null
  plans: PlanInfo[]
  pushSettings: PushSettings | null
  notifications: PushNotification[]
  unreadCount: number
  isLoading: boolean
  error: string | null

  fetchStatus: () => Promise<void>
  fetchPlans: () => Promise<void>
  subscribe: (plan: string, paymentMethod: string) => Promise<void>
  cancel: (subscriptionId: number) => Promise<void>
  upgrade: (newPlan: string) => Promise<void>
  renew: (paymentMethod: string) => Promise<void>
  fetchPushSettings: () => Promise<void>
  updatePushSettings: (data: Partial<PushSettings>) => Promise<void>
  fetchNotifications: () => Promise<void>
  markAsRead: (id: number) => Promise<void>
  fetchUnreadCount: () => Promise<void>
  clearError: () => void
}

export const useMembershipStore = create<MembershipState>()((set, get) => ({
  status: null,
  plans: [],
  pushSettings: null,
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  fetchStatus: async () => {
    try {
      const data = await getMembershipStatus()
      set({ status: data })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '获取会员状态失败' })
    }
  },

  fetchPlans: async () => {
    try {
      const data = await getPlans()
      set({ plans: data.plans || [] })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '获取套餐失败' })
    }
  },

  subscribe: async (plan: string, paymentMethod: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiSubscribe({ plan, payment_method: paymentMethod })
      await get().fetchStatus()
      set({ isLoading: false })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '订阅失败', isLoading: false })
      throw error
    }
  },

  cancel: async (subscriptionId: number) => {
    set({ isLoading: true, error: null })
    try {
      await apiCancelSubscription(subscriptionId)
      await get().fetchStatus()
      set({ isLoading: false })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '取消失败', isLoading: false })
      throw error
    }
  },

  upgrade: async (newPlan: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiUpgrade({ new_plan: newPlan })
      await get().fetchStatus()
      set({ isLoading: false })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '升级失败', isLoading: false })
      throw error
    }
  },

  renew: async (paymentMethod: string) => {
    set({ isLoading: true, error: null })
    try {
      await apiRenew({ payment_method: paymentMethod })
      await get().fetchStatus()
      set({ isLoading: false })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '续费失败', isLoading: false })
      throw error
    }
  },

  fetchPushSettings: async () => {
    try {
      const data = await getPushSettings()
      set({ pushSettings: data })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '获取推送设置失败' })
    }
  },

  updatePushSettings: async (data: Partial<PushSettings>) => {
    try {
      const result = await apiUpdatePushSettings(data)
      set({ pushSettings: result })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '更新推送设置失败' })
      throw error
    }
  },

  fetchNotifications: async () => {
    try {
      const data = await getPushHistory(1, 50)
      set({ notifications: data.notifications || [] })
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '获取推送历史失败' })
    }
  },

  markAsRead: async (id: number) => {
    try {
      await apiMarkRead(id)
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read_at: new Date().toISOString() } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }))
    } catch (error) {
      // 静默失败
    }
  },

  fetchUnreadCount: async () => {
    try {
      const data = await getUnreadCount()
      set({ unreadCount: data.count })
    } catch {
      // 静默失败
    }
  },

  clearError: () => set({ error: null }),
}))
