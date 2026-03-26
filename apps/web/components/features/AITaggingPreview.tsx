'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useWardrobeStore } from '@/store/wardrobe'
import { AITaggingResult } from '@/lib/api'

// 五行颜色映射
const ELEMENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  '金': { bg: 'bg-gradient-to-br from-amber-100 to-yellow-200', text: 'text-amber-800', border: 'border-amber-300' },
  '木': { bg: 'bg-gradient-to-br from-emerald-100 to-green-200', text: 'text-emerald-800', border: 'border-emerald-300' },
  '水': { bg: 'bg-gradient-to-br from-blue-100 to-cyan-200', text: 'text-blue-800', border: 'border-blue-300' },
  '火': { bg: 'bg-gradient-to-br from-rose-100 to-red-200', text: 'text-rose-800', border: 'border-rose-300' },
  '土': { bg: 'bg-gradient-to-br from-orange-100 to-amber-200', text: 'text-orange-800', border: 'border-orange-300' },
}

const ELEMENT_EMOJI: Record<string, string> = {
  '金': '✨', '木': '🌿', '水': '💧', '火': '🔥', '土': '🌻',
}

interface AITaggingPreviewProps {
  description: string
  onTaggingComplete?: (result: AITaggingResult) => void
}

export function AITaggingPreview({ description, onTaggingComplete }: AITaggingPreviewProps) {
  const { taggingPreview, isTaggingLoading, fetchTaggingPreview, clearTaggingPreview } = useWardrobeStore()

  // 防抖函数
  const debouncedFetch = useCallback(
    debounce((text: string) => {
      if (text.length >= 2) {
        fetchTaggingPreview(text)
      } else {
        clearTaggingPreview()
      }
    }, 500),
    []
  )

  useEffect(() => {
    debouncedFetch(description)
    return () => {
      debouncedFetch.cancel()
    }
  }, [description])

  useEffect(() => {
    if (taggingPreview && onTaggingComplete) {
      onTaggingComplete(taggingPreview)
    }
  }, [taggingPreview])

  if (!description || description.length < 2) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 p-4 rounded-xl bg-stone-50 border border-stone-200"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">✨</span>
        <span className="text-sm font-medium text-stone-600">AI 检测结果</span>
        {isTaggingLoading && (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="w-4 h-4 border-2 border-stone-300 border-t-stone-600 rounded-full"
          />
        )}
      </div>

      <AnimatePresence mode="wait">
        {taggingPreview && !isTaggingLoading ? (
          <motion.div
            key="result"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-3"
          >
            {/* 主五行和颜色 */}
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-stone-500">主五行</span>
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    ELEMENT_COLORS[taggingPreview.primary_element]?.bg || 'bg-stone-100'
                  } ${ELEMENT_COLORS[taggingPreview.primary_element]?.text || 'text-stone-700'}`}
                >
                  {ELEMENT_EMOJI[taggingPreview.primary_element] || '🔮'} {taggingPreview.primary_element}
                </motion.span>
              </div>

              {taggingPreview.color && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-500">颜色</span>
                  <span className="px-3 py-1 rounded-full text-sm bg-white border border-stone-200 text-stone-700">
                    {taggingPreview.color}
                  </span>
                </div>
              )}
            </div>

            {/* 材质和风格 */}
            <div className="flex flex-wrap gap-3">
              {taggingPreview.material && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-500">材质</span>
                  <span className="text-sm text-stone-700">{taggingPreview.material}</span>
                </div>
              )}
              {taggingPreview.style && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-500">风格</span>
                  <span className="text-sm text-stone-700">{taggingPreview.style}</span>
                </div>
              )}
            </div>

            {/* 适用季节 */}
            {taggingPreview.season && taggingPreview.season.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-stone-500">适用季节</span>
                <div className="flex gap-1">
                  {taggingPreview.season.map((s, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-xs bg-white border border-stone-200 text-stone-600">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 标签 */}
            {taggingPreview.tags && taggingPreview.tags.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-stone-500">标签</span>
                <div className="flex flex-wrap gap-1">
                  {taggingPreview.tags.map((tag, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-xs bg-stone-100 text-stone-600">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 置信度指示器 */}
            {taggingPreview.confidence !== undefined && (
              <div className="flex items-center gap-2 mt-2 pt-2 border-t border-stone-100">
                <span className="text-xs text-stone-400">AI 置信度</span>
                <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${taggingPreview.confidence * 100}%` }}
                    className="h-full bg-gradient-to-r from-amber-400 to-amber-500 rounded-full"
                  />
                </div>
                <span className="text-xs font-medium text-amber-600">
                  {(taggingPreview.confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </motion.div>
        ) : isTaggingLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="flex gap-2">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                  className="w-2 h-2 rounded-full bg-amber-400"
                />
              ))}
            </div>
          </div>
        ) : null}
      </AnimatePresence>
    </motion.div>
  )
}

// 简单的防抖 Hook
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) & { cancel: () => void } {
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  const debounced = (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      func(...args)
    }, wait)
  }

  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
  }

  return debounced
}
