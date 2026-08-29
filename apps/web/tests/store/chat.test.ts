import { describe, it, expect, beforeEach } from 'vitest'
import { useChatStore, getDefaultRetrievalMode, RETRIEVAL_MODE_CONFIG, RadarData } from '@/store/chat'
import { ChatMessage } from '@/types'

describe('useChatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      conversations: [],
      currentConversationId: null,
      currentConversation: null,
      userBazi: null,
      isLoading: false,
      radarData: {
        currentData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
        suggestedData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
        xiyongShen: [],
      },
      retrievalMode: 'wardrobe',
    })
  })

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useChatStore.getState()
      expect(state.conversations).toEqual([])
      expect(state.currentConversationId).toBeNull()
      expect(state.currentConversation).toBeNull()
      expect(state.userBazi).toBeNull()
      expect(state.isLoading).toBe(false)
      expect(state.retrievalMode).toBe('wardrobe')
    })

    it('should have default radar data', () => {
      const state = useChatStore.getState()
      expect(state.radarData.currentData).toEqual({
        '金': 20, '木': 20, '水': 20, '火': 20, '土': 20,
      })
      expect(state.radarData.xiyongShen).toEqual([])
    })
  })

  describe('createConversation', () => {
    it('should create a new conversation', () => {
      const id = useChatStore.getState().createConversation()

      expect(id).toMatch(/^conv_\d+$/)
      const state = useChatStore.getState()
      expect(state.conversations).toHaveLength(1)
      expect(state.conversations[0].id).toBe(id)
      expect(state.conversations[0].title).toBe('新对话')
      expect(state.conversations[0].messages).toEqual([])
      expect(state.currentConversationId).toBe(id)
      expect(state.currentConversation?.id).toBe(id)
    })

    it('should prepend new conversation to existing ones', () => {
      const id1 = useChatStore.getState().createConversation()
      const id2 = useChatStore.getState().createConversation()

      const state = useChatStore.getState()
      expect(state.conversations).toHaveLength(2)
      expect(state.conversations[0].id).toBe(id2)
      expect(state.conversations[1].id).toBe(id1)
    })
  })

  describe('setCurrentConversation', () => {
    it('should set current conversation by id', () => {
      const id1 = useChatStore.getState().createConversation()
      const id2 = useChatStore.getState().createConversation()

      useChatStore.getState().setCurrentConversation(id1)

      const state = useChatStore.getState()
      expect(state.currentConversationId).toBe(id1)
      expect(state.currentConversation?.id).toBe(id1)
    })

    it('should set currentConversation to null when id not found', () => {
      useChatStore.getState().createConversation()

      useChatStore.getState().setCurrentConversation('nonexistent')

      const state = useChatStore.getState()
      expect(state.currentConversationId).toBe('nonexistent')
      expect(state.currentConversation).toBeNull()
    })
  })

  describe('addMessage', () => {
    it('should add message to conversation', () => {
      const convId = useChatStore.getState().createConversation()
      const message: ChatMessage = {
        id: 'msg1',
        role: 'user',
        content: 'Hello',
        createdAt: Date.now(),
      }

      useChatStore.getState().addMessage(convId, message)

      const state = useChatStore.getState()
      expect(state.conversations[0].messages).toHaveLength(1)
      expect(state.conversations[0].messages[0]).toEqual(message)
    })

    it('should update conversation title for first user message', () => {
      const convId = useChatStore.getState().createConversation()
      const message: ChatMessage = {
        id: 'msg1',
        role: 'user',
        content: '今天穿什么好呢？',
        createdAt: Date.now(),
      }

      useChatStore.getState().addMessage(convId, message)

      const state = useChatStore.getState()
      expect(state.conversations[0].title).toBe('今天穿什么好呢？')
    })

    it('should truncate title for long first user message', () => {
      const convId = useChatStore.getState().createConversation()
      const longContent = '这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常长的消息'
      const message: ChatMessage = {
        id: 'msg1',
        role: 'user',
        content: longContent,
        createdAt: Date.now(),
      }

      useChatStore.getState().addMessage(convId, message)

      const state = useChatStore.getState()
      expect(state.conversations[0].title).toBe(longContent.slice(0, 20) + '...')
    })

    it('should not update title for assistant message', () => {
      const convId = useChatStore.getState().createConversation()
      const message: ChatMessage = {
        id: 'msg1',
        role: 'assistant',
        content: 'Hello',
        createdAt: Date.now(),
      }

      useChatStore.getState().addMessage(convId, message)

      const state = useChatStore.getState()
      expect(state.conversations[0].title).toBe('新对话')
    })

    it('should not update title for non-first message', () => {
      const convId = useChatStore.getState().createConversation()
      const msg1: ChatMessage = {
        id: 'msg1',
        role: 'user',
        content: 'First message',
        createdAt: Date.now(),
      }
      useChatStore.getState().addMessage(convId, msg1)

      const msg2: ChatMessage = {
        id: 'msg2',
        role: 'user',
        content: 'Second message that is different',
        createdAt: Date.now(),
      }
      useChatStore.getState().addMessage(convId, msg2)

      const state = useChatStore.getState()
      expect(state.conversations[0].title).toBe('First message')
    })
  })

  describe('updateMessage', () => {
    it('should update message in conversation', () => {
      const convId = useChatStore.getState().createConversation()
      const message: ChatMessage = {
        id: 'msg1',
        role: 'assistant',
        content: 'Hello',
        createdAt: Date.now(),
      }
      useChatStore.getState().addMessage(convId, message)

      useChatStore.getState().updateMessage(convId, 'msg1', { content: 'Updated content' })

      const state = useChatStore.getState()
      expect(state.conversations[0].messages[0].content).toBe('Updated content')
    })
  })

  describe('appendMessageContent', () => {
    it('should append token to message content', () => {
      const convId = useChatStore.getState().createConversation()
      const message: ChatMessage = {
        id: 'msg1',
        role: 'assistant',
        content: 'Hello',
        createdAt: Date.now(),
      }
      useChatStore.getState().addMessage(convId, message)

      useChatStore.getState().appendMessageContent(convId, 'msg1', ' World')

      const state = useChatStore.getState()
      expect(state.conversations[0].messages[0].content).toBe('Hello World')
    })
  })

  describe('mergeMessageMetadata', () => {
    it('should merge metadata into message', () => {
      const convId = useChatStore.getState().createConversation()
      const message: ChatMessage = {
        id: 'msg1',
        role: 'assistant',
        content: 'Hello',
        createdAt: Date.now(),
        metadata: { targetElements: ['木'] },
      }
      useChatStore.getState().addMessage(convId, message)

      useChatStore.getState().mergeMessageMetadata(convId, 'msg1', { scene: 'office' })

      const state = useChatStore.getState()
      expect(state.conversations[0].messages[0].metadata).toEqual({
        targetElements: ['木'],
        scene: 'office',
      })
    })
  })

  describe('replaceMessageItem', () => {
    const makeMessage = (): ChatMessage => ({
      id: 'msg1',
      role: 'assistant',
      content: '推荐结果',
      createdAt: Date.now(),
      metadata: {
        items: [
          { item_code: 'TC001', name: '白色衬衫', category: '上装', primary_element: '金', final_score: 0.9 },
          { item_code: 'SH002', name: '黑色皮鞋', category: '鞋履', primary_element: '水', final_score: 0.8 },
        ],
      },
    })

    it('should replace the matched item in place, keeping others untouched', () => {
      const convId = useChatStore.getState().createConversation()
      useChatStore.getState().addMessage(convId, makeMessage())

      useChatStore.getState().replaceMessageItem(convId, 'msg1', 'TC001', {
        item_code: 'wardrobe-101',
        item_id: 101,
        name: '米白衬衫',
        category: '上装',
        primary_element: '金',
        final_score: 0.9,
        source: 'wardrobe',
      })

      const items = useChatStore.getState().conversations[0].messages[0].metadata!.items as any[]
      expect(items).toHaveLength(2)
      expect(items[0].item_code).toBe('wardrobe-101')
      expect(items[0].name).toBe('米白衬衫')
      expect(items[0].source).toBe('wardrobe')
      // 其他槽位不受影响
      expect(items[1].item_code).toBe('SH002')
    })

    it('should be reversible (undo by replacing back)', () => {
      const convId = useChatStore.getState().createConversation()
      const original = makeMessage().metadata!.items![0]
      useChatStore.getState().addMessage(convId, makeMessage())

      const store = useChatStore.getState()
      store.replaceMessageItem(convId, 'msg1', 'TC001', {
        item_code: 'wardrobe-101', name: '米白衬衫', category: '上装', primary_element: '金', final_score: 0.9, source: 'wardrobe',
      })
      useChatStore.getState().replaceMessageItem(convId, 'msg1', 'wardrobe-101', original as any)

      const items = useChatStore.getState().conversations[0].messages[0].metadata!.items as any[]
      expect(items[0].item_code).toBe('TC001')
      expect(items[0].name).toBe('白色衬衫')
    })

    it('should be no-op when item_code does not match', () => {
      const convId = useChatStore.getState().createConversation()
      useChatStore.getState().addMessage(convId, makeMessage())

      useChatStore.getState().replaceMessageItem(convId, 'msg1', 'NOPE', {
        item_code: 'wardrobe-999', name: 'X', category: '上装', primary_element: '金', final_score: 0.5,
      })

      const items = useChatStore.getState().conversations[0].messages[0].metadata!.items as any[]
      expect(items.map((i) => i.item_code)).toEqual(['TC001', 'SH002'])
    })
  })

  describe('setUserBazi', () => {
    it('should set user bazi', () => {
      const bazi = {
        birthYear: 1990,
        birthMonth: 5,
        birthDay: 15,
        birthHour: 8,
        gender: '男' as const,
      }

      useChatStore.getState().setUserBazi(bazi)

      expect(useChatStore.getState().userBazi).toEqual(bazi)
    })

    it('should set user bazi to null', () => {
      useChatStore.getState().setUserBazi(null)
      expect(useChatStore.getState().userBazi).toBeNull()
    })
  })

  describe('setIsLoading', () => {
    it('should set loading state', () => {
      useChatStore.getState().setIsLoading(true)
      expect(useChatStore.getState().isLoading).toBe(true)

      useChatStore.getState().setIsLoading(false)
      expect(useChatStore.getState().isLoading).toBe(false)
    })
  })

  describe('setRadarData', () => {
    it('should set radar data', () => {
      const newRadar: RadarData = {
        currentData: { '金': 30, '木': 10, '水': 20, '火': 20, '土': 20 },
        suggestedData: { '金': 10, '木': 30, '水': 20, '火': 20, '土': 20 },
        xiyongShen: ['木'],
      }

      useChatStore.getState().setRadarData(newRadar)

      expect(useChatStore.getState().radarData).toEqual(newRadar)
    })
  })

  describe('setRetrievalMode', () => {
    it('should set retrieval mode', () => {
      useChatStore.getState().setRetrievalMode('public')
      expect(useChatStore.getState().retrievalMode).toBe('public')

      useChatStore.getState().setRetrievalMode('wardrobe')
      expect(useChatStore.getState().retrievalMode).toBe('wardrobe')
    })
  })

  describe('clearConversations', () => {
    it('should clear all conversations', () => {
      useChatStore.getState().createConversation()
      useChatStore.getState().createConversation()

      useChatStore.getState().clearConversations()

      const state = useChatStore.getState()
      expect(state.conversations).toEqual([])
      expect(state.currentConversationId).toBeNull()
    })
  })
})

describe('getDefaultRetrievalMode', () => {
  it('should return wardrobe when authenticated', () => {
    expect(getDefaultRetrievalMode(true)).toBe('wardrobe')
  })

  it('should return public when not authenticated', () => {
    expect(getDefaultRetrievalMode(false)).toBe('public')
  })
})

describe('RETRIEVAL_MODE_CONFIG', () => {
  it('should have correct config for public mode (灵感库)', () => {
    expect(RETRIEVAL_MODE_CONFIG.public.label).toBe('灵感库')
    expect(RETRIEVAL_MODE_CONFIG.public.requiresAuth).toBe(false)
  })

  it('should have correct config for wardrobe mode', () => {
    expect(RETRIEVAL_MODE_CONFIG.wardrobe.label).toBe('我的衣橱')
    expect(RETRIEVAL_MODE_CONFIG.wardrobe.requiresAuth).toBe(true)
  })

  it('should not expose hybrid mode in UI', () => {
    expect('hybrid' in RETRIEVAL_MODE_CONFIG).toBe(false)
  })
})
