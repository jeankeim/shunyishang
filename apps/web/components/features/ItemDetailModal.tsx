'use client'

import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { createPortal } from 'react-dom'
import { RecommendItem } from '@/types'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { getImageUrl } from '@/lib/image'

interface ItemDetailModalProps {
  item: RecommendItem
  onClose: () => void
}

/**
 * 物品详情弹窗组件
 * 展示推荐物品的高清图片、基本信息、五行属性、适用场景等详细信息
 */
export function ItemDetailModal({ item, onClose }: ItemDetailModalProps) {
  const config = getWuxingConfig(item.primary_element)
  const fullImageUrl = getImageUrl(item.image_url)
  const attrs = item.attributes_detail || {}

  // ESC 键关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [onClose])

  // 从 attributes_detail 提取颜色信息
  const colorInfo = attrs['颜色'] || attrs['color']
  const colorName = colorInfo?.['名称'] || item.color || ''
  const colorHex = colorInfo?.['色值'] || ''

  // 从 attributes_detail 提取面料信息
  const fabricInfo = attrs['面料'] || attrs['fabric']
  const fabricName = fabricInfo?.['名称'] || ''
  const fabricTouch = fabricInfo?.['触感'] || ''
  const fabricWeight = fabricInfo?.['克重'] || ''

  // 从 attributes_detail 提取款式信息
  const styleInfo = attrs['款式'] || attrs['style']
  const styleShape = styleInfo?.['形状'] || ''
  const styleDetails = styleInfo?.['细节'] || []

  // 温度范围
  const tempRange = item.temperature_range
  const tempText = tempRange
    ? `${tempRange['最低'] ?? tempRange['min']}°C ~ ${tempRange['最高'] ?? tempRange['max']}°C`
    : ''

  // 功能特性
  const functionalities = item.functionality
    ? Object.entries(item.functionality)
        .filter(([, v]) => v)
        .map(([k]) => k)
    : []

  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-end md:items-center justify-center"
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-label="物品详情"
      >
        <motion.div
          initial={{ y: '100%', opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          className="relative bg-white w-full md:max-w-lg md:rounded-2xl rounded-t-2xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 关闭按钮 */}
          <button
            onClick={onClose}
            className="sticky top-3 right-3 float-right z-10 w-9 h-9 bg-black/40 hover:bg-black/60 rounded-full flex items-center justify-center transition-colors mr-3"
            aria-label="关闭详情"
          >
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {/* 物品图片 */}
          {fullImageUrl ? (
            <div className="w-full h-64 md:h-72 bg-stone-100 relative overflow-hidden">
              <img
                src={fullImageUrl}
                alt={item.name}
                className="w-full h-full object-cover"
              />
              {/* 来源标签 */}
              <div className={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-medium ${
                item.source === 'wardrobe'
                  ? 'bg-emerald-500/90 text-white'
                  : 'bg-blue-500/90 text-white'
              }`}>
                {item.source === 'wardrobe' ? '🏠 自有衣橱' : '📚 公共库'}
              </div>
            </div>
          ) : (
            <div className={`w-full h-48 bg-gradient-to-br ${config.gradientClass} flex items-center justify-center`}>
              <span className="text-6xl opacity-60">{config.emoji}</span>
            </div>
          )}

          {/* 内容区 */}
          <div className="p-5 md:p-6">
            {/* 标题 + 五行标签 */}
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <h2 className="text-lg font-bold text-stone-800 leading-snug">{item.name}</h2>
                <p className="text-sm text-stone-500 mt-1">{item.category}</p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-bold shrink-0 ${config.bgClass} ${config.textClass}`}
              >
                {item.primary_element}
              </span>
            </div>

            {/* 综合匹配度 */}
            <div className="flex items-center gap-2 mb-5 pb-4 border-b border-stone-100">
              <span className="text-sm text-stone-500">综合匹配度</span>
              <span className="text-xl font-bold" style={{ color: 'var(--wuxing-earth)' }}>
                {(item.final_score * 100).toFixed(0)}%
              </span>
              {/* 评分条 */}
              <div className="flex-1 h-2 bg-stone-100 rounded-full overflow-hidden ml-2">
                <div
                  className={`h-full rounded-full ${config.gradientClass}`}
                  style={{ width: `${item.final_score * 100}%` }}
                />
              </div>
            </div>

            {/* 基本信息网格 */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              {colorName && (
                <InfoCell label="颜色" value={colorName}>
                  {colorHex && (
                    <span
                      className="inline-block w-4 h-4 rounded-full border border-stone-200 ml-1 align-middle"
                      style={{ backgroundColor: colorHex }}
                    />
                  )}
                </InfoCell>
              )}
              {fabricName && (
                <InfoCell label="面料" value={fabricName} />
              )}
              {item.thickness_level && (
                <InfoCell label="厚度" value={item.thickness_level} />
              )}
              {item.gender && item.gender !== '中性' && (
                <InfoCell label="适用性别" value={item.gender} />
              )}
              {fabricTouch && (
                <InfoCell label="触感" value={fabricTouch} />
              )}
              {fabricWeight && (
                <InfoCell label="克重" value={fabricWeight} />
              )}
              {styleShape && (
                <InfoCell label="版型" value={styleShape} />
              )}
              {tempRange && (
                <InfoCell label="适宜温度" value={tempText} />
              )}
            </div>

            {/* 款式细节 */}
            {Array.isArray(styleDetails) && styleDetails.length > 0 && (
              <Section title="款式细节">
                <div className="flex flex-wrap gap-2">
                  {styleDetails.map((d: string, i: number) => (
                    <span key={i} className="px-3 py-1 bg-stone-100 text-stone-600 text-xs rounded-full">
                      {d}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {/* 适用场景 */}
            {(item.applicable_weather?.length || item.applicable_seasons?.length) ? (
              <Section title="适用场景">
                <div className="space-y-2">
                  {item.applicable_seasons && item.applicable_seasons.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-stone-400 w-10">季节</span>
                      <div className="flex gap-1.5">
                        {item.applicable_seasons.map((s) => (
                          <span key={s} className="px-2.5 py-0.5 bg-amber-50 text-amber-700 text-xs rounded-full">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {item.applicable_weather && item.applicable_weather.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-stone-400 w-10">天气</span>
                      <div className="flex gap-1.5">
                        {item.applicable_weather.map((w) => (
                          <span key={w} className="px-2.5 py-0.5 bg-sky-50 text-sky-700 text-xs rounded-full">
                            {w}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Section>
            ) : null}

            {/* 功能特性 */}
            {functionalities.length > 0 && (
              <Section title="功能特性">
                <div className="flex flex-wrap gap-2">
                  {functionalities.map((f) => (
                    <span key={f} className="px-2.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded-full">
                      {f}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {/* 推荐理由 */}
            {item.reason && (
              <Section title="推荐理由">
                <p className="text-sm text-stone-600 leading-relaxed">{item.reason}</p>
              </Section>
            )}
          </div>

          {/* 底部安全区（移动端） */}
          <div className="h-6 md:hidden" />
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  )
}

/* ---- 子组件 ---- */

function InfoCell({ label, value, children }: { label: string; value: string; children?: React.ReactNode }) {
  return (
    <div className="bg-stone-50 rounded-lg px-3 py-2.5">
      <div className="text-xs text-stone-400 mb-0.5">{label}</div>
      <div className="text-sm font-medium text-stone-700 flex items-center">
        {value}
        {children}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">{title}</h3>
      {children}
    </div>
  )
}
