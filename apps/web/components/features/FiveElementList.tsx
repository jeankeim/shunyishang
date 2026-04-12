'use client'

interface FiveElementListProps {
  currentData?: Record<string, number>
  suggestedData?: Record<string, number>
  xiyongShen?: string[]
}

export function FiveElementList({ currentData, suggestedData, xiyongShen }: FiveElementListProps) {
  const elements = [
    { name: '金', key: 'metal', color: 'bg-[#C5D0D8]', emoji: '⚔️', current: currentData?.metal || 0, suggested: suggestedData?.metal || 0 },
    { name: '木', key: 'wood', color: 'bg-[#3DA35D]', emoji: '🌳', current: currentData?.wood || 0, suggested: suggestedData?.wood || 0 },
    { name: '水', key: 'water', color: 'bg-[#4A90C4]', emoji: '💧', current: currentData?.water || 0, suggested: suggestedData?.water || 0 },
    { name: '火', key: 'fire', color: 'bg-[#D4656B]', emoji: '🔥', current: currentData?.fire || 0, suggested: suggestedData?.fire || 0 },
    { name: '土', key: 'earth', color: 'bg-[#B89B5E]', emoji: '🌍', current: currentData?.earth || 0, suggested: suggestedData?.earth || 0 },
  ]
  
  return (
    <div className="space-y-3 p-4 bg-white/80 rounded-xl">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#2D4A38]">五行分析</h3>
        {xiyongShen && xiyongShen.length > 0 && (
          <span className="text-xs px-2 py-1 bg-gradient-to-r from-[#F0F7F4] to-[#E8F5EC] text-[#3DA35D] rounded-full font-medium">
            喜用: {xiyongShen.join(', ')}
          </span>
        )}
      </div>
      
      <div className="space-y-2.5">
        {elements.map(el => (
          <div key={el.key} className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">{el.emoji}</span>
                <span className="text-[#2D4A38] font-medium">{el.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[#6B7F72]">现 {Math.round(el.current * 100)}%</span>
                {el.suggested > 0 && (
                  <span className="text-[#3DA35D] font-medium">→ {Math.round(el.suggested * 100)}%</span>
                )}
              </div>
            </div>
            <div className="h-2 bg-[#F0F7F4] rounded-full overflow-hidden">
              <div 
                className={`h-full ${el.color} transition-all duration-500 rounded-full`}
                style={{ width: `${el.current * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
