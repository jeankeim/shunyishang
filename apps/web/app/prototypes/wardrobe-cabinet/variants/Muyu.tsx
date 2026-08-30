'use client'

// 方向一「木语」—— 国风木质衣橱。
// 轴：真实衣柜隐喻。木纹柜体 + 铜挂杆衣架悬挂区 + 抽屉叠放区 + 鞋架区；
// 切换风格联动木色主题（国风→红木 / 简约→白橡 / 商务→深胡桃…）。
import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ITEMS, STYLE_TABS, ELEMENT_COLOR, HANG_CATEGORIES, FOLD_CATEGORIES,
  filterByStyle, countByStyle, groupByCategory, type ProtoItem,
} from '../content'

// 风格 → 木色主题
const WOOD: Record<string, { wood: [string, string]; panel: string; bg: string; ink: string }> = {
  全部: { wood: ['#7A5233', '#5D3E26'], panel: '#8B6240', bg: '#F3EEE4', ink: '#3E2C1D' },
  国风: { wood: ['#6E2F2A', '#4A1F1C'], panel: '#7A3B34', bg: '#F5EDE6', ink: '#40201C' },
  简约: { wood: ['#D8C7AC', '#BFA985'], panel: '#E4D6BC', bg: '#FAF7F0', ink: '#5C4B33' },
  商务: { wood: ['#4A3626', '#33241A'], panel: '#57422F', bg: '#EFEBE3', ink: '#2E2117' },
  休闲: { wood: ['#9A6B3F', '#7C5430'], panel: '#A8794C', bg: '#F4EFE5', ink: '#4A331D' },
  运动: { wood: ['#8A8D8F', '#6E7275'], panel: '#989B9D', bg: '#F2F3F3', ink: '#3B3E40' },
  甜美: { wood: ['#B0766B', '#96584E'], panel: '#BC8478', bg: '#F8F0EC', ink: '#5E372F' },
}

function Hanger({ tone }: { tone: string }) {
  return (
    <svg viewBox="0 0 24 14" className="w-8 h-5" style={{ color: tone }} aria-hidden="true">
      <path d="M12 1.2c-1.3 0-2.1 1-2.1 1.9" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M12 4.2 2.6 12.4h18.8L12 4.2Z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
    </svg>
  )
}

/** 悬挂衣物：衣架 + 五行色衣片，hover 微摆 */
function HangingItem({ item, reduce, delay }: { item: ProtoItem; reduce: boolean; delay: number }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.div
      className="flex flex-col items-center w-16 shrink-0 cursor-pointer"
      style={{ originY: 0 }}
      initial={reduce ? false : { opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay, ease: [0.22, 1, 0.36, 1] }}
      whileHover={reduce ? undefined : { rotate: [0, 2.4, -1.8, 0] }}
      title={item.name}
    >
      <Hanger tone="#C9A76B" />
      <div
        className="w-14 h-20 rounded-b-[14px] rounded-t-[4px] shadow-md relative overflow-hidden"
        style={{ background: `linear-gradient(160deg, ${c}E6 0%, ${c}B3 55%, ${c}8C 100%)` }}
      >
        <div className="absolute inset-x-0 top-0 h-3" style={{ background: 'rgba(255,255,255,0.22)' }} />
        <span className="absolute bottom-1 right-1.5 text-[10px] text-white/85 font-serif">{item.element}</span>
      </div>
      <span className="mt-1.5 text-[10px] leading-tight text-center opacity-70 truncate w-full">{item.name}</span>
    </motion.div>
  )
}

/** 叠放衣物：三折堆叠 */
function FoldStack({ item, reduce, delay }: { item: ProtoItem; reduce: boolean; delay: number }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.div
      className="flex flex-col items-center w-16 shrink-0 cursor-pointer"
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay, ease: 'easeOut' }}
      whileHover={reduce ? undefined : { y: -3 }}
      title={item.name}
    >
      <div className="flex flex-col items-center gap-[3px]">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-[4px] shadow-sm"
            style={{
              width: 52 - i * 4,
              height: 10,
              background: `linear-gradient(180deg, ${c}D9, ${c}A6)`,
              opacity: 1 - i * 0.14,
            }}
          />
        ))}
      </div>
      <span className="mt-1.5 text-[10px] leading-tight text-center opacity-70 truncate w-full">{item.name}</span>
    </motion.div>
  )
}

/** 鞋：侧影 */
function ShoeItem({ item, reduce, delay }: { item: ProtoItem; reduce: boolean; delay: number }) {
  const c = ELEMENT_COLOR[item.element]
  return (
    <motion.div
      className="flex flex-col items-center w-16 shrink-0 cursor-pointer"
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay, ease: 'easeOut' }}
      whileHover={reduce ? undefined : { y: -3 }}
      title={item.name}
    >
      <div className="relative w-14 h-9">
        <div
          className="absolute bottom-1 left-0 w-full h-6 rounded-tl-[14px] rounded-tr-[6px] rounded-b-[4px] shadow-md"
          style={{ background: `linear-gradient(150deg, ${c}E6, ${c}99)` }}
        />
        <div className="absolute bottom-0 left-0 w-full h-1.5 rounded-full bg-black/25" />
      </div>
      <span className="mt-1.5 text-[10px] leading-tight text-center opacity-70 truncate w-full">{item.name}</span>
    </motion.div>
  )
}

function VerticalLabel({ text, count, ink }: { text: string; count: number; ink: string }) {
  return (
    <div className="flex flex-col items-center gap-2 shrink-0 pr-1">
      <span
        className="text-sm font-semibold tracking-[0.2em] font-serif"
        style={{ writingMode: 'vertical-rl', color: ink }}
      >
        {text}
      </span>
      <span className="text-[10px] tabular-nums opacity-60" style={{ color: ink }}>{count}</span>
    </div>
  )
}

export function MuyuVariant() {
  const [style, setStyle] = useState('全部')
  const reduce = useReducedMotion()
  const theme = WOOD[style] || WOOD['全部']
  const items = filterByStyle(ITEMS, style)
  const groups = groupByCategory(items)

  return (
    <div className="min-h-[100dvh] pb-28 transition-colors duration-500" style={{ background: theme.bg, color: theme.ink }}>
      <header className="mx-auto max-w-6xl px-6 pt-8 md:px-10">
        <div className="flex items-baseline justify-between">
          <h1 className="text-2xl md:text-3xl font-bold font-serif tracking-wide">我的衣橱</h1>
          <p className="text-xs opacity-70">共 {items.length} 件 · {style === '全部' ? '全部风格' : `${style}衣橱`}</p>
        </div>
        {/* 风格衣橱切换 */}
        <div className="mt-4 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {STYLE_TABS.map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs transition-all touch-feedback ${
                style === s ? 'text-white shadow-md font-medium' : 'bg-black/5 hover:bg-black/10'
              }`}
              style={style === s ? { background: `linear-gradient(135deg, ${theme.wood[0]}, ${theme.wood[1]})` } : undefined}
            >
              {s}
              <span className="ml-1 tabular-nums opacity-70">{countByStyle(ITEMS, s)}</span>
            </button>
          ))}
        </div>
      </header>

      {/* 木柜主体 */}
      <motion.div
        key={style}
        className="mx-auto max-w-6xl px-6 md:px-10 mt-6"
        initial={reduce ? false : { opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        <div
          className="rounded-[26px] p-5 md:p-7 shadow-2xl transition-all duration-500"
          style={{
            background: `linear-gradient(180deg, ${theme.wood[0]} 0%, ${theme.wood[1]} 100%)`,
            boxShadow: '0 24px 48px -16px rgba(62,44,29,0.35), inset 0 1px 0 rgba(255,255,255,0.18)',
          }}
        >
          {/* 柜顶檐线 */}
          <div className="h-1.5 rounded-full mb-5" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,167,107,0.7), transparent)' }} />

          {/* 悬挂区 */}
          <div className="space-y-5">
            {HANG_CATEGORIES.map((cat) => {
              const list = groups[cat] || []
              return (
                <div key={cat} className="flex gap-3 items-stretch">
                  <VerticalLabel text={cat} count={list.length} ink="#F0E4D0" />
                  <div className="flex-1 rounded-xl p-3 pt-2" style={{ background: 'rgba(0,0,0,0.18)' }}>
                    {/* 铜挂杆 */}
                    <div className="h-1.5 rounded-full mb-1" style={{ background: 'linear-gradient(90deg, #8C6D3F, #C9A76B, #8C6D3F)' }} />
                    {list.length ? (
                      <div className="flex gap-2 overflow-x-auto pb-1 pt-1 scrollbar-hide">
                        {list.map((it, i) => (
                          <HangingItem key={it.id} item={it} reduce={!!reduce} delay={i * 0.04} />
                        ))}
                      </div>
                    ) : (
                      <div className="h-24 flex items-center justify-center text-[11px] text-white/40 border border-dashed border-white/20 rounded-lg mt-1">
                        空挂位
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* 隔板 */}
          <div className="my-5 h-2 rounded-full" style={{ background: 'rgba(0,0,0,0.28)', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.4)' }} />

          {/* 叠放抽屉区 + 鞋架区 */}
          <div className="grid md:grid-cols-2 gap-5">
            {FOLD_CATEGORIES.map((cat) => {
              const list = groups[cat] || []
              return (
                <div key={cat} className="flex gap-3">
                  <VerticalLabel text={cat} count={list.length} ink="#F0E4D0" />
                  <div
                    className="flex-1 rounded-xl p-3"
                    style={{ background: `linear-gradient(180deg, ${theme.panel}66, rgba(0,0,0,0.22))`, boxShadow: 'inset 0 2px 6px rgba(0,0,0,0.3)' }}
                  >
                    {/* 抽屉拉手 */}
                    <div className="flex justify-center mb-2">
                      <div className="w-10 h-1.5 rounded-full" style={{ background: '#C9A76B' }} />
                    </div>
                    {list.length ? (
                      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                        {list.map((it, i) => (
                          <FoldStack key={it.id} item={it} reduce={!!reduce} delay={i * 0.04} />
                        ))}
                      </div>
                    ) : (
                      <div className="h-16 flex items-center justify-center text-[11px] text-white/40 border border-dashed border-white/20 rounded-lg">空抽屉</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="my-5 h-2 rounded-full" style={{ background: 'rgba(0,0,0,0.28)', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.4)' }} />

          {(() => {
            const list = groups['鞋履'] || []
            return (
              <div className="flex gap-3">
                <VerticalLabel text="鞋履" count={list.length} ink="#F0E4D0" />
                <div className="flex-1 rounded-xl p-3" style={{ background: 'rgba(0,0,0,0.18)' }}>
                  {list.length ? (
                    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                      {list.map((it, i) => (
                        <ShoeItem key={it.id} item={it} reduce={!!reduce} delay={i * 0.04} />
                      ))}
                    </div>
                  ) : (
                    <div className="h-16 flex items-center justify-center text-[11px] text-white/40 border border-dashed border-white/20 rounded-lg">空鞋架</div>
                  )}
                  <div className="mt-2 h-1 rounded-full" style={{ background: 'linear-gradient(90deg, #8C6D3F, #C9A76B, #8C6D3F)' }} />
                </div>
              </div>
            )
          })()}
        </div>
      </motion.div>
    </div>
  )
}
