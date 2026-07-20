'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, Sun, CloudSun, Sparkles, Shirt } from 'lucide-react'
import { getDailyOutfit, type DailyOutfit, type DailyOutfitItem } from '@/lib/api'
import { WUXING_CONFIG, type WuxingElement } from '@/lib/wuxing-config'
import { ItemDetailModal } from './ItemDetailModal'

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
    const next = (batchIndex + 1) % 3
    setBatchIndex(next)
    setRefreshing(true)
    fetchOutfit(next)
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
