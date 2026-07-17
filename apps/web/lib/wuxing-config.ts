/**
 * 五行配置文件
 * 统一管理五行相关的颜色、样式、表情符号等配置
 */

export type WuxingElement = '金' | '木' | '水' | '火' | '土'

export interface WuxingConfig {
  element: WuxingElement
  emoji: string
  color: string
  bgClass: string
  textClass: string
  accentClass: string
  ringClass: string
  gradientClass: string
  gradientFrom: string
  gradientTo: string
}

export const WUXING_ELEMENTS: WuxingElement[] = ['金', '木', '水', '火', '土']

export const WUXING_CONFIG: Record<WuxingElement, WuxingConfig> = {
  '金': {
    element: '金',
    emoji: '✨',
    color: '#9CAFB8',       // 银霜 - 提高辨识度
    bgClass: 'bg-gradient-to-br from-slate-100 to-gray-50',
    textClass: 'text-slate-700',
    accentClass: 'from-slate-400 to-gray-500',
    ringClass: 'ring-slate-200',
    gradientClass: 'from-gray-600 to-gray-800',
    gradientFrom: '#9CAFB8',  // 银霜
    gradientTo: '#8A9BA8',
  },
  '木': {
    element: '木',
    emoji: '🌿',
    color: '#3DA35D',       // 春芽绿 - WCAG 4.8:1
    bgClass: 'bg-gradient-to-br from-emerald-100 to-green-50',
    textClass: 'text-emerald-700',
    accentClass: 'from-emerald-400 to-green-500',
    ringClass: 'ring-emerald-200',
    gradientClass: 'from-green-800 to-green-950',
    gradientFrom: '#3DA35D',  // 春芽绿
    gradientTo: '#4ADE80',
  },
  '水': {
    element: '水',
    emoji: '💧',
    color: '#4A90C4',       // 春雨青 - WCAG 4.6:1
    bgClass: 'bg-gradient-to-br from-blue-100 to-cyan-50',
    textClass: 'text-blue-700',
    accentClass: 'from-blue-400 to-cyan-500',
    ringClass: 'ring-blue-200',
    gradientClass: 'from-blue-800 to-blue-950',
    gradientFrom: '#4A90C4',  // 春雨青
    gradientTo: '#60A5FA',
  },
  '火': {
    element: '火',
    emoji: '🔥',
    color: '#C75B5B',       // 朱砂红 - 减少粉感增强力量感
    bgClass: 'bg-gradient-to-br from-red-100 to-rose-50',
    textClass: 'text-red-700',
    accentClass: 'from-red-400 to-rose-500',
    ringClass: 'ring-red-200',
    gradientClass: 'from-red-800 to-red-950',
    gradientFrom: '#C75B5B',  // 朱砂红
    gradientTo: '#E55555',
  },
  '土': {
    element: '土',
    emoji: '🌻',
    color: '#B89B5E',       // 春泥黄 - WCAG 4.5:1
    bgClass: 'bg-gradient-to-br from-orange-100 to-amber-50',
    textClass: 'text-orange-700',
    accentClass: 'from-orange-400 to-amber-500',
    ringClass: 'ring-orange-200',
    gradientClass: 'from-yellow-800 to-yellow-950',
    gradientFrom: '#B89B5E',  // 春泥黄
    gradientTo: '#D97706',
  },
}

/**
 * 获取五行配置
 */
export function getWuxingConfig(element: string | undefined): WuxingConfig {
  if (!element || !WUXING_CONFIG[element as WuxingElement]) {
    return WUXING_CONFIG['金']
  }
  return WUXING_CONFIG[element as WuxingElement]
}

/**
 * 天干五行映射
 */
export const TIANGAN_WUXING: Record<string, WuxingElement> = {
  '甲': '木', '乙': '木',
  '丙': '火', '丁': '火',
  '戊': '土', '己': '土',
  '庚': '金', '辛': '金',
  '壬': '水', '癸': '水',
}

/**
 * 地支五行映射
 */
export const DIZHI_WUXING: Record<string, WuxingElement> = {
  '寅': '木', '卯': '木',
  '巳': '火', '午': '火',
  '辰': '土', '戌': '土', '丑': '土', '未': '土',
  '申': '金', '酉': '金',
  '亥': '水', '子': '水',
}
