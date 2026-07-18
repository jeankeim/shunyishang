'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RecommendItem } from '@/types'
import { submitFeedback, reportBehavior } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'
import { ItemDetailModal } from './ItemDetailModal'

interface RecommendCardProps {
  item: RecommendItem
  index: number
  sessionId?: string
  onFeedback?: (action: 'like' | 'dislike') => void
  onImageClick?: (imageUrl: string) => void
}

export function RecommendCard({ item, index, sessionId, onFeedback, onImageClick }: RecommendCardProps) {
  const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [showDislikeReasons, setShowDislikeReasons] = useState(false)
  const [selectedReason, setSelectedReason] = useState<string | null>(null)
  const dwellTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hasReportedView = useRef(false)
  const hasReportedDwell = useRef(false)
  const config = getWuxingConfig(item.primary_element)

  // 行为埋点：卡片曝光（view）
  useEffect(() => {
    if (!hasReportedView.current) {
      hasReportedView.current = true
      reportBehavior(undefined, item.item_id || item.item_code || '', 'view')
    }
  }, [item.item_id, item.item_code])

  // 行为埋点：停留检测（dwell > 3秒）
  useEffect(() => {
    dwellTimerRef.current = setTimeout(() => {
      if (!hasReportedDwell.current) {
        hasReportedDwell.current = true
        reportBehavior(undefined, item.item_id || item.item_code || '', 'dwell', 3)
      }
    }, 3000)

    return () => {
      if (dwellTimerRef.current) clearTimeout(dwellTimerRef.current)
    }
  }, [item.item_id, item.item_code])

  const fullImageUrl = getImageUrl(item.image_url)
  const thumbnailUrl = item.thumbnail_url ? getImageUrl(item.thumbnail_url) : null
  const shouldShowImage = fullImageUrl && !imageError
  
  // 优先使用缩略图，如果没有则使用原图
  const displayImageUrl = thumbnailUrl || fullImageUrl

  // 行为埋点：展开详情
  const handleToggleDetails = () => {
    if (!showDetails) {
      reportBehavior(undefined, item.item_id || item.item_code || '', 'expand')
    }
    setShowDetails(!showDetails)
  }

  // 行为埋点：点击图片
  const handleImageClick = (url: string) => {
    reportBehavior(undefined, item.item_id || item.item_code || '', 'image_click')
    onImageClick?.(url)
  }

  const handleFeedback = async (action: 'like' | 'dislike') => {
    if (feedback || isSubmitting) return

    // 行为埋点：点击反馈
    reportBehavior(undefined, item.item_id || item.item_code || '', 'click')

    if (action === 'dislike') {
      // dislike 先展示原因选择器，不立即提交
      setShowDislikeReasons(true)
      return
    }

    setIsSubmitting(true)
    try {
      await submitFeedback({
        session_id: sessionId,
        item_id: item.item_id,
        item_code: item.item_code,
        item_source: item.source || 'public',
        action,
      })
      setFeedback(action)
      onFeedback?.(action)
    } catch (error) {
      console.error('反馈提交失败:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDislikeReason = async (reason: string) => {
    setSelectedReason(reason)
    setShowDislikeReasons(false)
    setIsSubmitting(true)
    try {
      await submitFeedback({
        session_id: sessionId,
        item_id: item.item_id,
        item_code: item.item_code,
        item_source: item.source || 'public',
        action: 'dislike',
        feedback_reason: reason,
      })
      setFeedback('dislike')
      onFeedback?.('dislike')
    } catch (error) {
      console.error('反馈提交失败:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const DISLIKE_REASONS = [
    { value: 'style', label: '风格不符' },
    { value: 'color', label: '颜色不喜欢' },
    { value: 'scene', label: '不适合场景' },
    { value: 'thickness', label: '太厚/太薄' },
    { value: 'other', label: '其他' },
  ]

  const isFromWardrobe = item.source === 'wardrobe'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      whileTap={{ scale: 0.98 }}
      className="bg-card rounded-lg border overflow-hidden hover:shadow-lg transition-shadow touch-manipulation"
      style={{ willChange: 'transform' }}
    >
      {/* 元素渐变占位图 */}
      {shouldShowImage ? (
        <motion.div
          className="h-40 cursor-pointer relative overflow-hidden group"
          style={{ backgroundImage: `url(${displayImageUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
          onClick={() => handleImageClick(fullImageUrl!)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-10 h-10 bg-white/90 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-stone-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </div>
          </div>
          {/* 缩略图标记 */}
          {thumbnailUrl && (
            <div className="absolute top-2 right-2 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-full text-xs text-white">
              缩略图
            </div>
          )}
        </motion.div>
      ) : (
        <div
          className={`h-40 bg-gradient-to-br ${config.gradientClass} flex items-center justify-center relative`}
        >
          <span className="text-4xl opacity-60">{config.emoji}</span>
          
          {/* 来源标签 */}
          <div className={`absolute top-2 left-2 px-2 py-0.5 rounded-full text-xs font-medium ${
            isFromWardrobe 
              ? 'bg-emerald-500/90 text-white' 
              : 'bg-blue-500/90 text-white'
          }`}>
            {isFromWardrobe ? '🏠 自有' : '📚 公共库'}
          </div>
        </div>
      )}
      
      {/* 如果有图片且是衣橱物品，也显示标签 */}
      {shouldShowImage && (
        <div className="relative -mt-8 ml-2 w-fit">
          <div className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            isFromWardrobe 
              ? 'bg-emerald-500/90 text-white' 
              : 'bg-blue-500/90 text-white'
          }`}>
            {isFromWardrobe ? '🏠 自有' : '📚 公共库'}
          </div>
        </div>
      )}
      
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <button
            onClick={() => setShowDetailModal(true)}
            className="text-left flex-1 min-w-0 group"
          >
            <h4 className="font-medium text-sm line-clamp-2 text-stone-700 group-hover:text-[var(--wuxing-wood)] transition-colors">
              {item.name}
            </h4>
          </button>
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium shrink-0 ${config.bgClass} ${config.textClass}`}
          >
            {item.primary_element}
          </span>
        </div>
        <p className="text-xs text-stone-500 mt-1">{item.category}</p>
        {item.color && (
          <p className="text-xs text-stone-500 mt-1">颜色：{item.color}</p>
        )}
        
        {/* 综合匹配度 + 展开详情 */}
        <div className="mt-3 pt-3 border-t border-stone-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-stone-500 text-xs">综合匹配</span>
                <span className="font-bold text-[var(--wuxing-earth)] text-lg">
                  {(item.final_score * 100).toFixed(0)}%
                </span>
              </div>
              {/* 展开/收起按钮 */}
              <button
                onClick={handleToggleDetails}
                className="p-1.5 rounded-lg hover:bg-stone-100 transition-all"
                aria-label={showDetails ? '收起详情' : '展开详情'}
              >
                <svg 
                  className={`w-4 h-4 text-stone-400 transition-transform duration-200 ${showDetails ? 'rotate-180' : ''}`}
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
            
            {/* 反馈按钮 */}
            <div className="flex gap-1 relative">
              <button
                onClick={() => handleFeedback('like')}
                disabled={!!feedback || isSubmitting}
                className={`p-1.5 rounded-full transition-all ${
                  feedback === 'like'
                    ? 'bg-emerald-100 text-emerald-600'
                    : 'hover:bg-stone-100 text-[var(--brand-subtle)] hover:text-emerald-500'
                } disabled:cursor-not-allowed`}
              >
                <svg className="w-4 h-4" fill={feedback === 'like' ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
              </button>
              <button
                onClick={() => handleFeedback('dislike')}
                disabled={!!feedback || isSubmitting}
                className={`p-1.5 rounded-full transition-all ${
                  feedback === 'dislike'
                    ? 'bg-red-100 text-red-600'
                    : 'hover:bg-stone-100 text-[var(--brand-subtle)] hover:text-red-500'
                } disabled:cursor-not-allowed`}
              >
                <svg className="w-4 h-4" fill={feedback === 'dislike' ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                </svg>
              </button>

              {/* Dislike 原因选择器 */}
              <AnimatePresence>
                {showDislikeReasons && !feedback && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full mt-1 z-20 bg-white rounded-lg shadow-lg border border-stone-200 p-2 min-w-[140px]"
                  >
                    <p className="text-xs text-stone-500 mb-1.5 px-1">不喜欢的原因：</p>
                    {DISLIKE_REASONS.map((r) => (
                      <button
                        key={r.value}
                        onClick={() => handleDislikeReason(r.value)}
                        className="w-full text-left px-2 py-1.5 text-xs rounded-md hover:bg-red-50 hover:text-red-600 text-stone-600 transition-colors"
                      >
                        {r.label}
                      </button>
                    ))}
                    <button
                      onClick={() => setShowDislikeReasons(false)}
                      className="w-full text-center px-2 py-1 text-xs text-stone-400 hover:text-stone-600 mt-1 border-t border-stone-100 pt-1"
                    >
                      取消
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
          
          {/* 详细评分（可折叠） */}
          {showDetails && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-3 space-y-2 overflow-hidden"
            >
              {/* 语义匹配 */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-stone-500 w-16">语义匹配</span>
                <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all"
                    style={{ width: `${(item.semantic_score || 0.5) * 100}%` }}
                  />
                </div>
                <span className="text-stone-600 font-medium w-10 text-right">
                  {((item.semantic_score || 0.5) * 100).toFixed(0)}%
                </span>
              </div>
              
              {/* 五行匹配 */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-stone-500 w-16">五行匹配</span>
                <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all ${config.gradientClass}`}
                    style={{ width: `${(item.wuxing_score || 0) * 100}%` }}
                  />
                </div>
                <span className="text-stone-600 font-medium w-10 text-right">
                  {((item.wuxing_score || 0) * 100).toFixed(0)}%
                </span>
              </div>
              
              {/* 场景适配（如果有场景分数） */}
              {item.scene_score !== undefined && item.scene_score > 0 && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-stone-500 w-16">场景适配</span>
                  <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-amber-400 to-amber-600 rounded-full transition-all"
                      style={{ width: `${item.scene_score * 100}%` }}
                    />
                  </div>
                  <span className="text-stone-600 font-medium w-10 text-right">
                    {(item.scene_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}

              {/* 偏好匹配（如果有偏好分数且不是默认中性值） */}
              {item.preference_score !== undefined && item.preference_score !== 0.5 && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-stone-500 w-16">偏好匹配</span>
                  <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        item.preference_score > 0.5 
                          ? 'bg-gradient-to-r from-emerald-400 to-emerald-600' 
                          : 'bg-gradient-to-r from-red-300 to-red-500'
                      }`}
                      style={{ width: `${item.preference_score * 100}%` }}
                    />
                  </div>
                  <span className="text-stone-600 font-medium w-10 text-right">
                    {(item.preference_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </motion.div>
          )}
        </div>
        
        {item.reason && (
          <p className="text-xs text-stone-500 mt-2 line-clamp-2">{item.reason}</p>
        )}
      </div>

      {/* 物品详情弹窗 */}
      {showDetailModal && (
        <ItemDetailModal
          item={item}
          onClose={() => setShowDetailModal(false)}
        />
      )}
    </motion.div>
  )
}
