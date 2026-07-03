'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FortuneCard } from '@/components/features/fortune/FortuneCard'
import { FortuneRadar } from '@/components/features/fortune/FortuneRadar'
import { LuckyElements } from '@/components/features/fortune/LuckyElements'
import { FortuneShareCard } from '@/components/features/fortune/FortuneShareCard'
import { useFortuneStore } from '@/store/fortune'
import { useUserStore } from '@/store/user'
import { generateAnnualReport, getFortuneReport } from '@/lib/api'

export default function FortunePage() {
  const { todayFortune, isLoading, error, fetchTodayFortune, regenerateFortune, clearError } = useFortuneStore()
  const { isAuthenticated, user } = useUserStore()
  const [showShareCard, setShowShareCard] = useState(false)
  const [annualReport, setAnnualReport] = useState<any>(null)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportView, setReportView] = useState<any>(null)

  useEffect(() => {
    if (isAuthenticated) {
      fetchTodayFortune()
    }
    return () => clearError()
  }, [isAuthenticated, fetchTodayFortune, clearError])

  const handleGenerateReport = async () => {
    if (generatingReport) return
    setGeneratingReport(true)
    try {
      const report = await generateAnnualReport()
      setAnnualReport(report)
    } catch (e: any) {
      alert(e.message || '生成报告失败')
    } finally {
      setGeneratingReport(false)
    }
  }

  const handleViewReport = async (reportId: number) => {
    try {
      const report = await getFortuneReport(reportId)
      setReportView(report)
    } catch (e) {
      console.error('获取报告失败:', e)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <p className="text-4xl mb-3">🔮</p>
        <h2 className="text-lg font-semibold text-stone-800 mb-2">每日运势</h2>
        <p className="text-sm text-stone-500 mb-4">登录后即可查看基于您八字的专属运势分析</p>
      </div>
    )
  }

  if (isLoading && !todayFortune) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-emerald-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-stone-800">每日运势</h1>
          <p className="text-xs text-stone-500 mt-0.5">基于八字五行分析今日运势</p>
        </div>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={regenerateFortune}
          disabled={isLoading}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm disabled:opacity-60"
        >
          {isLoading ? '生成中...' : '重新生成'}
        </motion.button>
      </div>

      {todayFortune ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* 运势卡片 */}
          <FortuneCard fortune={todayFortune} onRegenerate={regenerateFortune} />

          {/* 雷达图 */}
          <FortuneRadar scores={todayFortune.scores} />

          {/* 幸运元素 */}
          {todayFortune.lucky_elements && (
            <LuckyElements luckyElements={todayFortune.lucky_elements} />
          )}

          {/* 八字快照 */}
          {todayFortune.bazi_snapshot && Object.keys(todayFortune.bazi_snapshot).length > 0 && (
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
              <h3 className="text-sm font-semibold text-stone-800 mb-3">八字分析依据</h3>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { label: '年柱', key: 'year' },
                  { label: '月柱', key: 'month' },
                  { label: '日柱', key: 'day' },
                  { label: '时柱', key: 'hour' },
                ].map(({ label, key }) => {
                  const pillar = todayFortune.bazi_snapshot?.pillars?.[key]
                  return (
                    <div key={label} className="text-center bg-stone-50 rounded-xl p-2.5">
                      <p className="text-[10px] text-stone-500 mb-1">{label}</p>
                      <p className="text-sm font-semibold text-stone-800">
                        {pillar || '-'}
                      </p>
                    </div>
                  )
                })}
              </div>
              {todayFortune.bazi_snapshot?.day_master && (
                <p className="text-xs text-stone-500 mt-3 text-center">
                  日元: <span className="font-semibold text-stone-700">{todayFortune.bazi_snapshot.day_master}</span>
                  {todayFortune.bazi_snapshot?.target_day_ganzhi && (
                    <> · 今日: <span className="font-semibold text-stone-700">{todayFortune.bazi_snapshot.target_day_ganzhi}</span> ({todayFortune.bazi_snapshot.target_day_element})</>
                  )}
                </p>
              )}
            </div>
          )}

          {/* 分享卡片 */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-stone-800">分享运势卡片</h3>
                <p className="text-[11px] text-stone-500 mt-0.5">生成精美卡片分享给朋友</p>
              </div>
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowShareCard(!showShareCard)}
                className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-violet-500 to-purple-500 text-white text-xs font-medium shadow-sm"
              >
                {showShareCard ? '收起' : '生成卡片'}
              </motion.button>
            </div>

            {showShareCard && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <FortuneShareCard
                  fortune={{
                    fortune_date: todayFortune.fortune_date,
                    scores: todayFortune.scores as unknown as Record<string, number>,
                    overall_score: todayFortune.overall_score,
                    lucky_colors: todayFortune.lucky_elements?.colors?.slice(0, 3),
                    outfit_suggestion: todayFortune.outfit_suggestion,
                    advice_text: todayFortune.advice_text,
                    day_ganzhi: todayFortune.bazi_snapshot?.target_day_ganzhi,
                    day_element: todayFortune.bazi_snapshot?.target_day_element,
                    day_master: todayFortune.bazi_snapshot?.day_master,
                    fortune_level:
                      todayFortune.overall_score >= 80 ? 'great' :
                      todayFortune.overall_score >= 65 ? 'good' :
                      todayFortune.overall_score >= 50 ? 'normal' : 'weak',
                  }}
                  username={user?.nickname || user?.phone}
                />
              </motion.div>
            )}
          </div>
        </motion.div>
      ) : (
        <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
          <p className="text-3xl mb-2">🌟</p>
          <p className="text-sm text-stone-500">暂无运势数据</p>
          <p className="text-xs text-stone-400 mt-1">点击上方按钮生成今日运势</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* 年度运势详批入口 */}
      <div className="mt-6 bg-gradient-to-br from-purple-50 via-pink-50 to-amber-50 rounded-2xl p-5 border border-purple-200/40">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-base font-semibold text-stone-800">年度运势详批</h3>
            <p className="text-xs text-stone-500 mt-0.5">AI 深度解析来年运势，助您趋吉避凶</p>
          </div>
          <span className="text-2xl">🔮</span>
        </div>
        <button
          onClick={handleGenerateReport}
          disabled={generatingReport}
          className="w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium text-sm shadow-md hover:shadow-lg transition-all disabled:opacity-50"
        >
          {generatingReport ? 'AI 正在生成报告...' : '生成年度运势报告 (¥99)'}
        </button>

        {/* 新生成的报告 */}
        {annualReport && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 bg-white rounded-xl p-4 border border-stone-200/60"
          >
            <h4 className="font-semibold text-stone-800 mb-2">
              {annualReport.year}年运势详批
            </h4>
            <p className="text-sm text-stone-600 mb-3 line-clamp-3">
              {annualReport.content?.overall}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setReportView(annualReport)}
                className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium"
              >
                查看完整报告
              </button>
            </div>
          </motion.div>
        )}
      </div>

      {/* 报告详情弹窗 */}
      {reportView && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4" onClick={() => setReportView(null)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-lg bg-white rounded-2xl p-6 shadow-2xl max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-stone-800">
                {reportView.year || reportView.title} 运势详批
              </h3>
              <button onClick={() => setReportView(null)} className="text-stone-400 hover:text-stone-600 text-xl">✕</button>
            </div>

            {reportView.content && (
              <div className="space-y-4 text-sm">
                {[
                  { key: 'overall', label: '整体运势', icon: '🌟' },
                  { key: 'career', label: '事业运', icon: '💼' },
                  { key: 'wealth', label: '财运', icon: '💰' },
                  { key: 'love', label: '感情运', icon: '❤️' },
                  { key: 'health', label: '健康运', icon: '🏃' },
                ].map(({ key, label, icon }) => (
                  reportView.content[key] && (
                    <div key={key} className="bg-stone-50 rounded-xl p-3">
                      <h4 className="font-medium text-stone-700 mb-1">{icon} {label}</h4>
                      <p className="text-stone-600 leading-relaxed">{reportView.content[key]}</p>
                    </div>
                  )
                ))}

                {reportView.content.monthly_breakdown && (
                  <div className="bg-stone-50 rounded-xl p-3">
                    <h4 className="font-medium text-stone-700 mb-2">📅 月度运势</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {reportView.content.monthly_breakdown.map((m: string, i: number) => (
                        <div key={i} className="text-xs text-stone-600">
                          <span className="font-medium text-stone-500">{i + 1}月：</span>{m}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {reportView.content.lucky_months && (
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-stone-500">幸运月份：</span>
                    {reportView.content.lucky_months.map((m: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs">{m}</span>
                    ))}
                  </div>
                )}

                {reportView.content.style_advice && (
                  <div className="bg-purple-50 rounded-xl p-3">
                    <h4 className="font-medium text-purple-700 mb-1">👗 穿搭建议</h4>
                    <p className="text-purple-600 text-sm">{reportView.content.style_advice}</p>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  )
}
