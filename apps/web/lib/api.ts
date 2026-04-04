const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
}

export interface SSEEvent {
  type: 'analysis' | 'items' | 'token' | 'done' | 'error'
  data: any
}

/**
 * 流式推荐请求 - 返回 AsyncGenerator
 */
export async function* streamRecommendation(
  request: RecommendRequest
): AsyncGenerator<SSEEvent, void, unknown> {
  const response = await fetch(`${API_BASE}/api/v1/recommend/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
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
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: SSEEvent = JSON.parse(line.slice(6))
          yield event
        } catch (e) {
          console.error('Parse error:', e)
        }
      }
    }
  }
}

/**
 * 健康检查
 */
export async function checkHealth(): Promise<{ status: string; db: string }> {
  const response = await fetch(`${API_BASE}/health`)
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
  const response = await fetch(`${API_BASE}/api/v1/bazi/calculate`, {
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
  const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
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

  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
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
  console.log('[Login] 收到响应，token:', data.access_token?.substring(0, 20) + '...')
  setAuthToken(data.access_token)
  
  // 验证 token 是否正确设置
  const savedToken = getAuthToken()
  console.log('[Login] 验证保存的 token:', savedToken?.substring(0, 20) + '...')
  
  return data
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<User> {
  const headers = getAuthHeaders()
  console.log('[getCurrentUser] 请求 headers:', JSON.stringify(headers))
  
  const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: {
      ...headers,
    },
  })

  if (!response.ok) {
    console.log('[getCurrentUser] 请求失败，状态:', response.status)
    if (response.status === 401) {
      // 只在确实没有有效登录时才清除 token
      // 不要在请求失败时立即清除，可能是临时的网络问题
      console.log('[getCurrentUser] 401 错误，但不立即清除 token')
    }
    throw new Error('获取用户信息失败')
  }

  return response.json()
}

/**
 * 更新用户八字
 */
export async function updateUserBazi(request: BaziCalculateRequest): Promise<User> {
  const response = await fetch(`${API_BASE}/api/v1/auth/bazi`, {
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
  const response = await fetch(`${API_BASE}/api/v1/auth/profile`, {
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
  const headers = getAuthHeaders()
  console.log('[getUserProfile] 请求 headers:', JSON.stringify(headers))
  
  const response = await fetch(`${API_BASE}/api/v1/auth/profile`, {
    headers: {
      ...headers,
    },
  })

  console.log('[getUserProfile] 响应状态:', response.status)

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
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
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

  const headers = getAuthHeaders()
  console.log('[getWardrobeItems] 请求 headers:', JSON.stringify(headers))

  const response = await fetch(`${API_BASE}/api/v1/wardrobe/items?${searchParams}`, {
    headers: {
      ...headers,
    },
  })

  if (!response.ok) {
    console.log('[getWardrobeItems] 请求失败，状态:', response.status)
    throw new Error('获取衣橱列表失败')
  }

  return response.json()
}

/**
 * 添加衣物到衣橱
 */
export async function addWardrobeItem(data: AddWardrobeItemRequest): Promise<WardrobeItem> {
  const response = await fetch(`${API_BASE}/api/v1/wardrobe/items`, {
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
  const response = await fetch(`${API_BASE}/api/v1/wardrobe/items/${itemId}`, {
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
  const response = await fetch(`${API_BASE}/api/v1/wardrobe/items/${itemId}`, {
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
  
  console.log('[previewTagging] 请求 headers:', JSON.stringify(headers))
  
  const response = await fetch(`${API_BASE}/api/v1/wardrobe/items/preview-tagging`, {
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
  const response = await fetch(`${API_BASE}/api/v1/wardrobe/feedback`, {
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
