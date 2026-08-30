'use client'

// 方向二「素简」—— 现代简约白柜。
// 轴：密度与克制。浅色细线格柜 + 抽屉式叠放 + 均匀磁贴陈列，接近现代家居收纳系统；
// 动效仅淡入，150ms，stagger 20ms。
import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ITEMS, STYLE_TABS, ELEMENT_COLOR, HANG_CATEGORIES, FOLD_CATEGORIES,
  filterByStyle, countByStyle, groupByCategory, type ProtoItem,
} from '../content'

const LINE = '#E7E5E0'
const INK = '#1C1917'
const SUB = '#78716C'

/** 挂式磁贴：细线衣架 + 直角衣片 */
function HangTile({ item, reduce, delay }: { item: ProtoItem; reduce: boolean; delay: number }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.button
      className="group flex flex-col items-center w-[72px] shrink-0 text-left"
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15, delay }}
      title={item.name}
    >
      <svg viewBox="0 0 24 14" className="w-7 h-4 text-stone-400" aria-hidden="true">
        <path d="M12 1.2c-1.3 0-2.1 1-2.1 1.9M12 4.2 2.6 12.4h18.8L12 4.2Z" fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div
        className="w-[52px] h-[72px] rounded-[3px] border transition-transform duration-150 group-hover:-translate-y-0.5"
        style={{ background: `${c}1A`, borderColor: `${c}66` }}
      >
        <div className="h-[3px] w-full rounded-t-[3px]" style={{ background: c }} />
        <div className="px-1.5 pt-1.5 space-y-1">
          <div className="h-px w-3/4" style={{ background: `${c}55` }} />
          <div className="h-px w-1/2" style={{ background: `${c}40` }} />
        </div>
      </div>
      <span className="mt-1.5 text-[10px] text-stone-500 truncate w-full text-center">{item.name}</span>
    </motion.button>
  )
}

/** 叠放磁贴：等宽折叠条 */
function FoldTile({ item, reduce, delay }: { item: ProtoItem; reduce: boolean; delay: number }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.button
      className="group flex flex-col items-center w-[72px] shrink-0"
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15, delay }}
      title={item.name}
    >
      <div className="w-[56px] rounded-[3px] border p-1.5 space-y-[3px] transition-transform duration-150 group-hover:-translate-y-0.5" style={{ borderColor: LINE, background: '#fff' }}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-[7px] rounded-[2px]" style={{ background: `${c}${i === 0 ? 'CC' : i === 1 ? '99' : '66'}` }} />
        ))}
      </div>
      <span className="mt-1.5 text-[10px] text-stone-500 truncate w-full text-center">{item.name}</span>
    </motion.button>
  )
}

/** 鞋磁贴：俯视鞋盒 */
function ShoeTile({ item, reduce, delay }: { item: ProtoItem; reduce: boolean; delay: number }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.button
      className="group flex flex-col items-center w-[72px] shrink-0"
      initial={reduce ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15, delay }}
      title={item.name}
    >
      <div className="w-[56px] h-[40px] rounded-[3px] border flex items-center justify-center gap-1 transition-transform duration-150 group-hover:-translate-y-0.5" style={{ borderColor: LINE, background: '#fff' }}>
        <div className="w-[10px] h-[26px] rounded-full" style={{ background: `${c}B3` }} />
        <div className="w-[10px] h-[26px] rounded-full" style={{ background: `${c}80` }} />
      </div>
      <span className="mt-1.5 text-[10px] text-stone-500 truncate w-full text-center">{item.name}</span>
    </motion.button>
  )
}

function Cell({ label, count, children }: { label: string; count: number; children: React.ReactNode }) {
  return (
    <section className="border-t" style={{ borderColor: LINE }}>
      <div className="flex items-baseline justify-between px-1 pt-3 pb-2">
        <h3 className="text-[11px] font-medium tracking-[0.18em]" style={{ color: SUB }}>{label}</h3>
        <span className="text-[10px] tabular-nums" style={{ color: SUB }}>{count}</span>
      </div>
      {children}
    </section>
  )
}

export function SujianVariant() {
  const [style, setStyle] = useState('全部')
  const reduce = useReducedMotion()
  const items = filterByStyle(ITEMS, style)
  const groups = groupByCategory(items)

  return (
    <div className="min-h-[100dvh] pb-28" style={{ background: '#FAFAF9', color: INK }}>
      <header className="mx-auto max-w-5xl px-6 pt-8">
        <div className="flex items-baseline justify-between">
          <h1 className="text-xl font-semibold tracking-tight">我的衣橱</h1>
          <p className="text-xs tabular-nums" style={{ color: SUB }}>{items.length} 件 · {style}</p>
        </div>
        {/* 风格切换：下划线式 */}
        <nav className="mt-4 flex gap-5 overflow-x-auto scrollbar-hide border-b" style={{ borderColor: LINE }}>
          {STYLE_TABS.map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`shrink-0 pb-2 text-xs transition-colors touch-feedback ${style === s ? 'font-medium' : ''}`}
              style={{
                color: style === s ? INK : SUB,
                boxShadow: style === s ? 'inset 0 -2px 0 0 #1C1917' : 'none',
              }}
            >
              {s} <span className="tabular-nums opacity-60">{countByStyle(ITEMS, s)}</span>
            </button>
          ))}
        </nav>
      </header>

      <motion.main
        key={style}
        className="mx-auto max-w-5xl px-6 mt-6 rounded-lg border bg-white"
        style={{ borderColor: LINE }}
        initial={reduce ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {/* 悬挂区：四格并列 */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4">
          {HANG_CATEGORIES.map((cat, ci) => {
            const list = groups[cat] || []
            return (
              <div key={cat} className={`p-4 ${ci > 0 ? 'border-l' : ''} ${ci >= 2 ? 'border-t sm:border-t-0' : ''}`} style={{ borderColor: LINE }}>
                <Cell label={cat} count={list.length}>
                  {list.length ? (
                    <div className="flex gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-hide">
                      {list.map((it, i) => <HangTile key={it.id} item={it} reduce={!!reduce} delay={i * 0.02} />)}
                    </div>
                  ) : (
                    <div className="h-24 rounded-[3px] border border-dashed flex items-center justify-center text-[10px]" style={{ borderColor: LINE, color: SUB }}>空</div>
                  )}
                </Cell>
              </div>
            )
          })}
        </div>

        {/* 叠放区：两格 */}
        <div className="grid sm:grid-cols-2 border-t" style={{ borderColor: LINE }}>
          {FOLD_CATEGORIES.map((cat, ci) => {
            const list = groups[cat] || []
            return (
              <div key={cat} className={`p-4 ${ci > 0 ? 'border-l' : ''}`} style={{ borderColor: LINE }}>
                <Cell label={`${cat} · 抽屉`} count={list.length}>
                  {list.length ? (
                    <div className="flex gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-hide">
                      {list.map((it, i) => <FoldTile key={it.id} item={it} reduce={!!reduce} delay={i * 0.02} />)}
                    </div>
                  ) : (
                    <div className="h-16 rounded-[3px] border border-dashed flex items-center justify-center text-[10px]" style={{ borderColor: LINE, color: SUB }}>空</div>
                  )}
                </Cell>
              </div>
            )
          })}
        </div>

        {/* 鞋架区 */}
        <div className="p-4">
          <Cell label="鞋履 · 层架" count={(groups['鞋履'] || []).length}>
            {(groups['鞋履'] || []).length ? (
              <div className="flex gap-1.5 overflow-x-auto pb-1 pt-1 scrollbar-hide">
                {(groups['鞋履'] || []).map((it, i) => <ShoeTile key={it.id} item={it} reduce={!!reduce} delay={i * 0.02} />)}
              </div>
            ) : (
              <div className="h-16 rounded-[3px] border border-dashed flex items-center justify-center text-[10px]" style={{ borderColor: LINE, color: SUB }}>空</div>
            )}
          </Cell>
        </div>
      </motion.main>

      <p className="mx-auto max-w-5xl px-6 mt-4 text-[10px]" style={{ color: SUB }}>
        悬挂 {HANG_CATEGORIES.reduce((n, c) => n + (groups[c] || []).length, 0)} 件 · 叠放 {FOLD_CATEGORIES.reduce((n, c) => n + (groups[c] || []).length, 0)} 件 · 鞋履 {(groups['鞋履'] || []).length} 件
      </p>
    </div>
  )
}
