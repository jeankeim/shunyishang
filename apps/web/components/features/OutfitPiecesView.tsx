'use client'

/**
 * 成套单品渲染（按槽位分组小标 + 衣橱缺口占位）
 *
 * 由首页「今日穿搭建议」与一周穿搭日历共用：后端已按槽位顺序
 * （核心位 → 鞋履 → 外套 → 配饰 → 补齐）返回物品，这里按相邻同槽位归组渲染，
 * 并在尾部用虚线占位提示「衣橱缺 · 点这里补」，点击跳推荐并带上元素语境。
 */

import { motion } from 'framer-motion'
import { Shirt, Plus } from 'lucide-react'
import type { DailyOutfitItem } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'

/** 品类 → 槽位小标（饰品/文玩统一归入配饰位） */
const SLOT_LABELS: Record<string, string> = {
  上装: '上装',
  下装: '下装',
  裙装: '裙装',
  套装: '套装',
  外套: '外套',
  鞋履: '鞋履',
  配饰: '配饰',
  饰品: '配饰',
  文玩: '配饰',
}

export function slotLabelOf(category?: string): string {
  if (!category) return '单品'
  return SLOT_LABELS[category] || category
}

interface OutfitPiecesViewProps {
  items: DailyOutfitItem[]
  /** 衣橱缺口品类（后端 completeness.missing），渲染为尾部虚线占位 */
  missing?: string[]
  /** 当日幸运元素，「点这里补」时带入推荐输入框作语境 */
  luckyElement?: string
  onSelectItem: (item: DailyOutfitItem) => void
  /** 点击缺口占位：由调用方负责跳转推荐并透传关键词 */
  onFillMissing?: (category: string, luckyElement?: string) => void
  /** 缩略图边长（默认 100px，一周日历用更小尺寸） */
  thumbSize?: 'md' | 'sm'
}

export function OutfitPiecesView({
  items,
  missing = [],
  luckyElement,
  onSelectItem,
  onFillMissing,
  thumbSize = 'md',
}: OutfitPiecesViewProps) {
  return (
    <div className="flex gap-2.5 overflow-x-auto pb-1 scrollbar-hide">
      {items.map((item, idx) => (
        <OutfitPieceCard
          key={item.id}
          item={item}
          index={idx}
          size={thumbSize}
          onClick={() => onSelectItem(item)}
        />
      ))}
      {missing.map((category) => (
        <MissingPieceCard
          key={category}
          category={category}
          size={thumbSize}
          onClick={() => onFillMissing?.(category, luckyElement)}
        />
      ))}
    </div>
  )
}

// ── 单件衣物卡片（带槽位小标）─────────────────────────────────────────────────

interface OutfitPieceCardProps {
  item: DailyOutfitItem
  index: number
  size: 'md' | 'sm'
  onClick: () => void
}

export function OutfitPieceCard({ item, index, size, onClick }: OutfitPieceCardProps) {
  const elementColor = item.primary_element ? getWuxingConfig(item.primary_element).color : '#ccc'
  const boxClass = size === 'sm' ? 'w-[76px]' : 'w-[100px]'
  const thumbClass = size === 'sm' ? 'h-[76px]' : 'h-[100px]'

  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.06, duration: 0.2 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className={`${boxClass} flex-shrink-0 rounded-xl border border-[var(--brand-border)]/60 bg-white overflow-hidden shadow-sm hover:shadow-md transition-shadow text-left`}
    >
      <div className={`w-full ${thumbClass} bg-[var(--brand-surface)] relative overflow-hidden`}>
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={getImageUrl(item.image_url)}
            alt={item.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Shirt className={`w-8 h-8 text-[var(--brand-subtle)]/40`} />
          </div>
        )}
        {/* 五行标签 */}
        {item.primary_element && (
          <div
            className="absolute top-1.5 left-1.5 text-[9px] px-1.5 py-0.5 rounded-full text-white font-medium"
            style={{ backgroundColor: elementColor }}
          >
            {item.primary_element}
          </div>
        )}
        {/* 收藏标记 */}
        {item.is_favorite && (
          <div className="absolute top-1.5 right-1.5 text-xs">♥</div>
        )}
        {/* 槽位小标 */}
        <div className="absolute bottom-1.5 left-1.5 text-[9px] px-1.5 py-0.5 rounded bg-white/85 text-[var(--brand-subtle)] tracking-wide">
          {slotLabelOf(item.category)}
        </div>
      </div>

      <div className="p-2">
        <p className="text-xs font-medium text-[var(--brand-heading)] line-clamp-1 leading-tight">
          {item.name}
        </p>
        <p className="text-[10px] text-[var(--brand-subtle)] mt-0.5">
          {item.wear_count > 0 ? `穿过 ${item.wear_count} 次` : '还没穿过'}
        </p>
      </div>
    </motion.button>
  )
}

// ── 衣橱缺口占位 ──────────────────────────────────────────────────────────────

interface MissingPieceCardProps {
  category: string
  size: 'md' | 'sm'
  onClick: () => void
}

function MissingPieceCard({ category, size, onClick }: MissingPieceCardProps) {
  const boxClass = size === 'sm' ? 'w-[76px]' : 'w-[100px]'
  const thumbClass = size === 'sm' ? 'h-[76px]' : 'h-[100px]'

  return (
    <motion.button
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      aria-label={`衣橱缺${category}，去推荐补充`}
      className={`${boxClass} flex-shrink-0 rounded-xl border border-dashed border-[var(--brand-border)] bg-[var(--brand-surface)]/40 overflow-hidden text-left hover:bg-[var(--brand-surface-active)]/60 transition-colors`}
    >
      <div className={`w-full ${thumbClass} flex flex-col items-center justify-center gap-1 text-[var(--brand-subtle)]`}>
        <Plus className="w-4 h-4" />
        <span className="text-[10px] leading-none">衣橱缺</span>
      </div>
      <div className="px-2 pb-2">
        <p className="text-[10px] text-[var(--brand-subtle)] leading-tight line-clamp-1">
          {category} · 点这里补
        </p>
      </div>
    </motion.button>
  )
}
