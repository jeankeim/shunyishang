/**
 * 用户状态管理
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  User,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getCurrentUser,
  updateUserBazi,
  updateProfile,
  initAuthToken,
} from '@/lib/api'
import type { BaziCalculateRequest, UpdateProfileRequest } from '@/lib/api'

interface UserState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  login: (phone: string, password: string) => Promise<void>
  loginWithEmail: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  fetchUserInfo: () => Promise<void>
  updateBazi: (data: BaziCalculateRequest) => Promise<void>
  updateProfile: (data: UpdateProfileRequest) => Promise<User>
  clearError: () => void
  initAuth: () => void
}

interface RegisterData {
  phone?: string
  email?: string
  password: string
  nickname?: string
  gender?: string
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      initAuth: () => {
        initAuthToken()
        const token = typeof window !== 'undefined' ? localStorage.getItem('wuxing_token') : null
        const state = get()

        if (!token) {
          // 无 token 但 isAuthenticated 为 true → 清除状态
          if (state.isAuthenticated) {
            set({ isAuthenticated: false, user: null })
          }
        } else {
          // 有 token 时始终验证有效性（避免过期 token 导致 401）
          // 先设为 loading 状态，防止组件在验证完成前发起 API 请求
          set({ isLoading: true })
          get().fetchUserInfo().finally(() => {
            set({ isLoading: false })
          })
        }
      },

      login: async (phone: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiLogin({ phone, password })
          set({ user: response.user, isAuthenticated: true, isLoading: false })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '登录失败', isLoading: false })
          throw error
        }
      },

      loginWithEmail: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiLogin({ email, password })
          set({ user: response.user, isAuthenticated: true, isLoading: false })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '登录失败', isLoading: false })
          throw error
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiRegister(data)
          set({ user: response.user, isAuthenticated: true, isLoading: false })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '注册失败', isLoading: false })
          throw error
        }
      },

      logout: async () => {
        set({ isLoading: true })
        try {
          await apiLogout()
        } finally {
          set({ user: null, isAuthenticated: false, isLoading: false, error: null })
        }
      },

      fetchUserInfo: async () => {
        try {
          const user = await getCurrentUser()
          set({ user, isAuthenticated: true })
        } catch {
          // token 无效/过期，清除本地凭证
          if (typeof window !== 'undefined') {
            localStorage.removeItem('wuxing_token')
          }
          set({ user: null, isAuthenticated: false })
        }
      },

      updateBazi: async (data: BaziCalculateRequest) => {
        set({ isLoading: true, error: null })
        try {
          const user = await updateUserBazi(data)
          set({ user, isLoading: false })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '更新八字失败', isLoading: false })
          throw error
        }
      },

      updateProfile: async (data: UpdateProfileRequest) => {
        set({ isLoading: true, error: null })
        try {
          const updatedUser = await updateProfile(data)
          set({ user: updatedUser, isLoading: false })
          return updatedUser
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '更新资料失败', isLoading: false })
          throw error
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'wuxing-user-storage',
      skipHydration: true,
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => {
        return (state, error) => {
          if (error) {
            console.error('[Zustand] 状态恢复失败:', error)
            // 清除损坏的localStorage数据
            if (typeof window !== 'undefined') {
              localStorage.removeItem('wuxing-user-storage')
            }
          }
          initAuthToken()
        }
      },
    }
  )
)
