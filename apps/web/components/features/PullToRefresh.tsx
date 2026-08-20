'use client'

import React, { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw } from 'lucide-react'

interface PullToRefreshProps {
  onRefresh: () => Promise<void>
  children: React.ReactNode
  threshold?: number // 触发刷新的下拉距离（像素）
}

const DAMPING = 0.5 // 下拉阻尼系数，接近 iOS 原生手感
const AXIS_LOCK_PX = 8 // 方向锁定判定阈值（像素）

function isVerticallyScrollable(el: HTMLElement): boolean {
  const oy = window.getComputedStyle(el).overflowY
  return oy === 'auto' || oy === 'scroll' || oy === 'overlay'
}

// 向上查找最近的可纵向滚动祖先（computed style 判定，兼容 Safari/Chrome，不依赖类名）
function findScrollable(el: Element | null): HTMLElement | null {
  let node = el
  while (node && node !== document.documentElement) {
    if (node instanceof HTMLElement && isVerticallyScrollable(node)) return node
    node = node.parentElement
  }
  return null
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
  const outerScrollRef = useRef<HTMLElement | null>(null)

  // 手势可变状态：ref 保存避免闭包过期，同时保持监听器只注册一次
  const gesture = useRef({
    startX: 0,
    startY: 0,
    tracking: false, // 候选态：在顶部开始触摸，等待方向锁定
    active: false,   // 下拉刷新已接管当前手势
  })
  const pullDistanceRef = useRef(0)
  const refreshingRef = useRef(false)
  refreshingRef.current = refreshing

  const updatePullDistance = useCallback((v: number) => {
    pullDistanceRef.current = v
    setPullDistance(v)
  }, [])

  const handleTouchStart = useCallback((e: TouchEvent) => {
    const g = gesture.current
    g.tracking = false
    g.active = false
    // 刷新中或多指触摸不响应
    if (refreshingRef.current || e.touches.length > 1) return
    const container = containerRef.current
    if (!container) return
    // 弹窗/表单控件内不介入，保留其原生手势
    const target = e.target as Element | null
    if (target?.closest?.('[role="dialog"], input, textarea, select, [data-ptr-ignore]')) return
    // 触摸点路径上的嵌套可滚动层必须都在顶部，否则交给内层容器原生滚动
    let node: Element | null = target
    while (node && node !== container) {
      if (node instanceof HTMLElement && isVerticallyScrollable(node) && node.scrollTop > 0) return
      node = node.parentElement
    }
    // 外层滚动容器在顶部（兼容 overflow-y-auto 容器和 window 滚动）
    const outer = findScrollable(container.parentElement)
    outerScrollRef.current = outer
    const atTop = outer ? outer.scrollTop <= 0 : window.scrollY <= 0
    if (!atTop) return

    g.tracking = true
    g.startX = e.touches[0].clientX
    g.startY = e.touches[0].clientY
  }, [])

  const handleTouchMove = useCallback((e: TouchEvent) => {
    const g = gesture.current
    if (refreshingRef.current || (!g.tracking && !g.active)) return
    const touch = e.touches[0]
    if (!touch) return
    const dx = touch.clientX - g.startX
    const dy = touch.clientY - g.startY

    if (!g.active) {
      // 方向锁定：横向意图优先交还浏览器，避免与横滑/ Safari 边缘返回手势冲突
      if (Math.abs(dx) > AXIS_LOCK_PX && Math.abs(dx) > Math.abs(dy)) {
        g.tracking = false
        return
      }
      if (dy <= AXIS_LOCK_PX) return // 下拉幅度不足，继续等待
      g.active = true
      setPulling(true)
    }

    // 接管后始终阻止默认行为，防止 iOS Safari 橡皮筋/Chrome 原生下拉刷新介入
    // （监听器以 passive: false 注册，Safari/Chrome 才会尊重 preventDefault）
    e.preventDefault()
    updatePullDistance(dy > 0 ? Math.min(dy * DAMPING, threshold * 1.5) : 0)
  }, [threshold, updatePullDistance])

  const handleTouchEnd = useCallback(async () => {
    const g = gesture.current
    const reached = g.active && pullDistanceRef.current >= threshold
    g.tracking = false
    g.active = false
    if (!reached || refreshingRef.current) {
      setPulling(false)
      updatePullDistance(0)
      return
    }
    // 达到阈值：回正滚动位置并进入刷新态
    outerScrollRef.current?.scrollTo({ top: 0 })
    setPulling(false)
    updatePullDistance(0)
    setRefreshing(true)
    refreshingRef.current = true
    try {
      await onRefresh()
    } catch (error) {
      console.error('[PullToRefresh] 刷新失败:', error)
    } finally {
      refreshingRef.current = false
      setRefreshing(false)
    }
  }, [threshold, onRefresh, updatePullDistance])

  // Safari 系统手势接管（通知中心、返回等）会触发 touchcancel，必须复位避免指示器卡死
  const handleTouchCancel = useCallback(() => {
    gesture.current.tracking = false
    gesture.current.active = false
    setPulling(false)
    updatePullDistance(0)
  }, [updatePullDistance])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    container.addEventListener('touchstart', handleTouchStart, { passive: true })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd)
    container.addEventListener('touchcancel', handleTouchCancel)

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
      container.removeEventListener('touchcancel', handleTouchCancel)
    }
  }, [handleTouchStart, handleTouchMove, handleTouchEnd, handleTouchCancel])

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

      {/* 内容区域：下拉时用 translate3d 触发 GPU 合成，Safari 上更稳定 */}
      <div
        style={{
          transform: pulling && !refreshing ? `translate3d(0, ${pullDistance}px, 0)` : undefined,
          transition: pulling && !refreshing ? 'none' : 'transform 0.3s ease',
        }}
      >
        {children}
      </div>
    </div>
  )
}
