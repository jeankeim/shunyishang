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

// SSE 流式请求专用：直接访问后端（绕过 Next.js rewrites，避免流式响应被缓冲/断开）
const getDirectAPIBase = () => {
  if (typeof window !== 'undefined') {
    // 浏览器环境：优先使用环境变量中的后端地址（生产环境为 Zeabur HTTPS 域名）
    // 仅在未配置时回退到本地开发地址
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
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
}

export interface SSEEvent {
  type: 'analysis' | 'items' | 'token' | 'done' | 'error' | 'travel_plan'
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
    const error = await response.json()
    throw new Error(error.detail || 'AI 打标失败')
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
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || '提交反馈失败')
  }

  return response.json()
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
}): Promise<any> {
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
  return response.json()
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
