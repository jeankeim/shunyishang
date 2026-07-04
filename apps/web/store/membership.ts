/**
 * 会员状态管理
 */
import { create } from 'zustand'
import type { MembershipStatus, PlanInfo, PushSettings, PushNotification } from '@/types'
// 个人备案版：会员 API 已禁用，保留推送相关功能
import {
  // getMembershipStatus,   // 已禁用
  // getPlans,              // 已禁用
  // subscribe as apiSubscribe,           // 已禁用
  // cancelSubscription as apiCancelSubscription,  // 已禁用
  // upgradeMembership as apiUpgrade,     // 已禁用
  // renewMembership as apiRenew,         // 已禁用
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
    // 个人备案版：会员功能已禁用
  },

  fetchPlans: async () => {
    // 个人备案版：会员功能已禁用
  },

  subscribe: async (_plan: string, _paymentMethod: string) => {
    // 个人备案版：会员功能已禁用
  },

  cancel: async (_subscriptionId: number) => {
    // 个人备案版：会员功能已禁用
  },

  upgrade: async (_newPlan: string) => {
    // 个人备案版：会员功能已禁用
  },

  renew: async (_paymentMethod: string) => {
    // 个人备案版：会员功能已禁用
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
