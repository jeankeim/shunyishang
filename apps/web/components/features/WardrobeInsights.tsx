'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3, Flame, Snowflake, Sun, Leaf,
  TrendingUp, TrendingDown, Package, Eye
} from 'lucide-react'
import {
  getWardrobeAnalytics,
  type WardrobeAnalytics,
  type FreqItem,
  type SeasonalPattern,
} from '@/lib/api'

/** 五行元素颜色 */
const ELEM_COLORS: Record<string, string> = {
  '金': '#9CAFB8', '木': '#3DA35D', '水': '#4A90C4', '火': '#C75B5B', '土': '#B89B5E',
}

/** 季节配置 */
const SEASON_CONFIG: Record<string, { label: string; icon: typeof Sun; color: string }> = {
  spring: { label: '春', icon: Leaf,   color: '#3DA35D' },
  summer: { label: '夏', icon: Sun,    color: '#C75B5B' },
  autumn: { label: '秋', icon: Leaf,   color: '#B89B5E' },
  winter: { label: '冬', icon: Snowflake, color: '#4A90C4' },
}

export function WardrobeInsights() {
  const [data, setData] = useState<WardrobeAnalytics | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'freq' | 'season' | 'weather' | 'stats'>('freq')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getWardrobeAnalytics().then(result => {
      if (!cancelled) {
        setData(result)
        setLoading(false)
      }
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  // ── 加载中 ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[var(--brand-border)]/40 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[var(--wuxing-earth)]/20 to-[var(--wuxing-fire)]/20 flex items-center justify-center">
            <BarChart3 className="w-3.5 h-3.5 text-[var(--wuxing-earth)]" />
          </div>
          <span className="text-sm font-semibold text-[var(--brand-heading)]">衣橱洞察</span>
        </div>
        <div className="flex items-center justify-center py-8 gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--wuxing-earth)] border-t-transparent" />
          <span className="text-sm text-[var(--brand-subtle)]">正在分析衣橱数据...</span>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { frequency_analysis, seasonal_patterns, weather_adaptability, overall_stats } = data

  // ── 空衣橱 ─────────────────────────────────────────────────────────────────
  if (overall_stats.total_items === 0) {
    return (
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-[var(--brand-border)]/40 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 className="w-4 h-4 text-[var(--brand-subtle)]" />
          <span className="text-sm font-semibold text-[var(--brand-heading)]">衣橱洞察</span>
        </div>
        <p className="text-sm text-[var(--brand-subtle)]">添加衣物后可查看穿着分析</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl shadow-sm border border-[var(--brand-border)]/40 mb-4 overflow-hidden"
    >
      {/* 头部 */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[#B89B5E]/20 to-[#C75B5B]/20 flex items-center justify-center">
            <BarChart3 className="w-3.5 h-3.5 text-[#B89B5E]" />
          </div>
          <span className="text-sm font-semibold text-[var(--brand-heading)]">衣橱洞察</span>
          <span className="ml-auto text-xs text-[var(--brand-subtle)]">
            共 {overall_stats.total_items} 件
          </span>
        </div>

        {/* Tab 切换 */}
        <div className="flex gap-1 bg-[var(--brand-bg)]/50 rounded-lg p-0.5">
          {[
            { key: 'freq',    label: '穿着频率' },
            { key: 'season',  label: '季节模式' },
            { key: 'weather', label: '天气适应' },
            { key: 'stats',   label: '总体统计' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as typeof activeTab)}
              className={`flex-1 text-xs py-1.5 rounded-md transition-all ${
                activeTab === tab.key
                  ? 'bg-white text-[var(--brand-heading)] shadow-sm font-medium'
                  : 'text-[var(--brand-subtle)] hover:text-[var(--brand-heading)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 内容区 */}
      <div className="px-4 pb-4 pt-2">
        {activeTab === 'freq' && <FrequencyPanel data={frequency_analysis} />}
        {activeTab === 'season' && <SeasonPanel patterns={seasonal_patterns} />}
        {activeTab === 'weather' && <WeatherPanel data={weather_adaptability} />}
        {activeTab === 'stats' && <StatsPanel stats={overall_stats} />}
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────────
// 穿着频率面板
// ─────────────────────────────────────────────────────────────────────────────────
function FrequencyPanel({ data }: { data: WardrobeAnalytics['frequency_analysis'] }) {
  const { high_freq_items, low_freq_items, redundant_items, summary } = data

  return (
    <div className="space-y-3">
      {/* 汇总条 */}
      <div className="flex gap-2">
        <StatBadge icon={TrendingUp} label="高频" value={summary.high_freq_count} color="#3DA35D" />
        <StatBadge icon={TrendingDown} label="低频" value={summary.low_freq_count} color="#C75B5B" />
        <StatBadge icon={Package} label="冗余" value={summary.redundant_count} color="#B89B5E" />
      </div>

      {/* 高频物品 */}
      {high_freq_items.length > 0 && (
        <FreqSection title="高频穿着" items={high_freq_items} color="#3DA35D" />
      )}

      {/* 低频物品 */}
      {low_freq_items.length > 0 && (
        <FreqSection title="低频穿着" items={low_freq_items.slice(0, 6)} color="#C75B5B" />
      )}

      {/* 冗余提示 */}
      {redundant_items.length > 0 && (
        <div className="bg-[#B89B5E]/5 rounded-lg p-2.5">
          <p className="text-xs font-medium text-[#B89B5E] mb-1.5">冗余提醒</p>
          <div className="space-y-1">
            {redundant_items.slice(0, 3).map(item => (
              <div key={item.id} className="flex items-center gap-2">
                <span className="text-xs text-[var(--brand-text)] truncate flex-1">{item.name}</span>
                <span className="text-[10px] text-[var(--brand-subtle)]">{item.extra_info}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {high_freq_items.length === 0 && low_freq_items.length === 0 && (
        <p className="text-xs text-[var(--brand-subtle)] text-center py-4">
          穿着更多衣物后，这里会显示穿着频率分析
        </p>
      )}
    </div>
  )
}

function FreqSection({ title, items, color }: { title: string; items: FreqItem[]; color: string }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <div className="w-1 h-3 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-xs font-medium text-[var(--brand-heading)]">{title}</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {items.slice(0, 8).map(item => (
          <div
            key={item.id}
            className="flex-shrink-0 w-16 text-center group cursor-default"
          >
            {item.image_url ? (
              <img
                src={item.image_url}
                alt={item.name}
                className="w-16 h-16 rounded-lg object-cover border border-[var(--brand-border)]/40"
              />
            ) : (
              <div
                className="w-16 h-16 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: (ELEM_COLORS[item.primary_element || ''] || '#E8E8E8') + '20' }}
              >
                <span className="text-lg">
                  {item.primary_element ? (
                    <span style={{ color: ELEM_COLORS[item.primary_element] }}>{item.primary_element}</span>
                  ) : '📦'}
                </span>
              </div>
            )}
            <p className="text-[10px] text-[var(--brand-text)] truncate mt-1">{item.name}</p>
            <p className="text-[10px] text-[var(--brand-subtle)]">{item.wear_count}次</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────────
// 季节模式面板
// ─────────────────────────────────────────────────────────────────────────────────
function SeasonPanel({ patterns }: { patterns: WardrobeAnalytics['seasonal_patterns'] }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {Object.entries(patterns).map(([key, pattern]) => {
        const config = SEASON_CONFIG[key] || { label: key, icon: Sun, color: '#999' }
        const Icon = config.icon
        const hasData = pattern.total_records > 0

        return (
          <div
            key={key}
            className="rounded-lg p-2.5 border border-[var(--brand-border)]/30"
            style={{ backgroundColor: config.color + '08' }}
          >
            <div className="flex items-center gap-1.5 mb-1.5">
              <Icon className="w-3.5 h-3.5" style={{ color: config.color }} />
              <span className="text-xs font-medium" style={{ color: config.color }}>
                {config.label}季
              </span>
              {hasData && (
                <span className="ml-auto text-[10px] text-[var(--brand-subtle)]">
                  {pattern.total_records}次记录
                </span>
              )}
            </div>

            {hasData ? (
              <div className="space-y-1">
                {pattern.top_categories.length > 0 && (
                  <div className="text-[10px] text-[var(--brand-text)]">
                    <span className="text-[var(--brand-subtle)]">品类：</span>
                    {pattern.top_categories.map(c => c.name).join('、')}
                  </div>
                )}
                {pattern.top_elements.length > 0 && (
                  <div className="flex gap-1">
                    {pattern.top_elements.map(e => (
                      <span
                        key={e.name}
                        className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: (ELEM_COLORS[e.name] || '#999') + '20',
                          color: ELEM_COLORS[e.name] || '#666',
                        }}
                      >
                        {e.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-[10px] text-[var(--brand-subtle)]">暂无数据</p>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────────
// 天气适应性面板
// ─────────────────────────────────────────────────────────────────────────────────
function WeatherPanel({ data }: { data: WardrobeAnalytics['weather_adaptability'] }) {
  const buckets = [
    { key: 'cold', icon: Snowflake, color: '#4A90C4' },
    { key: 'mild', icon: Sun,       color: '#3DA35D' },
    { key: 'warm', icon: Sun,       color: '#B89B5E' },
    { key: 'hot',  icon: Flame,     color: '#C75B5B' },
  ] as const

  return (
    <div className="space-y-2">
      {buckets.map(({ key, icon: Icon, color }) => {
        const bucket = data[key]
        if (!bucket) return null
        return (
          <div key={key} className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: color + '15' }}
            >
              <Icon className="w-4 h-4" style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-[var(--brand-heading)]">{bucket.label}</span>
                <span className="text-[10px] text-[var(--brand-subtle)]">
                  {bucket.total_records > 0 ? `${bucket.total_records}次记录` : '暂无数据'}
                </span>
              </div>
              {bucket.preferred_items.length > 0 && (
                <p className="text-[10px] text-[var(--brand-text)] truncate">
                  偏好：{bucket.preferred_items.slice(0, 3).map(i => i.name.split('|')[0]).join('、')}
                </p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────────
// 总体统计面板
// ─────────────────────────────────────────────────────────────────────────────────
function StatsPanel({ stats }: { stats: WardrobeAnalytics['overall_stats'] }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <StatCard label="总件数" value={stats.total_items} />
      <StatCard label="活跃件数" value={stats.active_items} />
      <StatCard label="平均穿着" value={`${stats.avg_wear_count}次`} />
      <StatCard label="总穿着次数" value={stats.total_wear_count} />
      {stats.most_worn_category && (
        <StatCard label="最常穿品类" value={stats.most_worn_category} />
      )}
      {stats.most_worn_element && (
        <div className="bg-[var(--brand-bg)]/50 rounded-lg p-2.5">
          <p className="text-[10px] text-[var(--brand-subtle)] mb-0.5">最常穿五行</p>
          <span
            className="text-sm font-semibold"
            style={{ color: ELEM_COLORS[stats.most_worn_element] || 'var(--brand-heading)' }}
          >
            {stats.most_worn_element}
          </span>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────────
// 子组件
// ─────────────────────────────────────────────────────────────────────────────────
function StatBadge({ icon: Icon, label, value, color }: {
  icon: typeof TrendingUp; label: string; value: number; color: string
}) {
  return (
    <div
      className="flex-1 flex items-center gap-1.5 rounded-lg px-2.5 py-1.5"
      style={{ backgroundColor: color + '10' }}
    >
      <Icon className="w-3 h-3" style={{ color }} />
      <span className="text-[10px] text-[var(--brand-subtle)]">{label}</span>
      <span className="ml-auto text-xs font-semibold" style={{ color }}>{value}</span>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-[var(--brand-bg)]/50 rounded-lg p-2.5">
      <p className="text-[10px] text-[var(--brand-subtle)] mb-0.5">{label}</p>
      <p className="text-sm font-semibold text-[var(--brand-heading)]">{value}</p>
    </div>
  )
}
