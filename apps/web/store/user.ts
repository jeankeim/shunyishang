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

        if (state.isAuthenticated && !token) {
          set({ isAuthenticated: false, user: null })
        } else if (token && !state.isAuthenticated) {
          set({ isAuthenticated: true })
          get().fetchUserInfo()
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
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => {
        console.log('[Zustand] 开始恢复状态...')
        return (state, error) => {
          if (error) {
            console.error('[Zustand] 状态恢复失败:', error)
            // 清除损坏的localStorage数据
            if (typeof window !== 'undefined') {
              localStorage.removeItem('wuxing-user-storage')
            }
          } else {
            console.log('[Zustand] 状态恢复成功:', state)
          }
          initAuthToken()
          const token = typeof window !== 'undefined' ? localStorage.getItem('wuxing_token') : null
          console.log('[Zustand] Token状态:', token ? '存在' : '不存在')
        }
      },
    }
  )
)
