'use client'

import { motion } from 'framer-motion'
import type { AnnualLuckData } from '@/store/destiny'

// 五行颜色映射
const ELEMENT_COLORS: Record<string, string> = {
  '金': '#8A9BA8', '木': '#3DA35D', '水': '#4A90C4', '火': '#D4656B', '土': '#B89B5E',
}

// 五维度中文名
const DIM_NAMES: Record<string, string> = {
  career: '事业', wealth: '财运', love: '桃花', health: '健康', study: '学业',
}

// 关系描述
const RELATION_DESC: Record<string, { label: string; tone: string }> = {
  '生': { label: '生扶', tone: 'text-emerald-600' },
  '泄': { label: '泄气', tone: 'text-amber-600' },
  '克': { label: '受克', tone: 'text-red-600' },
  '耗': { label: '消耗', tone: 'text-orange-600' },
  '比': { label: '比和', tone: 'text-blue-600' },
}

interface AnnualLuckCardProps {
  data: AnnualLuckData
}

export function AnnualLuckCard({ data }: AnnualLuckCardProps) {
  const { annual_luck, scores, overall_score, lucky_colors, lucky_materials, lucky_directions, lucky_elements, outfit_advice } = data
  const relation = RELATION_DESC[annual_luck.relationship] || { label: annual_luck.relationship, tone: 'text-stone-600' }
  const elementColor = ELEMENT_COLORS[annual_luck.element] || '#666'

  // 找出最高和最低维度
  const sortedDims = Object.entries(scores).sort(([, a], [, b]) => b - a)
  const bestDim = sortedDims[0]
  const worstDim = sortedDims[sortedDims.length - 1]

  return (
    <div className="space-y-4">
      {/* 流年概览 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-stone-800 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#D4656B] to-[#B89B5E] rounded-full" />
            {annual_luck.year} 流年运势
          </h3>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full bg-stone-50 ${relation.tone}`}>
              {relation.label}
            </span>
            <div className="text-right">
              <span className="text-2xl font-bold text-stone-800">{overall_score}</span>
              <span className="text-xs text-stone-400 ml-1">分</span>
            </div>
          </div>
        </div>

        {/* 流年干支 */}
        <div className="flex items-center gap-4 mb-4 p-3 bg-stone-50 rounded-xl">
          <div className="text-center">
            <p className="text-[10px] text-stone-400 mb-0.5">流年干支</p>
            <p className="text-xl font-bold" style={{ color: elementColor }}>{annual_luck.ganzhi}</p>
          </div>
          <div className="h-8 w-px bg-stone-200" />
          <div className="text-center">
            <p className="text-[10px] text-stone-400 mb-0.5">流年五行</p>
            <span className="text-sm font-semibold px-2 py-0.5 rounded-full text-white" style={{ backgroundColor: elementColor }}>
              {annual_luck.element}
            </span>
          </div>
          <div className="h-8 w-px bg-stone-200" />
          <div className="flex-1">
            <p className="text-xs text-stone-500 leading-relaxed">{annual_luck.advice}</p>
          </div>
        </div>

        {/* 五维度评分 */}
        <div className="space-y-2 mb-4">
          {Object.entries(scores).map(([dim, score]) => {
            const isBest = dim === bestDim[0]
            const isWorst = dim === worstDim[0]
            const barColor = score >= 70 ? 'bg-emerald-400' : score >= 50 ? 'bg-blue-400' : 'bg-amber-400'

            return (
              <div key={dim} className="flex items-center gap-2">
                <span className="text-xs text-stone-500 w-8">{DIM_NAMES[dim] || dim}</span>
                <div className="flex-1 h-4 bg-stone-50 rounded-full overflow-hidden relative">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${score}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    className={`h-full rounded-full ${barColor}`}
                  />
                  <span className="absolute inset-0 flex items-center justify-center text-[10px] text-stone-600 font-medium">
                    {score}
                  </span>
                </div>
                {isBest && <span className="text-[10px] text-emerald-600">▲</span>}
                {isWorst && <span className="text-[10px] text-amber-600">▼</span>}
              </div>
            )
          })}
        </div>
      </div>

      {/* 穿搭建议 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <h3 className="text-sm font-semibold text-stone-800 mb-3 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#3DA35D] to-[#B89B5E] rounded-full" />
          流年穿搭指南
        </h3>

        {/* 幸运元素 */}
        <div className="grid grid-cols-3 gap-3 mb-3">
          {lucky_colors.length > 0 && (
            <div className="text-center p-2 bg-stone-50 rounded-xl">
              <p className="text-[10px] text-stone-400 mb-1">幸运色</p>
              <div className="flex flex-wrap justify-center gap-1">
                {lucky_colors.slice(0, 3).map((c, i) => (
                  <span key={i} className="text-xs text-stone-600">{c}</span>
                ))}
              </div>
            </div>
          )}
          {lucky_materials.length > 0 && (
            <div className="text-center p-2 bg-stone-50 rounded-xl">
              <p className="text-[10px] text-stone-400 mb-1">推荐材质</p>
              <div className="flex flex-wrap justify-center gap-1">
                {lucky_materials.slice(0, 2).map((m, i) => (
                  <span key={i} className="text-xs text-stone-600">{m}</span>
                ))}
              </div>
            </div>
          )}
          {lucky_directions.length > 0 && (
            <div className="text-center p-2 bg-stone-50 rounded-xl">
              <p className="text-[10px] text-stone-400 mb-1">有利方位</p>
              <div className="flex flex-wrap justify-center gap-1">
                {lucky_directions.slice(0, 3).map((d, i) => (
                  <span key={i} className="text-xs text-stone-600">{d}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        <p className="text-xs text-stone-500 leading-relaxed bg-emerald-50/50 rounded-xl p-3">
          👔 {outfit_advice}
        </p>
      </div>
    </div>
  )
}
