'use client'

import { useState, useEffect, lazy, Suspense } from 'react'
// Image from 'next/image' 已移除：OSS 默认域名 Content-Disposition:attachment 导致 Image 组件服务端优化失败，改用原生 img
import { motion, AnimatePresence } from 'framer-motion'
import { useWardrobeStore } from '@/store/wardrobe'
import { useUserStore } from '@/store/user'
import { SwipeToDelete } from '@/components/features/SwipeToDelete'
import { WUXING_ELEMENTS, WUXING_CONFIG, getWuxingConfig } from '@/lib/wuxing-config'
import type { WardrobeItem } from '@/lib/api'
import { getWardrobeFilterStats, type WardrobeFilterStats } from '@/lib/api'
import { getImageUrl } from '@/lib/image'
import { EmptyState, SkeletonList, ConfirmDialog } from '@/components/ui'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { WardrobeInsights } from '@/components/features/WardrobeInsights'
import { WuxingBaguaChart } from '@/components/features/WuxingBaguaChart'
import { IdleItemsCard } from '@/components/features/IdleItemsCard'
import { WardrobeCabinet } from '@/components/features/WardrobeCabinet'
import { WardrobeItemViewer } from '@/components/features/WardrobeItemViewer'
import { IDLE_BADGE_MIN_DAYS, idleBadgeClass } from '@/lib/wardrobe-display'

const AddWardrobeModal = lazy(() => import('@/components/features/AddWardrobeModal').then(m => ({ default: m.AddWardrobeModal })))
const BatchUploadModal = lazy(() => import('@/components/features/BatchUploadModal'))

// 五行数据配置 - 春分优化版
const WUXING_THEME: Record<string, { color: string; gradient: string; symbol: string; pattern: string }> = {
  '金': { color: '#9CAFB8', gradient: 'from-[#F5F7F9] via-[#F0F2F5] to-[#E8EBF0]', symbol: '☰', pattern: 'cloud' },
  '木': { color: '#3DA35D', gradient: 'from-[#F0F9F4] via-[#E8F5EC] to-[#D4E8DC]', symbol: '☳', pattern: 'leaf' },
  '水': { color: '#4A90C4', gradient: 'from-[#F0F7FA] via-[#E8F0F8] to-[#D4E4F0]', symbol: '☵', pattern: 'wave' },
  '火': { color: '#C75B5B', gradient: 'from-[#FDF2F2] via-[#FBE8E8] to-[#F5D4D4]', symbol: '☲', pattern: 'flame' },
  '土': { color: '#B89B5E', gradient: 'from-[#F9F5EC] via-[#F5F0E0] to-[#EDE5D0]', symbol: '☷', pattern: 'mountain' },
}

// 多维筛选状态（与后端列表接口筛选参数一一对应）
interface WardrobeFilters {
  element: string | null
  category: string | null
  season: string | null
  weather: string | null
  thickness: string | null
  color_family: string | null
}

const EMPTY_FILTERS: WardrobeFilters = {
  element: null, category: null, season: null,
  weather: null, thickness: null, color_family: null,
}

// 筛选栏维度配置（选项与后端词表对齐：ai_tagging_service / COLOR_FAMILY_KEYWORDS）
const FILTER_DIMENSIONS: { key: keyof WardrobeFilters; label: string; options: string[] }[] = [
  { key: 'element', label: '五行', options: ['金', '木', '水', '火', '土'] },
  { key: 'category', label: '品类', options: ['上装', '下装', '外套', '裙装', '套装', '鞋履', '配饰'] },
  { key: 'season', label: '季节', options: ['春', '夏', '秋', '冬'] },
  { key: 'weather', label: '天气', options: ['晴', '多云', '阴', '雨', '雪'] },
  { key: 'thickness', label: '厚度', options: ['轻薄', '适中', '加厚', '厚重'] },
  { key: 'color_family', label: '色系', options: ['白色系', '黑色系', '灰色系', '红色系', '蓝色系', '绿色系', '黄棕色系', '粉紫色系'] },
]

/** 筛选状态 → 列表接口请求参数（剔除空值） */
function toFetchParams(f: WardrobeFilters) {
  const params: Partial<Record<keyof WardrobeFilters, string>> = {}
  ;(Object.keys(f) as (keyof WardrobeFilters)[]).forEach((k) => {
    const v = f[k]
    if (v) params[k] = v
  })
  return params
}

// 闲置徽标阈值与分级配色见 @/lib/wardrobe-display（柜体抽屉视图与网格视图共用）

export default function WardrobePage() {
  const { items, total, elementStats, isLoading, fetchItems, deleteItem } = useWardrobeStore()
  const { isAuthenticated } = useUserStore()
  
  const [filters, setFilters] = useState<WardrobeFilters>({ ...EMPTY_FILTERS })
  const [filterStats, setFilterStats] = useState<WardrobeFilterStats | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false)
  const [editItem, setEditItem] = useState<WardrobeItem | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  // cabinet = 品类抽屉柜（默认）；grid / flow = 平铺网格
  const [viewMode, setViewMode] = useState<'cabinet' | 'grid' | 'flow'>('cabinet')
  // 放大查看的衣物（柜体抽屉与网格卡片点击共用）
  const [zoomItem, setZoomItem] = useState<WardrobeItem | null>(null)
  
  // 判断是否移动端
  const isMobile = useMediaQuery('(max-width: 768px)')

  useEffect(() => {
    if (isAuthenticated) {
      fetchItems()
      refreshStats(EMPTY_FILTERS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, fetchItems])

  /** 拉取筛选栏实时计数（失败静默，不阻断页面） */
  const refreshStats = (f: WardrobeFilters) => {
    getWardrobeFilterStats(toFetchParams(f))
      .then(setFilterStats)
      .catch(() => undefined)
  }

  /** 点击筛选 chips：再次点击同值取消；变更后走列表接口服务端筛选 */
  const updateFilter = (key: keyof WardrobeFilters, value: string) => {
    const next = { ...filters, [key]: filters[key] === value ? null : value }
    setFilters(next)
    fetchItems(toFetchParams(next))
    refreshStats(next)
  }

  const clearFilters = () => {
    setFilters({ ...EMPTY_FILTERS })
    fetchItems()
    refreshStats(EMPTY_FILTERS)
  }

  const hasActiveFilter = (Object.values(filters) as (string | null)[]).some(Boolean)

  // 衣橱是否真的为空（区别于筛选无结果）：优先用统计接口总数判定
  const wardrobeEmpty = filterStats ? filterStats.total === 0 : (!hasActiveFilter && total === 0)

  const handleDelete = async (itemId: number) => {
    setConfirmDeleteId(itemId)
  }

  const doDeleteItem = async () => {
    if (!confirmDeleteId) return
    setDeletingId(confirmDeleteId)
    try {
      await deleteItem(confirmDeleteId)
      refreshStats(filters)
    } finally {
      setDeletingId(null)
      setConfirmDeleteId(null)
    }
  }

  const handleAddNew = () => {
    setEditItem(null)
    setIsModalOpen(true)
  }

  // 多维筛选已由列表接口服务端完成，前端直接渲染 items


  // 未登录状态
  if (!isAuthenticated) {
    return (
      <div className="min-h-full flex items-center justify-center relative overflow-visible py-12">
        {/* 背景装饰 */}
        <div className="absolute inset-0 overflow-visible pointer-events-none">
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-64 h-64 rounded-full opacity-20"
              style={{
                background: `radial-gradient(circle, ${Object.values(WUXING_THEME)[i].color} 0%, transparent 70%)`,
                left: `${20 + i * 15}%`,
                top: `${10 + (i % 3) * 25}%`,
              }}
              animate={{
                scale: [1, 1.2, 1],
                x: [0, 20, 0],
                y: [0, -10, 0],
              }}
              transition={{
                duration: 8 + i * 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md mx-auto px-6 relative z-10"
        >
          <div className="w-36 h-36 mx-auto mb-8 relative">
            {/* 柔和光晕 */}
            <div className="absolute inset-4 rounded-full bg-gradient-to-br from-[#3DA35D]/10 to-[#4A90C4]/10 blur-xl" />
            {/* 引导圆环 */}
            <div className="absolute inset-3 rounded-full border border-[var(--brand-heading)]/10" />
            {/* 旋转的五行环 */}
            <motion.div
              className="absolute inset-0"
              animate={{ rotate: 360 }}
              transition={{ duration: 40, repeat: Infinity, ease: 'linear' }}
            >
              {WUXING_ELEMENTS.map((element, i) => {
                const config = WUXING_CONFIG[element]
                const angle = (i * 72 - 90) * (Math.PI / 180)
                const x = 72 + 50 * Math.cos(angle)
                const y = 72 + 50 * Math.sin(angle)
                return (
                  <motion.div
                    key={element}
                    className="absolute w-9 h-9 rounded-full flex items-center justify-center shadow-md ring-2 ring-white/70"
                    style={{
                      left: x - 18,
                      top: y - 18,
                      background: `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})`,
                    }}
                    animate={{ rotate: -360 }}
                    transition={{ duration: 40, repeat: Infinity, ease: 'linear' }}
                  >
                    <span className="text-white text-sm font-semibold" style={{ fontFamily: 'serif' }}>{element}</span>
                  </motion.div>
                )
              })}
            </motion.div>
            {/* 中心徽标 */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-14 h-14 rounded-full bg-white/90 backdrop-blur-sm shadow-lg flex items-center justify-center">
                <span className="text-2xl font-bold bg-gradient-to-br from-[#3DA35D] to-[#4A90C4] bg-clip-text text-transparent" style={{ fontFamily: 'serif' }}>衣</span>
              </div>
            </div>
          </div>
          
          <h2 className="text-3xl font-bold text-[var(--brand-heading)] mb-3" style={{ fontFamily: 'serif' }}>
            我的衣橱
          </h2>
          <p className="text-stone-500 mb-2">登录后开启您的五行穿搭之旅</p>
          <p className="text-sm text-[var(--brand-subtle)]">点击右上角「登录」按钮</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-full relative overflow-visible py-4 md:py-8">
      {/* 顶部艺术化标题区 - 移动端优化 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mb-6 md:mb-8"
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4">
          <div>
            <motion.h1 
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              className="text-2xl md:text-4xl font-bold text-[var(--brand-heading)] tracking-tight"
              style={{ fontFamily: 'serif' }}
            >
              我的衣橱
            </motion.h1>
            <motion.p 
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="text-stone-500 mt-2 flex items-center gap-2 text-sm md:text-base"
            >
              <span className="inline-block w-2 h-2 rounded-full bg-gradient-to-r from-rose-400 to-pink-400" />
              共收藏 <span className="font-medium text-stone-700">{filterStats?.total ?? total}</span> 件衣物
              {hasActiveFilter && filterStats && (
                <span className="text-[var(--brand-subtle)]">· 当前命中 <span className="font-medium text-stone-700">{filterStats.matched}</span> 件</span>
              )}
            </motion.p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <motion.button
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2 }}
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleAddNew}
            className="relative group px-4 md:px-6 py-2.5 md:py-3 rounded-xl md:rounded-2xl bg-gradient-to-r from-stone-800 to-stone-700 text-white font-medium shadow-xl shadow-stone-300/30 overflow-hidden touch-feedback w-full sm:w-auto"
          >
            <span className="relative z-10 flex items-center justify-center gap-2 text-sm md:text-base">
              <svg className="w-4 h-4 md:w-5 md:h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              添加衣物
            </span>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-amber-500 to-orange-500"
              initial={{ x: '100%' }}
              whileHover={{ x: 0 }}
              transition={{ duration: 0.3 }}
            />
          </motion.button>

          <motion.button
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.25 }}
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsBatchModalOpen(true)}
            className="relative group px-4 md:px-6 py-2.5 md:py-3 rounded-xl md:rounded-2xl bg-gradient-to-r from-rose-500 to-pink-500 text-white font-medium shadow-xl shadow-rose-300/30 overflow-hidden touch-feedback w-full sm:w-auto"
          >
            <span className="relative z-10 flex items-center justify-center gap-2 text-sm md:text-base">
              <svg className="w-4 h-4 md:w-5 md:h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0-12l-4 4m4-4l4 4" />
              </svg>
              批量上传
            </span>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-pink-400 to-rose-400"
              initial={{ x: '100%' }}
              whileHover={{ x: 0 }}
              transition={{ duration: 0.3 }}
            />
          </motion.button>
          </div>
        </div>
      </motion.div>

      {/* 五行能量分布图 - 移动端优化 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-6 md:mb-8 p-4 md:p-6 bg-white/70 backdrop-blur-xl rounded-2xl md:rounded-3xl border border-white/50 shadow-xl shadow-stone-200/20"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs md:text-sm font-medium text-stone-500 uppercase tracking-wider">五行能量分布 · 八卦图</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('cabinet')}
              title="柜体抽屉视图"
              aria-label="柜体抽屉视图"
              className={`p-2 rounded-lg transition-all touch-feedback ${viewMode === 'cabinet' ? 'bg-[var(--brand-heading)] text-white shadow-sm' : 'text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] hover:bg-[var(--brand-surface)]'}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5h16v5H4zM4 14h16v5H4zM10 7.5h4M10 16.5h4" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('flow')}
              title="平铺视图"
              aria-label="平铺视图"
              className={`p-2 rounded-lg transition-all touch-feedback ${viewMode === 'flow' ? 'bg-[var(--brand-heading)] text-white shadow-sm' : 'text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] hover:bg-[var(--brand-surface)]'}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('grid')}
              title="网格视图"
              aria-label="网格视图"
              className={`p-2 rounded-lg transition-all touch-feedback ${viewMode === 'grid' ? 'bg-[var(--brand-heading)] text-white shadow-sm' : 'text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] hover:bg-[var(--brand-surface)]'}`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
          </div>
        </div>

        {/* 道家五行八卦图 - 点击节点按五行筛选 */}
        <WuxingBaguaChart
          elementStats={elementStats}
          total={total}
          filterElement={filters.element}
          onFilter={(el) => {
            // 八卦图内部已处理 toggle（激活中再点传 null），这里直接写入状态
            const next = { ...filters, element: el }
            setFilters(next)
            fetchItems(toFetchParams(next))
            refreshStats(next)
          }}
        />

        {/* 图例说明 */}
        <div className="mt-3 flex items-center justify-center gap-4 text-[11px] text-[var(--brand-subtle)]">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-4 h-0 border-t" style={{ borderColor: 'var(--wuxing-wood)', opacity: 0.6 }} />
            外环相生
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-4 h-0 border-t border-dashed" style={{ borderColor: 'var(--brand-subtle)' }} />
            内星相克
          </span>
        </div>
      </motion.div>

      {/* 衣橱智能洞察面板 */}
      {total > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-6 md:mb-8"
        >
          <WardrobeInsights />
        </motion.div>
      )}

      {/* 闲置物品提醒 */}
      {total > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="mb-6 md:mb-8"
        >
          <IdleItemsCard />
        </motion.div>
      )}

      {/* 多维智能筛选栏 */}
      {total > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28 }}
          className="mb-6 md:mb-8 p-3 md:p-4 bg-white/70 backdrop-blur-xl rounded-2xl md:rounded-3xl border border-white/50 shadow-xl shadow-stone-200/20"
        >
          <div className="flex items-center justify-between mb-2 gap-2">
            <h3 className="text-xs md:text-sm font-medium text-stone-500 uppercase tracking-wider">智能筛选 · 多维分类</h3>
            <div className="flex items-center gap-3">
              {filterStats && (
                <span className="text-[11px] text-[var(--brand-subtle)] tabular-nums whitespace-nowrap">
                  命中 <span className="font-semibold text-[var(--brand-heading)]">{filterStats.matched}</span> / {filterStats.total} 件
                </span>
              )}
              {hasActiveFilter && (
                <button
                  onClick={clearFilters}
                  className="text-xs text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] transition-colors touch-feedback whitespace-nowrap"
                >
                  清除筛选
                </button>
              )}
            </div>
          </div>
          <div className="space-y-1.5">
            {FILTER_DIMENSIONS.map((dim) => (
              <div key={dim.key} className="flex items-center gap-2">
                <span className="w-10 shrink-0 text-[11px] text-[var(--brand-subtle)]">{dim.label}</span>
                <div className="flex gap-1.5 overflow-x-auto scrollbar-hide py-0.5">
                  {dim.options.map((opt) => {
                    const active = filters[dim.key] === opt
                    const count = filterStats?.facets?.[dim.key]?.[opt]
                    const elemColor = dim.key === 'element' ? WUXING_THEME[opt]?.color : null
                    return (
                      <button
                        key={opt}
                        onClick={() => updateFilter(dim.key, opt)}
                        className={`flex-shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition-all touch-feedback ${
                          active
                            ? 'text-white shadow-sm font-medium'
                            : count === 0
                              ? 'bg-[var(--brand-bg)]/40 text-[var(--brand-subtle)]/50 hover:bg-[var(--brand-surface)]'
                              : 'bg-[var(--brand-bg)]/60 text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] hover:bg-[var(--brand-surface)]'
                        }`}
                        style={active ? { backgroundColor: elemColor || 'var(--brand-heading)' } : undefined}
                      >
                        {opt}
                        {count != null && (
                          <span className={`text-[10px] tabular-nums ${active ? 'text-white/80' : 'opacity-60'}`}>{count}</span>
                        )}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* 衣物展示区 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        {isLoading && items.length === 0 ? (
          <SkeletonList count={6} showImage={true} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4" />
        ) : items.length === 0 ? (
          wardrobeEmpty ? (
            <EmptyState
              icon="wardrobe"
              title="衣橱空空如也"
              description="开始添加你的第一件衣物，让 AI 为你推荐完美搭配"
              actionLabel="添加衣物"
              onAction={handleAddNew}
            />
          ) : (
            /* 筛选无结果：保持页面结构稳定，内联轻量提示（不整页跳空态） */
            <div className="py-12 md:py-16 rounded-2xl md:rounded-3xl border border-dashed border-stone-300/60 bg-white/40 backdrop-blur-sm text-center">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[var(--brand-bg)] flex items-center justify-center">
                <svg className="w-5 h-5 text-[var(--brand-subtle)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-4.35-4.35M17 10.5a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-[var(--brand-heading)]" style={{ fontFamily: 'serif' }}>无相关物品</p>
              <p className="text-xs text-[var(--brand-subtle)] mt-1.5">试试调整上方筛选条件，或清除筛选查看全部衣物</p>
              <button
                onClick={clearFilters}
                className="mt-4 px-4 py-1.5 rounded-lg text-xs text-white bg-[var(--brand-heading)]/80 hover:bg-[var(--brand-heading)] transition-colors touch-feedback"
              >
                清除筛选
              </button>
            </div>
          )
        ) : viewMode === 'cabinet' ? (
          /* 品类抽屉柜：一柜多格，把手刻品类与实时件数，点一格摊开该品类 */
          <WardrobeCabinet
            items={items}
            filtered={hasActiveFilter}
            categoryAvail={filterStats?.facets?.category}
            onSelect={setZoomItem}
          />
        ) : (
          <div className={viewMode === 'grid' 
            ? "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
            : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
          }>
            <AnimatePresence mode="popLayout">
              {items.map((item, index) => {
                const config = getWuxingConfig(item.primary_element)
                const theme = WUXING_THEME[item.primary_element] || WUXING_THEME['金']

                const ItemCard = (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, y: 20, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ delay: index * 0.03, duration: 0.3 }}
                    onClick={() => setZoomItem(item)}
                    role="button"
                    tabIndex={0}
                    aria-label={`放大查看 ${item.name}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        setZoomItem(item)
                      }
                    }}
                    className={`group relative cursor-pointer overflow-hidden rounded-3xl bg-white shadow-sm hover:shadow-xl transition-all duration-500 ${
                      viewMode === 'flow' ? 'aspect-[4/3]' : 'aspect-[3/4]'
                    }`}
                  >
                    {/* 背景装饰 */}
                    <div 
                      className="absolute inset-0 opacity-30"
                      style={{ background: `linear-gradient(135deg, ${config.gradientFrom}20, ${config.gradientTo}10)` }}
                    />
                    
                    {/* 五行符号背景 */}
                    <div 
                      className="absolute -right-4 -top-4 text-8xl opacity-5 font-serif"
                      style={{ color: config.gradientFrom }}
                    >
                      {theme.symbol}
                    </div>

                    {/* 操作按钮 */}
                    <div className="absolute top-3 right-3 z-20 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-300">
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={(e) => { e.stopPropagation(); setEditItem(item); setIsModalOpen(true) }}
                        className="p-2 rounded-xl bg-white/90 backdrop-blur-md shadow-lg text-stone-500 hover:text-blue-600 hover:bg-blue-50 transition-all"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l2.768 2.768m-2.768-2.768l-5.5 5.5a1 1 0 00-.293.707v2.536a1 1 0 001 1h2.536a1 1 0 00.707-.293l5.5-5.5M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5" />
                        </svg>
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={(e) => { e.stopPropagation(); handleDelete(item.id) }}
                        disabled={deletingId === item.id}
                        className="p-2 rounded-xl bg-white/90 backdrop-blur-md shadow-lg text-stone-500 hover:text-rose-600 hover:bg-rose-50 transition-all"
                      >
                        {deletingId === item.id ? (
                          <motion.svg className="w-4 h-4" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </motion.svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </motion.button>
                    </div>

                    {/* 图片区域 */}
                    <div className={`relative ${viewMode === 'flow' ? 'h-2/3' : 'h-3/4'} overflow-hidden`}>
                      {item.image_url ? (
                        <img
                          src={getImageUrl(item.image_url) || ''}
                          alt={item.name}
                          loading="lazy"
                          className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                        />
                      ) : (
                        <div 
                          className="w-full h-full flex items-center justify-center"
                          style={{ background: `linear-gradient(135deg, ${config.gradientFrom}30, ${config.gradientTo}20)` }}
                        >
                          <motion.span 
                            className="text-7xl font-serif opacity-70"
                            style={{ color: config.gradientFrom }}
                            animate={{ scale: [1, 1.05, 1] }}
                            transition={{ duration: 3, repeat: Infinity }}
                          >
                            {config.element}
                          </motion.span>
                        </div>
                      )}
                      
                      {/* 底部渐变 */}
                      <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-white to-transparent" />

                      {/* 闲置天数徽标（图片右上角；hover 时让位于操作按钮） */}
                      {item.idle_days != null && item.idle_days >= IDLE_BADGE_MIN_DAYS && (
                        <div
                          className={`absolute top-3 right-3 z-10 px-2 py-1 rounded-lg backdrop-blur-md text-[10px] font-medium text-white shadow-sm transition-opacity duration-300 group-hover:opacity-0 ${idleBadgeClass(item.idle_days)}`}
                        >
                          {item.wear_count === 0 ? `未穿 ${item.idle_days} 天` : `已闲置 ${item.idle_days} 天`}
                        </div>
                      )}
                    </div>

                    {/* 信息区域 */}
                    <div className={`absolute bottom-0 left-0 right-0 p-4 ${viewMode === 'flow' ? 'h-1/3' : 'h-1/4'}`}>
                      {/* 五行标签 */}
                      <div className="flex items-center gap-2 mb-2">
                        <span 
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold shadow-sm font-serif"
                          style={{ 
                            background: `linear-gradient(135deg, ${config.gradientFrom}, ${config.gradientTo})`,
                            color: 'white',
                          }}
                        >
                          {config.element}
                        </span>
                        {item.secondary_element && (
                          <span className="text-xs text-[var(--brand-subtle)] bg-stone-100 px-2 py-0.5 rounded-full">
                            +{item.secondary_element}
                          </span>
                        )}
                        {item.category && (
                          <span className="text-xs text-[var(--brand-subtle)]">
                            · {item.category}
                          </span>
                        )}
                      </div>
                      
                      {/* 名称 */}
                      <h3 className="font-medium text-[var(--brand-heading)] truncate" title={item.name}>
                        {item.name}
                      </h3>
                    </div>
                  </motion.div>
                )
                
                // 移动端使用手势删除，桌面端直接显示
                return isMobile ? (
                  <SwipeToDelete
                    key={item.id}
                    onSwipe={async () => handleDelete(item.id)}
                    threshold={80}
                  >
                    {ItemCard}
                  </SwipeToDelete>
                ) : (
                  ItemCard
                )
              })}
            </AnimatePresence>
          </div>
        )}
      </motion.div>

      {/* 添加/编辑弹窗 */}
      <Suspense fallback={null}>
        <AddWardrobeModal
          isOpen={isModalOpen}
          onClose={() => { setIsModalOpen(false); setEditItem(null) }}
          onSuccess={() => { fetchItems(); refreshStats(filters); setIsModalOpen(false); setEditItem(null) }}
          editItem={editItem}
        />
      </Suspense>
      
            {/* 批量上传弹窗 */}
            <Suspense fallback={null}>
              <BatchUploadModal
                isOpen={isBatchModalOpen}
                onClose={() => setIsBatchModalOpen(false)}
                onSuccess={() => { fetchItems(); refreshStats(filters) }}
                isEmptyWardrobe={wardrobeEmpty}
              />
            </Suspense>

      {/* 衣物放大查看层（柜体抽屉与网格卡片共用） */}
      <WardrobeItemViewer
        item={zoomItem}
        onClose={() => setZoomItem(null)}
        onEdit={(it) => {
          setZoomItem(null)
          setEditItem(it)
          setIsModalOpen(true)
        }}
        onDelete={(id) => {
          setZoomItem(null)
          handleDelete(id)
        }}
        deleting={deletingId !== null}
      />

      {/* 删除确认弹窗 */}
      <ConfirmDialog
        isOpen={confirmDeleteId !== null}
        onClose={() => setConfirmDeleteId(null)}
        onConfirm={doDeleteItem}
        title="删除衣物"
        description="确定要删除这件衣物吗？此操作不可撤销。"
        confirmText="删除"
        danger
      />
    </div>
  )
}
