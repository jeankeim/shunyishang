'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TenGodsCard } from '@/components/features/destiny/TenGodsCard'
import { AnnualLuckCard } from '@/components/features/destiny/AnnualLuckCard'
import { MajorLuckCard } from '@/components/features/destiny/MajorLuckCard'
import { AdvancedBaziCard } from '@/components/features/destiny/AdvancedBaziCard'
import { useDestinyStore } from '@/store/destiny'
import { useUserStore } from '@/store/user'

type DestinyTab = 'ten-gods' | 'annual' | 'major' | 'advanced'

const TABS: Array<{ id: DestinyTab; label: string; icon: string }> = [
  { id: 'ten-gods', label: '十神格局', icon: '☯️' },
  { id: 'annual', label: '流年运势', icon: '📅' },
  { id: 'major', label: '大运周期', icon: '🔄' },
  { id: 'advanced', label: '高级分析', icon: '🔬' },
]

export default function DestinyPage() {
  const {
    tenGods, isTenGodsLoading, tenGodsError,
    majorLuck, isMajorLuckLoading, majorLuckError,
    annualLuck, isAnnualLuckLoading, annualLuckError,
    advancedBazi, isAdvancedBaziLoading, advancedBaziError,
    fetchTenGods, fetchMajorLuck, fetchAnnualLuck, fetchAdvancedBazi, fetchAll, clearErrors,
  } = useDestinyStore()
  const { isAuthenticated } = useUserStore()
  const [activeTab, setActiveTab] = useState<DestinyTab>('ten-gods')

  useEffect(() => {
    if (isAuthenticated) {
      fetchAll()
    }
    return () => clearErrors()
  }, [isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <p className="text-4xl mb-3">🔮</p>
        <h2 className="text-lg font-semibold text-stone-800 mb-2">命理分析</h2>
        <p className="text-sm text-stone-500 mb-4">登录后即可查看基于您八字的深度命理分析</p>
      </div>
    )
  }

  const isLoading = isTenGodsLoading && isAnnualLuckLoading && isMajorLuckLoading && isAdvancedBaziLoading
  const hasAnyData = tenGods || annualLuck || majorLuck || advancedBazi

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-stone-800">命理分析</h1>
          <p className="text-xs text-stone-500 mt-0.5">基于八字的多维度深度解读</p>
        </div>
        <motion.button
          whileTap={{ scale: 0.95 }}
          onClick={() => fetchAll()}
          disabled={isLoading}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm disabled:opacity-60"
        >
          {isLoading ? '分析中...' : '重新分析'}
        </motion.button>
      </div>

      {/* Tab 导航 */}
      <div className="flex gap-1 bg-stone-100/80 rounded-xl p-1">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          const hasError = (tab.id === 'ten-gods' && tenGodsError) ||
                          (tab.id === 'annual' && annualLuckError) ||
                          (tab.id === 'major' && majorLuckError) ||
                          (tab.id === 'advanced' && advancedBaziError)

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-1 px-2 py-2 rounded-lg text-xs font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-white text-stone-800 shadow-sm'
                  : 'text-stone-500 hover:text-stone-700'
              }`}
            >
              <span className="text-sm">{tab.icon}</span>
              <span className="hidden sm:inline">{tab.label}</span>
              {hasError && <span className="w-1.5 h-1.5 bg-red-400 rounded-full" />}
            </button>
          )
        })}
      </div>

      {/* Tab 内容 */}
      <AnimatePresence mode="wait">
        {activeTab === 'ten-gods' && (
          <motion.div
            key="ten-gods"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {isTenGodsLoading && !tenGods ? (
              <LoadingSkeleton />
            ) : tenGods ? (
              <TenGodsCard data={tenGods} />
            ) : (
              <EmptyState error={tenGodsError} onRetry={fetchTenGods} />
            )}
          </motion.div>
        )}

        {activeTab === 'annual' && (
          <motion.div
            key="annual"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {isAnnualLuckLoading && !annualLuck ? (
              <LoadingSkeleton />
            ) : annualLuck ? (
              <AnnualLuckCard data={annualLuck} />
            ) : (
              <EmptyState error={annualLuckError} onRetry={() => fetchAnnualLuck()} />
            )}
          </motion.div>
        )}

        {activeTab === 'major' && (
          <motion.div
            key="major"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {isMajorLuckLoading && !majorLuck ? (
              <LoadingSkeleton />
            ) : majorLuck ? (
              <MajorLuckCard luckPeriods={majorLuck.luck_periods} currentLuck={majorLuck.current_luck} />
            ) : (
              <EmptyState error={majorLuckError} onRetry={fetchMajorLuck} />
            )}
          </motion.div>
        )}

        {activeTab === 'advanced' && (
          <motion.div
            key="advanced"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {isAdvancedBaziLoading && !advancedBazi ? (
              <LoadingSkeleton />
            ) : advancedBazi ? (
              <AdvancedBaziCard data={advancedBazi} />
            ) : (
              <EmptyState error={advancedBaziError} onRetry={fetchAdvancedBazi} />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100 animate-pulse">
          <div className="h-4 bg-stone-100 rounded w-1/3 mb-3" />
          <div className="grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map((j) => (
              <div key={j} className="h-16 bg-stone-50 rounded-xl" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ error, onRetry }: { error: string | null; onRetry: () => void }) {
  if (error) {
    return (
      <div className="text-center py-8 bg-white rounded-2xl border border-stone-100">
        <p className="text-2xl mb-2">⚠️</p>
        <p className="text-sm text-red-500 mb-3">{error}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 text-sm text-[hsl(var(--primary))] hover:bg-[var(--brand-surface)] rounded-lg transition-colors"
        >
          重试
        </button>
      </div>
    )
  }

  return (
    <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
      <p className="text-3xl mb-2">🌟</p>
      <p className="text-sm text-stone-500">暂无命理数据</p>
      <p className="text-xs text-stone-400 mt-1">点击上方按钮开始分析</p>
    </div>
  )
}
