'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { RecommendItem } from '@/types'
import { submitFeedback } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'

interface RecommendCardProps {
  item: RecommendItem
  index: number
  sessionId?: string
  onFeedback?: (action: 'like' | 'dislike') => void
}

export function RecommendCard({ item, index, sessionId, onFeedback }: RecommendCardProps) {
  const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [imageError, setImageError] = useState(false)
  const config = getWuxingConfig(item.primary_element)

  // 构建完整的图片 URL，并对特殊字符（空格等）进行编码
  const getImageUrl = (url: string | undefined) => {
    if (!url) return null
    
    // 如果已经是完整 URL（http/https），直接返回
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }
    
    // 公共库图片（/images/seed/...）直接使用相对路径，前端会自动处理
    if (url.startsWith('/images/')) {
      return url
    }
    
    // 用户上传的图片（/uploads/...）需要拼接后端 baseURL
    if (url.startsWith('/uploads/')) {
      const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      // 使用 encodeURI 编码整个 URL，处理空格等特殊字符
      const encodedPath = encodeURI(url)
      return `${baseURL}${encodedPath}`
    }
    
    // 其他情况，尝试拼接 baseURL
    const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${baseURL}${url}`
  }

  const fullImageUrl = getImageUrl(item.image_url)
  const shouldShowImage = fullImageUrl && !imageError

  const handleFeedback = async (action: 'like' | 'dislike') => {
    if (feedback || isSubmitting) return

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

  const isFromWardrobe = item.source === 'wardrobe'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className="bg-card rounded-lg border overflow-hidden hover:shadow-lg transition-shadow"
    >
      {/* 元素渐变占位图 */}
      {shouldShowImage ? (
        <div
          className="h-32"
          style={{ backgroundImage: `url(${fullImageUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
        />
      ) : (
        <div
          className={`h-32 bg-gradient-to-br ${config.gradientClass} flex items-center justify-center relative`}
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
          <h4 className="font-medium text-sm line-clamp-2 text-stone-700">{item.name}</h4>
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
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-stone-500">匹配度</span>
            <span className="font-medium text-amber-600">
              {(item.final_score * 100).toFixed(0)}%
            </span>
          </div>
          
          {/* 反馈按钮 */}
          <div className="flex gap-1">
            <button
              onClick={() => handleFeedback('like')}
              disabled={!!feedback || isSubmitting}
              className={`p-1.5 rounded-full transition-all ${
                feedback === 'like'
                  ? 'bg-emerald-100 text-emerald-600'
                  : 'hover:bg-stone-100 text-[#6B7F72] hover:text-emerald-500'
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
                  : 'hover:bg-stone-100 text-[#6B7F72] hover:text-red-500'
              } disabled:cursor-not-allowed`}
            >
              <svg className="w-4 h-4" fill={feedback === 'dislike' ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
              </svg>
            </button>
          </div>
        </div>
        {item.reason && (
          <p className="text-xs text-stone-500 mt-2 line-clamp-2">{item.reason}</p>
        )}
      </div>
    </motion.div>
  )
}
