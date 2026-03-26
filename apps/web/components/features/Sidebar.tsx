'use client'

import { Plus, MessageSquare, X, Menu, Sparkles } from 'lucide-react'
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
      <div 
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onToggle}
      />
      
      {/* 侧边面板 - 桌面端固定宽度，移动端全宽 */}
      <div 
        className={cn(
          'fixed left-0 top-0 h-full w-80 md:w-[320px] z-50',
          'flex flex-col',
          'bg-gradient-to-b from-white to-amber-50/30 backdrop-blur-xl shadow-2xl border-r border-amber-200/30',
          'animate-in slide-in-from-left duration-300',
          className
        )}
      >
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-amber-200/30">
          <h2 className="text-lg font-semibold text-stone-700">历史记录</h2>
          <button
            onClick={onToggle}
            className="p-2 rounded-lg hover:bg-amber-100/60 transition-colors"
          >
            <X className="h-5 w-5 text-stone-500" />
          </button>
        </div>

        {/* 新建对话按钮 */}
        <div className="p-4">
          <button
            onClick={() => {
              createConversation()
              onToggle?.()
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-dashed border-amber-300/60 hover:border-amber-400 hover:bg-amber-50/60 transition-all text-stone-600"
          >
            <Plus className="h-4 w-4" />
            <span className="text-sm font-medium">新建对话</span>
          </button>
        </div>

        {/* 对话列表 */}
        <div className="flex-1 overflow-y-auto px-4">
          {conversations.length > 0 ? (
            <div className="space-y-2">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setCurrentConversation(conv.id)
                    onToggle?.()
                  }}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-left transition-all',
                    currentConversationId === conv.id
                      ? 'bg-gradient-to-r from-amber-100/80 to-orange-100/60 text-amber-700 border border-amber-200/40 shadow-sm'
                      : 'hover:bg-amber-50/60 text-stone-700'
                  )}
                >
                  <MessageSquare className="h-4 w-4 shrink-0 text-amber-500" />
                  <span className="truncate flex-1">{conv.title}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-stone-500">
              <MessageSquare className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm">暂无历史记录</p>
            </div>
          )}
        </div>

        {/* 底部工具栏 */}
        <div className="p-4 border-t border-amber-200/30">
          <div className="flex items-center justify-center gap-2 text-sm text-stone-600">
            <Sparkles className="h-4 w-4 text-amber-500" />
            <span>顺衣裳 · 五行智能衣橱</span>
          </div>
        </div>
      </div>
    </>
  )
}
