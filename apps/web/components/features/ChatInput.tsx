'use client'

import { useState } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BaziInput } from '@/types'

interface ChatInputProps {
  onSend: (message: string, bazi?: BaziInput) => void
  disabled?: boolean
  bazi?: BaziInput
}

export function ChatInput({ onSend, disabled, bazi }: ChatInputProps) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (!input.trim()) return
    onSend(input, bazi)
    setInput('')
  }

  return (
    <div className="border-t border-amber-200/30 bg-gradient-to-r from-white to-amber-50/30 p-4">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        {/* 输入框 */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="描述你的穿搭需求..."
          className="flex-1 min-h-[60px] max-h-[200px] resize-none rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400 shadow-sm placeholder:text-stone-400"
          disabled={disabled}
        />

        {/* 发送按钮 */}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className={cn(
            'p-2 rounded-lg bg-gradient-to-r from-amber-400 to-orange-400 text-white transition-all shadow-sm hover:shadow-md shrink-0',
            (disabled || !input.trim()) && 'opacity-50 cursor-not-allowed',
            !disabled && input.trim() && 'hover:from-amber-500 hover:to-orange-500'
          )}
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
    </div>
  )
}
