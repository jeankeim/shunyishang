'use client'

import { motion } from 'framer-motion'
import type { DailyFortune } from '@/types'

const DIMENSION_LABELS: Record<string, { label: string; emoji: string }> = {
  career: { label: '事业', emoji: '💼' },
  wealth: { label: '财运', emoji: '💰' },
  love: { label: '桃花', emoji: '💕' },
  health: { label: '健康', emoji: '🌿' },
  study: { label: '学业', emoji: '📚' },
}

interface FortuneCardProps {
  fortune: DailyFortune
  onRegenerate?: () => void
}

export function FortuneCard({ fortune, onRegenerate }: FortuneCardProps) {
  const date = new Date(fortune.fortune_date)
  const dateStr = `${date.getMonth() + 1}月${date.getDate()}日`

  const scoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600'
    if (score >= 60) return 'text-amber-500'
    return 'text-stone-500'
  }

  const overallColor = (score: number) => {
    if (score >= 80) return 'from-emerald-400 to-teal-500'
    if (score >= 60) return 'from-amber-400 to-orange-400'
    return 'from-stone-400 to-stone-500'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100"
    >
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-stone-800">{dateStr} 运势</h3>
          <p className="text-xs text-stone-500 mt-0.5">基于八字五行分析</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${overallColor(fortune.overall_score)} flex items-center justify-center shadow-sm`}>
            <span className="text-xl font-bold text-white">{fortune.overall_score}</span>
          </div>
        </div>
      </div>

      {/* 五维度分数 */}
      <div className="grid grid-cols-5 gap-2 mb-4">
        {Object.entries(fortune.scores).map(([key, score]) => {
          const dim = DIMENSION_LABELS[key]
          return (
            <div key={key} className="text-center">
              <span className="text-lg">{dim?.emoji}</span>
              <p className="text-[10px] text-stone-500 mt-0.5">{dim?.label}</p>
              <p className={`text-sm font-bold ${scoreColor(score)}`}>{score}</p>
            </div>
          )
        })}
      </div>

      {/* 建议文字 */}
      {fortune.advice_text && (
        <div className="bg-stone-50 rounded-xl p-3 mb-3">
          <p className="text-xs text-stone-600 leading-relaxed">{fortune.advice_text}</p>
        </div>
      )}

      {/* 穿搭建议 */}
      {fortune.outfit_suggestion && (
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-3 mb-3">
          <p className="text-xs font-medium text-emerald-700 mb-1">今日穿搭建议</p>
          <p className="text-xs text-emerald-600 leading-relaxed">{fortune.outfit_suggestion}</p>
        </div>
      )}

      {/* 重新生成 */}
      {onRegenerate && (
        <motion.button
          whileTap={{ scale: 0.98 }}
          onClick={onRegenerate}
          className="w-full py-2.5 rounded-xl border border-stone-200 text-xs text-stone-600 font-medium hover:bg-stone-50 transition-colors"
        >
          重新生成运势
        </motion.button>
      )}
    </motion.div>
  )
}
