/**
 * 农历转换工具模块
 * 使用 lunar-javascript 库实现精确的农历转换
 * 
 * 安装: npm install lunar-javascript
 */

import { Solar, Lunar } from 'lunar-javascript'

// 天干
export const TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
// 地支
export const DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
// 农历月份（易经风格）
export const LUNAR_MONTHS = ['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '冬', '腊']
// 农历日期（易经风格）
export const LUNAR_DAYS = [
  '初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
  '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
  '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'
]
// 时辰（易经风格）
export const SHI_CHEN = [
  '子时', '丑时', '寅时', '卯时', '辰时', '巳时', 
  '午时', '未时', '申时', '酉时', '戌时', '亥时'
]
// 时辰对应的时间段
export const SHI_CHEN_TIME = [
  '23:00-01:00', '01:00-03:00', '03:00-05:00', '05:00-07:00', '07:00-09:00', '09:00-11:00',
  '11:00-13:00', '13:00-15:00', '15:00-17:00', '17:00-19:00', '19:00-21:00', '21:00-23:00'
]

export interface LunarDate {
  // 公历
  solarYear: number
  solarMonth: number
  solarDay: number
  // 农历
  lunarYear: number
  lunarMonth: number
  lunarDay: number
  isLeapMonth: boolean
  // 干支纪年
  yearGanZhi: string   // 年柱
  monthGanZhi: string  // 月柱
  dayGanZhi: string    // 日柱
  // 易经风格显示
  lunarYearDisplay: string   // 如: 甲辰年
  lunarMonthDisplay: string  // 如: 正月
  lunarDayDisplay: string    // 如: 初一
  // 节气
  jieQi?: string
  // 星期
  weekDay: number
  weekDayName: string
}

/**
 * 公历转农历
 */
export function solarToLunar(year: number, month: number, day: number): LunarDate | null {
  try {
    const solar = Solar.fromYmd(year, month, day)
    const lunar = solar.getLunar()
    
    // 获取干支
    const yearGanZhi = lunar.getYearInGanZhi()
    const monthGanZhi = lunar.getMonthInGanZhi()
    const dayGanZhi = lunar.getDayInGanZhi()
    
    // 获取节气
    const jieQi = lunar.getJieQi()
    
    return {
      solarYear: year,
      solarMonth: month,
      solarDay: day,
      lunarYear: lunar.getYear(),
      lunarMonth: lunar.getMonth(),
      lunarDay: lunar.getDay(),
      isLeapMonth: lunar.getMonth() < 0,  // 负数表示闰月
      yearGanZhi,
      monthGanZhi,
      dayGanZhi,
      lunarYearDisplay: `${yearGanZhi}年`,
      lunarMonthDisplay: formatLunarMonth(lunar.getMonth(), lunar.getMonth() < 0),
      lunarDayDisplay: formatLunarDay(lunar.getDay()),
      jieQi: jieQi || undefined,
      weekDay: solar.getWeek(),
      weekDayName: ['日', '一', '二', '三', '四', '五', '六'][solar.getWeek()],
    }
  } catch (error) {
    console.error('公历转农历失败:', error)
    return null
  }
}

/**
 * 农历转公历
 */
export function lunarToSolar(
  lunarYear: number, 
  lunarMonth: number, 
  lunarDay: number,
  isLeapMonth: boolean = false
): { year: number; month: number; day: number } | null {
  try {
    // lunar-javascript 中闰月用负数表示
    const month = isLeapMonth ? -Math.abs(lunarMonth) : lunarMonth
    const lunar = Lunar.fromYmd(lunarYear, month, lunarDay)
    const solar = lunar.getSolar()
    
    return {
      year: solar.getYear(),
      month: solar.getMonth(),
      day: solar.getDay(),
    }
  } catch (error) {
    console.error('农历转公历失败:', error)
    return null
  }
}

/**
 * 格式化农历月份（易经风格）
 */
function formatLunarMonth(month: number, isLeap: boolean): string {
  const monthName = LUNAR_MONTHS[Math.abs(month) - 1] + '月'
  return isLeap ? `闰${monthName}` : monthName
}

/**
 * 格式化农历日期（易经风格）
 */
function formatLunarDay(day: number): string {
  if (day < 1 || day > 30) return '初一'
  return LUNAR_DAYS[day - 1]
}

/**
 * 获取时辰索引
 */
export function getShiChenIndex(hour: number): number {
  // 23:00-01:00 为子时，依次类推
  if (hour === 23 || hour === 0) return 0   // 子时
  if (hour >= 1 && hour < 3) return 1       // 丑时
  if (hour >= 3 && hour < 5) return 2       // 寅时
  if (hour >= 5 && hour < 7) return 3       // 卯时
  if (hour >= 7 && hour < 9) return 4       // 辰时
  if (hour >= 9 && hour < 11) return 5      // 巳时
  if (hour >= 11 && hour < 13) return 6     // 午时
  if (hour >= 13 && hour < 15) return 7     // 未时
  if (hour >= 15 && hour < 17) return 8     // 申时
  if (hour >= 17 && hour < 19) return 9     // 酉时
  if (hour >= 19 && hour < 21) return 10    // 戌时
  return 11  // 亥时
}

/**
 * 获取时辰干支
 */
export function getShiChenGanZhi(dayGan: string, hour: number): string {
  // 时辰天干根据日干推算
  const dayGanIndex = TIAN_GAN.indexOf(dayGan)
  const shiChenIndex = getShiChenIndex(hour)
  
  // 时干 = (日干序号 % 5) * 2 + 时支序号
  const shiGanIndex = (dayGanIndex % 5) * 2 + shiChenIndex
  const shiGan = TIAN_GAN[shiGanIndex % 10]
  const shiZhi = DI_ZHI[shiChenIndex]
  
  return shiGan + shiZhi
}

/**
 * 获取完整的农历日期显示（易经风格）
 */
export function getLunarDateDisplay(lunarDate: LunarDate): string {
  const parts = [
    lunarDate.lunarYearDisplay,
    lunarDate.lunarMonthDisplay,
    lunarDate.lunarDayDisplay,
  ]
  
  if (lunarDate.jieQi) {
    parts.push(`【${lunarDate.jieQi}】`)
  }
  
  return parts.join(' ')
}

/**
 * 获取今日农历信息
 */
export function getTodayLunar(): LunarDate | null {
  const today = new Date()
  return solarToLunar(
    today.getFullYear(),
    today.getMonth() + 1,
    today.getDate()
  )
}
