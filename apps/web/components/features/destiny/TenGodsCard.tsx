'use client'

import { motion } from 'framer-motion'
import type { TenGodsData } from '@/store/destiny'

// 十神颜色映射
const TEN_GOD_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  '比肩': { bg: 'bg-[#8A9BA8]/10', text: 'text-[#6B7F8C]', border: 'border-[#8A9BA8]/30' },
  '劫财': { bg: 'bg-[#C75B5B]/10', text: 'text-[#A84545]', border: 'border-[#C75B5B]/30' },
  '食神': { bg: 'bg-[var(--wuxing-wood)]/10', text: 'text-[#2D7A45]', border: 'border-[var(--wuxing-wood)]/30' },
  '伤官': { bg: 'bg-[#C75B5B]/10', text: 'text-[#A84545]', border: 'border-[#C75B5B]/30' },
  '偏财': { bg: 'bg-[#B89B5E]/10', text: 'text-[#9A7E47]', border: 'border-[#B89B5E]/30' },
  '正财': { bg: 'bg-[#D4A574]/10', text: 'text-[#B8865A]', border: 'border-[#D4A574]/30' },
  '七杀': { bg: 'bg-[#2C3E50]/10', text: 'text-[#1A252F]', border: 'border-[#2C3E50]/30' },
  '正官': { bg: 'bg-[var(--wuxing-water)]/10', text: 'text-[#3570A0]', border: 'border-[var(--wuxing-water)]/30' },
  '偏印': { bg: 'bg-[#6B5B95]/10', text: 'text-[#5A4D7F]', border: 'border-[#6B5B95]/30' },
  '正印': { bg: 'bg-[#5DADE2]/10', text: 'text-[#2E86C1]', border: 'border-[#5DADE2]/30' },
  '日主': { bg: 'bg-gradient-to-br from-[var(--wuxing-wood)]/15 to-[var(--wuxing-water)]/15', text: 'text-[var(--brand-heading)]', border: 'border-[var(--wuxing-wood)]/40' },
}

// 十神描述映射
const TEN_GOD_DESC: Record<string, string> = {
  '比肩': '独立自主，竞争合作',
  '劫财': '行动力强，宜稳健理财',
  '食神': '才华横溢，福禄之兆',
  '伤官': '聪明叛逆，创新之兆',
  '偏财': '意外之财，投资之兆',
  '正财': '正当收入，稳定之兆',
  '七杀': '权威压力，挑战之兆',
  '正官': '事业地位，名声之兆',
  '偏印': '学习深造，偏门之兆',
  '正印': '贵人相助，学业之兆',
}

// 十天干日主性格映射（基于日柱天干显示性格特质）
const DAY_MASTER_PERSONALITY: Record<string, string> = {
  '甲': '正直坚毅，参天大树',   // 阳木：刚直向上，不屈不挠
  '乙': '柔韧灵活，花草藤蔓',   // 阴木：委婉适应，随遇而安
  '丙': '热情奔放，太阳之火',   // 阳火：光明磊落，感染力强
  '丁': '温柔细腻，烛光之暖',   // 阴火：内秀含蓄，心思缜密
  '戊': '稳重包容，高山大地',   // 阳土：宽厚踏实，值得信赖
  '己': '温和谦逊，田园之土',   // 阴土：内敛含蓄，善于滋养
  '庚': '刚毅果断，刀剑之锋',   // 阳金：义气分明，执行力强
  '辛': '精致敏锐，珠玉之质',   // 阴金：敏感细腻，审美出众
  '壬': '智慧豪迈，江河奔流',   // 阳水：思维活跃，格局宏大
  '癸': '聪慧灵动，雨露润泽',   // 阴水：洞察力强，善解人意
}

// 柱名映射
const PILLAR_NAMES: Record<string, string> = {
  year: '年柱',
  month: '月柱',
  day: '日柱',
  hour: '时柱',
}

// 神煞分类配色（低饱和新中式）
const SHEN_SHA_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  '吉': { bg: 'bg-[#B89B5E]/10', text: 'text-[#9A7E47]', border: 'border-[#B89B5E]/30' },
  '中性': { bg: 'bg-[var(--wuxing-water)]/10', text: 'text-[#3570A0]', border: 'border-[var(--wuxing-water)]/30' },
  '煞': { bg: 'bg-[#6B5B95]/10', text: 'text-[#5A4D7F]', border: 'border-[#6B5B95]/30' },
}

interface TenGodsCardProps {
  data: TenGodsData
}

export function TenGodsCard({ data }: TenGodsCardProps) {
  const { pillars, hidden_gods, dominant_gods, weak_gods, god_distribution, analysis, shen_sha, shen_sha_note } = data

  // 计算十神分布的最大值（用于归一化柱状图）
  const maxCount = Math.max(...Object.values(god_distribution), 1)

  return (
    <div className="space-y-4">
      {/* 四柱十神 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] rounded-full" />
          四柱十神
        </h3>
        <div className="grid grid-cols-4 gap-3">
          {['year', 'month', 'day', 'hour'].map((pillarName) => {
            const pillar = pillars[pillarName]
            if (!pillar) return null
            const colors = TEN_GOD_COLORS[pillar.ten_god] || TEN_GOD_COLORS['比肩']
            const isDayMaster = pillar.ten_god === '日主'

            return (
              <motion.div
                key={pillarName}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center"
              >
                <p className="text-[10px] text-stone-500 mb-1.5">{PILLAR_NAMES[pillarName]}</p>
                <div className={`rounded-xl p-2.5 ${colors.bg} border ${colors.border}`}>
                  <p className="text-lg font-bold text-stone-800 mb-0.5">{pillar.ganzhi}</p>
                  <p className={`text-xs font-medium ${colors.text}`}>
                    {isDayMaster ? '日主' : pillar.ten_god}
                  </p>
                  <p className="text-[10px] text-stone-400 mt-1 leading-tight">
                    {isDayMaster
                      ? (DAY_MASTER_PERSONALITY[pillar.stem]?.slice(0, 4) || '')
                      : (TEN_GOD_DESC[pillar.ten_god]?.slice(0, 4) || '')}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* 命带神煞 */}
      {shen_sha && shen_sha.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#B89B5E] to-[#6B5B95] rounded-full" />
            命带神煞
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {shen_sha.map((s) => {
              const colors = SHEN_SHA_COLORS[s.category] || SHEN_SHA_COLORS['中性']
              return (
                <motion.div
                  key={s.name}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`rounded-xl p-3 ${colors.bg} border ${colors.border}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-sm font-semibold ${colors.text}`}>{s.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/70 text-stone-500">
                      {s.positions.join('·')}
                    </span>
                  </div>
                  <p className="text-xs text-stone-500 leading-relaxed">{s.duanyu}</p>
                </motion.div>
              )
            })}
          </div>
          {shen_sha_note && (
            <p className="text-[10px] text-stone-400 mt-3">{shen_sha_note}</p>
          )}
        </div>
      )}

      {/* 十神分布 */}
      {Object.keys(god_distribution).length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[var(--wuxing-earth)] to-[var(--wuxing-fire)] rounded-full" />
            十神分布
          </h3>
          <div className="space-y-2">
            {Object.entries(god_distribution)
              .sort(([, a], [, b]) => b - a)
              .map(([god, count]) => {
                const colors = TEN_GOD_COLORS[god] || TEN_GOD_COLORS['比肩']
                const percentage = (count / maxCount) * 100
                const isDominant = dominant_gods.includes(god)
                const isWeak = weak_gods.includes(god)

                return (
                  <div key={god} className="flex items-center gap-2">
                    <span className={`text-xs font-medium w-8 ${colors.text}`}>{god}</span>
                    <div className="flex-1 h-5 bg-stone-50 rounded-full overflow-hidden relative">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        transition={{ duration: 0.6, ease: 'easeOut' }}
                        className={`h-full rounded-full ${colors.bg.replace('/10', '/40')}`}
                      />
                      <span className="absolute inset-0 flex items-center justify-center text-[10px] text-stone-600 font-medium">
                        {count.toFixed(1)}
                      </span>
                    </div>
                    {isDominant && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-[var(--wuxing-wood)]/15 text-[var(--wuxing-wood)] rounded-full">旺</span>
                    )}
                    {isWeak && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-[var(--wuxing-metal)]/15 text-[var(--wuxing-metal)] rounded-full">弱</span>
                    )}
                  </div>
                )
              })}
          </div>
        </div>
      )}

      {/* 格局分析 */}
      {analysis && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[var(--wuxing-water)] to-[var(--wuxing-metal)] rounded-full" />
            格局分析
          </h3>
          <p className="text-sm text-stone-600 leading-relaxed">{analysis}</p>
        </div>
      )}

      {/* 藏干十神 */}
      {hidden_gods && hidden_gods.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#6B5B95] to-[#5DADE2] rounded-full" />
            地支藏干
          </h3>
          <div className="grid grid-cols-4 gap-3">
            {['year', 'month', 'day', 'hour'].map((pillarName) => {
              const pillarGods = hidden_gods.filter(g => g.pillar === pillarName)
              if (pillarGods.length === 0) return null

              return (
                <div key={pillarName} className="text-center">
                  <p className="text-[10px] text-stone-500 mb-1.5">{PILLAR_NAMES[pillarName]}</p>
                  <div className="space-y-1">
                    {pillarGods.map((god, idx) => {
                      const colors = TEN_GOD_COLORS[god.ten_god] || TEN_GOD_COLORS['比肩']
                      return (
                        <div
                          key={idx}
                          className={`text-xs px-2 py-1 rounded-lg ${colors.bg} ${colors.text} font-medium`}
                        >
                          {god.hidden_stem}·{god.ten_god}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
