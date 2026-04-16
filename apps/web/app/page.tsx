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
import { useChatStore } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { motion, AnimatePresence } from 'framer-motion'

// 懒加载衣橱页面，减少首页初始加载时间
const WardrobePage = lazy(() => import('./wardrobe/page'))

export default function Home() {
  const { radarData, setUserBazi } = useChatStore()
  const { user, isAuthenticated } = useUserStore()
  const [scene, setScene] = useState('')
  const [sceneElement, setSceneElement] = useState('')
  const [weatherElement, setWeatherElement] = useState('')
  const [weatherInfo, setWeatherInfo] = useState<any>(null)  // 新增：保存完整天气信息
  const [activeTab, setActiveTab] = useState<'chat' | 'wardrobe' | 'profile'>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  
  // 判断用户是否有八字（已登录且资料完整）
  const hasBazi = isAuthenticated && user?.bazi
  
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
      console.log('[HomePage] 从用户资料自动设置八字:', baziInput)
    }
  }, [hasBazi, user, setUserBazi])

  // 监听hash变化
  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#profile') {
        setActiveTab('profile')
      } else if (window.location.hash === '#wardrobe') {
        setActiveTab('wardrobe')
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
    console.log('[HomePage] 天气信息:', weather)
  }

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  // 下拉刷新功能
  const handleRefresh = useCallback(async () => {
    console.log('[HomePage] 下拉刷新')
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

  return (
    <div className="flex h-screen bg-gradient-to-br from-[#F8FAF9] via-[#F5F9F7] to-[#F0F7F4] overflow-hidden">
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
            ? 'w-[300px] lg:w-[340px]' 
            : 'w-[320px] lg:w-[360px]'
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
          <p className="text-sm text-[#4A5F52] font-light tracking-wide mt-2">
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
            className="card-secondary p-5 bg-gradient-to-br from-[#F8FAF9]/80 to-[#F0F7F4]/60 hover:shadow-[0_6px_24px_rgba(61,163,93,0.12)] transition-all duration-300 group"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2.5 h-2.5 bg-gradient-to-br from-[#3DA35D] to-[#4A90C4] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
              <h2 className="font-semibold text-[#2D4A38] text-base tracking-wide">生辰八字</h2>
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
            <h2 className="font-semibold text-[#2D4A38] text-base tracking-wide">天地气象</h2>
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
            className="card-secondary p-5 bg-gradient-to-br from-[#F0F9F4]/80 to-[#E8F5EC]/60 hover:shadow-[0_6px_24px_rgba(61,163,93,0.12)] transition-all duration-300 group hidden md:block"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2.5 h-2.5 bg-gradient-to-br from-[#3DA35D] to-[#B89B5E] rounded-full group-hover:scale-110 transition-transform duration-300"></div>
              <h2 className="font-semibold text-[#2D4A38] text-base tracking-wide">五行生克</h2>
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
            className="card-secondary p-4 bg-gradient-to-br from-[#F8FAF9]/80 to-[#F5F9F7]/60"
          >
            <p className="text-xs text-[#5A7A66] text-center leading-relaxed">
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
        {/* Header */}
        <Header 
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={toggleSidebar}
        />
        
        {/* 优化后的Tab导航 - 更简洁大方 */}
        <motion.div 
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white/90 backdrop-blur-xl flex-shrink-0 border-b border-stone-200/60"
        >
          <div className="flex items-center justify-between px-4 md:px-6">
            {/* Tab 按钮组 */}
            <div className="flex gap-1 py-2 overflow-x-auto scrollbar-hide">
              <button
                onClick={() => {
                  setActiveTab('chat')
                  window.location.hash = ''
                }}
                aria-label="切换到智能推荐页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'chat'
                    ? 'bg-gradient-to-r from-emerald-50 to-teal-50 text-emerald-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                <span className="hidden sm:inline">智能推荐</span>
              </button>
              <button
                onClick={() => {
                  setActiveTab('wardrobe')
                  window.location.hash = '#wardrobe'
                }}
                aria-label="切换到我的衣橱页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'wardrobe'
                    ? 'bg-gradient-to-r from-rose-50 to-pink-50 text-rose-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                <span className="hidden sm:inline">我的衣橱</span>
              </button>
              <button
                onClick={() => {
                  setActiveTab('profile')
                  window.location.hash = '#profile'
                }}
                aria-label="切换到个人资料页面"
                className={`relative flex items-center gap-2 px-4 py-2.5 min-h-[44px] rounded-xl font-medium text-sm transition-all duration-200 touch-manipulation ${
                  activeTab === 'profile'
                    ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 shadow-sm'
                    : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="hidden sm:inline">个人资料</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* 内容区域 - 优化间距和视觉层次 */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex-1 overflow-y-auto overflow-x-visible bg-stone-50/50 backdrop-blur-sm p-4 md:p-6 pb-24 md:pb-6"
          style={{ paddingBottom: 'max(6rem, 6rem)' }} // 为移动端底部导航预留空间
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
                <ChatInterface 
                  scene={scene} 
                  weatherElement={weatherElement}
                  weatherInfo={weatherInfo}
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
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab)
          if (tab === 'chat') {
            window.location.hash = ''
          } else {
            window.location.hash = `#${tab}`
          }
        }}
      />
    </div>
  )
}
