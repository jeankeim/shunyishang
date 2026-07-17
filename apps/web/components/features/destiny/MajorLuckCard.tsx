'use client'

import { motion } from 'framer-motion'
import type { LuckPeriod } from '@/store/destiny'

// 五行颜色
const ELEMENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  '金': { bg: 'bg-[#8A9BA8]/15', text: 'text-[#6B7F8C]', border: 'border-[#8A9BA8]/30' },
  '木': { bg: 'bg-[#3DA35D]/15', text: 'text-[#2D7A45]', border: 'border-[#3DA35D]/30' },
  '水': { bg: 'bg-[#4A90C4]/15', text: 'text-[#3570A0]', border: 'border-[#4A90C4]/30' },
  '火': { bg: 'bg-[#C75B5B]/15', text: 'text-[#A84545]', border: 'border-[#C75B5B]/30' },
  '土': { bg: 'bg-[#B89B5E]/15', text: 'text-[#9A7E47]', border: 'border-[#B89B5E]/30' },
}

// 旺衰等级颜色
const LUCK_LEVEL_COLORS: Record<string, string> = {
  '旺': 'text-emerald-600 bg-emerald-50',
  '相': 'text-blue-600 bg-blue-50',
  '休': 'text-amber-600 bg-amber-50',
  '囚': 'text-orange-600 bg-orange-50',
  '死': 'text-red-600 bg-red-50',
}

interface MajorLuckCardProps {
  luckPeriods: LuckPeriod[]
  currentLuck: LuckPeriod | null
}

export function MajorLuckCard({ luckPeriods, currentLuck }: MajorLuckCardProps) {
  return (
    <div className="space-y-4">
      {/* 当前大运 */}
      {currentLuck && (
        <div className="bg-gradient-to-br from-white to-stone-50/50 rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#4A90C4] to-[#3DA35D] rounded-full" />
            当前大运
          </h3>
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-2xl flex flex-col items-center justify-center bg-gradient-to-br from-[#3DA35D]/10 to-[#4A90C4]/10 border border-[#3DA35D]/20">
              <p className="text-2xl font-bold text-stone-800">{currentLuck.ganzhi}</p>
              <p className="text-xs text-stone-500">{currentLuck.element}</p>
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-stone-500">年龄范围</span>
                <span className="text-sm font-semibold text-stone-700">{currentLuck.start_age} - {currentLuck.end_age} 岁</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-stone-500">旺衰等级</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${LUCK_LEVEL_COLORS[currentLuck.luck_level] || 'bg-stone-50 text-stone-600'}`}>
                  {currentLuck.luck_level}
                </span>
              </div>
              <p className="text-xs text-stone-500">
                大运天干属{currentLuck.heavenly_stem}（{ELEMENT_COLORS[currentLuck.element]?.text ? currentLuck.element : ''}），
                地分支属{currentLuck.earthly_branch}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 大运时间线 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#B89B5E] to-[#C75B5B] rounded-full" />
          大运周期
        </h3>
        <div className="relative">
          {/* 时间线 */}
          <div className="absolute left-4 top-0 bottom-0 w-px bg-stone-200" />

          <div className="space-y-3">
            {luckPeriods.map((period, idx) => {
              const colors = ELEMENT_COLORS[period.element] || ELEMENT_COLORS['土']
              const isCurrent = currentLuck && period.start_age === currentLuck.start_age
              const levelStyle = LUCK_LEVEL_COLORS[period.luck_level] || 'bg-stone-50 text-stone-600'

              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className={`relative flex items-center gap-3 pl-8 ${isCurrent ? 'py-1' : ''}`}
                >
                  {/* 节点 */}
                  <div className={`absolute left-2.5 w-3 h-3 rounded-full border-2 ${
                    isCurrent ? 'border-[#3DA35D] bg-[#3DA35D]' : 'border-stone-300 bg-white'
                  }`} />

                  {/* 内容 */}
                  <div className={`flex-1 flex items-center gap-2 p-2 rounded-xl transition-all ${
                    isCurrent ? `${colors.bg} border ${colors.border}` : 'hover:bg-stone-50'
                  }`}>
                    <span className="text-sm font-bold text-stone-800 w-12">{period.ganzhi}</span>
                    <span className={`text-xs font-medium w-5 text-center ${colors.text}`}>{period.element}</span>
                    <span className="text-xs text-stone-400 w-16">{period.start_age}-{period.end_age}岁</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${levelStyle}`}>
                      {period.luck_level}
                    </span>
                    {isCurrent && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#3DA35D] text-white font-medium">
                        当前
                      </span>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
