'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Share2, CheckCircle } from 'lucide-react'
import { ConfirmDialog } from '@/components/ui'
import type { OutfitDiary } from '@/types'
import { getPostByDiary, deletePostByDiary, createCommunityPost } from '@/lib/api'

const MOOD_EMOJI: Record<string, string> = {
  happy: '😊', neutral: '😐', sad: '😢', excited: '🤩', calm: '😌',
}

const MOOD_TAG: Record<string, string> = {
  happy: '开心', neutral: '平静', sad: '低落', excited: '兴奋', calm: '平和',
}

interface DiaryDetailProps {
  diary: OutfitDiary
  onEdit?: () => void
  onDelete?: () => void
  onTriggerReview?: () => void
  onBack?: () => void
}

// 广场功能临时关闭（个人备案合规改造），恢复时改为 true
const COMMUNITY_ENABLED = false

export function DiaryDetail({ diary, onEdit, onDelete, onTriggerReview, onBack }: DiaryDetailProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)
  const [publishedPost, setPublishedPost] = useState<any>(null)
  const [publishing, setPublishing] = useState(false)
  const [showPublishConfirm, setShowPublishConfirm] = useState(false)
  const [showUnpublishConfirm, setShowUnpublishConfirm] = useState(false)
  const date = new Date(diary.diary_date)
  const dateStr = `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
  const emoji = diary.mood ? MOOD_EMOJI[diary.mood] || '📝' : '📝'

    // 检查日记是否已发布到广场（广场关闭期间跳过）
  useEffect(() => {
    if (!COMMUNITY_ENABLED) return
    getPostByDiary(diary.id)
      .then(setPublishedPost)
      .catch(() => setPublishedPost(null))
  }, [diary.id])

  const handlePublish = async () => {
    setPublishing(true)
    try {
      // 构建帖子内容
      const contentParts = [`${dateStr} 的穿搭记录`]
      if (diary.mood) contentParts.push(`心情：${MOOD_TAG[diary.mood] || diary.mood}`)
      if (diary.notes) contentParts.push(diary.notes)
      if (diary.occasion) contentParts.push(`场合：${diary.occasion}`)
      const content = contentParts.join('\n\n')

      const tags = []
      if (diary.mood) tags.push(MOOD_TAG[diary.mood] || diary.mood)
      if (diary.occasion) tags.push(diary.occasion)
      tags.push('穿搭日记')

      // 优先用用户上传的照片，没有则用今日穿搭的衣物图片
      const postImages = diary.image_urls?.length
        ? diary.image_urls
        : (diary.items || []).map((i: any) => i.image_url).filter(Boolean)

      const post = await createCommunityPost({
        content,
        image_urls: postImages,
        tags,
        diary_id: diary.id,
      })
      setPublishedPost(post)
      setShowPublishConfirm(false)
    } catch (err) {
      console.error('发布失败:', err)
      alert('发布失败，请稍后重试')
    } finally {
      setPublishing(false)
    }
  }

  const handleUnpublish = async () => {
    setShowUnpublishConfirm(true)
  }

  const doUnpublish = async () => {
    try {
      await deletePostByDiary(diary.id)
      setPublishedPost(null)
    } catch (err) {
      console.error('取消发布失败:', err)
      alert('取消发布失败，请稍后重试')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* 头部 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {onBack && (
              <motion.button whileTap={{ scale: 0.9 }} onClick={onBack} className="p-1.5 rounded-lg hover:bg-stone-50 text-stone-500">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
              </motion.button>
            )}
            <span className="text-3xl">{emoji}</span>
            <div>
              <h2 className="font-semibold text-stone-800">{dateStr}</h2>
              {diary.occasion && <p className="text-xs text-stone-500">{diary.occasion}</p>}
            </div>
          </div>
          <div className="flex gap-2">
            {onEdit && (
              <motion.button whileTap={{ scale: 0.95 }} onClick={onEdit} className="px-3 py-1.5 rounded-lg text-xs font-medium border border-stone-200 text-stone-600 hover:bg-stone-50">
                编辑
              </motion.button>
            )}
            {onDelete && (
              <motion.button whileTap={{ scale: 0.95 }} onClick={onDelete} className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-200 text-red-500 hover:bg-red-50">
                删除
              </motion.button>
            )}
          </div>
        </div>

        {/* 评分 */}
        {diary.rating && (
          <div className="flex items-center gap-1 mb-3">
            <span className="text-xs text-stone-500 mr-1">穿搭评分:</span>
            {[1, 2, 3, 4, 5].map((s) => (
              <span key={s} className={s <= diary.rating! ? 'text-amber-400' : 'text-stone-300'}>★</span>
            ))}
          </div>
        )}

                {/* 备注 */}
        {diary.notes && (
          <p className="text-sm text-stone-600 leading-relaxed bg-stone-50 rounded-xl p-3">{diary.notes}</p>
        )}
      </div>

      {/* 穿搭照片 */}
      {diary.image_urls && diary.image_urls.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-3">穿搭照片 ({diary.image_urls.length})</h3>
          <div className="grid grid-cols-3 gap-3">
            {diary.image_urls.map((url, index) => (
              <motion.div
                key={index}
                whileTap={{ scale: 0.97 }}
                onClick={() => setLightboxIndex(index)}
                className="aspect-square rounded-xl overflow-hidden border border-stone-100 cursor-pointer"
              >
                <img src={url} alt={`穿搭照片 ${index + 1}`} className="w-full h-full object-cover" />
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* 图片灯箱 */}
      <AnimatePresence>
        {lightboxIndex !== null && diary.image_urls && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setLightboxIndex(null)}
            className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          >
            <button
              onClick={() => setLightboxIndex(null)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 text-white flex items-center justify-center hover:bg-white/20 transition-colors"
              aria-label="关闭"
            >
              <X className="w-5 h-5" />
            </button>
            <motion.img
              key={lightboxIndex}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              src={diary.image_urls[lightboxIndex]}
              alt={`穿搭照片 ${lightboxIndex + 1}`}
              className="max-w-full max-h-full object-contain rounded-xl"
              onClick={(e) => e.stopPropagation()}
            />
            {/* 左右切换 */}
            {diary.image_urls.length > 1 && (
              <>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setLightboxIndex((prev) => prev === null ? 0 : (prev - 1 + diary.image_urls!.length) % diary.image_urls!.length)
                  }}
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/10 text-white flex items-center justify-center hover:bg-white/20 transition-colors text-xl"
                  aria-label="上一张"
                >
                  ‹
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setLightboxIndex((prev) => prev === null ? 0 : (prev + 1) % diary.image_urls!.length)
                  }}
                  className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/10 text-white flex items-center justify-center hover:bg-white/20 transition-colors text-xl"
                  aria-label="下一张"
                >
                  ›
                </button>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 关联衣物 */}
      {diary.items.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
          <h3 className="text-sm font-semibold text-stone-800 mb-3">今日穿搭 ({diary.items.length}件)</h3>
          <div className="grid grid-cols-3 gap-3">
            {diary.items.map((item) => (
              <div key={item.id} className="rounded-xl overflow-hidden border border-stone-100">
                <div className="aspect-square bg-stone-100">
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.name || ''} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-stone-400 text-2xl">
                      {item.primary_element || '👕'}
                    </div>
                  )}
                </div>
                <div className="p-2">
                  <p className="text-xs text-stone-700 truncate">{item.name || item.category || '衣物'}</p>
                  {item.primary_element && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600">{item.primary_element}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 发布到广场 — 广场关闭期间隐藏，恢复时将下方条件改回 true */}
      {COMMUNITY_ENABLED && (
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        {publishedPost ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-600">
              <CheckCircle className="w-5 h-5" />
              <span className="text-sm font-medium">已发布到穿搭广场</span>
            </div>
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={handleUnpublish}
              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-stone-200 text-stone-500 hover:bg-stone-50"
            >
              取消发布
            </motion.button>
          </div>
        ) : (
          <motion.button
            whileTap={{ scale: 0.97 }}
            onClick={() => setShowPublishConfirm(true)}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-sm"
          >
            <Share2 className="w-4 h-4" />
            发布到穿搭广场
          </motion.button>
        )}
      </div>
      )}

      {/* 发布确认弹窗 */}
      {COMMUNITY_ENABLED && (
      <AnimatePresence>
        {showPublishConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
            onClick={() => setShowPublishConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-sm bg-white rounded-2xl p-6 shadow-2xl"
              onClick={e => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-stone-800 mb-2">发布到穿搭广场</h3>
              <p className="text-sm text-stone-500 mb-4">
                将这篇日记发布到广场，其他用户将可以看到你的穿搭记录。
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowPublishConfirm(false)}
                  className="flex-1 py-2.5 border border-stone-200 rounded-xl text-sm text-stone-600 hover:bg-stone-50"
                >
                  取消
                </button>
                <button
                  onClick={handlePublish}
                  disabled={publishing}
                  className="flex-1 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl text-sm font-medium disabled:opacity-50"
                >
                  {publishing ? '发布中...' : '确认发布'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      )}

      {/* AI 点评 */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-stone-800">AI 穿搭点评</h3>
          {onTriggerReview && (
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={onTriggerReview}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white"
            >
              {typeof diary.ai_review?.score === 'number' ? '重新点评' : '生成点评'}
            </motion.button>
          )}
        </div>

        {typeof diary.ai_review?.score === 'number' ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center">
                <span className="text-xl font-bold text-emerald-600">{diary.ai_review.score}</span>
              </div>
              <p className="text-sm text-stone-700 flex-1">{diary.ai_review.comment}</p>
            </div>

            {diary.ai_review.suggestions && diary.ai_review.suggestions.length > 0 && (
              <div>
                <p className="text-xs font-medium text-stone-600 mb-1.5">改进建议:</p>
                <ul className="space-y-1">
                  {diary.ai_review.suggestions.map((s, i) => (
                    <li key={i} className="text-xs text-stone-500 flex gap-2">
                      <span className="text-emerald-500 flex-shrink-0">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-stone-400 text-center py-4">暂无 AI 点评，点击上方按钮生成</p>
        )}
      </div>

      {/* 取消发布确认弹窗 */}
      {COMMUNITY_ENABLED && (
      <ConfirmDialog
        isOpen={showUnpublishConfirm}
        onClose={() => setShowUnpublishConfirm(false)}
        onConfirm={doUnpublish}
        title="取消发布"
        description="确认从广场取消发布？"
        confirmText="确认"
      />
      )}
    </motion.div>
  )
}
