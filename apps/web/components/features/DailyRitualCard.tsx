'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getDailyRitual, getWuxingTip, getDailyPick } from '@/lib/api'
import { useUserStore } from '@/store/user'
import type { WuxingTip, DailyPick } from '@/lib/api'

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

// ============================================================
// 节气近似日期表（北半球，公历近似值，误差±1天）
// 仅列出未来几个月的节气，用于前端轻量推算
// ============================================================
const SOLAR_TERMS: Array<{ name: string; month: number; day: number; hint: string }> = [
  { name: '小寒', month: 1, day: 5,   hint: '寒气渐浓，宜穿厚实棉衣保暖' },
  { name: '大寒', month: 1, day: 20,  hint: '一年最冷时节，宜穿深色厚外套' },
  { name: '立春', month: 2, day: 4,   hint: '春回大地，可渐换轻薄春装' },
  { name: '雨水', month: 2, day: 19,  hint: '雨水增多，宜穿透气防水面料' },
  { name: '惊蛰', month: 3, day: 5,   hint: '万物复苏，宜穿明亮色彩增运' },
  { name: '春分', month: 3, day: 20,  hint: '昼夜平分，薄外套或针织衫最佳' },
  { name: '清明', month: 4, day: 4,   hint: '气清景明，踏青穿浅绿或青色最宜' },
  { name: '谷雨', month: 4, day: 19,  hint: '雨生百谷，穿透气棉麻面料舒适' },
  { name: '立夏', month: 5, day: 5,   hint: '夏意初显，可换清凉短袖薄衫' },
  { name: '小满', month: 5, day: 21,  hint: '天气渐热，穿浅色宽松衣物凉爽' },
  { name: '芒种', month: 6, day: 5,   hint: '湿热渐增，宜穿吸汗透气棉质' },
  { name: '夏至', month: 6, day: 21,  hint: '一年最长日照，轻薄防晒最重要' },
  { name: '小暑', month: 7, day: 7,   hint: '火旺土燥，宜穿透气棉麻清凉度夏' },
  { name: '大暑', month: 7, day: 23,  hint: '酷热难耐，浅色宽松衣物最消暑' },
  { name: '立秋', month: 8, day: 7,   hint: '秋意初起，可备薄外套早晚添衣' },
  { name: '处暑', month: 8, day: 23,  hint: '暑气消退，初秋穿长袖衬衫正好' },
  { name: '白露', month: 9, day: 7,   hint: '露水渐浓，早晚加件针织开衫' },
  { name: '秋分', month: 9, day: 23,  hint: '天气转凉，薄卫衣或风衣最应季' },
  { name: '寒露', month: 10, day: 8,  hint: '寒意渐浓，宜添厚实秋装保暖' },
  { name: '霜降', month: 10, day: 23, hint: '霜降来临，准备厚外套或大衣' },
  { name: '立冬', month: 11, day: 7,  hint: '冬季开始，厚实棉服或羽绒服上身' },
  { name: '小雪', month: 11, day: 22, hint: '天气渐冷，深色厚外套配围巾' },
  { name: '大雪', month: 12, day: 7,  hint: '寒冷加深，保暖大衣配厚毛衣' },
  { name: '冬至', month: 12, day: 22, hint: '一年最短日，厚实羽绒服不可少' },
]

/**
 * 查找近期节气（当前日期 ±7 天内）
 */
function findUpcomingSolarTerm(): { name: string; hint: string; daysUntil: number } | null {
  const now = new Date()
  const year = now.getFullYear()
  const todayMonthDay = now.getMonth() + 1 + now.getDate() / 100 // e.g. 7.16

  for (const term of SOLAR_TERMS) {
    const termMonthDay = term.month + term.day / 100
    const diff = termMonthDay - todayMonthDay
    // 节气在今天之后 0~7 天内，或今天就是节气当天
    if (diff >= -0.01 && diff <= 0.08) {
      const termDate = new Date(year, term.month - 1, term.day)
      const diffDays = Math.round((termDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
      if (diffDays >= -1 && diffDays <= 7) {
        return { name: term.name, hint: term.hint, daysUntil: diffDays }
      }
    }
  }
  return null
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
  onNavigateToWardrobe?: () => void
}

export function DailyRitualCard({ onCheckIn, onNavigateToFortune, onNavigateToCultivation, onNavigateToWardrobe }: DailyRitualCardProps) {
  const { isAuthenticated, isLoading: isAuthLoading } = useUserStore()
  const [data, setData] = useState<DailyRitualData | null>(null)
  const [loading, setLoading] = useState(true)

  // 新增：节气、五行百科、每日精选（异步加载，不阻塞渲染）
  const [solarTerm] = useState(() => findUpcomingSolarTerm())
  const [wuxingTip, setWuxingTip] = useState<WuxingTip | null>(null)
  const [dailyPick, setDailyPick] = useState<DailyPick | null>(null)

  useEffect(() => {
    // 仅在认证验证完成且已登录时获取数据
    if (isAuthenticated && !isAuthLoading) {
      fetchRitual()
    } else if (!isAuthenticated && !isAuthLoading) {
      setLoading(false)
    }
  }, [isAuthenticated, isAuthLoading])

  // 五行百科 + 每日精选：延迟异步加载（不阻塞 SSR，不阻塞主卡片渲染）
  useEffect(() => {
    if (!isAuthenticated || isAuthLoading) return

    // 五行穿搭百科（无需登录也可显示，但统一在已登录时加载）
    getWuxingTip()
      .then(res => {
        if (res?.title) setWuxingTip(res)
      })
      .catch(() => {}) // 静默失败

    // 每日精选（需要衣橱数据，未登录/无衣橱时返回 item=null）
    getDailyPick()
      .then(res => {
        if (res?.item) setDailyPick(res)
      })
      .catch(() => {}) // 静默失败，未登录直接不显示
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

  // 节气提示文案
  const solarTermText = solarTerm
    ? solarTerm.daysUntil <= 0
      ? `今日${solarTerm.name}，${solarTerm.hint}`
      : solarTerm.daysUntil === 1
        ? `明日${solarTerm.name}，${solarTerm.hint}`
        : `${solarTerm.name}将至（${solarTerm.daysUntil}天后），${solarTerm.hint}`
    : null

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

      {/* ── 节气提示条（近期有节气时显示） ──────────────────────────── */}
      {solarTermText && (
        <div className="mx-4 mt-3 mb-0 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200/60">
          <span className="text-sm flex-shrink-0">🌿</span>
          <p className="text-xs text-amber-700 leading-relaxed flex-1">
            {solarTermText}
          </p>
        </div>
      )}

      <div className="p-4">
        {/* 第一行：日期 + 运势等级 + 打卡状态 */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-base">{level.emoji}</span>
            <div>
              <span className="text-sm font-semibold text-stone-800">{dateStr} {weekday}</span>
              {fortune?.day_ganzhi && (
                <span className="text-xs text-stone-500 ml-1.5">
                  {fortune.day_ganzhi}日
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* 运势等级标签 */}
            {fortune && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full bg-gradient-to-r ${level.gradient} text-white font-medium cursor-pointer`}
                onClick={onNavigateToFortune}
              >
                {level.label} · {fortune.overall_score}分
              </span>
            )}
            {/* 打卡状态 */}
            {diary.checked_in_today ? (
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-medium">
                ✓ 已打卡
              </span>
            ) : (
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={onCheckIn}
                className="text-xs px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 text-white font-medium shadow-sm"
              >
                打卡
              </motion.button>
            )}
          </div>
        </div>

        {/* 第二行：核心数据网格 */}
        <div className="grid grid-cols-4 gap-2 mb-2">
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
            <p className="text-xs text-stone-500">幸运色</p>
          </div>

          {/* 日记连续 */}
          <div className="text-center">
            <p className="text-sm font-bold text-emerald-600 leading-none mb-0.5">{diary.streak_days}</p>
            <p className="text-xs text-stone-500">连续打卡</p>
          </div>

          {/* 修炼等级 */}
          <div className="text-center cursor-pointer" onClick={onNavigateToCultivation}>
            <p className="text-sm leading-none mb-0.5">{cultivation.level_icon || '🌱'}</p>
            <p className="text-xs text-stone-500">{cultivation.level}</p>
          </div>

          {/* 日记总数 */}
          <div className="text-center">
            <p className="text-sm font-bold text-stone-700 leading-none mb-0.5">{diary.total_diaries}</p>
            <p className="text-xs text-stone-500">篇日记</p>
          </div>
        </div>

        {/* 第三行：穿搭建议（如果有） */}
        {fortune?.outfit_suggestion && (
          <div
            className="bg-white/60 rounded-xl px-3 py-2 mb-2 cursor-pointer hover:bg-white/80 transition-colors"
            onClick={onNavigateToFortune}
          >
            <p className="text-xs text-stone-600 leading-relaxed">
              <span className="text-stone-400 mr-1">👔</span>
              {fortune.outfit_suggestion}
            </p>
          </div>
        )}

        {/* ── 五行穿搭小知识（异步加载） ──────────────────────────── */}
        <WuxingTipSection tip={wuxingTip} />

        {/* ── 每日精选入口卡片（异步加载） ─────────────────────────── */}
        <DailyPickSection pick={dailyPick} onNavigate={onNavigateToWardrobe} />

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
                  <span className="text-xs">{dim.emoji}</span>
                  <div className="mt-0.5 mx-auto w-full h-1.5 bg-stone-200/80 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${score}%`, backgroundColor: dim.color }}
                    />
                  </div>
                  <p className="text-[10px] text-stone-400 mt-0.5">{score}</p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </motion.div>
  )
}

// ============================================================
// 五行穿搭小知识子组件
// ============================================================
function WuxingTipSection({ tip }: { tip: WuxingTip | null }) {
  // 未加载完成或加载失败时不渲染
  if (!tip || !tip.title) return null

  // 内容摘要：截取前 80 字符
  const summary = tip.content && tip.content.length > 80
    ? tip.content.slice(0, 80) + '…'
    : tip.content || ''

  // 五行元素对应图标
  const elementEmoji: Record<string, string> = {
    '木': '🌿', '火': '🔥', '土': '🌍', '金': '✨', '水': '💧',
  }

  return (
    <div className="mb-2 bg-gradient-to-r from-emerald-50/80 to-teal-50/60 rounded-xl px-3 py-2.5 border border-emerald-100/60">
      <div className="flex items-start gap-2">
        <span className="text-sm flex-shrink-0 mt-0.5">
          {elementEmoji[tip.element] || '📖'}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[10px] px-1.5 py-0 rounded-full bg-emerald-100 text-emerald-700 font-medium">
              {tip.category || '穿搭百科'}
            </span>
            {tip.element && (
              <span className="text-[10px] text-emerald-500">· {tip.element}行</span>
            )}
          </div>
          <p className="text-xs font-medium text-stone-700 leading-snug mb-0.5 truncate">
            {tip.title}
          </p>
          {summary && (
            <p className="text-[11px] text-stone-500 leading-relaxed line-clamp-2">
              {summary}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 每日精选入口卡片子组件
// ============================================================
function DailyPickSection({ pick, onNavigate }: { pick: DailyPick | null; onNavigate?: () => void }) {
  if (!pick || !pick.item) return null

  const { item, reason } = pick

  return (
    <div
      className="mb-2 bg-white/70 rounded-xl px-3 py-2.5 border border-stone-100 cursor-pointer hover:bg-white/90 hover:shadow-sm transition-all group"
      onClick={onNavigate}
    >
      <div className="flex items-center gap-2.5">
        {/* 单品图片（如有） */}
        {item.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.image_url}
            alt={item.name}
            className="w-10 h-10 rounded-lg object-cover flex-shrink-0 border border-stone-100"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        ) : (
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 flex items-center justify-center flex-shrink-0 border border-stone-100">
            <span className="text-base">👕</span>
          </div>
        )}

        {/* 名称 + 推荐理由 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-xs font-semibold text-stone-700 truncate">
              {item.name}
            </span>
            {item.primary_element && (
              <span className="text-[10px] px-1 py-0 rounded-full bg-amber-100 text-amber-700 flex-shrink-0">
                {item.primary_element}
              </span>
            )}
          </div>
          <p className="text-[11px] text-stone-500 leading-relaxed truncate">
            {reason}
          </p>
        </div>

        {/* 箭头指示 */}
        <div className="flex-shrink-0 text-stone-300 group-hover:text-stone-500 transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  )
}
