'use client'

import { Plus, MessageSquare, X, Menu, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/store/chat'

interface SidebarProps {
  className?: string
  collapsed?: boolean
  onToggle?: () => void
}

export function Sidebar({ className, collapsed = true, onToggle }: SidebarProps) {
  const { conversations, currentConversationId, setCurrentConversation, createConversation } =
    useChatStore()

  if (collapsed) return null

  return (
    <>
      {/* 遮罩层 - 移动端全屏遮罩，桌面端半透明 */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity"
        onClick={onToggle}
      />
      
      {/* 侧边面板 - 桌面端固定宽度，移动端全宽 */}
      <motion.div 
        initial={{ x: -320, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: -320, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={cn(
          'fixed left-0 top-0 h-full w-80 md:w-[320px] z-50',
          'flex flex-col',
          'bg-white/95 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.12)] border-r border-[#E8F0EB]/60',
          className
        )}
      >
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E8F0EB]/50">
          <h2 className="text-lg font-semibold text-[#2D4A38] font-serif tracking-wide">历史记录</h2>
          <motion.button
            whileHover={{ scale: 1.1, rotate: 90 }}
            whileTap={{ scale: 0.9 }}
            onClick={onToggle}
            className="p-2 rounded-lg hover:bg-[#F0F7F4] transition-colors duration-200"
            aria-label="关闭侧边栏"
          >
            <X className="h-5 w-5 text-[#6B7F72]" />
          </motion.button>
        </div>

        {/* 新建对话按钮 */}
        <div className="p-4">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              createConversation()
              onToggle?.()
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 border-dashed border-[#3DA35D]/40 hover:border-[#3DA35D]/60 hover:bg-[#F0F7F4]/60 transition-all duration-200 text-[#5A7A66] hover:text-[#3DA35D]"
          >
            <Plus className="h-4 w-4" />
            <span className="text-sm font-medium">新建对话</span>
          </motion.button>
        </div>

        {/* 对话列表 */}
        <div className="flex-1 overflow-y-auto px-4">
          {conversations.length > 0 ? (
            <div className="space-y-2">
              {conversations.map((conv) => (
                <motion.button
                  key={conv.id}
                  whileHover={{ x: 4 }}
                  onClick={() => {
                    setCurrentConversation(conv.id)
                    onToggle?.()
                  }}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-left transition-all duration-200',
                    currentConversationId === conv.id
                      ? 'bg-gradient-to-r from-[#F0F7F4] to-[#E8F5EC] text-[#2D4A38] border border-[#3DA35D]/30 shadow-sm'
                      : 'hover:bg-[#F5F9F7] text-[#4A5F52]'
                  )}
                >
                  <MessageSquare className={cn(
                    "h-4 w-4 shrink-0",
                    currentConversationId === conv.id ? "text-[#3DA35D]" : "text-[#8A9F92]"
                  )} />
                  <span className="truncate flex-1 font-medium">{conv.title}</span>
                </motion.button>
              ))}
            </div>
          ) : (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="flex flex-col items-center justify-center py-16 text-[#8A9F92]"
            >
              <MessageSquare className="h-12 w-12 mb-3 opacity-30" />
              <p className="text-sm">暂无历史记录</p>
            </motion.div>
          )}
        </div>

        {/* 底部工具栏 */}
        <div className="p-4 border-t border-[#E8F0EB]/50">
          <div className="flex items-center justify-center gap-2 text-sm text-[#6B7F72]">
            <Sparkles className="h-4 w-4 text-[#3DA35D]" />
            <span className="font-medium">顺衣尚 · 五行智能衣橱</span>
          </div>
        </div>
      </motion.div>
    </>
  )
}
