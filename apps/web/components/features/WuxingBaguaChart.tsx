'use client'

/**
 * 道家五行八卦图 - 衣橱五行能量分布可视化
 * 以五行相生（外环）、相克（内星）的道家图式展示衣橱各五行占比，
 * 点击节点可按五行筛选衣物。配色沿用全局 wuxing-config，保持风格统一。
 */

import { motion } from 'framer-motion'
import { WUXING_CONFIG, type WuxingElement } from '@/lib/wuxing-config'

interface WuxingBaguaChartProps {
  elementStats: Record<string, number>
  total: number
  filterElement: string | null
  onFilter: (element: string | null) => void
}

// 按相生顺序排列（木→火→土→金→水→木），八卦符号沿用衣橱主题
const SHENG_ORDER: { element: WuxingElement; gua: string }[] = [
  { element: '木', gua: '☳' },
  { element: '火', gua: '☲' },
  { element: '土', gua: '☷' },
  { element: '金', gua: '☰' },
  { element: '水', gua: '☵' },
]

// 几何参数（viewBox 0 0 100 100 与 HTML 百分比定位共用）
const CENTER = 50
const RADIUS = 37

function nodePosition(index: number) {
  const angle = (-90 + index * 72) * (Math.PI / 180)
  return {
    x: CENTER + RADIUS * Math.cos(angle),
    y: CENTER + RADIUS * Math.sin(angle),
  }
}

const POSITIONS = SHENG_ORDER.map((_, i) => nodePosition(i))

export function WuxingBaguaChart({ elementStats, total, filterElement, onFilter }: WuxingBaguaChartProps) {
  const getPercentage = (element: string) => {
    if (total === 0) return 0
    return Math.round(((elementStats[element] || 0) / total) * 100)
  }

  return (
    <div className="relative mx-auto w-full max-w-[320px] aspect-square">
      {/* 相生 / 相克 连线 */}
      <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full" aria-hidden>
        {/* 外环相生 - 五边形闭合路径 */}
        <polygon
          points={POSITIONS.map((p) => `${p.x},${p.y}`).join(' ')}
          fill="none"
          stroke="var(--wuxing-wood)"
          strokeOpacity="0.35"
          strokeWidth="0.9"
          strokeLinejoin="round"
        />
        {/* 内星相克 - 连接间隔节点形成五角星 */}
        {POSITIONS.map((p, i) => {
          const target = POSITIONS[(i + 2) % 5]
          return (
            <line
              key={`ke-${i}`}
              x1={p.x}
              y1={p.y}
              x2={target.x}
              y2={target.y}
              stroke="var(--brand-subtle)"
              strokeOpacity="0.25"
              strokeWidth="0.6"
              strokeDasharray="1.5 1.5"
            />
          )
        })}
        {/* 中心太极环 */}
        <circle cx={CENTER} cy={CENTER} r="11" fill="var(--brand-surface)" stroke="var(--wuxing-water)" strokeOpacity="0.3" strokeWidth="0.8" />
      </svg>

      {/* 中心：总计 */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
        <span className="text-lg md:text-xl font-bold text-[var(--brand-heading)] leading-none font-serif">{total}</span>
        <span className="text-[10px] text-[var(--brand-subtle)] mt-0.5">件衣物</span>
      </div>

      {/* 五行节点 */}
      {SHENG_ORDER.map(({ element, gua }, i) => {
        const config = WUXING_CONFIG[element]
        const count = elementStats[element] || 0
        const percentage = getPercentage(element)
        const isActive = filterElement === element
        const isDimmed = filterElement !== null && !isActive
        const pos = POSITIONS[i]

        return (
          <motion.button
            key={element}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: isDimmed ? 0.45 : 1, scale: 1 }}
            transition={{ delay: 0.1 + i * 0.06, type: 'spring', stiffness: 220, damping: 18 }}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onFilter(isActive ? null : element)}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1 touch-feedback"
            style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
            aria-label={`${element} ${count}件 占比${percentage}%`}
          >
            <div
              className="relative w-14 h-14 md:w-16 md:h-16 rounded-full flex flex-col items-center justify-center shadow-sm transition-shadow"
              style={{
                background: `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})`,
                boxShadow: isActive ? `0 0 0 3px var(--brand-surface), 0 0 0 5px ${config.gradientFrom}` : undefined,
              }}
            >
              {/* 八卦符号水印 */}
              <span className="absolute inset-0 flex items-center justify-center text-2xl md:text-3xl text-white/20 font-serif select-none">
                {gua}
              </span>
              <span className="relative text-base md:text-lg font-bold text-white leading-none">{count}</span>
              <span className="relative text-[10px] md:text-xs text-white/85 leading-none mt-0.5">{element}</span>
            </div>
            <span className="text-[10px] text-[var(--brand-subtle)] leading-none">{percentage}%</span>
          </motion.button>
        )
      })}
    </div>
  )
}
