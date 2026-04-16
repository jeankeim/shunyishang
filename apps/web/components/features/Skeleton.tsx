'use client'

import { motion } from 'framer-motion'

interface SkeletonProps {
  type?: 'card' | 'list' | 'text' | 'image' | 'recommend'
  count?: number
}

export function Skeleton({ type = 'card', count = 3 }: SkeletonProps) {
  const renderSkeleton = () => {
    switch (type) {
      case 'card':
        return (
          <div className="bg-white rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-stone-200 animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-stone-200 rounded animate-pulse w-3/4" />
                <div className="h-3 bg-stone-200 rounded animate-pulse w-1/2" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-stone-200 rounded animate-pulse" />
              <div className="h-3 bg-stone-200 rounded animate-pulse w-5/6" />
            </div>
          </div>
        )

      case 'list':
        return (
          <div className="space-y-3">
            {Array.from({ length: count }).map((_, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-3 p-3 bg-white rounded-xl"
              >
                <div className="w-10 h-10 rounded-lg bg-stone-200 animate-pulse flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-stone-200 rounded animate-pulse w-2/3" />
                  <div className="h-3 bg-stone-200 rounded animate-pulse w-1/2" />
                </div>
              </motion.div>
            ))}
          </div>
        )

      case 'text':
        return (
          <div className="space-y-2">
            <div className="h-4 bg-stone-200 rounded animate-pulse w-full" />
            <div className="h-4 bg-stone-200 rounded animate-pulse w-5/6" />
            <div className="h-4 bg-stone-200 rounded animate-pulse w-4/6" />
          </div>
        )

      case 'image':
        return (
          <div className="relative aspect-square rounded-2xl overflow-hidden bg-stone-200 animate-pulse">
            <div className="absolute inset-0 bg-gradient-to-r from-stone-200 via-stone-100 to-stone-200 animate-pulse" />
          </div>
        )

      case 'recommend':
        return (
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-5 shadow-sm space-y-4">
            {/* 标题 */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-stone-200 animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-5 bg-stone-200 rounded animate-pulse w-2/3" />
                <div className="h-3 bg-stone-200 rounded animate-pulse w-1/2" />
              </div>
            </div>
            
            {/* 图片 */}
            <div className="aspect-[3/4] rounded-xl bg-stone-200 animate-pulse" />
            
            {/* 描述 */}
            <div className="space-y-2">
              <div className="h-4 bg-stone-200 rounded animate-pulse" />
              <div className="h-4 bg-stone-200 rounded animate-pulse w-5/6" />
              <div className="h-4 bg-stone-200 rounded animate-pulse w-4/6" />
            </div>
            
            {/* 标签 */}
            <div className="flex gap-2">
              <div className="h-6 w-16 rounded-full bg-stone-200 animate-pulse" />
              <div className="h-6 w-20 rounded-full bg-stone-200 animate-pulse" />
              <div className="h-6 w-14 rounded-full bg-stone-200 animate-pulse" />
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return <>{renderSkeleton()}</>
}
