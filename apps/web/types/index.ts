// ========== 八字相关类型 ==========

export interface BaziInput {
  birthYear: number
  birthMonth: number
  birthDay: number
  birthHour: number
  gender: '男' | '女'
}

// ========== 推荐相关类型 ==========

export interface RecommendItem {
  item_code: string
  name: string
  category: string
  primary_element: string
  secondary_element?: string
  final_score: number
  semantic_score?: number  // Task 05: 语义匹配分数
  wuxing_score?: number    // Task 05: 五行匹配分数
  scene_score?: number     // Task 05: 场景适配分数
  preference_score?: number // Task 2.4: 偏好匹配分数
  color?: string
  reason?: string
  image_url?: string       // 高清原图 URL
  thumbnail_url?: string   // 缩略图 URL（400px 宽度）
  source?: 'wardrobe' | 'public'
  is_anchor?: boolean  // 用户显式指定的锚点单品（🎯 指定徽章）
  item_id?: number
  // 物品详情字段（用于详情弹窗）
  attributes_detail?: Record<string, any>  // 完整属性（颜色/面料/款式等）
  thickness_level?: string  // 厚度等级
  applicable_weather?: string[]  // 适用天气
  applicable_seasons?: string[]  // 适用季节
  temperature_range?: { 最低?: number; 最高?: number; min?: number; max?: number }  // 温度范围
  functionality?: Record<string, boolean>  // 功能特性
  gender?: string  // 适用性别
}

// ========== 聊天相关类型 ==========

export interface ChatMessageMetadata {
  targetElements?: string[]
  baziAnalysis?: string
  items?: RecommendItem[]
  elementScores?: Record<string, number>
  suggestedElements?: string[]
  scene?: string
  travelPlan?: any  // 多天行程规划数据
  notice?: string  // 软降级提示（如衣橱→公共库），以温和横幅展示
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
  type?: 'analysis' | 'done' | 'error' | 'hint'
  metadata?: ChatMessageMetadata
}

export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}

// ========== 从 lib/api.ts 重新导出类型，保持向后兼容 ==========

export type {
  WardrobeItem,
  WardrobeListResponse,
  AITaggingResult,
  AddWardrobeItemRequest,
  UpdateWardrobeItemRequest,
  FeedbackRequest,
  FeedbackResponse,
  User,
  BaziCalculateResponse,
} from '@/lib/api'

// ========== 日记相关类型 ==========

export interface DiaryOutfitItem {
  id: number
  diary_id: number
  item_source: 'wardrobe' | 'seed'
  wardrobe_item_id?: number
  seed_item_code?: string
  category?: string
  notes?: string
  name?: string
  image_url?: string
  primary_element?: string
  created_at: string
}

export interface OutfitDiary {
  id: number
  user_id: number
  diary_date: string
  mood?: 'happy' | 'neutral' | 'sad' | 'excited' | 'calm'
  weather_snapshot?: Record<string, any>
  occasion?: string
  notes?: string
  rating?: number
  ai_review?: {
    score?: number
    comment?: string
    suggestions?: string[]
    wuxing_analysis?: Record<string, any>
  }
  image_urls?: string[]
  items: DiaryOutfitItem[]
  created_at: string
  updated_at: string
}

export interface DiaryCalendarEntry {
  date: string
  mood?: string
  rating?: number
  has_items: boolean
}

export interface DiaryStats {
  total_diaries: number
  avg_rating?: number
  mood_distribution: Record<string, number>
  streak_days: number
  total_items: number
}

// ========== 运势相关类型 ==========

export interface FortuneScores {
  career: number
  wealth: number
  love: number
  health: number
  study: number
}

export interface LuckyElements {
  colors: string[]
  materials: string[]
  directions: string[]
  elements: string[]
}

export interface DailyFortune {
  id: number
  user_id: number
  fortune_date: string
  scores: FortuneScores
  overall_score: number
  advice_text?: string
  lucky_elements: LuckyElements
  outfit_suggestion?: string
  bazi_snapshot?: Record<string, any>
  huangli?: HuangLiData
  ai_narrative?: AiNarrative
  ai_pending?: boolean
  created_at: string
}

// v2 新增

export interface HuangLiData {
  yi: string[]
  ji: string[]
  chong_sha: string
  chong_zodiac: string
  ji_shen: string[]
  xiong_sha: string[]
  solar_term: string | null
  next_solar_term: string
  days_to_next_term: number
  hour_luck: HourLuck[]
  today_level_name: string
}

export interface HourLuck {
  hour: string
  ganzhi: string
  lucky: string
}

export interface AiNarrative {
  overview: string
  career_tip: string
  love_tip: string
  health_tip: string
  lucky_action: string
  avoid_action: string
}

// ========== 会员相关类型 ==========

export interface MembershipStatus {
  plan: 'free' | 'monthly' | 'yearly'
  status: 'active' | 'cancelled' | 'expired' | 'suspended'
  started_at?: string
  expires_at?: string
  auto_renew: boolean
  days_remaining?: number
}

export interface PlanInfo {
  name: string
  plan_key: string
  price_monthly: number
  price_yearly: number
  features: string[]
  limits: Record<string, any>
}

export interface SubscribeRequest {
  plan: 'monthly' | 'yearly'
  payment_method: 'wechat' | 'alipay' | 'mock'
}

export interface SubscribeResponse {
  subscription_id: number
  status: string
  payment_url?: string
}

export interface PushSettings {
  enabled: boolean
  fortune_push: boolean
  fortune_push_time: string
  diary_reminder: boolean
  diary_reminder_time: string
  marketing: boolean
  vibrate: boolean
}

export interface PushNotification {
  id: number
  type: string
  title: string
  body?: string
  data: Record<string, any>
  sent_at: string
  read_at?: string
}

export interface PushHistoryResponse {
  notifications: PushNotification[]
  total: number
  page: number
  size: number
}

export interface QuotaInfo {
  feature: string
  allowed: boolean
  used: number
  limit?: number
  plan_required?: string
}
