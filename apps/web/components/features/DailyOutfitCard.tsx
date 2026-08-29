'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, Sun, CloudSun, Sparkles, Shirt, Dices, Check } from 'lucide-react'
import { getDailyOutfit, type DailyOutfit, type DailyOutfitItem } from '@/lib/api'
import { logOutfitAsDiary, hasTodayDiary, loggedFlagKey } from '@/lib/outfit-diary'
import { toast } from '@/components/ui/Toast'
import { WUXING_CONFIG, type WuxingElement } from '@/lib/wuxing-config'
import { ItemDetailModal } from './ItemDetailModal'
import { OutfitRoulette } from './OutfitRoulette'

/** 五行元素标签颜色映射 */
const ELEMENT_COLORS: Record<string, string> = {
  '金': '#9CAFB8',
  '木': '#3DA35D',
  '水': '#4A90C4',
  '火': '#C75B5B',
  '土': '#B89B5E',
}

interface DailyOutfitCardProps {
  /** 是否已登录 */
  isAuthenticated: boolean
  /** 前端定位城市（传递给后端确保天气一致） */
  city?: string
}

export function DailyOutfitCard({ isAuthenticated, city }: DailyOutfitCardProps) {
  const [data, setData] = useState<DailyOutfit | null>(null)
  const [loading, setLoading] = useState(false)
  const [batchIndex, setBatchIndex] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedItem, setSelectedItem] = useState<DailyOutfitItem | null>(null)
  const [error, setError] = useState(false)
  const [isPaused, setIsPaused] = useState(false) // 鼠标悬停时暂停自动轮换
  const [showRoulette, setShowRoulette] = useState(false)
  const [logging, setLogging] = useState(false)
  const [logged, setLogged] = useState(false)

  const MAX_BATCH = 5 // 增加到 5 批，更多变化

  const fetchOutfit = useCallback(async (batch = 0) => {
    if (!isAuthenticated) return
    setLoading(true)
    setError(false)
    try {
      const result = await getDailyOutfit(batch, city || undefined)
      if (result) {
        setData(result)
      } else {
        setError(true)
      }
    } catch {
      setError(true)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [isAuthenticated, city])

  useEffect(() => {
    if (isAuthenticated) {
      fetchOutfit(0)
    }
  }, [isAuthenticated, fetchOutfit])

  function handleRefresh() {
    const next = (batchIndex + 1) % MAX_BATCH
    setBatchIndex(next)
    setRefreshing(true)
    fetchOutfit(next)
  }

  // 自动轮换：每 30 秒切换一批（用户悬停时暂停）
  useEffect(() => {
    if (!isAuthenticated || refreshing || isPaused) return
    const timer = setInterval(() => {
      handleRefresh()
    }, 30000) // 30 秒
    return () => clearInterval(timer)
  }, [isAuthenticated, batchIndex, refreshing, isPaused])

  // 今日是否已有穿搭日记：本地标记只作首帧回显，挂载时向服务端核对
  // 日记被删 → 清除过期标记恢复可记；手动写日记/衣物打卡生成的日记 → 按钮同步转为已记入
  useEffect(() => {
    if (!isAuthenticated) return
    setLogged(localStorage.getItem(loggedFlagKey()) === '1')
    let cancelled = false
    hasTodayDiary()
      .then((exists) => {
        if (cancelled || exists === null) return // 查询失败回退本地标记，不阻断主流程
        setLogged(exists)
        if (exists) localStorage.setItem(loggedFlagKey(), '1')
        else localStorage.removeItem(loggedFlagKey())
      })
    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  /** 「今天就穿它」：当前整套搭配一键生成今日穿搭日记 */
  async function handleWearOutfit() {
    if (!data?.outfit_items?.length || logging) return
    // 今日已有日记则不重复记入（一天一本日记，重复关联会让穿着次数虚增），只提醒并跳转
    if (logged) {
      toast.info('今日已记入穿搭日记，去日记里看看或继续补充')
      window.location.hash = '#diary'
      return
    }
    setLogging(true)
    try {
      const res = await logOutfitAsDiary(
        data.outfit_items.map((i) => ({ id: i.id, category: i.category }))
      )
      if (res.ok) {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.success('已生成今日穿搭日记，拍照完善它')
      } else if (res.reason === 'exists') {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.info('今日已有穿搭日记，去日记里看看吧')
      } else {
        toast.error(res.message || '记录失败，请稍后重试')
        return
      }
      window.location.hash = '#diary'
    } finally {
      setLogging(false)
    }
  }

  if (!isAuthenticated) return null

  // ── 加载中 ────────────────────────────────────────────────────────────────
  if (loading && !data) {
    return (
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[var(--brand-border)]/40 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[var(--wuxing-wood)]/20 to-[var(--wuxing-water)]/20 flex items-center justify-center">
            <Shirt className="w-3.5 h-3.5 text-[var(--wuxing-wood)]" />
          </div>
          <span className="text-sm font-semibold text-[var(--brand-heading)]">今日穿搭建议</span>
        </div>
        <div className="flex items-center justify-center py-8 gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--wuxing-wood)] border-t-transparent" />
          <span className="text-sm text-[var(--brand-subtle)]">正在为你搭配...</span>
        </div>
      </div>
    )
  }

  // ── 错误状态 ──────────────────────────────────────────────────────────────
  if (error && !data) {
    return null // 静默失败，不影响首页体验
  }

  if (!data) return null

  const items = data.outfit_items || []
  const weather = data.weather_summary
  const fortune = data.fortune_summary

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white rounded-2xl shadow-sm border border-[var(--brand-border)]/40 overflow-hidden mb-4"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--wuxing-wood)]/20 to-[var(--wuxing-water)]/20 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-[var(--wuxing-wood)]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[var(--brand-heading)]">今日穿搭建议</h3>
              <p className="text-[10px] text-[var(--brand-subtle)] leading-tight">
                {weather.city} · {weather.weather} {weather.temperature}°C
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* 匹配分 */}
            {data.match_score > 0 && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                data.match_score >= 70
                  ? 'bg-emerald-50 text-emerald-600'
                  : data.match_score >= 40
                  ? 'bg-amber-50 text-amber-600'
                  : 'bg-stone-50 text-stone-500'
              }`}>
                {data.match_score}分
              </span>
            )}
            {/* 搭配盲盒 */}
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={() => setShowRoulette(true)}
              className="w-7 h-7 rounded-lg bg-[var(--brand-surface)] flex items-center justify-center hover:bg-[var(--brand-surface-active)] transition-colors"
              aria-label="搭配盲盒"
            >
              <Dices className="w-3.5 h-3.5 text-[var(--brand-subtle)]" />
            </motion.button>
            {/* 换一批 */}
            <motion.button
              whileTap={{ scale: 0.9, rotate: 180 }}
              onClick={handleRefresh}
              disabled={refreshing}
              className="w-7 h-7 rounded-lg bg-[var(--brand-surface)] flex items-center justify-center hover:bg-[var(--brand-surface-active)] transition-colors disabled:opacity-50"
              aria-label="换一批"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-[var(--brand-subtle)] ${refreshing ? 'animate-spin' : ''}`} />
            </motion.button>
          </div>
        </div>

        {/* 运势摘要条 */}
        <div className="mx-4 mb-3 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--brand-surface)]/60 border border-[var(--brand-border)]/60">
          <Sun className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
          <p className="text-xs text-[var(--brand-body)] leading-relaxed flex-1 line-clamp-1">
            {data.reasoning}
          </p>
        </div>

        {/* 衣物卡片列表 */}
        {items.length > 0 ? (
          <div className="px-4 pb-3">
            <AnimatePresence mode="wait">
              <motion.div
                key={batchIndex}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
                className="flex gap-2.5 overflow-x-auto pb-1 scrollbar-hide"
              >
                {items.map((item, idx) => (
                  <OutfitItemCard
                    key={item.id}
                    item={item}
                    index={idx}
                    onClick={() => setSelectedItem(item)}
                  />
                ))}
              </motion.div>
            </AnimatePresence>
          </div>
        ) : (
          <div className="px-4 pb-4 text-center">
            <p className="text-sm text-[var(--brand-subtle)] py-4">
              {data.reasoning || '暂无推荐，建议添加衣物到衣橱'}
            </p>
          </div>
        )}

        {/* 穿搭贴士 */}
        {data.style_tip && items.length > 0 && (
          <div className="mx-4 mb-3 flex items-start gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-[var(--wuxing-wood)]/5 to-[var(--wuxing-water)]/5 border border-[var(--wuxing-wood)]/10">
            <CloudSun className="w-3.5 h-3.5 text-[var(--wuxing-wood)] flex-shrink-0 mt-0.5" />
            <p className="text-xs text-[var(--brand-body)] leading-relaxed flex-1">
              {data.style_tip}
            </p>
          </div>
        )}

        {/* 幸运元素标签 */}
        {fortune.lucky_elements.length > 0 && (
          <div className="px-4 pb-3 flex items-center gap-1.5">
            <span className="text-[10px] text-[var(--brand-subtle)] mr-1">幸运</span>
            {fortune.lucky_elements.map((el) => (
              <span
                key={el}
                className="text-[10px] px-1.5 py-0.5 rounded-full font-medium text-white"
                style={{ backgroundColor: ELEMENT_COLORS[el] || '#999' }}
              >
                {el}
              </span>
            ))}
            {fortune.lucky_colors.length > 0 && (
              <>
                <span className="text-[10px] text-[var(--brand-subtle)] mx-1">·</span>
                {fortune.lucky_colors.slice(0, 2).map((c) => (
                  <span key={c} className="text-[10px] text-[var(--brand-subtle)]">{c}</span>
                ))}
              </>
            )}
          </div>
        )}

        {/* 「今天就穿它」：整套一键生成今日穿搭日记 */}
        {items.length > 0 && (
          <div className="px-4 pb-4">
            <motion.button
              whileTap={{ scale: 0.98 }}
              onClick={handleWearOutfit}
              disabled={logging}
              className={`w-full py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                logged
                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100'
                  : 'bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white shadow-sm hover:opacity-95 disabled:opacity-60'
              }`}
            >
              {logged ? (
                <>
                  <Check className="w-4 h-4" /> 今日已记入 · 去日记
                </>
              ) : logging ? (
                '记录中...'
              ) : (
                <>
                  <Sparkles className="w-4 h-4" /> 今天就穿它
                </>
              )}
            </motion.button>
          </div>
        )}
      </motion.div>

      {/* 物品详情弹窗（复用现有组件） */}
      {selectedItem && (
        <ItemDetailModal
          item={{
            item_code: String(selectedItem.id),
            name: selectedItem.name,
            category: selectedItem.category || '',
            primary_element: selectedItem.primary_element || '',
            secondary_element: selectedItem.secondary_element,
            image_url: selectedItem.image_url,
            final_score: selectedItem.match_score,
          }}
          onClose={() => setSelectedItem(null)}
        />
      )}

      {/* 搭配盲盒弹窗 */}
      <AnimatePresence>
        {showRoulette && <OutfitRoulette open={showRoulette} onClose={() => setShowRoulette(false)} />}
      </AnimatePresence>
    </>
  )
}

// ── 单个衣物卡片 ─────────────────────────────────────────────────────────────

interface OutfitItemCardProps {
  item: DailyOutfitItem
  index: number
  onClick: () => void
}

function OutfitItemCard({ item, index, onClick }: OutfitItemCardProps) {
  const elemColor = item.primary_element ? ELEMENT_COLORS[item.primary_element] : '#ccc'

  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.06, duration: 0.2 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className="flex-shrink-0 w-[100px] rounded-xl border border-[var(--brand-border)]/60 bg-white overflow-hidden shadow-sm hover:shadow-md transition-shadow text-left"
    >
      {/* 图片 */}
      <div className="w-full h-[100px] bg-[var(--brand-surface)] relative overflow-hidden">
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.image_url}
            alt={item.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Shirt className="w-8 h-8 text-[var(--brand-subtle)]/40" />
          </div>
        )}
        {/* 五行标签 */}
        {item.primary_element && (
          <div
            className="absolute top-1.5 left-1.5 text-[9px] px-1.5 py-0.5 rounded-full text-white font-medium"
            style={{ backgroundColor: elemColor }}
          >
            {item.primary_element}
          </div>
        )}
        {/* 收藏标记 */}
        {item.is_favorite && (
          <div className="absolute top-1.5 right-1.5 text-xs">♥</div>
        )}
      </div>

      {/* 信息 */}
      <div className="p-2">
        <p className="text-xs font-medium text-[var(--brand-heading)] line-clamp-1 leading-tight">
          {item.name}
        </p>
        {item.category && (
          <p className="text-[10px] text-[var(--brand-subtle)] mt-0.5">{item.category}</p>
        )}
      </div>
    </motion.button>
  )
}
