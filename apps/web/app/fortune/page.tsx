'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FortuneCard } from '@/components/features/fortune/FortuneCard'
import { FortuneRadar } from '@/components/features/fortune/FortuneRadar'
import { LuckyElements } from '@/components/features/fortune/LuckyElements'
import { FortuneShareCard } from '@/components/features/fortune/FortuneShareCard'
import { useFortuneStore } from '@/store/fortune'
import { useUserStore } from '@/store/user'
import { generateAnnualReport, getFortuneReport, getFortuneReports, getWeeklyFortune, type WeeklyFortune } from '@/lib/api'
import { createPortal } from 'react-dom'
import { SkeletonCard, EmptyState } from '@/components/ui'

// ========== 本周运势概览卡片（可折叠） ==========
function WeeklyFortuneCard() {
  const [weekly, setWeekly] = useState<WeeklyFortune | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    getWeeklyFortune()
      .then(data => setWeekly(data))
      .catch((err) => {
        console.error('[WeeklyFortuneCard] 获取周报失败:', err)
        setWeekly(null)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100 animate-pulse">
        <div className="h-4 bg-stone-200 rounded w-1/3 mb-3" />
        <div className="h-3 bg-stone-100 rounded w-2/3 mb-2" />
        <div className="h-3 bg-stone-100 rounded w-1/2" />
      </div>
    )
  }

  if (!weekly) return null

  const trendEmoji: Record<string, string> = { '上升': '📈', '平稳': '➡️', '下降': '📉' }
  const trendIcon = trendEmoji[weekly.overall_trend] || '📊'

  // 格式化日期：2026-07-14 → 7/14
  const fmtDay = (d: string) => {
    const parts = d.split('-')
    return `${parseInt(parts[1])}/${parseInt(parts[2])}`
  }

  // 柱状图颜色
  const barColor = (score: number) =>
    score >= 75 ? 'bg-[#3DA35D]' : score >= 55 ? 'bg-[#B89B5E]' : 'bg-[#9CAFB8]'

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-stone-100 overflow-hidden">
      {/* 折叠头部：始终可见的关键指标 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-stone-50/60 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">{trendIcon}</span>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-stone-800">本周运势概览</h3>
            <p className="text-xs text-stone-500 mt-0.5">
              {weekly.start_date} ~ {weekly.end_date}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* 关键指标：评分 + 趋势 */}
          <div className="text-right">
            <span className="text-lg font-bold text-stone-800">{weekly.overall_score}</span>
            <span className="text-xs text-stone-500 ml-1">分</span>
          </div>
          <motion.span
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-stone-400 text-xs"
          >
            ▼
          </motion.span>
        </div>
      </button>

      {/* 可折叠详情 */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-4">
              {/* 整体趋势 */}
              <div className="bg-stone-50 rounded-xl p-3">
                <p className="text-xs text-stone-500 mb-1">整体趋势</p>
                <p className="text-sm text-stone-700 font-medium">
                  {trendIcon} {weekly.overall_trend}
                </p>
              </div>

              {/* 7天运势柱状图 */}
              <div>
                <p className="text-xs text-stone-500 mb-2">7天运势趋势</p>
                <div className="flex items-end gap-1.5 h-24">
                  {weekly.daily_fortunes.map(day => (
                    <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[10px] text-stone-500 font-medium">{day.score}</span>
                      <div className="w-full flex items-end" style={{ height: '60px' }}>
                        <div
                          className={`w-full rounded-t-md ${barColor(day.score)} transition-all`}
                          style={{ height: `${Math.max(day.score, 8)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-stone-400">{fmtDay(day.date)}</span>
                      <span className="text-[10px] text-emerald-600">{day.lucky_element}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 幸运元素 */}
              {weekly.weekly_lucky_elements.length > 0 && (
                <div>
                  <p className="text-xs text-stone-500 mb-1.5">本周幸运元素</p>
                  <div className="flex flex-wrap gap-1.5">
                    {weekly.weekly_lucky_elements.map(el => (
                      <span key={el} className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium">
                        {el}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 穿搭关键词 */}
              {weekly.weekly_style_keywords.length > 0 && (
                <div>
                  <p className="text-xs text-stone-500 mb-1.5">本周穿搭关键词</p>
                  <div className="flex flex-wrap gap-1.5">
                    {weekly.weekly_style_keywords.map(kw => (
                      <span key={kw} className="px-2 py-0.5 bg-violet-50 text-violet-700 rounded-full text-xs font-medium">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 穿搭建议 */}
              {weekly.outfit_suggestions && (
                <div className="bg-[var(--brand-surface)]/60 rounded-xl p-3">
                  <p className="text-xs text-[var(--brand-body)] font-medium mb-1">👗 本周穿搭建议</p>
                  <p className="text-sm text-stone-600 leading-relaxed">{weekly.outfit_suggestions}</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function FortunePage() {
  const { todayFortune, isLoading, error, fetchTodayFortune, regenerateFortune, clearError } = useFortuneStore()
  const { isAuthenticated, user } = useUserStore()
  const [showShareCard, setShowShareCard] = useState(false)
  const [annualReport, setAnnualReport] = useState<any>(null)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [reportView, setReportView] = useState<any>(null)
  const [savedReports, setSavedReports] = useState<any[]>([])

  // 年度报告每年限频（与后端 ANNUAL_REPORT_YEARLY_LIMIT 保持一致）
  const ANNUAL_LIMIT = 3
  const currentYear = new Date().getFullYear()
  const annualCountThisYear = savedReports.filter(
    r => r.report_type === 'annual_fortune' && r.report_year === currentYear
  ).length

  useEffect(() => {
    if (isAuthenticated) {
      fetchTodayFortune()
      // 加载已保存的报告
      getFortuneReports().then(reports => {
        setSavedReports(reports || [])
      }).catch(() => {})
    }
    return () => clearError()
  }, [isAuthenticated, fetchTodayFortune, clearError])

  // 模态框打开时阻止背景滚动
  useEffect(() => {
    if (reportView) {
      document.body.style.overflow = 'hidden'
      return () => { document.body.style.overflow = '' }
    }
  }, [reportView])

  const handleGenerateReport = async () => {
    if (generatingReport) return
    setGeneratingReport(true)
    try {
      const report = await generateAnnualReport()
      setAnnualReport(report)
      // 刷新已保存的报告列表
      const reports = await getFortuneReports()
      setSavedReports(reports || [])
    } catch (e: any) {
      alert(e.message || '生成报告失败')
      // 达上限时也刷新列表，保证计数同步
      getFortuneReports().then(rs => setSavedReports(rs || [])).catch(() => {})
    } finally {
      setGeneratingReport(false)
    }
  }

  const handleViewReport = async (reportId: number, e?: React.MouseEvent) => {
    // 阻止任何可能的默认行为和事件冒泡
    if (e) {
      e.preventDefault()
      e.stopPropagation()
    }
    try {
      const report = await getFortuneReport(reportId)
      setReportView(report)
      // 防止页面滚动到顶部
      window.scrollTo({ top: window.scrollY, behavior: 'auto' })
    } catch (e) {
      console.error('获取报告失败:', e)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto space-y-4 py-8">
        {/* 未登录用户也展示本周运势概览（通用版） */}
        <WeeklyFortuneCard />
        <div className="text-center py-8">
          <p className="text-4xl mb-3">🔮</p>
          <h2 className="text-lg font-semibold text-stone-800 mb-2">每日运势</h2>
          <p className="text-sm text-stone-500 mb-4">登录后即可查看基于您八字的专属运势分析</p>
        </div>
      </div>
    )
  }

  if (isLoading && !todayFortune) {
    // 仅首屏无数据时：保留周报卡片即时渲染，运势区域用骨架屏占位（避免整页白等）
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-stone-800">每日运势</h1>
            <p className="text-xs text-stone-500 mt-0.5">基于八字五行分析今日运势</p>
          </div>
        </div>
        <WeeklyFortuneCard />
        <SkeletonCard lines={2} />
        <SkeletonCard lines={3} showImage={false} />
        <SkeletonCard lines={2} showImage={false} />
      </div>
    )
  }

  return (
    <>
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
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white text-sm font-medium shadow-sm disabled:opacity-60"
        >
          {isLoading ? '生成中...' : '重新生成'}
        </motion.button>
      </div>

      {/* 本周运势概览（可折叠卡片） */}
      <WeeklyFortuneCard />

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
        <EmptyState
          icon="search"
          title="暂无运势数据"
          description="点击上方按钮生成今日运势"
        />
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* 运势报告高端皮肤区（跟随全局皮肤） */}
      <div className="mt-6 space-y-4">
      {/* 年度运势详批入口 - 玄光神秘高端皮肤 */}
      <div className="mystic-panel p-5">
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="mystic-heading text-base font-semibold">年度运势详批</h3>
              <p className="mystic-subtle text-xs mt-0.5">AI 深度解析本年度运势，助您从容规划</p>
            </div>
            <span className="text-2xl">🔮</span>
          </div>
          <button
            onClick={handleGenerateReport}
            disabled={generatingReport || annualCountThisYear >= ANNUAL_LIMIT}
            className="mystic-btn w-full py-3 text-sm disabled:opacity-50"
          >
            {generatingReport
              ? 'AI 正在生成报告...'
              : annualCountThisYear >= ANNUAL_LIMIT
                ? `本年度已生成 ${annualCountThisYear}/${ANNUAL_LIMIT} 次，已达上限`
                : `生成年度运势报告（本年 ${annualCountThisYear}/${ANNUAL_LIMIT}）`}
          </button>
          {annualCountThisYear >= ANNUAL_LIMIT && (
            <p className="mystic-subtle text-[11px] mt-2 text-center">每年最多生成 {ANNUAL_LIMIT} 次，您可在下方查看已生成的报告</p>
          )}

          {/* 新生成的报告 */}
          {annualReport && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mystic-card mt-4 p-4"
            >
              <h4 className="mystic-heading font-semibold mb-2">
                {annualReport.year}年运势详批
              </h4>
              <p className="text-sm mb-3 line-clamp-3" style={{ color: '#cfc7dd' }}>
                {annualReport.content?.overall}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={(e) => { e.preventDefault(); setReportView(annualReport) }}
                  className="mystic-chip px-4 py-2 text-sm font-medium"
                >
                  查看完整报告
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* 已保存的报告列表 - 玄光神秘高端皮肤 */}
      {savedReports.length > 0 && (
        <div className="mystic-panel p-5">
          <div className="relative z-10">
            <h3 className="mystic-heading text-sm font-semibold mb-3">我的运势报告</h3>
            <div className="space-y-2">
              {savedReports.map((report) => (
                <div
                  key={report.id}
                  className="mystic-card flex items-center justify-between p-3 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium" style={{ color: '#e8e2f0' }}>{report.title || `${report.report_year}年运势详批`}</p>
                    <p className="mystic-subtle text-xs mt-0.5">
                      {report.report_type === 'annual_fortune' ? '年度运势' : report.report_type}
                      {report.created_at && ` · ${new Date(report.created_at).toLocaleDateString('zh-CN')}`}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleViewReport(report.id, e)}
                    className="mystic-chip px-3 py-1.5 text-xs font-medium"
                  >
                    查看
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>

    {/* 报告详情弹窗 - 使用 Portal 渲染到 body，确保不受父容器影响 */}
    {reportView && typeof document !== 'undefined' && createPortal(
      <div 
        className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        onClick={() => setReportView(null)}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="mystic-modal w-full max-w-lg rounded-2xl"
          onClick={e => e.stopPropagation()}
        >
          {/* 内层独立滚动容器：.mystic-modal 的 overflow:hidden 仅用于圆角/星空裁切，
              若在外层加 overflow-y-auto 会被其覆盖导致内容被裁、无法滚动 */}
          <div className="relative z-10 max-h-[85vh] overflow-y-auto overscroll-contain p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="mystic-heading text-lg font-bold">
              {reportView.year || reportView.title} 运势详批
            </h3>
            <button onClick={() => setReportView(null)} className="mystic-subtle hover:text-white text-xl">✕</button>
          </div>

          {reportView.content && (
            <div className="space-y-4 text-sm">
              {[
                { key: 'overall', label: '整体运势', icon: '🌟' },
                { key: 'career', label: '事业运', icon: '💼' },
                { key: 'wealth', label: '财运', icon: '' },
                { key: 'love', label: '感情运', icon: '❤️' },
                { key: 'health', label: '健康运', icon: '' },
              ].map(({ key, label, icon }) => (
                reportView.content[key] && (
                  <div key={key} className="mystic-card p-3">
                    <h4 className="mystic-gold font-medium mb-1">{icon} {label}</h4>
                    <p className="leading-relaxed" style={{ color: '#cfc7dd' }}>{reportView.content[key]}</p>
                  </div>
                )
              ))}

              {reportView.content.monthly_breakdown && (
                <div className="mystic-card p-3">
                  <h4 className="mystic-gold font-medium mb-2">📅 月度运势</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {reportView.content.monthly_breakdown.map((m: string, i: number) => (
                      <div key={i} className="text-xs" style={{ color: '#cfc7dd' }}>
                        <span className="font-medium mystic-subtle">{i + 1}月：</span>{m}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reportView.content.lucky_months && (
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-xs mystic-subtle">幸运月份：</span>
                  {reportView.content.lucky_months.map((m: string, i: number) => (
                    <span key={i} className="mystic-chip px-2 py-0.5 text-xs">{m}</span>
                  ))}
                </div>
              )}

              {reportView.content.style_advice && (
                <div className="mystic-card p-3">
                  <h4 className="mystic-gold font-medium mb-1">👗 穿搭建议</h4>
                  <p className="text-sm" style={{ color: '#cfc7dd' }}>{reportView.content.style_advice}</p>
                </div>
              )}
            </div>
          )}
          </div>
        </motion.div>
      </div>,
      document.body
    )}
    </>
  )
}
