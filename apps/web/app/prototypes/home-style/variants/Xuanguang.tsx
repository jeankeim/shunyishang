'use client'

// 方向一「玄光」—— 深色高定路线。
// 墨色底 + 鎏金单强调色 + 衬线大字 + 辉光材质，电影感入场。
import { motion } from 'framer-motion'
import { ArrowRight, CloudSun } from 'lucide-react'
import { TODAY, OUTFIT, WUXING_BALANCE } from '../content'

const gold = '#C9A76B'
const ink = '#0A0D12'

const rise = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const } },
}

export function XuanguangVariant() {
  return (
    <div
      className="relative min-h-[100dvh] overflow-hidden"
      style={{
        background: `radial-gradient(120% 80% at 85% -10%, rgba(201,167,107,0.14) 0%, transparent 55%),
          radial-gradient(90% 70% at -10% 110%, rgba(74,107,130,0.12) 0%, transparent 50%),
          linear-gradient(180deg, #0A0D12 0%, #0E131B 100%)`,
        color: '#E9E5DB',
      }}
    >
      {/* 顶部栏 */}
      <motion.header
        variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { duration: 0.6, ease: 'easeOut' } } }}
        initial="hidden"
        animate="show"
        className="mx-auto flex max-w-6xl items-center justify-between px-6 pt-7 md:px-10"
      >
        <div className="flex items-baseline gap-3">
          <span className="[font-family:var(--font-noto-serif-sc)] text-lg font-semibold tracking-[0.3em]">顺衣尚</span>
          <span className="hidden text-[11px] tracking-[0.35em] text-white/35 sm:inline">WUXING · OUTFIT</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-white/45">
          <CloudSun size={14} strokeWidth={1.5} style={{ color: gold }} />
          {TODAY.city} · {TODAY.weather}
        </div>
      </motion.header>

      <main className="mx-auto grid max-w-6xl gap-14 px-6 pb-24 pt-14 md:grid-cols-[1.05fr_1fr] md:items-center md:gap-10 md:px-10 md:pt-20">
        {/* 左侧：文案 */}
        <div>
          <motion.p
            variants={rise}
            initial="hidden"
            animate="show"
            className="mb-6 flex items-center gap-3 text-xs tracking-[0.4em] text-white/40"
          >
            <span className="inline-block h-px w-8" style={{ background: gold }} />
            {TODAY.date} {TODAY.weekday} · {TODAY.solarTerm} · {TODAY.elementTrend}
          </motion.p>

          <motion.h1
            initial="hidden"
            animate="show"
            variants={{ hidden: {}, show: { transition: { staggerChildren: 0.09 } } }}
            className="[font-family:var(--font-noto-serif-sc)] text-[2.9rem] font-semibold leading-[1.14] tracking-wide md:text-[4.2rem]"
          >
            <motion.span variants={rise} className="block">金气渐升，</motion.span>
            <motion.span variants={rise} className="block">
              衣以
              <span style={{ color: gold }}>载道</span>
              。
            </motion.span>
          </motion.h1>

          <motion.p
            variants={rise}
            initial="hidden"
            animate="show"
            transition={{ delay: 0.22 }}
            className="mt-6 max-w-[42ch] text-sm leading-7 text-white/55 md:text-[15px]"
          >
            今日喜用神为「{TODAY.xiyong}」。依八字与节气推演，为你择一套金水相生之配 ——
            通勤路上，亦有章法。
          </motion.p>

          <motion.div
            variants={rise}
            initial="hidden"
            animate="show"
            transition={{ delay: 0.32 }}
            className="mt-10 flex items-center gap-4"
          >
            <button
              className="group flex h-12 items-center gap-2 rounded-full px-7 text-sm font-medium transition-transform duration-150 ease-out active:scale-[0.97]"
              style={{ background: gold, color: ink, boxShadow: '0 8px 32px rgba(201,167,107,0.28)' }}
            >
              领取今日搭配
              <ArrowRight size={16} className="transition-transform duration-200 ease-out group-hover:translate-x-0.5" />
            </button>
            <button className="h-12 rounded-full border border-white/15 px-6 text-sm text-white/70 transition-colors duration-150 hover:border-white/35 hover:text-white">
              五行分析
            </button>
          </motion.div>

          {/* 三联数据 */}
          <motion.div
            variants={rise}
            initial="hidden"
            animate="show"
            transition={{ delay: 0.42 }}
            className="mt-14 flex gap-10 border-t pt-6 text-xs"
            style={{ borderColor: 'rgba(255,255,255,0.08)' }}
          >
            {[
              ['温度', '24–29°C'],
              ['场景', TODAY.scene],
              ['喜用神', `「${TODAY.xiyong}」`],
            ].map(([k, v]) => (
              <div key={k}>
                <p className="mb-1.5 tracking-[0.2em] text-white/35">{k}</p>
                <p className="text-base text-white/85">{v}</p>
              </div>
            ))}
          </motion.div>
        </div>

        {/* 右侧：今日搭配卡片 */}
        <motion.section
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
          className="rounded-2xl p-[1px]"
          style={{
            background: 'linear-gradient(160deg, rgba(201,167,107,0.45), rgba(255,255,255,0.06) 40%, rgba(201,167,107,0.18))',
            boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
          }}
        >
          <div className="rounded-2xl bg-[#0D1117]/92 p-7 backdrop-blur md:p-8">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="[font-family:var(--font-noto-serif-sc)] text-lg font-medium tracking-[0.15em]">今日搭配 · {TODAY.scene}</h2>
              <span
                className="rounded-full px-3 py-1 text-[11px] tracking-wider"
                style={{ color: gold, background: 'rgba(201,167,107,0.1)', border: '1px solid rgba(201,167,107,0.25)' }}
              >
                金水相生
              </span>
            </div>

            <ul>
              {OUTFIT.map((item, i) => (
                <motion.li
                  key={item.name}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, delay: 0.35 + i * 0.08, ease: 'easeOut' }}
                  className="flex items-center gap-4 py-4"
                  style={{ borderBottom: i < OUTFIT.length - 1 ? '1px solid rgba(255,255,255,0.06)' : undefined }}
                >
                  <span
                    className="h-9 w-9 shrink-0 rounded-full"
                    style={{ background: item.swatch, boxShadow: '0 2px 10px rgba(0,0,0,0.4), inset 0 0 0 1px rgba(255,255,255,0.12)' }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white/90">
                      {item.color} · {item.name}
                      <span className="ml-2 text-[11px]" style={{ color: gold }}>属{item.element}</span>
                    </p>
                    <p className="mt-0.5 truncate text-xs text-white/40">{item.reason}</p>
                  </div>
                </motion.li>
              ))}
            </ul>

            {/* 五行平衡 */}
            <div className="mt-6 border-t pt-5" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
              <p className="mb-3 text-[11px] tracking-[0.3em] text-white/35">五行平衡</p>
              <div className="flex items-end gap-3">
                {WUXING_BALANCE.map((w, i) => (
                  <div key={w.element} className="flex-1">
                    <div className="flex h-14 items-end">
                      <motion.div
                        initial={{ scaleY: 0 }}
                        animate={{ scaleY: 1 }}
                        transition={{ duration: 0.5, delay: 0.55 + i * 0.06, ease: [0.22, 1, 0.36, 1] }}
                        className="w-full origin-bottom rounded-sm"
                        style={{ height: `${w.value * 2.4}px`, background: w.swatch, opacity: 0.75 }}
                      />
                    </div>
                    <p className="mt-2 text-center text-[11px] text-white/45">{w.element}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.section>
      </main>

      <footer className="pb-10 text-center text-[11px] tracking-[0.25em] text-white/25">
        顺衣尚 · 五行穿搭灵感，仅供娱乐参考
      </footer>
    </div>
  )
}
