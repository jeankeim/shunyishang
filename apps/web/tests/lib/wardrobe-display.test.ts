import { describe, it, expect } from 'vitest'
import type { WardrobeItem } from '@/lib/api'
import {
  CATEGORY_ORDER,
  IDLE_BADGE_MIN_DAYS,
  groupWardrobeByCategory,
  idleBadgeClass,
} from '@/lib/wardrobe-display'

function makeItem(id: number, category?: string): WardrobeItem {
  return {
    id,
    user_id: 1,
    name: `衣物${id}`,
    category,
    primary_element: '木',
    is_custom: false,
    is_active: true,
    wear_count: 0,
    is_favorite: false,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  }
}

describe('groupWardrobeByCategory', () => {
  it('按固定品类顺序分组，空品类不出现', () => {
    const groups = groupWardrobeByCategory([
      makeItem(1, '鞋履'),
      makeItem(2, '上装'),
      makeItem(3, '上装'),
    ])
    expect(groups.map((g) => g.category)).toEqual(['上装', '鞋履'])
    expect(groups[0].items).toHaveLength(2)
    expect(groups[1].items).toHaveLength(1)
  })

  it('未知品类与缺失品类归入「其他」并排末尾', () => {
    const groups = groupWardrobeByCategory([
      makeItem(1, '泳装'),
      makeItem(2, undefined),
      makeItem(3, '配饰'),
    ])
    expect(groups.map((g) => g.category)).toEqual(['配饰', '其他'])
    expect(groups[1].items.map((i) => i.id)).toEqual([1, 2])
  })

  it('覆盖筛选栏「品类」维度的全部选项', () => {
    const groups = groupWardrobeByCategory(CATEGORY_ORDER.map((c, i) => makeItem(i + 1, c)))
    expect(groups.map((g) => g.category)).toEqual(CATEGORY_ORDER)
  })

  it('空列表返回空数组', () => {
    expect(groupWardrobeByCategory([])).toEqual([])
  })
})

describe('idleBadgeClass', () => {
  it('30 天为展示阈值', () => {
    expect(IDLE_BADGE_MIN_DAYS).toBe(30)
  })

  it('按闲置时长分级配色，越久越醒目', () => {
    expect(idleBadgeClass(45)).toBe('bg-stone-500/70')
    expect(idleBadgeClass(90)).toBe('bg-[#B89B5E]/85')
    expect(idleBadgeClass(180)).toBe('bg-[#C75B5B]/85')
  })
})
