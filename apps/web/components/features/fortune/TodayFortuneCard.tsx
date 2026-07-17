'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getTodayCard } from '@/lib/api'
import { useUserStore } from '@/store/user'

// 五维度配置
const DIMENSIONS: { key: string; label: string; emoji: string; color: string }[] = [
  { key: 'career', label: '事业', emoji: '💼', color: '#3DA35D' },
  { key: 'wealth', label: '财运', emoji: '💰', color: '#B89B5E' },
  { key: 'love',   label: '桃花', emoji: '💕', color: '#C75B5B' },
  { key: 'health', label: '健康', emoji: '🌿', color: '#4A90C4' },
  { key: 'study',  label: '学业', emoji: '📚', color: '#9CAFB8' },
]

// 颜色名称到实际色值的映射（用于显示色块）
const COLOR_MAP: Record<string, string> = {
  '红色': '#DC2626', '紫色': '#7C3AED', '粉色': '#EC4899',
  '橙色': '#EA580C', '黄色': '#CA8A04', '棕色': '#92400E',
  '绿色': '#16A34A', '青色': '#0D9488', '蓝色': '#2563EB',
  '黑色': '#1C1917', '白色': '#F5F5F4', '灰色': '#9CA3AF',
  '银色': '#C0C0C0', '金色': '#D4A574', '米色': '#F5E6D3',
}

// 运势等级配置
const LEVEL_CONFIG: Record<string, { label: string; gradient: string; textColor: string }> = {
  great:  { label: '大吉', gradient: 'from-emerald-400 to-teal-500',   textColor: 'text-emerald-700' },
  good:   { label: '良好', gradient: 'from-sky-400 to-blue-500',       textColor: 'text-sky-700' },
  normal: { label: '平稳', gradient: 'from-amber-400 to-orange-400',   textColor: 'text-amber-700' },
  weak:   { label: '偏弱', gradient: 'from-stone-400 to-stone-500',    textColor: 'text-stone-600' },
}

interface TodayCardData {
  fortune_date: string
  day_ganzhi: string
  day_element: string
  day_master: string
  scores: Record<string, number>
  overall_score: number
  lucky_colors: string[]
  avoid_colors: string[]
  outfit_suggestion: string
  advice_text: string
  fortune_level: string
}

interface TodayFortuneCardProps {
  onNavigateToFortune?: () => void
}

export function TodayFortuneCard({ onNavigateToFortune }: TodayFortuneCardProps) {
  const { isAuthenticated } = useUserStore()
  const [card, setCard] = useState<TodayCardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) {
      fetchCard()
    } else {
      setLoading(false)
    }
  }, [isAuthenticated])

  async function fetchCard() {
    try {
      setLoading(true)
      const data = await getTodayCard()
      setCard(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '获取运势失败')
    } finally {
      setLoading(false)
    }
  }

  // 未登录不显示
  if (!isAuthenticated) return null

  // 加载中骨架
  if (loading) {
    return (
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-4 shadow-sm border border-stone-100 animate-pulse">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-xl bg-stone-200" />
          <div className="flex-1">
            <div className="h-4 bg-stone-200 rounded w-24 mb-1.5" />
            <div className="h-3 bg-stone-100 rounded w-36" />
          </div>
        </div>
        <div className="flex gap-3">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="flex-1 h-8 bg-stone-100 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  // 错误状态
  if (error || !card) return null

  const level = LEVEL_CONFIG[card.fortune_level] || LEVEL_CONFIG.normal
  const today = new Date(card.fortune_date)
  const dateStr = `${today.getMonth() + 1}月${today.getDate()}日`
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  const weekday = `周${weekdays[today.getDay()]}`

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-sm border border-stone-100 overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
      onClick={onNavigateToFortune}
    >
      {/* 顶部渐变条 */}
      <div className={`h-1 bg-gradient-to-r ${level.gradient}`} />

      <div className="p-4">
        {/* 头部：日期 + 综合评分 */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            {/* 综合分数圆环 */}
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${level.gradient} flex items-center justify-center shadow-sm`}>
              <span className="text-lg font-bold text-white">{card.overall_score}</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-stone-800">{dateStr} {weekday}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full bg-gradient-to-r ${level.gradient} text-white font-medium`}>
                  {level.label}
                </span>
              </div>
              <p className="text-[11px] text-stone-500 mt-0.5">
                {card.day_ganzhi}日 · 五行属{card.day_element} · 日元{card.day_master}
              </p>
            </div>
          </div>
          {/* 箭头指示 */}
          <svg className="w-4 h-4 text-stone-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>

        {/* 五维度迷你进度条 */}
        <div className="flex gap-2 mb-3">
          {DIMENSIONS.map(dim => {
            const score = card.scores[dim.key] || 0
            return (
              <div key={dim.key} className="flex-1 text-center">
                <span className="text-sm">{dim.emoji}</span>
                <div className="mt-1 h-1.5 bg-stone-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${score}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: dim.color }}
                  />
                </div>
                <span className="text-[10px] text-stone-500 mt-0.5 block">{score}</span>
              </div>
            )
          })}
        </div>

        {/* 幸运色 + 忌讳色 */}
        <div className="flex items-center gap-3 mb-2.5">
          {card.lucky_colors.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-stone-500">幸运色</span>
              <div className="flex gap-1">
                {card.lucky_colors.map((color, i) => (
                  <div
                    key={i}
                    className="w-4 h-4 rounded-full border border-stone-200 shadow-sm"
                    style={{ backgroundColor: COLOR_MAP[color] || '#ccc' }}
                    title={color}
                  />
                ))}
              </div>
            </div>
          )}
          {card.avoid_colors.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-stone-500">忌讳</span>
              <div className="flex gap-1">
                {card.avoid_colors.map((color, i) => (
                  <div
                    key={i}
                    className="w-4 h-4 rounded-full border border-stone-200 shadow-sm opacity-50"
                    style={{ backgroundColor: COLOR_MAP[color] || '#ccc' }}
                    title={color}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 穿搭建议（单行） */}
        {card.outfit_suggestion && (
          <div className="bg-gradient-to-r from-emerald-50/80 to-teal-50/60 rounded-lg px-3 py-2">
            <p className="text-[11px] text-emerald-700 leading-relaxed line-clamp-2">
              <span className="font-medium">👔 </span>
              {card.outfit_suggestion}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  )
}
