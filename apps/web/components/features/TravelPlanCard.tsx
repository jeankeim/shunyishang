'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface DailyPlan {
  day: number
  scene: string
  sub_scene?: string
  weather: {
    date?: string
    weather_desc?: string
    temperature_max?: number
    temperature_min?: number
  }
  items: {
    id?: number | string
    name: string
    category: string
    primary_element: string
    image_url?: string
    final_score?: number
    scene_score?: number
    wuxing_score?: number
    weather_score?: number
  }[]
  notes: string
}

interface TravelPlanData {
  destination: string
  days: number
  luggage_size: string
  daily_plans: DailyPlan[]
  luggage_summary: {
    total_items: number
    categories?: Record<string, number>
    reusable_items?: { name: string; category: string }[]
    luggage_score: number
  }
  weather_forecast: {
    date: string
    weather_desc: string
    temperature_max: number
    temperature_min: number
    humidity?: number
    wind_level?: number
  }[]
  wuxing_analysis: {
    target_elements: string[]
    weather_elements?: { date: string; weather: string; element: string }[]
    item_element_distribution: Record<string, number>
    balance_score: number
  }
  // 未提供具体出行日期时，后端不生成天气预判（用户反馈 #4）
  weather_confirmed?: boolean
  weather_note?: string
}

interface TravelPlanCardProps {
  data: TravelPlanData
  /** 点击每日衣物图片时回调（复用消息层灯箱） */
  onImageClick?: (imageUrl: string) => void
}

const ELEMENT_COLORS: Record<string, string> = {
  '金': 'from-gray-200 to-amber-200 text-amber-800',
  '木': 'from-green-200 to-emerald-200 text-emerald-800',
  '水': 'from-blue-200 to-cyan-200 text-blue-800',
  '火': 'from-red-200 to-orange-200 text-red-800',
  '土': 'from-yellow-200 to-amber-200 text-yellow-800',
}

const LUGGAGE_EMOJI: Record<string, string> = { '小': '🎒', '中': '🧳', '大': '💼' }

export function TravelPlanCard({ data, onImageClick }: TravelPlanCardProps) {
  const [expandedDay, setExpandedDay] = useState<number | null>(0)
  const [showWuxing, setShowWuxing] = useState(false)

  const scorePercent = (data.luggage_summary.luggage_score * 100).toFixed(0)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl border border-amber-200/60 overflow-hidden shadow-sm"
    >
      {/* 头部 */}
      <div className="px-5 py-4 bg-gradient-to-r from-amber-100/80 to-orange-100/60 border-b border-amber-200/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">✈️</span>
            <div>
              <h3 className="font-bold text-stone-800 text-base">
                {data.destination} · {data.days}天行程规划
              </h3>
              <p className="text-xs text-stone-500 mt-0.5">
                {LUGGAGE_EMOJI[data.luggage_size] || '🧳'} {data.luggage_size}号行李箱 · 共{data.luggage_summary.total_items}件 · 行李评分 {scorePercent}%
              </p>
            </div>
          </div>
        </div>

        {/* 天气概览：未确认出行日期时展示提示条，不渲染可能不准确的天气数据（用户反馈 #4） */}
        {data.weather_confirmed === false ? (
          <div className="mt-3 px-3 py-2 bg-white/60 rounded-lg border border-amber-200/30 flex items-start gap-2">
            <span className="text-sm leading-none mt-0.5">🌤️</span>
            <p className="text-xs text-stone-500 leading-relaxed">
              {data.weather_note || '未提供具体出行日期，暂未生成天气预判，建议出发前查看目的地天气'}
            </p>
          </div>
        ) : (
          <div className="flex gap-2 mt-3 overflow-x-auto pb-1 scrollbar-hide">
            {data.weather_forecast.map((w, i) => (
              <div
                key={i}
                className="flex-shrink-0 px-3 py-1.5 bg-white/60 rounded-lg border border-amber-200/30 text-center min-w-[72px]"
              >
                <p className="text-xs text-stone-500">第{i + 1}天</p>
                <p className="text-sm">{w.weather_desc === '晴' ? '☀️' : w.weather_desc === '多云' ? '⛅' : w.weather_desc?.includes('雨') ? '🌧️' : w.weather_desc?.includes('雪') ? '❄️' : '🌤️'}</p>
                <p className="text-xs text-stone-600 font-medium">
                  {w.temperature_min}~{w.temperature_max}°C
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 每日穿搭计划 */}
      <div className="px-5 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-stone-700">每日穿搭</span>
          <button
            onClick={() => setShowWuxing(!showWuxing)}
            className="text-xs text-amber-600 hover:text-amber-700 transition-colors"
          >
            {showWuxing ? '隐藏五行分析' : '查看五行分析'}
          </button>
        </div>
        {/* 分数含义说明 */}
        <p className="text-[11px] text-stone-400 mb-2">
          分数为综合匹配度（满分100）= 五行喜用 + 场景适配 + 天气适配，越高越适合当天
        </p>

        <div className="space-y-2">
          {data.daily_plans.map((plan, idx) => (
            <div key={idx} className="rounded-xl border border-amber-200/40 bg-white/70 overflow-hidden">
              {/* 日标题 */}
              <button
                onClick={() => setExpandedDay(expandedDay === idx ? null : idx)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-full bg-gradient-to-br from-amber-300 to-orange-300 flex items-center justify-center text-xs font-bold text-white">
                    {plan.day}
                  </span>
                  <div className="text-left">
                    <span className="text-sm font-medium text-stone-700">
                      {plan.scene}{plan.sub_scene ? `·${plan.sub_scene}` : ''}
                    </span>
                    <span className="text-xs text-stone-500 ml-2">
                      {plan.weather?.weather_desc} {plan.weather?.temperature_min}~{plan.weather?.temperature_max}°C
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-400">{plan.items.length}件</span>
                  <svg
                    className={`w-4 h-4 text-stone-400 transition-transform duration-200 ${expandedDay === idx ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {/* 展开的物品列表 */}
              <AnimatePresence>
                {expandedDay === idx && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="px-4 pb-3 space-y-2">
                      {/* 每日衣物图片直接展示在对应天下方（用户反馈），点击图片可放大 */}
                      <div className="grid grid-cols-2 gap-2">
                        {plan.items.map((item, itemIdx) => (
                          <div
                            key={itemIdx}
                            className="bg-stone-50 rounded-lg overflow-hidden border border-stone-100"
                          >
                            {item.image_url && (
                              <button
                                type="button"
                                onClick={() => onImageClick?.(item.image_url!)}
                                className="block w-full aspect-square bg-stone-100 cursor-zoom-in"
                                aria-label={`查看${item.name}大图`}
                              >
                                <img
                                  src={item.image_url}
                                  alt={item.name}
                                  loading="lazy"
                                  className="w-full h-full object-cover"
                                />
                              </button>
                            )}
                            <div className="px-2.5 py-2">
                              <div className="flex items-center gap-1.5">
                                <div className={`shrink-0 w-1.5 h-4 rounded-full bg-gradient-to-b ${ELEMENT_COLORS[item.primary_element] || 'from-stone-200 to-stone-300'}`} />
                                <p className="flex-1 min-w-0 text-xs font-medium text-stone-700 truncate">{item.name}</p>
                                {item.final_score !== undefined && (
                                  <span
                                    className="shrink-0 text-[11px] font-semibold text-amber-600 cursor-help"
                                    title={`综合匹配度 ${(item.final_score * 100).toFixed(0)} 分\n场景适配 ${((item.scene_score ?? 0) * 100).toFixed(0)} · 五行 ${((item.wuxing_score ?? 0) * 100).toFixed(0)} · 天气 ${((item.weather_score ?? 0) * 100).toFixed(0)}`}
                                  >
                                    {(item.final_score * 100).toFixed(0)}分
                                  </span>
                                )}
                              </div>
                              <p className="text-[10px] text-stone-400 mt-0.5">{item.category} · {item.primary_element}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                      {plan.notes && (
                        <p className="text-xs text-stone-500 italic mt-1">{plan.notes}</p>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>

      {/* 五行分析面板 */}
      <AnimatePresence>
        {showWuxing && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 pt-2 border-t border-amber-200/40">
              <h4 className="text-sm font-semibold text-stone-700 mb-3">行李五行分析</h4>
              
              {/* 五行分布 */}
              <div className="flex gap-2 mb-3 flex-wrap">
                {Object.entries(data.wuxing_analysis.item_element_distribution).map(([elem, count]) => (
                  <div
                    key={elem}
                    className={`px-3 py-1.5 rounded-lg bg-gradient-to-r ${ELEMENT_COLORS[elem] || 'from-stone-200 to-stone-300 text-stone-700'} text-xs font-medium`}
                  >
                    {elem} × {count}
                  </div>
                ))}
              </div>
              
              {/* 平衡度 */}
              <div className="flex items-center gap-3 text-xs text-stone-600">
                <span>五行平衡度</span>
                <div className="flex-1 h-2 bg-stone-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-400 to-orange-500 rounded-full transition-all"
                    style={{ width: `${data.wuxing_analysis.balance_score * 100}%` }}
                  />
                </div>
                <span className="font-semibold text-amber-700">
                  {(data.wuxing_analysis.balance_score * 100).toFixed(0)}%
                </span>
              </div>

              {/* 喜用神 */}
              {data.wuxing_analysis.target_elements.length > 0 && (
                <div className="flex items-center gap-2 mt-2 text-xs">
                  <span className="text-stone-500">喜用神:</span>
                  {data.wuxing_analysis.target_elements.map((elem) => (
                    <span key={elem} className={`px-2 py-0.5 rounded-full bg-gradient-to-r ${ELEMENT_COLORS[elem]} text-xs font-medium`}>
                      {elem}
                    </span>
                  ))}
                </div>
              )}

              {/* 可复用单品 */}
              {data.luggage_summary.reusable_items && data.luggage_summary.reusable_items.length > 0 && (
                <div className="mt-3 pt-2 border-t border-amber-100">
                  <p className="text-xs text-stone-500 mb-1">♻️ 百搭可复用单品:</p>
                  <div className="flex flex-wrap gap-1">
                    {data.luggage_summary.reusable_items.map((item, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 bg-stone-100 text-stone-600 rounded-full">
                        {item.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
