'use client'

import React, { useState, useRef, useCallback } from 'react'
import { motion, PanInfo } from 'framer-motion'
import { Trash2 } from 'lucide-react'

interface SwipeToDeleteProps {
  children: React.ReactNode
  onSwipe: () => Promise<void>
  threshold?: number // 触发删除的滑动距离（像素）
}

export const SwipeToDelete: React.FC<SwipeToDeleteProps> = ({
  children,
  onSwipe,
  threshold = 100,
}) => {
  const [dragX, setDragX] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)
  const constraintsRef = useRef<HTMLDivElement>(null)

  const handleDragEnd = useCallback(async (_event: MouseEvent | TouchEvent, info: PanInfo) => {
    const offset = info.offset.x
    
    // 左滑超过阈值
    if (offset < -threshold && !isDeleting) {
      setIsDeleting(true)
      setDragX(-200) // 完全显示删除按钮
      
      try {
        await onSwipe()
      } catch (error) {
        console.error('[SwipeToDelete] 删除失败:', error)
        setDragX(0) // 恢复原位
      } finally {
        setIsDeleting(false)
      }
    } else {
      // 未达到阈值，弹回原位
      setDragX(0)
    }
  }, [threshold, onSwipe, isDeleting])

  const handleDrag = useCallback((_event: MouseEvent | TouchEvent, info: PanInfo) => {
    // 只允许左滑
    if (info.offset.x > 0) {
      setDragX(0)
    } else {
      setDragX(Math.max(info.offset.x, -200)) // 限制最大滑动距离
    }
  }, [])

  return (
    <div className="relative overflow-hidden rounded-xl">
      {/* 删除按钮背景 */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-red-500 to-red-600 flex items-center justify-end pr-4 rounded-xl"
        initial={false}
      >
        <div className="flex items-center gap-2 text-white">
          <Trash2 className="w-5 h-5" />
          <span className="text-sm font-medium">删除</span>
        </div>
      </motion.div>

      {/* 可拖动内容 */}
      <motion.div
        ref={constraintsRef}
        drag="x"
        dragConstraints={{ left: -200, right: 0 }}
        dragElastic={0.2}
        style={{ x: dragX }}
        onDrag={handleDrag}
        onDragEnd={handleDragEnd}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="relative z-10 bg-white touch-none"
      >
        {children}
      </motion.div>
    </div>
  )
}
