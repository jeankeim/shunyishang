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
    color: '#E5E7EB',
    bgClass: 'bg-gradient-to-br from-amber-100 to-yellow-50',
    textClass: 'text-amber-700',
    accentClass: 'from-amber-400 to-yellow-500',
    ringClass: 'ring-amber-200',
    gradientClass: 'from-gray-600 to-gray-800',
    gradientFrom: '#F59E0B',
    gradientTo: '#EAB308',
  },
  '木': {
    element: '木',
    emoji: '🌿',
    color: '#4ADE80',
    bgClass: 'bg-gradient-to-br from-emerald-100 to-green-50',
    textClass: 'text-emerald-700',
    accentClass: 'from-emerald-400 to-green-500',
    ringClass: 'ring-emerald-200',
    gradientClass: 'from-green-800 to-green-950',
    gradientFrom: '#10B981',
    gradientTo: '#22C55E',
  },
  '水': {
    element: '水',
    emoji: '💧',
    color: '#60A5FA',
    bgClass: 'bg-gradient-to-br from-blue-100 to-cyan-50',
    textClass: 'text-blue-700',
    accentClass: 'from-blue-400 to-cyan-500',
    ringClass: 'ring-blue-200',
    gradientClass: 'from-blue-800 to-blue-950',
    gradientFrom: '#3B82F6',
    gradientTo: '#06B6D4',
  },
  '火': {
    element: '火',
    emoji: '🔥',
    color: '#F87171',
    bgClass: 'bg-gradient-to-br from-rose-100 to-pink-50',
    textClass: 'text-rose-700',
    accentClass: 'from-rose-400 to-pink-500',
    ringClass: 'ring-rose-200',
    gradientClass: 'from-red-800 to-red-950',
    gradientFrom: '#F43F5E',
    gradientTo: '#EC4899',
  },
  '土': {
    element: '土',
    emoji: '🌻',
    color: '#D97706',
    bgClass: 'bg-gradient-to-br from-orange-100 to-amber-50',
    textClass: 'text-orange-700',
    accentClass: 'from-orange-400 to-amber-500',
    ringClass: 'ring-orange-200',
    gradientClass: 'from-yellow-800 to-yellow-950',
    gradientFrom: '#F97316',
    gradientTo: '#F59E0B',
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
