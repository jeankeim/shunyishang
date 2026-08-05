'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CalendarDays, ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react'
import { formatLocalDate, parseLocalDate, todayLocal } from '@/lib/date'

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
const WEEKDAY_FULL = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

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
  const isValueToday = value === todayStr

  const dateText = selected
    ? `${selected.getFullYear()}年${selected.getMonth() + 1}月${selected.getDate()}日`
    : '请选择日期'
  const weekdayText = selected ? WEEKDAY_FULL[selected.getDay()] : ''

  return (
    <div ref={containerRef} className="relative">
      {/* 触发按钮 */}
      <button
        type="button"
        data-testid="date-picker-trigger"
        onClick={() => (open ? setOpen(false) : openPicker())}
        className="w-full flex items-center justify-between px-3.5 py-3 rounded-xl border border-stone-200 bg-stone-50/60 hover:bg-stone-50 hover:border-stone-300 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-emerald-200"
      >
        <span className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
            <CalendarDays className="w-[18px] h-[18px] text-emerald-600" />
          </span>
          <span className="flex flex-col items-start leading-tight">
            <span className="font-medium text-[var(--brand-heading)]">{dateText}</span>
            <span className="text-xs text-stone-400 mt-0.5">
              {selected ? (isValueToday ? `${weekdayText} · 今天` : weekdayText) : '点击选择日期'}
            </span>
          </span>
        </span>
        <ChevronDown
          className={`w-4 h-4 text-stone-400 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* 日历弹窗 */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            data-testid="date-picker-panel"
            className="absolute left-0 right-0 top-full mt-2 z-30 bg-white rounded-2xl shadow-xl shadow-stone-300/40 border border-stone-100 p-4"
          >
            {/* 月份导航 */}
            <div className="flex items-center justify-between mb-3">
              <button
                type="button"
                aria-label="上一月"
                onClick={() => goToMonth(-1)}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-stone-100 active:bg-stone-200 text-stone-500 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <div className="text-center">
                <span className="font-semibold text-sm text-stone-800">{viewYear}年{viewMonth}月</span>
              </div>
              <button
                type="button"
                aria-label="下一月"
                onClick={() => canGoNext && goToMonth(1)}
                disabled={!canGoNext}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-stone-100 active:bg-stone-200 text-stone-500 transition-colors disabled:opacity-25 disabled:hover:bg-transparent"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* 星期头 */}
            <div className="grid grid-cols-7 mb-1">
              {WEEKDAYS.map((d) => (
                <div key={d} className="text-center text-[11px] font-medium text-stone-400 py-1.5">{d}</div>
              ))}
            </div>

            {/* 日期格子 */}
            <div className="grid grid-cols-7 gap-y-1">
              {cells.map((day, i) => {
                if (day === null) return <div key={`e-${i}`} />
                const dateStr = formatLocalDate(new Date(viewYear, viewMonth - 1, day))
                const disabled = dateStr > max
                const isSelected = selected !== null && dateStr === value
                const isToday = dateStr === todayStr
                return (
                  <div key={dateStr} className="flex justify-center">
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => {
                        onChange(dateStr)
                        setOpen(false)
                      }}
                      className={`relative w-9 h-9 rounded-full text-[13px] transition-all duration-150 ${
                        isSelected
                          ? 'bg-emerald-500 text-white font-semibold shadow-md shadow-emerald-500/30 scale-105'
                          : disabled
                            ? 'text-stone-300 cursor-not-allowed'
                            : isToday
                              ? 'text-emerald-600 font-semibold bg-emerald-50 hover:bg-emerald-100'
                              : 'text-stone-700 hover:bg-stone-100 active:bg-stone-200'
                      }`}
                    >
                      {day}
                      {/* 今天的小圆点标记（非选中态时） */}
                      {isToday && !isSelected && (
                        <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-emerald-500" />
                      )}
                    </button>
                  </div>
                )
              })}
            </div>

            {/* 快捷选今天 */}
            <div className="mt-3 pt-3 border-t border-stone-100 flex justify-center">
              <button
                type="button"
                onClick={() => {
                  onChange(max)
                  setOpen(false)
                }}
                className="px-5 py-1.5 rounded-full text-xs font-medium text-emerald-600 bg-emerald-50 hover:bg-emerald-100 active:bg-emerald-200 transition-colors"
              >
                选择今天
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
