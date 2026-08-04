'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatLocalDate, parseLocalDate, todayLocal } from '@/lib/date'

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

interface DiaryDatePickerProps {
  value: string
  onChange: (date: string) => void
  /** 最大可选日期（默认今天，不允许选未来） */
  maxDate?: string
}

/**
 * 日历格式日期选择器
 *
 * 替代原生 input[type=date]：iOS 上原生控件是滚轮而非日历，
 * 且 toISOString 计算的 max 在凌晨时段会错误地禁止选择"今天"。
 */
export function DiaryDatePicker({ value, onChange, maxDate }: DiaryDatePickerProps) {
  const max = maxDate ?? todayLocal()
  const [open, setOpen] = useState(false)

  const initial = value ? parseLocalDate(value) : new Date()
  const [viewYear, setViewYear] = useState(initial.getFullYear())
  const [viewMonth, setViewMonth] = useState(initial.getMonth() + 1)

  const containerRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent | TouchEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('touchstart', handler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('touchstart', handler)
    }
  }, [open])

  const openPicker = () => {
    // 每次打开时回到「已选日期」所在月份
    const d = value ? parseLocalDate(value) : new Date()
    setViewYear(d.getFullYear())
    setViewMonth(d.getMonth() + 1)
    setOpen(true)
  }

  const goToMonth = (delta: number) => {
    const d = new Date(viewYear, viewMonth - 1 + delta, 1)
    setViewYear(d.getFullYear())
    setViewMonth(d.getMonth() + 1)
  }

  const firstDay = new Date(viewYear, viewMonth - 1, 1).getDay()
  const daysInMonth = new Date(viewYear, viewMonth, 0).getDate()

  // 不允许翻到「今天」所在月份之后
  const maxDateObj = parseLocalDate(max)
  const canGoNext = new Date(viewYear, viewMonth - 1 + 1, 1) <= maxDateObj

  const cells: (number | null)[] = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  const selected = value ? parseLocalDate(value) : null
  const todayStr = todayLocal()

  const displayText = selected
    ? `${selected.getFullYear()}年${selected.getMonth() + 1}月${selected.getDate()}日`
    : '请选择日期'

  return (
    <div ref={containerRef} className="relative">
      {/* 触发按钮 */}
      <button
        type="button"
        data-testid="date-picker-trigger"
        onClick={() => (open ? setOpen(false) : openPicker())}
        className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-sm text-[var(--brand-heading)] focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 transition-all"
      >
        <span className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-stone-400" />
          {displayText}
        </span>
        <span className="text-stone-300 text-xs">{open ? '收起' : '选择'}</span>
      </button>

      {/* 日历弹窗 */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            data-testid="date-picker-panel"
            className="absolute left-0 right-0 top-full mt-2 z-30 bg-white rounded-2xl shadow-lg border border-stone-100 p-4"
          >
            {/* 月份导航 */}
            <div className="flex items-center justify-between mb-3">
              <button
                type="button"
                aria-label="上一月"
                onClick={() => goToMonth(-1)}
                className="p-1.5 rounded-lg hover:bg-stone-50 text-stone-500"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-semibold text-sm text-stone-800">{viewYear}年{viewMonth}月</span>
              <button
                type="button"
                aria-label="下一月"
                onClick={() => canGoNext && goToMonth(1)}
                disabled={!canGoNext}
                className="p-1.5 rounded-lg hover:bg-stone-50 text-stone-500 disabled:opacity-30 disabled:hover:bg-transparent"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
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
                const dateStr = formatLocalDate(new Date(viewYear, viewMonth - 1, day))
                const disabled = dateStr > max
                const isSelected = selected !== null && dateStr === value
                const isToday = dateStr === todayStr
                return (
                  <button
                    key={dateStr}
                    type="button"
                    disabled={disabled}
                    onClick={() => {
                      onChange(dateStr)
                      setOpen(false)
                    }}
                    className={`aspect-square rounded-lg text-xs font-medium transition-colors ${
                      isSelected
                        ? 'bg-emerald-500 text-white'
                        : disabled
                          ? 'text-stone-200 cursor-not-allowed'
                          : isToday
                            ? 'bg-emerald-50 ring-1 ring-emerald-300 text-emerald-700 hover:bg-emerald-100'
                            : 'text-stone-700 hover:bg-stone-50'
                    }`}
                  >
                    {day}
                  </button>
                )
              })}
            </div>

            {/* 快捷选今天 */}
            <button
              type="button"
              onClick={() => {
                onChange(max)
                setOpen(false)
              }}
              className="mt-3 w-full py-2 rounded-lg text-xs text-emerald-600 bg-emerald-50 hover:bg-emerald-100 font-medium"
            >
              选择今天
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
