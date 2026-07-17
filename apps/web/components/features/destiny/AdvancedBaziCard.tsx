'use client'

import { motion } from 'framer-motion'
import type { AdvancedBaziData } from '@/store/destiny'

// 五行颜色
const ELEMENT_COLORS: Record<string, { bg: string; text: string }> = {
  '金': { bg: 'bg-[#8A9BA8]/15', text: 'text-[#6B7F8C]' },
  '木': { bg: 'bg-[#3DA35D]/15', text: 'text-[#2D7A45]' },
  '水': { bg: 'bg-[#4A90C4]/15', text: 'text-[#3570A0]' },
  '火': { bg: 'bg-[#C75B5B]/15', text: 'text-[#A84545]' },
  '土': { bg: 'bg-[#B89B5E]/15', text: 'text-[#9A7E47]' },
}

const PILLAR_NAMES: Record<string, string> = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' }

// 关系类型图标和颜色
const RELATION_STYLES: Record<string, { icon: string; color: string; bg: string }> = {
  chong: { icon: '⚡', color: 'text-red-600', bg: 'bg-red-50 border-red-100' },
  xing: { icon: '⚠️', color: 'text-orange-600', bg: 'bg-orange-50 border-orange-100' },
  hai: { icon: '💔', color: 'text-amber-600', bg: 'bg-amber-50 border-amber-100' },
  he: { icon: '🤝', color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-100' },
}

interface AdvancedBaziCardProps {
  data: AdvancedBaziData
}

export function AdvancedBaziCard({ data }: AdvancedBaziCardProps) {
  const { nayin, hidden_stems, chong, xing, hai, he, analysis } = data

  // 收集所有刑冲克害关系
  const relations: Array<{ type: string; items: Array<{ description: string; branches?: string[]; element?: string }> }> = []
  if (chong.has_chong) relations.push({ type: 'chong', items: chong.pairs })
  if (xing.has_xing) relations.push({ type: 'xing', items: xing.groups })
  if (hai.has_hai) relations.push({ type: 'hai', items: hai.pairs })
  if (he.has_he) {
    const heItems = [...he.sanhe, ...he.liuhe.map(l => ({ ...l, description: l.description }))]
    relations.push({ type: 'he', items: heItems })
  }

  return (
    <div className="space-y-4">
      {/* 纳音五行 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#B89B5E] to-[#C75B5B] rounded-full" />
          纳音五行
        </h3>
        <div className="grid grid-cols-4 gap-2">
          {['year', 'month', 'day', 'hour'].map((pillar) => {
            const item = nayin[pillar]
            if (!item) return null
            const colors = ELEMENT_COLORS[item.nayin_element] || ELEMENT_COLORS['土']

            return (
              <motion.div
                key={pillar}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center"
              >
                <p className="text-[10px] text-stone-400 mb-1">{PILLAR_NAMES[pillar]}</p>
                <div className={`rounded-xl p-2.5 ${colors.bg}`}>
                  <p className="text-sm font-bold text-stone-800">{item.nayin_name}</p>
                  <span className={`text-[10px] font-medium ${colors.text}`}>{item.nayin_element}</span>
                </div>
                <p className="text-[10px] text-stone-400 mt-1 leading-tight line-clamp-2">{item.nayin_description}</p>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* 地支藏干 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#6B5B95] to-[#5DADE2] rounded-full" />
          地支藏干详解
        </h3>
        <div className="grid grid-cols-4 gap-3">
          {['year', 'month', 'day', 'hour'].map((pillar) => {
            const stems = hidden_stems[pillar]
            if (!stems || stems.length === 0) return null

            return (
              <div key={pillar} className="text-center">
                <p className="text-[10px] text-stone-400 mb-1.5">{PILLAR_NAMES[pillar]}</p>
                <div className="space-y-1">
                  {stems.map((stem, idx) => {
                    const colors = ELEMENT_COLORS[stem.element] || ELEMENT_COLORS['土']
                    return (
                      <div
                        key={idx}
                        className={`flex items-center justify-between px-2 py-1 rounded-lg ${colors.bg}`}
                      >
                        <span className={`text-xs font-bold ${colors.text}`}>{stem.stem}</span>
                        <span className="text-[10px] text-stone-400">{stem.element}</span>
                        {stem.is_main && <span className="text-[10px] text-stone-400">主</span>}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 刑冲克害 */}
      {relations.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#C75B5B] to-[#B89B5E] rounded-full" />
            刑冲克害
          </h3>
          <div className="space-y-2">
            {relations.map((rel, idx) => {
              const style = RELATION_STYLES[rel.type] || RELATION_STYLES.chong
              const typeName = { chong: '六冲', xing: '刑', hai: '六害', he: '合' }[rel.type] || rel.type

              return (
                <div key={idx} className={`flex items-start gap-2 p-2.5 rounded-xl border ${style.bg}`}>
                  <span className="text-base">{style.icon}</span>
                  <div className="flex-1">
                    <span className={`text-xs font-semibold ${style.color}`}>{typeName}</span>
                    {rel.items.map((item, i) => (
                      <p key={i} className="text-xs text-stone-600 mt-0.5">{item.description}</p>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 无刑冲克害 */}
      {relations.length === 0 && (
        <div className="bg-emerald-50/50 rounded-2xl p-4 border border-emerald-100">
          <p className="text-sm text-emerald-700 text-center">
            ✨ 四柱地支无明显刑冲克害，格局较为平和
          </p>
        </div>
      )}

      {/* 综合分析 */}
      {analysis && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-gradient-to-r from-[#4A90C4] to-[#9CAFB8] rounded-full" />
            综合分析
          </h3>
          <p className="text-sm text-stone-600 leading-relaxed">{analysis}</p>
        </div>
      )}
    </div>
  )
}
