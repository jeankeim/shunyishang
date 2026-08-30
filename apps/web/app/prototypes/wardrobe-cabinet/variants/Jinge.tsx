'use client'

// 方向三「锦阁」—— 中式精品展柜。
// 轴：仪式感与华丽。深木 + 鎏金边展格，每件衣物如展品置于聚光底座；
// 竖排鎏金品类签 + 五行朱印；入场 fade-up + 聚光渐亮。
import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ITEMS, STYLE_TABS, ELEMENT_COLOR, HANG_CATEGORIES, FOLD_CATEGORIES,
  filterByStyle, countByStyle, groupByCategory, type ProtoItem,
} from '../content'

const GOLD = '#C9A76B'
const WOOD_DEEP = '#171009'
const WOOD_MID = '#241811'
const PAPER = '#E9E0CE'

/** 展品卡：聚光底座 + 衣片 + 朱印 */
function Exhibit({ item, reduce, delay, tall }: { item: ProtoItem; reduce: boolean; delay: number; tall?: boolean }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.div
      className="relative flex flex-col items-center w-[84px] shrink-0 cursor-pointer"
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay, ease: [0.22, 1, 0.36, 1] }}
      whileHover={reduce ? undefined : { y: -4 }}
      title={item.name}
    >
      {/* 聚光 */}
      <div
        className="absolute -inset-2 rounded-full pointer-events-none"
        style={{ background: `radial-gradient(60% 45% at 50% 30%, ${GOLD}26 0%, transparent 70%)` }}
      />
      <div
        className={`relative w-[64px] ${tall ? 'h-[92px]' : 'h-[64px]'} rounded-t-[10px] rounded-b-[4px] border`}
        style={{
          background: `linear-gradient(165deg, ${c}F2 0%, ${c}B8 60%, ${c}8F 100%)`,
          borderColor: `${GOLD}66`,
          boxShadow: `0 6px 16px -6px ${c}66, inset 0 1px 0 rgba(255,255,255,0.25)`,
        }}
      >
        <span className="absolute top-1 right-1.5 text-[10px] font-serif text-white/90">{item.element}</span>
      </div>
      {/* 底座 */}
      <div className="w-[72px] h-2 rounded-[2px] mt-1" style={{ background: `linear-gradient(180deg, ${GOLD}AA, ${GOLD}55)` }} />
      <span className="mt-1.5 text-[10px] leading-tight text-center truncate w-full" style={{ color: `${PAPER}B3` }}>
        {item.name}
      </span>
    </motion.div>
  )
}

function GoldLabel({ text, count }: { text: string; count: number }) {
  return (
    <div className="flex flex-col items-center gap-2 shrink-0">
      <span
        className="text-[13px] font-semibold tracking-[0.25em] font-serif"
        style={{ writingMode: 'vertical-rl', color: GOLD }}
      >
        {text}
      </span>
      <span className="text-[10px] tabular-nums" style={{ color: `${GOLD}99` }}>{count}</span>
    </div>
  )
}

function ShowcaseRow({ label, list, reduce, tall }: { label: string; list: ProtoItem[]; reduce: boolean; tall?: boolean }) {
  return (
    <div className="flex gap-4 items-stretch">
      <GoldLabel text={label} count={list.length} />
      <div
        className="flex-1 rounded-lg p-3 border"
        style={{
          borderColor: `${GOLD}40`,
          background: `linear-gradient(180deg, ${WOOD_MID} 0%, ${WOOD_DEEP} 100%)`,
          boxShadow: 'inset 0 2px 12px rgba(0,0,0,0.6)',
        }}
      >
        {list.length ? (
          <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
            {list.map((it, i) => <Exhibit key={it.id} item={it} reduce={reduce} delay={i * 0.05} tall={tall} />)}
          </div>
        ) : (
          <div className="h-20 flex items-center justify-center text-[11px] border border-dashed rounded-md" style={{ borderColor: `${GOLD}33`, color: `${GOLD}66` }}>
            虚位以待
          </div>
        )}
      </div>
    </div>
  )
}

export function JingeVariant() {
  const [style, setStyle] = useState('全部')
  const reduce = useReducedMotion()
  const items = filterByStyle(ITEMS, style)
  const groups = groupByCategory(items)

  return (
    <div
      className="min-h-[100dvh] pb-28"
      style={{
        background: `radial-gradient(120% 60% at 50% -10%, ${GOLD}14 0%, transparent 55%), linear-gradient(180deg, ${WOOD_DEEP} 0%, #0E0906 100%)`,
        color: PAPER,
      }}
    >
      <header className="mx-auto max-w-6xl px-6 pt-8 md:px-10">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-[10px] tracking-[0.4em] mb-1.5" style={{ color: `${GOLD}99` }}>WARDROBE GALLERY</p>
            <h1 className="text-2xl md:text-3xl font-bold font-serif tracking-wide">我的衣橱</h1>
          </div>
          <p className="text-xs tabular-nums" style={{ color: `${PAPER}80` }}>{items.length} 件藏品 · {style}</p>
        </div>
        {/* 风格切换：鎏金印章式 */}
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {STYLE_TABS.map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`shrink-0 px-3.5 py-1.5 text-xs border transition-all touch-feedback ${style === s ? 'font-medium' : ''}`}
              style={{
                borderColor: style === s ? GOLD : `${GOLD}40`,
                color: style === s ? WOOD_DEEP : `${GOLD}CC`,
                background: style === s ? `linear-gradient(135deg, ${GOLD}, #B08D4F)` : 'transparent',
                borderRadius: 4,
              }}
            >
              {s}
              <span className="ml-1 tabular-nums opacity-70">{countByStyle(ITEMS, s)}</span>
            </button>
          ))}
        </div>
      </header>

      <motion.main
        key={style}
        className="mx-auto max-w-6xl px-6 md:px-10 mt-6 space-y-5"
        initial={reduce ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {/* 外框鎏金边 */}
        <div className="rounded-[20px] p-5 md:p-7 space-y-6 border" style={{ borderColor: `${GOLD}55`, background: `${WOOD_MID}80`, boxShadow: `0 32px 64px -24px rgba(0,0,0,0.8), inset 0 0 0 1px ${GOLD}22` }}>
          {HANG_CATEGORIES.map((cat) => (
            <ShowcaseRow key={cat} label={cat} list={groups[cat] || []} reduce={!!reduce} tall />
          ))}
          {/* 鎏金隔梁 */}
          <div className="h-px" style={{ background: `linear-gradient(90deg, transparent, ${GOLD}AA, transparent)` }} />
          <div className="grid md:grid-cols-2 gap-6">
            {FOLD_CATEGORIES.map((cat) => (
              <ShowcaseRow key={cat} label={cat} list={groups[cat] || []} reduce={!!reduce} />
            ))}
          </div>
          <div className="h-px" style={{ background: `linear-gradient(90deg, transparent, ${GOLD}AA, transparent)` }} />
          <ShowcaseRow label="鞋履" list={groups['鞋履'] || []} reduce={!!reduce} />
        </div>
      </motion.main>
    </div>
  )
}
