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
    primaryColor: '#3DA35D',    // 春芽绿 - 与 globals.css 一致
    bgColor: '#f8faf8',
    cssVariable: '142 76% 36%',
  },
  fire: {
    name: '火',
    element: 'fire',
    primaryColor: '#C75B5B',    // 朱砂红 - 与 globals.css 一致
    bgColor: '#fdf8f8',
    cssVariable: '0 84% 60%',
  },
  earth: {
    name: '土',
    element: 'earth',
    primaryColor: '#B89B5E',    // 春泥黄 - 与 globals.css 一致
    bgColor: '#faf8f5',
    cssVariable: '35 92% 33%',
  },
  metal: {
    name: '金',
    element: 'metal',
    primaryColor: '#9CAFB8',    // 银霜 - 与 globals.css 一致
    bgColor: '#f9fafb',
    cssVariable: '48 96% 53%',
  },
  water: {
    name: '水',
    element: 'water',
    primaryColor: '#4A90C4',    // 春雨青 - 与 globals.css 一致
    bgColor: '#f8f9fc',
    cssVariable: '217 91% 60%',
  },
}

/**
 * 获取当前节气对应的五行主题
 */
export function getCurrentSolarTerm(date = new Date()): SolarTerm {
  const month = date.getMonth() + 1

  // 根据月份映射五行（参考节气与四季土）
  // 四季土（辰戌丑未）对应 1/4/7/10 月（季节交替期）
  if ([1, 4, 7, 10].includes(month)) return ELEMENT_THEME.earth
  if ([2, 3].includes(month)) return ELEMENT_THEME.wood
  if ([5, 6].includes(month)) return ELEMENT_THEME.fire
  if ([8, 9].includes(month)) return ELEMENT_THEME.metal
  return ELEMENT_THEME.water // 11, 12
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
