import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useUserStore } from '@/store/user'

// Mock @/lib/api
vi.mock('@/lib/api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getCurrentUser: vi.fn(),
  updateUserBazi: vi.fn(),
  updateProfile: vi.fn(),
  initAuthToken: vi.fn(),
}))

import { login as apiLogin, register as apiRegister, logout as apiLogout, getCurrentUser, updateUserBazi, updateProfile } from '@/lib/api'

const mockUser = {
  id: 1,
  user_code: 'U001',
  phone: '13800138000',
  nickname: 'TestUser',
  gender: '男',
}

describe('useUserStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useUserStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    localStorage.clear()
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useUserStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('login', () => {
    it('should login successfully with phone', async () => {
      vi.mocked(apiLogin).mockResolvedValue({
        access_token: 'token123',
        token_type: 'bearer',
        expires_in: 3600,
        user: mockUser,
      })

      await useUserStore.getState().login('13800138000', 'password123')

      expect(apiLogin).toHaveBeenCalledWith({ phone: '13800138000', password: 'password123' })
      const state = useUserStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('should set error on login failure', async () => {
      vi.mocked(apiLogin).mockRejectedValue(new Error('密码错误'))

      await expect(useUserStore.getState().login('13800138000', 'wrong')).rejects.toThrow('密码错误')

      const state = useUserStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBe('密码错误')
    })

    it('should set generic error message for non-Error throws', async () => {
      vi.mocked(apiLogin).mockRejectedValue('unknown error')

      await expect(useUserStore.getState().login('13800138000', 'wrong')).rejects.toBe('unknown error')

      const state = useUserStore.getState()
      expect(state.error).toBe('登录失败')
    })
  })

  describe('loginWithEmail', () => {
    it('should login successfully with email', async () => {
      vi.mocked(apiLogin).mockResolvedValue({
        access_token: 'token123',
        token_type: 'bearer',
        expires_in: 3600,
        user: mockUser,
      })

      await useUserStore.getState().loginWithEmail('test@test.com', 'password123')

      expect(apiLogin).toHaveBeenCalledWith({ email: 'test@test.com', password: 'password123' })
      const state = useUserStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
    })

    it('should set error on email login failure', async () => {
      vi.mocked(apiLogin).mockRejectedValue(new Error('邮箱不存在'))

      await expect(useUserStore.getState().loginWithEmail('test@test.com', 'wrong')).rejects.toThrow('邮箱不存在')

      const state = useUserStore.getState()
      expect(state.error).toBe('邮箱不存在')
    })
  })

  describe('register', () => {
    it('should register successfully', async () => {
      vi.mocked(apiRegister).mockResolvedValue({
        access_token: 'token123',
        token_type: 'bearer',
        expires_in: 3600,
        user: mockUser,
      })

      await useUserStore.getState().register({
        phone: '13800138000',
        password: 'password123',
        nickname: 'TestUser',
      })

      expect(apiRegister).toHaveBeenCalledWith({
        phone: '13800138000',
        password: 'password123',
        nickname: 'TestUser',
      })
      const state = useUserStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on register failure', async () => {
      vi.mocked(apiRegister).mockRejectedValue(new Error('手机号已注册'))

      await expect(useUserStore.getState().register({
        phone: '13800138000',
        password: 'password123',
      })).rejects.toThrow('手机号已注册')

      const state = useUserStore.getState()
      expect(state.error).toBe('手机号已注册')
    })
  })

  describe('logout', () => {
    it('should logout successfully', async () => {
      useUserStore.setState({ user: mockUser, isAuthenticated: true })
      vi.mocked(apiLogout).mockResolvedValue(undefined)

      await useUserStore.getState().logout()

      const state = useUserStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })

    it('should clear state even if apiLogout fails', async () => {
      useUserStore.setState({ user: mockUser, isAuthenticated: true })
      vi.mocked(apiLogout).mockRejectedValue(new Error('Network error'))

      await expect(useUserStore.getState().logout()).rejects.toThrow('Network error')

      const state = useUserStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('fetchUserInfo', () => {
    it('should fetch user info successfully', async () => {
      vi.mocked(getCurrentUser).mockResolvedValue(mockUser)

      await useUserStore.getState().fetchUserInfo()

      const state = useUserStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isAuthenticated).toBe(true)
    })

    it('should clear user on fetch failure', async () => {
      vi.mocked(getCurrentUser).mockRejectedValue(new Error('Unauthorized'))

      await useUserStore.getState().fetchUserInfo()

      const state = useUserStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })
  })

  describe('updateBazi', () => {
    it('should update bazi successfully', async () => {
      const updatedUser = { ...mockUser, bazi: { day_master: '甲' } as any }
      vi.mocked(updateUserBazi).mockResolvedValue(updatedUser)

      const baziRequest = {
        birth_year: 1990,
        birth_month: 5,
        birth_day: 15,
        birth_hour: 8,
        gender: '男' as const,
      }

      await useUserStore.getState().updateBazi(baziRequest)

      expect(updateUserBazi).toHaveBeenCalledWith(baziRequest)
      const state = useUserStore.getState()
      expect(state.user).toEqual(updatedUser)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on update bazi failure', async () => {
      vi.mocked(updateUserBazi).mockRejectedValue(new Error('更新八字失败'))

      await expect(useUserStore.getState().updateBazi({
        birth_year: 1990,
        birth_month: 5,
        birth_day: 15,
        birth_hour: 8,
        gender: '男',
      })).rejects.toThrow('更新八字失败')

      const state = useUserStore.getState()
      expect(state.error).toBe('更新八字失败')
    })
  })

  describe('updateProfile', () => {
    it('should update profile successfully', async () => {
      const updatedUser = { ...mockUser, nickname: 'NewName' }
      vi.mocked(updateProfile).mockResolvedValue(updatedUser)

      const result = await useUserStore.getState().updateProfile({ nickname: 'NewName' })

      expect(updateProfile).toHaveBeenCalledWith({ nickname: 'NewName' })
      expect(result).toEqual(updatedUser)
      const state = useUserStore.getState()
      expect(state.user).toEqual(updatedUser)
      expect(state.isLoading).toBe(false)
    })

    it('should set error on update profile failure', async () => {
      vi.mocked(updateProfile).mockRejectedValue(new Error('更新资料失败'))

      await expect(useUserStore.getState().updateProfile({ nickname: 'NewName' })).rejects.toThrow('更新资料失败')

      const state = useUserStore.getState()
      expect(state.error).toBe('更新资料失败')
    })
  })

  describe('clearError', () => {
    it('should clear error', () => {
      useUserStore.setState({ error: 'some error' })
      useUserStore.getState().clearError()
      expect(useUserStore.getState().error).toBeNull()
    })
  })

  describe('initAuth', () => {
    it('should clear auth when authenticated but no token', () => {
      useUserStore.setState({ isAuthenticated: true, user: mockUser })
      localStorage.removeItem('wuxing_token')

      useUserStore.getState().initAuth()

      const state = useUserStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
    })

    it('should set authenticated when token exists but not authenticated', async () => {
      useUserStore.setState({ isAuthenticated: false })
      localStorage.setItem('wuxing_token', 'token123')
      vi.mocked(getCurrentUser).mockResolvedValue(mockUser)

      useUserStore.getState().initAuth()

      // initAuth is async - wait for fetchUserInfo to resolve
      await vi.waitFor(() => {
        const state = useUserStore.getState()
        expect(state.isAuthenticated).toBe(true)
      })
    })

    it('should do nothing when already authenticated and token exists', () => {
      useUserStore.setState({ isAuthenticated: true, user: mockUser })
      localStorage.setItem('wuxing_token', 'token123')

      useUserStore.getState().initAuth()

      const state = useUserStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).toEqual(mockUser)
    })
  })
})
