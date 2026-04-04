'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Calendar, ChevronDown, Loader2, Moon, Sun, AlertCircle, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BaziInput } from '@/types'
import { calculateBazi, BaziCalculateRequest } from '@/lib/api'
import { useChatStore, RadarData } from '@/store/chat'
import { useUserStore } from '@/store/user'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from '@/components/ui/Toast'
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

  // 当用户资料中有完整的出生信息时，初始化八字输入组件并自动计算
  useEffect(() => {
    if (hasCompleteProfileInfo && user?.birth_date && user.gender) {
      const birthDate = new Date(user.birth_date)
      const newDate = {
        year: birthDate.getFullYear(),
        month: birthDate.getMonth() + 1,
        day: birthDate.getDate(),
        hour: user.birth_time ? parseInt(user.birth_time.split(':')[0]) : 12,
        minute: user.birth_time ? parseInt(user.birth_time.split(':')[1]) : 0,
      }
      const newGender = user.gender as '男' | '女'
      
      setDate(newDate)
      setGender(newGender)
      
      // 自动计算八字并设置 userBazi（无需调用 API，直接设置）
      const baziInput: BaziInput = {
        birthYear: newDate.year,
        birthMonth: newDate.month,
        birthDay: newDate.day,
        birthHour: newDate.hour,
        gender: newGender,
      }
      setUserBazi(baziInput)
      
      console.log('[BaziInputSection] 从用户资料自动设置八字:', baziInput)
    }
  }, [hasCompleteProfileInfo, user, setUserBazi])

  // 监听用户资料更新事件并同步数据
  useEffect(() => {
    const handleProfileUpdate = (event: CustomEvent) => {
      const { birth_date, birth_time, gender } = event.detail
      
      if (birth_date && gender) {
        const birthDate = new Date(birth_date)
        if (birthDate instanceof Date && !isNaN(birthDate.getTime())) {
          const newDate = {
            year: birthDate.getFullYear(),
            month: birthDate.getMonth() + 1,
            day: birthDate.getDate(),
            hour: birth_time ? parseInt(birth_time.split(':')[0]) : 12,
            minute: birth_time ? parseInt(birth_time.split(':')[1]) : 0,
          }
          const newGender = gender as '男' | '女'
          
          setDate(newDate)
          setGender(newGender)
          
          // 自动设置 userBazi
          const baziInput: BaziInput = {
            birthYear: newDate.year,
            birthMonth: newDate.month,
            birthDay: newDate.day,
            birthHour: newDate.hour,
            gender: newGender,
          }
          setUserBazi(baziInput)
          
          console.log('[BaziInputSection] 用户资料更新，重新设置八字:', baziInput)
          
          // 自动展开
          setIsExpanded(true)
        }
      }
    }

    document.addEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    return () => {
      document.removeEventListener('userProfileUpdated', handleProfileUpdate as EventListener)
    }
  }, [setUserBazi])

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
      
      toast.success('八字计算成功！')
    } catch (e) {
      console.error('八字计算失败:', e)
      toast.error('八字计算失败，请检查输入')
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
    <div className={cn('bg-white/80 backdrop-blur-sm border border-[#E8F0EB]/60 rounded-xl p-4 shadow-sm', className)}>
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-[#3DA35D]" />
          <h3 className="font-medium text-[#2D4A38]">生辰八字</h3>
          {userBazi && (
            <span className="text-xs text-[#6B7F72]">
              {userBazi.birthYear}年{userBazi.birthMonth}月{userBazi.birthDay}日
            </span>
          )}
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggleExpanded}
          className="flex items-center gap-1 text-sm text-[#3DA35D] hover:text-[#2D7A45] transition-colors duration-200"
        >
          {userBazi ? '修改' : '输入八字'}
          <ChevronDown className={cn('h-4 w-4 transition-transform duration-200', isExpanded && 'rotate-180')} />
        </motion.button>
      </div>
      
      {/* 用户资料提醒区域 */}
      {!hasCompleteProfileInfo && isAuthenticated && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mb-4 p-3 bg-[#F9F5EC]/60 border border-[#B89B5E]/40 rounded-lg"
        >
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-[#B89B5E] mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="text-[#9A7E47] font-medium">建议完善个人资料</p>
              <p className="text-[#8A7340] mt-1">
                在个人资料中填写完整的出生信息，可以让八字计算更加准确，
                并且无需重复输入。
              </p>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  // 这里可以触发打开个人资料面板的逻辑
                  document.dispatchEvent(new CustomEvent('openUserProfile'))
                }}
                className="mt-2 inline-flex items-center gap-1 text-[#B89B5E] hover:text-[#9A7E47] text-xs font-medium transition-colors"
              >
                <User className="h-3 w-3" />
                去完善资料
              </motion.button>
            </div>
          </div>
        </motion.div>
      )}
      
      {/* 展开的输入表单 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="space-y-4 pt-3 border-t border-[#E8F0EB]/50"
          >
            {/* 历法切换 */}
            <div className="flex bg-[#F0F7F4] rounded-lg p-1">
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => switchCalendarType('solar')}
                className={cn(
                  'flex-1 py-2 text-sm rounded-md transition-all duration-200 font-medium',
                  calendarType === 'solar'
                    ? 'bg-white shadow-sm text-[#2D4A38]'
                    : 'text-[#6B7F72] hover:text-[#2D4A38]'
                )}
              >
                <Sun className="h-4 w-4 inline mr-1" />
                公历
              </motion.button>
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => switchCalendarType('lunar')}
                className={cn(
                  'flex-1 py-2 text-sm rounded-md transition-all duration-200 font-medium',
                  calendarType === 'lunar'
                    ? 'bg-white shadow-sm text-[#2D4A38]'
                    : 'text-[#6B7F72] hover:text-[#2D4A38]'
                )}
              >
                <Moon className="h-4 w-4 inline mr-1" />
                农历
              </motion.button>
            </div>

          {/* 日期选择 */}
          <div className="grid grid-cols-4 gap-2">
            {/* 年 */}
            <div className="min-w-0">
              <label className="text-xs text-[#6B7F72] mb-1 block truncate">
                {calendarType === 'solar' ? '年' : '农历年'}
              </label>
              <select
                value={date.year}
                onChange={(e) => updateDate('year', parseInt(e.target.value))}
                className="w-full min-w-[70px] px-3 py-2.5 rounded-lg border border-[#E8F0EB] bg-white text-sm text-[#2D4A38] focus:outline-none focus:ring-2 focus:ring-[#3DA35D]/30 focus:border-[#3DA35D] hover:border-[#3DA35D]/50 transition-all duration-200"
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
              <label className="text-xs text-[#6B7F72] mb-1 block truncate">
                {calendarType === 'solar' ? '月' : '农历月'}
              </label>
              <select
                value={date.month}
                onChange={(e) => updateDate('month', parseInt(e.target.value))}
                className="w-full min-w-[60px] px-3 py-2.5 rounded-lg border border-[#E8F0EB] bg-white text-sm text-[#2D4A38] focus:outline-none focus:ring-2 focus:ring-[#3DA35D]/30 focus:border-[#3DA35D] hover:border-[#3DA35D]/50 transition-all duration-200"
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
              <label className="text-xs text-[#6B7F72] mb-1 block truncate">
                {calendarType === 'solar' ? '日' : '农历日'}
              </label>
              <select
                value={date.day}
                onChange={(e) => updateDate('day', parseInt(e.target.value))}
                className="w-full min-w-[60px] px-3 py-2.5 rounded-lg border border-[#E8F0EB] bg-white text-sm text-[#2D4A38] focus:outline-none focus:ring-2 focus:ring-[#3DA35D]/30 focus:border-[#3DA35D] hover:border-[#3DA35D]/50 transition-all duration-200"
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
              <label className="text-xs text-[#6B7F72] mb-1 block truncate">时辰</label>
              <select
                value={date.hour}
                onChange={(e) => updateDate('hour', parseInt(e.target.value))}
                className="w-full min-w-[70px] px-3 py-2.5 rounded-lg border border-[#E8F0EB] bg-white text-sm text-[#2D4A38] focus:outline-none focus:ring-2 focus:ring-[#3DA35D]/30 focus:border-[#3DA35D] hover:border-[#3DA35D]/50 transition-all duration-200"
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
              <span className="text-[#6B7F72]">农历：</span>
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
            <span className="text-sm text-[#6B7F72]">性别</span>
            <div className="flex gap-3">
              <label className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#E8F0EB] cursor-pointer hover:border-[#3DA35D]/50 hover:bg-[#F5F9F7] transition-all duration-200">
                <input
                  type="radio"
                  name="gender"
                  checked={gender === '男'}
                  onChange={() => switchGender('男')}
                  className="w-4 h-4 text-[#3DA35D] focus:ring-[#3DA35D]/30 border-[#E8F0EB]"
                />
                <span className="text-sm text-[#2D4A38]">男</span>
              </label>
              <label className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#E8F0EB] cursor-pointer hover:border-[#D4656B]/50 hover:bg-[#FDF2F2] transition-all duration-200">
                <input
                  type="radio"
                  name="gender"
                  checked={gender === '女'}
                  onChange={() => switchGender('女')}
                  className="w-4 h-4 text-[#D4656B] focus:ring-[#D4656B]/30 border-[#E8F0EB]"
                />
                <span className="text-sm text-[#2D4A38]">女</span>
              </label>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-2 pt-2">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleClear}
              className="flex-1 px-4 py-2 rounded-lg border border-[#E8F0EB] hover:bg-[#F5F9F7] transition-all duration-200 text-sm text-[#4A5F52] font-medium"
            >
              清除
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleCalculate}
              disabled={isCalculating}
              className="flex-1 px-4 py-2 rounded-lg bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white hover:from-[#359454] hover:to-[#3F84B5] transition-all duration-200 text-sm disabled:opacity-50 flex items-center justify-center gap-1 font-medium shadow-sm hover:shadow-md"
            >
              {isCalculating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  计算中
                </>
              ) : (
                '计算八字'
              )}
            </motion.button>
          </div>
        </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
