'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useWardrobeStore } from '@/store/wardrobe'
import { useUserStore } from '@/store/user'
import type { WardrobeItem, AITaggingResult } from '@/lib/api'
import { initAuthToken } from '@/lib/api'
import { WUXING_ELEMENTS, WUXING_CONFIG, getWuxingConfig } from '@/lib/wuxing-config'

const CATEGORIES = ['上装', '下装', '外套', '鞋履', '配饰', '裙装', '套装', '其他'] as const
const SEASONS = ['春', '夏', '秋', '冬'] as const
const WEATHER_TYPES = ['晴', '多云', '阴', '雨', '雪'] as const
const THICKNESS_LEVELS = ['轻薄', '适中', '加厚', '厚重'] as const
const SHAPES = ['长方', '正方', '圆形', '三角', '不规则'] as const

interface AddWardrobeModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  editItem?: WardrobeItem | null
}

// 可编辑的 AI 分析结果
interface EditableAnalysis extends AITaggingResult {
  isEditing?: boolean
  category?: string  // 分类也由 AI 生成
}

export function AddWardrobeModal({ isOpen, onClose, onSuccess, editItem }: AddWardrobeModalProps) {
  const { addItem, updateItem, taggingPreview, isTaggingLoading, fetchTaggingPreview, clearTaggingPreview } = useWardrobeStore()
  const { isAuthenticated } = useUserStore()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // 基础信息（简化：name 由 description 自动填充）
  const [description, setDescription] = useState('')  // 衣物描述，同时也作为名称
  const [imageUrl, setImageUrl] = useState('')
  const [localImage, setLocalImage] = useState<string | null>(null)
  
  // AI 分析结果（可编辑）
  const [analysis, setAnalysis] = useState<EditableAnalysis | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'input' | 'review'>('input')

  // 初始化 token
  useEffect(() => {
    initAuthToken()
  }, [])

  // 编辑模式下初始化表单
  useEffect(() => {
    if (editItem) {
      setDescription(editItem.name || '')  // 编辑模式下，name 作为 description
      setImageUrl(editItem.image_url || '')
      setLocalImage(null)
      // 从 editItem 构建 analysis（支持新字段）
      const attrs = editItem.attributes_detail || {}
      setAnalysis({
        primary_element: editItem.primary_element,
        secondary_element: editItem.secondary_element,
        color: attrs.颜色?.名称 || attrs.color || '',
        color_element: attrs.颜色?.主五行,
        material: attrs.面料?.名称 || attrs.material,
        material_element: attrs.面料?.主五行,
        style: attrs.款式?.风格 || attrs.style,
        shape: attrs.款式?.形状,
        details: attrs.款式?.细节 || [],
        energy_intensity: editItem.energy_intensity || attrs.颜色?.能量强度,
        season: attrs.season || [],
        tags: attrs.tags || [],
        confidence: 1,
        applicable_weather: editItem.applicable_weather || attrs.applicable_weather || [],
        applicable_seasons: editItem.applicable_seasons || attrs.applicable_seasons || [],
        temperature_range: editItem.temperature_range || attrs.temperature_range,
        functionality: editItem.functionality || attrs.functionality || [],
        thickness_level: editItem.thickness_level || attrs.thickness_level,
        suggested_name: editItem.name,
        category: editItem.category,  // 新增：分类也由 AI 生成
      })
      setStep('review')
    } else {
      resetForm()
    }
  }, [editItem, isOpen])

  // 当 AI 分析完成时，自动填充所有字段
  useEffect(() => {
    if (taggingPreview) {
      setAnalysis(taggingPreview)
      // AI 生成的 suggested_name 作为默认名称显示在描述框
      if (taggingPreview.suggested_name && !description) {
        setDescription(taggingPreview.suggested_name)
      }
    }
  }, [taggingPreview])

  const resetForm = () => {
    setDescription('')
    setImageUrl('')
    setLocalImage(null)
    setAnalysis(null)
    clearTaggingPreview()
    setError('')
    setStep('input')
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  // 处理图片上传
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setError('请上传图片文件')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('图片大小不能超过 5MB')
      return
    }

    const reader = new FileReader()
    reader.onload = (event) => {
      const base64 = event.target?.result as string
      setLocalImage(base64)
      setImageUrl('')
      setError('')
      setStep('input')
      setAnalysis(null)
      clearTaggingPreview()
    }
    reader.readAsDataURL(file)
  }

  // AI 分析
  const handleAutoAnalyze = useCallback(async () => {
    // 使用 description 作为衣物描述
    const descriptionText = description.trim()
    if (!descriptionText && !localImage && !imageUrl) {
      setError('请上传图片或输入衣物描述')
      return
    }
    setError('')
    await fetchTaggingPreview(descriptionText || '请根据图片分析这件衣物')
  }, [description, localImage, imageUrl, fetchTaggingPreview])

  // 进入确认步骤
  const handleReview = () => {
    if (!analysis) {
      setError('请先进行 AI 分析')
      return
    }
    setStep('review')
  }

  // 返回修改
  const handleBackToInput = () => {
    setStep('input')
  }

  // 更新 analysis 字段
  const updateAnalysisField = <K extends keyof EditableAnalysis>(
    field: K,
    value: EditableAnalysis[K]
  ) => {
    setAnalysis(prev => prev ? { ...prev, [field]: value } : null)
  }

  // 切换数组字段（如季节、天气）
  const toggleArrayField = (field: 'season' | 'applicable_seasons' | 'applicable_weather', value: string) => {
    setAnalysis(prev => {
      if (!prev) return null
      const current = prev[field] || []
      const updated = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value]
      return { ...prev, [field]: updated }
    })
  }

  // 提交表单
  const handleSubmit = async () => {
    if (!isAuthenticated) {
      setError('请先登录后再添加衣物')
      return
    }

    if (!analysis) {
      setError('请先进行 AI 分析')
      return
    }

    // description 作为名称
    const finalName = description.trim() || analysis.suggested_name || '未命名衣物'
    
    setIsSubmitting(true)
    setError('')

    try {
      const finalImageUrl = localImage || imageUrl || undefined
      
      const data: any = {
        name: finalName,
        category: analysis.category || undefined,  // 分类由 AI 生成
        image_url: finalImageUrl,
        primary_element: analysis.primary_element,
        secondary_element: analysis.secondary_element || undefined,
        description: description || finalName,
        // 天气/场景字段
        applicable_weather: analysis.applicable_weather,
        applicable_seasons: analysis.applicable_seasons,
        temperature_range: analysis.temperature_range,
        functionality: analysis.functionality,
        thickness_level: analysis.thickness_level,
        energy_intensity: analysis.energy_intensity,
        // attributes_detail 与后端新结构对齐
        attributes_detail: {
          颜色: {
            名称: analysis.color,
            主五行: analysis.color_element,
            能量强度: analysis.energy_intensity,
          },
          面料: {
            名称: analysis.material,
            主五行: analysis.material_element,
          },
          款式: {
            形状: analysis.shape,
            细节: analysis.details || [],
            风格: analysis.style,
          },
          season: analysis.season,
          tags: analysis.tags,
        },
      }

      if (editItem) {
        await updateItem(editItem.id, data)
      } else {
        await addItem(data)
      }
      
      resetForm()
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const displayImage = localImage || imageUrl

  // 渲染输入步骤
  const renderInputStep = () => (
    <div className="space-y-5">
      {/* 衣物描述输入 */}
      <div className="p-4 bg-gradient-to-br from-rose-50 to-pink-50 rounded-2xl border border-rose-100">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-6 h-6 rounded-full bg-rose-500 text-white text-sm flex items-center justify-center">1</span>
          <span className="font-medium text-stone-700">输入衣物描述</span>
        </div>
        
        <textarea
          value={description}
          onChange={(e) => { setDescription(e.target.value); setAnalysis(null); clearTaggingPreview(); }}
          placeholder="例如：红色真丝衬衫，V领设计，适合正式场合..."
          rows={3}
          className="w-full px-4 py-3 rounded-xl border border-rose-200 focus:border-rose-400 focus:ring-2 focus:ring-rose-100 transition-all outline-none resize-none text-sm"
        />
        
        {/* 图片上传（可选） */}
        <div className="mt-3 flex items-center gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-rose-200 bg-white text-rose-600 text-sm hover:bg-rose-50 transition-all"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            上传图片（可选）
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
          />
          
          {displayImage && (
            <div className="relative w-16 h-16 rounded-xl overflow-hidden bg-stone-100">
              <img src={displayImage} alt="预览" className="w-full h-full object-cover" />
              <button
                type="button"
                onClick={() => { setLocalImage(null); setImageUrl(''); setAnalysis(null); clearTaggingPreview(); }}
                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600"
              >
                ×
              </button>
            </div>
          )}
        </div>
      </div>

      {/* AI 分析按钮 */}
      <div className="p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-2xl border border-blue-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-blue-500 text-white text-sm flex items-center justify-center">2</span>
            <div>
              <span className="font-medium text-stone-700 block">AI 智能分析</span>
              <span className="text-xs text-stone-500">自动识别五行、颜色、材质、款式等</span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleAutoAnalyze}
            disabled={isTaggingLoading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-sm font-medium hover:shadow-lg disabled:opacity-50 transition-all flex items-center gap-2"
          >
            {isTaggingLoading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                分析中...
              </>
            ) : (
              <>
                <span>✨</span>
                <span>开始分析</span>
              </>
            )}
          </button>
        </div>
        
        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 bg-white rounded-xl p-4 border border-blue-100"
          >
            <div className="flex items-center gap-4 mb-3">
              <div className="flex-1">
                <div className="text-xs text-stone-500 mb-1">主五行</div>
                {(() => {
                  const config = getWuxingConfig(analysis.primary_element)
                  return (
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${config.bgClass} ${config.textClass} font-medium`}>
                      <span className="text-lg">{config.emoji}</span>
                      <span>{analysis.primary_element}</span>
                    </span>
                  )
                })()}
              </div>
              {analysis.secondary_element && (
                <div className="flex-1">
                  <div className="text-xs text-stone-500 mb-1">次五行</div>
                  <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-stone-100 text-stone-700 font-medium">
                    {getWuxingConfig(analysis.secondary_element).emoji} {analysis.secondary_element}
                  </span>
                </div>
              )}
              <div className="text-right">
                <div className="text-xs text-stone-500 mb-1">置信度</div>
                <span className="text-lg font-bold text-blue-600">{(analysis.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
            <p className="text-sm text-stone-500">✅ 分析完成，点击下方按钮查看详情并修改</p>
          </motion.div>
        )}
      </div>

      {/* 下一步按钮 */}
      <motion.button
        type="button"
        onClick={handleReview}
        disabled={!analysis}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className="w-full py-3.5 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium shadow-lg shadow-blue-200/50 hover:shadow-xl hover:shadow-blue-300/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      >
        查看分析结果 →
      </motion.button>
    </div>
  )

  // 渲染确认步骤（可编辑）
  const renderReviewStep = () => {
    if (!analysis) return null

    return (
      <div className="space-y-5">
        {/* 返回按钮 */}
        <button
          type="button"
          onClick={handleBackToInput}
          className="flex items-center gap-1 text-sm text-stone-500 hover:text-stone-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          返回修改描述
        </button>

        {/* 图片预览 */}
        {displayImage && (
          <div className="relative h-40 rounded-2xl overflow-hidden">
            <img src={displayImage} alt="预览" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
            <div className="absolute bottom-3 left-3 right-3">
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="衣物名称/描述"
                className="w-full px-3 py-2 rounded-lg bg-white/90 backdrop-blur-sm border-0 text-stone-800 placeholder:text-stone-400 text-sm"
              />
            </div>
          </div>
        )}

        {/* 五行属性（可编辑） */}
        <div className="p-4 bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl border border-amber-100">
          <h3 className="font-medium text-stone-700 mb-3 flex items-center gap-2">
            <span>🔮</span> 五行属性
          </h3>
          
          {/* 主五行 */}
          <div className="mb-4">
            <label className="text-xs text-stone-500 mb-2 block">主五行</label>
            <div className="flex gap-2">
              {WUXING_ELEMENTS.map((element) => {
                const config = WUXING_CONFIG[element]
                const isSelected = analysis.primary_element === element
                return (
                  <button
                    key={element}
                    type="button"
                    onClick={() => updateAnalysisField('primary_element', element)}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                      isSelected
                        ? `${config.bgClass} ${config.textClass} ring-2 ring-offset-1`
                        : 'bg-white text-stone-600 hover:bg-stone-50'
                    }`}
                    style={isSelected ? { '--tw-ring-color': config.gradientFrom } as React.CSSProperties : {}}
                  >
                    {config.emoji} {element}
                  </button>
                )
              })}
            </div>
          </div>

          {/* 次五行 */}
          <div className="mb-4">
            <label className="text-xs text-stone-500 mb-2 block">次五行（可选）</label>
            <div className="flex gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => updateAnalysisField('secondary_element', undefined)}
                className={`px-3 py-2 rounded-xl text-sm transition-all ${
                  !analysis.secondary_element
                    ? 'bg-stone-800 text-white'
                    : 'bg-white text-stone-600 hover:bg-stone-50'
                }`}
              >
                无
              </button>
              {WUXING_ELEMENTS.filter(e => e !== analysis.primary_element).map((element) => {
                const config = WUXING_CONFIG[element]
                const isSelected = analysis.secondary_element === element
                return (
                  <button
                    key={element}
                    type="button"
                    onClick={() => updateAnalysisField('secondary_element', element)}
                    className={`px-3 py-2 rounded-xl text-sm transition-all ${
                      isSelected
                        ? `${config.bgClass} ${config.textClass}`
                        : 'bg-white text-stone-600 hover:bg-stone-50'
                    }`}
                  >
                    {config.emoji} {element}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* 基本信息（可编辑） */}
        <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-2xl border border-emerald-100">
          <h3 className="font-medium text-stone-700 mb-3 flex items-center gap-2">
            <span>📋</span> 基本信息
          </h3>
          
          <div className="grid grid-cols-2 gap-3">
            {/* 颜色 */}
            <div>
              <label className="text-xs text-stone-500 mb-1 block">颜色</label>
              <input
                type="text"
                value={analysis.color || ''}
                onChange={(e) => updateAnalysisField('color', e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-emerald-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all outline-none text-sm"
              />
            </div>
            
            {/* 颜色五行 */}
            <div>
              <label className="text-xs text-stone-500 mb-1 block">颜色五行</label>
              <select
                value={analysis.color_element || ''}
                onChange={(e) => updateAnalysisField('color_element', e.target.value || undefined)}
                className="w-full px-3 py-2 rounded-xl border border-emerald-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all outline-none bg-white text-sm"
              >
                <option value="">选择五行</option>
                {WUXING_ELEMENTS.map((element) => {
                  const config = WUXING_CONFIG[element]
                  return (
                    <option key={element} value={element}>
                      {config.emoji} {element}
                    </option>
                  )
                })}
              </select>
            </div>
            
            {/* 材质 */}
            <div>
              <label className="text-xs text-stone-500 mb-1 block">材质</label>
              <input
                type="text"
                value={analysis.material || ''}
                onChange={(e) => updateAnalysisField('material', e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-emerald-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all outline-none text-sm"
              />
            </div>
            
            {/* 材质五行 */}
            <div>
              <label className="text-xs text-stone-500 mb-1 block">材质五行</label>
              <select
                value={analysis.material_element || ''}
                onChange={(e) => updateAnalysisField('material_element', e.target.value || undefined)}
                className="w-full px-3 py-2 rounded-xl border border-emerald-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all outline-none bg-white text-sm"
              >
                <option value="">选择五行</option>
                {WUXING_ELEMENTS.map((element) => {
                  const config = WUXING_CONFIG[element]
                  return (
                    <option key={element} value={element}>
                      {config.emoji} {element}
                    </option>
                  )
                })}
              </select>
            </div>
            
            {/* 风格 */}
            <div>
              <label className="text-xs text-stone-500 mb-1 block">风格</label>
              <input
                type="text"
                value={analysis.style || ''}
                onChange={(e) => updateAnalysisField('style', e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-emerald-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all outline-none text-sm"
              />
            </div>
            
            {/* 分类 */}
            <div>
              <label className="text-xs text-stone-500 mb-1 block">分类</label>
              <select
                value={analysis.category || ''}
                onChange={(e) => updateAnalysisField('category', e.target.value || undefined)}
                className="w-full px-3 py-2 rounded-xl border border-emerald-200 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all outline-none bg-white text-sm"
              >
                <option value="">选择分类</option>
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 款式与能量（新增） */}
        <div className="p-4 bg-gradient-to-br from-indigo-50 to-violet-50 rounded-2xl border border-indigo-100">
          <h3 className="font-medium text-stone-700 mb-3 flex items-center gap-2">
            <span>✨</span> 款式与能量
          </h3>
          
          <div className="grid grid-cols-2 gap-3">
            {/* 款式形状 */}
            <div>
              <label className="text-xs text-stone-500 mb-2 block">款式形状</label>
              <div className="flex gap-2 flex-wrap">
                {SHAPES.map((shape) => (
                  <button
                    key={shape}
                    type="button"
                    onClick={() => updateAnalysisField('shape', analysis.shape === shape ? undefined : shape)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      analysis.shape === shape
                        ? 'bg-indigo-500 text-white'
                        : 'bg-white text-stone-600 hover:bg-indigo-50'
                    }`}
                  >
                    {shape}
                  </button>
                ))}
              </div>
            </div>
            
            {/* 能量强度 */}
            <div>
              <label className="text-xs text-stone-500 mb-2 block">能量强度</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={analysis.energy_intensity || 0.5}
                  onChange={(e) => updateAnalysisField('energy_intensity', parseFloat(e.target.value))}
                  className="flex-1 h-2 bg-indigo-200 rounded-lg appearance-none cursor-pointer"
                />
                <span className="text-sm font-medium text-indigo-600 w-12">
                  {((analysis.energy_intensity || 0.5) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
          
          {/* 款式细节 */}
          <div className="mt-3">
            <label className="text-xs text-stone-500 mb-2 block">款式细节</label>
            <div className="flex flex-wrap gap-2">
              {analysis.details?.map((detail, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white text-stone-600 text-sm border border-indigo-200"
                >
                  {detail}
                  <button
                    type="button"
                    onClick={() => updateAnalysisField('details', analysis.details?.filter((_, i) => i !== index))}
                    className="text-stone-400 hover:text-red-500"
                  >
                    ×
                  </button>
                </span>
              ))}
              <input
                type="text"
                placeholder="+ 添加细节"
                className="px-3 py-1.5 rounded-lg bg-white border border-indigo-200 text-sm w-24 focus:w-32 transition-all outline-none focus:border-indigo-400"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const value = e.currentTarget.value.trim()
                    if (value && !analysis.details?.includes(value)) {
                      updateAnalysisField('details', [...(analysis.details || []), value])
                      e.currentTarget.value = ''
                    }
                  }
                }}
              />
            </div>
          </div>
        </div>

        {/* 适用场景（可编辑） */}
        <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl border border-purple-100">
          <h3 className="font-medium text-stone-700 mb-3 flex items-center gap-2">
            <span>🌤</span> 适用场景
          </h3>
          
          {/* 适用季节 */}
          <div className="mb-4">
            <label className="text-xs text-stone-500 mb-2 block">适用季节</label>
            <div className="flex gap-2">
              {SEASONS.map((season) => (
                <button
                  key={season}
                  type="button"
                  onClick={() => toggleArrayField('applicable_seasons', season)}
                  className={`flex-1 py-2 rounded-xl text-sm transition-all ${
                    analysis.applicable_seasons?.includes(season)
                      ? 'bg-purple-500 text-white'
                      : 'bg-white text-stone-600 hover:bg-purple-50'
                  }`}
                >
                  {season}
                </button>
              ))}
            </div>
          </div>
          
          {/* 适用天气 */}
          <div className="mb-4">
            <label className="text-xs text-stone-500 mb-2 block">适用天气</label>
            <div className="flex gap-2 flex-wrap">
              {WEATHER_TYPES.map((weather) => (
                <button
                  key={weather}
                  type="button"
                  onClick={() => toggleArrayField('applicable_weather', weather)}
                  className={`px-3 py-2 rounded-xl text-sm transition-all ${
                    analysis.applicable_weather?.includes(weather)
                      ? 'bg-pink-500 text-white'
                      : 'bg-white text-stone-600 hover:bg-pink-50'
                  }`}
                >
                  {weather}
                </button>
              ))}
            </div>
          </div>
          
          {/* 厚度 */}
          <div>
            <label className="text-xs text-stone-500 mb-2 block">厚度等级</label>
            <div className="flex gap-2">
              {THICKNESS_LEVELS.map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => updateAnalysisField('thickness_level', level)}
                  className={`flex-1 py-2 rounded-xl text-sm transition-all ${
                    analysis.thickness_level === level
                      ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
                      : 'bg-white text-stone-600 hover:bg-purple-50'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 标签 */}
        <div className="p-4 bg-gradient-to-br from-stone-50 to-gray-50 rounded-2xl border border-stone-200">
          <h3 className="font-medium text-stone-700 mb-3 flex items-center gap-2">
            <span>🏷️</span> 标签
          </h3>
          <div className="flex flex-wrap gap-2">
            {analysis.tags?.map((tag, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white text-stone-600 text-sm border border-stone-200"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => updateAnalysisField('tags', analysis.tags?.filter((_, i) => i !== index))}
                  className="text-stone-400 hover:text-red-500"
                >
                  ×
                </button>
              </span>
            ))}
            <input
              type="text"
              placeholder="+ 添加标签"
              className="px-3 py-1.5 rounded-lg bg-white border border-stone-200 text-sm w-24 focus:w-32 transition-all outline-none focus:border-stone-400"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const value = e.currentTarget.value.trim()
                  if (value && !analysis.tags?.includes(value)) {
                    updateAnalysisField('tags', [...(analysis.tags || []), value])
                    e.currentTarget.value = ''
                  }
                }
              }}
            />
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 pt-2">
          <motion.button
            type="button"
            onClick={handleClose}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className="flex-1 py-3.5 rounded-xl bg-stone-100 text-stone-700 font-medium hover:bg-stone-200 transition-all"
          >
            取消
          </motion.button>
          <motion.button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || !isAuthenticated}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className="flex-1 py-3.5 rounded-xl bg-gradient-to-r from-rose-500 to-pink-500 text-white font-medium shadow-lg shadow-rose-200/50 hover:shadow-xl hover:shadow-rose-300/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                添加中...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <span>✨</span>
                <span>确认添加</span>
              </span>
            )}
          </motion.button>
        </div>
      </div>
    )
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div 
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
            >
              {/* 标题栏 */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-stone-100">
                <div>
                  <h2 className="text-lg font-bold text-stone-700">
                    {editItem ? '编辑衣物' : step === 'input' ? '添加衣物' : '确认分析结果'}
                  </h2>
                  <p className="text-xs text-stone-500 mt-0.5">
                    {step === 'input' ? 'AI 自动分析五行属性' : '检查并修改 AI 分析结果'}
                  </p>
                </div>
                <button
                  onClick={handleClose}
                  className="p-2 rounded-full hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {!isAuthenticated && (
                <div className="mx-6 mt-4 p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700">
                  ⚠️ 请先登录后再添加衣物
                </div>
              )}

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600"
                >
                  {error}
                </motion.div>
              )}

              <div className="flex-1 overflow-y-auto p-6">
                {step === 'input' ? renderInputStep() : renderReviewStep()}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
