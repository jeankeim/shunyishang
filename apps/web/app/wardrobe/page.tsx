'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useWardrobeStore } from '@/store/wardrobe'
import { AddWardrobeModal } from '@/components/features/AddWardrobeModal'
import { initAuthToken } from '@/lib/api'
import { WUXING_ELEMENTS, WUXING_CONFIG, getWuxingConfig } from '@/lib/wuxing-config'
import type { WardrobeItem } from '@/lib/api'

// 五行数据配置
const WUXING_THEME: Record<string, { color: string; gradient: string; symbol: string; pattern: string }> = {
  '金': { color: '#F5D0C5', gradient: 'from-amber-100 via-yellow-50 to-orange-50', symbol: '☰', pattern: 'cloud' },
  '木': { color: '#A8D5BA', gradient: 'from-emerald-100 via-green-50 to-teal-50', symbol: '☳', pattern: 'leaf' },
  '水': { color: '#B8D4E8', gradient: 'from-blue-100 via-cyan-50 to-sky-50', symbol: '☵', pattern: 'wave' },
  '火': { color: '#F5C6C6', gradient: 'from-rose-100 via-pink-50 to-red-50', symbol: '☲', pattern: 'flame' },
  '土': { color: '#E8D5B8', gradient: 'from-amber-100 via-orange-50 to-yellow-50', symbol: '☷', pattern: 'mountain' },
}

export default function WardrobePage() {
  const { items, total, elementStats, isLoading, fetchItems, deleteItem } = useWardrobeStore()
  
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)
  const [filterElement, setFilterElement] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editItem, setEditItem] = useState<WardrobeItem | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<'grid' | 'flow'>('flow')

  useEffect(() => {
    initAuthToken()
    const checkAuth = () => {
      const token = localStorage.getItem('wuxing_token')
      const store = localStorage.getItem('wuxing-user-storage')
      const isAuth = token && store ? JSON.parse(store).state?.isAuthenticated : false
      setIsAuthenticated(isAuth)
      setIsHydrated(true)
    }
    checkAuth()
    window.addEventListener('storage', () => checkAuth())
    return () => window.removeEventListener('storage', () => checkAuth())
  }, [])

  useEffect(() => {
    if (isAuthenticated && isHydrated) {
      fetchItems()
    }
  }, [isAuthenticated, isHydrated, fetchItems])

  const handleFilterChange = (element: string | null) => {
    setFilterElement(element)
    if (element) {
      fetchItems({ element })
    } else {
      fetchItems()
    }
  }

  const handleDelete = async (itemId: number) => {
    if (!confirm('确定要删除这件衣物吗？')) return
    setDeletingId(itemId)
    try {
      await deleteItem(itemId)
    } finally {
      setDeletingId(null)
    }
  }

  const handleAddNew = () => {
    setEditItem(null)
    setIsModalOpen(true)
  }

  const filteredItems = filterElement
    ? items.filter((item) => item.primary_element === filterElement)
    : items

  // 计算五行比例
  const getElementPercentage = (element: string) => {
    if (total === 0) return 0
    return Math.round(((elementStats[element] || 0) / total) * 100)
  }

  // 未登录状态
  if (!isAuthenticated) {
    return (
      <div className="min-h-full flex items-center justify-center relative overflow-hidden">
        {/* 背景装饰 */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-64 h-64 rounded-full opacity-20"
              style={{
                background: `radial-gradient(circle, ${Object.values(WUXING_THEME)[i].color} 0%, transparent 70%)`,
                left: `${20 + i * 15}%`,
                top: `${10 + (i % 3) * 25}%`,
              }}
              animate={{
                scale: [1, 1.2, 1],
                x: [0, 20, 0],
                y: [0, -10, 0],
              }}
              transition={{
                duration: 8 + i * 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md mx-auto px-6 relative z-10"
        >
          <motion.div 
            className="w-32 h-32 mx-auto mb-8 relative"
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
          >
            {/* 五行圆环 */}
            {WUXING_ELEMENTS.map((element, i) => {
              const config = WUXING_CONFIG[element]
              const angle = (i * 72 - 90) * (Math.PI / 180)
              const x = 48 + 40 * Math.cos(angle)
              const y = 48 + 40 * Math.sin(angle)
              return (
                <div
                  key={element}
                  className="absolute w-8 h-8 rounded-full flex items-center justify-center text-lg shadow-lg"
                  style={{
                    left: x - 16,
                    top: y - 16,
                    background: `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})`,
                  }}
                >
                  {config.emoji}
                </div>
              )
            })}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-3xl">👗</span>
            </div>
          </motion.div>
          
          <h2 className="text-3xl font-bold text-stone-800 mb-3" style={{ fontFamily: 'serif' }}>
            我的衣橱
          </h2>
          <p className="text-stone-500 mb-2">登录后开启您的五行穿搭之旅</p>
          <p className="text-sm text-stone-400">点击右上角「登录」按钮</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-full relative">
      {/* 顶部艺术化标题区 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mb-8"
      >
        <div className="flex items-end justify-between">
          <div>
            <motion.h1 
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              className="text-4xl font-bold text-stone-800 tracking-tight"
              style={{ fontFamily: 'serif' }}
            >
              我的衣橱
            </motion.h1>
            <motion.p 
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-stone-500 mt-2 flex items-center gap-2"
            >
              <span className="inline-block w-2 h-2 rounded-full bg-gradient-to-r from-rose-400 to-pink-400" />
              共收藏 <span className="font-medium text-stone-700">{total}</span> 件衣物
            </motion.p>
          </div>
          
          <motion.button
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleAddNew}
            className="relative group px-6 py-3 rounded-2xl bg-gradient-to-r from-stone-800 to-stone-700 text-white font-medium shadow-xl shadow-stone-300/30 overflow-hidden"
          >
            <span className="relative z-10 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              添加衣物
            </span>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-amber-500 to-orange-500"
              initial={{ x: '100%' }}
              whileHover={{ x: 0 }}
              transition={{ duration: 0.3 }}
            />
          </motion.button>
        </div>
      </motion.div>

      {/* 五行能量分布图 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-8 p-6 bg-white/70 backdrop-blur-xl rounded-3xl border border-white/50 shadow-xl shadow-stone-200/20"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wider">五行能量分布</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('flow')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'flow' ? 'bg-stone-800 text-white' : 'text-stone-400 hover:text-stone-600'}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-stone-800 text-white' : 'text-stone-400 hover:text-stone-600'}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
          </div>
        </div>
        
        {/* 五行条形图 */}
        <div className="flex gap-3">
          {WUXING_ELEMENTS.map((element, index) => {
            const config = WUXING_CONFIG[element]
            const count = elementStats[element] || 0
            const percentage = getElementPercentage(element)
            const isActive = filterElement === element

            return (
              <motion.button
                key={element}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + index * 0.05 }}
                onClick={() => handleFilterChange(isActive ? null : element)}
                className={`flex-1 group relative overflow-hidden rounded-2xl p-4 transition-all ${
                  isActive 
                    ? 'ring-2 ring-offset-2 scale-105 shadow-lg' 
                    : 'hover:scale-102 hover:shadow-md'
                }`}
                style={{
                  background: `linear-gradient(135deg, ${config.gradientFrom}20, ${config.gradientTo}10)`,
                  borderColor: isActive ? config.gradientFrom : 'transparent',
                }}
              >
                <div className="text-center relative z-10">
                  <span className="text-2xl mb-2 block">{config.emoji}</span>
                  <span className="text-lg font-bold text-stone-700">{element}</span>
                  <div className="mt-1 text-2xl font-bold" style={{ color: config.gradientFrom }}>
                    {count}
                  </div>
                  <span className="text-xs text-stone-400">{percentage}%</span>
                </div>
                
                {/* 背景进度条 */}
                <div 
                  className="absolute bottom-0 left-0 right-0 transition-all duration-500"
                  style={{
                    height: `${Math.max(percentage, 8)}%`,
                    background: `linear-gradient(to top, ${config.gradientFrom}30, transparent)`,
                  }}
                />
              </motion.button>
            )
          })}
        </div>
      </motion.div>

      {/* 衣物展示区 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        {isLoading && items.length === 0 ? (
          <div className="flex items-center justify-center py-32">
            <motion.div className="relative">
              {[...Array(5)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute w-4 h-4 rounded-full"
                  style={{
                    background: Object.values(WUXING_CONFIG)[i].gradientFrom,
                    left: i * 24 - 48,
                  }}
                  animate={{
                    y: [0, -20, 0],
                    opacity: [0.3, 1, 0.3],
                  }}
                  transition={{
                    duration: 1,
                    delay: i * 0.1,
                    repeat: Infinity,
                  }}
                />
              ))}
            </motion.div>
          </div>
        ) : filteredItems.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-24"
          >
            <div className="w-24 h-24 mx-auto mb-6 relative">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                className="absolute inset-0 border-2 border-dashed border-stone-200 rounded-full"
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-4xl">👔</span>
              </div>
            </div>
            <h3 className="text-xl font-medium text-stone-700 mb-2" style={{ fontFamily: 'serif' }}>
              {filterElement ? '此五行暂无衣物' : '衣橱空空如也'}
            </h3>
            <p className="text-stone-500 mb-8">
              {filterElement ? '换个五行属性看看' : '开启您的五行穿搭之旅'}
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleAddNew}
              className="px-8 py-3 rounded-2xl bg-gradient-to-r from-stone-800 to-stone-700 text-white font-medium shadow-xl"
            >
              添加第一件衣物
            </motion.button>
          </motion.div>
        ) : (
          <div className={viewMode === 'grid' 
            ? "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
            : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          }>
            <AnimatePresence mode="popLayout">
              {filteredItems.map((item, index) => {
                const config = getWuxingConfig(item.primary_element)
                const theme = WUXING_THEME[item.primary_element] || WUXING_THEME['金']

                return (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, y: 20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ delay: index * 0.03, duration: 0.3 }}
                    className={`group relative overflow-hidden rounded-3xl bg-white shadow-sm hover:shadow-xl transition-all duration-500 ${
                      viewMode === 'flow' ? 'aspect-[4/3]' : 'aspect-[3/4]'
                    }`}
                  >
                    {/* 背景装饰 */}
                    <div 
                      className="absolute inset-0 opacity-30"
                      style={{ background: `linear-gradient(135deg, ${config.gradientFrom}20, ${config.gradientTo}10)` }}
                    />
                    
                    {/* 五行符号背景 */}
                    <div 
                      className="absolute -right-4 -top-4 text-8xl opacity-5 font-serif"
                      style={{ color: config.gradientFrom }}
                    >
                      {theme.symbol}
                    </div>

                    {/* 操作按钮 */}
                    <div className="absolute top-3 right-3 z-20 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-300">
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => { setEditItem(item); setIsModalOpen(true) }}
                        className="p-2 rounded-xl bg-white/90 backdrop-blur-md shadow-lg text-stone-500 hover:text-blue-600 hover:bg-blue-50 transition-all"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l2.768 2.768m-2.768-2.768l-5.5 5.5a1 1 0 00-.293.707v2.536a1 1 0 001 1h2.536a1 1 0 00.707-.293l5.5-5.5M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5" />
                        </svg>
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id}
                        className="p-2 rounded-xl bg-white/90 backdrop-blur-md shadow-lg text-stone-500 hover:text-rose-600 hover:bg-rose-50 transition-all"
                      >
                        {deletingId === item.id ? (
                          <motion.svg className="w-4 h-4" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </motion.svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </motion.button>
                    </div>

                    {/* 图片区域 */}
                    <div className={`relative ${viewMode === 'flow' ? 'h-2/3' : 'h-3/4'} overflow-hidden`}>
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none'
                          }}
                        />
                      ) : (
                        <div 
                          className="w-full h-full flex items-center justify-center"
                          style={{ background: `linear-gradient(135deg, ${config.gradientFrom}30, ${config.gradientTo}20)` }}
                        >
                          <motion.span 
                            className="text-6xl opacity-60"
                            animate={{ scale: [1, 1.1, 1] }}
                            transition={{ duration: 3, repeat: Infinity }}
                          >
                            {config.emoji}
                          </motion.span>
                        </div>
                      )}
                      
                      {/* 底部渐变 */}
                      <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-white to-transparent" />
                    </div>

                    {/* 信息区域 */}
                    <div className={`absolute bottom-0 left-0 right-0 p-4 ${viewMode === 'flow' ? 'h-1/3' : 'h-1/4'}`}>
                      {/* 五行标签 */}
                      <div className="flex items-center gap-2 mb-2">
                        <span 
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold shadow-sm"
                          style={{ 
                            background: `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})`,
                            color: 'white',
                          }}
                        >
                          {config.emoji} {item.primary_element}
                        </span>
                        {item.secondary_element && (
                          <span className="text-xs text-stone-400 bg-stone-100 px-2 py-0.5 rounded-full">
                            +{item.secondary_element}
                          </span>
                        )}
                        {item.category && (
                          <span className="text-xs text-stone-400">
                            · {item.category}
                          </span>
                        )}
                      </div>
                      
                      {/* 名称 */}
                      <h3 className="font-medium text-stone-800 truncate" title={item.name}>
                        {item.name}
                      </h3>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        )}
      </motion.div>

      {/* 添加/编辑弹窗 */}
      <AddWardrobeModal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditItem(null) }}
        onSuccess={() => { fetchItems(); setIsModalOpen(false); setEditItem(null) }}
        editItem={editItem}
      />
    </div>
  )
}
