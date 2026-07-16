'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { quickCheckIn } from '@/lib/api'
import { useUserStore } from '@/store/user'

// 心情选项
const MOODS = [
  { value: 'happy', emoji: '😊', label: '开心' },
  { value: 'excited', emoji: '🤩', label: '兴奋' },
  { value: 'calm', emoji: '😌', label: '平静' },
  { value: 'neutral', emoji: '😐', label: '一般' },
  { value: 'sad', emoji: '😢', label: '低落' },
]

// 五行颜色映射
const ELEMENT_COLORS: Record<string, string> = {
  '金': '#9E9E9E', '木': '#4CAF50', '水': '#2196F3',
  '火': '#FF6B6B', '土': '#D4A574',
}

interface QuickCheckInProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (diaryId: number) => void
  weatherInfo?: any
}

export function QuickCheckIn({ isOpen, onClose, onSuccess, weatherInfo }: QuickCheckInProps) {
  const { isAuthenticated } = useUserStore()
  const [description, setDescription] = useState('')
  const [mood, setMood] = useState('neutral')
  const [submitting, setSubmitting] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [aiTags, setAiTags] = useState<Record<string, string> | null>(null)
  const [result, setResult] = useState<{ diaryId: number; created: boolean } | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!isAuthenticated || !isOpen) return null

  async function handleSubmit() {
    if (!description.trim()) {
      setError('请描述今天的穿搭')
      return
    }
    setError(null)
    setAnalyzing(true)
    setSubmitting(true)

    try {
      const res = await quickCheckIn({
        description: description.trim(),
        mood,
        weather_snapshot: weatherInfo || undefined,
      })

      setAiTags(res.ai_tags || null)
      setResult({ diaryId: res.diary_id, created: res.created })

      if (res.created) {
        onSuccess?.(res.diary_id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '打卡失败')
    } finally {
      setAnalyzing(false)
      setSubmitting(false)
    }
  }

  function handleClose() {
    setDescription('')
    setMood('neutral')
    setAiTags(null)
    setResult(null)
    setError(null)
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
          onClick={handleClose}
        >
          {/* 背景遮罩 */}
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />

          {/* 弹窗内容 */}
          <motion.div
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-md bg-white rounded-t-3xl sm:rounded-3xl shadow-xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 顶部把手（移动端） */}
            <div className="flex justify-center pt-3 sm:hidden">
              <div className="w-10 h-1 rounded-full bg-stone-300" />
            </div>

            <div className="p-5">
              {/* 标题 */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-stone-800">今日穿搭打卡</h3>
                  <p className="text-xs text-stone-500 mt-0.5">30秒记录今天的穿搭</p>
                </div>
                <button
                  onClick={handleClose}
                  className="p-2 rounded-xl hover:bg-stone-100 text-stone-400 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* 成功状态 */}
              {result ? (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="text-center py-6"
                >
                  <div className="text-5xl mb-3">{result.created ? '✅' : '📝'}</div>
                  <h4 className="text-lg font-semibold text-stone-800 mb-1">
                    {result.created ? '打卡成功！' : '今日已打卡'}
                  </h4>
                  <p className="text-sm text-stone-500 mb-4">
                    {result.created ? '已记录今日穿搭日记' : '今天已经打过卡啦'}
                  </p>

                  {/* AI 识别结果 */}
                  {aiTags && Object.keys(aiTags).length > 0 && (
                    <div className="bg-stone-50 rounded-xl p-3 mb-4 text-left">
                      <p className="text-xs font-medium text-stone-600 mb-2">AI 识别结果</p>
                      <div className="flex flex-wrap gap-2">
                        {aiTags.color && (
                          <span className="text-xs px-2 py-1 bg-white rounded-lg border border-stone-200">
                            🎨 {aiTags.color}
                          </span>
                        )}
                        {aiTags.primary_element && (
                          <span
                            className="text-xs px-2 py-1 rounded-lg text-white"
                            style={{ backgroundColor: ELEMENT_COLORS[aiTags.primary_element] || '#999' }}
                          >
                            ☯ {aiTags.primary_element}
                          </span>
                        )}
                        {aiTags.material && (
                          <span className="text-xs px-2 py-1 bg-white rounded-lg border border-stone-200">
                            🧵 {aiTags.material}
                          </span>
                        )}
                        {aiTags.style && (
                          <span className="text-xs px-2 py-1 bg-white rounded-lg border border-stone-200">
                            👔 {aiTags.style}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={handleClose}
                      className="flex-1 py-2.5 rounded-xl border border-stone-200 text-sm text-stone-600 font-medium hover:bg-stone-50 transition-colors"
                    >
                      关闭
                    </button>
                    <button
                      onClick={() => {
                        handleClose()
                        window.location.hash = '#diary'
                      }}
                      className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-medium shadow-sm"
                    >
                      查看日记
                    </button>
                  </div>
                </motion.div>
              ) : (
                <>
                  {/* 穿搭描述输入 */}
                  <div className="mb-4">
                    <label className="text-sm font-medium text-stone-700 mb-1.5 block">
                      今天穿了什么？
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="例如：白色T恤 + 牛仔裤 + 帆布鞋"
                      className="w-full h-20 px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-sm text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 resize-none transition-all"
                      maxLength={200}
                    />
                    <div className="text-right text-[10px] text-[var(--brand-subtle)] mt-0.5">
                      {description.length}/200
                    </div>
                  </div>

                  {/* 心情选择 */}
                  <div className="mb-4">
                    <label className="text-sm font-medium text-stone-700 mb-1.5 block">
                      今天心情
                    </label>
                    <div className="flex gap-2">
                      {MOODS.map(m => (
                        <button
                          key={m.value}
                          onClick={() => setMood(m.value)}
                          className={`flex-1 py-2 rounded-xl text-center transition-all ${
                            mood === m.value
                              ? 'bg-emerald-50 border-2 border-emerald-400 shadow-sm'
                              : 'bg-stone-50 border-2 border-transparent hover:bg-stone-100'
                          }`}
                        >
                          <span className="text-lg block">{m.emoji}</span>
                          <span className="text-[10px] text-stone-600">{m.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* 错误提示 */}
                  {error && (
                    <div className="mb-3 bg-red-50 border border-red-200 rounded-xl p-2.5 text-xs text-red-600">
                      {error}
                    </div>
                  )}

                  {/* AI 分析中 */}
                  {analyzing && (
                    <div className="mb-3 bg-blue-50 border border-blue-200 rounded-xl p-3 flex items-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent" />
                      <span className="text-xs text-blue-600">AI 正在分析穿搭...</span>
                    </div>
                  )}

                  {/* 提交按钮 */}
                  <button
                    onClick={handleSubmit}
                    disabled={submitting || !description.trim()}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white font-medium text-sm shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-md transition-all active:scale-[0.98]"
                  >
                    {submitting ? '打卡中...' : '完成打卡 ✨'}
                  </button>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
