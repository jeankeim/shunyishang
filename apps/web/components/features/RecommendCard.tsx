'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RecommendItem } from '@/types'
import { submitFeedback, cancelFeedback, reportBehavior, WardrobeSimilarItem } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'
import { useUserStore } from '@/store/user'
import { ItemDetailModal } from './ItemDetailModal'
import { WardrobeSimilarSheet } from './WardrobeSimilarSheet'

interface RecommendCardProps {
  item: RecommendItem
  index: number
  sessionId?: string
  onFeedback?: (action: 'like' | 'dislike') => void
  onImageClick?: (imageUrl: string) => void
  /** 是否显示卡片底部推荐理由小字（搭配页仅对最相关1-2张显示，避免雷同重复） */
  showReason?: boolean
  /** 衣橱相似款替换（灵感库单品→用户衣橱同款/类似款，原位替换到推荐网格） */
  onReplaceItem?: (oldItem: RecommendItem, newItem: RecommendItem, similar: WardrobeSimilarItem) => void
  /** 相似款面板空态「去衣橱添加」导流 */
  onNavigateToWardrobe?: () => void
}

// 点踩原因配置：五行传统色系（低饱和、雅致）
const DISLIKE_REASONS = [
  { value: 'style', label: '风格不符', color: 'bg-[#5B7B6A]', ring: 'ring-[#5B7B6A]/30' },   // 松石绿
  { value: 'color', label: '颜色不喜欢', color: 'bg-[#8B6B5B]', ring: 'ring-[#8B6B5B]/30' }, // 赫石棕
  { value: 'scene', label: '不适合场景', color: 'bg-[#6B7B8B]', ring: 'ring-[#6B7B8B]/30' }, // 青灰蓝
  { value: 'thickness', label: '太厚/太薄', color: 'bg-[#7B6B5B]', ring: 'ring-[#7B6B5B]/30' }, // 檀木色
  { value: 'other', label: '其他', color: 'bg-[#5A5A5A]', ring: 'ring-[#5A5A5A]/30' },       // 墨灰
]

export function RecommendCard({ item, index, sessionId, onFeedback, onImageClick, showReason = true, onReplaceItem, onNavigateToWardrobe }: RecommendCardProps) {
  const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  // 图片覆盖层交互状态
  const [showOverlay, setShowOverlay] = useState(false)
  const [showReasons, setShowReasons] = useState(false)
  const [feedbackAnimation, setFeedbackAnimation] = useState<'like' | 'dislike' | null>(null)
  // 点踩多选状态
  const [selectedReasons, setSelectedReasons] = useState<string[]>([])
  const [submitError, setSubmitError] = useState<string | null>(null)
  // 衣橱相似款面板
  const [showSimilarSheet, setShowSimilarSheet] = useState(false)
  const dwellTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hasReportedView = useRef(false)
  const hasReportedDwell = useRef(false)
  const config = getWuxingConfig(item.primary_element)
  const isAuthenticated = useUserStore((s) => s.isAuthenticated)

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
  const displayImageUrl = thumbnailUrl || fullImageUrl

  // 行为埋点：展开详情
  const handleToggleDetails = () => {
    if (!showDetails) {
      reportBehavior(undefined, item.item_id || item.item_code || '', 'expand')
    }
    setShowDetails(!showDetails)
  }

  // 点击图片 → 显示反馈覆盖层（已反馈时显示撤销选项）
  const handleImageTap = () => {
    reportBehavior(undefined, item.item_id || item.item_code || '', 'image_click')
    setShowOverlay(true)
    setShowReasons(false)
    setSelectedReasons([])
    setSubmitError(null)
  }

  // 点赞（小爱心）
  const handleLike = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)
    reportBehavior(undefined, item.item_id || item.item_code || '', 'click')
    try {
      await submitFeedback({
        session_id: sessionId,
        item_id: item.item_id,
        item_code: item.item_code,
        item_source: item.source || 'public',
        action: 'like',
      })
      setFeedback('like')
      setFeedbackAnimation('like')
      onFeedback?.('like')
      // 动画后关闭覆盖层
      setTimeout(() => {
        setShowOverlay(false)
        setFeedbackAnimation(null)
      }, 800)
    } catch (error) {
      console.error('反馈提交失败:', error)
      setSubmitError(error instanceof Error ? error.message : '提交失败，请重试')
    } finally {
      setIsSubmitting(false)
    }
  }

  // 点踩 → 显示原因选择
  const handleDislikeTap = () => {
    reportBehavior(undefined, item.item_id || item.item_code || '', 'click')
    setShowReasons(true)
    setSelectedReasons([])
    setSubmitError(null)
  }

  // 切换点踩原因选中状态（多选）
  const toggleReason = (reason: string) => {
    setSelectedReasons(prev =>
      prev.includes(reason) ? prev.filter(r => r !== reason) : [...prev, reason]
    )
  }

  // 确认提交点踩（多选原因）
  const handleDislikeConfirm = async () => {
    if (isSubmitting || selectedReasons.length === 0) return
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      await submitFeedback({
        session_id: sessionId,
        item_id: item.item_id,
        item_code: item.item_code,
        item_source: item.source || 'public',
        action: 'dislike',
        feedback_reason: selectedReasons.join(','),
      })
      setFeedback('dislike')
      setFeedbackAnimation('dislike')
      onFeedback?.('dislike')
      setTimeout(() => {
        setShowOverlay(false)
        setShowReasons(false)
        setFeedbackAnimation(null)
      }, 800)
    } catch (error) {
      console.error('反馈提交失败:', error)
      setSubmitError(error instanceof Error ? error.message : '提交失败，请重试')
    } finally {
      setIsSubmitting(false)
    }
  }

  // 撤销反馈
  const handleUndoFeedback = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)
    try {
      await cancelFeedback(item.item_code || '', item.item_id)
      setFeedback(null)
      setShowOverlay(false)
      setShowReasons(false)
      setSelectedReasons([])
    } catch (error) {
      console.error('撤销反馈失败:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isFromWardrobe = item.source === 'wardrobe'

  // 「找相似」仅对灵感库（公共库）单品 + 已登录用户展示：衣橱模式/未登录无替换意义
  const canFindSimilar = !isFromWardrobe && !!onReplaceItem && isAuthenticated && !!item.item_code

  // 相似款面板点「替换」→ 构造衣橱单品并原位替换（保留槽位分数，清掉公共库推荐理由）
  const handleReplaceSimilar = (similar: WardrobeSimilarItem) => {
    onReplaceItem?.(item, {
      item_code: `wardrobe-${similar.id}`,
      item_id: similar.id,
      name: similar.name,
      category: similar.category,
      primary_element: similar.primary_element || item.primary_element,
      secondary_element: similar.secondary_element ?? undefined,
      final_score: item.final_score,
      image_url: similar.image_url || undefined,
      source: 'wardrobe',
    }, similar)
    setShowSimilarSheet(false)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className="bg-card rounded-xl border hover:shadow-lg transition-shadow overflow-hidden"
    >
      {/* ===== 图片区域 + 反馈覆盖层 ===== */}
      <div className="relative">
        {shouldShowImage ? (
          <div
            className="h-40 sm:h-44 cursor-pointer relative overflow-hidden"
            style={{ backgroundImage: `url(${displayImageUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
            onClick={handleImageTap}
          >
            {/* 来源标签 */}
            <div className={`absolute top-2 left-2 z-10 px-2 py-0.5 rounded-full text-[10px] font-medium backdrop-blur-sm ${
              item.is_anchor ? 'bg-amber-500/90 text-white' : isFromWardrobe ? 'bg-emerald-500/80 text-white' : 'bg-blue-500/80 text-white'
            }`}>
              {item.is_anchor ? '🎯 指定' : isFromWardrobe ? '🏠 自有' : '📚 公共库'}
            </div>
            {/* 放大查看按钮 */}
            <button
              onClick={(e) => { e.stopPropagation(); setShowDetailModal(true) }}
              className="absolute top-2 right-2 z-10 w-7 h-7 bg-black/30 backdrop-blur-sm rounded-full flex items-center justify-center text-white/80 hover:text-white hover:bg-black/50 transition-all"
              aria-label="查看大图"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </button>
            {/* 找相似：灵感库单品→衣橱同款/类似款原位替换 */}
            {canFindSimilar && (
              <button
                onClick={(e) => { e.stopPropagation(); setShowSimilarSheet(true) }}
                className="absolute bottom-2 left-2 z-10 flex items-center gap-1 px-2 py-1 rounded-full bg-black/35 backdrop-blur-sm text-[10px] font-medium text-white/90 hover:bg-emerald-500/85 active:scale-95 transition-all"
                aria-label="在衣橱中找相似单品"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                找相似
              </button>
            )}
            {/* 已反馈标记 */}
            {feedback && (
              <div className="absolute bottom-2 right-2 z-10">
                <span className={`text-sm ${feedback === 'like' ? '' : 'grayscale'}`}>
                  {feedback === 'like' ? '❤️' : '👎'}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div
            className={`h-40 sm:h-44 bg-gradient-to-br ${config.gradientClass} flex items-center justify-center relative cursor-pointer`}
            onClick={handleImageTap}
          >
            <span className="text-4xl opacity-60">{config.emoji}</span>
            <div className={`absolute top-2 left-2 px-2 py-0.5 rounded-full text-[10px] font-medium ${
              item.is_anchor ? 'bg-amber-500/90 text-white' : isFromWardrobe ? 'bg-emerald-500/80 text-white' : 'bg-blue-500/80 text-white'
            }`}>
              {item.is_anchor ? '🎯 指定' : isFromWardrobe ? '🏠 自有' : '📚 公共库'}
            </div>
            {/* 找相似（无图占位区同样提供入口） */}
            {canFindSimilar && (
              <button
                onClick={(e) => { e.stopPropagation(); setShowSimilarSheet(true) }}
                className="absolute bottom-2 left-2 flex items-center gap-1 px-2 py-1 rounded-full bg-black/35 backdrop-blur-sm text-[10px] font-medium text-white/90 hover:bg-emerald-500/85 active:scale-95 transition-all"
                aria-label="在衣橱中找相似单品"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                找相似
              </button>
            )}
            {feedback && (
              <div className="absolute bottom-2 right-2">
                <span className="text-sm">{feedback === 'like' ? '❤️' : '👎'}</span>
              </div>
            )}
          </div>
        )}

        {/* ===== 反馈覆盖层 ===== */}
        <AnimatePresence>
          {showOverlay && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 z-20 bg-black/50 backdrop-blur-[2px] flex flex-col items-center justify-center"
              onClick={() => { setShowOverlay(false); setShowReasons(false) }}
            >
              {/* 已反馈状态：显示撤销选项 */}
              {feedback && !feedbackAnimation ? (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 22 }}
                  className="flex flex-col items-center gap-3"
                  onClick={(e) => e.stopPropagation()}
                >
                  <span className="text-2xl">{feedback === 'like' ? '❤️' : '👎'}</span>
                  <p className="text-xs text-white/80">
                    {feedback === 'like' ? '已喜欢' : '已标记不喜欢'}
                  </p>
                  <button
                    onClick={handleUndoFeedback}
                    disabled={isSubmitting}
                    className="px-4 py-1.5 rounded-full text-[11px] font-medium text-white/90 bg-white/20 hover:bg-white/30 active:scale-95 transition-all border border-white/30"
                  >
                    撤销
                  </button>
                </motion.div>
              ) : !showReasons ? (
                /* 未反馈：点赞/点踩 图标按钮 */
                <motion.div
                  initial={{ scale: 0.85, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 22 }}
                  className="flex items-center gap-5"
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* 小爱心 - 点赞（空心→实心动画） */}
                  <button
                    onClick={handleLike}
                    disabled={isSubmitting}
                    className="flex flex-col items-center gap-1 group"
                    aria-label="喜欢这个推荐"
                  >
                    <div className="w-11 h-11 rounded-full bg-white/90 shadow-md flex items-center justify-center group-hover:scale-105 group-active:scale-90 transition-transform">
                      <motion.svg
                        className="w-5 h-5 text-rose-400"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                        initial={false}
                        animate={isSubmitting ? { scale: [1, 1.3, 1] } : {}}
                        transition={{ duration: 0.3 }}
                      >
                        <motion.path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                          initial={{ fill: 'rgba(255,255,255,0)' }}
                          animate={isSubmitting ? { fill: 'rgba(244,63,94,1)' } : { fill: 'rgba(255,255,255,0)' }}
                          transition={{ duration: 0.4, ease: 'easeInOut' }}
                        />
                      </motion.svg>
                    </div>
                    <span className="text-[11px] text-white/85 font-medium">喜欢</span>
                  </button>

                  {/* 点踩 */}
                  <button
                    onClick={handleDislikeTap}
                    disabled={isSubmitting}
                    className="flex flex-col items-center gap-1 group"
                    aria-label="不喜欢这个推荐"
                  >
                    <div className="w-11 h-11 rounded-full bg-white/90 shadow-md flex items-center justify-center group-hover:scale-105 group-active:scale-90 transition-transform">
                      <svg className="w-5 h-5 text-stone-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                      </svg>
                    </div>
                    <span className="text-[11px] text-white/85 font-medium">不喜欢</span>
                  </button>
                </motion.div>
              ) : (
                /* 点踩原因多选器 */
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 24 }}
                  className="flex flex-col items-center gap-1.5 px-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  <p className="text-xs text-white/85 font-medium mb-0.5">不喜欢的原因？（可多选）</p>
                  <div className="flex flex-wrap justify-center gap-1.5 max-w-[220px]">
                    {DISLIKE_REASONS.map((r) => {
                      const isSelected = selectedReasons.includes(r.value)
                      return (
                        <button
                          key={r.value}
                          onClick={() => toggleReason(r.value)}
                          className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-all active:scale-95 ring-1 ${
                            isSelected
                              ? `${r.color} text-white shadow-md ${r.ring} scale-105`
                              : 'bg-white/15 text-white/70 ring-white/20 hover:bg-white/25'
                          }`}
                        >
                          {isSelected ? '✓ ' : ''}{r.label}
                        </button>
                      )
                    })}
                  </div>
                  <div className="flex items-center gap-3 mt-2">
                    <button
                      onClick={() => setShowReasons(false)}
                      className="text-[11px] text-white/50 hover:text-white/80 transition-colors"
                    >
                      返回
                    </button>
                    <button
                      onClick={handleDislikeConfirm}
                      disabled={selectedReasons.length === 0 || isSubmitting}
                      className={`px-3.5 py-1 rounded-full text-[11px] font-medium transition-all ${
                        selectedReasons.length > 0 && !isSubmitting
                          ? 'bg-white/90 text-stone-700 shadow-sm hover:bg-white active:scale-95'
                          : 'bg-white/10 text-white/30 cursor-not-allowed'
                      }`}
                    >
                      {isSubmitting ? '提交中…' : `确认${selectedReasons.length > 0 ? `(${selectedReasons.length})` : ''}`}
                    </button>
                  </div>
                  {submitError && (
                    <p className="text-[10px] text-red-300 mt-1.5">{submitError}</p>
                  )}
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* 反馈成功动画 */}
        <AnimatePresence>
          {feedbackAnimation && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none"
            >
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: [0, 1.2, 1], opacity: 1 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
                className="text-4xl"
              >
                {feedbackAnimation === 'like' ? '❤️' : '👋'}
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ===== 文字信息区域 ===== */}
      <div className="p-3 sm:p-3.5">
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
          <p className="text-xs text-stone-500 mt-0.5">颜色：{item.color}</p>
        )}

        {/* 综合匹配度 + 展开详情 */}
        <div className="mt-2.5 pt-2.5 border-t border-stone-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-stone-400 text-xs">综合匹配</span>
              <span className="font-bold text-[var(--wuxing-earth)] text-base">
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

          {/* 详细评分（可折叠） */}
          <AnimatePresence>
            {showDetails && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-2.5 space-y-2 overflow-hidden"
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

                {/* 场景适配 */}
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

                {/* 偏好匹配 */}
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
          </AnimatePresence>
        </div>

        {/* 推荐理由（五行契合/场景适配/气温适配，后端生成，用户反馈 #6） */}
        {item.reason && showReason && (
          <div className="mt-2 px-2.5 py-1.5 rounded-lg bg-amber-50/80 border border-amber-100">
            <p className="text-[11px] leading-relaxed text-amber-700 line-clamp-2">
              <span className="mr-1" aria-hidden="true">💡</span>
              {item.reason}
            </p>
          </div>
        )}
      </div>

      {/* 物品详情弹窗 */}
      {showDetailModal && (
        <ItemDetailModal
          item={item}
          onClose={() => setShowDetailModal(false)}
        />
      )}

      {/* 衣橱相似款面板（底部滑出） */}
      {canFindSimilar && (
        <WardrobeSimilarSheet
          open={showSimilarSheet}
          sourceItemCode={item.item_code}
          sourceItemName={item.name}
          sourceItemCategory={item.category}
          onClose={() => setShowSimilarSheet(false)}
          onSelect={handleReplaceSimilar}
          onNavigateToWardrobe={onNavigateToWardrobe}
        />
      )}
    </motion.div>
  )
}
