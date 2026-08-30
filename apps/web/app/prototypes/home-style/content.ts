// 原型共享内容 —— 三个风格方向使用完全相同的产品文案，
// 确保比较的是"风格"而不是"内容"。
export const TODAY = {
  date: '8月25日',
  weekday: '周二',
  solarTerm: '处暑',
  weather: '多云转晴 · 24–29°C',
  city: '杭州',
  scene: '早通勤',
  elementTrend: '金气渐升',
  xiyong: '水',
} as const

export interface OutfitItem {
  name: string
  color: string
  element: '金' | '木' | '水' | '火' | '土'
  reason: string
  swatch: string
}

export const OUTFIT: OutfitItem[] = [
  {
    name: '立领衬衫',
    color: '象牙白',
    element: '金',
    reason: '金生水，提亮整体气色',
    swatch: '#EFECE2',
  },
  {
    name: '阔腿长裤',
    color: '黛绿',
    element: '木',
    reason: '木气疏土，松弛有度',
    swatch: '#3D5C4E',
  },
  {
    name: '皮质乐福鞋',
    color: '檀棕',
    element: '土',
    reason: '土稳根基，落地踏实',
    swatch: '#6E4F37',
  },
  {
    name: '银饰小坠',
    color: '银霜',
    element: '金',
    reason: '点缀金气，呼应喜用',
    swatch: '#C8CCD2',
  },
]

export const WUXING_BALANCE: { element: string; value: number; swatch: string }[] = [
  { element: '金', value: 28, swatch: '#C8CCD2' },
  { element: '木', value: 16, swatch: '#5F8266' },
  { element: '水', value: 12, swatch: '#4A6B82' },
  { element: '火', value: 29, swatch: '#A85A48' },
  { element: '土', value: 15, swatch: '#9A7B55' },
]
