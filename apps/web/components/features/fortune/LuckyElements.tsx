'use client'

import { motion } from 'framer-motion'
import type { LuckyElements as LuckyElementsType } from '@/types'

const SECTION_CONFIG = [
  { key: 'colors' as const, label: '幸运颜色', emoji: '🎨' },
  { key: 'materials' as const, label: '推荐材质', emoji: '🧵' },
  { key: 'directions' as const, label: '吉利方位', emoji: '🧭' },
  { key: 'elements' as const, label: '五行元素', emoji: '✨' },
]

interface LuckyElementsProps {
  luckyElements: LuckyElementsType
}

export function LuckyElements({ luckyElements }: LuckyElementsProps) {
  const hasAny = SECTION_CONFIG.some((s) => luckyElements[s.key]?.length > 0)

  if (!hasAny) {
    return (
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100 text-center">
        <p className="text-sm text-stone-400">暂无幸运元素数据</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100"
    >
      <h3 className="text-sm font-semibold text-stone-800 mb-4">今日幸运元素</h3>
      <div className="grid grid-cols-2 gap-3">
        {SECTION_CONFIG.map((section) => {
          const items = luckyElements[section.key]
          if (!items || items.length === 0) return null
          return (
            <div key={section.key} className="bg-stone-50 rounded-xl p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-sm">{section.emoji}</span>
                <p className="text-xs font-medium text-stone-600">{section.label}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {items.map((item, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-full bg-white border border-stone-200 text-xs text-stone-700"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
