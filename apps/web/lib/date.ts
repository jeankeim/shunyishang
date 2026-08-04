/**
 * 本地时区日期工具
 *
 * 注意：禁止使用 new Date().toISOString().split('T')[0] 取"今天"——
 * toISOString() 按 UTC 计算，北京时间 00:00~08:00 会拿到前一天的日期，
 * 导致日记日期无法选择今天、签到状态误判等问题。
 */

/** 将 Date 格式化为本地时区的 YYYY-MM-DD */
export function formatLocalDate(d: Date = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 本地时区的今天（YYYY-MM-DD） */
export function todayLocal(): string {
  return formatLocalDate(new Date())
}

/** 解析 YYYY-MM-DD 为本地时间 00:00 的 Date（避免 new Date('YYYY-MM-DD') 按 UTC 解析偏移） */
export function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}
