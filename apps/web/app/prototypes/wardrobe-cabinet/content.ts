// 衣橱柜体原型共享 mock 数据 —— realistic 形状，与生产 WardrobeItem 字段对齐。
// 仅原型面使用，不导入生产代码。

export interface ProtoItem {
  id: number
  name: string
  category: string
  style: string
  element: '金' | '木' | '水' | '火' | '土'
}

// 五行配色（与生产 WUXING_THEME 一致）
export const ELEMENT_COLOR: Record<string, string> = {
  金: '#9CAFB8',
  木: '#3DA35D',
  水: '#4A90C4',
  火: '#C75B5B',
  土: '#B89B5E',
}

// 柜体分区（与计划一致）
export const HANG_CATEGORIES = ['上装', '外套', '裙装', '套装']
export const FOLD_CATEGORIES = ['下装', '配饰']
export const SHOE_CATEGORIES = ['鞋履']
export const ALL_CATEGORIES = [...HANG_CATEGORIES, ...FOLD_CATEGORIES, ...SHOE_CATEGORIES]

export const ITEMS: ProtoItem[] = [
  // 国风
  { id: 1, name: '墨蓝国风盘扣外套', category: '外套', style: '国风', element: '水' },
  { id: 2, name: '宋锦圆领袍连衣裙', category: '裙装', style: '国风', element: '土' },
  { id: 3, name: '白玉兰发簪', category: '配饰', style: '国风', element: '金' },
  { id: 4, name: '竹青棉麻衬衫', category: '上装', style: '国风', element: '木' },
  { id: 5, name: '朱砂红马面裙', category: '下装', style: '国风', element: '火' },
  { id: 6, name: '玄青水墨印花长衫', category: '上装', style: '国风', element: '水' },
  { id: 7, name: '青绿山水绣团扇', category: '配饰', style: '国风', element: '木' },
  // 简约
  { id: 8, name: '米白基础T恤', category: '上装', style: '简约', element: '金' },
  { id: 9, name: '浅灰直筒西裤', category: '下装', style: '简约', element: '金' },
  { id: 10, name: '燕麦色针织开衫', category: '外套', style: '简约', element: '土' },
  { id: 11, name: '象牙白衬衫裙', category: '裙装', style: '简约', element: '金' },
  { id: 12, name: '驼色休闲皮鞋', category: '鞋履', style: '简约', element: '土' },
  // 商务
  { id: 13, name: '炭灰西装套装', category: '套装', style: '商务', element: '水' },
  { id: 14, name: '藏青商务衬衫', category: '上装', style: '商务', element: '水' },
  { id: 15, name: '黑色高腰阔腿裤', category: '下装', style: '商务', element: '水' },
  { id: 16, name: '银白毛呢大衣', category: '外套', style: '商务', element: '金' },
  { id: 17, name: '黑色尖头高跟鞋', category: '鞋履', style: '商务', element: '水' },
  { id: 18, name: '鎏棕皮质短靴', category: '鞋履', style: '商务', element: '土' },
  // 休闲
  { id: 19, name: '卡其工装夹克', category: '外套', style: '休闲', element: '土' },
  { id: 20, name: '蓝白条纹休闲衬衫', category: '上装', style: '休闲', element: '水' },
  { id: 21, name: '浅蓝水洗牛仔裤', category: '下装', style: '休闲', element: '水' },
  { id: 22, name: '米白帆布鞋', category: '鞋履', style: '休闲', element: '金' },
  { id: 23, name: '咖啡帆布托特包', category: '配饰', style: '休闲', element: '土' },
  // 运动
  { id: 24, name: '玄黑速干运动T恤', category: '上装', style: '运动', element: '水' },
  { id: 25, name: '苔绿防风冲锋衣', category: '外套', style: '运动', element: '木' },
  { id: 26, name: '深灰束脚卫裤', category: '下装', style: '运动', element: '金' },
  { id: 27, name: '荧光绿跑鞋', category: '鞋履', style: '运动', element: '木' },
  { id: 28, name: '黑色棒球帽', category: '配饰', style: '运动', element: '水' },
  // 甜美
  { id: 29, name: '粉紫蝴蝶结针织衫', category: '上装', style: '甜美', element: '火' },
  { id: 30, name: '杏粉纱质连衣裙', category: '裙装', style: '甜美', element: '火' },
  { id: 31, name: '珍珠白玛丽珍鞋', category: '鞋履', style: '甜美', element: '金' },
  { id: 32, name: '绛红羊毛围巾', category: '配饰', style: '甜美', element: '火' },
]

// 风格切换条选项（全部 + 数据中存在的风格，固定顺序）
export const STYLE_TABS = ['全部', '国风', '简约', '商务', '休闲', '运动', '甜美']

export function filterByStyle(items: ProtoItem[], style: string): ProtoItem[] {
  return style === '全部' ? items : items.filter((i) => i.style === style)
}

export function countByStyle(items: ProtoItem[], style: string): number {
  return style === '全部' ? items.length : items.filter((i) => i.style === style).length
}

export function groupByCategory(items: ProtoItem[]): Record<string, ProtoItem[]> {
  const groups: Record<string, ProtoItem[]> = {}
  for (const cat of ALL_CATEGORIES) groups[cat] = []
  for (const item of items) {
    if (!groups[item.category]) groups[item.category] = []
    groups[item.category].push(item)
  }
  return groups
}
