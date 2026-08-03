'use client'

import { motion } from 'framer-motion'
import type { DailyFortune } from '@/types'

const DIMENSION_LABELS: Record<string, { label: string; emoji: string }> = {
  career: { label: '事业', emoji: '💼' },
  wealth: { label: '财运', emoji: '💰' },
  love: { label: '桃花', emoji: '💕' },
  health: { label: '健康', emoji: '🌿' },
  study: { label: '学业', emoji: '📚' },
}

interface FortuneCardProps {
  fortune: DailyFortune
  onRegenerate?: () => void
}

export function FortuneCard({ fortune, onRegenerate }: FortuneCardProps) {
  const date = new Date(fortune.fortune_date)
  const dateStr = `${date.getMonth() + 1}月${date.getDate()}日`
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  const weekday = `周${weekdays[date.getDay()]}`

  const scoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600'
    if (score >= 60) return 'text-amber-500'
    return 'text-stone-500'
  }

  const overallColor = (score: number) => {
    if (score >= 80) return 'from-emerald-400 to-teal-500'
    if (score >= 60) return 'from-amber-400 to-orange-400'
    return 'from-stone-400 to-stone-500'
  }

  const huangli = fortune.huangli
  const ai = fortune.ai_narrative

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100 space-y-4"
    >
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-stone-800">
            {dateStr} {weekday} 运势
          </h3>
          <p className="text-xs text-stone-500 mt-0.5">
            {fortune.bazi_snapshot?.target_day_ganzhi || ''}日 · 基于八字五行分析
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${overallColor(fortune.overall_score)} flex items-center justify-center shadow-sm`}>
            <span className="text-xl font-bold text-white">{fortune.overall_score}</span>
          </div>
        </div>
      </div>

      {/* 五维度分数 */}
      <div className="grid grid-cols-5 gap-2">
        {Object.entries(fortune.scores).map(([key, score]) => {
          const dim = DIMENSION_LABELS[key]
          return (
            <div key={key} className="text-center">
              <span className="text-lg">{dim?.emoji}</span>
              <p className="text-[10px] text-stone-500 mt-0.5">{dim?.label}</p>
              <p className={`text-sm font-bold ${scoreColor(score)}`}>{score}</p>
            </div>
          )
        })}
      </div>

      {/* ── AI 个性化叙事 ──────────────────────────── */}
      {ai?.overview && (
        <div className="bg-gradient-to-br from-violet-50/60 to-purple-50/40 rounded-xl p-4 border border-violet-100/50">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm">🔮</span>
            <span className="text-xs font-semibold text-violet-700">今日格局</span>
          </div>
          <p className="text-sm text-stone-700 leading-relaxed">{ai.overview}</p>
        </div>
      )}

      {/* ── 黄历宜忌 ──────────────────────────── */}
      {huangli && (huangli.yi?.length > 0 || huangli.ji?.length > 0) && (
        <div className="grid grid-cols-2 gap-3">
          {/* 宜 */}
          <div className="bg-emerald-50/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-xs">✅</span>
              <span className="text-xs font-semibold text-emerald-700">宜</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {huangli.yi?.slice(0, 4).map((item, i) => (
                <span key={i} className="px-2 py-0.5 bg-white/80 rounded-md text-xs text-emerald-700">
                  {item}
                </span>
              ))}
            </div>
          </div>
          {/* 忌 */}
          <div className="bg-red-50/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-xs">⚠️</span>
              <span className="text-xs font-semibold text-red-600">忌</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {huangli.ji?.slice(0, 4).map((item, i) => (
                <span key={i} className="px-2 py-0.5 bg-white/80 rounded-md text-xs text-red-600">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── 冲煞 + 节气提示 ──────────────────────────── */}
      {huangli && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {huangli.chong_sha && (
            <span className="px-2 py-1 bg-amber-50 rounded-lg text-amber-700">
              ⚡ {huangli.chong_sha}
            </span>
          )}
          {huangli.solar_term && (
            <span className="px-2 py-1 bg-teal-50 rounded-lg text-teal-700">
              🌿 今日{huangli.solar_term}
            </span>
          )}
          {!huangli.solar_term && huangli.next_solar_term && huangli.days_to_next_term > 0 && huangli.days_to_next_term <= 7 && (
            <span className="px-2 py-1 bg-teal-50/60 rounded-lg text-teal-600">
              🌱 {huangli.days_to_next_term}天后{huangli.next_solar_term}
            </span>
          )}
        </div>
      )}

      {/* ── AI 分维度提示 ──────────────────────────── */}
      {ai && (ai.career_tip || ai.love_tip || ai.health_tip) && (
        <div className="space-y-2">
          {ai.career_tip && (
            <div className="flex items-start gap-2 text-xs">
              <span className="flex-shrink-0 mt-0.5">💼</span>
              <p className="text-stone-600">{ai.career_tip}</p>
            </div>
          )}
          {ai.love_tip && (
            <div className="flex items-start gap-2 text-xs">
              <span className="flex-shrink-0 mt-0.5">❤️</span>
              <p className="text-stone-600">{ai.love_tip}</p>
            </div>
          )}
          {ai.health_tip && (
            <div className="flex items-start gap-2 text-xs">
              <span className="flex-shrink-0 mt-0.5">🌿</span>
              <p className="text-stone-600">{ai.health_tip}</p>
            </div>
          )}
        </div>
      )}

      {/* ── AI 今日宜忌行动 ──────────────────────────── */}
      {ai && (ai.lucky_action || ai.avoid_action) && (
        <div className="grid grid-cols-2 gap-3">
          {ai.lucky_action && (
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-3 border border-emerald-100/50">
              <p className="text-[10px] text-emerald-600 font-medium mb-0.5">今日宜</p>
              <p className="text-xs text-stone-700 leading-relaxed">{ai.lucky_action}</p>
            </div>
          )}
          {ai.avoid_action && (
            <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl p-3 border border-red-100/50">
              <p className="text-[10px] text-red-500 font-medium mb-0.5">今日忌</p>
              <p className="text-xs text-stone-700 leading-relaxed">{ai.avoid_action}</p>
            </div>
          )}
        </div>
      )}

      {/* ── 十二时辰气场参考 ──────────────────────────── */}
      {huangli?.hour_luck && huangli.hour_luck.length > 0 && (
        <div>
          <p className="text-xs text-stone-500 mb-2">⏰ 十二时辰气场参考</p>
          <div className="grid grid-cols-6 gap-1">
            {huangli.hour_luck.map((h, i) => (
              <div
                key={i}
                className={`text-center py-1.5 rounded-lg text-[10px] ${
                  h.lucky === '吉'
                    ? 'bg-emerald-50 text-emerald-700'
                    : h.lucky === '凶'
                    ? 'bg-red-50 text-red-600'
                    : 'bg-stone-50 text-stone-500'
                }`}
              >
                <p className="font-medium">{h.hour.split('(')[0]}</p>
                <p className="opacity-70">{h.lucky === '吉' ? '宜' : h.lucky === '凶' ? '慎' : h.lucky}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 穿搭建议 */}
      {fortune.outfit_suggestion && (
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-3">
          <p className="text-xs font-medium text-emerald-700 mb-1">👔 今日穿搭建议</p>
          <p className="text-xs text-emerald-600 leading-relaxed">{fortune.outfit_suggestion}</p>
        </div>
      )}

      {/* 免责声明 */}
      <p className="text-[10px] text-stone-400 text-center pt-1">
        ⚠️ 以上内容为基于五行文化的穿搭参考建议，仅供娱乐参考
      </p>

      {/* 重新生成 */}
      {onRegenerate && (
        <motion.button
          whileTap={{ scale: 0.98 }}
          onClick={onRegenerate}
          className="w-full py-2.5 rounded-xl border border-stone-200 text-xs text-stone-600 font-medium hover:bg-stone-50 transition-colors"
        >
          🔄 重新生成运势
        </motion.button>
      )}
    </motion.div>
  )
}
