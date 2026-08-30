'use client'

/**
 * 换季开柜仪式（批次三 3.3）
 *
 * 挂在衣橱页顶部：以下一个节气为参照，给出「该收 / 该拿」两张清单与一句宜忌提示。
 * 清单条目都带「按清单筛选」，点了直接写进页面既有的多维筛选栏，不另造一套筛选态。
 * 「该拿」的行内提供穿着打卡，走既有 /wardrobe/items/{id}/wear 通路（日记与计数由后端
 * 唯一写入通路维护），本卡只把该条从当日快照里摘掉。
 *
 * 文案口径：节气宜忌为传统文化参考与搭配建议，不作吉凶断言；全卡无价格与购买引导。
 */

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Archive, ChevronDown, ChevronUp, Loader2, Shirt, Sparkles, Sunrise } from 'lucide-react'
import {
  getSolarTermRitual,
  wearItem,
  type RitualItem,
  type SolarTermRitual,
} from '@/lib/api'
import { toast } from '@/components/ui'
import { getImageUrl } from '@/lib/image'
import { notifyWardrobeActiveChanged } from '@/lib/wardrobe-display'
import { getWuxingConfig } from '@/lib/wuxing-config'

/** 卡片可写入衣橱筛选栏的维度（需与 page.tsx 的 WardrobeFilters 键一致） */
export interface RitualFilterPatch {
  season?: string
  thickness?: string
  element?: string
}

interface SolarTermRitualCardProps {
  /** 把筛选条件交给页面写入筛选栏并滚过去 */
  onApplyFilter?: (patch: RitualFilterPatch) => void
}

/** 收起态每列展示几件 */
const COLLAPSED_COUNT = 3

/** 取清单里出现最多的取值，作为「按清单筛选」的条件 */
function dominant(values: string[]): string | null {
  const counts: Record<string, number> = {}
  values.forEach((v) => {
    if (v) counts[v] = (counts[v] || 0) + 1
  })
  const keys = Object.keys(counts)
  if (!keys.length) return null
  return keys.sort((a, b) => counts[b] - counts[a])[0]
}

export function SolarTermRitualCard({ onApplyFilter }: SolarTermRitualCardProps) {
  const [data, setData] = useState<SolarTermRitual | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [checkingId, setCheckingId] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    getSolarTermRitual()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch(() => {
        if (!cancelled) setData(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  /** 穿它打卡：走既有 wear 端点，成功后从当日快照清单里摘掉这一件 */
  async function handleWear(item: RitualItem) {
    if (checkingId) return
    setCheckingId(item.id)
    try {
      const res = await wearItem(item.id)
      setData((prev) => (prev ? {
        ...prev,
        take_out: {
          ...prev.take_out,
          items: prev.take_out.items.filter((x) => x.id !== item.id),
          total: Math.max(0, prev.take_out.total - 1),
        },
      } : prev))
      // 穿着次数与闲置天数变了，广播一次让衣橱列表与筛选计数同步
      notifyWardrobeActiveChanged()
      toast.success(res.already_logged
        ? `「${item.name}」今天已经打过卡了`
        : `「${item.name}」已记进今天的穿搭日记`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '打卡失败，请稍后重试')
    } finally {
      setCheckingId(null)
    }
  }

  if (loading) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-4">
        <div className="h-3 w-24 animate-pulse rounded bg-white/70" />
        <div className="mt-3 h-4 w-2/5 animate-pulse rounded bg-white/60" />
        <div className="mt-4 h-16 w-full animate-pulse rounded-xl bg-white/45" />
      </div>
    )
  }

  const term = data?.solar_term
  // 拿不到节气（后端定位失败）就不占位，避免展示一张没有参照的卡
  if (!data || !term) return null

  const storeItems = data.store_away.items
  const takeItems = data.take_out.items
  const visibleStore = expanded ? storeItems : storeItems.slice(0, COLLAPSED_COUNT)
  const visibleTake = expanded ? takeItems : takeItems.slice(0, COLLAPSED_COUNT)
  const hasMore = storeItems.length > COLLAPSED_COUNT || takeItems.length > COLLAPSED_COUNT

  const storeThickness = dominant(storeItems.map((x) => x.thickness_level || ''))
  const untilText = term.days_until === 0 ? '今天交节' : term.days_until ? `${term.days_until} 天后交节` : ''

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]"
    >
      {/* 节气抬头：当前节气 → 参照节气，附换季判定 */}
      <div className="flex flex-wrap items-start justify-between gap-2 px-1">
        <div className="min-w-0">
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#6F5D4B]/70">衣橱 · 开柜仪式</span>
          <h3 className="mt-0.5 flex items-center gap-1.5 text-[15px] font-semibold text-[#4A3F33]" style={{ fontFamily: 'serif' }}>
            <Sunrise className="w-4 h-4 shrink-0 text-[#B89B5E]" />
            {data.is_season_boundary ? `换季开柜 · 迎接${term.name}` : `${term.name}前的衣橱检查`}
          </h3>
        </div>
        <span className="rounded-full border border-[#6F5D4B]/15 bg-white/55 px-2 py-0.5 text-[10px] text-[#6F5D4B] whitespace-nowrap">
          {[data.current_term ? `${data.current_term.name} → ${term.name}` : term.name, untilText]
            .filter(Boolean)
            .join(' · ')}
        </span>
      </div>

      {/* 宜忌一行 + 衣橱缺口元素 */}
      <div className="mt-2 px-1">
        <p className="text-xs leading-relaxed text-[#6F5D4B]">{data.yi_ji.advice}</p>
        {data.next_season && (
          <p className="mt-1 text-[11px] text-[#6F5D4B]/70">
            下一季宜
            <span className="mx-1 font-medium text-[#4A3F33]">{data.next_season}</span>
            厚度参考
            <span className="ml-1 font-medium text-[#4A3F33]">
              {data.expected_thickness.length ? data.expected_thickness.join(' / ') : '按体感加减'}
            </span>
          </p>
        )}
        {data.yi_ji.gap_elements.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {data.yi_ji.gap_elements.map((gap) => {
              const label = gap.element || ''
              if (!label) return null
              return (
                <button
                  key={label}
                  type="button"
                  title={gap.headline || `衣橱里${label}气偏少，看看这类单品`}
                  onClick={() => onApplyFilter?.({ element: label })}
                  className="inline-flex items-center gap-1 rounded-full border bg-white/55 px-2 py-0.5 text-[11px] text-[#6F5D4B] transition-colors hover:bg-white touch-feedback"
                  style={{ borderColor: `${getWuxingConfig(label).color}40` }}
                >
                  <Sparkles className="w-3 h-3" style={{ color: getWuxingConfig(label).color }} />
                  衣橱缺{label}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* 两张清单 */}
      <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <RitualList
          variant="store"
          title="该收"
          reason={data.store_away.reason}
          total={data.store_away.total}
          items={visibleStore}
          emptyText="没有明显过季的单品，柜子保持原样就好。"
          filterLabel={storeThickness ? `只看${storeThickness}的` : undefined}
          onFilter={() => storeThickness && onApplyFilter?.({ thickness: storeThickness })}
        />
        <RitualList
          variant="take"
          title="该拿"
          reason={data.take_out.reason}
          total={data.take_out.total}
          items={visibleTake}
          emptyText="下一季能穿的单品最近都有上身。"
          filterLabel={data.next_season ? `只看${data.next_season}季` : undefined}
          onFilter={() => data.next_season && onApplyFilter?.({ season: data.next_season })}
          checkingId={checkingId}
          onWear={handleWear}
        />
      </div>

      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 flex w-full items-center justify-center gap-1 py-1.5 text-xs text-[#6F5D4B]/70 transition-colors hover:text-[#4A3F33] touch-feedback"
        >
          {expanded ? (
            <>收起 <ChevronUp className="w-3.5 h-3.5" /></>
          ) : (
            <>
              看更多（该收 {data.store_away.total} 件 · 该拿 {data.take_out.total} 件）
              <ChevronDown className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      )}
    </motion.div>
  )
}

/** 单张清单（该收 / 该拿）：标题 + 判定理由 + 条目 + 筛选入口 */
function RitualList({
  variant,
  title,
  reason,
  total,
  items,
  emptyText,
  filterLabel,
  onFilter,
  checkingId,
  onWear,
}: {
  variant: 'store' | 'take'
  title: string
  reason: string
  total: number
  items: RitualItem[]
  emptyText: string
  filterLabel?: string
  onFilter: () => void
  checkingId?: number | null
  onWear?: (item: RitualItem) => void
}) {
  const isTake = variant === 'take'
  const Icon = isTake ? Shirt : Archive

  return (
    <div className="rounded-xl border border-[#6F5D4B]/10 bg-white/55 p-2.5">
      <div className="flex items-center gap-1.5">
        <Icon className={`w-3.5 h-3.5 shrink-0 ${isTake ? 'text-[#3DA35D]' : 'text-[#9A8F84]'}`} />
        <span className="text-xs font-semibold text-[#4A3F33]">{title}</span>
        <span className="ml-auto text-[10px] tabular-nums text-[#6F5D4B]/70">
          {total > items.length ? `共 ${total} 件` : `${total} 件`}
        </span>
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-[#6F5D4B]/70">{reason}</p>

      {items.length === 0 ? (
        <p className="mt-2 text-[11px] text-[#6F5D4B]/60">{emptyText}</p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {items.map((item) => (
            <RitualRow
              key={item.id}
              item={item}
              isTake={isTake}
              checking={checkingId === item.id}
              busy={!!checkingId}
              onWear={onWear}
            />
          ))}
        </ul>
      )}

      {filterLabel && items.length > 0 && (
        <button
          type="button"
          onClick={onFilter}
          className="mt-2 w-full rounded-lg border border-[#6F5D4B]/15 bg-white/70 py-1.5 text-[11px] text-[#6F5D4B] transition-colors hover:bg-white hover:text-[#4A3F33] touch-feedback"
        >
          {filterLabel}
        </button>
      )}
    </div>
  )
}

function RitualRow({
  item,
  isTake,
  checking,
  busy,
  onWear,
}: {
  item: RitualItem
  isTake: boolean
  checking: boolean
  busy: boolean
  onWear?: (item: RitualItem) => void
}) {
  const elemColor = item.primary_element ? getWuxingConfig(item.primary_element).color : '#9A8F84'
  const src = getImageUrl(item.image_url)

  return (
    <li className="flex items-center gap-2">
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={item.name}
          className="h-9 w-9 shrink-0 rounded-lg border border-[#6F5D4B]/10 object-cover"
        />
      ) : (
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[11px] font-medium"
          style={{ backgroundColor: `${elemColor}15`, color: elemColor }}
        >
          {item.primary_element || '—'}
        </div>
      )}

      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-[#4A3F33]">{item.name}</p>
        <p className="mt-0.5 truncate text-[10px] text-[#6F5D4B]/70">
          {[item.category, item.thickness_level, item.seasons.length ? item.seasons.join('') : null]
            .filter(Boolean)
            .join(' · ') || '未分类'}
        </p>
      </div>

      {isTake ? (
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-[10px] text-[#B89B5E] whitespace-nowrap">
            {item.last_worn ? `${item.idle_days ?? 0} 天没上身` : '入橱后还没穿过'}
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => onWear?.(item)}
            aria-label={`穿${item.name}打卡`}
            className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] transition-opacity hover:opacity-80 disabled:opacity-40 touch-feedback"
            style={{ borderColor: '#3DA35D55', backgroundColor: '#3DA35D0D', color: '#3DA35D' }}
          >
            {checking && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
            {checking ? '打卡中' : '穿它打卡'}
          </button>
        </div>
      ) : (
        <span className="shrink-0 text-[10px] text-[#6F5D4B]/60 whitespace-nowrap">
          穿过 {item.wear_count} 次
        </span>
      )}
    </li>
  )
}
