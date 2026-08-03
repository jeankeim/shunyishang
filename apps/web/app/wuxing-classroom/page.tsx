'use client'

import { useEffect, useState, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { getWuxingTip, getAllWuxingTips } from '@/lib/api'
import type { WuxingTip } from '@/lib/api'

// ============================================================
// 配置常量
// ============================================================

// 内容类型 Tab
const TYPE_TABS = [
  { id: '', label: '全部', emoji: '📚' },
  { id: 'wuxing', label: '五行穿搭', emoji: '👗' },
  { id: 'zhouyi', label: '周易文化', emoji: '☯️' },
]

// 五行元素
const ELEMENTS = [
  { id: '', label: '全部', emoji: '📚', color: 'from-stone-400 to-stone-500' },
  { id: '木', label: '木', emoji: '🌿', color: 'from-emerald-400 to-green-500' },
  { id: '火', label: '火', emoji: '🔥', color: 'from-red-400 to-orange-500' },
  { id: '土', label: '土', emoji: '🌍', color: 'from-amber-400 to-yellow-500' },
  { id: '金', label: '金', emoji: '✨', color: 'from-yellow-300 to-amber-400' },
  { id: '水', label: '水', emoji: '💧', color: 'from-blue-400 to-cyan-500' },
]

// 难度级别
const DIFFICULTY_TABS = [
  { id: '', label: '全部难度', emoji: '📖' },
  { id: '入门', label: '入门', emoji: '🌱', color: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
  { id: '进阶', label: '进阶', emoji: '🌿', color: 'bg-blue-50 text-blue-600 border-blue-200' },
  { id: '精通', label: '精通', emoji: '🏔️', color: 'bg-purple-50 text-purple-600 border-purple-200' },
]

// 分类标签颜色
const CATEGORY_COLORS: Record<string, string> = {
  '颜色搭配': 'bg-rose-50 text-rose-600 border-rose-200',
  '材质推荐': 'bg-amber-50 text-amber-600 border-amber-200',
  '适合场景': 'bg-emerald-50 text-emerald-600 border-emerald-200',
  '忌讳搭配': 'bg-red-50 text-red-500 border-red-200',
  '历史趣闻': 'bg-purple-50 text-purple-600 border-purple-200',
  '周易基础': 'bg-indigo-50 text-indigo-600 border-indigo-200',
  '五行生克': 'bg-orange-50 text-orange-600 border-orange-200',
  '节气穿搭': 'bg-teal-50 text-teal-600 border-teal-200',
  '八字命理': 'bg-cyan-50 text-cyan-600 border-cyan-200',
  '文化参考': 'bg-stone-50 text-stone-500 border-stone-200',
}

// 五行生克关系
const WUXING_RELATIONS = [
  { from: '木', to: '火', relation: '生', desc: '木生火，绿色系搭配红色系增运' },
  { from: '火', to: '土', relation: '生', desc: '火生土，红色系搭配黄色系增运' },
  { from: '土', to: '金', relation: '生', desc: '土生金，黄色系搭配白色系增运' },
  { from: '金', to: '水', relation: '生', desc: '金生水，白色系搭配黑色系增运' },
  { from: '水', to: '木', relation: '生', desc: '水生木，黑色系搭配绿色系增运' },
  { from: '木', to: '土', relation: '克', desc: '木克土，绿色系避免过多黄色系' },
  { from: '土', to: '水', relation: '克', desc: '土克水，黄色系避免过多黑色系' },
  { from: '水', to: '火', relation: '克', desc: '水克火，黑色系避免过多红色系' },
  { from: '火', to: '金', relation: '克', desc: '火克金，红色系避免过多白色系' },
  { from: '金', to: '木', relation: '克', desc: '金克木，白色系避免过多绿色系' },
]

// 元素 emoji 映射
const ELEMENT_EMOJI: Record<string, string> = {
  '木': '🌿', '火': '🔥', '土': '🌍', '金': '✨', '水': '💧', '通用': '📖',
}

// ============================================================
// 页面组件
// ============================================================

export default function WuxingClassroomPage() {
  const { isAuthenticated } = useUserStore()

  // 状态
  const [tips, setTips] = useState<WuxingTip[]>([])
  const [loading, setLoading] = useState(false)
  const [activeContentType, setActiveContentType] = useState('')
  const [activeElement, setActiveElement] = useState('')
  const [activeDifficulty, setActiveDifficulty] = useState('')
  const [todayTip, setTodayTip] = useState<WuxingTip | null>(null)
  const [showRelations, setShowRelations] = useState(false)
  const [dailyLoading, setDailyLoading] = useState(false)

  // ========== 每日一学 ==========
  const fetchDailyTip = useCallback(async (contentType?: string, difficulty?: string) => {
    setDailyLoading(true)
    try {
      const data = await getWuxingTip({
        content_type: contentType || undefined,
        difficulty: difficulty || undefined,
      })
      if (data) setTodayTip(data)
    } catch {
      // ignore
    } finally {
      setDailyLoading(false)
    }
  }, [])

  // ========== 加载百科列表 ==========
  const fetchTips = useCallback(async (
    element?: string,
    contentType?: string,
    difficulty?: string,
  ) => {
    setLoading(true)
    try {
      const data = await getAllWuxingTips({
        element: element || undefined,
        content_type: contentType || undefined,
        difficulty: difficulty || undefined,
      })
      setTips(data || [])
    } catch (e) {
      console.error('获取百科失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  // 初次加载
  useEffect(() => {
    if (isAuthenticated) {
      fetchDailyTip()
      fetchTips()
    }
  }, [isAuthenticated, fetchDailyTip, fetchTips])

  // ========== 筛选切换 ==========
  const handleContentTypeChange = (ct: string) => {
    setActiveContentType(ct)
    fetchTips(activeElement || undefined, ct || undefined, activeDifficulty || undefined)
  }

  const handleElementChange = (el: string) => {
    setActiveElement(el)
    fetchTips(el || undefined, activeContentType || undefined, activeDifficulty || undefined)
  }

  const handleDifficultyChange = (diff: string) => {
    setActiveDifficulty(diff)
    fetchTips(activeElement || undefined, activeContentType || undefined, diff || undefined)
  }

  const handleDailyRefresh = () => {
    fetchDailyTip(activeContentType || undefined, activeDifficulty || undefined)
  }

  // ========== 按分类分组 ==========
  const groupedTips = useMemo(() => {
    const groups: Record<string, WuxingTip[]> = {}
    tips.forEach(tip => {
      const cat = tip.category || '其他'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(tip)
    })
    return groups
  }, [tips])

  // ========== 未登录 ==========
  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <p className="text-5xl mb-4">📖</p>
        <h2 className="text-lg font-semibold text-stone-800 mb-2">五行穿搭小课堂</h2>
        <p className="text-sm text-stone-500">登录后可学习五行与周易穿搭知识</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto pb-8">
      {/* 标题 */}
      <div className="mb-5">
        <h1 className="text-xl font-bold text-stone-800">五行穿搭小课堂</h1>
        <p className="text-xs text-stone-500 mt-1">了解五行周易，掌握穿搭智慧</p>
      </div>

      {/* ========== 每日一学卡片 ========== */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 rounded-2xl p-5 border border-amber-200/60 shadow-sm mb-6"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">📖</span>
            <span className="text-sm font-semibold text-amber-700">每日一学</span>
            {todayTip && (
              <>
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-600">
                  {todayTip.content_type === 'zhouyi' ? '周易' : '五行'}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${
                  todayTip.difficulty === '入门' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' :
                  todayTip.difficulty === '进阶' ? 'bg-blue-50 text-blue-600 border-blue-200' :
                  'bg-purple-50 text-purple-600 border-purple-200'
                }`}>
                  {todayTip.difficulty}
                </span>
              </>
            )}
          </div>
          <button
            onClick={handleDailyRefresh}
            disabled={dailyLoading}
            className="text-xs px-3 py-1 rounded-full bg-white/70 text-amber-600 border border-amber-200 hover:bg-amber-50 transition-colors disabled:opacity-50"
          >
            {dailyLoading ? '刷新中...' : '🔄 换一条'}
          </button>
        </div>

        {todayTip ? (
          <>
            <h3 className="text-base font-bold text-stone-800 mb-2">{todayTip.title}</h3>
            <p className="text-sm text-stone-600 leading-relaxed">{todayTip.content}</p>
            <div className="flex flex-wrap items-center gap-2 mt-3">
              {todayTip.tags.length > 0 && todayTip.tags.map((tag, i) => (
                <span key={i} className="px-2 py-0.5 bg-white/70 text-stone-500 rounded-full text-xs border border-stone-200/60">
                  #{tag}
                </span>
              ))}
              {todayTip.source && (
                <span className="ml-auto text-xs text-stone-400 italic">
                  来源：{todayTip.source}
                </span>
              )}
            </div>
          </>
        ) : dailyLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-amber-500 border-t-transparent" />
          </div>
        ) : (
          <p className="text-sm text-stone-500">暂无推荐内容</p>
        )}
      </motion.div>

      {/* ========== 筛选栏 - 内容类型 ========== */}
      <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
        {TYPE_TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => handleContentTypeChange(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
              activeContentType === tab.id
                ? 'bg-gradient-to-r from-indigo-400 to-purple-500 text-white shadow-sm'
                : 'bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-100'
            }`}
          >
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        ))}
        <button
          onClick={() => setShowRelations(!showRelations)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
            showRelations
              ? 'bg-gradient-to-r from-purple-400 to-indigo-500 text-white shadow-sm'
              : 'bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-100'
          }`}
        >
          <span>🔄</span>
          <span>生克关系</span>
        </button>
      </div>

      {/* ========== 筛选栏 - 五行元素 ========== */}
      <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
        {ELEMENTS.map(el => (
          <button
            key={el.id}
            onClick={() => handleElementChange(el.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
              activeElement === el.id
                ? `bg-gradient-to-r ${el.color} text-white shadow-sm`
                : 'bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-100'
            }`}
          >
            <span>{el.emoji}</span>
            <span>{el.label}</span>
          </button>
        ))}
      </div>

      {/* ========== 筛选栏 - 难度级别 ========== */}
      <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
        {DIFFICULTY_TABS.map(diff => (
          <button
            key={diff.id}
            onClick={() => handleDifficultyChange(diff.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
              activeDifficulty === diff.id
                ? diff.color + ' shadow-sm'
                : 'bg-stone-50 text-stone-500 border border-stone-200 hover:bg-stone-100'
            }`}
          >
            <span>{diff.emoji}</span>
            <span>{diff.label}</span>
          </button>
        ))}
      </div>

      {/* ========== 五行生克关系图 ========== */}
      <AnimatePresence>
        {showRelations && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-5 bg-white rounded-xl border border-stone-200/60 p-4 overflow-hidden"
          >
            <h3 className="text-sm font-semibold text-stone-700 mb-3">五行生克关系</h3>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {WUXING_RELATIONS.map((rel, i) => (
                <div
                  key={i}
                  className={`p-2 rounded-lg text-center text-xs ${
                    rel.relation === '生'
                      ? 'bg-emerald-50 border border-emerald-200/60'
                      : 'bg-red-50 border border-red-200/60'
                  }`}
                >
                  <span className="font-bold text-stone-700">{rel.from}→{rel.to}</span>
                  <span className={`ml-1 font-semibold ${rel.relation === '生' ? 'text-emerald-600' : 'text-red-500'}`}>
                    {rel.relation === '生' ? '相生' : '相克'}
                  </span>
                  <p className="text-stone-500 mt-0.5 leading-tight">{rel.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ========== 百科列表 ========== */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-emerald-500 border-t-transparent" />
        </div>
      ) : tips.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-4xl mb-3">📚</p>
          <p className="text-sm text-stone-500">暂无相关百科内容</p>
          <p className="text-xs text-stone-400 mt-1">试试切换筛选条件</p>
        </div>
      ) : (
        <div className="space-y-5">
          {Object.entries(groupedTips).map(([category, categoryTips]) => (
            <motion.div
              key={category}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${CATEGORY_COLORS[category] || 'bg-stone-50 text-stone-500 border-stone-200'}`}>
                  {category}
                </span>
                <span className="text-xs text-stone-400">{categoryTips.length} 条</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {categoryTips.map((tip, idx) => (
                  <TipCard key={tip.id} tip={tip} index={idx} />
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* ========== 底部免责声明 ========== */}
      <div className="mt-8 pt-4 border-t border-stone-200/60">
        <p className="text-xs text-stone-400 text-center leading-relaxed">
          文化参考 · 仅供娱乐 | 内容来源：《周易》《黄帝内经》《尚书》《渊海子平》《三命通会》等传统典籍
        </p>
      </div>
    </div>
  )
}

// ============================================================
// 百科卡片组件
// ============================================================

function TipCard({ tip, index }: { tip: WuxingTip; index: number }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.2) }}
      className="bg-white rounded-xl border border-stone-200/60 p-4 hover:shadow-sm transition-shadow"
    >
      {/* 头部：标题 + 元素 */}
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-semibold text-stone-700 flex-1 pr-2">{tip.title}</h4>
        <span className="text-lg flex-shrink-0">{ELEMENT_EMOJI[tip.element] || '📖'}</span>
      </div>

      {/* 难度 + 类型标签 */}
      <div className="flex items-center gap-1.5 mb-2">
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
          tip.difficulty === '入门' ? 'bg-emerald-50 text-emerald-600' :
          tip.difficulty === '进阶' ? 'bg-blue-50 text-blue-600' :
          'bg-purple-50 text-purple-600'
        }`}>
          {tip.difficulty}
        </span>
        {tip.content_type === 'zhouyi' && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-500">周易</span>
        )}
      </div>

      {/* 内容 */}
      <p className={`text-xs text-stone-500 leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>
        {tip.content}
      </p>
      {tip.content.length > 120 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-amber-500 hover:text-amber-600 mt-1"
        >
          {expanded ? '收起' : '展开全文'}
        </button>
      )}

      {/* 标签 + 来源 */}
      <div className="flex flex-wrap items-center gap-1 mt-2">
        {tip.tags.slice(0, 3).map((tag, i) => (
          <span key={i} className="px-1.5 py-0.5 bg-stone-50 text-stone-400 rounded-full text-[10px]">
            #{tag}
          </span>
        ))}
        {tip.source && (
          <span className="ml-auto text-[10px] text-stone-400 italic truncate max-w-[120px]">
            {tip.source}
          </span>
        )}
      </div>
    </motion.div>
  )
}