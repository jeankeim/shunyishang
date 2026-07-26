'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getAuthToken, previewTagging } from '@/lib/api'
import { useWardrobeStore } from '@/store/wardrobe'
import { Camera, X, Loader2, Check, Sparkles } from 'lucide-react'

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
    items?: { item_source: string; wardrobe_item_id?: number }[]
    trigger_ai_review?: boolean
  }) => Promise<void>
  onCancel?: () => void
  isEdit?: boolean
}

// 拍照新增、尚未存入衣橱的候选衣物
interface PendingItem {
  tempId: string
  name: string
  category?: string
  image_url: string
  primary_element: string
  secondary_element?: string
  applicable_weather?: string[]
  applicable_seasons?: string[]
  temperature_range?: { min: number; max: number }
  functionality?: string[]
  thickness_level?: string
  energy_intensity?: number
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

  // 从衣橱选择今日穿搭（仅创建模式；后端 update 不支持修改关联衣物）
  const { items: wardrobeItems, fetchItems, addItem } = useWardrobeStore()
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([])

  useEffect(() => {
    if (!isEdit && wardrobeItems.length === 0) {
      fetchItems()
    }
  }, [isEdit, wardrobeItems.length, fetchItems])

  const toggleItem = (id: number) => {
    setSelectedItemIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  // 拍照/上传新衣物（创建模式）：识别后作为"待存入"候选加入今日穿搭
  const newItemInputRef = useRef<HTMLInputElement>(null)
  const [pendingNewItems, setPendingNewItems] = useState<PendingItem[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [saveToWardrobe, setSaveToWardrobe] = useState<Record<string, boolean>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)

  // 上传图片（含一次自动重试）：抵御开发代理偶发的 socket 中断 / 5xx，返回 image_url
  const uploadImageWithRetry = useCallback(async (file: File, token: string): Promise<string> => {
    const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    const attempt = () => {
      const formData = new FormData()
      formData.append('file', file)
      return fetch(`${API_BASE}/api/v1/wardrobe/upload-image`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      })
    }
    let response: Response | null = null
    for (let i = 0; i < 2; i++) {
      try {
        response = await attempt()
      } catch {
        response = null // 网络中断
      }
      // 成功或 4xx（真实错误）不再重试；仅网络中断 / 5xx 重试一次
      if (response && response.status < 500) break
      if (i === 0) await new Promise((r) => setTimeout(r, 600))
    }
    if (!response) {
      throw new Error('网络连接中断，请重试')
    }
    if (!response.ok) {
      const errData = await response.json().catch(() => null)
      throw new Error(errData?.detail || (response.status >= 500 ? '上传服务暂时不可用，请稍后重试' : '上传失败'))
    }
    const data = await response.json()
    return data.image_url as string
  }, [])

  const handleAddNewItem = useCallback(async (file: File) => {
    setAnalyzeError(null)
    if (!file.type.startsWith('image/')) {
      setAnalyzeError('请上传图片文件（JPG/PNG 等）')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setAnalyzeError('图片大小不能超过 5MB')
      return
    }
    const token = getAuthToken()
    if (!token) {
      setAnalyzeError('请先登录后再添加衣物')
      return
    }
    setAnalyzing(true)
    try {
      // 1) 上传图片（含一次自动重试）
      const image_url = await uploadImageWithRetry(file, token)
      // 2) AI 打标识别五行属性（含一次自动重试）
      let tag
      try {
        tag = await previewTagging('请根据图片分析这件衣物', image_url)
      } catch {
        await new Promise((r) => setTimeout(r, 600))
        tag = await previewTagging('请根据图片分析这件衣物', image_url)
      }
      // 3) 加入待存入候选
      // 名称优先用 AI 建议名；缺失时用「颜色+分类」兜底，最后才回退占位
      const fallbackName = `${tag.color && tag.color !== '未知' ? tag.color : ''}${tag.category || ''}`.trim()
      const pending: PendingItem = {
        tempId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: tag.suggested_name || fallbackName || '未命名衣物',
        category: tag.category,
        image_url,
        primary_element: tag.primary_element,
        secondary_element: tag.secondary_element,
        applicable_weather: tag.applicable_weather,
        applicable_seasons: tag.applicable_seasons,
        temperature_range: tag.temperature_range,
        functionality: tag.functionality,
        thickness_level: tag.thickness_level,
        energy_intensity: tag.energy_intensity,
      }
      setPendingNewItems((prev) => [...prev, pending])
      setSaveToWardrobe((prev) => ({ ...prev, [pending.tempId]: true }))
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : '识别失败，请重试')
    } finally {
      setAnalyzing(false)
    }
  }, [])

  const handleNewItemFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      Array.from(files).forEach(handleAddNewItem)
    }
    if (newItemInputRef.current) {
      newItemInputRef.current.value = ''
    }
  }

  const removePendingItem = (tempId: string) => {
    setPendingNewItems((prev) => prev.filter((p) => p.tempId !== tempId))
  }

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
      const image_url = await uploadImageWithRetry(file, token)
      setImageUrls((prev) => [...prev, image_url])
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

  const doActualSubmit = async () => {
    setShowSaveDialog(false)
    setSubmitError(null)
    setIsSubmitting(true)

    // 1) 先把勾选的待选衣物存入衣橱。已成功存入的：移出 pending、转为“已选衣橱衣物”，
    //    这样即便随后建日记失败、用户重试，也不会重复创建（幂等），也不会同一件既显示“新”又显示已入库。
    const savedIds: number[] = []
    const remainingPendings: PendingItem[] = []
    const extraImageUrls: string[] = []
    for (const p of pendingNewItems) {
      let persisted = false
      if (saveToWardrobe[p.tempId]) {
        try {
          const created = await addItem({
            name: p.name,
            category: p.category,
            image_url: p.image_url,
            primary_element: p.primary_element,
            secondary_element: p.secondary_element,
            description: p.name,
            applicable_weather: p.applicable_weather,
            applicable_seasons: p.applicable_seasons,
            temperature_range: p.temperature_range,
            functionality: p.functionality,
            thickness_level: p.thickness_level,
            energy_intensity: p.energy_intensity,
          })
          savedIds.push(created.id)
          persisted = true
        } catch {
          // 存入衣橱失败：保留为待选并退化为照片，避免丢失
        }
      }
      if (!persisted) {
        remainingPendings.push(p)
        extraImageUrls.push(p.image_url)
      }
    }

    // 已存入的并入“已选”，未成功/未勾选的留在待选（下次重试只处理它们）
    const linkedIds = [...selectedItemIds, ...savedIds]
    if (savedIds.length > 0) {
      setSelectedItemIds(linkedIds)
      setPendingNewItems(remainingPendings)
    }

    // 2) 创建日记
    try {
      const finalImageUrls = [...imageUrls, ...extraImageUrls]
      await onSubmit({
        diary_date: date,
        mood: mood || undefined,
        occasion: occasion || undefined,
        notes: notes || undefined,
        rating: rating || undefined,
        image_urls: finalImageUrls.length > 0 ? finalImageUrls : undefined,
        items: linkedIds.length > 0
          ? linkedIds.map((id) => ({ item_source: 'wardrobe', wardrobe_item_id: id }))
          : undefined,
        trigger_ai_review: true,
      })
      // 成功：由父组件跳转
    } catch (err) {
      // 建日记失败：明确提示。已存入衣橱的衣物已转为“已选”，改好后重试不会重复创建。
      const msg = err instanceof Error ? err.message : '创建日记失败，请稍后重试'
      setSubmitError(
        savedIds.length > 0
          ? `${msg}（新衣物已存入衣橱，修正后可直接重试，不会重复添加）`
          : msg
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    // 创建模式下若有拍照新增的衣物，先统一询问是否存入衣橱
    if (!isEdit && pendingNewItems.length > 0) {
      setSaveToWardrobe((prev) => {
        const next = { ...prev }
        pendingNewItems.forEach((p) => {
          if (next[p.tempId] === undefined) next[p.tempId] = true
        })
        return next
      })
      setShowSaveDialog(true)
      return
    }
    await doActualSubmit()
  }

  return (
    <>
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* 日期 */}
      <div>
        <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">日期</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          max={today}
                    className="w-full px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-[var(--brand-heading)] text-sm focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 transition-all"
          required
        />
      </div>

      {/* 心情 */}
      <div>
        <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">今日心情</label>
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
                  : 'border-stone-200 bg-white text-[var(--brand-body)] hover:bg-stone-50'
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
        <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">场合</label>
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
                  : 'border-stone-200 bg-white text-[var(--brand-body)] hover:bg-stone-50'
              }`}
            >
              {o}
            </motion.button>
          ))}
        </div>
      </div>

      {/* 评分 */}
      <div>
        <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">穿搭评分</label>
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

      {/* 今日穿搭（从衣橱选择 / 拍照新增，仅创建模式） */}
      {!isEdit && (
        <div>
          <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">
            今日穿搭{selectedItemIds.length + pendingNewItems.length > 0 ? `（已选 ${selectedItemIds.length + pendingNewItems.length} 件）` : ''}
          </label>
          {wardrobeItems.length === 0 && pendingNewItems.length === 0 ? (
            <p className="text-xs text-[var(--brand-subtle)] py-3 text-center border-2 border-dashed border-stone-200 rounded-xl">
              衣橱还没有衣物，可拍照识别新衣物添加
            </p>
          ) : (
            <div className="grid grid-cols-4 gap-2 max-h-56 overflow-y-auto p-0.5">
              {/* 拍照新增的待选衣物 */}
              {pendingNewItems.map((item) => (
                <div
                  key={item.tempId}
                  className="relative aspect-square rounded-xl overflow-hidden border-2 border-amber-400 ring-2 ring-amber-200"
                >
                  <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                  <span className="absolute top-1 left-1 px-1 rounded bg-amber-500 text-white text-[10px] leading-4">新</span>
                  <button
                    type="button"
                    onClick={() => removePendingItem(item.tempId)}
                    className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70"
                    aria-label="移除"
                  >
                    <X className="w-3 h-3" />
                  </button>
                  <span className="absolute bottom-0 inset-x-0 bg-black/40 text-white text-[10px] px-1 py-0.5 truncate">
                    {item.name}
                  </span>
                </div>
              ))}
              {/* 衣橱已有衣物 */}
              {wardrobeItems.map((item) => {
                const selected = selectedItemIds.includes(item.id)
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => toggleItem(item.id)}
                    className={`relative aspect-square rounded-xl overflow-hidden border-2 transition-all ${
                      selected ? 'border-emerald-500 ring-2 ring-emerald-200' : 'border-stone-200'
                    }`}
                  >
                    {item.image_url ? (
                      <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-stone-100 text-xl text-stone-400">
                        {item.primary_element || '👕'}
                      </div>
                    )}
                    {selected && (
                      <div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                        <Check className="w-3 h-3" />
                      </div>
                    )}
                    <span className="absolute bottom-0 inset-x-0 bg-black/40 text-white text-[10px] px-1 py-0.5 truncate">
                      {item.name}
                    </span>
                  </button>
                )
              })}
            </div>
          )}

          {/* 拍照识别新衣物 */}
          <input
            ref={newItemInputRef}
            type="file"
            accept="image/*"
            onChange={handleNewItemFileSelect}
            className="hidden"
          />
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={() => newItemInputRef.current?.click()}
            disabled={analyzing}
            className="w-full mt-2 py-2.5 rounded-xl border-2 border-dashed border-stone-300 text-[var(--brand-subtle)] text-sm flex items-center justify-center gap-2 hover:border-amber-400 hover:text-amber-600 hover:bg-amber-50/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {analyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                识别中...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                拍照识别新衣物
              </>
            )}
          </motion.button>
          {analyzeError && <p className="text-xs text-red-500 mt-1">{analyzeError}</p>}
          <p className="text-[11px] text-[var(--brand-subtle)] mt-1.5 leading-relaxed">
            拍照或上传衣物照片，AI 会识别五行属性。创建日记时可选择存入衣橱；不存入的会作为本次日记照片保留。
          </p>
        </div>
      )}

      {/* 穿搭照片（编辑模式：仅附日记照片，不入衣橱） */}
      {isEdit && (
      <div>
        <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">穿搭照片</label>
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
          className="w-full py-3 rounded-xl border-2 border-dashed border-stone-300 text-[var(--brand-subtle)] text-sm flex items-center justify-center gap-2 hover:border-emerald-400 hover:text-emerald-600 hover:bg-emerald-50/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
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
      )}

      {/* 备注 */}
      <div>
        <label className="block text-sm font-medium text-[var(--brand-body)] mb-1.5">穿搭备注</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="记录今天的穿搭心得..."
          rows={3}
                    className="w-full px-3 py-2.5 rounded-xl border border-stone-200 bg-white text-[var(--brand-heading)] text-sm placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:border-emerald-400 transition-all resize-none"
        />
      </div>

      {/* 提交失败提示 */}
      {submitError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {submitError}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-3 pt-2">
        {onCancel && (
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={onCancel}
            className="flex-1 py-3 rounded-xl border border-stone-200 text-[var(--brand-body)] text-sm font-medium hover:bg-stone-50 transition-colors"
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

    {/* 存入衣橱确认弹窗 */}
    {showSaveDialog && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
        <div className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-xl">
          <h3 className="text-base font-semibold text-[var(--brand-heading)]">存入我的衣橱？</h3>
          <p className="mt-1 text-xs text-[var(--brand-subtle)]">
            以下 {pendingNewItems.length} 件是新拍的衣物。勾选后会存入你的衣橱，下次记录穿搭就不用重新拍照啦。
          </p>
          <div className="mt-3 space-y-2 max-h-64 overflow-y-auto">
            {pendingNewItems.map((item) => {
              const checked = saveToWardrobe[item.tempId] ?? true
              return (
                <button
                  key={item.tempId}
                  type="button"
                  onClick={() => setSaveToWardrobe((prev) => ({ ...prev, [item.tempId]: !checked }))}
                  className={`w-full flex items-center gap-3 p-2 rounded-xl border text-left transition-all ${
                    checked ? 'border-emerald-400 bg-emerald-50' : 'border-stone-200 bg-white'
                  }`}
                >
                  <img src={item.image_url} alt={item.name} className="w-12 h-12 rounded-lg object-cover flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--brand-heading)] truncate">{item.name}</p>
                    <p className="text-xs text-[var(--brand-subtle)]">{item.category || '衣物'} · {item.primary_element}</p>
                  </div>
                  <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${
                    checked ? 'bg-emerald-500 text-white' : 'border border-stone-300'
                  }`}>
                    {checked && <Check className="w-3.5 h-3.5" />}
                  </div>
                </button>
              )
            })}
          </div>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => setShowSaveDialog(false)}
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl border border-stone-200 text-[var(--brand-body)] text-sm font-medium hover:bg-stone-50 transition-colors disabled:opacity-60"
            >
              返回修改
            </button>
            <button
              type="button"
              onClick={doActualSubmit}
              disabled={isSubmitting}
              className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm hover:shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? '创建中...' : '确认创建'}
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  )
}
