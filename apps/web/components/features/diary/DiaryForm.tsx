'use client'

import { useState, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { getAuthToken } from '@/lib/api'
import { Camera, X, Loader2 } from 'lucide-react'

const MOODS = [
  { value: 'happy', label: '开心', emoji: '😊' },
  { value: 'excited', label: '兴奋', emoji: '🤩' },
  { value: 'calm', label: '平静', emoji: '😌' },
  { value: 'neutral', label: '一般', emoji: '😐' },
  { value: 'sad', label: '低落', emoji: '😢' },
]

const OCCASIONS = ['日常', '上班', '约会', '聚会', '运动', '旅行', '正式场合']

interface DiaryFormProps {
  initialData?: {
    diary_date?: string
    mood?: string
    occasion?: string
    notes?: string
    rating?: number
    image_urls?: string[]
  }
  onSubmit: (data: {
    diary_date: string
    mood?: string
    occasion?: string
    notes?: string
    rating?: number
    image_urls?: string[]
    trigger_ai_review?: boolean
  }) => Promise<void>
  onCancel?: () => void
  isEdit?: boolean
}

export function DiaryForm({ initialData, onSubmit, onCancel, isEdit }: DiaryFormProps) {
  const today = new Date().toISOString().split('T')[0]
  const [date, setDate] = useState(initialData?.diary_date || today)
  const [mood, setMood] = useState(initialData?.mood || '')
  const [occasion, setOccasion] = useState(initialData?.occasion || '')
  const [notes, setNotes] = useState(initialData?.notes || '')
  const [rating, setRating] = useState(initialData?.rating || 0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [imageUrls, setImageUrls] = useState<string[]>(initialData?.image_urls || [])
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUploadImage = useCallback(async (file: File) => {
    setUploadError(null)

    // 验证文件类型
    if (!file.type.startsWith('image/')) {
      setUploadError('请上传图片文件（JPG/PNG 等）')
      return
    }
    // 验证文件大小 (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setUploadError('图片大小不能超过 5MB')
      return
    }

    const token = getAuthToken()
    if (!token) {
      setUploadError('请先登录后再上传图片')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
      const response = await fetch(`${API_BASE}/api/v1/wardrobe/upload-image`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '上传失败')
      }

      const data = await response.json()
      setImageUrls((prev) => [...prev, data.image_url])
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : '上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      Array.from(files).forEach(handleUploadImage)
    }
    // 重置 input 以便可以重复选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleRemoveImage = (index: number) => {
    setImageUrls((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await onSubmit({
        diary_date: date,
        mood: mood || undefined,
        occasion: occasion || undefined,
        notes: notes || undefined,
        rating: rating || undefined,
        image_urls: imageUrls.length > 0 ? imageUrls : undefined,
        trigger_ai_review: true,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* 日期 */}
      <div>
        <label className="block text-sm font-medium text-[#4A5F52] mb-1.5">日期</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          max={today}
                    className="w-full px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-[#2D4A38] text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 transition-all"
          required
        />
      </div>

      {/* 心情 */}
      <div>
        <label className="block text-sm font-medium text-[#4A5F52] mb-1.5">今日心情</label>
        <div className="flex gap-2">
          {MOODS.map((m) => (
            <motion.button
              key={m.value}
              type="button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setMood(mood === m.value ? '' : m.value)}
              className={`flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl border text-sm transition-all ${
                mood === m.value
                  ? 'border-emerald-400 bg-emerald-50 text-emerald-700 shadow-sm'
                  : 'border-stone-200 bg-white text-[#4A5F52] hover:bg-stone-50'
              }`}
            >
              <span className="text-lg">{m.emoji}</span>
              <span className="text-xs">{m.label}</span>
            </motion.button>
          ))}
        </div>
      </div>

      {/* 场合 */}
      <div>
        <label className="block text-sm font-medium text-[#4A5F52] mb-1.5">场合</label>
        <div className="flex flex-wrap gap-2">
          {OCCASIONS.map((o) => (
            <motion.button
              key={o}
              type="button"
              whileTap={{ scale: 0.95 }}
              onClick={() => setOccasion(occasion === o ? '' : o)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                occasion === o
                  ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
                  : 'border-stone-200 bg-white text-[#4A5F52] hover:bg-stone-50'
              }`}
            >
              {o}
            </motion.button>
          ))}
        </div>
      </div>

      {/* 评分 */}
      <div>
        <label className="block text-sm font-medium text-[#4A5F52] mb-1.5">穿搭评分</label>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <motion.button
              key={star}
              type="button"
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setRating(rating === star ? 0 : star)}
              className="text-2xl transition-colors"
            >
              <span className={star <= rating ? 'text-amber-400' : 'text-stone-300'}>
                ★
              </span>
            </motion.button>
          ))}
        </div>
      </div>

      {/* 穿搭照片 */}
      <div>
        <label className="block text-sm font-medium text-[#4A5F52] mb-1.5">穿搭照片</label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* 已上传图片预览 */}
        {imageUrls.length > 0 && (
          <div className="grid grid-cols-3 gap-2 mb-2">
            {imageUrls.map((url, index) => (
              <div key={index} className="relative group aspect-square rounded-xl overflow-hidden border border-stone-200">
                <img src={url} alt={`穿搭照片 ${index + 1}`} className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => handleRemoveImage(index)}
                  className="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                  aria-label="删除照片"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* 上传按钮 */}
        <motion.button
          type="button"
          whileTap={{ scale: 0.98 }}
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="w-full py-3 rounded-xl border-2 border-dashed border-stone-300 text-[#6B7F72] text-sm flex items-center justify-center gap-2 hover:border-emerald-400 hover:text-emerald-600 hover:bg-emerald-50/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              上传中...
            </>
          ) : (
            <>
              <Camera className="w-4 h-4" />
              {imageUrls.length > 0 ? '继续添加照片' : '添加穿搭照片'}
            </>
          )}
        </motion.button>

        {uploadError && (
          <p className="text-xs text-red-500 mt-1">{uploadError}</p>
        )}
      </div>

      {/* 备注 */}
      <div>
        <label className="block text-sm font-medium text-[#4A5F52] mb-1.5">穿搭备注</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="记录今天的穿搭心得..."
          rows={3}
                    className="w-full px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-[#2D4A38] text-sm placeholder:text-[#6B7F72] focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 transition-all resize-none"
        />
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3 pt-2">
        {onCancel && (
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={onCancel}
            className="flex-1 py-3 rounded-xl border border-stone-200 text-[#4A5F52] text-sm font-medium hover:bg-stone-50 transition-colors"
          >
            取消
          </motion.button>
        )}
        <motion.button
          type="submit"
          whileTap={{ scale: 0.98 }}
          disabled={isSubmitting}
          className="flex-1 py-3 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm hover:shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isSubmitting ? '保存中...' : isEdit ? '更新日记' : '创建日记'}
        </motion.button>
      </div>
    </form>
  )
}
