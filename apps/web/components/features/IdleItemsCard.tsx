'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Heart, ChevronDown, ChevronUp, Leaf } from 'lucide-react'
import {
  declutterWardrobeItem,
  getIdleItems,
  type IdleItem,
  type IdleItemsResponse,
} from '@/lib/api'
import { ConfirmDialog, toast } from '@/components/ui'
import { DECLUTTER_OPTIONS, notifyWardrobeActiveChanged, type DeclutterOption } from '@/lib/wardrobe-display'

/** 五行元素颜色 */
const ELEM_COLORS: Record<string, string> = {
  '金': '#9CAFB8', '木': '#3DA35D', '水': '#4A90C4', '火': '#C75B5B', '土': '#B89B5E',
}

/** 待确认的处理动作 */
interface PendingDeclutter {
  item: IdleItem
  option: DeclutterOption
}

export function IdleItemsCard() {
  const [data, setData] = useState<IdleItemsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [pending, setPending] = useState<PendingDeclutter | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getIdleItems().then(result => {
      if (!cancelled) {
        setData(result)
        setLoading(false)
      }
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  /** 二次确认后写入三态：衣物移出活跃衣橱，同时从本卡列表移除 */
  const confirmDeclutter = async () => {
    if (!pending) return
    const { item, option } = pending
    setSubmitting(true)
    try {
      await declutterWardrobeItem(item.id, option.action)
      setData(prev => (prev ? {
        ...prev,
        idle_items: prev.idle_items.filter(x => x.id !== item.id),
        total_count: Math.max(0, prev.total_count - 1),
      } : prev))
      notifyWardrobeActiveChanged()
      toast.success(`「${item.name}」已标记${option.doneLabel}，可在断舍离战报里撤销`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '处理失败，请稍后重试')
    } finally {
      setSubmitting(false)
      setPending(null)
    }
  }

  // 没有闲置物品或加载中或已关闭
  if (loading || dismissed || !data || data.total_count === 0) return null

  const visibleItems = expanded ? data.idle_items : data.idle_items.slice(0, 3)
  const hasMore = data.idle_items.length > 3

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="bg-white rounded-2xl shadow-sm border border-[var(--brand-border)]/40 mb-4 overflow-hidden"
    >
      {/* 头部 */}
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[#3DA35D]/20 to-[#4A90C4]/20 flex items-center justify-center">
            <Leaf className="w-3.5 h-3.5 text-[#3DA35D]" />
          </div>
          <span className="text-sm font-semibold text-[var(--brand-heading)]">闲置提醒</span>
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-[#3DA35D]/10 text-[#3DA35D] font-medium">
            {data.total_count} 件
          </span>
        </div>
        <p className="text-xs text-[var(--brand-subtle)] mt-1.5 leading-relaxed">{data.message}</p>
      </div>

      {/* 物品列表 */}
      <div className="px-4 pb-3">
        <AnimatePresence initial={false}>
          {visibleItems.map((item, idx) => (
            <IdleItemRow
              key={item.id}
              item={item}
              index={idx}
              onRequestDeclutter={option => setPending({ item, option })}
            />
          ))}
        </AnimatePresence>

        {/* 展开/收起 */}
        {hasMore && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-center gap-1 py-2 text-xs text-[var(--brand-subtle)] hover:text-[var(--brand-heading)] transition-colors"
          >
            {expanded ? (
              <>收起 <ChevronUp className="w-3.5 h-3.5" /></>
            ) : (
              <>查看全部 {data.total_count} 件 <ChevronDown className="w-3.5 h-3.5" /></>
            )}
          </button>
        )}

        {/* 关闭按钮 */}
        <button
          onClick={() => setDismissed(true)}
          className="w-full text-[10px] text-[var(--brand-subtle)]/60 hover:text-[var(--brand-subtle)] py-1 transition-colors"
        >
          暂时忽略
        </button>
      </div>

      <ConfirmDialog
        isOpen={!!pending}
        onClose={() => (submitting ? undefined : setPending(null))}
        onConfirm={confirmDeclutter}
        title={pending ? `把「${pending.item.name}」${pending.option.title}？` : ''}
        description="处理后会从每日成套、搭配盲盒与推荐里移出，历史穿搭日记不受影响。随时可以在断舍离战报里撤销。"
        confirmText={pending ? pending.option.confirmText : '确认'}
        danger={pending?.option.action === 'discard'}
      />
    </motion.div>
  )
}

function IdleItemRow({
  item,
  index,
  onRequestDeclutter,
}: {
  item: IdleItem
  index: number
  onRequestDeclutter: (option: DeclutterOption) => void
}) {
  const [showSuggestion, setShowSuggestion] = useState(false)
  const elemColor = ELEM_COLORS[item.primary_element || ''] || '#999'

  /** 闲置程度徽标：超一年偏红，其余暖金 */
  const idleBadge = item.days_since_worn ? (
    <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
      item.days_since_worn > 365
        ? 'bg-[#C75B5B]/10 text-[#C75B5B]'
        : 'bg-[#B89B5E]/10 text-[#B89B5E]'
    }`}>
      {item.days_since_worn} 天前
    </span>
  ) : item.days_owned ? (
    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#B89B5E]/10 text-[#B89B5E]">
      拥有 {item.days_owned} 天
    </span>
  ) : null

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ delay: index * 0.05 }}
      className="border-b border-[var(--brand-border)]/20 last:border-b-0"
    >
      <div
        className="flex items-center gap-3 py-2.5 cursor-pointer"
        onClick={() => setShowSuggestion(!showSuggestion)}
      >
        {/* 图片 */}
        {item.image_url ? (
          <img
            src={item.image_url}
            alt={item.name}
            className="w-11 h-11 rounded-lg object-cover border border-[var(--brand-border)]/30 flex-shrink-0"
          />
        ) : (
          <div
            className="w-11 h-11 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: elemColor + '15' }}
          >
            <span className="text-sm font-medium" style={{ color: elemColor }}>
              {item.primary_element || '📦'}
            </span>
          </div>
        )}

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[var(--brand-heading)] truncate">{item.name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-[var(--brand-subtle)]">
              {item.category}
            </span>
            <span className="text-[10px] text-[var(--brand-subtle)]">
              穿着 {item.wear_count} 次
            </span>
          </div>
        </div>

        {/* 天数标签 + 断舍离三态小键 */}
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          {idleBadge}
          <div className="flex items-center gap-1">
            {DECLUTTER_OPTIONS.map(option => (
              <button
                key={option.action}
                type="button"
                title={option.title}
                aria-label={`${option.title}：${item.name}`}
                onClick={(e) => { e.stopPropagation(); onRequestDeclutter(option) }}
                className="flex h-6 w-6 items-center justify-center rounded-md border text-[11px] leading-none transition-opacity hover:opacity-75 touch-feedback"
                style={{
                  borderColor: `${option.color}55`,
                  backgroundColor: `${option.color}0D`,
                  color: option.color,
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <Heart
          className={`w-3.5 h-3.5 flex-shrink-0 transition-colors ${
            showSuggestion ? 'text-[#3DA35D]' : 'text-[var(--brand-subtle)]/40'
          }`}
        />
      </div>

      {/* 公益建议文案 */}
      <AnimatePresence>
        {showSuggestion && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-[#3DA35D]/5 rounded-lg p-2.5 mb-2">
              <p className="text-xs text-[#3DA35D] leading-relaxed">{item.donation_suggestion}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
