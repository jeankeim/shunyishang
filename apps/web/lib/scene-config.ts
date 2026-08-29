/**
 * 场景常量与使用频率排序
 *
 * 从 WeatherSceneSection 抽出，供「常用场景」选择区与「场景急救搭配」弹窗共用，
 * 避免同一份场景表在两处各自维护导致口径漂移。
 * id 与后端 packages/utils/wuxing_rules.py::SCENE_ELEMENT_MAP 的中文 key 完全一致。
 */

import type { ComponentType } from 'react'
import { Briefcase, Coffee, Heart, Users, Plane, Dumbbell, GraduationCap, PartyPopper, Home, Gift } from 'lucide-react'

export interface SceneOption {
  /** 后端场景 key */
  id: string
  label: string
  icon: ComponentType<{ className?: string }>
  element: string
  desc: string
}

/** 场景时间段定义（用于智能排序） */
export const SCENE_TIME_SLOTS: Record<string, { start: number; end: number }> = {
  商务: { start: 9, end: 12 },
  会议: { start: 10, end: 12 },
  面试: { start: 9, end: 11 },
  日常: { start: 8, end: 18 },
  约会: { start: 18, end: 22 },
  运动: { start: 6, end: 9 },
  派对: { start: 20, end: 24 },
  旅行: { start: 7, end: 19 },
  居家: { start: 19, end: 24 },
  婚礼: { start: 10, end: 16 },
}

export const COMMON_SCENES: SceneOption[] = [
  { id: '商务', label: '商务办公', icon: Briefcase, element: '金', desc: '专业沉稳' },
  { id: '会议', label: '会议汇报', icon: Users, element: '金', desc: '正式专业' },
  { id: '面试', label: '面试求职', icon: GraduationCap, element: '金', desc: '职业干练' },
  { id: '日常', label: '休闲日常', icon: Coffee, element: '土', desc: '舒适自然' },
  { id: '约会', label: '约会聚会', icon: Heart, element: '火', desc: '浪漫活力' },
  { id: '运动', label: '运动健身', icon: Dumbbell, element: '木', desc: '活力清爽' },
  { id: '旅行', label: '出行旅游', icon: Plane, element: '木', desc: '自由灵动' },
  { id: '派对', label: '派对聚会', icon: PartyPopper, element: '火', desc: '热情闪耀' },
  { id: '居家', label: '居家休闲', icon: Home, element: '土', desc: '温暖舒适' },
  { id: '婚礼', label: '婚礼婚宴', icon: Gift, element: '火', desc: '喜庆华丽' },
]

const SCENE_USAGE_KEY = 'scene_usage_frequency'

/** 场景使用频率（localStorage 持久化） */
export function getSceneUsageFrequency(): Record<string, number> {
  try {
    const data = localStorage.getItem(SCENE_USAGE_KEY)
    return data ? JSON.parse(data) : {}
  } catch {
    return {}
  }
}

export function recordSceneUsage(sceneId: string) {
  try {
    const freq = getSceneUsageFrequency()
    freq[sceneId] = (freq[sceneId] || 0) + 1
    localStorage.setItem(SCENE_USAGE_KEY, JSON.stringify(freq))
  } catch {
    // 隐私模式下的写入失败不影响功能
  }
}

/** 当前时间段的场景排序：时段命中优先 → 使用频率 → 默认顺序 */
export function getSortedScenes(): SceneOption[] {
  const hour = new Date().getHours()
  const usageFreq = getSceneUsageFrequency()

  return [...COMMON_SCENES].sort((a, b) => {
    const aFreq = usageFreq[a.id] || 0
    const bFreq = usageFreq[b.id] || 0
    const aSlot = SCENE_TIME_SLOTS[a.id]
    const bSlot = SCENE_TIME_SLOTS[b.id]
    const aInSlot = aSlot ? (hour >= aSlot.start && hour < aSlot.end ? 1 : 0) : 0
    const bInSlot = bSlot ? (hour >= bSlot.start && hour < bSlot.end ? 1 : 0) : 0

    if (aInSlot !== bInSlot) return bInSlot - aInSlot
    if (aFreq !== bFreq) return bFreq - aFreq
    return 0
  })
}
