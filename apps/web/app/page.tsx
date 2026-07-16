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
import { TodayFortuneCard } from '@/components/features/fortune/TodayFortuneCard'
import { DailyRitualCard } from '@/components/features/DailyRitualCard'
import { QuickCheckIn } from '@/components/features/QuickCheckIn'
import { useChatStore } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { motion, AnimatePresence } from 'framer-motion'
import { Users, BookOpen, Mountain, Compass, CircleDot, MoreHorizontal } from 'lucide-react'

// 懒加载衣橱页面，减少首页初始加载时间
const WardrobePage = lazy(() => import('./wardrobe/page'))
const DiaryPage = lazy(() => import('./diary/page'))
const FortunePage = lazy(() => import('./fortune/page'))
const DestinyPage = lazy(() => import('./destiny/page'))
const CommunityPage = lazy(() => import('./community/page'))
const CultivationPage = lazy(() => import('./cultivation/page'))
const AuthModal = lazy(() => import('@/components/features/AuthModal').then(m => ({ default: m.AuthModal })))

export default function Home() {
  const { radarData, setUserBazi } = useChatStore()
  const { user, isAuthenticated, isLoading: isAuthLoading } = useUserStore()
  const [mounted, setMounted] = useState(false)
  const [scene, setScene] = useState('')
  const [sceneElement, setSceneElement] = useState('')
    const [weatherElement, setWeatherElement] = useState('')
  const [weatherInfo, setWeatherInfo] = useState<any>(null)  // 新增：保存完整天气信息
  const [userCity, setUserCity] = useState<string>('')  // 用户当前城市
  const [activeTab, setActiveTab] = useState<'chat' | 'wardrobe' | 'tryon' | 'profile' | 'diary' | 'fortune' | 'destiny' | 'community' | 'cultivation'>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [showCheckIn, setShowCheckIn] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [smartAlerts, setSmartAlerts] = useState<string[]>([])
  
  // 判断用户是否有八字（已登录且资料完整）
  const hasBazi = isAuthenticated && !isAuthLoading && user?.bazi
  
  // 每日首次打开自动弹出打卡弹窗
  useEffect(() => {
    if (isAuthenticated && !isAuthLoading) {
      const today = new Date().toDateString()
      const lastCheckIn = localStorage.getItem('last_checkin_date')
      if (lastCheckIn !== today) {
        // 延迟 1.5s 弹出，避免打扰用户
        const timer = setTimeout(() => setShowCheckIn(true), 1500)
        return () => clearTimeout(timer)
      }
    }
  }, [isAuthenticated, isAuthLoading])
  
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
      } else if (window.location.hash === '#tryon') {
        setActiveTab('tryon')
      } else if (window.location.hash === '#diary') {
        setActiveTab('diary')
      } else if (window.location.hash === '#fortune') {
        setActiveTab('fortune')
      } else if (window.location.hash === '#destiny') {
        setActiveTab('destiny')
      } else if (window.location.hash === '#community') {
        setActiveTab('community')
      } else if (window.location.hash === '#cultivation') {
        setActiveTab('cultivation')
      } else {
        setActiveTab('chat')
      }
    }

    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const handleSceneChange = (sceneId: string, element: string) => {
    setScene(sceneId)
    setSceneElement(element)
  }

  const handleWeatherChange = (weather: any) => {
    setWeatherElement(weather.element)
    setWeatherInfo({  // 保存完整天气信息
      temperature: weather.temperature,
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
      <div className="flex h-dvh bg-stone-50 overflow-hidden items-center justify-center">
        <div className="text-[var(--brand-body)] text-sm animate-pulse">加载中...</div>
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
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[#3DA35D] via-[#4A90C4] to-[#D4656B] bg-clip-text text-transparent font-serif tracking-tight">
            五行穿搭
          </h1>
          <p className="text-sm text-[var(--brand-body)] font-light tracking-wide mt-2">
            {hasBazi ? '您的专属五行推荐' : '天人合一 · 五行相生'}
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
              <div className="w-2.5 h-2.5 bg-gradient-to-br from-[#3DA35D] to-[#4A90C4] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
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
            <div className="w-2.5 h-2.5 bg-gradient-to-br from-[#4A90C4] to-[#3DA35D] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
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
              <div className="w-2.5 h-2.5 bg-gradient-to-br from-[#3DA35D] to-[#B89B5E] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
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
            <span className="font-semibold text-sm bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] bg-clip-text text-transparent font-serif">顺衣尚</span>
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
              className="w-8 h-8 rounded-full bg-gradient-to-br from-[#3DA35D]/20 to-[#4A90C4]/20 flex items-center justify-center active:scale-95 transition-transform"
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
              {/* 1. 推荐 */}
              <button
                onClick={() => {
                  setActiveTab('chat')
                  window.location.hash = ''
                }}
                aria-label="切换到推荐页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'chat'
                    ? 'bg-gradient-to-r from-emerald-50 to-teal-50 text-emerald-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
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
                    ? 'bg-gradient-to-r from-rose-50 to-pink-50 text-rose-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <span className="hidden sm:inline">衣橱</span>
              </button>
              {/* 3. 广场 */}
              <button
                onClick={() => {
                  setActiveTab('community')
                  window.location.hash = '#community'
                }}
                aria-label="切换到广场页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'community'
                    ? 'bg-gradient-to-r from-pink-50 to-rose-50 text-pink-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                }`}
              >
                <Users className="w-5 h-5" />
                <span className="hidden sm:inline">广场</span>
              </button>
              {/* 4. 日记 */}
              <button
                onClick={() => {
                  setActiveTab('diary')
                  window.location.hash = '#diary'
                }}
                aria-label="切换到日记页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'diary'
                    ? 'bg-gradient-to-r from-emerald-50 to-cyan-50 text-emerald-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
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
                    ? 'bg-gradient-to-r from-amber-50 to-yellow-50 text-amber-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                }`}
              >
                <Mountain className="w-5 h-5" />
                <span className="hidden sm:inline">修炼</span>
              </button>
              {/* 6. 更多 — 下拉(运势/命理/试衣) */}
              <div className="relative group">
                <button
                  aria-label="更多功能"
                  className={`relative flex items-center gap-1.5 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                    activeTab === 'fortune' || activeTab === 'destiny' || activeTab === 'tryon'
                      ? 'bg-gradient-to-r from-indigo-50 to-violet-50 text-indigo-700 shadow-sm'
                      : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                  }`}
                >
                  <MoreHorizontal className="w-5 h-5" />
                  <span className="hidden sm:inline">更多</span>
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {/* 下拉菜单 */}
                <div className="absolute top-full right-0 mt-1 w-40 bg-white rounded-xl shadow-lg border border-stone-200/60 py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                  <button
                    onClick={() => {
                      setActiveTab('fortune')
                      window.location.hash = '#fortune'
                    }}
                    className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                      activeTab === 'fortune'
                        ? 'text-violet-700 bg-violet-50'
                        : 'text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    <Compass className="w-4 h-4" />
                    <span>运势</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('destiny')
                      window.location.hash = '#destiny'
                    }}
                    className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                      activeTab === 'destiny'
                        ? 'text-indigo-700 bg-indigo-50'
                        : 'text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    <CircleDot className="w-4 h-4" />
                    <span>命理</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('tryon')
                      window.location.hash = '#tryon'
                    }}
                    className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                      activeTab === 'tryon'
                        ? 'text-amber-700 bg-amber-50'
                        : 'text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span>试衣</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* 内容区域 - 优化间距和视觉层次 */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex-1 overflow-y-auto overflow-x-visible bg-stone-50/50 backdrop-blur-sm p-3 md:p-4 pb-24 md:pb-4"
          style={{ paddingBottom: 'calc(6rem + env(safe-area-inset-bottom, 0px))' }} // 为移动端底部导航预留空间
        >
          <AnimatePresence mode="wait">
            {activeTab === 'chat' && (
              <motion.div
                key="chat"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
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
                    />
                  </div>
                )}

                {/* 未登录时仍显示运势卡片（如果有八字） */}
                {!isAuthenticated && !isAuthLoading && hasBazi && (
                  <div className="mb-4">
                    <TodayFortuneCard
                      onNavigateToFortune={() => {
                        setActiveTab('fortune')
                        window.location.hash = '#fortune'
                      }}
                    />
                  </div>
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
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <Suspense fallback={
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#3DA35D] border-t-transparent"></div>
                  </div>
                }>
                  <WardrobePage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'profile' && (
              <motion.div
                key="profile"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <UserProfile 
                  onClose={() => {
                    setActiveTab('chat')
                    window.location.hash = ''
                  }}
                />
              </motion.div>
            )}
            {activeTab === 'tryon' && (
              <motion.div
                key="tryon"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="h-[calc(100vh-200px)] min-h-[400px]"
              >
                <iframe
                  src="/tryon"
                  className="w-full h-full border-0 rounded-xl"
                  title="虚拟试衣"
                  aria-label="虚拟试衣页面"
                />
              </motion.div>
            )}
            {activeTab === 'diary' && (
              <motion.div
                key="diary"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <Suspense fallback={
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#3DA35D] border-t-transparent"></div>
                  </div>
                }>
                  <DiaryPage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'fortune' && (
              <motion.div
                key="fortune"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <Suspense fallback={
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#3DA35D] border-t-transparent"></div>
                  </div>
                }>
                  <FortunePage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'destiny' && (
              <motion.div
                key="destiny"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <Suspense fallback={
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#3DA35D] border-t-transparent"></div>
                  </div>
                }>
                  <DestinyPage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'community' && (
              <motion.div
                key="community"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <Suspense fallback={
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#3DA35D] border-t-transparent"></div>
                  </div>
                }>
                  <CommunityPage />
                </Suspense>
              </motion.div>
            )}
            {activeTab === 'cultivation' && (
              <motion.div
                key="cultivation"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <Suspense fallback={
                  <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#3DA35D] border-t-transparent"></div>
                  </div>
                }>
                  <CultivationPage />
                </Suspense>
              </motion.div>
            )}
          </AnimatePresence>
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

      {/* 快捷打卡弹窗 */}
      <QuickCheckIn
        isOpen={showCheckIn}
        onClose={() => {
          setShowCheckIn(false)
          localStorage.setItem('last_checkin_date', new Date().toDateString())
        }}
        onSuccess={(diaryId) => {
          localStorage.setItem('last_checkin_date', new Date().toDateString())
        }}
                weatherInfo={weatherInfo}
      />

      {/* 登录弹窗 — 移动端未登录时点击头像触发 */}
      <Suspense fallback={null}>
        <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      </Suspense>
    </div>
  )
}
