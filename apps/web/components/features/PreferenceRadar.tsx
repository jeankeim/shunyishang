'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, Info } from 'lucide-react'
import { getPreferenceSummary, type PreferenceSummary, type PreferenceDimension } from '@/lib/api'

/**
 * 用户偏好画像雷达图组件
 * 展示6维偏好学习结果：颜色、五行、品类、风格、材质、厚度
 */
export function PreferenceRadar() {
  const [data, setData] = useState<PreferenceSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedDim, setExpandedDim] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetch = async () => {
      const result = await getPreferenceSummary()
      if (!cancelled) {
        setData(result)
        setLoading(false)
      }
    }
    fetch()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
        <h3 className="text-lg font-semibold text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
          我的偏好画像
        </h3>
        <div className="flex items-center justify-center h-48 text-[var(--brand-subtle)]">
          加载中...
        </div>
      </section>
    )
  }

  if (!data || data.feedback_count === 0) {
    return (
      <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
        <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
          <TrendingUp className="h-5 w-5 text-[var(--wuxing-earth)]" />
          我的偏好画像
        </h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--brand-surface)] to-stone-100 flex items-center justify-center mb-4">
            <Info className="h-7 w-7 text-[var(--brand-subtle)]" />
          </div>
          <p className="text-sm text-[var(--brand-body)] font-medium mb-1">还没有偏好数据</p>
          <p className="text-xs text-[var(--brand-subtle)] max-w-[240px]">
            在推荐结果上点击喜欢/不喜欢，系统会逐步学习您的穿搭偏好
          </p>
        </div>
      </section>
    )
  }

  const dims = data.dimensions
  const hasAnyData = dims.some(d => d.has_data)
  if (!hasAnyData) return null

  return (
    <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
      <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
        <TrendingUp className="h-5 w-5 text-[var(--wuxing-earth)]" />
        我的偏好画像
        <span className="ml-auto text-xs font-normal text-[var(--brand-subtle)]">
          系统了解度 {Math.round(data.overall_score * 100)}%
        </span>
      </h3>

      {/* SVG 雷达图 */}
      <div className="flex justify-center mb-4">
        <RadarChart dimensions={dims} />
      </div>

      {/* 了解度进度条 */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-[var(--brand-subtle)] mb-1">
          <span>系统了解度</span>
          <span>{Math.round(data.overall_score * 100)}%（{data.feedback_count}次反馈）</span>
        </div>
        <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${data.overall_score * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="h-full bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] rounded-full"
          />
        </div>
      </div>

      {/* 6维详情列表 */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {dims.filter(d => d.has_data).map(dim => (
          <button
            key={dim.key}
            onClick={() => setExpandedDim(expandedDim === dim.key ? null : dim.key)}
            className={`text-left p-3 rounded-xl border transition-all ${
              expandedDim === dim.key
                ? 'border-[var(--wuxing-wood)]/40 bg-[var(--brand-surface)]/60 shadow-sm'
                : 'border-[var(--brand-border)]/30 hover:border-[var(--wuxing-wood)]/20 hover:bg-stone-50'
            }`}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-sm">{dim.icon}</span>
              <span className="text-xs font-medium text-[var(--brand-body)]">{dim.label}</span>
              <span className="ml-auto text-[10px] text-[var(--brand-subtle)]">
                {Math.round(dim.score * 100)}%
              </span>
            </div>
            {/* 迷你进度条 */}
            <div className="h-1 bg-stone-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] rounded-full transition-all duration-500"
                style={{ width: `${dim.score * 100}%` }}
              />
            </div>
            {/* 展开详情 */}
            {expandedDim === dim.key && dim.top_items.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-2 space-y-1"
              >
                {dim.top_items.map((item, i) => (
                  <div key={i} className="flex items-center gap-1 text-[10px]">
                    <span className={item.direction === '喜欢' ? 'text-emerald-600' : 'text-rose-500'}>
                      {item.direction === '喜欢' ? '♥' : '✕'}
                    </span>
                    <span className="text-[var(--brand-body)]">{item.name}</span>
                    <span className="ml-auto text-[var(--brand-subtle)]">{item.weight > 0 ? '+' : ''}{item.weight}</span>
                  </div>
                ))}
              </motion.div>
            )}
          </button>
        ))}
      </div>
    </section>
  )
}

/**
 * SVG 雷达图（纯 SVG，无外部依赖）
 */
function RadarChart({ dimensions }: { dimensions: PreferenceDimension[] }) {
  const activeDims = dimensions.filter(d => d.has_data)
  const n = activeDims.length
  if (n < 3) return null

  const cx = 120
  const cy = 120
  const maxR = 90
  const levels = 4

  // 计算每个顶点的坐标
  const getPoint = (index: number, radius: number) => {
    const angle = (Math.PI * 2 * index) / n - Math.PI / 2
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  }

  // 背景网格
  const gridLines = []
  for (let level = 1; level <= levels; level++) {
    const r = (maxR * level) / levels
    const points = Array.from({ length: n }, (_, i) => getPoint(i, r))
    const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + 'Z'
    gridLines.push(
      <path key={`grid-${level}`} d={path} fill="none" stroke="#e7e5e4" strokeWidth={level === levels ? 1.5 : 0.5} />
    )
  }

  // 轴线
  const axisLines = Array.from({ length: n }, (_, i) => {
    const p = getPoint(i, maxR)
    return <line key={`axis-${i}`} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e7e5e4" strokeWidth={0.5} />
  })

  // 数据区域
  const dataPoints = activeDims.map((dim, i) => getPoint(i, maxR * dim.score))
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ') + 'Z'

  // 标签
  const labels = activeDims.map((dim, i) => {
    const p = getPoint(i, maxR + 18)
    return (
      <text
        key={`label-${dim.key}`}
        x={p.x}
        y={p.y}
        textAnchor="middle"
        dominantBaseline="middle"
        className="text-[10px] fill-stone-500"
      >
        {dim.icon} {dim.label}
      </text>
    )
  })

  return (
    <svg width={240} height={240} viewBox="0 0 240 240" className="select-none">
      {/* 背景网格 */}
      {gridLines}
      {axisLines}

      {/* 数据区域 */}
      <motion.path
        d={dataPath}
        fill="var(--wuxing-wood)"
        fillOpacity={0.15}
        stroke="var(--wuxing-wood)"
        strokeWidth={2}
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        style={{ transformOrigin: `${cx}px ${cy}px` }}
      />

      {/* 数据点 */}
      {dataPoints.map((p, i) => (
        <motion.circle
          key={`dot-${i}`}
          cx={p.x}
          cy={p.y}
          r={3.5}
          fill="var(--wuxing-wood)"
          stroke="white"
          strokeWidth={1.5}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.3 + i * 0.08 }}
        />
      ))}

      {/* 标签 */}
      {labels}
    </svg>
  )
}
