'use client'

import { useState, useEffect } from 'react'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts'
import { cn } from '@/lib/utils'

const ELEMENT_CONFIG: Record<string, { color: string; emoji: string }> = {
  '金': { color: '#E5E7EB', emoji: '⚪' },
  '木': { color: '#4ADE80', emoji: '🟢' },
  '水': { color: '#60A5FA', emoji: '🔵' },
  '火': { color: '#F87171', emoji: '🔴' },
  '土': { color: '#D97706', emoji: '🟡' },
}

interface FiveElementRadarProps {
  currentData?: Record<string, number>
  suggestedData?: Record<string, number>
  xiyongShen?: string[]
  pillars?: Record<string, string>
  eightChars?: string[]
  dayMaster?: string
  elementCounts?: Record<string, number>  // 原始计数
  className?: string
}

export function FiveElementRadar({
  currentData,
  suggestedData,
  xiyongShen = [],
  pillars,
  eightChars,
  dayMaster,
  elementCounts,
  className,
}: FiveElementRadarProps) {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  const data = ['金', '木', '水', '火', '土'].map((element) => ({
    element: `${ELEMENT_CONFIG[element].emoji}${element}`,
    当前八字: currentData?.[element] || 0,
    建议补充: suggestedData?.[element] || 0,
    fullMark: 100,
    isXiyong: xiyongShen.includes(element),
  }))

  const hasCurrent = currentData && Object.values(currentData).some((v) => v > 0)
  const hasSuggested = suggestedData && Object.values(suggestedData).some((v) => v > 0)
  
  // 客户端渲染前显示占位符
  if (!mounted) {
    return (
      <div className={cn('bg-card/50 backdrop-blur rounded-xl border p-6', className)}>
        <h3 className="text-lg font-semibold mb-2">五行能量分布</h3>
        <div className="h-[320px] flex items-center justify-center">
          <div className="animate-pulse text-muted-foreground">加载中...</div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('bg-card/50 backdrop-blur rounded-xl border p-6', className)}>
      <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
        <span>五行能量分布</span>
        {xiyongShen.length > 0 && (
          <span className="text-sm font-normal text-muted-foreground">
            (喜用神: {xiyongShen.join('、')})
          </span>
        )}
      </h3>

      <ResponsiveContainer width="100%" height={320}>
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="hsl(var(--border))" />
          <PolarAngleAxis
            dataKey="element"
            tick={({ payload, x, y, textAnchor }) => {
              const element = payload.value.slice(2)
              const isXiyong = xiyongShen.includes(element)
              return (
                <text
                  x={x}
                  y={y}
                  textAnchor={textAnchor}
                  fill={isXiyong ? ELEMENT_CONFIG[element].color : 'hsl(var(--muted-foreground))'}
                  fontSize={14}
                  fontWeight={isXiyong ? 'bold' : 'normal'}
                >
                  {payload.value}
                </text>
              )
            }}
          />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />

          {hasCurrent && (
            <Radar
              name="当前八字"
              dataKey="当前八字"
              stroke="#64748b"
              strokeDasharray="4 4"
              fill="#64748b"
              fillOpacity={0.1}
              strokeWidth={2}
            />
          )}

          {hasSuggested && (
            <Radar
              name="建议补充"
              dataKey="建议补充"
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.3}
              strokeWidth={3}
            />
          )}

          <Legend verticalAlign="bottom" height={36} iconType="circle" />
        </RadarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-5 gap-2 text-center text-xs">
        {Object.entries(ELEMENT_CONFIG).map(([element, config]) => {
          const currentValue = currentData?.[element] || 0
          const count = elementCounts?.[element] || 0
          const hasData = currentValue > 0
          return (
            <div
              key={element}
              className={cn(
                'flex flex-col items-center gap-1 p-2 rounded',
                xiyongShen.includes(element) && 'bg-primary/10'
              )}
            >
              <div className="w-4 h-4 rounded-full shadow" style={{ backgroundColor: config.color }} />
              <span className={cn(xiyongShen.includes(element) && 'text-primary font-medium')}>
                {element}
              </span>
              {hasData && count > 0 && (
                <span className="text-[10px] text-muted-foreground">
                  {count}个
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* 八字显示 */}
      {pillars && (
        <div className="mt-6 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium">八字排盘</h4>
            {dayMaster && (
              <span className="text-xs text-muted-foreground">
                日元: <span className="text-primary font-medium">{dayMaster}</span>
              </span>
            )}
          </div>
          <div className="grid grid-cols-4 gap-2 text-center">
            {[
              { key: 'year', label: '年柱' },
              { key: 'month', label: '月柱' },
              { key: 'day', label: '日柱' },
              { key: 'hour', label: '时柱' },
            ].map(({ key, label }) => (
              <div key={key} className="bg-muted/50 rounded-lg p-2">
                <div className="text-xs text-muted-foreground mb-1">{label}</div>
                <div className="text-lg font-semibold tracking-wider">
                  {pillars[key] || '--'}
                </div>
              </div>
            ))}
          </div>
          {eightChars && (
            <div className="mt-3 flex justify-center gap-1 text-sm">
              {eightChars.map((char, i) => (
                <span
                  key={i}
                  className={cn(
                    'w-6 h-6 flex items-center justify-center rounded',
                    i % 2 === 0 ? 'bg-primary/10 text-primary' : 'bg-muted'
                  )}
                  title={i % 2 === 0 ? '天干' : '地支'}
                >
                  {char}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
