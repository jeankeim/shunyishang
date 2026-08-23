/**
 * 字体大小注册表 - 适老化支持
 * 通过缩放根字体大小（html font-size）实现全站 rem 字号/间距等比放大：
 * - sm（小号）：默认 16px，即当前尺寸
 * - md（中号）：18px
 * - lg（大号）：20px，适合老年人
 * 组件零改动即可全站生效，与皮肤系统（lib/skins.ts）同一模式。
 */

export type FontSizeId = 'sm' | 'md' | 'lg'

export interface FontSizeDef {
  id: FontSizeId
  name: string
  desc: string
  /** 根字体大小（px） */
  px: number
}

export const FONT_SIZES: FontSizeDef[] = [
  { id: 'sm', name: '小号', desc: '当前默认', px: 16 },
  { id: 'md', name: '中号', desc: '清晰易读', px: 18 },
  { id: 'lg', name: '大号', desc: '长辈模式', px: 20 },
]

export const DEFAULT_FONT_SIZE: FontSizeId = 'sm'

export function getFontSize(id: string): FontSizeDef {
  return FONT_SIZES.find((f) => f.id === id) ?? FONT_SIZES[0]
}

/** 将字体大小应用到 <html>：设置 data-font-size，由 globals.css 缩放根字号 */
export function applyFontSize(id: string) {
  if (typeof document === 'undefined') return
  const el = document.documentElement
  const size = getFontSize(id)
  if (size.id === 'sm') {
    // 小号即默认 16px，移除属性回落到浏览器默认
    el.removeAttribute('data-font-size')
  } else {
    el.setAttribute('data-font-size', size.id)
  }
}
