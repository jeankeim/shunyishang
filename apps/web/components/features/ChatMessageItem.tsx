'use client'

import { useState, useEffect, useRef, useMemo, lazy, Suspense } from 'react'
import { motion } from 'framer-motion'
import { ChatMessage, RecommendItem } from '@/types'
import { RecommendCard } from './RecommendCard'
import { TravelPlanCard } from './TravelPlanCard'
const PosterGenerator = lazy(() => import('./PosterGenerator').then(m => ({ default: m.PosterGenerator })))
import { ImageLightbox } from './ImageLightbox'
import { cn } from '@/lib/utils'
import { Sparkles } from 'lucide-react'
import { useUserStore } from '@/store/user'

const ELEMENT_EMOJI: Record<string, string> = {
  '金': '⚪', '木': '🟢', '水': '🔵', '火': '🔴', '土': '🟡',
}

// 整体搭配展示顺序：按穿搭部位从主到次排列，让推荐结果更像一套完整 Outfit（用户反馈 #5）
const OUTFIT_SLOT_ORDER: Record<string, number> = {
  '上装': 0, '裙装': 1, '下装': 2, '外套': 3, '鞋履': 4, '配饰': 5, '饰品': 6, '文玩': 7,
}

interface ChatMessageItemProps {
  message: ChatMessage
  onOpenPoster?: () => void
  onClosePoster?: () => void
  onRefreshBatch?: () => void
  onNavigateToWardrobe?: () => void
  batchIndex?: number
  isLoading?: boolean
  /** 自动折叠：换一批/新输入后旧推荐结果收起为一行摘要，不再占位 */
  collapsed?: boolean
  /** 用户手动展开/收起时的回调（父组件同步记录，避免状态回弹） */
  onToggleCollapse?: (collapsed: boolean) => void
}

export function ChatMessageItem({ 
  message,
  onOpenPoster,
  onClosePoster,
  onRefreshBatch,
  onNavigateToWardrobe,
  batchIndex = 0,
  isLoading = false,
  collapsed: collapsedProp = false,
  onToggleCollapse,
}: ChatMessageItemProps) {
  const user = useUserStore(state => state.user)
  const displayName = user?.nickname || user?.phone || '用户'
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const isUser = message.role === 'user'
  const isStreaming = message.type !== 'done' && message.role === 'assistant' && message.type !== 'error'
  const isInitial = !message.content && isStreaming  // 刚开始，还没有内容
  const hasAnalysis = !!message.metadata?.targetElements  // 已有分析结果
  const hasItems = !!message.metadata?.items  // 已有推荐物品
  const [isPosterOpen, setIsPosterOpen] = useState(false)
  const messageRef = useRef<HTMLDivElement>(null)

  // 折叠态：外部（换一批/新输入）自动收起，本地允许手动展开/收起；
  // 流式消息不做折叠（用户正在看结果）
  const [collapsedState, setCollapsedState] = useState(collapsedProp)
  useEffect(() => {
    setCollapsedState(collapsedProp)
  }, [collapsedProp])
  const isCollapsed = collapsedState && !isStreaming

  // 推荐理由小字：仅对匹配度（final_score）最高的2件展示，避免多张卡片雷同重复
  const topReasonItems = useMemo(() => {
    const withReason = (message.metadata?.items || []).filter((it: RecommendItem) => it.reason)
    return new Set(
      [...withReason]
        .sort((a: RecommendItem, b: RecommendItem) => (b.final_score ?? 0) - (a.final_score ?? 0))
        .slice(0, 2)
    )
  }, [message.metadata?.items])

  // 当海报弹窗打开时，滚动到顶部
  useEffect(() => {
    if (isPosterOpen) {
      onOpenPoster?.()
    }
  }, [isPosterOpen, onOpenPoster])

  // 关闭海报时，滚动回消息位置
  const handleClosePoster = () => {
    setIsPosterOpen(false)
    // 延迟滚动，等待弹窗关闭动画
    setTimeout(() => {
      onClosePoster?.()
    }, 100)
  }

  // 根据处理阶段显示不同的提示
  const getStatusText = () => {
    if (isInitial && !hasAnalysis) return '正在分析您的八字和场景...'
    if (hasAnalysis && !hasItems) return '正在为您匹配最合适的衣物...'
    if (hasItems) return '正在生成搭配建议...'
    return '正在思考中...'
  }

  return (
    <motion.div
      ref={messageRef}
      data-message-id={message.id}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex gap-4 py-4 px-4',
        isUser ? 'bg-transparent' : 'bg-gradient-to-r from-amber-50/60 to-orange-50/40 rounded-lg border border-amber-200/30'
      )}
    >
      {/* 头像 */}
      <div className="shrink-0">
        <div
          className={cn(
            'h-8 w-8 rounded-full flex items-center justify-center text-sm font-medium',
            isUser 
              ? 'bg-gradient-to-br from-stone-300 to-stone-400 text-white' 
              : 'bg-gradient-to-br from-amber-400 to-orange-400 text-white'
          )}
        >
          {isUser ? '我' : 'AI'}
        </div>
      </div>

      {/* 移动端：整列内容左移与 AI 头像左缘对齐（正文/推荐理由/卡片一致），充分利用窄屏宽度（用户反馈）；桌面端保持原缩进 */}
      <div className={cn('flex-1 space-y-3 min-w-0', !isUser && '-ml-12 md:ml-0')}>
        <div className="font-medium">{isUser ? '' : ''}</div>

        {/* 五行标签 */}
        {message.metadata?.targetElements && (
          <div className="flex gap-2 flex-wrap">
            {message.metadata.targetElements.map((e) => (
              <span
                key={e}
                className="px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-100/80 to-orange-100/60 text-amber-700 text-xs border border-amber-200/40"
              >
                {ELEMENT_EMOJI[e]}{e}
              </span>
            ))}
          </div>
        )}

        {/* 加载动画：初始阶段显示 */}
        {isInitial && (
          <div className="flex items-center gap-3 py-2">
            <div className="flex gap-1">
              <motion.div
                className="w-2 h-2 bg-amber-500 rounded-full"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0 }}
              />
              <motion.div
                className="w-2 h-2 bg-amber-500 rounded-full"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
              />
              <motion.div
                className="w-2 h-2 bg-amber-500 rounded-full"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
              />
            </div>
            <span className="text-sm text-stone-500">{getStatusText()}</span>
          </div>
        )}

        {/* 内容（折叠态下收起正文，只保留下方摘要条） */}
        {message.type === 'hint' ? (
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/60 rounded-xl p-4 text-stone-700">
            <p className="text-sm leading-relaxed">{message.content}</p>
          </div>
        ) : !isCollapsed ? (
          <div className="text-stone-700 leading-relaxed whitespace-pre-wrap">
            {message.content}
            {isStreaming && message.content && <span className="inline-block w-0.5 h-4 bg-amber-500 ml-0.5 animate-pulse align-middle" />}
          </div>
        ) : null}

        {/* 软降级提示横幅（如衣橱→公共库） */}
        {message.metadata?.notice && (
          <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
            <span className="leading-none mt-0.5">ℹ️</span>
            <span className="leading-relaxed">{message.metadata.notice}</span>
          </div>
        )}

        {/* 多天行程规划卡片：每日衣物图片直接展示在对应天下方（用户反馈），底部不再重复聚合网格 */}
        {message.metadata?.travelPlan && (
          <TravelPlanCard data={message.metadata.travelPlan} onImageClick={(imageUrl) => setSelectedImage(imageUrl)} />
        )}

        {/* 推荐卡片：按穿搭部位排序，以整体搭配方案呈现（用户反馈 #5） */}
        {message.metadata?.items && message.metadata.items.length > 0 && isCollapsed && (
          /* 折叠摘要条：旧批次推荐自动收起，一行即可重新展开 */
          <button
            onClick={() => {
              setCollapsedState(false)
              onToggleCollapse?.(false)
            }}
            className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl border border-amber-200/50 bg-amber-50/50 hover:bg-amber-50 transition-colors text-left"
            aria-label="展开查看这条推荐结果"
          >
            <span className="flex items-center gap-2 min-w-0 text-xs text-stone-500">
              <span aria-hidden="true">🧥</span>
              <span className="truncate">
                {message.metadata.items.length} 件单品 · {Array.from(new Set(message.metadata.items.map((it: RecommendItem) => it.category))).slice(0, 3).join(' / ')}
              </span>
            </span>
            <span className="shrink-0 text-[11px] text-stone-400 flex items-center gap-0.5">
              展开
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>
        )}

        {message.metadata?.items && message.metadata.items.length > 0 && !isCollapsed && (
          <>
            {/* 行程规划场景下每日图片已在 TravelPlanCard 内按天展示，底部不再重复聚合网格 */}
            {!message.metadata?.travelPlan && (
            <>
            {/* 移动端对齐由外层内容列统一处理（-ml-12） */}
            <div className="space-y-3">
            {/* 整体搭配标题：强调这是一套可执行的搭配而非单品罗列 */}
            <div className="flex items-center justify-between gap-2 pt-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-medium text-stone-600">🧥 整体搭配方案</span>
                <span className="text-[10px] text-stone-400 truncate">
                  {Array.from(new Set(message.metadata.items.map((it: RecommendItem) => it.category))).slice(0, 4).join(' · ') || `${message.metadata.items.length} 件单品`}
                </span>
              </div>
              {/* 手动收起：已看过的批次可随时折叠，不占地方 */}
              {!isStreaming && (
                <button
                  onClick={() => {
                    setCollapsedState(true)
                    onToggleCollapse?.(true)
                  }}
                  className="shrink-0 flex items-center gap-0.5 text-[11px] text-stone-400 hover:text-stone-600 transition-colors"
                  aria-label="收起这条推荐结果"
                >
                  收起
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
              )}
            </div>
            {/* 移动端加大行间距，避免卡片拥挤（用户反馈 #2） */}
            <div className="grid grid-cols-2 gap-x-3 gap-y-4 pt-1 sm:gap-4">
              {[...message.metadata.items]
                .sort((a: RecommendItem, b: RecommendItem) =>
                  (OUTFIT_SLOT_ORDER[a.category] ?? 8) - (OUTFIT_SLOT_ORDER[b.category] ?? 8)
                )
                .map((item: RecommendItem, index: number) => (
                <RecommendCard 
                  key={item.item_code || `item-${index}`} 
                  item={item} 
                  index={index} 
                  onImageClick={(imageUrl) => setSelectedImage(imageUrl)}
                  showReason={topReasonItems.has(item)}
                />
              ))}
            </div>
            </div>
            </>
            )}

            {/* 生成海报按钮 */}
            <div className="pt-4 flex justify-center gap-3">
              <button
                onClick={() => setIsPosterOpen(true)}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium hover:from-purple-600 hover:to-pink-600 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
              >
                <Sparkles className="w-5 h-5" />
                生成分享海报
              </button>
              
              {/* 换一批按钮 */}
              {onRefreshBatch && batchIndex < 2 && !isLoading && (
                <button
                  onClick={onRefreshBatch}
                  className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium hover:from-blue-600 hover:to-cyan-600 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  换一批
                </button>
              )}

              {/* 衣橱交叉入口：推荐结果→衣橱，解决新用户找不到衣橱的问题 */}
              {onNavigateToWardrobe && (
                <button
                  onClick={onNavigateToWardrobe}
                  className="flex items-center gap-2 px-5 py-3 bg-white border border-stone-200 text-stone-700 rounded-xl font-medium hover:bg-stone-50 transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5"
                >
                  <span aria-hidden="true">👗</span>
                  去衣橱试搭
                </button>
              )}
            </div>
            
            {/* 批次提示 */}
            {batchIndex > 0 && (
              <p className="text-center text-xs text-stone-400 mt-2">
                第 {batchIndex + 1} 批推荐 {batchIndex >= 2 ? '（已是最后一批）' : ''}
              </p>
            )}

            {/* 海报生成器 */}
            <Suspense fallback={null}>
            <PosterGenerator
              isOpen={isPosterOpen}
              onClose={handleClosePoster}
              title="今日五行穿搭推荐"
              items={message.metadata.items.map((item: RecommendItem) => ({
                name: item.name,
                image_url: item.image_url,
                primary_element: item.primary_element,
                color: item.color,
                category: item.category,
                reason: item.reason,
              }))}
              xiyongElements={message.metadata?.targetElements || []}
              scene={message.metadata?.scene || ''}
              quote={message.content}
              username={displayName}
            />
            </Suspense>
          </>
        )}
      </div>

      {/* 图片灯箱 */}
      {selectedImage && (
        <ImageLightbox
          imageUrl={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </motion.div>
  )
}
