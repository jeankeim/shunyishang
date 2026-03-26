import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { ChatMessage, Conversation, BaziInput } from '@/types'

export interface RadarData {
  currentData: Record<string, number>   // 八字五行分布（百分比）
  suggestedData: Record<string, number> // 建议补充分布
  xiyongShen: string[]                  // 喜用神列表
  pillars?: Record<string, string>      // 四柱：年柱、月柱、日柱、时柱
  eightChars?: string[]                 // 八字八个字
  dayMaster?: string                    // 日元
  elementCounts?: Record<string, number> // 五行原始计数
}

const DEFAULT_RADAR: RadarData = {
  currentData:   { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
  suggestedData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
  xiyongShen: [],
}

// 推荐检索模式
export type RetrievalMode = 'public' | 'wardrobe' | 'hybrid'

export const RETRIEVAL_MODE_CONFIG: Record<RetrievalMode, { label: string; icon: string; description: string; requiresAuth: boolean }> = {
  public: {
    label: '全局库',
    icon: '🛒',
    description: '从公共种子库推荐',
    requiresAuth: false,
  },
  wardrobe: {
    label: '我的衣橱',
    icon: '🏠',
    description: '仅从您的衣橱推荐',
    requiresAuth: true,
  },
  hybrid: {
    label: '智能混合',
    icon: '✨',
    description: '优先衣橱，不足时补充',
    requiresAuth: true,
  },
}

// 获取默认推荐模式（根据登录状态）
export function getDefaultRetrievalMode(isAuthenticated: boolean): RetrievalMode {
  return isAuthenticated ? 'hybrid' : 'public'
}

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  currentConversation: Conversation | null
  userBazi: BaziInput | null
  isLoading: boolean
  radarData: RadarData
  retrievalMode: RetrievalMode

  createConversation: () => string
  setCurrentConversation: (id: string) => void
  addMessage: (conversationId: string, message: ChatMessage) => void
  updateMessage: (conversationId: string, messageId: string, updates: Partial<ChatMessage>) => void
  appendMessageContent: (conversationId: string, messageId: string, token: string) => void
  mergeMessageMetadata: (conversationId: string, messageId: string, metadata: Partial<ChatMessage['metadata']>) => void
  setUserBazi: (bazi: BaziInput | null) => void
  setIsLoading: (loading: boolean) => void
  setRadarData: (data: RadarData) => void
  setRetrievalMode: (mode: RetrievalMode) => void
  clearConversations: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      currentConversation: null,
      userBazi: null,
      isLoading: false,
      radarData: DEFAULT_RADAR,
      retrievalMode: 'hybrid',

      createConversation: () => {
        const id = `conv_${Date.now()}`
        const conversation: Conversation = {
          id,
          title: '新对话',
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }
        set((state) => ({
          conversations: [conversation, ...state.conversations],
          currentConversationId: id,
          currentConversation: conversation,
        }))
        return id
      },

      setCurrentConversation: (id) => {
        set((state) => ({
          currentConversationId: id,
          currentConversation: state.conversations.find((c) => c.id === id) || null,
        }))
      },

      addMessage: (conversationId, message) => {
        set((state) => {
          const updatedConversations = state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, message],
                  updatedAt: Date.now(),
                  title:
                    conv.messages.length === 0 && message.role === 'user'
                      ? message.content.slice(0, 20) +
                        (message.content.length > 20 ? '...' : '')
                      : conv.title,
                }
              : conv
          )
          return {
            conversations: updatedConversations,
            currentConversation:
              updatedConversations.find((c) => c.id === state.currentConversationId) || null,
          }
        })
      },

      updateMessage: (conversationId, messageId, updates) => {
        set((state) => {
          const updatedConversations = state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === messageId ? { ...msg, ...updates } : msg
                  ),
                }
              : conv
          )
          return {
            conversations: updatedConversations,
            currentConversation:
              updatedConversations.find((c) => c.id === state.currentConversationId) || null,
          }
        })
      },

      appendMessageContent: (conversationId, messageId, token) => {
        set((state) => {
          const updatedConversations = state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === messageId ? { ...msg, content: msg.content + token } : msg
                  ),
                }
              : conv
          )
          return {
            conversations: updatedConversations,
            currentConversation:
              updatedConversations.find((c) => c.id === state.currentConversationId) || null,
          }
        })
      },

      mergeMessageMetadata: (conversationId, messageId, metadata) => {
        set((state) => {
          const updatedConversations = state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === messageId
                      ? { ...msg, metadata: { ...msg.metadata, ...metadata } }
                      : msg
                  ),
                }
              : conv
          )
          return {
            conversations: updatedConversations,
            currentConversation:
              updatedConversations.find((c) => c.id === state.currentConversationId) || null,
          }
        })
      },

      setUserBazi: (bazi) => {
        set({ userBazi: bazi })
      },

      setIsLoading: (loading) => {
        set({ isLoading: loading })
      },

      setRadarData: (data) => {
        set({ radarData: data })
      },

      setRetrievalMode: (mode) => {
        set({ retrievalMode: mode })
      },

      clearConversations: () => {
        set({ conversations: [], currentConversationId: null })
      },
    }),
    {
      name: 'wuxing-chat-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        userBazi: state.userBazi,
        retrievalMode: state.retrievalMode,
      }),
    }
  )
)
