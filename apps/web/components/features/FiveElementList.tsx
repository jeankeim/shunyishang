'use client'

interface FiveElementListProps {
  currentData?: Record<string, number>
  suggestedData?: Record<string, number>
  xiyongShen?: string[]
  pillars?: Record<string, string>
  dayMaster?: string
}

const ELEMENT_META: { name: string; emoji: string; barColor: string }[] = [
  { name: '金', emoji: '⚔️', barColor: 'bg-[#9CAFB8]' },
  { name: '木', emoji: '🌳', barColor: 'bg-[#3DA35D]' },
  { name: '水', emoji: '💧', barColor: 'bg-[#4A90C4]' },
  { name: '火', emoji: '🔥', barColor: 'bg-[#C75B5B]' },
  { name: '土', emoji: '🌍', barColor: 'bg-[#B89B5E]' },
]

const PILLAR_NAMES: Record<string, string> = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' }

function getStatus(value: number, isXiyong: boolean) {
  if (value === 0) return { tag: '缺失', tagCls: 'bg-stone-100 text-stone-500' }
  if (isXiyong) {
    if (value >= 50) return { tag: '充沛', tagCls: 'bg-emerald-50 text-emerald-600' }
    return { tag: '需补充', tagCls: 'bg-amber-50 text-amber-600' }
  }
  if (value >= 50) return { tag: '偏旺', tagCls: 'bg-red-50 text-red-500' }
  return { tag: '适中', tagCls: 'bg-stone-50 text-stone-400' }
}

export function FiveElementList({ currentData, xiyongShen = [], pillars, dayMaster }: FiveElementListProps) {
  const hasData = currentData && Object.values(currentData).some(v => v > 0)

  // 穿搭建议：需要补充的喜用神 + 需要减少的偏旺元素
  const needBoost = ELEMENT_META.filter(el => xiyongShen.includes(el.name) && (currentData?.[el.name] || 0) < 50)
  const tooStrong = ELEMENT_META.filter(el => !xiyongShen.includes(el.name) && (currentData?.[el.name] || 0) >= 50)

  // 八字四柱
  const pillarKeys = ['year', 'month', 'day', 'hour'] as const
  const hasPillars = pillars && Object.values(pillars).some(v => v)

  return (
    <div className="space-y-3 p-4 bg-white/80 rounded-xl">
      {/* 八字四柱 */}
      {hasPillars && (
        <div className="mb-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-[var(--brand-heading)]">我的八字</h3>
            {dayMaster && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-stone-100 text-stone-500 font-medium">
                日元: {dayMaster}
              </span>
            )}
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {pillarKeys.map(key => {
              const gz = pillars?.[key]
              if (!gz) return null
              return (
                <div key={key} className="text-center bg-[var(--brand-surface)]/60 rounded-lg py-1.5">
                  <p className="text-[10px] text-stone-400 mb-0.5">{PILLAR_NAMES[key]}</p>
                  <p className="text-sm font-bold text-[var(--brand-heading)] tracking-wider">{gz}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 分割线 */}
      {hasPillars && <div className="border-t border-stone-100" />}

      {/* 五行分析 */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[var(--brand-heading)]">五行分析</h3>
        {xiyongShen.length > 0 && (
          <span className="text-xs px-2 py-1 bg-gradient-to-r from-[var(--brand-surface)] to-[var(--brand-surface-active)] text-[#3DA35D] rounded-full font-medium">
            喜用: {xiyongShen.join('、')}
          </span>
        )}
      </div>

      {/* 五行进度条 */}
      <div className="space-y-2.5">
        {ELEMENT_META.map(el => {
          const value = Math.round(currentData?.[el.name] || 0)
          const isXiyong = xiyongShen.includes(el.name)
          const status = getStatus(value, isXiyong)

          return (
            <div key={el.name} className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 w-12 shrink-0">
                <span className="text-sm">{el.emoji}</span>
                <span className={`text-xs font-medium ${isXiyong ? 'text-[var(--brand-heading)]' : 'text-stone-500'}`}>
                  {el.name}
                </span>
              </div>
              <div className="flex-1 h-2 bg-[var(--brand-surface)] rounded-full overflow-hidden">
                <div
                  className={`h-full ${el.barColor} transition-all duration-500 rounded-full`}
                  style={{ width: `${value}%` }}
                />
              </div>
              <span className="text-[11px] text-[var(--brand-subtle)] w-8 text-right tabular-nums">{value}%</span>
              {hasData && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap ${status.tagCls}`}>
                  {status.tag}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* 穿搭建议 */}
      {hasData && xiyongShen.length > 0 && (
        <div className="pt-2 mt-1 border-t border-stone-100">
          <p className="text-[11px] text-stone-500 leading-relaxed">
            <span className="text-[#3DA35D] font-medium">💡 穿搭建议：</span>
            {needBoost.length > 0 && (
              <span>宜多用{needBoost.map(e => e.name).join('、')}元素{tooStrong.length > 0 ? '，' : ''}</span>
            )}
            {tooStrong.length > 0 && (
              <span>减少{tooStrong.map(e => e.name).join('、')}元素</span>
            )}
            {needBoost.length === 0 && tooStrong.length === 0 && (
              <span>五行均衡，保持当前风格即可</span>
            )}
          </p>
        </div>
      )}
    </div>
  )
}
