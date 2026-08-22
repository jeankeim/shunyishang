'use client'

import { useState, useEffect, lazy, Suspense, useCallback } from 'react'
import { FiveElementRadar } from '@/components/features/FiveElementRadar'
import { FiveElementList } from '@/components/features/FiveElementList'
import { ChatInterface } from '@/components/features/ChatInterface'
import { BaziInputSection } from '@/components/features/BaziInputSection'
import { BaziCard } from '@/components/features/BaziCard'
import { WeatherSceneSection } from '@/components/features/WeatherSceneSection'
import { UserProfile } from '@/components/features/UserProfile'
import { Sidebar } from '@/components/features/Sidebar'
import { Header } from '@/components/features/Header'
import { MobileControlPanel } from '@/components/features/MobileControlPanel'
import { MobileBottomNav } from '@/components/features/MobileBottomNav'
import { DailyRitualCard } from '@/components/features/DailyRitualCard'
import { DailyOutfitCard } from '@/components/features/DailyOutfitCard'
import { QuickCheckIn } from '@/components/features/QuickCheckIn'
import { IcpFooter } from '@/components/features/IcpFooter'
import { PullToRefresh } from '@/components/features/PullToRefresh'
import { useChatStore } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { requestChatInputAutofill } from '@/lib/chatAutofill'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { motion, AnimatePresence } from 'framer-motion'
import { BookOpen, Mountain, Compass, MoreHorizontal } from 'lucide-react'
import { SkeletonCard } from '@/components/ui'

// 懒加载衣橱页面，减少首页初始加载时间
const WardrobePage = lazy(() => import('./wardrobe/page'))
const DiaryPage = lazy(() => import('./diary/page'))
const CommunityPage = lazy(() => import('./community/page'))
const CultivationPage = lazy(() => import('./cultivation/page'))
// 运势 + 命理 合并为综合页面
const DestinyFortuneHub = lazy(() => import('@/components/features/DestinyFortuneHub').then(m => ({ default: m.DestinyFortuneHub })))
const WuxingClassroomPage = lazy(() => import('./wuxing-classroom/page'))
const AuthModal = lazy(() => import('@/components/features/AuthModal').then(m => ({ default: m.AuthModal })))

// 统一的页面加载骨架屏
function PageLoadingFallback() {
  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
      <SkeletonCard lines={2} />
      <SkeletonCard lines={1} />
      <SkeletonCard lines={3} showImage={false} />
      <SkeletonCard lines={2} showImage={false} />
    </div>
  )
}

// ============================================================
// 快捷推荐栏 — 一键推荐入口
// ============================================================
function QuickRecommendBar({
  weatherElement,
  weatherInfo,
  userCity,
  onFocusChat,
}: {
  weatherElement: string
  weatherInfo: any
  userCity: string
  onFocusChat: () => void
}) {
  const quickRecs = [
    {
      icon: '✨',
      label: '今日运势推荐',
      desc: weatherInfo
        ? `${weatherInfo.temperature || '--'}°C ${weatherInfo.weather_desc || ''}`
        : '基于五行幸运色推荐',
      query: '根据今日运势和五行喜忌，推荐今日穿搭',
      gradient: 'from-amber-50 to-orange-50 border-amber-200/60',
    },
    {
      icon: '🌤️',
      label: '天气适配穿搭',
      desc: userCity ? `${userCity} · 实时天气` : '根据天气智能搭配',
      query: `今天${userCity || ''}天气${weatherInfo?.weather_desc || ''}，推荐适合的穿搭`,
      gradient: 'from-blue-50 to-cyan-50 border-blue-200/60',
    },
    {
      icon: '🎯',
      label: '场景智能推荐',
      desc: '面试·约会·通勤·旅行',
      query: '',
      gradient: 'from-emerald-50 to-teal-50 border-emerald-200/60',
    },
  ]

  const handleQuickRec = (query: string) => {
    onFocusChat()
    // 将推荐查询写入聊天输入框
    const chatInput = document.querySelector('textarea[placeholder*="穿搭"]') as HTMLTextAreaElement | null
    if (chatInput && query) {
      // 使用原生方法设置值并触发 input 事件（React 需要）
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
      )?.set
      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(chatInput, query)
        chatInput.dispatchEvent(new Event('input', { bubbles: true }))
      }
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="mb-4"
    >
      <p className="text-xs text-stone-500 mb-2 font-medium">💡 快捷推荐</p>
      <div className="grid grid-cols-3 gap-2">
        {quickRecs.map((rec, i) => (
          <motion.button
            key={i}
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => handleQuickRec(rec.query)}
            className={`flex flex-col items-center gap-1 p-3 rounded-xl bg-gradient-to-br ${rec.gradient} border text-left transition-all hover:shadow-sm`}
          >
            <span className="text-lg">{rec.icon}</span>
            <span className="text-xs font-semibold text-stone-700">{rec.label}</span>
            <span className="text-[10px] text-stone-500 text-center leading-tight">{rec.desc}</span>
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}

export default function Home() {
  const { radarData, setUserBazi } = useChatStore()
  const { user, isAuthenticated, isLoading: isAuthLoading } = useUserStore()
  const [mounted, setMounted] = useState(false)
  const [scene, setScene] = useState('')
  const [sceneElement, setSceneElement] = useState('')
    const [weatherElement, setWeatherElement] = useState('')
  const [weatherInfo, setWeatherInfo] = useState<any>(null)  // 新增：保存完整天气信息
  const [userCity, setUserCity] = useState<string>('')  // 用户当前城市
  const [activeTab, setActiveTab] = useState<'chat' | 'wardrobe' | 'tryon' | 'profile' | 'diary' | 'fortune' | 'destiny' | 'community' | 'cultivation' | 'wuxing-classroom'>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [showCheckIn, setShowCheckIn] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showMoreMenu, setShowMoreMenu] = useState(false)
  const [smartAlerts, setSmartAlerts] = useState<string[]>([])
  
  // 判断用户是否有八字（已登录且资料完整）
  const hasBazi = isAuthenticated && !isAuthLoading && user?.bazi
  
  // 智能提醒检查（天气变化 + 衣橱闲置）
  useEffect(() => {
    if (isAuthenticated && !isAuthLoading) {
      import('@/lib/api').then(({ checkSmartReminders }) => {
        checkSmartReminders(weatherInfo).then(data => {
          if (data?.alerts?.length > 0) {
            setSmartAlerts(data.alerts.map((a: any) => a.message))
          }
        }).catch(() => {})
      })
    }
  }, [isAuthenticated, isAuthLoading])

  // 当用户有八字信息时，自动设置 userBazi 到 chat store
  useEffect(() => {
    if (hasBazi && user?.birth_date && user?.gender) {
      const birthDate = new Date(user.birth_date)
      const baziInput = {
        birthYear: birthDate.getFullYear(),
        birthMonth: birthDate.getMonth() + 1,
        birthDay: birthDate.getDate(),
        birthHour: user.birth_time ? parseInt(user.birth_time.split(':')[0]) : 12,
        gender: user.gender as '男' | '女',
      }
      setUserBazi(baziInput)
    }
  }, [hasBazi, user, setUserBazi])

  // 监听hash变化
  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#profile') {
        setActiveTab('profile')
      } else if (window.location.hash === '#wardrobe') {
        setActiveTab('wardrobe')
      } else if (window.location.hash === '#diary') {
        setActiveTab('diary')
      } else if (window.location.hash === '#fortune') {
        setActiveTab('fortune')
      } else if (window.location.hash === '#destiny') {
        setActiveTab('destiny')
      } else if (window.location.hash === '#cultivation') {
        setActiveTab('cultivation')
      } else if (window.location.hash === '#wuxing-classroom') {
        setActiveTab('wuxing-classroom')
      } else {
        setActiveTab('chat')
      }
    }

    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const handleSceneChange = (sceneId: string, element: string, sceneLabel?: string) => {
    setScene(sceneId)
    setSceneElement(element)
    // 常用场景联动：选中场景后将场景名称自动填充到推荐输入框，取消选择时同步清空
    requestChatInputAutofill(sceneLabel || '')
  }

  const handleWeatherChange = (weather: any) => {
    setWeatherElement(weather.element)
    setWeatherInfo({  // 保存完整天气信息
      temperature: weather.temperature,
      temperature_max: weather.temperature_max,
      weather_desc: weather.weather,
      humidity: weather.humidity,
      wind_level: parseInt(weather.wind?.replace('级', '') || '0'),
    })
    setUserCity(weather.city || '')  // 保存城市名
  }

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  // 下拉刷新功能
  const handleRefresh = useCallback(async () => {
    // 清空当前对话和推荐结果
    useChatStore.getState().clearConversations()
    useChatStore.getState().setRadarData({
      currentData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
      suggestedData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
      xiyongShen: [],
    })
    setScene('')
    setSceneElement('')
    setWeatherElement('')
    setWeatherInfo(null)
    // 等待一小段时间让用户看到刷新反馈
    await new Promise(resolve => setTimeout(resolve, 500))
  }, [])

  const isMobile = useMediaQuery('(max-width: 768px)')

  // 客户端挂载后再渲染完整 UI，避免 SSR hydration 不匹配
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <div className="flex h-dvh bg-stone-50 overflow-hidden">
        {/* 左侧骨架屏 - 匹配最终布局结构，减少布局偏移 */}
        <div className="w-[280px] lg:w-[320px] hidden md:block bg-white/90 p-5 space-y-5">
          <div className="text-center mb-4">
            <div className="h-8 w-24 mx-auto bg-stone-200 rounded-lg animate-pulse" />
            <div className="h-4 w-32 mx-auto mt-2 bg-stone-100 rounded animate-pulse" />
          </div>
          <div className="h-32 bg-stone-100 rounded-xl animate-pulse" />
          <div className="h-40 bg-stone-100 rounded-xl animate-pulse" />
        </div>
        {/* 右侧主内容骨架 */}
        <div className="flex-1 flex flex-col">
          <div className="hidden md:block h-14 border-b border-stone-200/60 bg-white" />
          <div className="md:hidden h-12 border-b border-stone-200/60 bg-white/90 flex items-center px-4">
            <div className="h-5 w-16 bg-stone-200 rounded animate-pulse" />
          </div>
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-2xl bg-[var(--brand-surface)] flex items-center justify-center">
                <span className="text-3xl">🌿</span>
              </div>
              <div className="h-4 w-24 bg-stone-200 rounded animate-pulse" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-dvh bg-stone-50 overflow-hidden">
      {/* Sidebar - 聊天记录面板 */}
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={toggleSidebar}
      />

      {/* 左侧：清新五行风格控制面板 - 移动端优化 */}
      <motion.div 
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className={`bg-white/90 backdrop-blur-xl overflow-y-auto transition-all duration-300 scrollbar-hide ${
          hasBazi 
            ? 'w-[280px] lg:w-[320px]' 
            : 'w-[300px] lg:w-[340px]'
        } hidden md:block`}
      >
        <div className="space-y-5">
        {/* 标题区域 - 清雅书法风格 */}
        <motion.div 
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-center mb-4"
        >
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[var(--wuxing-wood)] via-[var(--wuxing-water)] to-[var(--wuxing-fire)] bg-clip-text text-transparent font-serif tracking-tight">
            五行穿搭
          </h1>
          <p className="text-sm text-[var(--brand-body)] font-light tracking-wide mt-2">
            {hasBazi ? '您的专属五行穿搭推荐' : '基于传统文化的每日穿搭灵感'}
          </p>
        </motion.div>

        {/* 八字区域：有八字显示卡片，无八字显示输入 */}
        {hasBazi ? (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <BaziCard 
              onEdit={() => {
                setActiveTab('profile')
                window.location.hash = '#profile'
              }}
            />
          </motion.div>
        ) : (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="card-secondary p-5 bg-gradient-to-br from-[var(--brand-surface)]/80 to-[var(--brand-surface-active)]/60 hover:shadow-[0_6px_24px_rgba(61,163,93,0.12)] transition-all duration-300 group"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2.5 h-2.5 bg-gradient-to-br from-[var(--wuxing-wood)] to-[var(--wuxing-water)] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
              <h2 className="font-semibold text-[var(--brand-heading)] text-base tracking-wide">生辰八字</h2>
            </div>
            <BaziInputSection />
          </motion.div>
        )}
        
        {/* 天气和场景选择 - 水行清雅风格 */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="card-secondary p-5 bg-gradient-to-br from-[#F0F7FA]/80 to-[#E8F4F8]/60 hover:shadow-[0_6px_24px_rgba(74,144,196,0.12)] transition-all duration-300 group"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-2.5 h-2.5 bg-gradient-to-br from-[var(--wuxing-water)] to-[var(--wuxing-wood)] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
            <h2 className="font-semibold text-[var(--brand-heading)] text-base tracking-wide">天地气象</h2>
          </div>
          <WeatherSceneSection 
            onSceneChange={handleSceneChange}
            onWeatherChange={handleWeatherChange}
          />
        </motion.div>
        
        {/* 五行雷达图：仅在没有八字时显示 - 移动端优化 */}
        {!hasBazi && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="card-secondary p-5 bg-gradient-to-br from-[var(--brand-surface)]/80 to-[var(--brand-surface-active)]/60 hover:shadow-[0_6px_24px_rgba(61,163,93,0.12)] transition-all duration-300 group hidden md:block"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2.5 h-2.5 bg-gradient-to-br from-[var(--wuxing-wood)] to-[var(--wuxing-earth)] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
              <h2 className="font-semibold text-[var(--brand-heading)] text-base tracking-wide">五行生克</h2>
            </div>
            <FiveElementRadar
              currentData={radarData.currentData}
              suggestedData={radarData.suggestedData}
              xiyongShen={radarData.xiyongShen}
              pillars={radarData.pillars}
              eightChars={radarData.eightChars}
              dayMaster={radarData.dayMaster}
              elementCounts={radarData.elementCounts}
            />
          </motion.div>
        )}
        
        {/* 有八字时的提示信息 */}
        {hasBazi && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="card-secondary p-4 bg-gradient-to-br from-[var(--brand-surface)]/80 to-[var(--brand-surface-active)]/60"
          >
            <p className="text-xs text-[var(--brand-subtle)] text-center leading-relaxed">
              基于您的八字分析，我们已为您计算喜用神。
              <br />
              智能推荐将以此为依据，为您推荐最适合的穿搭。
            </p>
          </motion.div>
        )}
        </div>
      </motion.div>

      {/* 右侧：主要内容区 - 移动端优化 */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Header - 简化版，移动端隐藏 */}
        <div className="hidden md:block">
          <Header 
            sidebarCollapsed={sidebarCollapsed}
            onToggleSidebar={toggleSidebar}
          />
        </div>

        {/* 移动端头部栏 - 仅移动端显示，提供用户头像入口 */}
        <div className="md:hidden flex items-center justify-between px-4 h-12 bg-white/90 backdrop-blur-xl border-b border-stone-200/60 flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">🌿</span>
            <span className="font-semibold text-sm bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] bg-clip-text text-transparent font-serif">我的个人衣橱</span>
          </div>
          <div className="flex items-center gap-2">
            {/* 登录后显示用户名 */}
            {isAuthenticated && user && (
              <span className="text-sm font-medium text-stone-700 max-w-[120px] truncate">
                {user.nickname || user.phone || '用户'}
              </span>
            )}
            <button
              onClick={() => {
                if (isAuthenticated) {
                  setActiveTab('profile')
                  window.location.hash = '#profile'
                } else {
                  setShowAuthModal(true)
                }
              }}
              aria-label={isAuthenticated ? '打开个人中心' : '登录'}
              className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--wuxing-wood)]/20 to-[var(--wuxing-water)]/20 flex items-center justify-center active:scale-95 transition-transform"
            >
              {isAuthenticated && user?.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={user.avatar_url} alt="头像" className="w-7 h-7 rounded-full object-cover" />
              ) : (
                <svg className="w-4 h-4 text-[var(--brand-subtle)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              )}
            </button>
          </div>
        </div>
        
        {/* 优化后的Tab导航 - 移动端底部导航，桌面端顶部显示 */}
        <motion.div 
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="hidden md:block bg-white border-b border-stone-200/60"
        >
          <div className="flex items-center px-6">
                        {/* Tab 按钮组 */}
            <div className="flex gap-2 py-3">
              {/* 1. 运势 — 日活主角，放在最显眼的位置 */}
              <button
                onClick={() => {
                  setActiveTab('fortune')
                  window.location.hash = '#fortune'
                }}
                aria-label="切换到运势页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'fortune' || activeTab === 'destiny'
                    ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                    : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                }`}
              >
                <Compass className="w-5 h-5" />
                <span className="hidden sm:inline">运势</span>
              </button>
              {/* 2. 推荐 */}
              <button
                onClick={() => {
                  setActiveTab('chat')
                  window.location.hash = ''
                }}
                aria-label="切换到推荐页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'chat'
                    ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                    : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                <span className="hidden sm:inline">推荐</span>
              </button>
              {/* 2. 衣橱 */}
              <button
                onClick={() => {
                  setActiveTab('wardrobe')
                  window.location.hash = '#wardrobe'
                }}
                aria-label="切换到衣橱页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'wardrobe'
                    ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                    : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <span className="hidden sm:inline">衣橱</span>
              </button>
              {/* 3. 广场 — 临时关闭（个人备案合规改造，暂不提供UGC交互功能），恢复时取消注释并恢复 Users 图标导入 */}
              {/* <button
                onClick={() => {
                  setActiveTab('community')
                  window.location.hash = '#community'
                }}
                aria-label="切换到广场页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'community'
                    ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                    : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                }`}
              >
                <Users className="w-5 h-5" />
                <span className="hidden sm:inline">广场</span>
              </button> */}
              {/* 4. 日记 */}
              <button
                onClick={() => {
                  setActiveTab('diary')
                  window.location.hash = '#diary'
                }}
                aria-label="切换到日记页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'diary'
                    ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                    : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                }`}
              >
                <BookOpen className="w-5 h-5" />
                <span className="hidden sm:inline">日记</span>
              </button>
              {/* 5. 修炼 */}
              <button
                onClick={() => {
                  setActiveTab('cultivation')
                  window.location.hash = '#cultivation'
                }}
                aria-label="切换到修炼页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'cultivation'
                    ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                    : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                }`}
              >
                <Mountain className="w-5 h-5" />
                <span className="hidden sm:inline">修炼</span>
              </button>
              {/* 6. 更多 — 下拉(试衣等) - 支持 click + 键盘导航 */}
              <div className="relative">
                <button
                  onClick={() => setShowMoreMenu(!showMoreMenu)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowMoreMenu(!showMoreMenu) } }}
                  aria-label="更多功能"
                  aria-expanded={showMoreMenu}
                  aria-haspopup="menu"
                  className={`relative flex items-center gap-1.5 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                    showMoreMenu
                      ? 'bg-[var(--brand-surface)] text-[var(--brand-heading)] shadow-sm'
                      : 'text-stone-600 hover:bg-[var(--brand-surface)] hover:text-[var(--brand-heading)]'
                  }`}
                >
                  <MoreHorizontal className="w-5 h-5" />
                  <span className="hidden sm:inline">更多</span>
                  <svg className={`w-3 h-3 transition-transform duration-200 ${showMoreMenu ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {/* 下拉菜单 - click 触发，支持键盘 Escape 关闭 */}
                {showMoreMenu && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setShowMoreMenu(false)} />
                    <div
                      role="menu"
                      aria-label="更多功能菜单"
                      onKeyDown={(e) => { if (e.key === 'Escape') setShowMoreMenu(false) }}
                      className="absolute top-full right-0 mt-1 w-64 bg-white rounded-xl shadow-lg border border-stone-200/60 py-1 z-50"
                    >
                  {/* 五行小课堂 */}
                  <button
                    role="menuitem"
                    onClick={() => {
                      setActiveTab('wuxing-classroom' as any)
                      window.location.hash = '#wuxing-classroom'
                      setShowMoreMenu(false)
                    }}
                    className="w-full text-left px-4 py-2.5 hover:bg-[var(--brand-surface)] transition-colors"
                  >
                    <div className="flex items-center gap-2 text-sm font-medium text-stone-700">
                      <span className="text-base">📖</span>
                      <span>五行小课堂</span>
                    </div>
                    <p className="mt-0.5 text-[11px] leading-snug text-stone-500">
                      了解五行生克，掌握穿搭智慧
                    </p>
                  </button>
                  {/* 试衣 — 暂未上线，置于末尾并禁用 */}
                  <div
                    role="menuitem"
                    aria-disabled="true"
                    className="px-4 py-2.5 opacity-70 cursor-not-allowed select-none"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-sm font-medium text-stone-400">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span>试衣</span>
                      </div>
                      <span className="shrink-0 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-stone-100 text-stone-400">敬请期待</span>
                    </div>
                    <p className="mt-1 text-[11px] leading-snug text-stone-400">
                      AI人物形象智能穿搭推荐功能 - 稍后上线，敬请期待
                    </p>
                  </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* 内容区域 - 优化间距和视觉层次 */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex-1 overflow-y-auto overflow-x-visible bg-white p-3 md:p-4 pb-24 md:pb-4"
          style={{
            paddingBottom: 'calc(6rem + env(safe-area-inset-bottom, 0px))',
            // Safari 滚动适配：阻止滚动链/橡皮筋干扰下拉刷新手势，iOS 惯性滚动更顺滑
            overscrollBehaviorY: 'contain',
            WebkitOverflowScrolling: 'touch',
          }}
        >
          <PullToRefresh onRefresh={handleRefresh}>
          <AnimatePresence initial={false}>
            {activeTab === 'chat' && (
              <motion.div
                key="chat"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                {/* 智能提醒横幅 */}
                {smartAlerts.length > 0 && (
                  <div className="mb-3 space-y-2">
                    {smartAlerts.map((msg, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-start gap-2 px-4 py-3 bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200/60 rounded-xl text-sm text-blue-700"
                      >
                        <span className="text-base mt-0.5">🔔</span>
                        <span className="flex-1">{msg}</span>
                        <button
                          onClick={() => setSmartAlerts(prev => prev.filter((_, idx) => idx !== i))}
                          className="text-blue-400 hover:text-blue-600"
                        >
                          ✕
                        </button>
                      </motion.div>
                    ))}
                  </div>
                )}

                {/* 每日仪式卡片 — 运势摘要 + 打卡状态 + 连续天数 + 修炼等级 */}
                {isAuthenticated && !isAuthLoading && (
                  <div className="mb-4">
                    <DailyRitualCard
                      onCheckIn={() => setShowCheckIn(true)}
                      onNavigateToFortune={() => {
                        setActiveTab('fortune')
                        window.location.hash = '#fortune'
                      }}
                      onNavigateToCultivation={() => {
                        setActiveTab('cultivation')
                        window.location.hash = '#cultivation'
                      }}
                      onNavigateToWardrobe={() => {
                        setActiveTab('wardrobe')
                        window.location.hash = '#wardrobe'
                      }}
                    />
                  </div>
                )}

                {/* 每日智能穿搭建议 — 已登录用户自动展示 */}
                {isAuthenticated && !isAuthLoading && (
                  <DailyOutfitCard isAuthenticated={isAuthenticated} city={userCity} />
                )}

                {/* 快捷推荐入口 — 已登录用户一键推荐 */}
                {isAuthenticated && !isAuthLoading && (
                  <QuickRecommendBar
                    weatherElement={weatherElement}
                    weatherInfo={weatherInfo}
                    userCity={userCity}
                    onFocusChat={() => {
                      // 滚动到聊天输入框
                      const chatInput = document.querySelector('textarea[placeholder*="穿搭"]')
                      if (chatInput) {
                        chatInput.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        setTimeout(() => (chatInput as HTMLTextAreaElement).focus(), 300)
                      }
                    }}
                  />
                )}

                <ChatInterface 
                  scene={scene} 
                  weatherElement={weatherElement}
                  weatherInfo={weatherInfo}
                  userCity={userCity}
                />
              </motion.div>
            )}
            {activeTab === 'wardrobe' && (
              <motion.div
                key="wardrobe"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <Suspense fallback={<PageLoadingFallback />}>
                  <WardrobePage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'profile' && (
              <motion.div
                key="profile"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <UserProfile 
                  onClose={() => {
                    setActiveTab('chat')
                    window.location.hash = ''
                  }}
                />
              </motion.div>
            )}
            {activeTab === 'diary' && (
              <motion.div
                key="diary"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <Suspense fallback={<PageLoadingFallback />}>
                  <DiaryPage />
                </Suspense>
              </motion.div>
            )}
            {(activeTab === 'fortune' || activeTab === 'destiny') && (
              <motion.div
                key="destiny-fortune"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <Suspense fallback={<PageLoadingFallback />}>
                  <DestinyFortuneHub
                    activeTab={activeTab === 'destiny' ? 'destiny' : 'fortune'}
                    onTabChange={(tab) => {
                      setActiveTab(tab)
                      window.location.hash = `#${tab}`
                    }}
                  />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'community' && (
              <motion.div
                key="community"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <Suspense fallback={<PageLoadingFallback />}>
                  <CommunityPage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'cultivation' && (
              <motion.div
                key="cultivation"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <Suspense fallback={<PageLoadingFallback />}>
                  <CultivationPage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'wuxing-classroom' && (
              <motion.div
                key="wuxing-classroom"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              >
                <Suspense fallback={<PageLoadingFallback />}>
                  <WuxingClassroomPage />
                </Suspense>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ICP 备案信息：滚动区底部展示，不被底部导航遮挡 */}
          <IcpFooter />
          </PullToRefresh>
        </motion.div>
      </div>
      
      {/* 移动端控制面板 - 底部固定 */}
      <MobileControlPanel
        onSceneChange={handleSceneChange}
        onWeatherChange={handleWeatherChange}
      />
      
      {/* 移动端底部导航 */}
      <MobileBottomNav
        activeTab={activeTab as any}
        onTabChange={(tab: any) => {
          setActiveTab(tab)
          if (tab === 'chat') {
            window.location.hash = ''
          } else {
            window.location.hash = `#${tab}`
          }
        }}
      />

      {/* 快捷打卡弹窗（仅手动触发：每日仪式卡片打卡按钮） */}
      <QuickCheckIn
        isOpen={showCheckIn}
        onClose={() => setShowCheckIn(false)}
        weatherInfo={weatherInfo}
      />

      {/* 登录弹窗 — 移动端未登录时点击头像触发 */}
      <Suspense fallback={null}>
        <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      </Suspense>
    </div>
  )
}
