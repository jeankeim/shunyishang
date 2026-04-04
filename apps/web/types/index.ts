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
  color?: string
  reason?: string
  image_url?: string
  source?: 'wardrobe' | 'public'
  item_id?: number
}

// ========== 聊天相关类型 ==========

export interface ChatMessageMetadata {
  targetElements?: string[]
  baziAnalysis?: string
  items?: RecommendItem[]
  elementScores?: Record<string, number>
  suggestedElements?: string[]
  scene?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
  type?: 'analysis' | 'done' | 'error'
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
