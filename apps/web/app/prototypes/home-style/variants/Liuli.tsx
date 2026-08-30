'use client'

// 方向三「琉璃」—— 现代极简冷奢路线。
// 银灰中性底 + 单一钴蓝强调 + 无衬线主导 + Bento 网格 + 1px 实线。
// 与前两方向分叉轴：色板与密度 —— 去装饰、产品化的清爽 App 气质。
// 造型锁：卡片 16px 圆角、按钮全圆角胶囊。
import { motion } from 'framer-motion'
import { ArrowUpRight, CloudSun, Sparkles } from 'lucide-react'
import { TODAY, OUTFIT, WUXING_BALANCE } from '../content'

const bg = '#F4F5F7'
const line = '#E2E5EA'
const ink = '#101216'
const sub = '#5C636E'
const cobalt = '#2F50C8' // 单一强调色

const easeOut = [0.22, 1, 0.36, 1] as const
const card = { background: '#FFFFFF', border: `1px solid ${line}`, borderRadius: 16 }

export function LiuliVariant() {
  return (
    <div className="min-h-[100dvh]" style={{ background: bg, color: ink }}>
      {/* 顶部栏 */}
      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: easeOut }}
        className="mx-auto flex max-w-6xl items-center justify-between px-6 pt-7 md:px-10"
      >
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold text-white" style={{ background: cobalt }}>
            顺
          </span>
          <span className="text-[15px] font-semibold tracking-wide">顺衣尚</span>
        </div>
        <button className="h-10 rounded-full border bg-white px-5 text-[13px] font-medium transition-transform duration-150 ease-out active:scale-[0.97]" style={{ borderColor: line }}>
          我的衣橱
        </button>
      </motion.header>

      <main className="mx-auto max-w-6xl px-6 pb-24 pt-8 md:px-10">
        {/* Bento 网格 */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:grid-rows-[auto_auto]">
          {/* 主视觉卡 */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: easeOut }}
            className="relative overflow-hidden p-8 md:col-span-2 md:p-10"
            style={card}
          >
            <div className="mb-8 flex items-center gap-2 text-[13px]" style={{ color: sub }}>
              <CloudSun size={15} strokeWidth={1.8} />
              {TODAY.date} {TODAY.weekday} · {TODAY.solarTerm} · {TODAY.city} {TODAY.weather}
            </div>
            <h1 className="text-[2.2rem] font-semibold leading-[1.16] tracking-tight md:text-[3.2rem]">
              今天，穿「{TODAY.xiyong}」出门。
            </h1>
            <p className="mt-4 max-w-[46ch] text-sm leading-6 md:text-[15px]" style={{ color: sub }}>
              {TODAY.elementTrend}，喜用神为「{TODAY.xiyong}」。已为{TODAY.scene}场景生成一套金水相生的搭配。
            </p>
            <div className="mt-8 flex items-center gap-3">
              <button
                className="group flex h-11 items-center gap-1.5 rounded-full px-6 text-sm font-medium text-white transition-transform duration-150 ease-out active:scale-[0.97]"
                style={{ background: cobalt }}
              >
                查看今日搭配
                <ArrowUpRight size={15} className="transition-transform duration-200 ease-out group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </button>
              <button className="h-11 rounded-full border bg-white px-6 text-sm font-medium transition-colors duration-150 hover:bg-gray-50" style={{ borderColor: line }}>
                换一批
              </button>
            </div>
            <span
              className="absolute right-8 top-8 hidden items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium md:flex"
              style={{ color: cobalt, background: 'rgba(47,80,200,0.08)' }}
            >
              <Sparkles size={13} strokeWidth={1.8} />
              AI 已就绪
            </span>
          </motion.section>

          {/* 五行平衡卡 */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.08, ease: easeOut }}
            className="p-7"
            style={card}
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-sm font-semibold">五行平衡</h2>
              <span className="text-xs" style={{ color: sub }}>喜用「{TODAY.xiyong}」</span>
            </div>
            <div className="flex items-end gap-2.5">
              {WUXING_BALANCE.map((w, i) => (
                <div key={w.element} className="flex-1">
                  <div className="flex h-24 items-end">
                    <motion.div
                      initial={{ scaleY: 0 }}
                      animate={{ scaleY: 1 }}
                      transition={{ duration: 0.5, delay: 0.25 + i * 0.05, ease: easeOut }}
                      className="w-full origin-bottom rounded-md"
                      style={{
                        height: `${w.value * 2.6}px`,
                        background: w.element === TODAY.xiyong || w.element === '金' ? cobalt : '#D5DAE1',
                      }}
                    />
                  </div>
                  <p className="mt-2 text-center text-xs" style={{ color: sub }}>{w.element}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs leading-5" style={{ color: sub }}>
              火旺水弱，今日宜以金、水之色补足气场。
            </p>
          </motion.section>

          {/* 今日搭配卡（横向通栏） */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.16, ease: easeOut }}
            className="p-7 md:col-span-3"
            style={card}
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-sm font-semibold">今日搭配 · {TODAY.scene}</h2>
              <span className="rounded-full px-3 py-1 text-xs font-medium" style={{ color: cobalt, background: 'rgba(47,80,200,0.08)' }}>
                金水相生
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {OUTFIT.map((item, i) => (
                <motion.div
                  key={item.name}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: 0.3 + i * 0.06, ease: easeOut }}
                  className="group cursor-pointer rounded-xl border p-4 transition-shadow duration-200 ease-out hover:shadow-[0_8px_24px_rgba(16,18,22,0.08)]"
                  style={{ borderColor: line }}
                >
                  <div className="mb-4 flex h-24 items-center justify-center rounded-lg" style={{ background: '#F7F8FA' }}>
                    <span
                      className="h-12 w-12 rounded-full transition-transform duration-200 ease-out group-hover:scale-110"
                      style={{ background: item.swatch, boxShadow: 'inset 0 0 0 1px rgba(16,18,22,0.08)' }}
                    />
                  </div>
                  <p className="text-[13px] font-semibold">{item.color} · {item.name}</p>
                  <p className="mt-1 text-xs leading-5" style={{ color: sub }}>{item.reason}</p>
                  <p className="mt-2 text-xs font-medium" style={{ color: cobalt }}>属{item.element}</p>
                </motion.div>
              ))}
            </div>
          </motion.section>
        </div>
      </main>

      <footer className="pb-10 text-center text-xs" style={{ color: '#9AA1AB' }}>
        顺衣尚 · 五行穿搭灵感，仅供娱乐参考
      </footer>
    </div>
  )
}
