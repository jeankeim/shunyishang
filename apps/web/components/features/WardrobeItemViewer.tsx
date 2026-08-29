'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createPortal } from 'react-dom'
import type { WardrobeItem } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'
import { IDLE_BADGE_MIN_DAYS, idleBadgeClass } from '@/lib/wardrobe-display'

interface WardrobeItemViewerProps {
  item: WardrobeItem | null
  onClose: () => void
  onEdit?: (item: WardrobeItem) => void
  onDelete?: (itemId: number) => void
  /** 删除请求进行中（用于按钮态与二次确认由调用方决定） */
  deleting?: boolean
}

/** 把 items 里的属性拼成展示用的标签组（缺项自动跳过） */
function buildTags(item: WardrobeItem): string[] {
  return [
    item.color,
    item.style,
    item.material,
    item.thickness_level,
    item.gender && item.gender !== '中性' ? item.gender : null,
    ...(item.applicable_seasons ?? []),
  ].filter((t): t is string => Boolean(t))
}

/**
 * 衣物放大查看层
 *
 * 柜体抽屉与网格视图里缩略图都很小，点开后用大片区域看清整件衣物：
 * 图片默认 contain（保证整件可见），点按图片切成 cover（铺满看清质感/纹样）。
 * 移动端底部抽屉式、桌面居中卡片，动画只走 transform/opacity。
 */
export function WardrobeItemViewer({ item, onClose, onEdit, onDelete, deleting }: WardrobeItemViewerProps) {
  const [fitCover, setFitCover] = useState(false)
  // createPortal 依赖 document，跳过服务端渲染首帧；组件本身常驻挂载以保留退场动画
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (!item) return
    setFitCover(false)
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handleKey)
      document.body.style.overflow = prevOverflow
    }
  }, [item, onClose])

  const config = item ? getWuxingConfig(item.primary_element) : null
  const imageUrl = item?.image_url ? getImageUrl(item.image_url) : null
  const idleDays = item?.idle_days

  if (!mounted) return null

  return createPortal(
    <AnimatePresence>
      {item && config && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[9999] flex items-end justify-center bg-black/70 backdrop-blur-sm md:items-center md:p-6"
          onClick={onClose}
          role="dialog"
          aria-modal="true"
          aria-label={`放大查看：${item.name}`}
        >
          <motion.div
            initial={{ y: 40, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 24, opacity: 0, scale: 0.98 }}
            transition={{ type: 'spring', damping: 30, stiffness: 320 }}
            className="relative flex max-h-[86dvh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl bg-white shadow-2xl md:max-h-[88dvh] md:rounded-3xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 大图区：点按切换 适配 / 充满 */}
            <button
              type="button"
              onClick={() => setFitCover((v) => !v)}
              aria-label={fitCover ? '切换为完整显示' : '切换为充满显示'}
              className="relative block w-full shrink-0 overflow-hidden"
              style={{
                height: '46dvh',
                background: `linear-gradient(135deg, ${config.gradientFrom}22, ${config.gradientTo}12)`,
              }}
            >
              {imageUrl ? (
                <motion.img
                  key={imageUrl}
                  initial={{ opacity: 0, scale: 1.02 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.28, ease: 'easeOut' }}
                  src={imageUrl}
                  alt={item.name}
                  className="w-full"
                  style={{ height: '100%', objectFit: fitCover ? 'cover' : 'contain' }}
                />
              ) : (
                <span
                  className="font-serif text-[120px] leading-none opacity-70"
                  style={{ color: config.gradientFrom }}
                >
                  {config.element}
                </span>
              )}

              {/* 闲置徽标 */}
              {idleDays != null && idleDays >= IDLE_BADGE_MIN_DAYS && (
                <span
                  className={`absolute left-3 top-3 rounded-lg px-2 py-1 text-[10px] font-medium text-white shadow-sm backdrop-blur-md ${idleBadgeClass(idleDays)}`}
                >
                  {item.wear_count === 0 ? `未穿 ${idleDays} 天` : `已闲置 ${idleDays} 天`}
                </span>
              )}

              <span className="absolute bottom-2.5 right-3 rounded-full bg-white/70 px-2 py-0.5 text-[10px] text-stone-500 backdrop-blur-sm">
                {imageUrl ? `点按图片：${fitCover ? '充满' : '完整'} → ${fitCover ? '完整' : '充满'}` : '暂无实拍图'}
              </span>
            </button>

            {/* 关闭 */}
            <button
              onClick={onClose}
              aria-label="关闭放大查看"
              className="absolute right-3 top-3 flex h-11 w-11 items-center justify-center rounded-full bg-white/85 text-stone-500 shadow-md backdrop-blur-md transition-colors hover:bg-white hover:text-stone-800"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* 信息区：可纵向滚动，不撑破视口 */}
            <div className="min-h-0 overflow-y-auto overscroll-contain px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2
                    className="truncate text-lg font-bold text-[var(--brand-heading)]"
                    style={{ fontFamily: 'serif' }}
                    title={item.name}
                  >
                    {item.name}
                  </h2>
                  <p className="mt-0.5 text-xs text-[var(--brand-subtle)]">
                    {item.category || '未分类'}
                    {item.secondary_element ? ` · 次五行 ${item.secondary_element}` : ''}
                  </p>
                </div>
                <span
                  className="inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-1 text-xs font-bold text-white shadow-sm"
                  style={{ background: `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})` }}
                >
                  {config.element}
                  <span className="font-normal opacity-80">{config.emoji}</span>
                </span>
              </div>

              {buildTags(item).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {buildTags(item).map((tag, i) => (
                    <span
                      key={`${tag}-${i}`}
                      className="rounded-full bg-[var(--brand-bg)] px-2.5 py-1 text-[11px] text-[var(--brand-subtle)]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-3 flex items-center gap-4 text-[11px] text-[var(--brand-subtle)]">
                <span>
                  穿着 <span className="font-semibold text-[var(--brand-heading)]">{item.wear_count}</span> 次
                </span>
                {item.last_worn_date && <span>最近穿着 {item.last_worn_date.slice(0, 10)}</span>}
                {item.is_favorite && <span className="text-rose-500">♥ 已收藏</span>}
              </div>

              {item.notes && (
                <p className="mt-3 rounded-xl bg-stone-50 px-3 py-2 text-xs leading-relaxed text-stone-600">
                  {item.notes}
                </p>
              )}

              {/* 操作：把柜体/网格里靠 hover 才可见的入口收进放大层 */}
              {(onEdit || onDelete) && (
                <div className="mt-4 flex gap-2 border-t border-stone-100 pt-3">
                  {onEdit && (
                    <button
                      type="button"
                      onClick={() => onEdit(item)}
                      className="min-h-[44px] flex-1 rounded-xl bg-[var(--brand-bg)] text-sm font-medium text-[var(--brand-heading)] transition-colors hover:bg-[var(--brand-surface)] active:scale-[0.99]"
                    >
                      编辑衣物
                    </button>
                  )}
                  {onDelete && (
                    <button
                      type="button"
                      disabled={deleting}
                      onClick={() => onDelete(item.id)}
                      className="min-h-[44px] flex-1 rounded-xl border border-rose-200 text-sm font-medium text-rose-600 transition-colors hover:bg-rose-50 disabled:opacity-50"
                    >
                      {deleting ? '删除中…' : '删除衣物'}
                    </button>
                  )}
                </div>
              )}
            </div>
            <div className="h-2 md:hidden" />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
