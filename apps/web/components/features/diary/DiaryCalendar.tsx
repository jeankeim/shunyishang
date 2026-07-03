'use client'

import { motion } from 'framer-motion'
import type { DiaryCalendarEntry } from '@/types'

const MOOD_EMOJI: Record<string, string> = {
  happy: '😊', neutral: '😐', sad: '😢', excited: '🤩', calm: '😌',
}

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

interface DiaryCalendarProps {
  year: number
  month: number
  entries: DiaryCalendarEntry[]
  onPrevMonth: () => void
  onNextMonth: () => void
  onDateClick?: (date: string) => void
}

export function DiaryCalendar({ year, month, entries, onPrevMonth, onNextMonth, onDateClick }: DiaryCalendarProps) {
  const firstDay = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()

  const entryMap = new Map(entries.map((e) => [e.date, e]))

  const cells: (number | null)[] = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm border border-stone-100">
      {/* 月份导航 */}
      <div className="flex items-center justify-between mb-4">
        <motion.button whileTap={{ scale: 0.9 }} onClick={onPrevMonth} className="p-2 rounded-lg hover:bg-stone-50 text-stone-600">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
        </motion.button>
        <h3 className="font-semibold text-stone-800">{year}年{month}月</h3>
        <motion.button whileTap={{ scale: 0.9 }} onClick={onNextMonth} className="p-2 rounded-lg hover:bg-stone-50 text-stone-600">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
        </motion.button>
      </div>

      {/* 星期头 */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {WEEKDAYS.map((d) => (
          <div key={d} className="text-center text-xs text-stone-400 py-1">{d}</div>
        ))}
      </div>

      {/* 日期格子 */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, i) => {
          if (day === null) return <div key={`e-${i}`} />
          const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
          const entry = entryMap.get(dateStr)
          const emoji = entry?.mood ? MOOD_EMOJI[entry.mood] : null
          const isToday = dateStr === new Date().toISOString().split('T')[0]

          return (
            <motion.button
              key={dateStr}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onDateClick?.(dateStr)}
              className={`relative aspect-square rounded-lg flex flex-col items-center justify-center text-xs transition-colors ${
                isToday ? 'bg-emerald-50 ring-1 ring-emerald-300' : 'hover:bg-stone-50'
              }`}
            >
              <span className="text-stone-700">{day}</span>
              {emoji && <span className="text-[10px] leading-none">{emoji}</span>}
              {entry?.has_items && (
                <span className="absolute bottom-0.5 w-1 h-1 rounded-full bg-emerald-400" />
              )}
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
