/**
 * 衣橱展示层共享常量与纯函数
 *
 * 原先这些定义散落在 app/wardrobe/page.tsx 内部，柜体抽屉视图（WardrobeCabinet）
 * 与网格视图都要用到，抽出来避免两处色板 / 品类顺序漂移。
 */
import type { DeclutterAction, WardrobeItem } from './api'

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

/** 断舍离三态配置（顺序即按钮顺序），暖色描边小键与柜体设计语言一致 */
export interface DeclutterOption {
  action: DeclutterAction
  /** 小键上的单字 */
  label: string
  /** 二次确认标题里的说法 */
  title: string
  /** 成功提示与战报里的动作名 */
  doneLabel: string
  color: string
  confirmText: string
}

export const DECLUTTER_OPTIONS: DeclutterOption[] = [
  { action: 'donate', label: '捐', title: '让它找新主人', doneLabel: '捐赠', color: '#3DA35D', confirmText: '确认捐赠' },
  { action: 'sell', label: '卖', title: '挂出去转让', doneLabel: '转让', color: '#B89B5E', confirmText: '确认转让' },
  { action: 'discard', label: '丢', title: '正式告别', doneLabel: '舍弃', color: '#9A8F84', confirmText: '确认舍弃' },
]

export function getDeclutterOption(action: DeclutterAction) {
  return DECLUTTER_OPTIONS.find(o => o.action === action) || DECLUTTER_OPTIONS[0]
}

/** 衣物活跃态变化（断舍离 / 撤销）后广播，衣橱页与战报卡据此刷新 */
export const WARDROBE_ACTIVE_CHANGED = 'wardrobe-active-changed'

export function notifyWardrobeActiveChanged() {
  if (typeof document !== 'undefined') {
    document.dispatchEvent(new CustomEvent(WARDROBE_ACTIVE_CHANGED))
  }
}
