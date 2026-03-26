'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Calendar, ChevronDown, Loader2, Moon, Sun, AlertCircle, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BaziInput } from '@/types'
import { calculateBazi, BaziCalculateRequest } from '@/lib/api'
import { useChatStore, RadarData } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  solarToLunar, 
  lunarToSolar, 
  getShiChenIndex,
  SHI_CHEN, 
  SHI_CHEN_TIME,
  type LunarDate 
} from '@/lib/lunar'

// ============================================================
// 静态常量 - 移到组件外部避免每次渲染重新创建
// ============================================================

// 年份选项（1900-2030）- 静态常量
const YEARS = Array.from({ length: 131 }, (_, i) => 1900 + i)

// 月份选项 - 静态常量
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)

// 时辰选项 - 静态常量（预计算）
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => ({
  value: i,
  label: `${SHI_CHEN[getShiChenIndex(i)]} (${SHI_CHEN_TIME[getShiChenIndex(i)]})`
}))

// ============================================================

interface BaziInputSectionProps {
  className?: string
}

export function BaziInputSection({ className }: BaziInputSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true)
  const [calendarType, setCalendarType] = useState<'solar' | 'lunar'>('solar')
  const [isCalculating, setIsCalculating] = useState(false)
  const { setRadarData, userBazi, setUserBazi } = useChatStore()
  const { user, isAuthenticated } = useUserStore()

  // 日期状态
  const [date, setDate] = useState({
    year: 1995,
    month: 1,
    day: 1,
    hour: 12,
    minute: 0,
  })
  const [gender, setGender] = useState<'男' | '女'>('男')

  // 检查用户资料中的出生信息是否完整
  const hasCompleteProfileInfo = useMemo(() => {
    if (!user?.birth_date) return false
    
    const birthDate = new Date(user.birth_date)
    return (
      birthDate instanceof Date && 
      !isNaN(birthDate.getTime()) && 
      user.gender
    )
  }, [user])

  // 当用户资料中有完整的出生信息时，初始化八字输入组件
  useEffect(() => {
    if (hasCompleteProfileInfo && user?.birth_date && user.gender) {
      const birthDate = new Date(user.birth_date)
      setDate({
        year: birthDate.getFullYear(),
        month: birthDate.getMonth() + 1,
        day: birthDate.getDate(),
        hour: user.birth_time ? parseInt(user.birth_time.split(':')[0]) : 12,
        minute: user.birth_time ? parseInt(user.birth_time.split(':')[1]) : 0,
      })
      setGender(user.gender as '男' | '女')
    }
  }, [hasCompleteProfileInfo, user])

  // 监听用户资料更新事件并同步数据
  useEffect(() => {
    const handleProfileUpdate = (event: CustomEvent) => {
      const { birth_date, birth_time, gender } = event.detail
      
      if (birth_date && gender) {
        const birthDate = new Date(birth_date)
        if (birthDate instanceof Date && !isNaN(birthDate.getTime())) {
          setDate({
            year: birthDate.getFullYear(),
            month: birthDate.getMonth() + 1,
            day: birthDate.getDate(),
            hour: birth_time ? parseInt(birth_time.split(':')[0]) : 12,
            minute: birth_time ? parseInt(birth_time.split(':')[1]) : 0,
          })
          setGender(gender as '男' | '女')
          
          // 自动展开并计算八字
          setIsExpanded(true)
        }
      }
    }

    document.addEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    return () => {
      document.removeEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    }
  }, [])

  // ============================================================
  // 性能优化：使用 useMemo 缓存计算结果
  // ============================================================
  
  // 日期选项（根据年月动态计算）- 使用 useMemo 缓存
  const days = useMemo(() => {
    const daysInMonth = new Date(date.year, date.month, 0).getDate()
    return Array.from({ length: daysInMonth }, (_, i) => i + 1)
  }, [date.year, date.month])

  // 农历转换 - 使用 useMemo 缓存，避免每次渲染重新计算
  const lunarDisplay = useMemo(() => {
    if (calendarType === 'solar') {
      return solarToLunar(date.year, date.month, date.day)
    }
    return null
  }, [date.year, date.month, date.day, calendarType])

  // ============================================================
  // 性能优化：使用 useCallback 缓存事件处理函数
  // ============================================================

  // 更新日期的通用方法
  const updateDate = useCallback((field: keyof typeof date, value: number) => {
    setDate(prev => ({ ...prev, [field]: value }))
  }, [])

  const handleCalculate = useCallback(async () => {
    setIsCalculating(true)
    try {
      // 如果是农历，需要转换为公历再计算
      let solarDate = { ...date }
      if (calendarType === 'lunar') {
        const converted = lunarToSolar(date.year, date.month, date.day)
        if (converted) {
          solarDate = { ...converted, hour: date.hour, minute: date.minute }
        }
      }

      const request: BaziCalculateRequest = {
        birth_year: solarDate.year,
        birth_month: solarDate.month,
        birth_day: solarDate.day,
        birth_hour: solarDate.hour,
        gender: gender,
      }

      const result = await calculateBazi(request)

      // 更新雷达图数据 - 将计数转换为百分比
      const elements = ['金', '木', '水', '火', '土']
      const maxCount = Math.max(...elements.map((el) => result.five_elements_count[el] || 0))
      const currentData: Record<string, number> = {}
      elements.forEach((el) => {
        const count = result.five_elements_count[el] || 0
        currentData[el] = maxCount > 0 ? Math.round((count / maxCount) * 100) : 20
      })
            
      const suggestedData: Record<string, number> = {}
      elements.forEach((el) => {
        suggestedData[el] = result.suggested_elements.includes(el) ? 80 : 25
      })
      
      const radarData: RadarData = {
        currentData,
        suggestedData,
        xiyongShen: result.suggested_elements,
        pillars: result.pillars,
        eightChars: result.eight_chars,
        dayMaster: result.day_master,
        elementCounts: result.five_elements_count,
      }
      setRadarData(radarData)

      // 保存八字信息
      const baziInput: BaziInput = {
        birthYear: solarDate.year,
        birthMonth: solarDate.month,
        birthDay: solarDate.day,
        birthHour: solarDate.hour,
        gender: gender,
      }
      setUserBazi(baziInput)

      // 收起输入区
      setIsExpanded(false)
    } catch (e) {
      console.error('八字计算失败:', e)
      alert('八字计算失败，请检查输入')
    } finally {
      setIsCalculating(false)
    }
  }, [date, calendarType, gender, setRadarData, setUserBazi])

  const handleClear = useCallback(() => {
    setUserBazi(null)
    setRadarData({
      currentData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
      suggestedData: { '金': 20, '木': 20, '水': 20, '火': 20, '土': 20 },
      xiyongShen: [],
      pillars: undefined,
      eightChars: undefined,
      dayMaster: undefined,
    })
    setIsExpanded(false)
  }, [setUserBazi, setRadarData])

  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  const switchCalendarType = useCallback((type: 'solar' | 'lunar') => {
    setCalendarType(type)
  }, [])

  const switchGender = useCallback((g: '男' | '女') => {
    setGender(g)
  }, [])

  return (
    <div className={cn('bg-background/60 backdrop-blur-sm border border-border/30 rounded-xl p-4 shadow-sm', className)}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-primary" />
          <h3 className="font-medium">生辰八字</h3>
          {userBazi && (
            <span className="text-xs text-muted-foreground">
              {userBazi.birthYear}年{userBazi.birthMonth}月{userBazi.birthDay}日
            </span>
          )}
        </div>
        <button
          onClick={toggleExpanded}
          className="flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition"
        >
          {userBazi ? '修改' : '输入八字'}
          <ChevronDown className={cn('h-4 w-4 transition-transform', isExpanded && 'rotate-180')} />
        </button>
      </div>
      
      {/* 用户资料提醒区域 */}
      {!hasCompleteProfileInfo && isAuthenticated && (
        <div className="mb-4 p-3 bg-amber-50/60 border border-amber-200/60 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="text-amber-800 font-medium">建议完善个人资料</p>
              <p className="text-amber-700 mt-1">
                在个人资料中填写完整的出生信息，可以让八字计算更加准确，
                并且无需重复输入。
              </p>
              <button
                onClick={() => {
                  // 这里可以触发打开个人资料面板的逻辑
                  document.dispatchEvent(new CustomEvent('openUserProfile'))
                }}
                className="mt-2 inline-flex items-center gap-1 text-amber-600 hover:text-amber-700 text-xs font-medium"
              >
                <User className="h-3 w-3" />
                去完善资料
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* 展开的输入表单 */}
      {isExpanded && (
        <div className="space-y-4 pt-3 border-t border-border/50">
          {/* 历法切换 */}
          <div className="flex bg-muted/50 rounded-lg p-1">
            <button
              onClick={() => switchCalendarType('solar')}
              className={cn(
                'flex-1 py-1.5 text-sm rounded-md transition',
                calendarType === 'solar'
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              公历
            </button>
            <button
              onClick={() => switchCalendarType('lunar')}
              className={cn(
                'flex-1 py-1.5 text-sm rounded-md transition',
                calendarType === 'lunar'
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              农历
            </button>
          </div>

          {/* 日期选择 */}
          <div className="grid grid-cols-4 gap-2">
            {/* 年 */}
            <div className="min-w-0">
              <label className="text-xs text-muted-foreground mb-1 block truncate">
                {calendarType === 'solar' ? '年' : '农历年'}
              </label>
              <select
                value={date.year}
                onChange={(e) => updateDate('year', parseInt(e.target.value))}
                className="w-full min-w-[70px] px-2 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            {/* 月 */}
            <div className="min-w-0">
              <label className="text-xs text-muted-foreground mb-1 block truncate">
                {calendarType === 'solar' ? '月' : '农历月'}
              </label>
              <select
                value={date.month}
                onChange={(e) => updateDate('month', parseInt(e.target.value))}
                className="w-full min-w-[60px] px-2 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              >
                {MONTHS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            {/* 日 */}
            <div className="min-w-0">
              <label className="text-xs text-muted-foreground mb-1 block truncate">
                {calendarType === 'solar' ? '日' : '农历日'}
              </label>
              <select
                value={date.day}
                onChange={(e) => updateDate('day', parseInt(e.target.value))}
                className="w-full min-w-[60px] px-2 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              >
                {days.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* 时辰 */}
            <div className="min-w-0">
              <label className="text-xs text-muted-foreground mb-1 block truncate">时辰</label>
              <select
                value={date.hour}
                onChange={(e) => updateDate('hour', parseInt(e.target.value))}
                className="w-full min-w-[70px] px-2 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
              >
                {HOUR_OPTIONS.map((h) => (
                  <option key={h.value} value={h.value}>
                    {h.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* 农历日期显示（公历模式下显示） */}
          {calendarType === 'solar' && lunarDisplay && (
            <div className="flex items-center gap-2 px-2 py-1.5 bg-muted/30 rounded-lg text-xs">
              <Moon className="h-3 w-3 text-primary" />
              <span className="text-muted-foreground">农历：</span>
              <span className="font-medium">
                {lunarDisplay.lunarYearDisplay}
                {lunarDisplay.lunarMonthDisplay}
                {lunarDisplay.lunarDayDisplay}
              </span>
              {lunarDisplay.jieQi && (
                <span className="text-primary ml-1">【{lunarDisplay.jieQi}】</span>
              )}
            </div>
          )}

          {/* 性别选择 */}
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">性别</span>
            <div className="flex gap-3">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="gender"
                  checked={gender === '男'}
                  onChange={() => switchGender('男')}
                  className="accent-primary"
                />
                <span className="text-sm">男</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="gender"
                  checked={gender === '女'}
                  onChange={() => switchGender('女')}
                  className="accent-primary"
                />
                <span className="text-sm">女</span>
              </label>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleClear}
              className="flex-1 px-4 py-2 rounded border hover:bg-muted transition text-sm"
            >
              清除
            </button>
            <button
              onClick={handleCalculate}
              disabled={isCalculating}
              className="flex-1 px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90 transition text-sm disabled:opacity-50 flex items-center justify-center gap-1"
            >
              {isCalculating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  计算中
                </>
              ) : (
                '计算八字'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
