export interface SolarTerm {
  name: string
  element: 'wood' | 'fire' | 'earth' | 'metal' | 'water'
  primaryColor: string
  bgColor: string
  cssVariable: string
}

const ELEMENT_THEME: Record<string, SolarTerm> = {
  wood: {
    name: '木',
    element: 'wood',
    primaryColor: '#22c55e',
    bgColor: '#0f172a',
    cssVariable: '142 76% 36%',
  },
  fire: {
    name: '火',
    element: 'fire',
    primaryColor: '#ef4444',
    bgColor: '#1a0f0f',
    cssVariable: '0 84% 60%',
  },
  earth: {
    name: '土',
    element: 'earth',
    primaryColor: '#a16207',
    bgColor: '#1a150f',
    cssVariable: '35 92% 33%',
  },
  metal: {
    name: '金',
    element: 'metal',
    primaryColor: '#eab308',
    bgColor: '#0f0f1a',
    cssVariable: '48 96% 53%',
  },
  water: {
    name: '水',
    element: 'water',
    primaryColor: '#3b82f6',
    bgColor: '#0a0f1a',
    cssVariable: '217 91% 60%',
  },
}

/**
 * 获取当前节气对应的五行主题
 */
export function getCurrentSolarTerm(date = new Date()): SolarTerm {
  const month = date.getMonth() + 1

  // 简化版：根据月份判断
  if (month >= 2 && month <= 4) return ELEMENT_THEME.wood
  if (month >= 5 && month <= 7) return ELEMENT_THEME.fire
  if (month >= 8 && month <= 10) return ELEMENT_THEME.metal
  if (month >= 11 || month === 1) return ELEMENT_THEME.water
  return ELEMENT_THEME.earth
}

/**
 * 将八字结果转换为雷达图数据
 */
export function baziToRadarData(bazi: any): Record<string, number> {
  if (!bazi) return {}

  const counts: Record<string, number> = { '金': 0, '木': 0, '水': 0, '火': 0, '土': 0 }

  const tianganWuxing: Record<string, string> = {
    '甲': '木', '乙': '木',
    '丙': '火', '丁': '火',
    '戊': '土', '己': '土',
    '庚': '金', '辛': '金',
    '壬': '水', '癸': '水',
  }

  const dizhiWuxing: Record<string, string> = {
    '寅': '木', '卯': '木',
    '巳': '火', '午': '火',
    '辰': '土', '戌': '土', '丑': '土', '未': '土',
    '申': '金', '酉': '金',
    '亥': '水', '子': '水',
  }

  const pillars = [bazi.year_pillar, bazi.month_pillar, bazi.day_pillar, bazi.hour_pillar]

  pillars.forEach((pillar: string) => {
    if (pillar && pillar.length === 2) {
      const [gan, zhi] = pillar.split('')
      if (tianganWuxing[gan]) counts[tianganWuxing[gan]]++
      if (dizhiWuxing[zhi]) counts[dizhiWuxing[zhi]]++
    }
  })

  const max = Math.max(...Object.values(counts), 1)
  return Object.fromEntries(
    Object.entries(counts).map(([k, v]) => [k, Math.round((v / max) * 100)])
  )
}

/**
 * 将推荐物品转换为雷达图数据
 */
export function itemsToRadarData(items: Array<{ primary_element: string }>): Record<string, number> {
  const counts: Record<string, number> = { '金': 0, '木': 0, '水': 0, '火': 0, '土': 0 }

  items.forEach((item) => {
    if (item.primary_element) {
      counts[item.primary_element] = (counts[item.primary_element] || 0) + 1
    }
  })

  const max = Math.max(...Object.values(counts), 1)
  return Object.fromEntries(
    Object.entries(counts).map(([k, v]) => [k, Math.round((v / max) * 100)])
  )
}
