'use client'

/**
 * 衣橱相似款内联面板
 *
 * 灵感库推荐卡片点「找相似」后，在卡片就地展开（卡片已横跨整行 col-span-2）：
 * 向量检索用户衣橱中同品类的相似单品，一键「替换」到推荐结果中。
 * 与旧的底部滑出面板不同——这里无遮罩、页面不变暗，列表清晰可读。
 * 空态引导用户去衣橱添加。
 */

import { useState, useEffect, useCallback } from 'react'
import { WardrobeSimilarItem, getWardrobeSimilar } from '@/lib/api'
import { getImageUrl } from '@/lib/image'
import { getWuxingConfig } from '@/lib/wuxing-config'

interface WardrobeSimilarInlineProps {
  /** 源灵感库单品的 item_code（用于向量检索） */
  sourceItemCode: string
  sourceItemName: string
  sourceItemCategory: string
  /** 用户点击「替换」：把选中的衣橱相似品替换到推荐网格槽位 */
  onSelect: (similar: WardrobeSimilarItem) => void
  /** 空态「去衣橱添加」导流 */
  onNavigateToWardrobe?: () => void
  /** 收起内联面板 */
  onCollapse: () => void
}

export function WardrobeSimilarInline({
  sourceItemCode,
  sourceItemName,
  sourceItemCategory,
  onSelect,
  onNavigateToWardrobe,
  onCollapse,
}: WardrobeSimilarInlineProps) {
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

  // 挂载即查询（每次展开都是新挂载，天然拿到最新衣橱数据）
  useEffect(() => {
    fetchSimilar()
  }, [fetchSimilar])

  return (
    <div className="border-t border-stone-100 bg-stone-50/70 px-3 py-3 sm:px-3.5">
      {/* 标题行 */}
      <div className="mb-2.5 flex items-center justify-between gap-2">
        <h4 className="flex min-w-0 items-center gap-1.5 text-xs font-semibold text-stone-700">
          <span aria-hidden="true">🧺</span>
          <span className="shrink-0">衣橱里的相似款</span>
          <span className="truncate font-normal text-[11px] text-stone-400">
            与「{sourceItemName}」同品类{sourceItemCategory ? `（${sourceItemCategory}）` : ''}
          </span>
        </h4>
        <button
          onClick={onCollapse}
          className="shrink-0 rounded-full px-2 py-0.5 text-[11px] text-stone-400 hover:bg-stone-200 hover:text-stone-600 transition-colors"
          aria-label="收起相似款列表"
        >
          收起
        </button>
      </div>

      {/* 加载中：骨架屏 */}
      {loading && (
        <div className="flex gap-3 overflow-hidden">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-32 shrink-0 animate-pulse">
              <div className="h-28 w-full rounded-xl bg-stone-200" />
              <div className="mt-2 h-3 w-3/4 rounded bg-stone-200" />
              <div className="mt-1.5 h-6 w-full rounded-lg bg-stone-200" />
            </div>
          ))}
        </div>
      )}

      {/* 查询失败 */}
      {!loading && error && (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-white px-3 py-3">
          <p className="text-xs text-stone-400">{error}</p>
          <button
            onClick={fetchSimilar}
            className="shrink-0 rounded-lg bg-stone-100 px-3 py-1.5 text-xs text-stone-600 hover:bg-stone-200 transition-colors"
          >
            重试
          </button>
        </div>
      )}

      {/* 空态：衣橱里还没有相似单品 → 引导去衣橱添加 */}
      {!loading && !error && items.length === 0 && (
        <div className="flex flex-col items-center rounded-xl bg-white px-4 py-5 text-center">
          <span className="text-2xl" aria-hidden="true">👗</span>
          <p className="mt-1.5 text-sm text-stone-500">衣橱里还没有类似单品</p>
          <p className="mt-0.5 text-[11px] text-stone-400">添加更多衣物后，替换会更精准</p>
          {onNavigateToWardrobe && (
            <button
              onClick={() => {
                onCollapse()
                onNavigateToWardrobe()
              }}
              className="mt-3 rounded-xl bg-emerald-500 px-5 py-2 text-xs font-medium text-white hover:bg-emerald-600 transition-colors shadow-sm"
            >
              去衣橱添加
            </button>
          )}
        </div>
      )}

      {/* 相似款列表：横向可滑动，缩略图清晰、替换按钮醒目 */}
      {!loading && !error && items.length > 0 && (
        <div className="-mx-1 flex gap-3 overflow-x-auto px-1 pb-1">
          {items.map((similar) => {
            const imageUrl = getImageUrl(similar.image_url)
            const config = getWuxingConfig(similar.primary_element || undefined)
            const pct = Math.round(similar.similarity * 100)
            return (
              <div
                key={similar.id}
                className="flex w-32 shrink-0 flex-col overflow-hidden rounded-xl border border-stone-100 bg-white"
              >
                {/* 缩略图 */}
                <div className="relative h-28 w-full bg-stone-50">
                  {imageUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={imageUrl}
                      alt={similar.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div
                      className={`flex h-full w-full items-center justify-center bg-gradient-to-br ${config.gradientClass}`}
                    >
                      <span className="text-2xl opacity-60">{config.emoji}</span>
                    </div>
                  )}
                  <span className="absolute left-1.5 top-1.5 rounded-full bg-emerald-500/90 px-1.5 py-0.5 text-[10px] font-medium text-white">
                    相似 {pct}%
                  </span>
                </div>
                {/* 信息 */}
                <div className="flex flex-1 flex-col px-2 pt-1.5">
                  <p className="line-clamp-2 text-xs font-medium text-stone-800">{similar.name}</p>
                  <p className="mt-0.5 truncate text-[10px] text-stone-400">
                    {similar.category}
                    {similar.primary_element ? ` · 属${similar.primary_element}` : ''}
                  </p>
                </div>
                {/* 替换按钮 */}
                <button
                  onClick={() => onSelect(similar)}
                  className="m-2 mt-1.5 rounded-lg bg-emerald-500 py-1.5 text-xs font-medium text-white hover:bg-emerald-600 active:scale-95 transition-all"
                >
                  替换
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
