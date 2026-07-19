'use client'

import { motion } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import type { DiaryStats } from '@/types'

const MOOD_COLORS: Record<string, string> = {
  happy: '#3DA35D', excited: '#C75B5B', calm: '#4A90C4', neutral: '#B89B5E', sad: '#9CAFB8',
}
const MOOD_LABELS: Record<string, string> = {
  happy: '开心', excited: '兴奋', calm: '平静', neutral: '一般', sad: '低落',
}

interface DiaryStatsProps {
  stats: DiaryStats | null
}

export function DiaryStatsPanel({ stats }: DiaryStatsProps) {
  if (!stats) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-stone-100 text-center">
        <p className="text-sm text-stone-400">暂无统计数据</p>
      </div>
    )
  }

  const moodData = Object.entries(stats.mood_distribution).map(([key, value]) => ({
    name: MOOD_LABELS[key] || key,
    value,
    color: MOOD_COLORS[key] || '#ccc',
  }))

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      {/* 统计卡片 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-stone-100">
          <p className="text-xs text-stone-500 mb-1">总日记数</p>
          <p className="text-2xl font-bold text-[var(--brand-heading)]">{stats.total_diaries}</p>
        </div>
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-stone-100">
          <p className="text-xs text-stone-500 mb-1">连续打卡</p>
          <p className="text-2xl font-bold text-emerald-600">{stats.streak_days}<span className="text-sm font-normal text-stone-500"> 天</span></p>
        </div>
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-stone-100">
          <p className="text-xs text-stone-500 mb-1">平均评分</p>
          <p className="text-2xl font-bold text-amber-500">{stats.avg_rating?.toFixed(1) || '-'}</p>
        </div>
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-stone-100">
          <p className="text-xs text-stone-500 mb-1">穿搭件数</p>
          <p className="text-2xl font-bold text-[#4A90C4]">{stats.total_items}</p>
        </div>
      </div>

      {/* 心情分布 */}
      {moodData.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-[var(--brand-heading)] mb-3">心情分布</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={moodData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                  {moodData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </motion.div>
  )
}
