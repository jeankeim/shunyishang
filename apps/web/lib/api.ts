// 智能 API 地址检测
// - 静态导出模式（OSS 托管）：浏览器直接使用 NEXT_PUBLIC_API_URL（无 Next.js rewrites）
// - Vercel/开发模式：浏览器使用相对路径，通过 Next.js rewrites 代理，消除 CORS
const isStaticExport = process.env.NEXT_PUBLIC_STATIC_EXPORT === 'true'

const getAPIBase = () => {
  if (typeof window !== 'undefined') {
    // 浏览器环境
    if (isStaticExport) {
      // 静态导出：无 Next.js rewrites，直接使用后端完整 URL
      return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    }
    // Vercel/开发模式：返回空字符串，使用相对路径（Next.js rewrites 代理）
    return ''
  }
  // SSR 环境：使用完整 URL（Next.js rewrites 在服务端代理请求）
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

// SSE 流式请求专用
// - 静态导出模式：浏览器直连后端（无 Nginx/rewrites 可用）
// - 非静态导出模式：浏览器走相对路径，由 Nginx 代理（已配 proxy_buffering off 支持 SSE）
const getDirectAPIBase = () => {
  if (typeof window !== 'undefined') {
    if (isStaticExport) {
      return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    }
    // 非静态导出：走 Nginx 反代（同源，无 CORS，SSE 由 Nginx proxy_buffering off 保障）
    return ''
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

// 不要在这里固定API_BASE，而是在每次请求时动态获取
// const API_BASE = getAPIBase()  // 删除这行

// 安全提取错误信息：兼容后端返回非 JSON 的情况（如后端未启动时 Next.js 代理返回
// 纯文本 "Internal Server Error"，直接 response.json() 会抛出误导性的
// "Unexpected token 'I'" 错误，掩盖真实问题）
async function extractErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const text = await response.text()
    if (!text) return `${fallback}（${response.status}）`
    try {
      const data = JSON.parse(text)
      return data?.detail || data?.message || fallback
    } catch {
      // 非 JSON 响应（如代理层 / 网关返回的纯文本错误）
      if (response.status >= 500) return `服务暂时不可用，请稍后重试（${response.status}）`
      return `${fallback}（${response.status}）`
    }
  } catch {
    return fallback
  }
}

// 调试信息：打印API地址（仅在浏览器环境）
if (typeof window !== 'undefined') {
  // 全局测试函数：在浏览器控制台执行 testAPI() 测试连接
  ;(window as any).testAPI = async () => {
    console.log('\n=== API 连接测试 ===')
    console.log('当前页面:', window.location.href)
    const apiUrl = getAPIBase()
    console.log('目标API:', apiUrl)
    
    try {
      console.log('测试健康检查...')
      const health = await fetch(`${apiUrl}/health`).then(r => r.json())
      console.log('✅ 健康检查成功:', health)
      
      console.log('测试八字计算接口...')
      const bazi = await fetch(`${apiUrl}/api/v1/bazi/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          birth_year: 1990,
          birth_month: 5,
          birth_day: 15,
          birth_hour: 8,
          gender: '男'
        })
      }).then(r => r.json())
      console.log('✅ 八字计算成功:', bazi.day_master)
      
      console.log('\n=== 所有测试通过 ✅ ===')
      return true
    } catch (error) {
      console.error('\n❌ API 连接失败:', error)
      console.error('请检查：')
      console.error('1. 后端服务是否运行 (lsof -i:8000)')
      console.error('2. 手机和电脑是否在同一WiFi')
      console.error('3. Mac防火墙是否关闭')
      return false
    }
  }
  
}

export interface RecommendRequest {
  query: string
  scene?: string
  weather_element?: string
  weather?: {  // 新增：完整天气信息
    temperature?: number
    temperature_max?: number
    weather_desc?: string
    humidity?: number
    wind_level?: number
  }
  bazi?: {
    birth_year: number
    birth_month: number
    birth_day: number
    birth_hour: number
    gender: '男' | '女'
  }
  gender?: '男' | '女'  // 用户性别（优先于bazi中的gender）
  top_k?: number
  retrieval_mode?: 'public' | 'wardrobe' | 'hybrid'  // 推荐检索模式
  user_id?: number  // 用户ID（衣橱模式必需）
  user_city?: string  // 用户当前城市（用于城市五行计算）
  
  // 旅行/出差场景参数（可选，也可从query中自动提取）
  travel_days?: number   // 旅行天数
  destination?: string   // 目的地城市
  luggage_size?: '小' | '中' | '大'  // 行李箱大小
  
  // 换一批功能
  batch_index?: number   // 批次索引（0-2，最多3批）
}

export interface SSEEvent {
  type: 'analysis' | 'items' | 'token' | 'done' | 'error' | 'travel_plan' | 'hint' | 'notice'
  data: any
}

/**
 * 上报用户行为（隐性反馈）
 */
export async function reportBehavior(
  userId: number | undefined,
  itemId: string | number,
  action: 'view' | 'click' | 'expand' | 'image_click' | 'dwell',
  dwellDuration?: number
): Promise<void> {
  try {
    await fetch(`${getAPIBase()}/api/v1/wardrobe/behavior`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        item_id: itemId,
        action,
        dwell_duration: dwellDuration,
      }),
    })
  } catch (e) {
    // 静默失败，不影响用户体验
  }
}

/**
 * 流式推荐请求 - 返回 AsyncGenerator
 */
export async function* streamRecommendation(
  request: RecommendRequest
): AsyncGenerator<SSEEvent, void, unknown> {
  // SSE 流式请求直连后端，避免 Next.js rewrites 缓冲/断开流式响应
  const response = await fetch(`${getDirectAPIBase()}/api/v1/recommend/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  })

  if (!response.body) {
    throw new Error('No response body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    
    if (done) {
      break
    }
    
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: SSEEvent = JSON.parse(line.slice(6))
          yield event
        } catch (e) {
          console.error('[SSE] 解析错误:', e, '原始数据:', line.slice(0, 100))
        }
      }
    }
  }
}

/**
 * 健康检查
 */
export async function checkHealth(): Promise<{ status: string; db: string }> {
  const response = await fetch(`${getAPIBase()}/health`)
  if (!response.ok) throw new Error('Health check failed')
  return response.json()
}

/**
 * 八字计算接口
 * 输入年月日时，返回八字排盘和五行分布
 */
export interface BaziCalculateRequest {
  birth_year: number
  birth_month: number
  birth_day: number
  birth_hour: number
  gender: '男' | '女'
  /** PIPL 敏感信息处理同意（保存八字到账号时必传 true） */
  sensitive_consent?: boolean
}

export interface BaziCalculateResponse {
  pillars: Record<string, string>
  eight_chars: string[]
  five_elements_count: Record<string, number>
  dominant_element: string
  lacking_element: string | null
  day_master: string
  month_element: string
  suggested_elements: string[]
  avoid_elements: string[]
  reasoning: string
}

export async function calculateBazi(request: BaziCalculateRequest): Promise<BaziCalculateResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/bazi/calculate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '八字计算失败')
  }

  return response.json()
}

// ========== 用户认证接口 ==========

export interface User {
  id: number
  user_code: string
  phone?: string
  email?: string
  nickname?: string
  gender?: string
  birth_date?: string
  birth_time?: string
  birth_location?: string
  preferred_city?: string
  avatar_url?: string
  bazi?: BaziCalculateResponse
  xiyong_elements?: string[]
  skin_tone?: string
  style_preference?: string
  body_type?: string
  aesthetic_tags?: string[]
}

export interface LoginRequest {
  phone?: string
  email?: string
  password: string
}

export interface RegisterRequest {
  phone?: string
  email?: string
  password: string
  nickname?: string
  gender?: string
  /** PIPL 单独同意：已阅读并同意隐私政策 */
  privacy_consent?: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

// 存储 token
let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('wuxing_token', token)
    } else {
      localStorage.removeItem('wuxing_token')
    }
  }
}

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  if (!authToken) {
    authToken = localStorage.getItem('wuxing_token')
  }
  return authToken
}

export function initAuthToken() {
  if (typeof window !== 'undefined') {
    authToken = localStorage.getItem('wuxing_token')
  }
}

// 获取认证 headers
function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken()
  const headers: Record<string, string> = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

/**
 * 用户注册
 */
export async function register(request: RegisterRequest): Promise<AuthResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '注册失败')
  }

  const data = await response.json()
  setAuthToken(data.access_token)
  return data
}

/**
 * 用户登录
 */
export async function login(request: LoginRequest): Promise<AuthResponse> {
  const formData = new URLSearchParams()
  formData.append('username', request.phone || request.email || '')
  formData.append('password', request.password)

  const response = await fetch(`${getAPIBase()}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '登录失败')
  }

  const data = await response.json()
  setAuthToken(data.access_token)
  return data
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<User> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/auth/me`, {
      headers: getAuthHeaders(),
    })

    if (!response.ok) {
      if (response.status === 502) {
        throw new Error('后端服务暂时不可用，请稍后重试')
      }
      throw new Error('获取用户信息失败')
    }

    return response.json()
  } catch (error) {
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      throw new Error('网络连接失败，请检查后端服务')
    }
    throw error
  }
}

/**
 * 更新用户八字
 */
export async function updateUserBazi(request: BaziCalculateRequest): Promise<User> {
  const response = await fetch(`${getAPIBase()}/api/v1/auth/bazi`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error('更新八字失败')
  }

  return response.json()
}

/**
 * 更新用户资料
 */
export interface UpdateProfileRequest {
  nickname?: string | null
  gender?: string | null
  birth_date?: string | null
  birth_time?: string | null
  birth_location?: string | null
  preferred_city?: string | null
  avatar_url?: string | null
  skin_tone?: string | null
  style_preference?: string | null
  body_type?: string | null
  aesthetic_tags?: string[] | null
  /** PIPL 敏感信息处理同意（修改出生信息时必传 true） */
  sensitive_consent?: boolean
}

export async function updateProfile(request: UpdateProfileRequest): Promise<User> {
  const response = await fetch(`${getAPIBase()}/api/v1/auth/profile`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '更新资料失败')
  }

  return response.json()
}

/**
 * 获取完整用户资料
 */
export async function getUserProfile(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/auth/profile`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    if (response.status === 401) {
      setAuthToken(null)
    }
    const errorText = await response.text()
    console.error('[getUserProfile] 错误响应:', errorText)
    throw new Error('获取用户资料失败')
  }

  return response.json()
}

/**
 * 用户登出
 */
export async function logout(): Promise<void> {
  try {
    await fetch(`${getAPIBase()}/api/v1/auth/logout`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
      },
    })
  } finally {
    setAuthToken(null)
  }
}

/**
 * 注销账号（PIPL：彻底删除账号及全部个人数据，不可恢复）
 */
export async function deleteAccount(): Promise<void> {
  const response = await fetch(`${getAPIBase()}/api/v1/auth/account`, {
    method: 'DELETE',
    headers: {
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '注销账号失败，请重试')
  }

  // 注销成功，清除本地凭证
  setAuthToken(null)
}

// ========== 衣橱管理接口 ==========

export interface WardrobeItem {
  id: number
  user_id: number
  item_code?: string
  name: string
  category?: string
  image_url?: string
  primary_element: string
  secondary_element?: string
  attributes_detail?: Record<string, any>
  is_custom: boolean
  is_active: boolean
  wear_count: number
  last_worn_date?: string
  is_favorite: boolean
  notes?: string
  created_at: string
  updated_at: string
  gender?: string
  applicable_weather?: string[]
  applicable_seasons?: string[]
  temperature_range?: { min: number; max: number }
  functionality?: string[]
  thickness_level?: string
  energy_intensity?: number
}

export interface WardrobeListResponse {
  items: WardrobeItem[]
  total: number
  element_stats: Record<string, number>
}

export interface AITaggingResult {
  primary_element: string
  secondary_element?: string
  
  // 颜色信息
  color: string
  color_element?: string
  
  // 材质信息
  material?: string
  material_element?: string
  
  // 款式信息
  style?: string
  shape?: string
  details?: string[]
  
  // 能量信息
  energy_intensity?: number
  
  // 分类
  category?: string
  
  // 其他信息
  season: string[]
  tags: string[]
  confidence: number
  
  // 天气/场景相关
  applicable_weather?: string[]
  applicable_seasons?: string[]
  temperature_range?: { min: number; max: number }
  functionality?: string[]
  thickness_level?: string
  
  // 建议名称
  suggested_name?: string
}

export interface AddWardrobeItemRequest {
  item_code?: string
  name: string
  category?: string
  image_url?: string
  primary_element?: string
  secondary_element?: string
  description?: string
  gender?: string
  applicable_weather?: string[]
  applicable_seasons?: string[]
  temperature_range?: { min: number; max: number }
  functionality?: string[]
  thickness_level?: string
  energy_intensity?: number
}

export interface UpdateWardrobeItemRequest {
  name?: string
  category?: string
  primary_element?: string
  secondary_element?: string
  attributes_detail?: Record<string, any>
  image_url?: string
}

export interface FeedbackRequest {
  session_id?: string
  item_id?: number
  item_code?: string
  item_source: 'wardrobe' | 'public'
  action: 'like' | 'dislike'
  feedback_reason?: string
}

export interface FeedbackResponse {
  id: number
  user_id: number
  action: string
  created_at: string
}

/**
 * 获取衣橱列表
 */
export async function getWardrobeItems(params?: {
  category?: string
  element?: string
  page?: number
  limit?: number
}): Promise<WardrobeListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.category) searchParams.append('category', params.category)
  if (params?.element) searchParams.append('element', params.element)
  if (params?.page) searchParams.append('page', params.page.toString())
  if (params?.limit) searchParams.append('limit', params.limit.toString())

  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/items?${searchParams}`, {
    headers: getAuthHeaders(),
  })

  if (!response.ok) {
    throw new Error('获取衣橱列表失败')
  }

  return response.json()
}

/**
 * 添加衣物到衣橱
 */
export async function addWardrobeItem(data: AddWardrobeItemRequest): Promise<WardrobeItem> {
  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/items`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '添加衣物失败')
  }

  return response.json()
}

/**
 * 更新衣物信息
 */
export async function updateWardrobeItem(itemId: number, data: UpdateWardrobeItemRequest): Promise<WardrobeItem> {
  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/items/${itemId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '更新衣物失败')
  }

  return response.json()
}

/**
 * 删除衣物（软删除）
 */
export async function deleteWardrobeItem(itemId: number): Promise<void> {
  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/items/${itemId}`, {
    method: 'DELETE',
    headers: {
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '删除衣物失败')
  }
}

/**
 * AI 打标预览
 */
export async function previewTagging(description: string, image_url?: string): Promise<AITaggingResult> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
  }

  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/items/preview-tagging`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ description, image_url }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || (response.status >= 500 ? 'AI 打标服务暂时不可用，请稍后重试' : 'AI 打标失败'))
  }

  return response.json()
}

/**
 * 提交推荐反馈
 */
export async function submitFeedback(data: FeedbackRequest): Promise<FeedbackResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(10000), // 10秒超时，避免请求挂起导致按钮永久锁死
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '提交反馈失败')
  }

  return response.json()
}

/**
 * 撤销推荐反馈
 */
export async function cancelFeedback(itemCode: string, itemId?: number): Promise<void> {
  const params = new URLSearchParams({ item_code: itemCode })
  if (itemId) params.append('item_id', itemId.toString())

  const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/feedback?${params}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
    signal: AbortSignal.timeout(10000),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || '撤销反馈失败')
  }
}

// ========== 日记接口 ==========

export interface CreateDiaryRequest {
  diary_date: string
  mood?: string
  occasion?: string
  notes?: string
  rating?: number
  image_urls?: string[]
  items?: {
    item_source?: string
    wardrobe_item_id?: number
    seed_item_code?: string
    category?: string
    notes?: string
  }[]
  trigger_ai_review?: boolean
}

export interface UpdateDiaryRequest {
  mood?: string
  occasion?: string
  notes?: string
  rating?: number
  image_urls?: string[]
}

export async function getDiaries(params?: {
  page?: number
  size?: number
  mood?: string
  date_from?: string
  date_to?: string
}): Promise<any> {
  const sp = new URLSearchParams()
  if (params?.page) sp.append('page', params.page.toString())
  if (params?.size) sp.append('size', params.size.toString())
  if (params?.mood) sp.append('mood', params.mood)
  if (params?.date_from) sp.append('date_from', params.date_from)
  if (params?.date_to) sp.append('date_to', params.date_to)

  const response = await fetch(`${getAPIBase()}/api/v1/diary?${sp}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取日记列表失败')
  return response.json()
}

export async function createDiary(data: CreateDiaryRequest): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '创建日记失败')
  }
  return response.json()
}

export async function getDiaryById(diaryId: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/${diaryId}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取日记详情失败')
  return response.json()
}

export async function updateDiary(diaryId: number, data: UpdateDiaryRequest): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/${diaryId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('更新日记失败')
  return response.json()
}

export async function deleteDiary(diaryId: number): Promise<void> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/${diaryId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('删除日记失败')
}

export async function getDiaryCalendar(year: number, month: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/calendar?year=${year}&month=${month}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取日历失败')
  return response.json()
}

export async function getDiaryStats(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/stats`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取统计失败')
  return response.json()
}

export async function quickCheckIn(data: {
  image_url?: string
  description?: string
  mood?: string
  weather_snapshot?: Record<string, any>
}): Promise<QuickCheckInResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/quick-checkin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, '打卡失败'))
  }
  return response.json()
}

export async function triggerDiaryReview(diaryId: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/diary/${diaryId}/review`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, 'AI点评失败'))
  }
  return response.json()
}

// ========== 运势接口 ==========

export async function getTodayFortune(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/today`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取今日运势失败')
  return response.json()
}

export async function getTodayCard(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/today-card`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取今日运势卡片失败')
  return response.json()
}

export async function getDailyRitual(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/daily-ritual`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取每日仪式摘要失败')
  return response.json()
}

export async function getFortuneByDate(dateStr: string): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune?date=${dateStr}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取运势失败')
  return response.json()
}

export async function generateFortune(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/generate`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('生成运势失败')
  return response.json()
}

// ========== 命理分析接口 ==========

export async function getTenGods(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/destiny/ten-gods`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取十神格局失败')
  return response.json()
}

export async function getAnnualLuck(year: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/destiny/annual-luck?year=${year}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取流年运势失败')
  return response.json()
}

export async function getMajorLuck(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/destiny/major-luck`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取大运周期失败')
  return response.json()
}

export async function getAdvancedBazi(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/destiny/advanced-bazi`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取高级八字分析失败')
  return response.json()
}

// ========== 会员接口（个人备案版：已禁用） ==========

// export async function getMembershipStatus(): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/status`, {
//     headers: getAuthHeaders(),
//   })
//   if (!response.ok) throw new Error('获取会员状态失败')
//   return response.json()
// }
//
// export async function getPlans(): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/plans`, {
//     headers: getAuthHeaders(),
//   })
//   if (!response.ok) throw new Error('获取套餐列表失败')
//   return response.json()
// }
//
// export async function subscribe(data: { plan: string; payment_method: string }): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/subscribe`, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
//     body: JSON.stringify(data),
//   })
//   if (!response.ok) {
//     const error = await response.json()
//     throw new Error(error.detail || '订阅失败')
//   }
//   return response.json()
// }
//
// export async function cancelSubscription(subscriptionId: number): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/cancel?subscription_id=${subscriptionId}`, {
//     method: 'POST',
//     headers: getAuthHeaders(),
//   })
//   if (!response.ok) {
//     const error = await response.json()
//     throw new Error(error.detail || '取消订阅失败')
//   }
//   return response.json()
// }
//
// export async function upgradeMembership(data: { new_plan: string }): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/upgrade`, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
//     body: JSON.stringify(data),
//   })
//   if (!response.ok) {
//     const error = await response.json()
//     throw new Error(error.detail || '升级失败')
//   }
//   return response.json()
// }
//
// export async function renewMembership(data: { payment_method: string }): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/renew`, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
//     body: JSON.stringify(data),
//   })
//   if (!response.ok) {
//     const error = await response.json()
//     throw new Error(error.detail || '续费失败')
//   }
//   return response.json()
// }
//
// export async function getQuota(feature: string): Promise<any> {
//   const response = await fetch(`${getAPIBase()}/api/v1/membership/quota/${feature}`, {
//     headers: getAuthHeaders(),
//   })
//   if (!response.ok) throw new Error('获取配额失败')
//   return response.json()
// }

// ========== 推送接口 ==========

export async function getPushSettings(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/settings`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取推送设置失败')
  return response.json()
}

export async function updatePushSettings(data: Record<string, any>): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('更新推送设置失败')
  return response.json()
}

export async function getPushHistory(page = 1, size = 20): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/history?page=${page}&size=${size}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取推送历史失败')
  return response.json()
}

export async function getUnreadCount(): Promise<{ count: number }> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/unread-count`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取未读数量失败')
  return response.json()
}

export async function markNotificationRead(id: number): Promise<void> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/${id}/read`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('标记已读失败')
}

/** 推送行为反馈（行为闭环） */
export interface PushFeedbackResponse {
  status: 'ok' | 'error'
  action: string
  preference_updated: boolean
  message?: string
}

export async function reportPushFeedback(
  notificationId: number,
  action: 'click' | 'ignore' | 'close'
): Promise<PushFeedbackResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/${notificationId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ action }),
  })
  if (!response.ok) throw new Error('推送反馈提交失败')
  return response.json()
}

/** 智能提醒检查（首页加载时调用） */
export interface SmartAlert {
  type: string
  message: string
  [key: string]: any
}

export async function smartReminderCheck(weatherInfo?: Record<string, any>): Promise<{ alerts: SmartAlert[] }> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/smart-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(weatherInfo || {}),
  })
  if (!response.ok) throw new Error('智能提醒检查失败')
  return response.json()
}

// ============================================
// 用户不喜欢物品 API
// ============================================

export async function reportItemDislike(itemCode: string, reason?: string): Promise<{ success: boolean; message: string }> {
  const params = new URLSearchParams({ item_code: itemCode })
  if (reason) params.set('reason', reason)
  const response = await fetch(`${getAPIBase()}/api/v1/recommend/dislike?${params}`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
  })
  if (!response.ok) throw new Error('记录不喜欢失败')
  return response.json()
}

export async function getDislikedItems(): Promise<any[]> {
  const response = await fetch(`${getAPIBase()}/api/v1/recommend/disliked`, {
    headers: { ...getAuthHeaders() },
  })
  if (!response.ok) throw new Error('获取不喜欢列表失败')
  return response.json()
}

export async function removeDislike(itemCode: string): Promise<{ success: boolean }> {
  const response = await fetch(`${getAPIBase()}/api/v1/recommend/dislike/${encodeURIComponent(itemCode)}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() },
  })
  if (!response.ok) throw new Error('取消不喜欢失败')
  return response.json()
}

// ============================================
// 穿搭广场社区 API
// ============================================

export async function getCommunityPosts(page = 1, size = 20, element?: string): Promise<any> {
  const params = new URLSearchParams({ page: String(page), size: String(size) })
  if (element) params.set('element', element)
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts?${params}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取帖子列表失败')
  return response.json()
}

export async function getCommunityPost(postId: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/${postId}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取帖子详情失败')
  return response.json()
}

export async function createCommunityPost(data: {
  content: string
  image_urls?: string[]
  tags?: string[]
  element?: string
  diary_id?: number
}): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '发布失败' }))
    throw new Error(err.detail || '发布失败')
  }
  return response.json()
}

export async function deleteCommunityPost(postId: number): Promise<void> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/${postId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('删除帖子失败')
}

export async function getPostByDiary(diaryId: number): Promise<any | null> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/by-diary/${diaryId}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) return null
  return response.json()
}

export async function deletePostByDiary(diaryId: number): Promise<void> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/by-diary/${diaryId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('取消发布失败')
}

export async function togglePostLike(postId: number): Promise<{ action: string }> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/${postId}/like`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('操作失败')
  return response.json()
}

export async function getPostComments(postId: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/${postId}/comments`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取评论失败')
  return response.json()
}

export async function createPostComment(postId: number, data: { content: string; parent_id?: number }): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/community/posts/${postId}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '评论失败' }))
    throw new Error(err.detail || '评论失败')
  }
  return response.json()
}

// ============================================
// 游戏化 / 修炼系统 API
// ============================================

export async function getCultivationProfile(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/cultivation/profile`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取修炼档案失败')
  return response.json()
}

export async function dailyCheckin(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/cultivation/checkin`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('签到失败')
  return response.json()
}

export async function checkAchievements(): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/cultivation/check-achievements`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('检查成就失败')
  return response.json()
}

export async function getPointsHistory(page = 1, size = 20): Promise<any> {
  const params = new URLSearchParams({ page: String(page), size: String(size) })
  const response = await fetch(`${getAPIBase()}/api/v1/cultivation/history?${params}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取积分历史失败')
  return response.json()
}

// ============================================
// 智能提醒 API
// ============================================

export async function checkSmartReminders(weatherInfo?: any): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/push/smart-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(weatherInfo || null),
  })
  if (!response.ok) return { alerts: [] }
  return response.json()
}

// ============================================
// 付费运势报告 API
// ============================================

export async function getTask(taskId: string): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/tasks/${taskId}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('查询任务状态失败')
  return response.json()
}

const TASK_POLL_INTERVAL_MS = 2000
const TASK_POLL_TIMEOUT_MS = 120000

async function pollTaskResult(taskId: string): Promise<any> {
  const deadline = Date.now() + TASK_POLL_TIMEOUT_MS
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, TASK_POLL_INTERVAL_MS))
    const task = await getTask(taskId)
    if (task.status === 'done') return task.result
    if (task.status === 'failed') throw new Error(task.error || '任务执行失败')
  }
  throw new Error('任务处理超时，请稍后在报告列表中查看')
}

export async function generateAnnualReport(year?: number): Promise<any> {
  const params = year ? `?year=${year}` : ''
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/reports/annual${params}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '生成报告失败' }))
    throw new Error(err.detail || '生成报告失败')
  }
  const { task_id } = await response.json()
  return pollTaskResult(task_id)
}

export async function getFortuneReports(): Promise<any[]> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/reports`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) return []
  return response.json()
}

export async function getFortuneReport(reportId: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/reports/${reportId}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) throw new Error('获取报告失败')
  return response.json()
}

export async function purchaseFortuneReport(reportId: number): Promise<any> {
  const response = await fetch(`${getAPIBase()}/api/v1/fortune/reports/${reportId}/purchase`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '购买失败' }))
    throw new Error(err.detail || '购买失败')
  }
  return response.json()
}

// ============================================
// 五行穿搭百科 + 周易文化知识库 API
// ============================================

/** 五行穿搭/周易百科条目 */
export interface WuxingTip {
  id: number
  element: string            // 木/火/土/金/水/通用
  category: string           // 颜色搭配/材质推荐/周易基础/八卦入门/...
  content_type: string       // wuxing/zhouyi
  difficulty: string         // 入门/进阶/精通
  title: string
  content: string
  tags: string[]
  source?: string            // 知识来源，如"《周易》"
  sort_order: number
  is_published: boolean
  created_at?: string
  updated_at?: string
  date?: string              // 今日推荐携带的日期
}

/** 获取百科分类列表 */
export async function getWuxingCategories(): Promise<{ categories: { content_type: string; category: string; difficulty: string }[] }> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/content/wuxing-tips/categories`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) return { categories: [] }
    return response.json()
  } catch {
    return { categories: [] }
  }
}

/**
 * 获取每日一学（今日五行/周易百科，按日期自动匹配）
 * @param content_type 可选内容类型筛选: wuxing/zhouyi
 * @param difficulty 可选难度筛选: 入门/进阶/精通
 */
export async function getWuxingTip(params?: {
  date?: string
  element?: string
  content_type?: string
  difficulty?: string
}): Promise<WuxingTip | null> {
  try {
    const searchParams = new URLSearchParams()
    if (params?.date) searchParams.set('date', params.date)
    if (params?.element) searchParams.set('element', params.element)
    if (params?.content_type) searchParams.set('content_type', params.content_type)
    if (params?.difficulty) searchParams.set('difficulty', params.difficulty)
    const qs = searchParams.toString()
    const response = await fetch(`${getAPIBase()}/api/v1/content/wuxing-tips${qs ? '?' + qs : ''}`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getWuxingTip] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getWuxingTip] 异常:', error)
    return null
  }
}

/**
 * 获取全部百科知识
 * @param params 多维度筛选参数
 */
export async function getAllWuxingTips(params?: {
  element?: string
  content_type?: string
  category?: string
  difficulty?: string
}): Promise<WuxingTip[]> {
  try {
    const searchParams = new URLSearchParams()
    if (params?.element) searchParams.set('element', params.element)
    if (params?.content_type) searchParams.set('content_type', params.content_type)
    if (params?.category) searchParams.set('category', params.category)
    if (params?.difficulty) searchParams.set('difficulty', params.difficulty)
    const qs = searchParams.toString()
    const response = await fetch(`${getAPIBase()}/api/v1/content/wuxing-tips/all${qs ? '?' + qs : ''}`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getAllWuxingTips] 请求失败:', response.status)
      return []
    }
    const data = await response.json()
    // 后端返回 { tips: [...], total: N }
    return data.tips || []
  } catch (error) {
    console.error('[getAllWuxingTips] 异常:', error)
    return []
  }
}

// ============================================
// 每日精选推荐 API
// ============================================

/** 每日精选推荐 */
export interface DailyPick {
  item: {
    id: number
    name: string
    image_url: string
    category: string
    primary_element: string
    secondary_element?: string
    wear_count: number
    is_favorite: boolean
  } | null
  reason: string
  lucky_element: string
  lucky_color: string
  match_score: number
}

/**
 * 获取每日精选推荐（基于用户八字 + 当日运势 + 衣橱数据）
 */
export async function getDailyPick(): Promise<DailyPick | null> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/recommend/daily-pick`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getDailyPick] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getDailyPick] 异常:', error)
    return null
  }
}

// ============================================
// 每日智能穿搭建议 API
// ============================================

/** 每日智能穿搭物品 */
export interface DailyOutfitItem {
  id: number
  name: string
  category?: string
  image_url?: string
  primary_element?: string
  secondary_element?: string
  wear_count: number
  is_favorite: boolean
  match_score: number
}

/** 每日智能穿搭建议 */
export interface DailyOutfit {
  outfit_items: DailyOutfitItem[]
  reasoning: string
  weather_summary: {
    city: string
    temperature: number
    weather: string
    element: string
  }
  fortune_summary: {
    lucky_elements: string[]
    lucky_colors: string[]
    overall_score: number
  }
  style_tip: string
  match_score: number
  date: string
}

/**
 * 获取每日智能穿搭建议（基于八字+运势+天气+季节+偏好+衣橱）
 * @param batchIndex 换一批批次 (0-2)
 * @param city 前端定位城市（优先于用户设置，确保与首页天气显示一致）
 */
export async function getDailyOutfit(batchIndex = 0, city?: string): Promise<DailyOutfit | null> {
  try {
    const params = new URLSearchParams()
    if (batchIndex > 0) params.append('batch_index', String(batchIndex))
    if (city) params.append('city', city)
    const queryStr = params.toString() ? `?${params.toString()}` : ''
    const response = await fetch(`${getAPIBase()}/api/v1/recommend/daily-outfit${queryStr}`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getDailyOutfit] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getDailyOutfit] 异常:', error)
    return null
  }
}

// ============================================
// 流年运势周报 API
// ============================================

/** 流年运势周报 */
export interface WeeklyFortune {
  week_number: number
  start_date: string
  end_date: string
  overall_trend: string   // 上升/平稳/下降
  overall_score: number
  daily_fortunes: Array<{
    date: string
    score: number
    lucky_element: string
    lucky_color: string
  }>
  weekly_lucky_elements: string[]
  weekly_style_keywords: string[]
  outfit_suggestions: string
}

/**
 * 获取流年运势周报（基于用户八字 + 当前流年 + 本周节气）
 */
export async function getWeeklyFortune(): Promise<WeeklyFortune | null> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/fortune/weekly`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getWeeklyFortune] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getWeeklyFortune] 异常:', error)
    return null
  }
}

// ============================================
// 快捷打卡增强返回类型
// ============================================

/** 快捷打卡增强返回（扩展 quickCheckIn 的响应） */
export interface QuickCheckInResponse {
  id: number
  diary_id: number
  diary_date: string
  mood?: string
  occasion?: string
  notes?: string
  rating?: number
  image_urls?: string[]
  created_at?: string
  created: boolean
  ai_tags?: Record<string, any> | null
  /** 穿搭推荐（基于打卡内容 + 运势匹配） */
  outfit_recommendation?: {
    item_name: string
    item_id: number
    image_url: string
    reason: string
  }
  /** 穿搭与运势的匹配度评分 */
  fortune_match_score?: number
  /** 连续打卡天数 */
  streak_days?: number
}

// ============================================
// 用户偏好画像 API
// ============================================

/** 偏好维度摘要项 */
export interface PreferenceDimensionItem {
  name: string
  weight: number
  direction: '喜欢' | '不喜欢'
}

/** 偏好维度摘要 */
export interface PreferenceDimension {
  key: string
  label: string
  icon: string
  score: number          // 0~1 偏好强度
  top_items: PreferenceDimensionItem[]
  has_data: boolean
}

/** 用户偏好画像 */
export interface PreferenceSummary {
  dimensions: PreferenceDimension[]
  overall_score: number  // 0~1 系统了解度
  feedback_count: number
}

/**
 * 获取用户偏好画像（6维雷达图数据）
 */
export async function getPreferenceSummary(): Promise<PreferenceSummary | null> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/preference-summary`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getPreferenceSummary] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getPreferenceSummary] 异常:', error)
    return null
  }
}

// ============================================
// 衣橱智能分析 API
// ============================================

/** 频率分析物品 */
export interface FreqItem {
  id: number
  name: string
  category: string
  image_url?: string
  primary_element?: string
  wear_count: number
  last_worn_date?: string
  days_since_worn?: number
  freq_type: 'high' | 'low' | 'redundant'
  extra_info?: string
}

/** 频率分析汇总 */
export interface FrequencyAnalysis {
  high_freq_items: FreqItem[]
  low_freq_items: FreqItem[]
  redundant_items: FreqItem[]
  category_avg_wear: Record<string, number>
  summary: {
    total_items: number
    high_freq_count: number
    low_freq_count: number
    redundant_count: number
    high_freq_ratio: number
    low_freq_ratio: number
  }
}

/** 季节穿着模式 */
export interface SeasonalPattern {
  top_categories: Array<{ name: string; count: number }>
  top_elements: Array<{ name: string; count: number }>
  top_colors: Array<{ name: string; count: number }>
  total_records: number
}

/** 天气适应性 */
export interface WeatherBucket {
  label: string
  preferred_items: Array<{ name: string; count: number }>
  total_records: number
}

/** 衣橱总体统计 */
export interface WardrobeOverallStats {
  total_items: number
  active_items: number
  inactive_items: number
  avg_wear_count: number
  total_wear_count: number
  most_worn_category: string
  most_worn_element: string
}

/** 衣橱智能分析完整响应 */
export interface WardrobeAnalytics {
  frequency_analysis: FrequencyAnalysis
  seasonal_patterns: {
    spring: SeasonalPattern
    summer: SeasonalPattern
    autumn: SeasonalPattern
    winter: SeasonalPattern
  }
  weather_adaptability: {
    cold: WeatherBucket
    mild: WeatherBucket
    warm: WeatherBucket
    hot: WeatherBucket
  }
  overall_stats: WardrobeOverallStats
}

/**
 * 获取衣橱智能分析数据
 */
export async function getWardrobeAnalytics(): Promise<WardrobeAnalytics | null> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/analytics`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getWardrobeAnalytics] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getWardrobeAnalytics] 异常:', error)
    return null
  }
}

/** 闲置物品 */
export interface IdleItem {
  id: number
  name: string
  category: string
  image_url?: string
  primary_element?: string
  wear_count: number
  last_worn_date?: string
  days_since_worn?: number
  created_at?: string
  days_owned?: number
  donation_suggestion: string
}

/** 闲置物品响应 */
export interface IdleItemsResponse {
  idle_items: IdleItem[]
  total_count: number
  message: string
}

/**
 * 获取长期闲置衣物 + 公益建议
 */
export async function getIdleItems(): Promise<IdleItemsResponse | null> {
  try {
    const response = await fetch(`${getAPIBase()}/api/v1/wardrobe/idle-items`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      console.error('[getIdleItems] 请求失败:', response.status)
      return null
    }
    return response.json()
  } catch (error) {
    console.error('[getIdleItems] 异常:', error)
    return null
  }
}

// ============================================================
// 后台管理模块（仅管理员白名单可访问）
// ============================================================

/** 管理员身份 */
export interface AdminMeResponse {
  is_admin: boolean
  nickname: string
}

/** 看板单日指标 */
export interface DashboardDayMetrics {
  date: string
  dau: number
  new_users: number
  recommend_count: number
  api_requests: number
  diary_count: number
  fortune_count: number
  like_count: number
  dislike_count: number
  wardrobe_added: number
}

/** 运营看板响应 */
export interface AdminDashboardResponse {
  days: number
  today: DashboardDayMetrics
  totals: {
    total_users: number
    total_wardrobe_items: number
    total_seed_items: number
    recommend_total: number
    api_total: number
  }
  trend: DashboardDayMetrics[]
}

/** 阿里云账单按产品汇总 */
export interface BillProductSummary {
  product_code: string
  product_name: string
  pretax_amount: number
  payment_amount: number
  deducted_by_coupons: number
  percentage: number
}

/** 阿里云账单响应 */
export interface AdminBillsResponse {
  configured: boolean
  range: { start: string; end: string; days: number }
  total_pretax: number
  total_payment: number
  by_product: BillProductSummary[]
  daily: { date: string; pretax_amount: number; payment_amount: number }[]
  last_sync_at: string | null
}

/** 账单同步结果 */
export interface BillSyncResponse {
  synced_days: number
  synced_rows: number
  errors: string[]
  synced_at: string
}

/** 查询当前用户是否为管理员（未登录时抛错） */
export async function getAdminStatus(): Promise<AdminMeResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/admin/me`, {
    headers: getAuthHeaders(),
  })
  if (response.status === 403) {
    // 已登录但不在管理员白名单
    return { is_admin: false, nickname: '' }
  }
  if (!response.ok) {
    throw new Error(response.status === 401 ? '未登录' : '查询管理员身份失败')
  }
  return response.json()
}

/** 获取运营数据看板 */
export async function getAdminDashboard(days = 30): Promise<AdminDashboardResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/admin/dashboard?days=${days}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, '获取看板数据失败'))
  }
  return response.json()
}

/** 获取阿里云费用账单汇总 */
export async function getAdminBills(days = 31): Promise<AdminBillsResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/admin/bills?days=${days}`, {
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, '获取账单数据失败'))
  }
  return response.json()
}

/** 手动同步阿里云账单 */
export async function syncAdminBills(days = 3): Promise<BillSyncResponse> {
  const response = await fetch(`${getAPIBase()}/api/v1/admin/bills/sync?days=${days}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  })
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, '账单同步失败'))
  }
  return response.json()
}
