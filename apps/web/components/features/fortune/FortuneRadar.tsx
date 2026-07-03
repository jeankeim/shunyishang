'use client'

import { motion } from 'framer-motion'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts'
import type { FortuneScores } from '@/types'

const DIMENSIONS: { key: keyof FortuneScores; label: string; emoji: string }[] = [
  { key: 'career', label: '事业', emoji: '💼' },
  { key: 'wealth', label: '财运', emoji: '💰' },
  { key: 'love', label: '桃花', emoji: '💕' },
  { key: 'health', label: '健康', emoji: '🌿' },
  { key: 'study', label: '学业', emoji: '📚' },
]

interface FortuneRadarProps {
  scores: FortuneScores
  size?: number
}

export function FortuneRadar({ scores, size = 240 }: FortuneRadarProps) {
  const data = DIMENSIONS.map((dim) => ({
    dimension: `${dim.emoji} ${dim.label}`,
    score: scores[dim.key] ?? 0,
    fullMark: 100,
  }))

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100"
    >
      <h3 className="text-sm font-semibold text-stone-800 mb-2">五维度运势雷达</h3>
      <div style={{ width: '100%', height: size }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} cx="50%" cy="50%" outerRadius={size * 0.38}>
            <PolarGrid stroke="#e7e5e4" />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fill: '#78716c', fontSize: 12 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: '#a8a29e', fontSize: 10 }}
              tickCount={3}
            />
            <Radar
              dataKey="score"
              stroke="#3DA35D"
              fill="#3DA35D"
              fillOpacity={0.15}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  )
}
