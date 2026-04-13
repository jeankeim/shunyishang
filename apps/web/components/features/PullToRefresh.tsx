'use client'

import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw } from 'lucide-react'

interface PullToRefreshProps {
  onRefresh: () => Promise<void>
  children: React.ReactNode
  threshold?: number // 触发刷新的下拉距离（像素）
}

export const PullToRefresh: React.FC<PullToRefreshProps> = ({
  onRefresh,
  children,
  threshold = 80,
}) => {
  const [pulling, setPulling] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const startY = useRef(0)
  const currentY = useRef(0)

  const handleTouchStart = useCallback((e: TouchEvent) => {
    // 只在顶部时允许下拉刷新
    if (window.scrollY === 0) {
      startY.current = e.touches[0].clientY
    }
  }, [])

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (startY.current === 0 || refreshing) return
    
    currentY.current = e.touches[0].clientY
    const distance = currentY.current - startY.current
    
    // 只处理下拉
    if (distance > 0) {
      e.preventDefault()
      setPulling(true)
      setPullDistance(Math.min(distance, threshold * 1.5)) // 限制最大距离
    }
  }, [refreshing, threshold])

  const handleTouchEnd = useCallback(async () => {
    if (!pulling || refreshing) {
      setPulling(false)
      setPullDistance(0)
      startY.current = 0
      return
    }

    // 检查是否达到阈值
    if (pullDistance >= threshold) {
      setRefreshing(true)
      setPullDistance(0)
      
      try {
        await onRefresh()
      } catch (error) {
        console.error('[PullToRefresh] 刷新失败:', error)
      } finally {
        setRefreshing(false)
      }
    }

    setPulling(false)
    setPullDistance(0)
    startY.current = 0
  }, [pulling, refreshing, pullDistance, threshold, onRefresh])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    container.addEventListener('touchstart', handleTouchStart, { passive: true })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [handleTouchStart, handleTouchMove, handleTouchEnd])

  const progress = Math.min(pullDistance / threshold, 1)
  const rotation = progress * 360

  return (
    <div ref={containerRef} className="relative">
      {/* 下拉刷新指示器 */}
      <AnimatePresence>
        {(pulling || refreshing) && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center pt-4 pb-2 bg-white/90 backdrop-blur-md border-b border-gray-200 safe-top"
          >
            {refreshing ? (
              <>
                <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
                <span className="ml-2 text-sm font-medium text-gray-600">刷新中...</span>
              </>
            ) : (
              <>
                <motion.div
                  animate={{ rotate: rotation }}
                  transition={{ type: "tween", duration: 0.1 }}
                >
                  <RefreshCw className="w-5 h-5 text-blue-500" />
                </motion.div>
                <span className="ml-2 text-sm font-medium text-gray-600">
                  {progress >= 1 ? '松开刷新' : '下拉刷新'}
                </span>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 内容区域 */}
      <div
        style={{
          transform: pulling && !refreshing ? `translateY(${pullDistance}px)` : undefined,
          transition: pulling && !refreshing ? 'none' : 'transform 0.3s ease',
        }}
      >
        {children}
      </div>
    </div>
  )
}
