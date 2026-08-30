'use client'

// 方向二「宋韵」—— 浅色编辑刊式路线。
// 冷宣纸底 + 墨色 + 单一黛青强调 + 全直角造型 + 细线分隔 + 竖排点缀。
// 与「玄光」分叉轴：明暗/材质 → 版式结构；排版语言完全不同。
import { motion } from 'framer-motion'
import { TODAY, OUTFIT, WUXING_BALANCE } from '../content'

const paper = '#EFF2EC'
const ink = '#1B1E1B'
const dai = '#2F5B56' // 单一强调色：黛青

const easeOut = [0.22, 1, 0.36, 1] as const

export function SongyunVariant() {
  return (
    <div className="min-h-[100dvh]" style={{ background: paper, color: ink }}>
      {/* 刊头 */}
      <motion.header
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="mx-auto max-w-6xl px-6 md:px-10"
      >
        <div className="flex items-center justify-between border-b py-5 text-xs tracking-[0.25em]" style={{ borderColor: 'rgba(27,30,27,0.18)' }}>
          <span className="[font-family:var(--font-noto-serif-sc)] text-base font-semibold">顺衣尚</span>
          <span style={{ color: dai }}>{TODAY.solarTerm} · 第廿四候</span>
          <span className="opacity-60">{TODAY.date} {TODAY.weekday}</span>
        </div>
      </motion.header>

      <main className="mx-auto max-w-6xl px-6 pb-24 md:px-10">
        {/* 头版：大标题 + 竖排句 */}
        <div className="grid grid-cols-[1fr_auto] gap-8 pb-16 pt-14 md:pt-20">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: easeOut }}
              className="mb-5 text-xs tracking-[0.4em] opacity-50"
            >
              {TODAY.city} · {TODAY.weather} · {TODAY.elementTrend}
            </motion.p>
            <motion.h1
              initial="hidden"
              animate="show"
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.1 } } }}
              className="[font-family:var(--font-noto-serif-sc)] text-[2.7rem] font-semibold leading-[1.18] md:text-[4rem]"
            >
              <motion.span initial={{ opacity: 0, y: 26 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: easeOut }} className="block">
                应时而衣，
              </motion.span>
              <motion.span initial={{ opacity: 0, y: 26 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: easeOut }} className="block">
                五色与节气<span style={{ color: dai }}>相和</span>。
              </motion.span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.25, ease: easeOut }}
              className="mt-7 max-w-[46ch] text-sm leading-7 opacity-65 md:text-[15px]"
            >
              你的喜用神为「{TODAY.xiyong}」。我们以八字为经、节气为纬，
              为今日的{TODAY.scene}择一套相合之衣。
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.35, ease: easeOut }}
              className="mt-10 flex items-center gap-3"
            >
              <button
                className="h-12 px-8 text-sm tracking-[0.15em] text-white transition-transform duration-150 ease-out active:scale-[0.97]"
                style={{ background: ink }}
              >
                阅今日搭配
              </button>
              <button
                className="h-12 border px-8 text-sm tracking-[0.15em] transition-colors duration-150"
                style={{ borderColor: 'rgba(27,30,27,0.3)' }}
              >
                五行小课
              </button>
            </motion.div>
          </div>

          {/* 竖排点缀 */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            aria-hidden
            className="hidden select-none [font-family:var(--font-noto-serif-sc)] text-sm tracking-[0.5em] opacity-45 md:block"
            style={{ writingMode: 'vertical-rl' }}
          >
            顺天之时 · 应物而生
          </motion.p>
        </div>

        {/* 〇一 今日搭配 */}
        <section className="border-t pt-10" style={{ borderColor: 'rgba(27,30,27,0.22)' }}>
          <motion.div
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.6, ease: easeOut }}
            className="origin-left"
          >
            <div className="mb-8 flex items-baseline gap-4">
              <span className="[font-family:var(--font-noto-serif-sc)] text-sm" style={{ color: dai }}>〇一</span>
              <h2 className="[font-family:var(--font-noto-serif-sc)] text-xl font-semibold tracking-[0.2em]">今日搭配</h2>
              <span className="text-xs opacity-50">{TODAY.scene} · 金水相生</span>
            </div>
          </motion.div>

          <ul className="grid gap-x-10 md:grid-cols-2">
            {OUTFIT.map((item, i) => (
              <motion.li
                key={item.name}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.15 + i * 0.08, ease: easeOut }}
                className="flex items-center justify-between border-b py-5"
                style={{ borderColor: 'rgba(27,30,27,0.12)' }}
              >
                <div className="flex items-center gap-4">
                  <span className="w-6 text-xs opacity-40">{String(i + 1).padStart(2, '0')}</span>
                  <span className="h-6 w-6" style={{ background: item.swatch, boxShadow: 'inset 0 0 0 1px rgba(27,30,27,0.15)' }} />
                  <div>
                    <p className="text-sm font-medium">{item.color} · {item.name}</p>
                    <p className="mt-0.5 text-xs opacity-50">{item.reason}</p>
                  </div>
                </div>
                <span className="[font-family:var(--font-noto-serif-sc)] text-base" style={{ color: dai }}>{item.element}</span>
              </motion.li>
            ))}
          </ul>
        </section>

        {/* 〇二 五行盈缺 */}
        <section className="mt-16 border-t pt-10" style={{ borderColor: 'rgba(27,30,27,0.22)' }}>
          <div className="mb-8 flex items-baseline gap-4">
            <span className="[font-family:var(--font-noto-serif-sc)] text-sm" style={{ color: dai }}>〇二</span>
            <h2 className="[font-family:var(--font-noto-serif-sc)] text-xl font-semibold tracking-[0.2em]">五行盈缺</h2>
            <span className="text-xs opacity-50">喜用「{TODAY.xiyong}」，宜以金水补足</span>
          </div>
          <div className="grid grid-cols-5 gap-6 md:gap-10">
            {WUXING_BALANCE.map((w, i) => (
              <motion.div
                key={w.element}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.2 + i * 0.06, ease: easeOut }}
                className="text-center"
              >
                <p className="mb-3 [font-family:var(--font-noto-serif-sc)] text-2xl font-semibold">{w.value}</p>
                <div className="mx-auto mb-3 h-px w-full" style={{ background: 'rgba(27,30,27,0.2)' }} />
                <p className="text-xs tracking-[0.3em] opacity-60">{w.element}</p>
              </motion.div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t py-8 text-center text-[11px] tracking-[0.25em] opacity-40" style={{ borderColor: 'rgba(27,30,27,0.18)' }}>
        顺衣尚 · 五行穿搭灵感，仅供娱乐参考
      </footer>
    </div>
  )
}
