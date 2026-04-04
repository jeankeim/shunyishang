'use client'

import { motion } from 'framer-motion'
import { ChatMessage, RecommendItem } from '@/types'
import { RecommendCard } from './RecommendCard'
import { cn } from '@/lib/utils'

const ELEMENT_EMOJI: Record<string, string> = {
  '金': '⚪', '木': '🟢', '水': '🔵', '火': '🔴', '土': '🟡',
}

interface ChatMessageItemProps {
  message: ChatMessage
}

export function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.role === 'user'
  const isStreaming = message.type !== 'done' && message.role === 'assistant' && message.type !== 'error'
  const isInitial = !message.content && isStreaming  // 刚开始，还没有内容
  const hasAnalysis = !!message.metadata?.targetElements  // 已有分析结果
  const hasItems = !!message.metadata?.items  // 已有推荐物品

  // 根据处理阶段显示不同的提示
  const getStatusText = () => {
    if (isInitial && !hasAnalysis) return '正在分析您的八字和场景...'
    if (hasAnalysis && !hasItems) return '正在为您匹配最合适的衣物...'
    if (hasItems) return '正在生成搭配建议...'
    return '正在思考中...'
  }

  return (
    <motion.div
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
            {message.metadata.items.map((item: RecommendItem, index: number) => (
              <RecommendCard 
                key={item.item_code || `item-${index}`} 
                item={item} 
                index={index} 
              />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
