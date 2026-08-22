'use client'

/**
 * 批量上传衣物弹窗
 *
 * 三步状态机：
 * - select：拖拽/选择器选图（≤5 张，"已选 N/5"），支持分批连续上传
 * - review：并行上传 + VL 批量识别，卡片预览基础属性（同意/编辑，单件失败可重试/移除）
 * - wuxing：五行深度分析（规则引擎 + 喜用神比对），全字段可编辑，批量入库（部分成功语义）
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ModalPortal } from '@/components/ui/ModalPortal'
import { useWardrobeStore } from '@/store/wardrobe'
import { useUserStore } from '@/store/user'
import {
  initAuthToken,
  uploadWardrobeImage,
  batchRecognizeItems,
  batchWuxingAnalysis,
  BatchAddItemRequest,
} from '@/lib/api'
import { WUXING_ELEMENTS, WUXING_CONFIG, getWuxingConfig } from '@/lib/wuxing-config'
import { compressImageFile } from '@/lib/image-compress'

const MAX_BATCH = 5
const MAX_FILE_SIZE = 5 * 1024 * 1024
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const CATEGORIES = ['上装', '下装', '外套', '鞋履', '配饰', '裙装', '套装', '饰品', '文玩', '其他'] as const
const GENDERS = ['男', '女', '中性'] as const
const SEASONS = ['春', '夏', '秋', '冬'] as const
const OCCASIONS = ['日常', '通勤', '商务', '约会', '休闲', '运动', '聚会', '旅行'] as const

type Step = 'select' | 'review' | 'wuxing'

/** select 步本地预览条目：blob URL 仅在选图时创建一次，
 * 避免渲染期间反复 createObjectURL 导致 next/image 重载竞态、移动端预览图空白 */
interface SelectedEntry {
  id: string
  file: File
  previewUrl: string
}

/** 单件衣物卡片状态（贯穿识别→五行→入库全流程） */
interface BatchCard {
  id: string
  file: File
  previewUrl: string
  // 上传
  imageUrl: string
  uploadStatus: 'uploading' | 'done' | 'failed'
  // 第一阶段识别结果
  name: string
  description: string
  category?: string
  gender?: string
  applicable_seasons: string[]
  functionality: string[]
  color: string
  material: string
  style?: string
  confidence: number
  needsManualReview: boolean
  isEditing: boolean
  // 第二阶段五行分析结果
  primary_element?: string
  secondary_element?: string
  color_element?: string
  material_element?: string
  style_element?: string
  xiyong_match?: string
  xiyong_advice?: string
  // 入库失败原因（部分成功时保留卡片）
  saveFailedReason?: string
}

interface BatchUploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function BatchUploadModal({ isOpen, onClose, onSuccess }: BatchUploadModalProps) {
  const { addItems } = useWardrobeStore()
  const { isAuthenticated } = useUserStore()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<Step>('select')
  const [selectedFiles, setSelectedFiles] = useState<SelectedEntry[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [cards, setCards] = useState<BatchCard[]>([])
  const [isRecognizing, setIsRecognizing] = useState(false)
  const [wuxingLoading, setWuxingLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [xiyongElements, setXiyongElements] = useState<string[]>([])

  useEffect(() => {
    initAuthToken()
  }, [])

  // 弹窗关闭时重置
  useEffect(() => {
    if (!isOpen) {
      // 回收 blob URL，避免内存泄漏
      selectedFiles.forEach(e => URL.revokeObjectURL(e.previewUrl))
      cards.forEach(c => URL.revokeObjectURL(c.previewUrl))
      setStep('select')
      setSelectedFiles([])
      setCards([])
      setIsRecognizing(false)
      setWuxingLoading(false)
      setIsSubmitting(false)
      setError('')
      setSuccessMsg('')
      setXiyongElements([])
    }
  }, [isOpen])

  // ---------- select 步：文件选择 ----------

  const addFiles = useCallback(async (files: FileList | File[]) => {
    setError('')
    setSuccessMsg('')
    const incoming = Array.from(files)
    const accepted: SelectedEntry[] = []
    for (const f of incoming) {
      if (selectedFiles.length + accepted.length >= MAX_BATCH) {
        setError(`每批最多上传 ${MAX_BATCH} 件，超出部分请分批上传`)
        break
      }
      if (!ACCEPTED_TYPES.includes(f.type)) {
        setError(`「${f.name}」格式不支持，仅支持 JPG/PNG/WebP`)
        continue
      }
      // 超限图片前端自动压缩至 5MB 内（未超限原样保留，零损耗）
      let target = f
      if (f.size > MAX_FILE_SIZE) {
        try {
          target = await compressImageFile(f, MAX_FILE_SIZE)
        } catch {
          setError(`「${f.name}」解析失败，请更换图片`)
          continue
        }
      }
      if (target.size > MAX_FILE_SIZE) {
        setError(`「${f.name}」过大且无法压缩至 5MB 内，请更换图片`)
        continue
      }
      accepted.push({ id: makeId(), file: target, previewUrl: URL.createObjectURL(target) })
    }
    if (accepted.length > 0) {
      setSelectedFiles(prev => [...prev, ...accepted])
    }
  }, [selectedFiles.length])

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => {
      const target = prev[index]
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((_, i) => i !== index)
    })
    setError('')
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files)
    }
  }, [addFiles])

  // ---------- review 步：并行上传 + 批量识别 ----------

  const handleStartRecognize = async () => {
    if (selectedFiles.length === 0) {
      setError('请先选择图片')
      return
    }
    if (!isAuthenticated) {
      setError('请先登录后再上传衣物')
      return
    }
    setError('')
    setSuccessMsg('')
    setStep('review')
    setIsRecognizing(true)

    const initial: BatchCard[] = selectedFiles.map(entry => ({
      id: entry.id,
      file: entry.file,
      previewUrl: entry.previewUrl,
      imageUrl: '',
      uploadStatus: 'uploading',
      name: '',
      description: '',
      category: undefined,
      gender: undefined,
      applicable_seasons: [],
      functionality: [],
      color: '',
      material: '',
      style: undefined,
      confidence: 0,
      needsManualReview: false,
      isEditing: false,
    }))
    setCards(initial)
    setSelectedFiles([])

    // 并行上传全部图片
    const uploadResults = await Promise.allSettled(
      initial.map(card => uploadWardrobeImage(card.file))
    )
    const uploaded: BatchCard[] = initial.map((card, i) => {
      const r = uploadResults[i]
      return r.status === 'fulfilled'
        ? { ...card, imageUrl: r.value, uploadStatus: 'done' as const }
        : { ...card, uploadStatus: 'failed' as const, needsManualReview: true, isEditing: true }
    })

    // 上传成功的进入批量识别
    const okCards = uploaded.filter(c => c.uploadStatus === 'done')
    let afterRecognize = uploaded
    if (okCards.length > 0) {
      try {
        const results = await batchRecognizeItems(
          okCards.map((c, i) => ({ index: i, image_url: c.imageUrl }))
        )
        const byIndex = new Map(results.map(r => [r.index, r]))
        let okIdx = 0
        afterRecognize = uploaded.map(card => {
          if (card.uploadStatus !== 'done') return card
          const r = byIndex.get(okIdx++)
          if (!r || r.error || r.needs_manual_review) {
            return {
              ...card,
              needsManualReview: true,
              isEditing: true,
              name: card.name || r?.suggested_name || '',
              description: r?.description || card.description,
              color: r?.color || card.color,
              material: r?.material || card.material,
              category: r?.category ?? card.category,
            }
          }
          return {
            ...card,
            name: r.suggested_name || card.name,
            description: r.description || '',
            category: r.category ?? undefined,
            gender: r.gender ?? undefined,
            applicable_seasons: r.applicable_seasons || [],
            functionality: r.functionality || [],
            color: r.color || '',
            material: r.material || '',
            style: r.style ?? undefined,
            confidence: r.confidence ?? 0,
            needsManualReview: false,
            isEditing: false,
          }
        })
      } catch (err) {
        // 识别接口整体失败：全部转手动填写
        afterRecognize = uploaded.map(c =>
          c.uploadStatus === 'done'
            ? { ...c, needsManualReview: true, isEditing: true }
            : c
        )
        setError(err instanceof Error ? err.message : 'AI 识别失败，请手动填写或重试')
      }
    }
    setCards(afterRecognize)
    setIsRecognizing(false)
  }

  // 单件重试：重新上传 + 单独识别
  const retryCard = async (cardId: string) => {
    setError('')
    setCards(prev => prev.map(c => (c.id === cardId ? { ...c, uploadStatus: 'uploading', saveFailedReason: undefined } : c)))
    const card = cards.find(c => c.id === cardId)
    if (!card) return

    try {
      const url = await uploadWardrobeImage(card.file)
      const results = await batchRecognizeItems([{ index: 0, image_url: url }])
      const r = results[0]
      setCards(prev => prev.map(c => {
        if (c.id !== cardId) return c
        if (!r || r.error || r.needs_manual_review) {
          return { ...c, imageUrl: url, uploadStatus: 'done', needsManualReview: true, isEditing: true }
        }
        return {
          ...c,
          imageUrl: url,
          uploadStatus: 'done',
          name: r.suggested_name || c.name,
          description: r.description || c.description,
          category: r.category ?? c.category,
          gender: r.gender ?? c.gender,
          applicable_seasons: r.applicable_seasons || c.applicable_seasons,
          functionality: r.functionality || c.functionality,
          color: r.color || c.color,
          material: r.material || c.material,
          style: r.style ?? c.style,
          confidence: r.confidence ?? 0,
          needsManualReview: false,
          isEditing: false,
        }
      }))
    } catch (err) {
      setCards(prev => prev.map(c => (c.id === cardId ? { ...c, uploadStatus: 'failed' } : c)))
      setError(err instanceof Error ? err.message : '重试失败，请稍后再试')
    }
  }

  const removeCard = (cardId: string) => {
    setCards(prev => {
      const target = prev.find(c => c.id === cardId)
      if (target) URL.revokeObjectURL(target.previewUrl)
      return prev.filter(c => c.id !== cardId)
    })
  }

  const updateCard = useCallback((cardId: string, patch: Partial<BatchCard>) => {
    setCards(prev => prev.map(c => (c.id === cardId ? { ...c, ...patch } : c)))
  }, [])

  const toggleArrayValue = (cardId: string, field: 'applicable_seasons' | 'functionality', value: string) => {
    setCards(prev => prev.map(c => {
      if (c.id !== cardId) return c
      const current = c[field] || []
      const next = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value]
      return { ...c, [field]: next }
    }))
  }

  // ---------- wuxing 步：五行深度分析 ----------

  const handleConfirmBasic = async () => {
    const validCards = cards.filter(c => c.uploadStatus === 'done')
    if (validCards.length === 0) {
      setError('没有可确认的衣物，请重试上传或移除失败项')
      return
    }
    setError('')
    setStep('wuxing')
    setWuxingLoading(true)
    try {
      const resp = await batchWuxingAnalysis(
        cards.map((c, i) => ({
          index: i,
          name: c.name,
          category: c.category,
          color: c.color,
          material: c.material,
          style: c.style,
        }))
      )
      const byIndex = new Map(resp.results.map(r => [r.index, r]))
      setCards(prev => prev.map((c, i) => {
        const r = byIndex.get(i)
        if (!r) return c
        return {
          ...c,
          primary_element: r.primary_element,
          secondary_element: r.secondary_element ?? undefined,
          color_element: r.color_element ?? undefined,
          material_element: r.material_element ?? undefined,
          style_element: r.style_element ?? undefined,
          xiyong_match: r.xiyong_match ?? undefined,
          xiyong_advice: r.xiyong_advice ?? undefined,
        }
      }))
      setXiyongElements(resp.xiyong_elements || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '五行分析失败，请稍后重试')
    } finally {
      setWuxingLoading(false)
    }
  }

  // ---------- 批量入库（部分成功语义） ----------

  const handleSave = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)
    setError('')
    setSuccessMsg('')
    try {
      const payload: BatchAddItemRequest[] = cards.map(c => ({
        name: c.name.trim() || `${c.color || '未命名'}${c.category || '衣物'}`,
        description: c.description || undefined,
        category: c.category || undefined,
        image_url: c.imageUrl || undefined,
        primary_element: c.primary_element || '金',
        secondary_element: c.secondary_element || undefined,
        color: c.color || undefined,
        color_element: c.color_element || undefined,
        material: c.material || undefined,
        material_element: c.material_element || undefined,
        style: c.style || undefined,
        season: c.applicable_seasons,
        tags: [],
        confidence: c.confidence || undefined,
        xiyong_match: c.xiyong_match || undefined,
        xiyong_advice: c.xiyong_advice || undefined,
        gender: c.gender || undefined,
        applicable_seasons: c.applicable_seasons,
        functionality: c.functionality,
      }))

      const resp = await addItems(payload)
      onSuccess()

      if (resp.failed.length === 0) {
        // 全部成功：清空已选，弹窗保留支持下一批
        setSuccessMsg(`成功入库 ${resp.created.length} 件，可继续上传下一批`)
        cards.forEach(c => URL.revokeObjectURL(c.previewUrl))
        setCards([])
        setStep('select')
      } else {
        // 部分失败：成功项已进列表，失败卡片保留可重提
        const failedMap = new Map(resp.failed.map(f => [f.index, f.reason]))
        setCards(prev =>
          prev
            .map((c, i) => (failedMap.has(i) ? { ...c, saveFailedReason: failedMap.get(i) } : c))
            .filter((_, i) => failedMap.has(i))
        )
        setError(`成功入库 ${resp.created.length} 件，${resp.failed.length} 件失败，请修改后重新提交`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量入库失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (isRecognizing || isSubmitting) return
    selectedFiles.forEach(e => URL.revokeObjectURL(e.previewUrl))
    cards.forEach(c => URL.revokeObjectURL(c.previewUrl))
    onClose()
  }

  // ---------- 渲染 ----------

  if (!isOpen) return null

  const chipClass = (active: boolean) =>
    `px-2.5 py-1 rounded-lg text-xs font-medium transition-all border ${
      active
        ? 'bg-gradient-to-r from-rose-400 to-pink-400 text-white border-transparent'
        : 'bg-white text-[var(--brand-body)] border-stone-200 hover:border-rose-300'
    }`

  /** 五行徽章 */
  const renderElementBadge = (element?: string) => {
    if (!element) return null
    const config = getWuxingConfig(element)
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg ${config.bgClass} ${config.textClass} text-xs font-medium`}>
        <span>{config.emoji}</span>
        <span>{element}</span>
      </span>
    )
  }

  /** 喜用匹配徽章 */
  const renderXiyongBadge = (card: BatchCard) => {
    if (!card.xiyong_match) return null
    if (card.xiyong_match === '喜用匹配') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200" title={card.xiyong_advice || ''}>
          ✓ 喜用匹配
        </span>
      )
    }
    if (card.xiyong_match === '忌讳五行') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-stone-100 text-stone-500 text-xs font-medium border border-stone-200" title={card.xiyong_advice || ''}>
          ⚠ 忌讳五行
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-stone-50 text-[var(--brand-subtle)] text-xs font-medium border border-stone-200" title={card.xiyong_advice || ''}>
        {card.xiyong_match}
      </span>
    )
  }

  /** 五行选择器（主五行可编辑） */
  const renderElementSelector = (card: BatchCard) => (
    <div className="flex flex-wrap gap-1.5">
      {WUXING_ELEMENTS.map(el => {
        const config = WUXING_CONFIG[el]
        const selected = card.primary_element === el
        return (
          <button
            key={el}
            type="button"
            onClick={() => updateCard(card.id, { primary_element: el })}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selected
                ? `${config.bgClass} ${config.textClass} ring-2 ${config.ringClass}`
                : 'bg-stone-50 text-[var(--brand-subtle)] hover:bg-stone-100'
            }`}
          >
            {config.emoji} {el}
          </button>
        )
      })}
    </div>
  )

  /** 单件卡片（review / wuxing 步共用） */
  const renderCard = (card: BatchCard) => {
    const encodedImage = card.imageUrl && !card.imageUrl.startsWith('data:')
      ? encodeURI(card.imageUrl)
      : card.previewUrl

    return (
      <motion.div
        key={card.id}
        layout
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className={`rounded-2xl border p-4 space-y-3 ${
          card.saveFailedReason || card.uploadStatus === 'failed'
            ? 'border-red-300 bg-red-50/50'
            : card.needsManualReview
              ? 'border-amber-300 bg-amber-50/30'
              : 'border-stone-200 bg-white'
        }`}
      >
        {/* 图片 + 状态 */}
        <div className="flex gap-3">
          <div className="relative w-20 h-20 rounded-xl overflow-hidden bg-stone-100 flex-shrink-0">
            {/* 原生 img 急加载：避免 next/image 对 blob/外链 URL 的加载竞态 */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={encodedImage}
              alt={card.name || '衣物'}
              loading="eager"
              decoding="async"
              // 上传后 URL 加载失败时回退本地预览，保证图区不空白
              onError={e => {
                const el = e.currentTarget
                if (card.previewUrl && el.src !== card.previewUrl) el.src = card.previewUrl
              }}
              className="absolute inset-0 h-full w-full object-cover"
            />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {card.uploadStatus === 'uploading' && (
                <span className="text-xs text-[var(--brand-subtle)] flex items-center gap-1">
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  上传中...
                </span>
              )}
              {card.uploadStatus === 'failed' && (
                <span className="text-xs text-red-600 font-medium">上传失败</span>
              )}
              {card.needsManualReview && card.uploadStatus === 'done' && (
                <span className="text-xs text-amber-600 font-medium">需手动填写</span>
              )}
              {renderXiyongBadge(card)}
              {renderElementBadge(card.primary_element)}
            </div>
            {card.saveFailedReason && (
              <p className="text-xs text-red-600 mt-1">入库失败：{card.saveFailedReason}</p>
            )}
            {card.xiyong_advice && step === 'wuxing' && !card.isEditing && (
              <p className="text-xs text-[var(--brand-subtle)] mt-1 line-clamp-2">{card.xiyong_advice}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => removeCard(card.id)}
            className="text-stone-400 hover:text-red-500 transition-colors self-start flex-shrink-0"
            aria-label="移除"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 上传失败：重试/移除 */}
        {card.uploadStatus === 'failed' ? (
          <button
            type="button"
            onClick={() => retryCard(card.id)}
            className="w-full py-2 rounded-xl border border-rose-300 text-rose-500 text-sm font-medium hover:bg-rose-50 transition-colors"
          >
            重试上传
          </button>
        ) : card.isEditing || card.needsManualReview ? (
          /* 编辑模式 */
          <div className="space-y-2.5">
            <input
              type="text"
              value={card.name}
              onChange={e => updateCard(card.id, { name: e.target.value })}
              placeholder="衣物名称"
              className="w-full px-3 py-2 rounded-xl border border-stone-200 focus:border-rose-400 focus:ring-2 focus:ring-rose-100 outline-none text-sm text-[var(--brand-heading)]"
            />
            <textarea
              value={card.description}
              onChange={e => updateCard(card.id, { description: e.target.value })}
              placeholder="描述（视觉特征、款式等）"
              rows={2}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 focus:border-rose-400 focus:ring-2 focus:ring-rose-100 outline-none text-sm resize-none text-[var(--brand-body)]"
            />
            {/* 品类 */}
            <div className="flex flex-wrap gap-1.5">
              {CATEGORIES.map(cat => (
                <button key={cat} type="button" onClick={() => updateCard(card.id, { category: card.category === cat ? undefined : cat })} className={chipClass(card.category === cat)}>
                  {cat}
                </button>
              ))}
            </div>
            {/* 性别 + 季节 */}
            <div className="flex flex-wrap gap-1.5">
              {GENDERS.map(g => (
                <button key={g} type="button" onClick={() => updateCard(card.id, { gender: card.gender === g ? undefined : g })} className={chipClass(card.gender === g)}>
                  {g}
                </button>
              ))}
              <span className="w-px bg-stone-200 mx-1" />
              {SEASONS.map(s => (
                <button key={s} type="button" onClick={() => toggleArrayValue(card.id, 'applicable_seasons', s)} className={chipClass(card.applicable_seasons.includes(s))}>
                  {s}
                </button>
              ))}
            </div>
            {/* 场合 */}
            <div className="flex flex-wrap gap-1.5">
              {Array.from(new Set([...OCCASIONS, ...card.functionality])).map(o => (
                <button key={o} type="button" onClick={() => toggleArrayValue(card.id, 'functionality', o)} className={chipClass(card.functionality.includes(o))}>
                  {o}
                </button>
              ))}
            </div>
            {/* 颜色/材质/风格（五行步追加展示五行徽章） */}
            <div className="grid grid-cols-3 gap-2">
              <input type="text" value={card.color} onChange={e => updateCard(card.id, { color: e.target.value })} placeholder="颜色" className="px-2.5 py-1.5 rounded-lg border border-stone-200 focus:border-rose-400 outline-none text-xs" />
              <input type="text" value={card.material} onChange={e => updateCard(card.id, { material: e.target.value })} placeholder="材质" className="px-2.5 py-1.5 rounded-lg border border-stone-200 focus:border-rose-400 outline-none text-xs" />
              <input type="text" value={card.style || ''} onChange={e => updateCard(card.id, { style: e.target.value })} placeholder="风格" className="px-2.5 py-1.5 rounded-lg border border-stone-200 focus:border-rose-400 outline-none text-xs" />
            </div>
            {step === 'wuxing' && (
              <>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-[var(--brand-subtle)]">主五行：</span>
                  {renderElementSelector(card)}
                </div>
                {(card.color_element || card.material_element) && (
                  <div className="flex items-center gap-2 text-xs text-[var(--brand-subtle)]">
                    {card.color_element && <span>颜色属{card.color_element}</span>}
                    {card.material_element && <span>材质属{card.material_element}</span>}
                    {card.style_element && <span>风格属{card.style_element}</span>}
                  </div>
                )}
              </>
            )}
            {!card.needsManualReview && (
              <button
                type="button"
                onClick={() => updateCard(card.id, { isEditing: false })}
                className="text-xs text-rose-500 hover:text-rose-600 font-medium"
              >
                ✓ 完成编辑
              </button>
            )}
          </div>
        ) : (
          /* 展示模式 */
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-sm text-[var(--brand-heading)] truncate">{card.name || '未命名'}</span>
              <button
                type="button"
                onClick={() => updateCard(card.id, { isEditing: true })}
                className="text-xs text-rose-500 hover:text-rose-600 font-medium flex-shrink-0"
              >
                编辑
              </button>
            </div>
            {card.description && (
              <p className="text-xs text-[var(--brand-subtle)] line-clamp-2">{card.description}</p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {card.category && <span className="px-2 py-0.5 rounded-md bg-rose-50 text-rose-600 text-xs">{card.category}</span>}
              {card.gender && <span className="px-2 py-0.5 rounded-md bg-stone-100 text-[var(--brand-body)] text-xs">{card.gender}</span>}
              {card.applicable_seasons.map(s => (
                <span key={s} className="px-2 py-0.5 rounded-md bg-stone-100 text-[var(--brand-body)] text-xs">{s}</span>
              ))}
              {card.functionality.map(o => (
                <span key={o} className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-600 text-xs">{o}</span>
              ))}
            </div>
            {(card.color || card.material || card.style) && (
              <div className="flex items-center gap-2 text-xs text-[var(--brand-subtle)] flex-wrap">
                {card.color && <span>颜色：{card.color}</span>}
                {card.material && <span>材质：{card.material}</span>}
                {card.style && <span>风格：{card.style}</span>}
              </div>
            )}
            {step === 'wuxing' && (card.color_element || card.material_element || card.style_element) && (
              <div className="flex items-center gap-2 text-xs text-[var(--brand-subtle)] flex-wrap">
                {card.color_element && <span>颜色属{card.color_element}</span>}
                {card.material_element && <span>材质属{card.material_element}</span>}
                {card.style_element && <span>风格属{card.style_element}</span>}
              </div>
            )}
            {card.confidence > 0 && (
              <div className="text-xs text-[var(--brand-subtle)]">置信度 {(card.confidence * 100).toFixed(0)}%</div>
            )}
          </div>
        )}
      </motion.div>
    )
  }

  return (
    <ModalPortal>
    <AnimatePresence>
      <div className="fixed inset-x-0 top-0 h-viewport z-[70] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          onClick={handleClose}
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 16 }}
          className="relative w-full max-w-2xl max-h-[90vh] bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* 头部 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100 flex-shrink-0">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-[var(--brand-heading)]">批量上传衣物</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                (step === 'select' ? selectedFiles.length : cards.length) >= MAX_BATCH
                  ? 'bg-stone-200 text-stone-500'
                  : 'bg-rose-50 text-rose-600'
              }`}>
                已选 {step === 'select' ? selectedFiles.length : cards.length}/{MAX_BATCH}
              </span>
            </div>
            <button
              type="button"
              onClick={handleClose}
              disabled={isRecognizing || isSubmitting}
              className="w-8 h-8 rounded-full hover:bg-stone-100 flex items-center justify-center text-stone-400 hover:text-stone-600 transition-colors disabled:opacity-50"
              aria-label="关闭"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* 内容区 */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            {successMsg && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 px-4 py-3 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-700"
              >
                {successMsg}
              </motion.div>
            )}
            {error && (
              <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* ===== select 步 ===== */}
            {step === 'select' && (
              <div className="space-y-4">
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
                    dragOver
                      ? 'border-rose-400 bg-rose-50'
                      : 'border-stone-300 hover:border-rose-300 hover:bg-rose-50/30'
                  }`}
                >
                  <div className="text-4xl mb-3">👕</div>
                  <p className="text-sm font-medium text-[var(--brand-body)]">拖拽图片到此处，或点击选择</p>
                  <p className="text-xs text-[var(--brand-subtle)] mt-1">
                    支持 JPG / PNG / WebP，超过 5MB 自动压缩，每批最多 {MAX_BATCH} 件
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={e => {
                      if (e.target.files?.length) addFiles(e.target.files)
                      e.target.value = ''
                    }}
                  />
                </div>

                {selectedFiles.length > 0 && (
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                    {selectedFiles.map((entry, i) => (
                      <div key={entry.id} className="relative aspect-square rounded-xl overflow-hidden bg-stone-100 group">
                        {/* blob URL 稳定不变，原生 img 急加载，杜绝重载竞态导致的预览空白 */}
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={entry.previewUrl}
                          alt={entry.file.name}
                          loading="eager"
                          decoding="async"
                          className="absolute inset-0 h-full w-full object-cover"
                        />
                        <button
                          type="button"
                          onClick={() => removeFile(i)}
                          className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                          aria-label="移除"
                        >
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <motion.button
                  type="button"
                  onClick={handleStartRecognize}
                  disabled={selectedFiles.length === 0}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 text-white font-medium shadow-lg shadow-rose-200/50 hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  ✨ 开始识别（{selectedFiles.length} 件）
                </motion.button>
              </div>
            )}

            {/* ===== review / wuxing 步 ===== */}
            {(step === 'review' || step === 'wuxing') && (
              <div className="space-y-4">
                {isRecognizing && (
                  <div className="flex items-center justify-center gap-2 py-3 text-sm text-[var(--brand-subtle)]">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    AI 正在识别衣物，请稍候...
                  </div>
                )}

                {step === 'wuxing' && wuxingLoading && (
                  <div className="flex items-center justify-center gap-2 py-3 text-sm text-[var(--brand-subtle)]">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    五行深度分析中...
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {cards.map(renderCard)}
                </div>

                {cards.length === 0 && !isRecognizing && (
                  <div className="text-center py-8">
                    <p className="text-sm text-[var(--brand-subtle)]">没有待处理的衣物</p>
                    <button
                      type="button"
                      onClick={() => setStep('select')}
                      className="mt-3 text-sm text-rose-500 font-medium hover:text-rose-600"
                    >
                      继续上传
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 底部操作区 */}
          {(step === 'review' || step === 'wuxing') && cards.length > 0 && !isRecognizing && (
            <div className="px-6 py-4 border-t border-stone-100 flex gap-3 flex-shrink-0">
              {step === 'review' ? (
                <>
                  <button
                    type="button"
                    onClick={() => { cards.forEach(c => URL.revokeObjectURL(c.previewUrl)); setCards([]); setStep('select') }}
                    className="flex-1 py-3 rounded-xl border border-stone-200 text-sm font-medium text-[var(--brand-body)] hover:bg-stone-50 transition-colors"
                  >
                    重新选择
                  </button>
                  <motion.button
                    type="button"
                    onClick={handleConfirmBasic}
                    whileTap={{ scale: 0.99 }}
                    className="flex-[2] py-3 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-sm font-medium shadow-lg shadow-blue-200/50 hover:shadow-xl transition-all"
                  >
                    确认信息，五行深度分析 →
                  </motion.button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setStep('review')}
                    disabled={isSubmitting || wuxingLoading}
                    className="flex-1 py-3 rounded-xl border border-stone-200 text-sm font-medium text-[var(--brand-body)] hover:bg-stone-50 transition-colors disabled:opacity-50"
                  >
                    ← 返回基础信息
                  </button>
                  <motion.button
                    type="button"
                    onClick={handleSave}
                    disabled={isSubmitting || wuxingLoading}
                    whileTap={{ scale: 0.99 }}
                    className="flex-[2] py-3 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 text-white text-sm font-medium shadow-lg shadow-rose-200/50 hover:shadow-xl disabled:opacity-50 transition-all"
                  >
                    {isSubmitting ? '入库中...' : `入库 ${cards.length} 件`}
                  </motion.button>
                </>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
    </ModalPortal>
  )
}

export default BatchUploadModal
