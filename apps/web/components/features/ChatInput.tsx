'use client'

import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BaziInput } from '@/types'
import { consumePendingChatAutofill, onChatInputAutofill } from '@/lib/chatAutofill'

interface ChatInputProps {
  onSend: (message: string, bazi?: BaziInput) => void
  disabled?: boolean
  bazi?: BaziInput
}

export function ChatInput({ onSend, disabled, bazi }: ChatInputProps) {
  const [input, setInput] = useState('')
  // 联动填充高亮：短暂光晕反馈，避免文本静默出现的生硬感
  const [autofillFlash, setAutofillFlash] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  // 场景联动：记录最近一次自动填充的文本，清除场景时仅清空联动文本，避免误删用户已输入内容
  const lastAutofillRef = useRef('')
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 联动填充反馈：平滑滚动至输入框 + 短暂光晕，让用户感知到场景已带入
  const playAutofillFeedback = () => {
    setAutofillFlash(true)
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current)
    flashTimerRef.current = setTimeout(() => setAutofillFlash(false), 1500)
    // 延迟等待移动端控制面板收起动画，避免滚动目标被遮挡或位置偏移
    setTimeout(() => {
      textareaRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
    }, 350)
  }

  // 场景选择联动：常用场景选中后将场景名称自动填充到输入框
  useEffect(() => {
    // 消费挂载前产生的联动文本（如在其他 Tab 选择了场景）
    const pending = consumePendingChatAutofill()
    if (pending) {
      lastAutofillRef.current = pending
      setInput(pending)
      playAutofillFeedback()
    }
    const unsubscribe = onChatInputAutofill((text) => {
      if (text) {
        lastAutofillRef.current = text
        setInput(text)
        playAutofillFeedback()
      } else {
        // 取消场景：仅当输入框仍为联动文本时清空（先取值再重置，避免 updater 执行时 ref 已被清空）
        const last = lastAutofillRef.current
        lastAutofillRef.current = ''
        setInput(prev => (prev === last ? '' : prev))
      }
    })
    return () => {
      unsubscribe()
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current)
    }
  }, [])

  const handleSend = () => {
    if (!input.trim()) return
    onSend(input, bazi)
    setInput('')
  }

  // 移动端键盘弹出时，确保输入框可见
  const handleFocus = () => {
    // 延迟执行，等待键盘动画完成
    setTimeout(() => {
      textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 300)
  }

  return (
    <div className="border-t border-[var(--brand-border)] bg-white p-4">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        {/* 输入框 */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={handleFocus}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="描述你的穿搭需求..."
          className={cn(
            'flex-1 min-h-[60px] max-h-[200px] resize-none rounded-lg border bg-white px-3 py-2 text-sm text-[var(--brand-heading)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)]/40 focus:border-[var(--wuxing-wood)]/40 shadow-sm placeholder:text-[var(--brand-subtle)] font-medium transition-all duration-500',
            autofillFlash
              ? 'border-[var(--wuxing-wood)]/60 ring-2 ring-[var(--wuxing-wood)]/30 bg-[var(--brand-surface)]/40'
              : 'border-[var(--brand-border)]'
          )}
          disabled={disabled}
        />

        {/* 发送按钮 */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className={cn(
            'p-2 rounded-lg bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white transition-all shadow-sm hover:shadow-md shrink-0',
            (disabled || !input.trim()) && 'opacity-50 cursor-not-allowed',
            !disabled && input.trim() && 'hover:opacity-90'
          )}
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
