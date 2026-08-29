/**
 * 「今天就穿它」一键日记工具
 *
 * 将一套衣橱衣物直接生成为今日穿搭日记（草稿），
 * 是推荐→日记一步转化的共享链路（每日穿搭卡片 / 搭配盲盒 / 物品详情共用）
 */

import { createDiary } from './api'

export interface OutfitPiece {
  /** 衣橱物品 ID */
  id: number
  /** 品类（用于日记关联展示） */
  category?: string
}

export type LogOutfitResult =
  | { ok: true }
  | { ok: false; reason: 'exists' | 'error'; message?: string }

/** 获取中国时区今日日期（与后端 today_cn 保持一致） */
export function todayISO(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' })
}

/**
 * 将一套衣物记录为今日穿搭日记
 *
 * @returns ok=true 创建成功；reason='exists' 表示今日已有日记
 */
export async function logOutfitAsDiary(pieces: OutfitPiece[]): Promise<LogOutfitResult> {
  if (!pieces.length) {
    return { ok: false, reason: 'error', message: '没有可记录的衣物' }
  }
  try {
    await createDiary({
      diary_date: todayISO(),
      items: pieces.map((p) => ({
        item_source: 'wardrobe',
        wardrobe_item_id: p.id,
        category: p.category,
      })),
    })
    return { ok: true }
  } catch (e) {
    const message = e instanceof Error ? e.message : '记录失败'
    if (message.includes('已有日记记录')) {
      return { ok: false, reason: 'exists' }
    }
    return { ok: false, reason: 'error', message }
  }
}
