'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChatMessage, BaziInput } from '@/types'
import { useChatStore, RadarData, RetrievalMode, RETRIEVAL_MODE_CONFIG } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { streamRecommendation } from '@/lib/api'
import { ChatMessageItem } from './ChatMessageItem'
import { ChatInput } from './ChatInput'

interface ChatInterfaceProps {
  scene?: string
  weatherElement?: string
  weatherInfo?: {  // 新增：完整天气信息
    temperature?: number
    weather_desc?: string
    humidity?: number
    wind_level?: number
  }
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
        <span className="text-xs text-[#6B7F72] ml-1" title="登录后可使用更多模式">
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

export function ChatInterface({ scene, weatherElement, weatherInfo }: ChatInterfaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [currentPrompts, setCurrentPrompts] = useState<string[]>([])
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

  // 推荐场景库 - 展示多维度推荐能力
  const PROMPT_LIBRARY = [
    // ========== 💚 简单场景（24个）- 单维度推荐 ==========
    // 场景维度
    '明天面试穿什么',
    '周末约会推荐',
    '参加派对穿什么',
    '上班通勤穿什么',
    '去海边怎么穿',
    // 五行维度
    '五行缺木怎么穿',
    '喜用神是火应该穿什么颜色',
    '八字缺金怎么补',
    '水命人适合什么颜色',
    '土命人穿搭建议',
    // 季节维度
    '春天适合什么颜色',
    '夏天怎么穿凉快',
    '秋天外套推荐',
    '冬天保暖穿搭',
    // 风格维度
    '休闲风格推荐',
    '黑色裤子怎么搭配',
    '白色T恤怎么搭',
    '牛仔裤配什么鞋',
    '今天穿什么好看',
    // 功能维度
    '运动健身穿什么',
    '居家休闲怎么穿',
    '雨天出门穿搭',
    
    // ========== 💛 中等场景（24个）- 双维度推荐 ==========
    // 场景 + 五行
    '商务会议穿搭，要显得专业（金属性）',
    '第一次约会，想给对方好印象（火属性）',
    '参加婚礼，不想太抢风头但要得体（土属性）',
    '运动后去逛街，怎么穿方便又好看（木属性）',
    '相亲第一次见面穿搭，想要温柔气质（水属性）',
    // 场景 + 身材
    '小个子女生显高穿搭技巧',
    '微胖身材怎么穿显瘦',
    '梨形身材穿搭建议',
    '苹果型身材怎么搭',
    'H型身材穿搭技巧',
    // 场景 + 职业
    '职场新人穿搭指南',
    '面试销售岗位怎么穿',
    '程序员日常穿搭推荐',
    '教师上课穿什么合适',
    '医生上班穿搭建议',
    // 季节 + 五行
    '秋冬过渡季节怎么搭配',
    '喜用神是火，冬天应该穿什么',
    '夏天穿什么颜色能降燥',
    '春秋季节适合什么五行',
    // 场景 + 风格
    '去听音乐会穿什么',
    '看话剧演出穿搭',
    '参加同学聚会怎么穿',
    '创意行业穿搭建议',
    '金融行业穿搭风格',
    
    // ========== ❤️ 复杂场景（24个）- 多维度综合推荐 ==========
    // 八字 + 天气 + 场景
    '明天要去见客户，气温15度多云，我八字喜用水，想要专业又有亲和力的搭配',
    '周末和朋友去郊外野餐，天气晴朗25度，想要舒适又有拍照效果的穿搭',
    '周末要去参加户外婚礼，天气预报说可能下雨，想要优雅又实用的搭配',
    '下周要去上海参加行业峰会，那边比较潮湿，想要专业又舒适的搭配',
    '下周要去成都出差，那边天气潮湿闷热，想要清爽又专业的搭配',
    // 八字 + 情绪 + 场景
    '今天心情不太好，想通过穿搭提升一下气场，我的喜用神是金',
    '今天是我的幸运日，想要穿得旺桃花运，我的喜用神是木和火',
    '我的日主是壬水，最近事业不顺，想通过穿搭增强水元素转运',
    '明天有重要演讲，我是火命人，想要既有权威感又不压抑的穿搭',
    '要去参加创业路演，想要穿得既有创意又值得信赖的搭配',
    // 八字 + 关系 + 场景
    '要去看望长辈，想要得体稳重但不显老气的搭配建议',
    '明天要去见未来的公婆，想要端庄大方又有亲和力的穿搭',
    '要去参加前男友的婚礼，想要穿得漂亮得体但不刻意，有什么建议',
    '要去参加孩子的家长会，想要得体又不失时尚的穿搭',
    '明天要去相亲，对方是文艺青年，想要有气质又有品味的穿搭',
    // 八字 + 五行 + 功能
    '我的八字日主是甲木，喜用神是火和土，今天想穿得旺运又有气质',
    '我八字缺金缺水，喜用神是金，想要增强财运和事业运的穿搭',
    '周末要带娃去游乐园，想要方便活动又好看的妈妈装',
    '周末要去参加马拉松，想要专业运动装备又好看的搭配',
    '要去参加慈善晚宴，想要高雅大方又符合场合的穿搭',
    '明天要去面试外企，想要国际化但又符合五行的穿搭建议',
  ]

  // 随机选择 3 个不重复的推荐示例
  useEffect(() => {
    const shuffled = [...PROMPT_LIBRARY].sort(() => Math.random() - 0.5)
    setCurrentPrompts(shuffled.slice(0, 3))
  }, [])

  // 刷新推荐示例
  const refreshPrompts = () => {
    const shuffled = [...PROMPT_LIBRARY].sort(() => Math.random() - 0.5)
    setCurrentPrompts(shuffled.slice(0, 3))
  }

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
    
    // 调试：打印八字信息
    console.log('[推荐请求] bazi 参数:', bazi)
    console.log('[推荐请求] userBazi (store):', userBazi)
    console.log('[推荐请求] effectiveBazi:', effectiveBazi)

    // 流式请求
    // 优先从用户资料获取性别，其次从八字输入获取
    const userGender = (user?.gender as '男' | '女' | undefined) || effectiveBazi?.gender
    
    // 调试日志：打印 gender 信息
    console.log('[推荐请求] user?.gender:', user?.gender)
    console.log('[推荐请求] effectiveBazi?.gender:', effectiveBazi?.gender)
    console.log('[推荐请求] 最终使用的 userGender:', userGender)
    
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
        weather: weatherInfo || undefined,  // 新增：传递完整天气信息
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
      <div className="flex items-center justify-between px-4 py-3 bg-white/50 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-stone-700">智能推荐</span>
          <span className="text-xs text-[#6B7F72]">·</span>
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
            
            <div className="flex flex-col items-center gap-4">
              <div className="flex flex-wrap justify-center gap-3 max-w-lg">
                <AnimatePresence mode="wait">
                  {currentPrompts.map((prompt, index) => (
                    <motion.button
                      key={prompt}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.1, duration: 0.3 }}
                      onClick={() => handleSend(prompt)}
                      className="px-4 py-2.5 text-sm bg-gradient-to-br from-amber-100/60 to-orange-100/40 border border-amber-200/40 rounded-xl hover:from-amber-200/60 hover:to-orange-200/40 transition-all shadow-sm hover:shadow-md hover:scale-105"
                    >
                      {prompt}
                    </motion.button>
                  ))}
                </AnimatePresence>
              </div>
              
              {/* 换一批按钮 */}
              <button
                onClick={refreshPrompts}
                className="flex items-center gap-1.5 text-xs text-stone-500 hover:text-stone-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>换一批</span>
              </button>
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
