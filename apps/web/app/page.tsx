'use client'

import { useState, useEffect, lazy, Suspense } from 'react'
import { FiveElementRadar } from '@/components/features/FiveElementRadar'
import { ChatInterface } from '@/components/features/ChatInterface'
import { BaziInputSection } from '@/components/features/BaziInputSection'
import { BaziCard } from '@/components/features/BaziCard'
import { WeatherSceneSection } from '@/components/features/WeatherSceneSection'
import { UserProfile } from '@/components/features/UserProfile'
import { Sidebar } from '@/components/features/Sidebar'
import { Header } from '@/components/features/Header'
import { useChatStore } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { motion } from 'framer-motion'

// 懒加载衣橱页面，减少首页初始加载时间
const WardrobePage = lazy(() => import('./wardrobe/page'))

export default function Home() {
  const { radarData } = useChatStore()
  const { user, isAuthenticated } = useUserStore()
  const [scene, setScene] = useState('')
  const [sceneElement, setSceneElement] = useState('')
  const [weatherElement, setWeatherElement] = useState('')
  const [activeTab, setActiveTab] = useState<'chat' | 'wardrobe' | 'profile'>('chat')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  
  // 判断用户是否有八字（已登录且资料完整）
  const hasBazi = isAuthenticated && user?.bazi

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
  }

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-blue-50">
      {/* Sidebar - 聊天记录面板 */}
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={toggleSidebar}
      />

      {/* 左侧：清新五行风格控制面板 */}
      <motion.div 
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className={`bg-white/80 backdrop-blur-xl border-r border-amber-200/30 p-6 overflow-y-auto space-y-6 shadow-lg transition-all duration-300 ${
          hasBazi ? 'w-[300px] lg:w-[340px]' : 'w-[320px] lg:w-[360px]'
        }`}
      >
        {/* 标题区域 - 清雅书法风格 */}
        <motion.div 
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-center mb-4"
        >
          <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-600 via-orange-500 to-rose-500 bg-clip-text text-transparent font-serif">
            五行穿搭
          </h1>
          <div className="w-24 h-0.5 bg-gradient-to-r from-amber-300 to-orange-300 mx-auto my-3 rounded-full"></div>
          <p className="text-sm text-stone-600 font-light">
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
            className="bg-gradient-to-br from-amber-50/60 to-yellow-50/40 rounded-2xl p-5 shadow-sm border border-amber-200/40 hover:shadow-md transition-all duration-300"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-3 h-3 bg-gradient-to-br from-amber-300 to-yellow-400 rounded-full"></div>
              <h2 className="font-semibold text-stone-700 text-lg">生辰八字</h2>
            </div>
            <BaziInputSection />
          </motion.div>
        )}
        
        {/* 天气和场景选择 - 水行清雅风格 */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-blue-50/60 to-cyan-50/40 rounded-2xl p-5 shadow-sm border border-blue-200/40 hover:shadow-md transition-all duration-300"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-gradient-to-br from-blue-300 to-cyan-400 rounded-full"></div>
            <h2 className="font-semibold text-stone-700 text-lg">天地气象</h2>
          </div>
          <WeatherSceneSection 
            onSceneChange={handleSceneChange}
            onWeatherChange={handleWeatherChange}
          />
        </motion.div>
        
        {/* 五行雷达图：仅在没有八字时显示 */}
        {!hasBazi && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="bg-gradient-to-br from-green-50/60 to-emerald-50/40 rounded-2xl p-5 shadow-sm border border-green-200/40 hover:shadow-md transition-all duration-300"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-3 h-3 bg-gradient-to-br from-green-300 to-emerald-400 rounded-full"></div>
              <h2 className="font-semibold text-stone-700 text-lg">五行生克</h2>
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
            className="bg-gradient-to-br from-amber-50/40 to-orange-50/30 rounded-xl p-4 border border-amber-200/30"
          >
            <p className="text-xs text-stone-500 text-center leading-relaxed">
              基于您的八字分析，我们已为您计算喜用神。
              <br />
              智能推荐将以此为依据，为您推荐最适合的穿搭。
            </p>
          </motion.div>
        )}
      </motion.div>

      {/* 右侧：主要内容区 */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <Header 
          sidebarCollapsed={sidebarCollapsed}
          onToggleSidebar={toggleSidebar}
        />
        
        {/* 清雅五行风格Tab导航 */}
        <motion.div 
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white/80 backdrop-blur-xl border-b border-amber-200/30 flex-shrink-0"
        >
          <div className="flex px-6 py-2">
            <button
              onClick={() => {
                setActiveTab('chat')
                window.location.hash = ''
              }}
              className={`relative px-6 py-4 font-medium text-sm transition-all duration-300 ${
                activeTab === 'chat'
                  ? 'text-amber-600'
                  : 'text-stone-500 hover:text-amber-700'
              }`}
            >
              智能推荐
              {activeTab === 'chat' && (
                <motion.div 
                  layoutId="tabIndicator"
                  className="absolute bottom-0 left-4 right-4 h-1 bg-gradient-to-r from-amber-400 to-orange-400 rounded-full"
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
            </button>
            <button
              onClick={() => {
                setActiveTab('wardrobe')
                window.location.hash = '#wardrobe'
              }}
              className={`relative px-6 py-4 font-medium text-sm transition-all duration-300 ${
                activeTab === 'wardrobe'
                  ? 'text-rose-500'
                  : 'text-stone-500 hover:text-rose-600'
              }`}
            >
              我的衣橱
              {activeTab === 'wardrobe' && (
                <motion.div
                  layoutId="tabIndicator"
                  className="absolute bottom-0 left-4 right-4 h-1 bg-gradient-to-r from-rose-400 to-pink-400 rounded-full"
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
            </button>
            <button
              onClick={() => {
                setActiveTab('profile')
                window.location.hash = '#profile'
              }}
              className={`relative px-6 py-4 font-medium text-sm transition-all duration-300 ${
                activeTab === 'profile'
                  ? 'text-blue-500'
                  : 'text-stone-500 hover:text-blue-600'
              }`}
            >
              个人资料
              {activeTab === 'profile' && (
                <motion.div 
                  layoutId="tabIndicator"
                  className="absolute bottom-0 left-4 right-4 h-1 bg-gradient-to-r from-blue-400 to-cyan-400 rounded-full"
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
            </button>
          </div>
        </motion.div>

        {/* 内容区域 */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex-1 overflow-y-auto bg-gradient-to-b from-white/70 to-amber-50/30 backdrop-blur-sm p-6"
        >
          {activeTab === 'chat' && (
            <ChatInterface scene={scene} weatherElement={weatherElement} />
          )}
          {activeTab === 'wardrobe' && (
            <Suspense fallback={
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-500"></div>
              </div>
            }>
              <WardrobePage />
            </Suspense>
          )}
          {activeTab === 'profile' && (
            <UserProfile 
              onClose={() => {
                setActiveTab('chat')
                window.location.hash = ''
              }}
            />
          )}
        </motion.div>
      </div>
    </div>
  )
}
