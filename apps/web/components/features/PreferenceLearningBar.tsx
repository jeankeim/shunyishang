'use client'

/**
 * 穿搭数据反哺显性化（批次一 1.3）
 *
 * 一行窄卡片，让用户看见「记日记/打卡正在让推荐更准」：
 * 近 30 天记录套数、已学习维度数、系统了解度进度条；点击展开复用 PreferenceRadar。
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GraduationCap, ChevronDown } from 'lucide-react'
import { getPreferenceSummary, type PreferenceSummary } from '@/lib/api'
import { PreferenceRadar } from './PreferenceRadar'

export function PreferenceLearningBar() {
  const [data, setData] = useState<PreferenceSummary | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let cancelled = false
    getPreferenceSummary().then(result => {
      if (!cancelled) setData(result)
    }).catch(() => {
      // 只作展示，失败时静默不渲染
    })
    return () => { cancelled = true }
  }, [])

  const signals = data?.learning_signals
  const learnedDims = data?.dimensions.filter(d => d.has_data).length ?? 0
  const diaryCount = signals?.diary_count_30d ?? 0
  const wearCount = signals?.wear_checkin_count_30d ?? 0
  const windowDays = signals?.window_days ?? 30

  // 既没记录也没反馈时无内容可显性化
  if (!data || (diaryCount === 0 && wearCount === 0 && learnedDims === 0)) return null

  const depth = Math.round((data.overall_score ?? 0) * 100)

  return (
    <div className="w-full rounded-2xl sm:rounded-3xl border border-stone-300/70 bg-gradient-to-b from-[#F6F2EC] to-[#EAE2D6] p-2.5 sm:p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_18px_36px_-24px_rgba(87,75,62,0.45)]">
      <button
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
        className="w-full text-left touch-feedback"
      >
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[#6F5D4B]/10">
            <GraduationCap className="h-3.5 w-3.5 text-[#6F5D4B]" />
          </span>
          <p className="min-w-0 flex-1 text-[11px] leading-snug text-[#5C4B3A] sm:text-xs">
            近 {windowDays} 天你记了 <span className="font-semibold tabular-nums">{diaryCount}</span> 套穿搭
            {learnedDims > 0 && <> · 推荐已按 <span className="font-semibold tabular-nums">{learnedDims}</span> 个维度更懂你</>}
            {depth > 0 && <> · 学习深度 <span className="font-semibold tabular-nums">{depth}%</span></>}
          </p>
          <ChevronDown
            className={`h-3.5 w-3.5 shrink-0 text-[#6F5D4B]/60 transition-transform ${expanded ? 'rotate-180' : ''}`}
          />
        </div>

        {/* 学习深度细进度条 */}
        {depth > 0 && (
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-[#6F5D4B]/10">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${depth}%` }}
              transition={{ duration: 0.7, ease: 'easeOut' }}
              className="h-full rounded-full bg-gradient-to-r from-[#6F5D4B]/45 to-[#B89B5E]/70"
            />
          </div>
        )}

        {/* 变化最大的维度 */}
        {(signals?.top_changed_dimensions.length ?? 0) > 0 && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1">
            {signals!.top_changed_dimensions.map(dim => (
              <span
                key={dim.key}
                className="rounded bg-white/70 px-1.5 py-0.5 text-[10px] text-[#6F5D4B]/80 tabular-nums"
              >
                {dim.label} {dim.delta > 0 ? '+' : ''}{dim.delta}
              </span>
            ))}
          </div>
        )}
      </button>

      {/* 展开：复用 6 维偏好画像 */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="mt-2.5">
              <PreferenceRadar />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
