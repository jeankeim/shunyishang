'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getDailyRitual } from '@/lib/api'
import { useUserStore } from '@/store/user'

// 颜色名称到色值
const COLOR_MAP: Record<string, string> = {
  '红色': '#DC2626', '紫色': '#7C3AED', '粉色': '#EC4899',
  '橙色': '#EA580C', '黄色': '#CA8A04', '棕色': '#92400E',
  '绿色': '#16A34A', '青色': '#0D9488', '蓝色': '#2563EB',
  '黑色': '#1C1917', '白色': '#F5F5F4', '灰色': '#9CA3AF',
  '银色': '#C0C0C0', '金色': '#D4A574', '米色': '#F5E6D3',
}

// 运势等级配置
const LEVEL_CONFIG: Record<string, { label: string; gradient: string; emoji: string }> = {
  great:  { label: '大吉', gradient: 'from-emerald-400 to-teal-500', emoji: '🎉' },
  good:   { label: '良好', gradient: 'from-blue-400 to-cyan-500', emoji: '✨' },
  normal: { label: '平稳', gradient: 'from-amber-400 to-orange-400', emoji: '☀️' },
  weak:   { label: '偏弱', gradient: 'from-stone-400 to-stone-500', emoji: '🌙' },
}

interface DailyRitualData {
  fortune: {
    fortune_date: string
    overall_score: number
    scores: Record<string, number>
    lucky_colors: string[]
    avoid_colors: string[]
    outfit_suggestion: string
    advice_text: string
    fortune_level: string
    day_ganzhi: string
    day_element: string
  } | null
  diary: {
    checked_in_today: boolean
    streak_days: number
    total_diaries: number
  }
  cultivation: {
    level: string
    level_icon?: string
    points: number
    streak_days: number
  }
}

interface DailyRitualCardProps {
  onCheckIn?: () => void
  onNavigateToFortune?: () => void
  onNavigateToCultivation?: () => void
}

export function DailyRitualCard({ onCheckIn, onNavigateToFortune, onNavigateToCultivation }: DailyRitualCardProps) {
  const { isAuthenticated, isLoading: isAuthLoading } = useUserStore()
  const [data, setData] = useState<DailyRitualData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 仅在认证验证完成且已登录时获取数据
    if (isAuthenticated && !isAuthLoading) {
      fetchRitual()
    } else if (!isAuthenticated && !isAuthLoading) {
      setLoading(false)
    }
  }, [isAuthenticated, isAuthLoading])

  async function fetchRitual() {
    try {
      setLoading(true)
      const res = await getDailyRitual()
      setData(res)
    } catch {
      // 静默失败，不显示卡片
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated || loading) return null
  if (!data) return null

  const { fortune, diary, cultivation } = data
  const level = LEVEL_CONFIG[fortune?.fortune_level || 'normal'] || LEVEL_CONFIG.normal

  const today = new Date()
  const dateStr = `${today.getMonth() + 1}月${today.getDate()}日`
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  const weekday = `周${weekdays[today.getDay()]}`

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl overflow-hidden shadow-sm border border-stone-100"
      style={{
        background: 'linear-gradient(135deg, #FEFDF8 0%, #F8F5EC 40%, #F0EDE4 100%)',
      }}
    >
      {/* 顶部运势条 */}
      <div className={`h-1 bg-gradient-to-r ${level.gradient}`} />

      <div className="p-4">
        {/* 第一行：日期 + 运势等级 + 打卡状态 */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">{level.emoji}</span>
            <div>
              <span className="text-sm font-semibold text-stone-800">{dateStr} {weekday}</span>
              {fortune?.day_ganzhi && (
                <span className="text-[10px] text-stone-500 ml-1.5">
                  {fortune.day_ganzhi}日
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* 运势等级标签 */}
            {fortune && (
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r ${level.gradient} text-white font-medium cursor-pointer`}
                onClick={onNavigateToFortune}
              >
                {level.label} · {fortune.overall_score}分
              </span>
            )}
            {/* 打卡状态 */}
            {diary.checked_in_today ? (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">
                ✓ 已打卡
              </span>
            ) : (
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={onCheckIn}
                className="text-[10px] px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 text-white font-medium shadow-sm"
              >
                打卡
              </motion.button>
            )}
          </div>
        </div>

        {/* 第二行：核心数据网格 */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          {/* 幸运色 */}
          <div className="text-center">
            <div className="flex justify-center gap-0.5 mb-1">
              {(fortune?.lucky_colors || []).slice(0, 3).map((c, i) => (
                <div
                  key={i}
                  className="w-3.5 h-3.5 rounded-full border border-white shadow-sm"
                  style={{ backgroundColor: COLOR_MAP[c] || '#ccc' }}
                  title={c}
                />
              ))}
              {(!fortune?.lucky_colors?.length) && <div className="w-3.5 h-3.5 rounded-full bg-stone-200" />}
            </div>
            <p className="text-[9px] text-stone-500">幸运色</p>
          </div>

          {/* 日记连续 */}
          <div className="text-center">
            <p className="text-sm font-bold text-emerald-600 leading-none mb-0.5">{diary.streak_days}</p>
            <p className="text-[9px] text-stone-500">连续打卡</p>
          </div>

          {/* 修炼等级 */}
          <div className="text-center cursor-pointer" onClick={onNavigateToCultivation}>
            <p className="text-sm leading-none mb-0.5">{cultivation.level_icon || '🌱'}</p>
            <p className="text-[9px] text-stone-500">{cultivation.level}</p>
          </div>

          {/* 日记总数 */}
          <div className="text-center">
            <p className="text-sm font-bold text-stone-700 leading-none mb-0.5">{diary.total_diaries}</p>
            <p className="text-[9px] text-stone-500">篇日记</p>
          </div>
        </div>

        {/* 第三行：穿搭建议（如果有） */}
        {fortune?.outfit_suggestion && (
          <div
            className="bg-white/60 rounded-xl px-3 py-2 mb-2 cursor-pointer hover:bg-white/80 transition-colors"
            onClick={onNavigateToFortune}
          >
            <p className="text-[11px] text-stone-600 leading-relaxed">
              <span className="text-stone-400 mr-1">👔</span>
              {fortune.outfit_suggestion}
            </p>
          </div>
        )}

        {/* 底部：五维度迷你分数条 */}
        {fortune?.scores && (
          <div className="flex gap-1.5">
            {Object.entries(fortune.scores).map(([key, score]) => {
              const dimConfig: Record<string, { emoji: string; color: string }> = {
                career: { emoji: '💼', color: '#3DA35D' },
                wealth: { emoji: '💰', color: '#B89B5E' },
                love:   { emoji: '💕', color: '#D4656B' },
                health: { emoji: '🌿', color: '#4A90C4' },
                study:  { emoji: '📚', color: '#8B6DB0' },
              }
              const dim = dimConfig[key] || { emoji: '·', color: '#999' }
              return (
                <div key={key} className="flex-1 text-center">
                  <span className="text-[10px]">{dim.emoji}</span>
                  <div className="mt-0.5 mx-auto w-full h-1.5 bg-stone-200/80 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${score}%`, backgroundColor: dim.color }}
                    />
                  </div>
                  <p className="text-[8px] text-stone-400 mt-0.5">{score}</p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </motion.div>
  )
}
