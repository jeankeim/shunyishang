'use client'

/**
 * 断舍离年度战报（批次三 3.1）
 *
 * 折叠展示：收起时只给一句话战报与三个关键数字，展开后看三态分布、五行构成
 * 与已处理清单（清单即撤销入口）。
 *
 * 口径：站内无价格字段，只做件数折算（「相当于少买 N 件」），不做金额换算。
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Feather, RotateCcw } from 'lucide-react'
import {
  getDeclutterReport,
  undoDeclutterWardrobeItem,
  type DeclutterReport,
} from '@/lib/api'
import { toast } from '@/components/ui'
import { getImageUrl } from '@/lib/image'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { WARDROBE_ACTIVE_CHANGED, getDeclutterOption, notifyWardrobeActiveChanged } from '@/lib/wardrobe-display'

/** 三态在战报条里的走色（与闲置卡的描边小键同一套色板） */
const ACTION_COLORS: Record<string, string> = {
  donate: '#3DA35D',
  sell: '#B89B5E',
  discard: '#9A8F84',
}

export function DeclutterReportCard() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [data, setData] = useState<DeclutterReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const [undoingId, setUndoingId] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    getDeclutterReport(year)
      .then(result => { setData(result) })
      .catch(() => { setData(null) })
      .finally(() => { setLoading(false) })
  }, [year])

  useEffect(() => { load() }, [load])

  // 闲置卡处理完衣物后刷新战报
  useEffect(() => {
    const handler = () => load()
    document.addEventListener(WARDROBE_ACTIVE_CHANGED, handler)
    return () => document.removeEventListener(WARDROBE_ACTIVE_CHANGED, handler)
  }, [load])

  const handleUndo = async (itemId: number, name: string) => {
    setUndoingId(itemId)
    try {
      await undoDeclutterWardrobeItem(itemId)
      toast.success(`「${name}」已回到衣橱`)
      // 本卡自监听 WARDROBE_ACTIVE_CHANGED，广播即刷新，无需再显式 load()
      notifyWardrobeActiveChanged()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '撤销失败，请稍后重试')
    } finally {
      setUndoingId(null)
    }
  }

  if (loading) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]">
        <div className="mb-2 h-4 w-32 animate-pulse rounded bg-white/50" />
        <div className="h-9 animate-pulse rounded-xl bg-white/50" />
      </div>
    )
  }

  // 没有处理记录（或接口失败）时不占位
  if (!data || data.total_processed === 0) return null

  const maxActionCount = Math.max(...data.by_action.map(a => a.count), 1)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]"
    >
      {/* 头部：年份切换 + 展开/收起 */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="min-w-0">
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#6F5D4B]/70">断舍离 · 年度战报</span>
          <h3 className="mt-0.5 text-[15px] font-semibold text-[#4A3F33]" style={{ fontFamily: 'serif' }}>
            给衣橱减了 {data.total_processed} 件负担
          </h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setYear(y => y - 1)}
            aria-label="上一年"
            className="rounded-md p-1 text-[#6F5D4B]/60 transition-colors hover:bg-white/70 hover:text-[#4A3F33] touch-feedback"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="min-w-[3.2rem] text-center text-xs tabular-nums text-[#6F5D4B]">{data.year} 年</span>
          <button
            type="button"
            onClick={() => setYear(y => Math.min(currentYear, y + 1))}
            disabled={year >= currentYear}
            aria-label="下一年"
            className="rounded-md p-1 text-[#6F5D4B]/60 transition-colors hover:bg-white/70 hover:text-[#4A3F33] disabled:opacity-30 disabled:hover:bg-transparent touch-feedback"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setExpanded(v => !v)}
            aria-expanded={expanded}
            className="ml-1 inline-flex items-center gap-1 rounded-lg border border-[#6F5D4B]/15 bg-white/60 px-2 py-1 text-[11px] text-[#6F5D4B] transition-colors hover:bg-white/90 touch-feedback"
          >
            {expanded ? '收起' : '展开'}
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      <p className="mt-2 px-1 text-xs leading-relaxed text-[#6F5D4B]">{data.summary}</p>

      {/* 关键数字（始终可见） */}
      <div className="mt-2.5 grid grid-cols-3 gap-1.5">
        <StatCell value={`${data.released_count} 件`} label="衣橱让出的位置" />
        <StatCell
          value={data.max_idle_days ? `${data.max_idle_days} 天` : '—'}
          label="最久的一件闲置"
        />
        <StatCell value={`${data.avoided_purchase_count} 件`} label="相当于少买" />
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            {/* 三态分布 */}
            <div className="mt-3 rounded-xl bg-white/55 p-2.5 sm:p-3">
              <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[#6F5D4B]/70">处理方式</div>
              <div className="space-y-1.5">
                {data.by_action.map(entry => (
                  <div key={entry.action} className="flex items-center gap-2">
                    <span className="w-8 shrink-0 text-[11px] text-[#4A3F33]">{entry.label}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#6F5D4B]/10">
                      <div
                        className="h-full rounded-full transition-[width] duration-500"
                        style={{
                          width: `${(entry.count / maxActionCount) * 100}%`,
                          backgroundColor: (ACTION_COLORS[entry.action] || '#9A8F84') + 'B3',
                        }}
                      />
                    </div>
                    <span className="w-8 shrink-0 text-right text-[11px] tabular-nums text-[#6F5D4B]">{entry.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 五行构成 */}
            {data.element_breakdown.length > 0 && (
              <div className="mt-2 rounded-xl bg-white/55 p-2.5 sm:p-3">
                <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-[#6F5D4B]/70">放下的多是哪一行</div>
                <div className="flex flex-wrap gap-x-3 gap-y-1.5">
                  {data.element_breakdown.map(entry => (
                    <span key={entry.element} className="inline-flex items-center gap-1 text-[11px] text-[#4A3F33]">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: getWuxingConfig(entry.element).color }}
                      />
                      {entry.element}
                      <span className="tabular-nums text-[#6F5D4B]/70">{entry.count} 件</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 已处理清单（撤销入口） */}
            <div className="mt-2 rounded-xl bg-white/55 p-2.5 sm:p-3">
              <div className="mb-1.5 flex items-center gap-1.5">
                <Feather className="w-3 h-3 text-[#B89B5E]" />
                <span className="text-[10px] uppercase tracking-[0.18em] text-[#6F5D4B]/70">
                  {data.year} 年处理清单
                </span>
              </div>
              <ul className="divide-y divide-[#6F5D4B]/10">
                {data.processed_items.map(item => {
                  const accent = ACTION_COLORS[item.action] || '#9A8F84'
                  return (
                    <li key={item.id} className="flex items-center gap-2.5 py-2">
                      {item.image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={getImageUrl(item.image_url)}
                          alt={item.name}
                          className="h-8 w-8 shrink-0 rounded-md object-cover"
                        />
                      ) : (
                        <div
                          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[11px]"
                          style={{ backgroundColor: `${accent}14`, color: accent }}
                        >
                          {item.primary_element || '衣'}
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[11px] font-medium text-[#4A3F33]">{item.name || '未命名衣物'}</p>
                        <p className="mt-0.5 text-[10px] text-[#6F5D4B]/70">
                          {item.action_label || getDeclutterOption(item.action).doneLabel}
                          {item.acted_date ? ` · ${item.acted_date}` : ''}
                          {item.idle_days_at_action ? ` · 当时已闲置 ${item.idle_days_at_action} 天` : ''}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleUndo(item.id, item.name || '这件衣物')}
                        disabled={undoingId === item.id}
                        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[#6F5D4B]/15 bg-white/80 px-2 py-1 text-[10px] text-[#6F5D4B] transition-colors hover:bg-white disabled:opacity-50 touch-feedback"
                      >
                        <RotateCcw className="w-3 h-3" />
                        撤销
                      </button>
                    </li>
                  )
                })}
              </ul>
              {data.total_processed > data.processed_items.length && (
                <p className="mt-1.5 text-[10px] text-[#6F5D4B]/60">
                  仅展示最近 {data.processed_items.length} 件
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-2 px-1 text-[10px] leading-relaxed text-[#6F5D4B]/60">
        处理只是让衣物离开每日成套与推荐，历史穿搭日记完整保留；在清单里点「撤销」即可放回衣橱。
      </p>
    </motion.div>
  )
}

/** 关键数字小格（白色半透明内格，与柜体其他面板一致） */
function StatCell({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl bg-white/55 px-2 py-2 text-center">
      <div className="text-[13px] font-semibold tabular-nums text-[#4A3F33]" style={{ fontFamily: 'serif' }}>
        {value}
      </div>
      <div className="mt-0.5 text-[10px] leading-tight text-[#6F5D4B]/70">{label}</div>
    </div>
  )
}
