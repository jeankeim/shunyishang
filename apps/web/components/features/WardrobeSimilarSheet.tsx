'use client'

/**
 * 衣橱相似款面板（底部滑出）
 *
 * 灵感库推荐卡片点「找相似」后弹出：向量检索用户衣橱中同品类的相似单品，
 * 支持一键「替换」到推荐结果中（对标淘宝"找相似"心智）。
 * 空态引导用户去衣橱添加。
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { WardrobeSimilarItem, getWardrobeSimilar } from '@/lib/api'
import { getImageUrl } from '@/lib/image'
import { getWuxingConfig } from '@/lib/wuxing-config'

interface WardrobeSimilarSheetProps {
  open: boolean
  /** 源灵感库单品的 item_code（用于向量检索） */
  sourceItemCode: string
  sourceItemName: string
  sourceItemCategory: string
  onClose: () => void
  /** 用户点击「替换」：把选中的衣橱相似品替换到推荐网格槽位 */
  onSelect: (similar: WardrobeSimilarItem) => void
  /** 空态「去衣橱添加」导流 */
  onNavigateToWardrobe?: () => void
}

export function WardrobeSimilarSheet({
  open,
  sourceItemCode,
  sourceItemName,
  sourceItemCategory,
  onClose,
  onSelect,
  onNavigateToWardrobe,
}: WardrobeSimilarSheetProps) {
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<WardrobeSimilarItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const fetchSimilar = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getWardrobeSimilar(sourceItemCode)
      setItems(res.items || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : '查询失败，请重试')
    } finally {
      setLoading(false)
    }
  }, [sourceItemCode])

  // 每次打开都重新查询（衣橱可能刚添加了新单品）
  useEffect(() => {
    if (open) fetchSimilar()
  }, [open, fetchSimilar])

  // 打开时锁定背景滚动（与弹层惯例一致）
  useEffect(() => {
    if (!open) return
    const original = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = original
    }
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* 遮罩 */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]"
            onClick={onClose}
          />
          {/* 底部面板 */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="fixed inset-x-0 bottom-0 z-50 max-h-[75vh] overflow-y-auto rounded-t-2xl bg-card shadow-2xl"
          >
            {/* 拖拽指示条 */}
            <div className="sticky top-0 z-10 bg-card pt-3 pb-1">
              <div className="mx-auto h-1 w-10 rounded-full bg-stone-200" />
            </div>

            <div className="px-4 pb-6">
              {/* 标题行 */}
              <div className="flex items-center justify-between gap-2 py-2">
                <h3 className="text-sm font-semibold text-stone-800 min-w-0">
                  🧺 衣橱里的相似款
                  <span className="ml-1.5 font-normal text-[11px] text-stone-400 truncate">
                    与「{sourceItemName}」同品类{sourceItemCategory ? `（${sourceItemCategory}）` : ''}
                  </span>
                </h3>
                <button
                  onClick={onClose}
                  className="shrink-0 w-7 h-7 rounded-full bg-stone-100 flex items-center justify-center text-stone-400 hover:text-stone-600 hover:bg-stone-200 transition-colors"
                  aria-label="关闭"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* 加载中：骨架屏 */}
              {loading && (
                <div className="space-y-3 py-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="flex items-center gap-3 animate-pulse">
                      <div className="w-16 h-16 rounded-xl bg-stone-100" />
                      <div className="flex-1 space-y-2">
                        <div className="h-3.5 bg-stone-100 rounded w-2/3" />
                        <div className="h-3 bg-stone-100 rounded w-1/3" />
                      </div>
                      <div className="w-14 h-8 rounded-lg bg-stone-100" />
                    </div>
                  ))}
                </div>
              )}

              {/* 查询失败 */}
              {!loading && error && (
                <div className="py-6 text-center">
                  <p className="text-xs text-stone-400 mb-3">{error}</p>
                  <button
                    onClick={fetchSimilar}
                    className="px-4 py-1.5 rounded-lg bg-stone-100 text-xs text-stone-600 hover:bg-stone-200 transition-colors"
                  >
                    重试
                  </button>
                </div>
              )}

              {/* 空态：衣橱里还没有相似单品 → 引导去衣橱添加 */}
              {!loading && !error && items.length === 0 && (
                <div className="py-8 text-center">
                  <span className="text-3xl" aria-hidden="true">👗</span>
                  <p className="mt-2 text-sm text-stone-500">衣橱里还没有类似单品</p>
                  <p className="mt-0.5 text-[11px] text-stone-400">添加更多衣物后，替换会更精准</p>
                  {onNavigateToWardrobe && (
                    <button
                      onClick={() => {
                        onClose()
                        onNavigateToWardrobe()
                      }}
                      className="mt-4 px-5 py-2 rounded-xl bg-emerald-500 text-white text-xs font-medium hover:bg-emerald-600 transition-colors shadow-sm"
                    >
                      去衣橱添加
                    </button>
                  )}
                </div>
              )}

              {/* 相似品列表 */}
              {!loading && !error && items.length > 0 && (
                <ul className="space-y-3 pt-1">
                  {items.map((similar) => {
                    const imageUrl = getImageUrl(similar.image_url)
                    const config = getWuxingConfig(similar.primary_element || undefined)
                    const pct = Math.round(similar.similarity * 100)
                    return (
                      <li
                        key={similar.id}
                        className="flex items-center gap-3 rounded-xl border border-stone-100 p-2.5 hover:border-emerald-200 transition-colors"
                      >
                        {/* 缩略图 */}
                        {imageUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={imageUrl}
                            alt={similar.name}
                            className="w-16 h-16 rounded-xl object-cover shrink-0 bg-stone-50"
                          />
                        ) : (
                          <div
                            className={`w-16 h-16 rounded-xl shrink-0 bg-gradient-to-br ${config.gradientClass} flex items-center justify-center`}
                          >
                            <span className="text-xl opacity-60">{config.emoji}</span>
                          </div>
                        )}
                        {/* 信息 */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-stone-800 font-medium truncate">{similar.name}</p>
                          <div className="mt-1 flex items-center gap-1.5">
                            <span className="px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-medium">
                              相似 {pct}%
                            </span>
                            <span className="text-[11px] text-stone-400">{similar.category}</span>
                            {similar.primary_element && (
                              <span className="text-[11px] text-stone-400">· 属{similar.primary_element}</span>
                            )}
                          </div>
                        </div>
                        {/* 替换按钮 */}
                        <button
                          onClick={() => onSelect(similar)}
                          className="shrink-0 px-4 py-2 rounded-xl bg-stone-800 text-white text-xs font-medium hover:bg-stone-700 active:scale-95 transition-all"
                        >
                          替换
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
