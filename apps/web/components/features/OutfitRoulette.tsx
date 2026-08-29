'use client'

/**
 * 搭配盲盒
 *
 * 从用户衣橱随机摇出一套搭配（上装 + 下装/裙装 + 鞋履 + 0-2 件配饰），
 * 附五行加成提示；可一键「就穿这套记一笔」生成今日穿搭日记。
 * 纯前端随机逻辑，数据来自衣橱列表接口。
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Dices, X, Check, Shirt, Loader2 } from 'lucide-react'
import { getWardrobeItems, type WardrobeItem } from '@/lib/api'
import { logOutfitAsDiary, hasTodayDiary, loggedFlagKey } from '@/lib/outfit-diary'
import { toast } from '@/components/ui/Toast'

/** 五行标签配色（与 DailyOutfitCard 保持一致） */
const ELEMENT_COLORS: Record<string, string> = {
  '金': '#9CAFB8',
  '木': '#3DA35D',
  '水': '#4A90C4',
  '火': '#C75B5B',
  '土': '#B89B5E',
}

/** 五行加成提示文案 */
const ELEMENT_HINTS: Record<string, string> = {
  '金': '金气当头，宜推进事务、明确边界',
  '木': '木气生发，宜行动规划、开启新事',
  '水': '水气流转，宜沟通交流、顺水行舟',
  '火': '火气加持，宜露面展示、见客谈事',
  '土': '土气稳固，宜稳事协调、积累信任',
}

/** 计入配饰点缀的品类 */
const ACCESSORY_CATEGORIES = new Set(['配饰', '饰品', '文玩'])

const SPIN_DURATION_MS = 1200
const SPIN_TICK_MS = 70

interface OutfitRouletteProps {
  open: boolean
  onClose: () => void
}

function pickRandom<T>(list: T[]): T {
  return list[Math.floor(Math.random() * list.length)]
}

/** 摇出一套搭配；品类不足时返回 null */
function drawOutfit(items: WardrobeItem[]): WardrobeItem[] | null {
  const tops = items.filter((i) => i.category === '上装')
  const bottoms = items.filter((i) => i.category === '下装')
  const dresses = items.filter((i) => i.category === '裙装')
  const shoes = items.filter((i) => i.category === '鞋履')
  const accessories = items.filter((i) => i.category && ACCESSORY_CATEGORIES.has(i.category))

  if (!tops.length || (!bottoms.length && !dresses.length) || !shoes.length) return null

  // 裤装/裙装随机（有裙装时 40% 概率走裙装套）
  const useDress = dresses.length > 0 && (bottoms.length === 0 || Math.random() < 0.4)
  const bottom = useDress ? pickRandom(dresses) : pickRandom(bottoms)

  const outfit: WardrobeItem[] = [pickRandom(tops), bottom, pickRandom(shoes)]

  // 配饰随机 0-2 件
  if (accessories.length) {
    const n = Math.min(Math.floor(Math.random() * 3), accessories.length)
    const shuffled = [...accessories].sort(() => Math.random() - 0.5)
    outfit.push(...shuffled.slice(0, n))
  }
  return outfit
}

/** 汇总一套搭配的五行加成文案 */
function buildElementHint(outfit: WardrobeItem[]): string {
  const counts = new Map<string, number>()
  for (const item of outfit) {
    const el = item.primary_element
    if (!el) continue
    counts.set(el, (counts.get(el) || 0) + 1)
  }
  if (!counts.size) return '随心而穿，自在即好运'
  const sorted = Array.from(counts.entries()).sort((a, b) => b[1] - a[1])
  const main = sorted.slice(0, 2).map(([el]) => el).join('、')
  return `这套以「${main}」气为主 · ${ELEMENT_HINTS[sorted[0][0]] || '五行调和，诸事皆宜'}`
}

export function OutfitRoulette({ open, onClose }: OutfitRouletteProps) {
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<WardrobeItem[]>([])
  const [spinning, setSpinning] = useState(false)
  const [previewItem, setPreviewItem] = useState<WardrobeItem | null>(null)
  const [result, setResult] = useState<WardrobeItem[] | null>(null)
  const [insufficient, setInsufficient] = useState(false)
  const [logging, setLogging] = useState(false)
  const [logged, setLogged] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 打开时拉取衣橱（最多两页共 200 件）
  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const first = await getWardrobeItems({ limit: 100 })
        let all: WardrobeItem[] = first.items || []
        if (first.total > 100) {
          const second = await getWardrobeItems({ limit: 100, page: 2 })
          all = all.concat(second.items || [])
        }
        if (!cancelled) setItems(all)
      } catch {
        if (!cancelled) setItems([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open])

  // 重置状态
  useEffect(() => {
    if (!open) {
      setResult(null)
      setSpinning(false)
      setPreviewItem(null)
      setInsufficient(false)
      setLogged(false)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [open])

  // 打开时核对「今日是否已记入」：本地标记只作首帧回显，最终以服务端为准
  // （日记被删、或今日日记来自手动记录/衣物打卡，本地标记都不知道）
  useEffect(() => {
    if (!open) return
    setLogged(localStorage.getItem(loggedFlagKey()) === '1')
    let cancelled = false
    hasTodayDiary().then((exists) => {
      if (cancelled || exists === null) return // 查询失败：保留本地标记，不阻断
      setLogged(exists)
      if (exists) localStorage.setItem(loggedFlagKey(), '1')
      else localStorage.removeItem(loggedFlagKey())
    })
    return () => {
      cancelled = true
    }
  }, [open])

  const handleSpin = useCallback(() => {
    if (spinning || !items.length) return
    const outfit = drawOutfit(items)
    if (!outfit) {
      setInsufficient(true)
      setResult(null)
      return
    }
    setInsufficient(false)
    setResult(null)
    setSpinning(true)

    const startedAt = Date.now()
    timerRef.current = setInterval(() => {
      setPreviewItem(pickRandom(items))
      if (Date.now() - startedAt >= SPIN_DURATION_MS) {
        if (timerRef.current) clearInterval(timerRef.current)
        timerRef.current = null
        setSpinning(false)
        setPreviewItem(null)
        setResult(outfit)
      }
    }, SPIN_TICK_MS)
  }, [spinning, items])

  const handleLog = useCallback(async () => {
    if (!result || logging) return
    // 今日已有日记则不重复记入：一天只能有一本日记，重复关联会让穿着次数虚增。
    // 按钮保持可点，退化成提醒 + 带用户去日记页补充
    if (logged) {
      toast.info('今日已记入穿搭日记，去日记里看看或继续补充')
      window.location.hash = '#diary'
      onClose()
      return
    }
    setLogging(true)
    try {
      const res = await logOutfitAsDiary(result.map((i) => ({ id: i.id, category: i.category })))
      if (res.ok) {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.success('已记入今日穿搭日记')
      } else if (res.reason === 'exists') {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.info('今日已有穿搭日记，去日记里看看吧')
      } else {
        toast.error(res.message || '记录失败，请稍后重试')
        return
      }
      window.location.hash = '#diary'
      onClose()
    } finally {
      setLogging(false)
    }
  }, [result, logging, logged, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94 }}
        transition={{ duration: 0.22 }}
        className="relative w-full max-w-sm bg-white rounded-2xl shadow-xl p-5 max-h-[85vh] overflow-y-auto"
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--wuxing-fire)]/20 to-[var(--wuxing-earth)]/20 flex items-center justify-center">
              <Dices className="w-4.5 h-4.5 text-[var(--wuxing-fire)]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[var(--brand-heading)]">搭配盲盒</h3>
              <p className="text-[10px] text-[var(--brand-subtle)]">不知道穿什么？交给缘分</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-[var(--brand-surface)] transition-colors"
            aria-label="关闭"
          >
            <X className="w-4 h-4 text-[var(--brand-subtle)]" />
          </button>
        </div>

        {/* 加载中 */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-[var(--brand-subtle)]" />
            <span className="text-xs text-[var(--brand-subtle)]">正在翻你的衣橱...</span>
          </div>
        )}

        {/* 摇动中 / 预览帧 */}
        {!loading && spinning && previewItem && (
          <div className="flex flex-col items-center py-6">
            <motion.div
              key={previewItem.id}
              initial={{ opacity: 0.4, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-32 h-32 rounded-2xl overflow-hidden border border-[var(--brand-border)]/60 bg-[var(--brand-surface)]"
            >
              {previewItem.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={previewItem.image_url} alt={previewItem.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Shirt className="w-8 h-8 text-[var(--brand-subtle)]/40" />
                </div>
              )}
            </motion.div>
            <p className="text-xs text-[var(--brand-subtle)] mt-3 animate-pulse">正在为你摇搭配...</p>
          </div>
        )}

        {/* 结果展示 */}
        {!loading && !spinning && result && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="grid grid-cols-3 gap-2 mb-3">
              {result.map((item) => (
                <div
                  key={item.id}
                  className="rounded-xl border border-[var(--brand-border)]/60 bg-white overflow-hidden shadow-sm"
                >
                  <div className="w-full h-[84px] bg-[var(--brand-surface)] relative overflow-hidden">
                    {item.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Shirt className="w-6 h-6 text-[var(--brand-subtle)]/40" />
                      </div>
                    )}
                    {item.primary_element && (
                      <span
                        className="absolute top-1 left-1 text-[9px] px-1.5 py-0.5 rounded-full text-white font-medium"
                        style={{ backgroundColor: ELEMENT_COLORS[item.primary_element] || '#999' }}
                      >
                        {item.primary_element}
                      </span>
                    )}
                  </div>
                  <div className="p-1.5">
                    <p className="text-[10px] font-medium text-[var(--brand-heading)] line-clamp-1">{item.name}</p>
                    <p className="text-[9px] text-[var(--brand-subtle)]">{item.category}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* 五行加成提示 */}
            <div className="px-3 py-2 rounded-lg bg-gradient-to-r from-[var(--wuxing-fire)]/5 to-[var(--wuxing-earth)]/5 border border-[var(--wuxing-earth)]/15 mb-4">
              <p className="text-xs text-[var(--brand-body)] leading-relaxed">{buildElementHint(result)}</p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleSpin}
                className="flex-1 py-2.5 rounded-xl border border-[var(--brand-border)] text-sm text-[var(--brand-body)] font-medium hover:bg-[var(--brand-surface)] transition-colors"
              >
                再摇一次
              </button>
              <button
                onClick={handleLog}
                disabled={logging}
                className={`flex-1 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-1 transition-colors ${
                  logged
                    ? 'border border-[var(--brand-border)] bg-[var(--brand-surface)] text-[var(--brand-subtle)] hover:bg-[var(--brand-border)]/40'
                    : 'bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white shadow-sm hover:opacity-95 disabled:opacity-60'
                }`}
              >
                {logged ? (
                  <>
                    <Check className="w-3.5 h-3.5" /> 今日已记入 · 去日记
                  </>
                ) : logging ? (
                  '记录中...'
                ) : (
                  '就穿这套记一笔'
                )}
              </button>
            </div>
          </motion.div>
        )}

        {/* 待摇初始态 */}
        {!loading && !spinning && !result && !insufficient && (
          <div className="flex flex-col items-center py-8">
            <motion.div
              animate={{ rotate: [0, -8, 8, -5, 5, 0] }}
              transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 1.2 }}
              className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--wuxing-fire)]/15 to-[var(--wuxing-earth)]/15 flex items-center justify-center mb-4"
            >
              <Dices className="w-8 h-8 text-[var(--wuxing-fire)]" />
            </motion.div>
            <p className="text-sm text-[var(--brand-body)] mb-1">摇一摇，看看今天穿什么</p>
            <p className="text-[10px] text-[var(--brand-subtle)] mb-5">上装 + 下装/裙装 + 鞋履，也许还有配饰惊喜</p>
            <button
              onClick={handleSpin}
              className="px-8 py-2.5 rounded-xl bg-gradient-to-r from-[var(--wuxing-fire)] to-[var(--wuxing-earth)] text-white text-sm font-medium shadow-sm"
            >
              开始摇
            </button>
          </div>
        )}

        {/* 衣物不足 */}
        {!loading && !spinning && insufficient && (
          <div className="flex flex-col items-center py-8">
            <Shirt className="w-10 h-10 text-[var(--brand-subtle)]/40 mb-3" />
            <p className="text-sm text-[var(--brand-body)] text-center leading-relaxed">
              衣橱里还凑不齐一套搭配
              <br />
              <span className="text-xs text-[var(--brand-subtle)]">至少需要上装、下装（或裙装）、鞋履各一件</span>
            </p>
          </div>
        )}
      </motion.div>
    </div>
  )
}
