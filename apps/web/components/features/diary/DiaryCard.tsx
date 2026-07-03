'use client'

import { motion } from 'framer-motion'
import type { OutfitDiary } from '@/types'

const MOOD_EMOJI: Record<string, string> = {
  happy: '😊',
  neutral: '😐',
  sad: '😢',
  excited: '🤩',
  calm: '😌',
}

const RATING_STARS = (rating: number) => '★'.repeat(rating) + '☆'.repeat(5 - rating)

interface DiaryCardProps {
  diary: OutfitDiary
  onClick?: () => void
  onDelete?: () => void
}

export function DiaryCard({ diary, onClick, onDelete }: DiaryCardProps) {
  const date = new Date(diary.diary_date)
  const dateStr = `${date.getMonth() + 1}月${date.getDate()}日`
  const emoji = diary.mood ? MOOD_EMOJI[diary.mood] || '😐' : '📝'

  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.01 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className="bg-white rounded-2xl p-4 shadow-sm border border-stone-100 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{emoji}</span>
          <div>
            <p className="text-sm font-medium text-stone-800">{dateStr}</p>
            {diary.occasion && (
              <p className="text-xs text-stone-500">{diary.occasion}</p>
            )}
          </div>
        </div>
        {diary.rating && (
          <span className="text-amber-500 text-sm">{RATING_STARS(diary.rating)}</span>
        )}
        {onDelete && (
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="p-1 rounded text-stone-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            aria-label="删除日记"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </motion.button>
        )}
      </div>

      {/* 关联衣物缩略图 */}
      {diary.items.length > 0 && (
        <div className="flex gap-2 mb-2">
          {diary.items.slice(0, 4).map((item) => (
            <div key={item.id} className="w-12 h-12 rounded-lg bg-stone-100 overflow-hidden flex-shrink-0">
              {item.image_url ? (
                <img src={item.image_url} alt={item.name || ''} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-stone-400">
                  {item.primary_element || '?'}
                </div>
              )}
            </div>
          ))}
          {diary.items.length > 4 && (
            <div className="w-12 h-12 rounded-lg bg-stone-50 flex items-center justify-center text-xs text-stone-500">
              +{diary.items.length - 4}
            </div>
          )}
        </div>
      )}

      {/* AI 点评摘要 */}
      {diary.ai_review?.score && (
        <div className="flex items-center gap-2 text-xs text-stone-500">
          <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 font-medium">
            AI {diary.ai_review.score}分
          </span>
          {diary.ai_review.comment && (
            <span className="truncate">{diary.ai_review.comment}</span>
          )}
        </div>
      )}

      {diary.notes && (
        <p className="text-xs text-stone-500 mt-2 line-clamp-2">{diary.notes}</p>
      )}
    </motion.div>
  )
}
