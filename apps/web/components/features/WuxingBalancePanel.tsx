'use client'

/**
 * 五行衣橱平衡仪表盘（批次一 1.2）
 *
 * 实际占比（主五行 1.0 + 次五行 0.5 归一化）与命理目标参考口径对比：
 * 每行一条横杠，缺口段用该五行低饱和走色填充，目标位画刻度线。
 * 底部「补运建议」取缺口最大的 1-2 行，列出公共库当季单品，点击「看看这类」跳推荐。
 *
 * 文案口径：目标占比为传统文化参考口径，只作搭配参考，不作吉凶断言。
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Compass, Sparkles } from 'lucide-react'
import { getElementBalance, type ElementBalance, type ElementBalanceEntry } from '@/lib/api'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'
import { requestChatInputAutofill } from '@/lib/chatAutofill'

/** 缺口/超出文案（balanced 返回空） */
function gapText(entry: ElementBalanceEntry): string {
  if (entry.status === 'balanced') return ''
  const pct = Math.abs(Math.round(entry.gap_pct))
  return entry.status === 'deficient' ? `缺 ${pct}%` : `多 ${pct}%`
}

/** 「看看这类」：带元素与品类语境跳推荐输入框 */
function handleSeeMore(element: string, category: string) {
  requestChatInputAutofill(`推荐一件${element}属性的${category}`)
  window.location.hash = '#chat'
}

export function WuxingBalancePanel() {
  const [data, setData] = useState<ElementBalance | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getElementBalance().then(result => {
      if (!cancelled) {
        setData(result)
        setLoading(false)
      }
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]">
        <div className="mb-2 flex items-center justify-between px-1">
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#6F5D4B]/70">五行平衡 · 衣橱构成</span>
        </div>
        <div className="space-y-1.5">
          {[0, 1, 2].map(i => (
            <div key={i} className="h-9 animate-pulse rounded-xl bg-white/50" />
          ))}
        </div>
      </div>
    )
  }

  // 空衣橱或接口失败时不占位（衣橱页本身已有 EmptyState 引导）
  if (!data || data.is_empty) return null

  const luckySet = new Set(data.lucky_elements)
  const avoidSet = new Set(data.avoid_elements)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-3 sm:p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]"
    >
      {/* 头部 */}
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 px-1">
        <div>
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#6F5D4B]/70">五行平衡 · 衣橱构成</span>
          <h3 className="mt-0.5 text-[15px] font-semibold text-[#4A3F33]" style={{ fontFamily: 'serif' }}>
            五行穿搭平衡
          </h3>
        </div>
        <div className="flex items-center gap-1.5">
          {data.lucky_elements.length > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-white/70 px-2 py-0.5 text-[10px] text-[#6F5D4B]">
              <Sparkles className="w-2.5 h-2.5 text-[#B89B5E]" />
              喜用 {data.lucky_elements.join('·')}
            </span>
          )}
          <span className="text-[10px] tabular-nums text-[#6F5D4B]/70">共 {data.total_items} 件</span>
        </div>
      </div>

      {/* 五行占比条 */}
      <div className="space-y-1.5">
        {data.elements.map((entry, index) => (
          <BalanceRow
            key={entry.element}
            entry={entry}
            index={index}
            isLucky={luckySet.has(entry.element)}
            isAvoid={avoidSet.has(entry.element)}
          />
        ))}
      </div>

      <p className="mt-2 px-1 text-[10px] leading-relaxed text-[#6F5D4B]/60">
        目标占比为传统文化参考口径（第一喜用 40%、第二喜用 25%、其余三行均分，忌神上限 10%），仅作搭配参考，不构成吉凶判断。
      </p>

      {/* 补运建议 */}
      {data.advice.length > 0 && (
        <div className="mt-3 space-y-2">
          {data.advice.map(advice => (
            <div key={advice.element} className="rounded-xl border border-[#6F5D4B]/10 bg-white/55 p-2.5 sm:p-3">
              <div className="mb-2 flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5 shrink-0" style={{ color: getWuxingConfig(advice.element).color }} />
                <span className="text-[11px] font-medium leading-snug text-[#4A3F33] sm:text-xs">{advice.headline}</span>
              </div>
              {advice.items.length > 0 ? (
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
                  {advice.items.map(item => (
                    <div
                      key={item.item_code}
                      className="flex min-w-0 items-center gap-2 rounded-lg bg-white/85 p-1.5"
                    >
                      {item.image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={getImageUrl(item.image_url)}
                          alt={item.name}
                          className="h-9 w-9 shrink-0 rounded-md object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <span
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-[11px] text-white"
                          style={{ backgroundColor: getWuxingConfig(advice.element).color }}
                        >
                          {advice.element}
                        </span>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[11px] font-medium leading-tight text-[#4A3F33]">{item.name}</p>
                        <p className="mt-0.5 truncate text-[10px] leading-tight text-[#6F5D4B]/70">
                          {item.category}{item.color ? ` · ${item.color}` : ''}
                          {item.element_role === 'secondary' ? ' · 次属性' : ''}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-[#6F5D4B]/60">站内暂无该属性的当季单品，可换个季节再看看</p>
              )}
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-[10px] text-[#6F5D4B]/60">
                  可留意 {advice.want.colors.join('、')} 系{advice.want.category}
                </span>
                <button
                  onClick={() => handleSeeMore(advice.element, advice.want.category)}
                  className="inline-flex min-h-[30px] shrink-0 items-center rounded-lg border border-[#6F5D4B]/25 bg-white/80 px-2.5 text-[11px] font-medium text-[#5C4B3A] transition-colors hover:bg-white touch-feedback"
                >
                  看看这类
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

// ── 单行占比条 ────────────────────────────────────────────────────────────────

interface BalanceRowProps {
  entry: ElementBalanceEntry
  index: number
  isLucky: boolean
  isAvoid: boolean
}

function BalanceRow({ entry, index, isLucky, isAvoid }: BalanceRowProps) {
  const color = getWuxingConfig(entry.element).color
  const gapWidth = Math.max(0, Math.min(100 - entry.actual_pct, entry.gap_pct))
  const text = gapText(entry)

  return (
    <div className="flex items-center gap-2 rounded-xl bg-white/60 px-2.5 py-2 sm:gap-3">
      {/* 五行字 chip */}
      <span
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[11px] font-semibold"
        style={{ backgroundColor: `${color}1F`, color }}
      >
        {entry.element}
      </span>

      {/* 占比横条 + 目标刻度 */}
      <div className="relative h-2.5 min-w-0 flex-1 rounded-full bg-[#6F5D4B]/8">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(entry.actual_pct, 100)}%` }}
          transition={{ duration: 0.6, delay: index * 0.06, ease: 'easeOut' }}
          className="absolute left-0 top-0 h-full rounded-full"
          style={{ backgroundColor: color, opacity: 0.55 }}
        />
        {/* 缺口段：低饱和斜纹填充 */}
        {gapWidth > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 + index * 0.06 }}
            className="absolute top-0 h-full rounded-r-full"
            style={{
              left: `${Math.min(entry.actual_pct, 100)}%`,
              width: `${gapWidth}%`,
              backgroundImage: `repeating-linear-gradient(45deg, ${color}33 0 3px, ${color}14 3px 6px)`,
            }}
          />
        )}
        {/* 目标刻度线 */}
        <span
          className="absolute -top-1 h-[18px] w-[2px] rounded-full bg-[#6F5D4B]/55"
          style={{ left: `calc(${Math.min(entry.target_pct, 100)}% - 1px)` }}
          title={`目标 ${entry.target_pct}%`}
        />
      </div>

      {/* 数值与状态 */}
      <div className="flex w-[78px] shrink-0 items-center justify-end gap-1.5 sm:w-[92px]">
        <span className="text-[11px] tabular-nums text-[#6F5D4B]">{entry.actual_pct.toFixed(0)}%</span>
        <AnimatePresence mode="wait" initial={false}>
          {text ? (
            <motion.span
              key={text}
              initial={{ opacity: 0, x: 4 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="rounded px-1 py-0.5 text-[9px] font-medium leading-none tabular-nums"
              style={{
                backgroundColor: `${color}1A`,
                color,
              }}
            >
              {text}
            </motion.span>
          ) : (
            <motion.span
              key="ok"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-[9px] text-[#6F5D4B]/45"
            >
              适中
            </motion.span>
          )}
        </AnimatePresence>
        {isAvoid ? (
          <span className="text-[9px] text-[#6F5D4B]/50" title="该五行为命理忌神，占比越低越理想">忌</span>
        ) : isLucky ? (
          <span className="text-[9px]" style={{ color }} title="该五行为命理喜用">喜</span>
        ) : null}
      </div>
    </div>
  )
}
