'use client'

import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { ChatMessage, RecommendItem } from '@/types'
import { RecommendCard } from './RecommendCard'
import { PosterGenerator } from './PosterGenerator'
import { cn } from '@/lib/utils'
import { Sparkles } from 'lucide-react'

const ELEMENT_EMOJI: Record<string, string> = {
  '金': '⚪', '木': '🟢', '水': '🔵', '火': '🔴', '土': '🟡',
}

interface ChatMessageItemProps {
  message: ChatMessage
  onOpenPoster?: () => void
  onClosePoster?: () => void
}

export function ChatMessageItem({ 
  message,
  onOpenPoster,
  onClosePoster 
}: ChatMessageItemProps) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const isUser = message.role === 'user'
  const isStreaming = message.type !== 'done' && message.role === 'assistant' && message.type !== 'error'
  const isInitial = !message.content && isStreaming  // 刚开始，还没有内容
  const hasAnalysis = !!message.metadata?.targetElements  // 已有分析结果
  const hasItems = !!message.metadata?.items  // 已有推荐物品
  const [isPosterOpen, setIsPosterOpen] = useState(false)
  const messageRef = useRef<HTMLDivElement>(null)

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

      <div className="flex-1 space-y-3 min-w-0">
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

        {/* 内容 */}
        <div className="text-stone-700 leading-relaxed whitespace-pre-wrap">
          {message.content}
          {isStreaming && message.content && <span className="inline-block w-0.5 h-4 bg-amber-500 ml-0.5 animate-pulse align-middle" />}
        </div>

        {/* 推荐卡片 */}
        {message.metadata?.items && message.metadata.items.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-3 pt-2">
              {message.metadata.items.map((item: RecommendItem, index: number) => (
                <RecommendCard 
                  key={item.item_code || `item-${index}`} 
                  item={item} 
                  index={index} 
                  onImageClick={(imageUrl) => setSelectedImage(imageUrl)}
                />
              ))}
            </div>

            {/* 生成海报按钮 */}
            <div className="pt-4 flex justify-center">
              <button
                onClick={() => setIsPosterOpen(true)}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-medium hover:from-purple-600 hover:to-pink-600 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
              >
                <Sparkles className="w-5 h-5" />
                生成分享海报
              </button>
            </div>

            {/* 海报生成器 */}
            <PosterGenerator
              isOpen={isPosterOpen}
              onClose={handleClosePoster}
              title="今日五行穿搭推荐"
              items={message.metadata.items.map((item: RecommendItem) => ({
                name: item.name,
                image_url: item.image_url,
                primary_element: item.primary_element,
                color: item.color,
              }))}
              xiyongElements={message.metadata?.targetElements || []}
              scene={message.metadata?.scene || ''}
              quote={message.content}
              username="用户"
            />
          </>
        )}
      </div>

      {/* 图片灯箱 */}
      {selectedImage && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[200] flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ type: "spring", duration: 0.4 }}
            className="relative max-w-4xl max-h-[90vh] w-full"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 关闭按钮 */}
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute -top-12 right-0 w-10 h-10 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-colors"
              aria-label="关闭图片"
            >
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            {/* 图片 */}
            <img
              src={selectedImage}
              alt="推荐单品"
              className="w-full h-full object-contain rounded-lg"
            />
          </motion.div>
        </motion.div>
      )}
    </motion.div>
  )
}
