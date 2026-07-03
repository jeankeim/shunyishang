import { describe, it, expect } from 'vitest'
import {
  TIAN_GAN,
  DI_ZHI,
  LUNAR_MONTHS,
  LUNAR_DAYS,
  SHI_CHEN,
  SHI_CHEN_TIME,
  solarToLunar,
  lunarToSolar,
  getShiChenIndex,
  getShiChenGanZhi,
  getLunarDateDisplay,
  getTodayLunar,
  LunarDate,
} from '@/lib/lunar'

describe('lib/lunar', () => {
  describe('constants', () => {
    it('TIAN_GAN should have 10 stems', () => {
      expect(TIAN_GAN).toHaveLength(10)
      expect(TIAN_GAN[0]).toBe('甲')
      expect(TIAN_GAN[9]).toBe('癸')
    })

    it('DI_ZHI should have 12 branches', () => {
      expect(DI_ZHI).toHaveLength(12)
      expect(DI_ZHI[0]).toBe('子')
      expect(DI_ZHI[11]).toBe('亥')
    })

    it('LUNAR_MONTHS should have 12 months', () => {
      expect(LUNAR_MONTHS).toHaveLength(12)
      expect(LUNAR_MONTHS[0]).toBe('正')
      expect(LUNAR_MONTHS[11]).toBe('腊')
    })

    it('LUNAR_DAYS should have 30 days', () => {
      expect(LUNAR_DAYS).toHaveLength(30)
      expect(LUNAR_DAYS[0]).toBe('初一')
      expect(LUNAR_DAYS[29]).toBe('三十')
    })

    it('SHI_CHEN should have 12 time periods', () => {
      expect(SHI_CHEN).toHaveLength(12)
      expect(SHI_CHEN[0]).toBe('子时')
    })

    it('SHI_CHEN_TIME should have 12 time ranges', () => {
      expect(SHI_CHEN_TIME).toHaveLength(12)
      expect(SHI_CHEN_TIME[0]).toBe('23:00-01:00')
    })
  })

  describe('solarToLunar', () => {
    it('should convert a valid solar date to lunar', () => {
      const result = solarToLunar(2024, 1, 15)
      expect(result).not.toBeNull()
      expect(result!.solarYear).toBe(2024)
      expect(result!.solarMonth).toBe(1)
      expect(result!.solarDay).toBe(15)
      expect(result!.yearGanZhi).toBeDefined()
      expect(result!.monthGanZhi).toBeDefined()
      expect(result!.dayGanZhi).toBeDefined()
      expect(result!.lunarYearDisplay).toContain('年')
      expect(result!.lunarMonthDisplay).toContain('月')
      expect(result!.lunarDayDisplay).toBeDefined()
      expect(result!.weekDayName).toBeDefined()
    })

    it('should return null for invalid date', () => {
      const result = solarToLunar(99999, 99, 99)
      expect(result).toBeNull()
    })
  })

  describe('lunarToSolar', () => {
    it('should convert a valid lunar date to solar', () => {
      const result = lunarToSolar(2024, 1, 1)
      expect(result).not.toBeNull()
      expect(result!.year).toBeGreaterThan(2000)
      expect(result!.month).toBeGreaterThanOrEqual(1)
      expect(result!.month).toBeLessThanOrEqual(12)
      expect(result!.day).toBeGreaterThanOrEqual(1)
      expect(result!.day).toBeLessThanOrEqual(31)
    })

    it('should return null for invalid date', () => {
      const result = lunarToSolar(99999, 99, 99)
      expect(result).toBeNull()
    })
  })

  describe('getShiChenIndex', () => {
    it('should return 0 for hour 23 (子时)', () => {
      expect(getShiChenIndex(23)).toBe(0)
    })

    it('should return 0 for hour 0 (子时)', () => {
      expect(getShiChenIndex(0)).toBe(0)
    })

    it('should return 1 for hour 1 (丑时)', () => {
      expect(getShiChenIndex(1)).toBe(1)
    })

    it('should return 4 for hour 8 (辰时)', () => {
      expect(getShiChenIndex(8)).toBe(4)
    })

    it('should return 6 for hour 12 (午时)', () => {
      expect(getShiChenIndex(12)).toBe(6)
    })

    it('should return 11 for hour 22 (亥时)', () => {
      expect(getShiChenIndex(22)).toBe(11)
    })
  })

  describe('getShiChenGanZhi', () => {
    it('should return correct ganZhi for 甲 day at 子时', () => {
      const result = getShiChenGanZhi('甲', 23)
      expect(result).toHaveLength(2)
      expect(result[1]).toBe('子') // 地支 should be 子 for 子时
    })

    it('should return correct ganZhi for 丙 day at 午时', () => {
      const result = getShiChenGanZhi('丙', 12)
      expect(result).toHaveLength(2)
      expect(result[1]).toBe('午')
    })

    it('should return correct ganZhi for 戊 day', () => {
      const result = getShiChenGanZhi('戊', 8)
      expect(result).toHaveLength(2)
      expect(result[1]).toBe('辰')
    })
  })

  describe('getLunarDateDisplay', () => {
    it('should format lunar date without jieqi', () => {
      const lunarDate: LunarDate = {
        solarYear: 2024,
        solarMonth: 1,
        solarDay: 15,
        lunarYear: 2024,
        lunarMonth: 1,
        lunarDay: 5,
        isLeapMonth: false,
        yearGanZhi: '甲辰',
        monthGanZhi: '乙丑',
        dayGanZhi: '丙寅',
        lunarYearDisplay: '甲辰年',
        lunarMonthDisplay: '正月',
        lunarDayDisplay: '初五',
        weekDay: 1,
        weekDayName: '一',
      }
      const result = getLunarDateDisplay(lunarDate)
      expect(result).toBe('甲辰年 正月 初五')
    })

    it('should format lunar date with jieqi', () => {
      const lunarDate: LunarDate = {
        solarYear: 2024,
        solarMonth: 2,
        solarDay: 4,
        lunarYear: 2024,
        lunarMonth: 12,
        lunarDay: 25,
        isLeapMonth: false,
        yearGanZhi: '癸卯',
        monthGanZhi: '乙丑',
        dayGanZhi: '戊戌',
        lunarYearDisplay: '癸卯年',
        lunarMonthDisplay: '腊月',
        lunarDayDisplay: '廿五',
        jieQi: '立春',
        weekDay: 0,
        weekDayName: '日',
      }
      const result = getLunarDateDisplay(lunarDate)
      expect(result).toContain('立春')
    })
  })

  describe('getTodayLunar', () => {
    it('should return lunar date for today', () => {
      const result = getTodayLunar()
      expect(result).not.toBeNull()
      expect(result!.solarYear).toBe(new Date().getFullYear())
      expect(result!.solarMonth).toBe(new Date().getMonth() + 1)
      expect(result!.solarDay).toBe(new Date().getDate())
    })
  })
})
