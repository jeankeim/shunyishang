'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DiaryCard } from '@/components/features/diary/DiaryCard'
import { DiaryCalendar } from '@/components/features/diary/DiaryCalendar'
import { DiaryStatsPanel } from '@/components/features/diary/DiaryStats'
import { DiaryDetail } from '@/components/features/diary/DiaryDetail'
import { DiaryForm } from '@/components/features/diary/DiaryForm'
import { useDiaryStore } from '@/store/diary'
import { ConfirmDialog } from '@/components/ui'

type ViewMode = 'list' | 'calendar' | 'stats'
type DiaryView = 'list' | 'new' | 'detail'

// 统一滑动过渡动画配置
const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 80 : -80,
    opacity: 0,
    scale: 0.98,
  }),
  center: {
    x: 0,
    opacity: 1,
    scale: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -80 : 80,
    opacity: 0,
    scale: 0.98,
  }),
}

const transitionConfig = {
  type: 'spring' as const,
  stiffness: 300,
  damping: 30,
  mass: 0.8,
}

export default function DiaryPage() {
  const {
    diaries, total, page, calendar, calendarYear, calendarMonth, stats,
    currentDiary, isLoading, error,
    fetchDiaries, fetchDiary, fetchCalendar, fetchStats,
    createNewDiary, updateExistingDiary, deleteExistingDiary, triggerReview, clearError,
  } = useDiaryStore()

  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [moodFilter, setMoodFilter] = useState<string>('')

  // 内嵌视图状态：list / new / detail / edit
  const [diaryView, setDiaryView] = useState<DiaryView>('list')
  const [selectedDiaryId, setSelectedDiaryId] = useState<number | null>(null)
    const [slideDirection, setSlideDirection] = useState(1)
  const [initialDate, setInitialDate] = useState<string | undefined>(undefined)
  const [editInitialData, setEditInitialData] = useState<{
    diary_date: string
    mood?: string
    occasion?: string
    notes?: string
    rating?: number
    image_urls?: string[]
  } | undefined>(undefined)

  // 删除确认
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  // 清理错误
  useEffect(() => {
    return () => clearError()
  }, [clearError])

  // 数据获取
  useEffect(() => {
    if (diaryView === 'list') {
      fetchDiaries({ mood: moodFilter || undefined })
    }
  }, [diaryView, moodFilter, fetchDiaries])

  useEffect(() => {
    if (viewMode === 'calendar') {
      fetchCalendar(calendarYear, calendarMonth)
    } else if (viewMode === 'stats') {
      fetchStats()
    }
  }, [viewMode, calendarYear, calendarMonth, fetchCalendar, fetchStats])

  // === 导航操作 ===
  const navigateTo = useCallback((view: DiaryView, direction: number, diaryId?: number, date?: string) => {
    setSlideDirection(direction)
    setDiaryView(view)
    if (diaryId !== undefined) setSelectedDiaryId(diaryId)
    if (date !== undefined) setInitialDate(date)
  }, [])

  const goToList = useCallback(() => {
    setSlideDirection(-1)
    setDiaryView('list')
    setEditInitialData(undefined)
  }, [])
  const goToNew = useCallback((date?: string) => {
    setSlideDirection(1)
    setEditInitialData(undefined)
    setInitialDate(date)
    setDiaryView('new')
  }, [])
  const goToDetail = useCallback((id: number) => navigateTo('detail', 1, id), [navigateTo])

  // 进入详情时加载数据
  useEffect(() => {
    if (diaryView === 'detail' && selectedDiaryId) {
      fetchDiary(selectedDiaryId)
    }
  }, [diaryView, selectedDiaryId, fetchDiary])

  // === 业务操作 ===
  const handleCreateDiary = async (data: {
    diary_date: string
    mood?: string
    occasion?: string
    notes?: string
    rating?: number
    image_urls?: string[]
    trigger_ai_review?: boolean
  }) => {
    const diary = await createNewDiary({
      diary_date: data.diary_date,
      mood: data.mood,
      occasion: data.occasion,
      notes: data.notes,
      rating: data.rating,
      image_urls: data.image_urls,
      trigger_ai_review: data.trigger_ai_review,
    })
    // 创建成功后直接跳到详情
    setSlideDirection(1)
    setSelectedDiaryId(diary.id)
    setDiaryView('detail')
    fetchDiary(diary.id)
  }

    const handleUpdateDiary = async (data: {
    diary_date: string
    mood?: string
    occasion?: string
    notes?: string
    rating?: number
    image_urls?: string[]
  }) => {
    if (!selectedDiaryId) return
    await updateExistingDiary(selectedDiaryId, {
      mood: data.mood,
      occasion: data.occasion,
      notes: data.notes,
      rating: data.rating,
      image_urls: data.image_urls,
    })
    fetchDiary(selectedDiaryId)
  }

  const handleDeleteDiary = async (id: number) => {
    setConfirmDeleteId(id)
  }

  const doDeleteDiary = async () => {
    if (!confirmDeleteId) return
    await deleteExistingDiary(confirmDeleteId)
    setConfirmDeleteId(null)
    goToList()
  }

  const handleCalendarPrev = () => {
    const m = calendarMonth === 1 ? 12 : calendarMonth - 1
    const y = calendarMonth === 1 ? calendarYear - 1 : calendarYear
    fetchCalendar(y, m)
  }

  const handleCalendarNext = () => {
    const m = calendarMonth === 12 ? 1 : calendarMonth + 1
    const y = calendarMonth === 12 ? calendarYear + 1 : calendarYear
    fetchCalendar(y, m)
  }

  const loadMore = () => {
    fetchDiaries({ page: page + 1, mood: moodFilter || undefined })
  }

  // === 子视图配置 ===
  const tabs: { id: ViewMode; label: string; emoji: string }[] = [
    { id: 'list', label: '列表', emoji: '📋' },
    { id: 'calendar', label: '日历', emoji: '📅' },
    { id: 'stats', label: '统计', emoji: '📊' },
  ]

  const moods = [
    { value: '', label: '全部' },
    { value: 'happy', label: '😊开心' },
    { value: 'excited', label: '🤩兴奋' },
    { value: 'calm', label: '😌平静' },
    { value: 'neutral', label: '😐一般' },
    { value: 'sad', label: '😢低落' },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* 导航面包屑 — 统一的路径感知 */}
      <div className="flex items-center gap-1.5 text-sm min-h-[28px]">
        <button
          onClick={goToList}
          className={`flex items-center gap-1 transition-colors ${
            diaryView === 'list' ? 'text-stone-800 font-semibold' : 'text-stone-400 hover:text-stone-600'
          }`}
        >
          <span className="text-base">📓</span>
          穿搭日记
        </button>
        {diaryView !== 'list' && (
          <>
            <span className="text-stone-300">/</span>
            <span className="text-stone-600 font-medium">
              {diaryView === 'new'
                ? (editInitialData ? '编辑日记' : '新建日记')
                : '日记详情'}
            </span>
          </>
        )}
      </div>

      {/* 视图容器 — 带过渡动画 */}
      <div className="relative overflow-hidden">
        <AnimatePresence mode="wait" custom={slideDirection}>
          {/* ===== 列表视图 ===== */}
          {diaryView === 'list' && (
            <motion.div
              key="diary-list"
              custom={slideDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={transitionConfig}
              className="space-y-4"
            >
              {/* 页面标题 + 新建按钮 */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-stone-500 mt-0.5">记录每日穿搭，AI 智能点评</p>
                </div>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => goToNew()}
                  className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm hover:shadow-md transition-shadow flex items-center gap-1.5"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                  </svg>
                  新日记
                </motion.button>
              </div>

              {/* 视图切换 Tab */}
              <div className="flex items-center gap-2">
                {tabs.map((tab) => (
                  <motion.button
                    key={tab.id}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setViewMode(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                      viewMode === tab.id
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-white text-stone-600 border border-stone-200 hover:bg-stone-50'
                    }`}
                  >
                    <span>{tab.emoji}</span>
                    <span>{tab.label}</span>
                  </motion.button>
                ))}
              </div>

              {/* 列表内容区 */}
              <AnimatePresence mode="wait">
                {viewMode === 'list' && (
                  <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                    {/* 心情筛选 */}
                    <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
                      {moods.map((m) => (
                        <button
                          key={m.value}
                          onClick={() => setMoodFilter(m.value)}
                          className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                            moodFilter === m.value
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-white text-stone-500 border border-stone-200 hover:bg-stone-50'
                          }`}
                        >
                          {m.label}
                        </button>
                      ))}
                    </div>

                    {isLoading && diaries.length === 0 ? (
                      <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-2 border-emerald-500 border-t-transparent mx-auto" />
                        <p className="text-sm text-stone-400 mt-3">加载中...</p>
                      </div>
                    ) : diaries.length === 0 ? (
                      <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
                        <p className="text-3xl mb-2">📝</p>
                        <p className="text-sm text-stone-500">还没有穿搭日记</p>
                        <motion.button
                          whileTap={{ scale: 0.95 }}
                          onClick={() => goToNew()}
                          className="mt-3 px-5 py-2 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm"
                        >
                          创建第一篇日记
                        </motion.button>
                      </div>
                    ) : (
                      <>
                        {diaries.map((diary, index) => (
                          <motion.div
                            key={diary.id}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.04, duration: 0.25 }}
                          >
                            <DiaryCard
                              diary={diary}
                              onClick={() => goToDetail(diary.id)}
                              onDelete={() => handleDeleteDiary(diary.id)}
                            />
                          </motion.div>
                        ))}
                        {diaries.length < total && (
                          <motion.button
                            whileTap={{ scale: 0.98 }}
                            onClick={loadMore}
                            className="w-full py-3 rounded-xl border border-stone-200 text-sm text-stone-600 font-medium hover:bg-stone-50 transition-colors"
                          >
                            加载更多 ({total - diaries.length} 条)
                          </motion.button>
                        )}
                      </>
                    )}
                  </motion.div>
                )}

                {viewMode === 'calendar' && (
                  <motion.div key="calendar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <DiaryCalendar
                      year={calendarYear}
                      month={calendarMonth}
                      entries={calendar}
                      onPrevMonth={handleCalendarPrev}
                      onNextMonth={handleCalendarNext}
                      onDateClick={(date) => goToNew(date)}
                    />
                  </motion.div>
                )}

                {viewMode === 'stats' && (
                  <motion.div key="stats" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    <DiaryStatsPanel stats={stats} />
                  </motion.div>
                )}
              </AnimatePresence>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
                  {error}
                </div>
              )}
            </motion.div>
          )}

          {/* ===== 新建/编辑日记视图 ===== */}
          {diaryView === 'new' && (
            <motion.div
              key="diary-new"
              custom={slideDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={transitionConfig}
              className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100"
            >
              <div className="flex items-center gap-3 mb-5">
                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => {
                    // 如果是从详情编辑，先返回列表
                    if (editInitialData && selectedDiaryId) {
                      setEditInitialData(undefined)
                      setSlideDirection(-1)
                      setDiaryView('detail')
                    } else {
                      goToList()
                    }
                  }}
                  className="p-2 rounded-lg hover:bg-stone-100 text-stone-500 transition-colors"
                  aria-label="返回"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </motion.button>
                <div>
                  <h2 className="text-lg font-bold text-stone-800">
                    {editInitialData ? '编辑日记' : '新建日记'}
                  </h2>
                  <p className="text-xs text-stone-500">
                    {editInitialData ? '修改穿搭记录' : '记录今日穿搭与心情'}
                  </p>
                </div>
              </div>

              <DiaryForm
                isEdit={!!editInitialData}
                initialData={editInitialData || (initialDate ? { diary_date: initialDate } : undefined)}
                onSubmit={async (data) => {
                  if (editInitialData && selectedDiaryId) {
                    // 编辑模式：更新已有日记
                                        await updateExistingDiary(selectedDiaryId, {
                      mood: data.mood,
                      occasion: data.occasion,
                      notes: data.notes,
                      rating: data.rating,
                      image_urls: data.image_urls,
                    })
                    setEditInitialData(undefined)
                    setSlideDirection(-1)
                    fetchDiary(selectedDiaryId)
                    setDiaryView('detail')
                  } else {
                    // 新建模式
                    await handleCreateDiary(data)
                  }
                }}
                onCancel={() => {
                  if (editInitialData && selectedDiaryId) {
                    setEditInitialData(undefined)
                    setSlideDirection(-1)
                    setDiaryView('detail')
                  } else {
                    goToList()
                  }
                }}
              />

              {error && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
                  {error}
                </div>
              )}
            </motion.div>
          )}

          {/* ===== 日记详情视图 ===== */}
          {diaryView === 'detail' && (
            <motion.div
              key="diary-detail"
              custom={slideDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={transitionConfig}
            >
              {isLoading && !currentDiary ? (
                <div className="flex items-center justify-center py-24">
                  <div className="animate-spin rounded-full h-10 w-10 border-2 border-emerald-500 border-t-transparent" />
                </div>
              ) : !currentDiary ? (
                <div className="text-center py-24">
                  <p className="text-3xl mb-2">🔍</p>
                  <p className="text-sm text-stone-500">未找到该日记</p>
                  <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={goToList}
                    className="mt-4 px-4 py-2 rounded-xl bg-emerald-50 text-emerald-700 text-sm font-medium"
                  >
                    返回日记列表
                  </motion.button>
                </div>
              ) : (
                <DiaryDetail
                  diary={currentDiary}
                  onBack={goToList}
                  onDelete={() => selectedDiaryId && handleDeleteDiary(selectedDiaryId)}
                  onTriggerReview={() => selectedDiaryId && triggerReview(selectedDiaryId)}
                  onEdit={() => {
                    // 编辑模式：用当前日记数据填充表单
                    if (currentDiary) {
                      setSlideDirection(1)
                                            setEditInitialData({
                        diary_date: currentDiary.diary_date,
                        mood: currentDiary.mood || undefined,
                        occasion: currentDiary.occasion || undefined,
                        notes: currentDiary.notes || undefined,
                        rating: currentDiary.rating || undefined,
                        image_urls: currentDiary.image_urls,
                      })
                      setDiaryView('new')
                    }
                  }}
                />
              )}

              {error && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-600">
                  {error}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* 删除确认弹窗 */}
        <ConfirmDialog
          isOpen={confirmDeleteId !== null}
          onClose={() => setConfirmDeleteId(null)}
          onConfirm={doDeleteDiary}
          title="删除日记"
          description="确认删除该日记？此操作不可撤销。"
          confirmText="删除"
          danger
        />
      </div>
    </div>
  )
}
