import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockFetch = vi.fn()
global.fetch = mockFetch as any

import {
  setAuthToken,
  getAuthToken,
  initAuthToken,
  checkHealth,
  calculateBazi,
  register,
  login,
  getCurrentUser,
  updateUserBazi,
  updateProfile,
  getUserProfile,
  logout,
  getWardrobeItems,
  addWardrobeItem,
  updateWardrobeItem,
  deleteWardrobeItem,
  previewTagging,
  submitFeedback,
  getDiaries,
  createDiary,
  getDiaryById,
  updateDiary,
  deleteDiary,
  getDiaryCalendar,
  getDiaryStats,
  triggerDiaryReview,
  getTodayFortune,
  getFortuneByDate,
  generateFortune,
  getMembershipStatus,
  getPlans,
  subscribe,
  cancelSubscription,
  upgradeMembership,
  renewMembership,
  getQuota,
  getPushSettings,
  updatePushSettings,
  getPushHistory,
  getUnreadCount,
  markNotificationRead,
  streamRecommendation,
} from '@/lib/api'

function mockResponse(data: any, ok = true, status = 200) {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(data),
    text: vi.fn().mockResolvedValue(JSON.stringify(data)),
    body: null,
  } as any
}

describe('lib/api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    setAuthToken(null)
  })

  describe('Token Management', () => {
    it('setAuthToken should store token in localStorage', () => {
      setAuthToken('test-token')
      expect(localStorage.getItem('wuxing_token')).toBe('test-token')
    })

    it('setAuthToken(null) should remove token from localStorage', () => {
      localStorage.setItem('wuxing_token', 'test-token')
      setAuthToken(null)
      expect(localStorage.getItem('wuxing_token')).toBeNull()
    })

    it('getAuthToken should return token from memory', () => {
      setAuthToken('memory-token')
      expect(getAuthToken()).toBe('memory-token')
    })

    it('getAuthToken should return token from localStorage if not in memory', () => {
      localStorage.setItem('wuxing_token', 'storage-token')
      initAuthToken()
      expect(getAuthToken()).toBe('storage-token')
    })

    it('initAuthToken should read token from localStorage', () => {
      localStorage.setItem('wuxing_token', 'init-token')
      initAuthToken()
      expect(getAuthToken()).toBe('init-token')
    })

    it('getAuthToken should return null when no token', () => {
      expect(getAuthToken()).toBeNull()
    })
  })

  describe('checkHealth', () => {
    it('should return health status on success', async () => {
      mockFetch.mockReturnValue(mockResponse({ status: 'ok', db: 'connected' }))
      const result = await checkHealth()
      expect(result).toEqual({ status: 'ok', db: 'connected' })
    })

    it('should throw on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 500))
      await expect(checkHealth()).rejects.toThrow('Health check failed')
    })
  })

  describe('calculateBazi', () => {
    it('should return bazi calculation on success', async () => {
      const baziResult = {
        pillars: { year: '甲子', month: '乙丑', day: '丙寅', hour: '丁卯' },
        eight_chars: ['甲', '子', '乙', '丑', '丙', '寅', '丁', '卯'],
        five_elements_count: { '金': 1, '木': 2, '水': 1, '火': 2, '土': 2 },
        dominant_element: '木',
        lacking_element: null,
        day_master: '丙',
        month_element: '火',
        suggested_elements: ['木'],
        avoid_elements: ['金'],
        reasoning: 'test',
      }
      mockFetch.mockReturnValue(mockResponse(baziResult))
      const result = await calculateBazi({
        birth_year: 1990,
        birth_month: 5,
        birth_day: 15,
        birth_hour: 8,
        gender: '男',
      })
      expect(result).toEqual(baziResult)
    })

    it('should throw with detail on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({ detail: '无效日期' }, false, 400))
      await expect(calculateBazi({
        birth_year: 1990, birth_month: 5, birth_day: 15, birth_hour: 8, gender: '男',
      })).rejects.toThrow('无效日期')
    })
  })

  describe('register', () => {
    it('should register and store token', async () => {
      const authResponse = {
        access_token: 'reg-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 1, user_code: 'U001' },
      }
      mockFetch.mockReturnValue(mockResponse(authResponse))
      const result = await register({ phone: '13800138000', password: 'pass' })
      expect(result).toEqual(authResponse)
      expect(localStorage.getItem('wuxing_token')).toBe('reg-token')
    })

    it('should throw with detail on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({ detail: '手机号已存在' }, false, 400))
      await expect(register({ phone: '13800138000', password: 'pass' })).rejects.toThrow('手机号已存在')
    })
  })

  describe('login', () => {
    it('should login with phone and store token', async () => {
      const authResponse = {
        access_token: 'login-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 1, user_code: 'U001' },
      }
      mockFetch.mockReturnValue(mockResponse(authResponse))
      const result = await login({ phone: '13800138000', password: 'pass' })
      expect(result).toEqual(authResponse)
      expect(localStorage.getItem('wuxing_token')).toBe('login-token')

      // Verify URLSearchParams body
      const callArgs = mockFetch.mock.calls[0]
      const body = callArgs[1].body
      expect(body.toString()).toContain('username=13800138000')
      expect(body.toString()).toContain('password=pass')
    })

    it('should login with email', async () => {
      const authResponse = {
        access_token: 'login-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 1 },
      }
      mockFetch.mockReturnValue(mockResponse(authResponse))
      await login({ email: 'test@test.com', password: 'pass' })
      const callArgs = mockFetch.mock.calls[0]
      const body = callArgs[1].body
      expect(body.toString()).toContain('username=test%40test.com')
    })

    it('should throw with detail on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({ detail: '密码错误' }, false, 401))
      await expect(login({ phone: '13800138000', password: 'wrong' })).rejects.toThrow('密码错误')
    })
  })

  describe('getCurrentUser', () => {
    it('should return user on success', async () => {
      const user = { id: 1, user_code: 'U001', nickname: 'Test' }
      mockFetch.mockReturnValue(mockResponse(user))
      const result = await getCurrentUser()
      expect(result).toEqual(user)
    })

    it('should throw specific message on 502', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 502))
      await expect(getCurrentUser()).rejects.toThrow('后端服务暂时不可用，请稍后重试')
    })

    it('should throw generic message on other errors', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 401))
      await expect(getCurrentUser()).rejects.toThrow('获取用户信息失败')
    })

    it('should throw network error on TypeError', async () => {
      mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))
      await expect(getCurrentUser()).rejects.toThrow('网络连接失败，请检查后端服务')
    })
  })

  describe('updateUserBazi', () => {
    it('should return updated user on success', async () => {
      const user = { id: 1, bazi: { day_master: '甲' } }
      mockFetch.mockReturnValue(mockResponse(user))
      const result = await updateUserBazi({
        birth_year: 1990, birth_month: 5, birth_day: 15, birth_hour: 8, gender: '男',
      })
      expect(result).toEqual(user)
    })

    it('should throw on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 400))
      await expect(updateUserBazi({
        birth_year: 1990, birth_month: 5, birth_day: 15, birth_hour: 8, gender: '男',
      })).rejects.toThrow('更新八字失败')
    })
  })

  describe('updateProfile', () => {
    it('should return updated user on success', async () => {
      const user = { id: 1, nickname: 'NewName' }
      mockFetch.mockReturnValue(mockResponse(user))
      const result = await updateProfile({ nickname: 'NewName' })
      expect(result).toEqual(user)
    })

    it('should throw with detail on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({ detail: '昵称太长' }, false, 400))
      await expect(updateProfile({ nickname: 'x'.repeat(100) })).rejects.toThrow('昵称太长')
    })
  })

  describe('getUserProfile', () => {
    it('should return profile on success', async () => {
      const profile = { id: 1, nickname: 'Test' }
      mockFetch.mockReturnValue(mockResponse(profile))
      const result = await getUserProfile()
      expect(result).toEqual(profile)
    })

    it('should clear token on 401', async () => {
      setAuthToken('test-token')
      mockFetch.mockReturnValue(mockResponse({}, false, 401))
      await expect(getUserProfile()).rejects.toThrow('获取用户资料失败')
      expect(getAuthToken()).toBeNull()
    })

    it('should throw on other failures', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 500))
      await expect(getUserProfile()).rejects.toThrow('获取用户资料失败')
    })
  })

  describe('logout', () => {
    it('should clear token after logout', async () => {
      setAuthToken('test-token')
      mockFetch.mockReturnValue(mockResponse({}))
      await logout()
      expect(getAuthToken()).toBeNull()
    })

    it('should clear token even if request fails', async () => {
      setAuthToken('test-token')
      mockFetch.mockRejectedValue(new Error('Network error'))
      await expect(logout()).rejects.toThrow('Network error')
      expect(getAuthToken()).toBeNull()
    })
  })

  describe('Wardrobe API', () => {
    it('getWardrobeItems should return items', async () => {
      const response = { items: [], total: 0, element_stats: {} }
      mockFetch.mockReturnValue(mockResponse(response))
      const result = await getWardrobeItems({ category: '上衣', limit: 10 })
      expect(result).toEqual(response)
      expect(mockFetch.mock.calls[0][0]).toContain('category=')
      expect(mockFetch.mock.calls[0][0]).toContain('limit=10')
    })

    it('getWardrobeItems should throw on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 500))
      await expect(getWardrobeItems()).rejects.toThrow('获取衣橱列表失败')
    })

    it('addWardrobeItem should return new item', async () => {
      const item = { id: 1, name: 'T恤', primary_element: '金' }
      mockFetch.mockReturnValue(mockResponse(item))
      const result = await addWardrobeItem({ name: 'T恤', primary_element: '金' })
      expect(result).toEqual(item)
    })

    it('addWardrobeItem should throw with detail on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({ detail: '名称重复' }, false, 400))
      await expect(addWardrobeItem({ name: 'T恤' })).rejects.toThrow('名称重复')
    })

    it('updateWardrobeItem should return updated item', async () => {
      const item = { id: 1, name: 'Updated' }
      mockFetch.mockReturnValue(mockResponse(item))
      const result = await updateWardrobeItem(1, { name: 'Updated' })
      expect(result).toEqual(item)
    })

    it('deleteWardrobeItem should succeed', async () => {
      mockFetch.mockReturnValue(mockResponse({}))
      await deleteWardrobeItem(1)
      expect(mockFetch.mock.calls[0][1].method).toBe('DELETE')
    })

    it('deleteWardrobeItem should throw on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({ detail: '无权限' }, false, 403))
      await expect(deleteWardrobeItem(1)).rejects.toThrow('无权限')
    })

    it('previewTagging should return tagging result', async () => {
      const result = { primary_element: '木', color: 'green', confidence: 0.9, season: [], tags: [] }
      mockFetch.mockReturnValue(mockResponse(result))
      const res = await previewTagging('绿色T恤')
      expect(res).toEqual(result)
    })

    it('submitFeedback should return feedback response', async () => {
      const result = { id: 1, user_id: 1, action: 'like', created_at: '2024-01-01' }
      mockFetch.mockReturnValue(mockResponse(result))
      const res = await submitFeedback({
        item_source: 'wardrobe',
        action: 'like',
      })
      expect(res).toEqual(result)
    })
  })

  describe('Diary API', () => {
    it('getDiaries should return diaries list', async () => {
      const response = { diaries: [], total: 0, page: 1 }
      mockFetch.mockReturnValue(mockResponse(response))
      const result = await getDiaries({ page: 1, size: 10, mood: 'happy' })
      expect(result).toEqual(response)
    })

    it('getDiaries should throw on failure', async () => {
      mockFetch.mockReturnValue(mockResponse({}, false, 500))
      await expect(getDiaries()).rejects.toThrow('获取日记列表失败')
    })

    it('createDiary should return new diary', async () => {
      const diary = { id: 1, diary_date: '2024-01-15' }
      mockFetch.mockReturnValue(mockResponse(diary))
      const result = await createDiary({ diary_date: '2024-01-15' })
      expect(result).toEqual(diary)
    })

    it('getDiaryById should return diary', async () => {
      const diary = { id: 1, diary_date: '2024-01-15' }
      mockFetch.mockReturnValue(mockResponse(diary))
      const result = await getDiaryById(1)
      expect(result).toEqual(diary)
    })

    it('updateDiary should return updated diary', async () => {
      const diary = { id: 1, notes: 'updated' }
      mockFetch.mockReturnValue(mockResponse(diary))
      const result = await updateDiary(1, { notes: 'updated' })
      expect(result).toEqual(diary)
    })

    it('deleteDiary should succeed', async () => {
      mockFetch.mockReturnValue(mockResponse({}))
      await deleteDiary(1)
      expect(mockFetch.mock.calls[0][1].method).toBe('DELETE')
    })

    it('getDiaryCalendar should return entries', async () => {
      const response = { entries: [] }
      mockFetch.mockReturnValue(mockResponse(response))
      const result = await getDiaryCalendar(2024, 1)
      expect(result).toEqual(response)
    })

    it('getDiaryStats should return stats', async () => {
      const stats = { total_diaries: 10 }
      mockFetch.mockReturnValue(mockResponse(stats))
      const result = await getDiaryStats()
      expect(result).toEqual(stats)
    })

    it('triggerDiaryReview should return review', async () => {
      const review = { ai_review: { score: 90 } }
      mockFetch.mockReturnValue(mockResponse(review))
      const result = await triggerDiaryReview(1)
      expect(result).toEqual(review)
    })
  })

  describe('Fortune API', () => {
    it('getTodayFortune should return fortune', async () => {
      const fortune = { id: 1, overall_score: 80 }
      mockFetch.mockReturnValue(mockResponse(fortune))
      const result = await getTodayFortune()
      expect(result).toEqual(fortune)
    })

    it('getFortuneByDate should return fortune', async () => {
      const fortune = { id: 1, fortune_date: '2024-01-15' }
      mockFetch.mockReturnValue(mockResponse(fortune))
      const result = await getFortuneByDate('2024-01-15')
      expect(result).toEqual(fortune)
    })

    it('generateFortune should return new fortune', async () => {
      const fortune = { id: 1, overall_score: 90 }
      mockFetch.mockReturnValue(mockResponse(fortune))
      const result = await generateFortune()
      expect(result).toEqual(fortune)
    })
  })

  describe('Membership API', () => {
    it('getMembershipStatus should return status', async () => {
      const status = { plan: 'free', status: 'active' }
      mockFetch.mockReturnValue(mockResponse(status))
      const result = await getMembershipStatus()
      expect(result).toEqual(status)
    })

    it('getPlans should return plans', async () => {
      const plans = { plans: [] }
      mockFetch.mockReturnValue(mockResponse(plans))
      const result = await getPlans()
      expect(result).toEqual(plans)
    })

    it('subscribe should return result', async () => {
      const result = { subscription_id: 1, status: 'active' }
      mockFetch.mockReturnValue(mockResponse(result))
      const res = await subscribe({ plan: 'monthly', payment_method: 'wechat' })
      expect(res).toEqual(result)
    })

    it('cancelSubscription should return result', async () => {
      const result = { status: 'cancelled' }
      mockFetch.mockReturnValue(mockResponse(result))
      const res = await cancelSubscription(123)
      expect(res).toEqual(result)
    })

    it('upgradeMembership should return result', async () => {
      const result = { status: 'upgraded' }
      mockFetch.mockReturnValue(mockResponse(result))
      const res = await upgradeMembership({ new_plan: 'yearly' })
      expect(res).toEqual(result)
    })

    it('renewMembership should return result', async () => {
      const result = { status: 'renewed' }
      mockFetch.mockReturnValue(mockResponse(result))
      const res = await renewMembership({ payment_method: 'alipay' })
      expect(res).toEqual(result)
    })

    it('getQuota should return quota', async () => {
      const quota = { feature: 'recommend', allowed: true, used: 5 }
      mockFetch.mockReturnValue(mockResponse(quota))
      const result = await getQuota('recommend')
      expect(result).toEqual(quota)
    })
  })

  describe('Push API', () => {
    it('getPushSettings should return settings', async () => {
      const settings = { enabled: true }
      mockFetch.mockReturnValue(mockResponse(settings))
      const result = await getPushSettings()
      expect(result).toEqual(settings)
    })

    it('updatePushSettings should return updated settings', async () => {
      const settings = { enabled: false }
      mockFetch.mockReturnValue(mockResponse(settings))
      const result = await updatePushSettings({ enabled: false })
      expect(result).toEqual(settings)
    })

    it('getPushHistory should return history', async () => {
      const history = { notifications: [], total: 0, page: 1, size: 20 }
      mockFetch.mockReturnValue(mockResponse(history))
      const result = await getPushHistory(1, 20)
      expect(result).toEqual(history)
    })

    it('getUnreadCount should return count', async () => {
      mockFetch.mockReturnValue(mockResponse({ count: 5 }))
      const result = await getUnreadCount()
      expect(result).toEqual({ count: 5 })
    })

    it('markNotificationRead should succeed', async () => {
      mockFetch.mockReturnValue(mockResponse({}))
      await markNotificationRead(1)
      expect(mockFetch.mock.calls[0][1].method).toBe('POST')
    })
  })

  describe('streamRecommendation', () => {
    it('should throw if no response body', async () => {
      mockFetch.mockReturnValue(mockResponse({}))
      const gen = streamRecommendation({ query: 'test' })
      await expect(gen.next()).rejects.toThrow('No response body')
    })

    it('should parse SSE events', async () => {
      const sseData = 'data: {"type":"token","data":"Hello"}\n\ndata: {"type":"done","data":null}\n\n'
      const encoder = new TextEncoder()
      const chunks = [encoder.encode(sseData)]
      let chunkIndex = 0

      const mockReader = {
        read: vi.fn().mockImplementation(() => {
          if (chunkIndex < chunks.length) {
            return Promise.resolve({ done: false, value: chunks[chunkIndex++] })
          }
          return Promise.resolve({ done: true, value: undefined })
        }),
      }

      mockFetch.mockReturnValue({
        ok: true,
        body: { getReader: () => mockReader },
      } as any)

      const gen = streamRecommendation({ query: 'test' })
      const events = []
      for await (const event of gen) {
        events.push(event)
      }

      expect(events).toHaveLength(2)
      expect(events[0]).toEqual({ type: 'token', data: 'Hello' })
      expect(events[1]).toEqual({ type: 'done', data: null })
    })
  })
})
