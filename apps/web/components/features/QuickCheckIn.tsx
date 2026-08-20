'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ModalPortal } from '@/components/ui/ModalPortal'
import { quickCheckIn, getDailyPick } from '@/lib/api'
import { useUserStore } from '@/store/user'

// 心情选项
const MOODS = [
  { value: 'happy', emoji: '😊', label: '开心' },
  { value: 'excited', emoji: '🤩', label: '兴奋' },
  { value: 'calm', emoji: '😌', label: '平静' },
  { value: 'neutral', emoji: '😐', label: '一般' },
  { value: 'sad', emoji: '😢', label: '低落' },
]

// 五行颜色映射
const ELEMENT_COLORS: Record<string, string> = {
  '金': '#9E9E9E', '木': '#4CAF50', '水': '#2196F3',
  '火': '#FF6B6B', '土': '#D4A574',
}

interface DailyPickItem {
  id: number
  name: string
  category?: string
  image_url?: string
  primary_element?: string
  secondary_element?: string
  wear_count?: number
  is_favorite?: boolean
}

interface DailyPickData {
  item: DailyPickItem | null
  reason: string
  lucky_element: string
  lucky_color: string
  match_score: number
}

interface OutfitRecommendation {
  item_name: string
  item_id?: number
  image_url?: string
  reason: string
}

interface CheckInResult {
  diaryId: number
  created: boolean
  fortuneMatchScore?: number
  outfitRecommendation?: OutfitRecommendation | null
  streakDays?: number
}

interface QuickCheckInProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (diaryId: number) => void
  weatherInfo?: any
}

export function QuickCheckIn({ isOpen, onClose, onSuccess, weatherInfo }: QuickCheckInProps) {
  const { isAuthenticated } = useUserStore()
  const [description, setDescription] = useState('')
  const [mood, setMood] = useState('neutral')
  const [submitting, setSubmitting] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [aiTags, setAiTags] = useState<Record<string, string> | null>(null)
  const [result, setResult] = useState<CheckInResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dailyPick, setDailyPick] = useState<DailyPickData | null>(null)
  const [loadingDailyPick, setLoadingDailyPick] = useState(false)

  // 打开弹窗时加载每日精选
  useEffect(() => {
    if (!isOpen || !isAuthenticated || result) return
    let cancelled = false
    setLoadingDailyPick(true)
    getDailyPick()
      .then((data) => { if (!cancelled && data) setDailyPick(data) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingDailyPick(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, isAuthenticated])

  function handleUseDailyPick() {
    if (!dailyPick?.item) return
    const item = dailyPick.item
    const elemLabel = item.primary_element ? `（${item.primary_element}）` : ''
    setDescription(`${item.name}${elemLabel}`)
  }

  if (!isAuthenticated || !isOpen) return null

  async function handleSubmit() {
    if (!description.trim()) {
      setError('请描述今天的穿搭')
      return
    }
    setError(null)
    setAnalyzing(true)
    setSubmitting(true)

    try {
      const res = await quickCheckIn({
        description: description.trim(),
        mood,
        weather_snapshot: weatherInfo || undefined,
      })

      setAiTags(res.ai_tags || null)
      setResult({
        diaryId: res.diary_id,
        created: res.created,
        fortuneMatchScore: res.fortune_match_score,
        outfitRecommendation: res.outfit_recommendation,
        streakDays: res.streak_days,
      })

      if (res.created) {
        onSuccess?.(res.diary_id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '打卡失败')
    } finally {
      setAnalyzing(false)
      setSubmitting(false)
    }
  }

  function handleClose() {
    setDescription('')
    setMood('neutral')
    setAiTags(null)
    setResult(null)
    setError(null)
    setDailyPick(null)
    onClose()
  }

  /** 匹配度分数颜色 */
  function scoreColor(score: number): string {
    if (score >= 80) return '#10B981'
    if (score >= 60) return '#F59E0B'
    return '#9CA3AF'
  }

  /** 匹配度分数标签 — 穿搭导向表述 */
  function scoreLabel(score: number): string {
    if (score >= 80) return '宜搭配'
    if (score >= 60) return '可搭配'
    return '随性搭'
  }

  return (
    <ModalPortal>
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-x-0 top-0 h-viewport z-[70] flex items-end sm:items-center justify-center"
          onClick={handleClose}
        >
          {/* 背景遮罩 */}
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />

          {/* 弹窗内容 */}
          <motion.div
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl shadow-xl overflow-hidden max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 顶部把手（移动端） */}
            <div className="flex justify-center pt-3 sm:hidden">
              <div className="w-10 h-1 rounded-full bg-stone-300" />
            </div>

            <div className="p-5">
              {/* 标题 */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-stone-800">今日穿搭打卡</h3>
                  <p className="text-xs text-stone-500 mt-0.5">30秒记录今天的穿搭</p>
                </div>
                <button
                  onClick={handleClose}
                  className="p-2 rounded-xl hover:bg-stone-100 text-stone-400 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* 成功状态 */}
              {result ? (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="text-center py-4"
                >
                  <div className="text-5xl mb-3">{result.created ? '✅' : '📝'}</div>
                  <h4 className="text-lg font-semibold text-stone-800 mb-1">
                    {result.created ? '打卡成功！' : '今日已打卡'}
                  </h4>
                  <p className="text-sm text-stone-500 mb-4">
                    {result.created ? '已记录今日穿搭日记，并自动完成签到' : '今天已经打过卡啦'}
                  </p>

                  {/* ── 连续打卡庆祝 ──────────────────────────── */}
                  {result.created && result.streakDays !== undefined && result.streakDays >= 3 && (
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.1, type: 'spring', stiffness: 400 }}
                      className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl p-3 mb-4 border border-amber-200/60"
                    >
                      <p className="text-2xl mb-1">
                        {result.streakDays >= 30 ? '🔥' : result.streakDays >= 7 ? '⭐' : '💪'}
                      </p>
                      <p className="text-sm font-semibold text-amber-700">
                        {result.streakDays >= 30
                          ? `连续 ${result.streakDays} 天！你是穿搭修炼大师！`
                          : result.streakDays >= 7
                            ? `连续 ${result.streakDays} 天打卡，太棒了！`
                            : `已连续 ${result.streakDays} 天，继续加油！`}
                      </p>
                      {result.streakDays > 0 && result.streakDays % 7 === 0 && (
                        <p className="text-xs text-amber-600 mt-1">🎁 连续 {result.streakDays} 天奖励积分已发放</p>
                      )}
                    </motion.div>
                  )}

                  {/* 运势匹配度分数 */}
                  {result.created && result.fortuneMatchScore !== undefined && (
                    <motion.div
                      initial={{ y: 10, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ delay: 0.15 }}
                      className="bg-stone-50 rounded-2xl p-4 mb-4"
                    >
                      <p className="text-xs text-stone-500 mb-2">今日穿搭运势匹配度</p>
                      <div className="flex items-center justify-center gap-3">
                        {/* 圆形进度 */}
                        <div className="relative w-16 h-16 flex items-center justify-center">
                          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
                            <circle
                              cx="32" cy="32" r="28"
                              fill="none" stroke="#E5E7EB" strokeWidth="5"
                            />
                            <circle
                              cx="32" cy="32" r="28"
                              fill="none"
                              stroke={scoreColor(result.fortuneMatchScore)}
                              strokeWidth="5"
                              strokeLinecap="round"
                              strokeDasharray={`${(result.fortuneMatchScore / 100) * 175.9} 175.9`}
                            />
                          </svg>
                          <span
                            className="absolute text-lg font-bold"
                            style={{ color: scoreColor(result.fortuneMatchScore) }}
                          >
                            {result.fortuneMatchScore}
                          </span>
                        </div>
                        <div className="text-left">
                          <span
                            className="inline-block text-xs font-semibold px-2 py-0.5 rounded-full text-white mb-1"
                            style={{ backgroundColor: scoreColor(result.fortuneMatchScore) }}
                          >
                            {result.fortuneMatchScore >= 80 ? '✓' : ''} {scoreLabel(result.fortuneMatchScore)}
                          </span>
                          <p className="text-xs text-stone-500">
                            {result.fortuneMatchScore >= 80
                              ? '穿搭与今日运势高度契合！'
                              : result.fortuneMatchScore >= 60
                              ? '穿搭与运势较为匹配'
                              : '可尝试换用幸运色穿搭增运'}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* 衣橱单品推荐 */}
                  {result.created && result.outfitRecommendation && (
                    <motion.div
                      initial={{ y: 10, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ delay: 0.25 }}
                      className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-2xl p-3 mb-4 text-left"
                    >
                      <p className="text-xs font-medium text-emerald-700 mb-2">💡 下次穿搭推荐</p>
                      <div className="flex items-center gap-3">
                        {result.outfitRecommendation.image_url && (
                          <img
                            src={result.outfitRecommendation.image_url}
                            alt={result.outfitRecommendation.item_name}
                            className="w-12 h-12 rounded-xl object-cover border border-white shadow-sm flex-shrink-0"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-stone-700 truncate">
                            {result.outfitRecommendation.item_name}
                          </p>
                          <p className="text-xs text-stone-500 line-clamp-2">
                            {result.outfitRecommendation.reason}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* AI 识别结果 */}
                  {aiTags && Object.keys(aiTags).length > 0 && (
                    <div className="bg-stone-50 rounded-xl p-3 mb-4 text-left">
                      <p className="text-xs font-medium text-stone-600 mb-2">AI 识别结果</p>
                      <div className="flex flex-wrap gap-2">
                        {aiTags.color && (
                          <span className="text-xs px-2 py-1 bg-white rounded-lg border border-stone-200">
                            🎨 {aiTags.color}
                          </span>
                        )}
                        {aiTags.primary_element && (
                          <span
                            className="text-xs px-2 py-1 rounded-lg text-white"
                            style={{ backgroundColor: ELEMENT_COLORS[aiTags.primary_element] || '#999' }}
                          >
                            ☯ {aiTags.primary_element}
                          </span>
                        )}
                        {aiTags.material && (
                          <span className="text-xs px-2 py-1 bg-white rounded-lg border border-stone-200">
                            🧵 {aiTags.material}
                          </span>
                        )}
                        {aiTags.style && (
                          <span className="text-xs px-2 py-1 bg-white rounded-lg border border-stone-200">
                            👔 {aiTags.style}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={handleClose}
                      className="flex-1 py-2.5 rounded-xl border border-stone-200 text-sm text-stone-600 font-medium hover:bg-stone-50 transition-colors"
                    >
                      关闭
                    </button>
                    <button
                      onClick={() => {
                        handleClose()
                        window.location.hash = '#diary'
                      }}
                      className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-medium shadow-sm"
                    >
                      查看日记
                    </button>
                  </div>
                </motion.div>
              ) : (
                <>
                  {/* 每日精选推荐卡片 */}
                  {dailyPick?.item && (
                    <motion.div
                      initial={{ y: -5, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      className="mb-4 bg-[var(--brand-surface)]/60 rounded-2xl p-3 border border-[var(--brand-border)]"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-[var(--brand-body)]">🌟 今日精选推荐</span>
                        <span className="text-[10px] text-[var(--brand-subtle)]">
                          幸运{dailyPick.lucky_element}·{dailyPick.lucky_color}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        {dailyPick.item.image_url && (
                          <img
                            src={dailyPick.item.image_url}
                            alt={dailyPick.item.name}
                            className="w-11 h-11 rounded-xl object-cover border border-white shadow-sm flex-shrink-0"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-stone-700 truncate">
                            {dailyPick.item.name}
                          </p>
                          <p className="text-xs text-stone-500 line-clamp-1">{dailyPick.reason}</p>
                        </div>
                        <button
                          onClick={handleUseDailyPick}
                          className="flex-shrink-0 text-xs font-medium text-white bg-[var(--wuxing-wood)] hover:bg-[var(--wuxing-wood)]/90 px-3 py-1.5 rounded-lg transition-colors shadow-sm"
                        >
                          选这件
                        </button>
                      </div>
                    </motion.div>
                  )}

                  {/* 加载中状态 */}
                  {loadingDailyPick && (
                    <div className="mb-4 bg-[var(--brand-surface)]/40 rounded-xl p-3 flex items-center gap-2 border border-[var(--brand-border)]">
                      <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-[var(--wuxing-wood)] border-t-transparent" />
                      <span className="text-xs text-[var(--brand-subtle)]">加载今日精选...</span>
                    </div>
                  )}

                  {/* 穿搭描述输入 */}
                  <div className="mb-4">
                    <label className="text-sm font-medium text-stone-700 mb-1.5 block">
                      今天穿了什么？
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="例如：白色T恤 + 牛仔裤 + 帆布鞋"
                      className="w-full h-20 px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-sm text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 resize-none transition-all"
                      maxLength={200}
                    />
                    <div className="text-right text-[10px] text-[var(--brand-subtle)] mt-0.5">
                      {description.length}/200
                    </div>
                  </div>

                  {/* 心情选择 */}
                  <div className="mb-4">
                    <label className="text-sm font-medium text-stone-700 mb-1.5 block">
                      今天心情
                    </label>
                    <div className="flex gap-2">
                      {MOODS.map(m => (
                        <button
                          key={m.value}
                          onClick={() => setMood(m.value)}
                          className={`flex-1 py-2 rounded-xl text-center transition-all ${
                            mood === m.value
                              ? 'bg-emerald-50 border-2 border-emerald-400 shadow-sm'
                              : 'bg-stone-50 border-2 border-transparent hover:bg-stone-100'
                          }`}
                        >
                          <span className="text-lg block">{m.emoji}</span>
                          <span className="text-[10px] text-stone-600">{m.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 错误提示 */}
                  {error && (
                    <div className="mb-3 bg-red-50 border border-red-200 rounded-xl p-2.5 text-xs text-red-600">
                      {error}
                    </div>
                  )}

                  {/* AI 分析中 */}
                  {analyzing && (
                    <div className="mb-3 bg-blue-50 border border-blue-200 rounded-xl p-3 flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent" />
                      <span className="text-xs text-blue-600">AI 正在分析穿搭...</span>
                    </div>
                  )}

                  {/* 提交按钮 */}
                  <button
                    onClick={handleSubmit}
                    disabled={submitting || !description.trim()}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white font-medium text-sm shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-md transition-all active:scale-[0.98]"
                  >
                    {submitting ? '打卡中...' : '完成打卡 ✨'}
                  </button>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
    </ModalPortal>
  )
}
