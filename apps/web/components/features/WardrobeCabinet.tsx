'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import type { WardrobeItem } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'
import { useReducedMotion } from '@/hooks/useReducedMotion'
import { CATEGORY_ICON, IDLE_BADGE_MIN_DAYS, groupWardrobeByCategory, idleBadgeClass } from '@/lib/wardrobe-display'

interface WardrobeCabinetProps {
  /** 已经过服务端筛选的衣物列表 */
  items: WardrobeItem[]
  /** 是否处于筛选态（决定抽屉徽标显示「命中 / 全量」还是单一件数） */
  filtered?: boolean
  /** 各品类全量可用件数（来自 /wardrobe/filter-stats 的 category facet） */
  categoryAvail?: Record<string, number>
  /** 点击某件衣物 → 放大查看 */
  onSelect: (item: WardrobeItem) => void
}

/** 抽屉内单件衣物：图 + 名称 + 五行点，点击放大 */
function DrawerItem({ item, index, onSelect }: { item: WardrobeItem; index: number; onSelect: (item: WardrobeItem) => void }) {
  const reduced = useReducedMotion()
  const config = getWuxingConfig(item.primary_element)
  const imageUrl = item.image_url ? getImageUrl(item.image_url) : null
  const idleDays = item.idle_days

  return (
    <motion.button
      type="button"
      onClick={() => onSelect(item)}
      initial={reduced ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: reduced ? 0 : Math.min(index * 0.025, 0.3), duration: 0.24, ease: 'easeOut' }}
      whileTap={{ scale: 0.95 }}
      aria-label={`放大查看 ${item.name}`}
      className="group relative w-[calc(25%-9px)] overflow-hidden rounded-lg border border-stone-200/70 bg-white shadow-sm transition-shadow hover:shadow-md sm:w-[calc(16.666%-10px)]"
    >
      <div className="relative aspect-[3/4] w-full overflow-hidden">
        {imageUrl ? (
          <img src={imageUrl} alt={item.name} loading="lazy" className="h-full w-full object-cover" />
        ) : (
          <div
            className="flex h-full w-full items-center justify-center"
            style={{ background: `linear-gradient(135deg, ${config.gradientFrom}30, ${config.gradientTo}18)` }}
          >
            <span className="font-serif text-xl opacity-70" style={{ color: config.gradientFrom }}>
              {config.element}
            </span>
          </div>
        )}
        {/* 闲置提醒（与网格视图同一阈值与色阶） */}
        {idleDays != null && idleDays >= IDLE_BADGE_MIN_DAYS && (
          <span
            className={`absolute right-0.5 top-0.5 rounded px-1 py-px text-[8px] font-medium leading-tight text-white backdrop-blur-sm ${idleBadgeClass(idleDays)}`}
          >
            {idleDays}d
          </span>
        )}
        <span
          className="absolute bottom-0.5 left-0.5 h-1.5 w-1.5 rounded-full ring-1 ring-white/70"
          style={{ background: config.gradientFrom }}
        />
      </div>
      <p className="truncate px-1 py-1 text-[10px] leading-tight text-stone-600" title={item.name}>
        {item.name}
      </p>
    </motion.button>
  )
}

/** 一格抽屉：把手 + 品类刻印 + 件数徽标，点击拉出摊开 */
function DrawerRow({
  category,
  items,
  avail,
  filtered,
  open,
  onToggle,
  onSelect,
  registerRef,
}: {
  category: string
  items: WardrobeItem[]
  avail?: number
  filtered: boolean
  open: boolean
  onToggle: () => void
  onSelect: (item: WardrobeItem) => void
  registerRef: (el: HTMLDivElement | null) => void
}) {
  const reduced = useReducedMotion()
  const panelRef = useRef<HTMLDivElement>(null)
  const [scrollable, setScrollable] = useState(false)

  // 是否需要「抽屉内可滑动」提示：按实际溢出判定，固定件数阈值在小屏/大屏都会判错
  useEffect(() => {
    if (!open) return
    const timer = window.setTimeout(() => {
      const el = panelRef.current
      if (el) setScrollable(el.scrollHeight > el.clientHeight + 4)
    }, 320)
    return () => window.clearTimeout(timer)
  }, [open, items.length])

  return (
    <div
      ref={registerRef}
      className={`rounded-lg border transition-colors duration-200 ${
        open
          ? 'border-[var(--brand-heading)]/25 bg-[var(--brand-bg)]/40 shadow-inner'
          : 'border-stone-200/80 bg-white hover:border-stone-300'
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex min-h-[44px] w-full items-center gap-2 px-2.5 py-2 text-left sm:px-3"
      >
        <span className="h-1.5 w-6 shrink-0 rounded-full bg-gradient-to-b from-stone-300 to-stone-400 shadow-sm" />
        <span className="shrink-0 text-sm">{CATEGORY_ICON[category] ?? '🧺'}</span>
        <span
          className="shrink-0 text-[13px] font-semibold text-[var(--brand-heading)]"
          style={{ fontFamily: 'serif' }}
        >
          {category}
        </span>
        <span
          className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] tabular-nums ${
            open ? 'bg-[var(--brand-heading)] text-white' : 'bg-[var(--brand-surface)] text-[var(--brand-subtle)]'
          }`}
        >
          {filtered && avail != null && avail !== items.length ? `${items.length} / ${avail}` : `${items.length} 件`}
        </span>
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: reduced ? 0 : 0.2 }} className="ml-auto text-stone-400">
          <ChevronDown className="h-3.5 w-3.5" />
        </motion.span>
      </button>

      {/*
        展开用 height + opacity：抽屉摊开必须改变占据高度，无法只用 transform。
        重排范围限于单个抽屉内部，且同时只会展开一格，实测移动端流畅。
      */}
      <motion.div
        initial={false}
        animate={{ height: open ? 'auto' : 0, opacity: open ? 1 : 0 }}
        transition={{ duration: reduced ? 0 : 0.28, ease: 'easeOut' }}
        className="overflow-hidden"
      >
        <div
          ref={panelRef}
          className="flex max-h-[34dvh] flex-wrap content-start gap-3 overflow-y-auto overscroll-contain px-2.5 pb-2.5 sm:px-3"
        >
          {items.map((item, idx) => (
            <DrawerItem key={item.id} item={item} index={idx} onSelect={onSelect} />
          ))}
        </div>
        {scrollable && (
          <p className="pb-2 text-center text-[9px] text-[var(--brand-subtle)]">抽屉内可上下滑动查看全部 {items.length} 件</p>
        )}
      </motion.div>
    </div>
  )
}

/**
 * 衣橱「品类抽屉柜」视图
 *
 * 一列带把手的抽屉，每格对应一个品类（上装/下装/外套/裙装/套装/鞋履/配饰），
 * 把手上刻品类名与实时件数；点一格拉出摊开该品类衣物，再点推回（同时只开一格）。
 * 抽屉内衣物点击即进入放大查看层。尺寸一律用 px/百分比，不用 rem 档位
 * （项目 root font-size 为 18px，rem 档位会被放大 12.5% 导致窄屏溢出）。
 */
export function WardrobeCabinet({ items, filtered = false, categoryAvail, onSelect }: WardrobeCabinetProps) {
  const groups = groupWardrobeByCategory(items)
  const [openCategory, setOpenCategory] = useState<string | null>(() => groups[0]?.category ?? null)
  const rowRefs = useRef<(HTMLDivElement | null)[]>([])

  // 筛选后分组会变化：当前打开的品类若已不存在，则回落到第一格，避免出现「全部闭合」的空柜感
  const activeOpen = groups.some((g) => g.category === openCategory) ? openCategory : groups[0]?.category ?? null

  const toggle = useCallback(
    (category: string, index: number) => {
      const next = activeOpen === category ? null : category
      setOpenCategory(next)
      if (next) {
        // 抽屉变高会整体位移，滚到最近可见处，保证拉开的抽屉不会落在视口外
        window.setTimeout(() => {
          rowRefs.current[index]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
        }, 280)
      }
    },
    [activeOpen],
  )

  // 首次载入（数据异步到达晚于挂载）时补开第一格
  useEffect(() => {
    if (openCategory === null && groups.length > 0) setOpenCategory(groups[0].category)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups.length])

  return (
    <div className="mx-auto w-full max-w-[520px] rounded-2xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)] sm:p-3">
      <div className="mb-2 flex items-center justify-between px-1">
        <span className="text-[10px] uppercase tracking-[0.2em] text-[#6F5D4B]/70">按品类分格收纳</span>
        <span className="text-[10px] tabular-nums text-[#6F5D4B]/70">共 {items.length} 件</span>
      </div>
      <div className="space-y-1.5">
        {groups.map((group, index) => (
          <DrawerRow
            key={group.category}
            category={group.category}
            items={group.items}
            avail={categoryAvail?.[group.category]}
            filtered={filtered}
            open={activeOpen === group.category}
            onToggle={() => toggle(group.category, index)}
            onSelect={onSelect}
            registerRef={(el) => {
              rowRefs.current[index] = el
            }}
          />
        ))}
      </div>
    </div>
  )
}
