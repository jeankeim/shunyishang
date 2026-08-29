/**
 * 衣橱展示层共享常量与纯函数
 *
 * 原先这些定义散落在 app/wardrobe/page.tsx 内部，柜体抽屉视图（WardrobeCabinet）
 * 与网格视图都要用到，抽出来避免两处色板 / 品类顺序漂移。
 */
import type { WardrobeItem } from './api'

/** 闲置徽标展示阈值与分级配色（与 WardrobeInsights 低频/冗余色板一致） */
export const IDLE_BADGE_MIN_DAYS = 30

export function idleBadgeClass(days: number): string {
  if (days >= 180) return 'bg-[#C75B5B]/85'
  if (days >= 90) return 'bg-[#B89B5E]/85'
  return 'bg-stone-500/70'
}

/** 品类抽屉顺序（与筛选栏「品类」维度词表一致；未列出的品类归入「其他」并排末尾） */
export const CATEGORY_ORDER = ['上装', '下装', '外套', '裙装', '套装', '鞋履', '配饰']
export const UNCATEGORIZED = '其他'

/** 抽屉把手上的品类刻印图标 */
export const CATEGORY_ICON: Record<string, string> = {
  上装: '👕',
  下装: '👖',
  外套: '🧥',
  裙装: '👗',
  套装: '🎽',
  鞋履: '👟',
  配饰: '👜',
  [UNCATEGORIZED]: '🧺',
}

/** 按品类分组，顺序固定（上装 → … → 配饰 → 其他），空品类不出现 */
export function groupWardrobeByCategory(items: WardrobeItem[]): { category: string; items: WardrobeItem[] }[] {
  const rank = (cat: string) => {
    const i = CATEGORY_ORDER.indexOf(cat)
    return i === -1 ? CATEGORY_ORDER.length : i
  }

  // 用普通对象累加而非 Map：项目 TS target 未开 downlevelIteration，Map 迭代器展开会报错
  const buckets: Record<string, WardrobeItem[]> = {}
  for (const item of items) {
    const cat = item.category && CATEGORY_ORDER.includes(item.category) ? item.category : UNCATEGORIZED
    ;(buckets[cat] ||= []).push(item)
  }

  return Object.keys(buckets)
    .sort((a, b) => rank(a) - rank(b))
    .map((category) => ({ category, items: buckets[category] }))
}
