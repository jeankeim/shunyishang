/**
 * lunar-javascript 类型声明
 * npm: https://www.npmjs.com/package/lunar-javascript
 * 文档: https://6tail.cn/lunar.html
 */

declare module 'lunar-javascript' {
  // ============ Solar 公历类 ============
  export class Solar {
    static fromYmd(year: number, month: number, day: number): Solar
    static fromYmdHms(
      year: number,
      month: number,
      day: number,
      hour: number,
      minute: number,
      second: number
    ): Solar
    static fromDate(date: Date): Solar

    getYear(): number
    getMonth(): number
    getDay(): number
    getHour(): number
    getMinute(): number
    getSecond(): number
    getWeek(): number
    getLunar(): Lunar
    toString(): string
  }

  // ============ Lunar 农历类 ============
  export class Lunar {
    static fromYmd(year: number, month: number, day: number): Lunar
    static fromYmdHms(
      year: number,
      month: number,
      day: number,
      hour: number,
      minute: number,
      second: number
    ): Lunar

    getYear(): number
    getMonth(): number  // 负数表示闰月
    getDay(): number
    getHour(): number
    getMinute(): number
    getSecond(): number
    getSolar(): Solar

    // 干支
    getYearInGan(): string
    getYearInZhi(): string
    getYearInGanZhi(): string
    getMonthInGan(): string
    getMonthInZhi(): string
    getMonthInGanZhi(): string
    getDayInGan(): string
    getDayInZhi(): string
    getDayInGanZhi(): string
    getTimeInGan(): string
    getTimeInZhi(): string
    getTimeInGanZhi(): string

    // 节气
    getJieQi(): string | null
    getPrevJie(): JieQi | null
    getPrevQi(): JieQi | null
    getCurrentJieQi(): JieQi | null

    // 其他
    getYearShengXiao(): string
    getFestivals(): string[]
    getOtherFestivals(): string[]
    toString(): string
  }

  // ============ JieQi 节气类 ============
  export class JieQi {
    getName(): string
    getSolar(): Solar
    toString(): string
  }

  // ============ 其他导出 ============
  export const SolarUtil: {
    fromYmd(year: number, month: number, day: number): Solar
    getWeek(year: number, month: number, day: number): number
    getDaysInMonth(year: number, month: number): number
    isLeapYear(year: number): boolean
  }

  export const LunarUtil: {
    fromYmd(year: number, month: number, day: number): Lunar
    getJieQi(): string[]
  }
}
