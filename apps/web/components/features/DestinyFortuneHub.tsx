'use client'

import { lazy, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Compass, CircleDot } from 'lucide-react'
import { SkeletonCard } from '@/components/ui'

// 懒加载运势/命理页面，保持代码分割
const FortunePage = lazy(() => import('@/app/fortune/page'))
const DestinyPage = lazy(() => import('@/app/destiny/page'))

export type DestinyFortuneTab = 'fortune' | 'destiny'

interface DestinyFortuneHubProps {
  /** 当前激活的子页签（受控） */
  activeTab: DestinyFortuneTab
  /** 切换子页签回调 */
  onTabChange: (tab: DestinyFortuneTab) => void
}

const SUB_TABS: Array<{
  id: DestinyFortuneTab
  label: string
  desc: string
  Icon: typeof Compass
}> = [
  { id: 'fortune', label: '每日运势', desc: '今日运势 · 本周趋势', Icon: Compass },
  { id: 'destiny', label: '命理分析', desc: '十神格局 · 大运流年', Icon: CircleDot },
]

function HubLoadingFallback() {
  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <SkeletonCard lines={2} />
      <SkeletonCard lines={3} showImage={false} />
      <SkeletonCard lines={2} showImage={false} />
    </div>
  )
}

/**
 * 运势 + 命理 综合页面
 * 两个模块关联度高，合并为一个页签展示，通过顶部分段控件切换。
 */
export function DestinyFortuneHub({ activeTab, onTabChange }: DestinyFortuneHubProps) {
  return (
    <div className="max-w-4xl mx-auto">
      {/* 顶部分段切换控件 */}
      <div className="mb-4 grid grid-cols-2 gap-2 rounded-2xl bg-stone-100/80 p-1.5">
        {SUB_TABS.map((tab) => {
          const isActive = activeTab === tab.id
          const { Icon } = tab
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              aria-current={isActive ? 'page' : undefined}
              className={`relative flex items-center justify-center gap-2.5 rounded-xl px-4 py-2.5 text-left transition-all duration-200 ${
                isActive
                  ? 'text-[var(--brand-heading)]'
                  : 'text-stone-500 hover:text-stone-700'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="destinyFortuneHubIndicator"
                  className="absolute inset-0 rounded-xl bg-white shadow-sm"
                  transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative flex items-center gap-2.5">
                <Icon
                  className={`h-5 w-5 shrink-0 ${
                    isActive ? 'text-[var(--wuxing-wood)]' : 'text-stone-400'
                  }`}
                  strokeWidth={isActive ? 2.4 : 2}
                />
                <span className="flex flex-col">
                  <span className="text-sm font-semibold leading-tight">{tab.label}</span>
                  <span className="hidden text-[11px] font-normal leading-tight text-stone-400 sm:block">
                    {tab.desc}
                  </span>
                </span>
              </span>
            </button>
          )
        })}
      </div>

      {/* 子页签内容 */}
      <AnimatePresence mode="wait">
        {activeTab === 'fortune' ? (
          <motion.div
            key="hub-fortune"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <Suspense fallback={<HubLoadingFallback />}>
              <FortunePage />
            </Suspense>
          </motion.div>
        ) : (
          <motion.div
            key="hub-destiny"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <Suspense fallback={<HubLoadingFallback />}>
              <DestinyPage />
            </Suspense>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
