'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChatMessage, BaziInput } from '@/types'
import { useChatStore, RadarData, RetrievalMode, RETRIEVAL_MODE_CONFIG } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { streamRecommendation } from '@/lib/api'
import { ChatMessageItem } from './ChatMessageItem'
import { ChatInput } from './ChatInput'
import { toast } from '@/components/ui/Toast'

interface ChatInterfaceProps {
  scene?: string
  weatherElement?: string
  weatherInfo?: {  // 新增：完整天气信息
    temperature?: number
    temperature_max?: number
    weather_desc?: string
    humidity?: number
    wind_level?: number
  }
  userCity?: string  // 用户当前城市
  onNavigateToWardrobe?: () => void  // 推荐结果→衣橱交叉入口
}

// 推荐模式紧凑切换器（常驻顶部工具栏）：支持对话中随时切换 retrieval_mode，无需刷新页面
function RetrievalModeCompact({ isAuthenticated }: { isAuthenticated: boolean }) {
  const { retrievalMode, setRetrievalMode } = useChatStore()

  if (!isAuthenticated) return null

  return (
    <div
      className="flex items-center gap-0.5 bg-[var(--brand-surface)]/60 border border-[var(--brand-border)] rounded-full p-0.5"
      role="radiogroup"
      aria-label="推荐范围切换"
    >
      {(Object.keys(RETRIEVAL_MODE_CONFIG) as RetrievalMode[]).map((mode) => {
        const config = RETRIEVAL_MODE_CONFIG[mode]
        const isActive = retrievalMode === mode
        return (
          <button
            key={mode}
            role="radio"
            aria-checked={isActive}
            onClick={() => {
              if (isActive) return
              setRetrievalMode(mode)
              // 即时生效提示：store 已更新，下次发送即使用新模式，无需刷新
              toast.info(`已切换「${config.label}」，立即生效`, 2000)
            }}
            title={config.description}
            aria-label={`切换到${config.label}模式`}
            className={`px-2 py-1 rounded-full text-xs font-medium transition-all duration-200 ${
              isActive
                ? 'bg-white shadow-sm text-[var(--brand-heading)] border border-[var(--brand-border)]'
                : 'text-[var(--brand-subtle)] hover:text-[var(--brand-body)] border border-transparent'
            }`}
          >
            <span className="mr-0.5" aria-hidden="true">{config.icon}</span>
            <span>{config.label}</span>
          </button>
        )
      })}
    </div>
  )
}

// 推荐场景库 - 展示多维度推荐能力（模块级常量，避免每次渲染重建）
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
  '商务会议穿搭，要显得专业（金属性）',
  '第一次约会，想给对方好印象（火属性）',
  '参加婚礼，不想太抢风头但要得体（土属性）',
  '运动后去逛街，怎么穿方便又好看（木属性）',
  '相亲第一次见面穿搭，想要温柔气质（水属性）',
  '小个子女生显高穿搭技巧',
  '微胖身材怎么穿显瘦',
  '梨形身材穿搭建议',
  '苹果型身材怎么搭',
  'H型身材穿搭技巧',
  '职场新人穿搭指南',
  '面试销售岗位怎么穿',
  '程序员日常穿搭推荐',
  '教师上课穿什么合适',
  '医生上班穿搭建议',
  '秋冬过渡季节怎么搭配',
  '喜用神是火，冬天应该穿什么',
  '夏天穿什么颜色能降燥',
  '春秋季节适合什么五行',
  '去听音乐会穿什么',
  '看话剧演出穿搭',
  '参加同学聚会怎么穿',
  '创意行业穿搭建议',
  '金融行业穿搭风格',
  
  // ========== ✈️ 旅行/出差场景 ==========
  '去北京出差3天穿什么',
  '去三亚度假5天穿搭推荐',
  '去上海出差2天带什么衣服',
  '去成都旅行4天穿搭建议',
  '去哈尔滨旅游3天怎么穿',
  '去深圳出差一周穿搭规划',
  '去大理度假5天带什么衣服',
  '去西安旅行3天穿搭推荐',
  
  // ========== ❤️ 复杂场景（24个）- 多维度综合推荐 ==========
  '明天要去见客户，气温15度多云，我八字喜用水，想要专业又有亲和力的搭配',
  '周末和朋友去郊外野餐，天气晴朗25度，想要舒适又有拍照效果的穿搭',
  '周末要去参加户外婚礼，天气预报说可能下雨，想要优雅又实用的搭配',
  '下周要去上海参加行业峰会，那边比较潮湿，想要专业又舒适的搭配',
  '下周要去成都出差，那边天气潮湿闷热，想要清爽又专业的搭配',
  '今天心情不太好，想通过穿搭提升一下气场，我的喜用神是金',
  '今天是我的幸运日，想要穿得旺桃花运，我的喜用神是木和火',
  '我的日主是壬水，最近事业不顺，想通过穿搭增强水元素提升气场',
  '明天有重要演讲，我是火命人，想要既有权威感又不压抑的穿搭',
  '要去参加创业路演，想要穿得既有创意又值得信赖的搭配',
  '要去看望长辈，想要得体稳重但不显老气的搭配建议',
  '明天要去见未来的公婆，想要端庄大方又有亲和力的穿搭',
  '要去参加前男友的婚礼，想要穿得漂亮得体但不刻意，有什么建议',
  '要去参加孩子的家长会，想要得体又不失时尚的穿搭',
  '明天要去相亲，对方是文艺青年，想要有气质又有品味的穿搭',
  '我的八字日主是甲木，喜用神是火和土，今天想穿得五行相合又有气质',
  '我八字缺金缺水，喜用神是金，想要白色系为主、利落有型的穿搭',
  '周末要带娃去游乐园，想要方便活动又好看的妈妈装',
  '周末要去参加马拉松，想要专业运动装备又好看的搭配',
  '要去参加慈善晚宴，想要高雅大方又符合场合的穿搭',
  '明天要去面试外企，想要国际化但又符合五行的穿搭建议',
]

// 按场景分类的推荐示例库，确保每次展示覆盖多维度场景
const PROMPT_CATEGORIES = {
  scene: [
    '明天面试穿什么',
    '周末约会推荐',
    '参加派对穿什么',
    '去海边怎么穿',
    '去听音乐会穿什么',
    '上班通勤穿什么',
    '参加婚礼穿什么',
    '居家休闲怎么穿',
    '运动健身穿什么',
    '雨天出门穿搭',
  ],
  wuxing: [
    '五行缺木怎么穿',
    '喜用神是火应该穿什么颜色',
    '八字缺金怎么补',
    '水命人适合什么颜色',
    '土命人穿搭建议',
  ],
  season: [
    '春天适合什么颜色',
    '夏天怎么穿凉快',
    '秋天外套推荐',
    '冬天保暖穿搭',
  ],
  style: [
    '休闲风格推荐',
    '黑色裤子怎么搭配',
    '白色T恤怎么搭',
    '牛仔裤配什么鞋',
    '今天穿什么好看',
  ],
  travel: [
    '去北京出差3天穿什么',
    '去三亚度假5天穿搭推荐',
    '去成都旅行4天穿搭建议',
    '去哈尔滨旅游3天怎么穿',
  ],
  complex: [
    '商务会议穿搭，要显得专业（金属性）',
    '第一次约会，想给对方好印象（火属性）',
    '小个子女生显高穿搭技巧',
    '微胖身材怎么穿显瘦',
    '职场新人穿搭指南',
    '周末和朋友去郊外野餐，天气晴朗25度，想要舒适又有拍照效果的穿搭',
  ],
}

// 从每个分类中随机选取，确保场景多样性
function pickDiversePrompts(count: number): string[] {
  const categories = Object.values(PROMPT_CATEGORIES)
  const selected: string[] = []
  for (const cat of categories) {
    if (selected.length >= count) break
    const item = cat[Math.floor(Math.random() * cat.length)]
    if (!selected.includes(item)) selected.push(item)
  }
  if (selected.length < count) {
    const all = categories.flat()
    const shuffled = all.filter(x => !selected.includes(x)).sort(() => Math.random() - 0.5)
    selected.push(...shuffled.slice(0, count - selected.length))
  }
  return selected.sort(() => Math.random() - 0.5)
}

export function ChatInterface({ scene, weatherElement, weatherInfo, userCity, onNavigateToWardrobe }: ChatInterfaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [currentPrompts, setCurrentPrompts] = useState<string[]>([])
  const [batchIndex, setBatchIndex] = useState(0)  // 换一批：当前批次索引（0-2）
  const [lastQuery, setLastQuery] = useState<string>('')  // 换一批：记录上次查询内容
  const [lastBazi, setLastBazi] = useState<BaziInput | undefined>(undefined)  // 换一批：记录上次八字
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

  // 首次使用引导：全局模式下未填个人信息时，发起推荐前提示补充八字（用户反馈 #1）
  const [showBaziGuide, setShowBaziGuide] = useState(false)
  const dismissBaziGuide = useCallback(() => {
    setShowBaziGuide(false)
    try {
      window.localStorage.setItem('bazi_guide_dismissed', '1')
    } catch {
      /* 忽略存储异常 */
    }
  }, [])

  // 随机选择 5 个不重复的推荐示例，确保场景多样性
  useEffect(() => {
    setCurrentPrompts(pickDiversePrompts(5))
  }, [])

  // 刷新推荐示例
  const refreshPrompts = () => {
    setCurrentPrompts(pickDiversePrompts(5))
  }

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  // 滚动到顶部（用于打开海报）
  const scrollToTop = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    }
  }, [])

  // 滚动到指定消息（用于关闭海报）
  const scrollToMessage = useCallback((messageId: string) => {
    if (scrollRef.current) {
      const messageElement = scrollRef.current.querySelector(`[data-message-id="${messageId}"]`)
      if (messageElement) {
        messageElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        })
      }
    }
  }, [])

  const handleSend = async (content: string, bazi?: BaziInput) => {
    let convId = currentConversationId
    if (!convId) {
      convId = createConversation()
    }

    // 保存查询内容用于"换一批"功能
    setLastQuery(content)
    setLastBazi(bazi ?? userBazi ?? undefined)
    setBatchIndex(0)  // 新查询重置批次

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

    // 首次使用引导：未填写八字/性别等个人信息时，温和提示补充可获更精准推荐（一次性，用户反馈 #1）
    if (!effectiveBazi && !user?.bazi && !showBaziGuide) {
      try {
        if (typeof window === 'undefined' || !window.localStorage.getItem('bazi_guide_dismissed')) {
          setShowBaziGuide(true)
        }
      } catch {
        setShowBaziGuide(true)
      }
    }
    
    // 流式请求
    // 优先从用户资料获取性别，其次从八字输入获取
    const userGender = (user?.gender as '男' | '女' | undefined) || effectiveBazi?.gender
    
    // 未登录时强制使用 public 模式
    const effectiveRetrievalMode = isAuthenticated ? retrievalMode : 'public'
    
    // 获取用户ID（衣橱模式需要）
    const userId = user?.id
    
    // 防御性降级：衣橱/智能混合模式需要 user_id，若用户资料尚未加载完成则降级为 public
    const finalRetrievalMode = (effectiveRetrievalMode !== 'public' && !userId) ? 'public' : effectiveRetrievalMode
    // 构建请求参数
    const requestParams = {
      query: content,
      scene: scene || undefined,
      weather_element: weatherElement || undefined,
      weather: weatherInfo || undefined,
      // 兜底城市：weather 缺失时后端据此取天气，保证温度过滤生效
      city: userCity || undefined,
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
      retrieval_mode: finalRetrievalMode,
      user_id: userId,
      user_city: userCity || undefined,
      batch_index: batchIndex,
    }
    try {
      const startTime = Date.now()
      
      for await (const event of streamRecommendation(requestParams)) {
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

          case 'travel_plan':
            // 保存多天行程规划数据到消息 metadata
            mergeMessageMetadata(convId, aiMessageId, { travelPlan: event.data })
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

          case 'hint':
            // 非穿搭意图提示：显示友好引导文案
            updateMessage(convId, aiMessageId, {
              content: event.data,
              type: 'hint',
            })
            break

          case 'notice':
            // 后端软降级通知（如衣橱→公共库）：以温和横幅追加，不打断推荐结果
            mergeMessageMetadata(convId, aiMessageId, {
              notice: typeof event.data === 'string' ? event.data : String(event.data ?? ''),
            })
            break

          case 'error':
            // 根据错误内容显示更友好的提示
            // 安全提取：后端通常返回字符串，防御 object/null 导致 .includes 报错
            const errorMsg = typeof event.data === 'string' ? event.data : (event.data == null ? '' : JSON.stringify(event.data))
            let userFriendlyMsg = '抱歉，服务暂时不可用，请稍后重试。'
            
            // 调试：打印错误信息
            console.error('[推荐错误] 收到错误事件:', event)
            
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
            } else if (errorMsg.trim() === '') {
              // 空错误信息，可能是流处理中的临时问题，忽略
              console.warn('[推荐] 收到空错误事件，忽略')
              return
            } else if (finalRetrievalMode === 'wardrobe') {
              // 衣橱模式下的未知错误：通常是衣橱为空或衣物缺少语义向量
              userFriendlyMsg = '👗 暂时无法从您的衣橱生成推荐。\n\n💡 建议：\n1. 确认衣橱中已添加衣物\n2. 或切换到「智能混合」/「全局库」模式再试'
            }
            
            // 如果已经有推荐卡片，不覆盖错误信息，只在控制台记录
            const currentMessages = useChatStore.getState().conversations.find(c => c.id === convId)?.messages || []
            const currentMessage = currentMessages.find(m => m.id === aiMessageId)
            if (currentMessage?.metadata?.items && currentMessage.metadata.items.length > 0) {
              console.warn('[推荐] 已有推荐卡片，忽略错误事件:', errorMsg)
              return
            }
            
            updateMessage(convId, aiMessageId, {
              content: userFriendlyMsg,
              type: 'error',
            })
            setIsLoading(false)
            break
        }
      }
      // 流式处理完成
    } catch (error) {
      console.error('[推荐请求] 异常:', error)
      updateMessage(convId, aiMessageId, {
        content: '连接失败，请检查网络后重试。',
        type: 'error',
      })
      setIsLoading(false)
    }
  }

  // 换一批：重新请求相同查询但不同批次
  const handleRefreshBatch = async () => {
    if (!lastQuery || batchIndex >= 2) return  // 最多3批（0, 1, 2）
    
    const newBatchIndex = batchIndex + 1
    setBatchIndex(newBatchIndex)
    
    // 使用保存的查询参数重新发送请求
    let convId = currentConversationId
    if (!convId) {
      convId = createConversation()
    }

    // AI 占位消息
    const aiMessageId = `msg_${Date.now()}`
    const aiMessage: ChatMessage = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
    }
    addMessage(convId, aiMessage)
    setIsLoading(true)

    const effectiveBazi = lastBazi ?? userBazi
    const userGender = (user?.gender as '男' | '女' | undefined) || effectiveBazi?.gender
    const effectiveRetrievalMode = isAuthenticated ? retrievalMode : 'public'
    const userId = user?.id
    const finalRetrievalMode = (effectiveRetrievalMode !== 'public' && !userId) ? 'public' : effectiveRetrievalMode

    const requestParams = {
      query: lastQuery,
      scene: scene || undefined,
      weather_element: weatherElement || undefined,
      weather: weatherInfo || undefined,
      // 兜底城市：weather 缺失时后端据此取天气，保证温度过滤生效
      city: userCity || undefined,
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
      retrieval_mode: finalRetrievalMode,
      user_id: userId,
      user_city: userCity || undefined,
      batch_index: newBatchIndex,
    }

    try {
      for await (const event of streamRecommendation(requestParams)) {
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
            if (event.data.element_scores) {
              const elements = ['金', '木', '水', '火', '土']
              const suggestedElements: string[] = event.data.suggested_elements || event.data.target_elements || []
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
          case 'travel_plan':
            mergeMessageMetadata(convId, aiMessageId, { travelPlan: event.data })
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
          case 'hint':
            updateMessage(convId, aiMessageId, {
              content: event.data,
              type: 'hint',
            })
            break
          case 'notice':
            mergeMessageMetadata(convId, aiMessageId, {
              notice: typeof event.data === 'string' ? event.data : String(event.data ?? ''),
            })
            break
          case 'error':
            const errorMsg = typeof event.data === 'string' ? event.data : ''
            updateMessage(convId, aiMessageId, {
              content: errorMsg || '换一批失败，请稍后重试',
              type: 'error',
            })
            setIsLoading(false)
            break
        }
      }
    } catch (error) {
      console.error('[换一批] 异常:', error)
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
      {/* 顶部工具栏：推荐范围切换器常驻，对话中随时切换、无需刷新 */}
      <div className="flex items-center justify-between px-4 py-3 bg-white/50 backdrop-blur-sm border-b border-stone-200/60">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-stone-700 shrink-0">智能推荐</span>
          {!isAuthenticated && (
            <>
              <span className="text-xs text-stone-400">·</span>
              <span className="text-xs text-stone-500 truncate">从公共种子库推荐（登录后解锁更多）</span>
            </>
          )}
        </div>
        {/* 常驻模式切换器：登录后随时切换推荐范围，下次发送即生效 */}
        <RetrievalModeCompact isAuthenticated={isAuthenticated} />
      </div>

      {/* 首次使用引导：提示补充八字/性别可获得更精准推荐（用户反馈 #1） */}
      <AnimatePresence>
        {showBaziGuide && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="mx-4 mt-3 px-4 py-3 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/60 rounded-xl">
              <div className="flex items-start gap-2">
                <span className="text-lg leading-none mt-0.5">✨</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-stone-700">补充个人信息，推荐更精准</p>
                  <p className="text-xs text-stone-500 mt-1 leading-relaxed">
                    当前为通用推荐。在首页「八字输入」面板填写出生日期、时辰与性别后，
                    即可基于您的喜用神进行个性化五行穿搭推荐。
                  </p>
                </div>
                <button
                  onClick={dismissBaziGuide}
                  className="p-1 rounded-lg hover:bg-amber-100/60 text-stone-400 hover:text-stone-600 transition-colors shrink-0"
                  aria-label="关闭引导提示"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center min-h-full py-8 text-stone-500">
            <div className="w-20 h-20 rounded-2xl bg-[var(--brand-surface)] flex items-center justify-center mb-4 shadow-sm">
              <span className="text-4xl">🌿</span>
            </div>
            <h2 className="text-xl font-semibold mb-2 text-[var(--brand-heading)]">我的个人衣橱</h2>
            <p className="text-sm mb-4 text-[var(--brand-subtle)]">输入你的穿搭需求，获取五行推荐；顶部可随时切换推荐范围，底部导航可切换「衣橱」管理衣物</p>
            
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
              <div className="mb-6 px-4 py-3 bg-[var(--brand-surface)]/60 border border-[var(--brand-border)] rounded-xl max-w-md">
                <div className="flex items-center gap-2 text-[var(--brand-body)]">
                  <span className="text-lg">✨</span>
                  <span className="text-sm font-medium">
                    已根据您的八字（{user.bazi?.day_master || ''}日主）进行推荐
                  </span>
                </div>
                {user.xiyong_elements && user.xiyong_elements.length > 0 && (
                  <div className="mt-2 flex items-center gap-2 text-xs text-[var(--brand-subtle)]">
                    <span>喜用神:</span>
                    {user.xiyong_elements.map((el, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-[var(--wuxing-wood)]/15 text-[var(--wuxing-wood)] rounded-full">
                        {el}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* 推荐范围切换器已常驻顶部工具栏，空状态不再重复展示 */}
                        
            <div className="flex flex-col items-center gap-4">
              <div className="flex flex-wrap justify-center gap-3 max-w-2xl">
                <AnimatePresence mode="sync">
                  {currentPrompts.map((prompt, index) => (
                    <motion.button
                      key={prompt}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.1, duration: 0.3 }}
                      onClick={() => handleSend(prompt)}
                      aria-label={`发送推荐请求：${prompt}`}
                      whileTap={{ scale: 0.95 }}
                      className="px-3 py-2 min-h-[36px] text-xs bg-[var(--brand-surface)]/60 border border-[var(--brand-border)] rounded-lg hover:bg-[var(--brand-surface-active)] transition-all duration-200 shadow-sm hover:shadow-md touch-manipulation leading-snug text-[var(--brand-body)]"
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
          <div className="max-w-5xl mx-auto py-4 space-y-4 px-4">
            {messages.map((message) => (
              <ChatMessageItem 
                key={message.id} 
                message={message} 
                onOpenPoster={scrollToTop}
                onClosePoster={() => scrollToMessage(message.id)}
                onRefreshBatch={handleRefreshBatch}
                onNavigateToWardrobe={onNavigateToWardrobe}
                batchIndex={batchIndex}
                isLoading={false}
              />
            ))}
          </div>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={false} bazi={userBazi || undefined} />
    </div>
  )
}
