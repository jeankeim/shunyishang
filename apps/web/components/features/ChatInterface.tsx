'use client'

import { useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { ChatMessage, BaziInput } from '@/types'
import { useChatStore, RadarData, RetrievalMode, RETRIEVAL_MODE_CONFIG } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { streamRecommendation } from '@/lib/api'
import { ChatMessageItem } from './ChatMessageItem'
import { ChatInput } from './ChatInput'

interface ChatInterfaceProps {
  scene?: string
  weatherElement?: string
}

// 推荐模式切换组件
function RetrievalModeToggle({ isAuthenticated }: { isAuthenticated: boolean }) {
  const { retrievalMode, setRetrievalMode } = useChatStore()

  // 未登录时显示锁定状态
  if (!isAuthenticated) {
    return (
      <div className="flex items-center gap-2 bg-stone-100/80 rounded-xl p-1.5 border border-stone-200/60">
        <span className="text-xs text-stone-500 px-2">推荐范围</span>
        <div className="flex gap-1">
          <div className="relative px-3 py-1.5 rounded-lg text-xs font-medium text-stone-800 bg-gradient-to-r from-amber-100 to-orange-100">
            <span className="flex items-center gap-1">
              <span>🛒</span>
              <span className="hidden sm:inline">全局库</span>
            </span>
          </div>
        </div>
        <span className="text-xs text-stone-400 ml-1" title="登录后可使用更多模式">
          🔒
        </span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm rounded-xl p-1.5 border border-stone-200/60 shadow-sm">
      <span className="text-xs text-stone-500 px-2">推荐范围</span>
      <div className="flex gap-1">
        {(Object.keys(RETRIEVAL_MODE_CONFIG) as RetrievalMode[]).map((mode) => {
          const config = RETRIEVAL_MODE_CONFIG[mode]
          const isActive = retrievalMode === mode
          return (
            <motion.button
              key={mode}
              onClick={() => setRetrievalMode(mode)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`relative px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? 'text-stone-800'
                  : 'text-stone-500 hover:text-stone-700 hover:bg-stone-100'
              }`}
              title={config.description}
            >
              {isActive && (
                <motion.div
                  layoutId="activeMode"
                  className="absolute inset-0 bg-gradient-to-r from-amber-100 to-orange-100 rounded-lg"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-1">
                <span>{config.icon}</span>
                <span className="hidden sm:inline">{config.label}</span>
              </span>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}

export function ChatInterface({ scene, weatherElement }: ChatInterfaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const {
    currentConversation,
    currentConversationId,
    createConversation,
    addMessage,
    updateMessage,
    appendMessageContent,
    mergeMessageMetadata,
    setIsLoading,
    setRadarData,
    userBazi,
    retrievalMode,
  } = useChatStore()
  const { user, isAuthenticated } = useUserStore()

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  const handleSend = async (content: string, bazi?: BaziInput) => {
    let convId = currentConversationId
    if (!convId) {
      convId = createConversation()
    }

    // 用户消息
    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      createdAt: Date.now(),
    }
    addMessage(convId, userMessage)

    // AI 占位
    const aiMessageId = `msg_${Date.now() + 1}`
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
    }
    addMessage(convId, aiMessage)

    setIsLoading(true)

    // 使用传入的 bazi 参数，如果没有传入则使用 store 中的 userBazi
    const effectiveBazi = bazi ?? userBazi

    // 流式请求
    // 优先从用户资料获取性别，其次从八字输入获取
    const userGender = (user?.gender as '男' | '女' | undefined) || effectiveBazi?.gender
    
    // 未登录时强制使用 public 模式
    const effectiveRetrievalMode = isAuthenticated ? retrievalMode : 'public'
    
    // 获取用户ID（衣橱模式需要）
    const userId = user?.id
    console.log('[推荐请求] userId:', userId, 'retrievalMode:', effectiveRetrievalMode, 'isAuthenticated:', isAuthenticated)
    
    try {
      for await (const event of streamRecommendation({
        query: content,
        scene: scene || undefined,
        weather_element: weatherElement || undefined,
        bazi: effectiveBazi
          ? {
              birth_year: effectiveBazi.birthYear,
              birth_month: effectiveBazi.birthMonth,
              birth_day: effectiveBazi.birthDay,
              birth_hour: effectiveBazi.birthHour,
              gender: effectiveBazi.gender,
            }
          : undefined,
        gender: userGender,
        retrieval_mode: effectiveRetrievalMode,
        user_id: userId,
      })) {
        switch (event.type) {
          case 'analysis':
            updateMessage(convId, aiMessageId, {
              type: 'analysis',
              metadata: {
                targetElements: event.data.target_elements,
                baziAnalysis: event.data.bazi_reasoning,
                elementScores: event.data.element_scores,
                suggestedElements: event.data.suggested_elements,
              },
            })
            // 如果有八字五行数据，更新雷达图
            if (event.data.element_scores) {
              const elements = ['金', '木', '水', '火', '土']
              const suggestedElements: string[] = event.data.suggested_elements || event.data.target_elements || []
              // 建议层：喜用神高分，其他中等
              const suggestedData: Record<string, number> = {}
              elements.forEach((el) => {
                suggestedData[el] = suggestedElements.includes(el) ? 80 : 25
              })
              const radarData: RadarData = {
                currentData: event.data.element_scores,
                suggestedData,
                xiyongShen: suggestedElements,
              }
              setRadarData(radarData)
            }
            break

          case 'items':
            mergeMessageMetadata(convId, aiMessageId, { items: event.data })
            break

          case 'token':
            appendMessageContent(convId, aiMessageId, event.data)
            scrollToBottom()
            break

          case 'done':
            updateMessage(convId, aiMessageId, { type: 'done' })
            setIsLoading(false)
            break

          case 'error':
            // 根据错误内容显示更友好的提示
            const errorMsg = event.data || ''
            let userFriendlyMsg = '抱歉，服务暂时不可用，请稍后重试。'
            
            if (errorMsg.includes('衣橱')) {
              // 衣橱相关错误（需要登录）
              if (isAuthenticated) {
                userFriendlyMsg = '👗 ' + errorMsg + '\n\n💡 建议：\n1. 先添加几件衣物到您的衣橱\n2. 或切换到「智能混合」/「全局库」模式'
              } else {
                userFriendlyMsg = '👗 ' + errorMsg + '\n\n💡 建议：登录后可使用「我的衣橱」模式，获得更个性化的推荐'
              }
            } else if (errorMsg.includes('没有找到')) {
              // 未找到衣物的错误（可能是全局库为空或筛选条件太严格）
              userFriendlyMsg = '👗 ' + errorMsg + '\n\n💡 建议：\n1. 尝试调整筛选条件\n2. 更换推荐场景或天气'
            } else if (errorMsg.includes('登录')) {
              userFriendlyMsg = '🔒 ' + errorMsg
            }
            
            updateMessage(convId, aiMessageId, {
              content: userFriendlyMsg,
              type: 'error',
            })
            setIsLoading(false)
            break
        }
      }
    } catch (error) {
      updateMessage(convId, aiMessageId, {
        content: '连接失败，请检查网络后重试。',
        type: 'error',
      })
      setIsLoading(false)
    }
  }

  const messages = currentConversation?.messages || []

  return (
    <div className="flex flex-col h-full">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-stone-200/60 bg-white/50 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-stone-700">智能推荐</span>
          <span className="text-xs text-stone-400">·</span>
          <span className="text-xs text-stone-500">
            {isAuthenticated 
              ? RETRIEVAL_MODE_CONFIG[retrievalMode].description
              : '从公共种子库推荐（登录后解锁更多）'}
          </span>
        </div>
        <RetrievalModeToggle isAuthenticated={isAuthenticated} />
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-full py-8 text-stone-500">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-200/80 to-orange-200/60 flex items-center justify-center mb-4 shadow-sm">
              <span className="text-4xl">🌿</span>
            </div>
            <h2 className="text-xl font-semibold mb-2 text-stone-700">五行智能衣橱</h2>
            <p className="text-sm mb-4">输入你的穿搭需求，获取五行推荐</p>
            
            {/* 未登录提示 */}
            {!isAuthenticated && (
              <div className="mb-6 px-4 py-3 bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200/50 rounded-xl max-w-md">
                <div className="flex items-center gap-2 text-blue-700">
                  <span className="text-lg">🔓</span>
                  <span className="text-sm font-medium">
                    当前使用全局库模式
                  </span>
                </div>
                <p className="mt-1 text-xs text-stone-500">
                  登录后可解锁「我的衣橱」和「智能混合」模式，获得更个性化的推荐
                </p>
              </div>
            )}
            
            {/* 八字提示 */}
            {user?.bazi && (
              <div className="mb-6 px-4 py-3 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/50 rounded-xl max-w-md">
                <div className="flex items-center gap-2 text-amber-700">
                  <span className="text-lg">✨</span>
                  <span className="text-sm font-medium">
                    已根据您的八字（{user.bazi?.day_master || ''}日主）进行推荐
                  </span>
                </div>
                {user.xiyong_elements && user.xiyong_elements.length > 0 && (
                  <div className="mt-2 flex items-center gap-2 text-xs text-stone-500">
                    <span>喜用神:</span>
                    {user.xiyong_elements.map((el, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                        {el}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            <div className="flex flex-wrap justify-center gap-3 max-w-lg">
              {['明天面试穿什么', '周末约会推荐', '五行缺木怎么穿'].map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleSend(prompt)}
                  className="px-4 py-2 text-sm bg-gradient-to-br from-amber-100/60 to-orange-100/40 border border-amber-200/40 rounded-xl hover:from-amber-200/60 hover:to-orange-200/40 transition-all shadow-sm hover:shadow-md"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto py-4 space-y-4 px-4">
            {messages.map((message) => (
              <ChatMessageItem key={message.id} message={message} />
            ))}
          </div>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={false} bazi={userBazi || undefined} />
    </div>
  )
}
