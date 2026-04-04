'use client'

import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastProps {
  toast: Toast
  onRemove: (id: string) => void
}

const toastIcons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  warning: AlertCircle,
}

const toastStyles = {
  success: 'bg-[#3DA35D] text-white',
  error: 'bg-[#D4656B] text-white',
  info: 'bg-[#4A90C4] text-white',
  warning: 'bg-[#B89B5E] text-white',
}

export function ToastItem({ toast, onRemove }: ToastProps) {
  const Icon = toastIcons[toast.type]

  useEffect(() => {
    const timer = setTimeout(() => {
      onRemove(toast.id)
    }, toast.duration || 3000)

    return () => clearTimeout(timer)
  }, [toast.id, toast.duration, onRemove])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      className="flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg max-w-sm"
    >
      <div className={toastStyles[toast.type] + ' rounded-lg p-2 flex items-center gap-2 min-w-[280px]'}>
        <Icon className="w-5 h-5 flex-shrink-0" />
        <p className="text-sm font-medium flex-1">{toast.message}</p>
        <button
          onClick={() => onRemove(toast.id)}
          className="p-1 hover:bg-white/20 rounded transition-colors"
          aria-label="关闭通知"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  )
}

interface ToastContainerProps {
  toasts: Toast[]
  onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onRemove={onRemove} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// Toast 管理器
class ToastManager {
  private toasts: Toast[] = []
  private listeners: Array<(toasts: Toast[]) => void> = []

  add(message: string, type: ToastType = 'info', duration?: number) {
    const id = Math.random().toString(36).substr(2, 9)
    const newToast: Toast = { id, message, type, duration }
    this.toasts = [...this.toasts, newToast]
    this.notify()
    return id
  }

  remove(id: string) {
    this.toasts = this.toasts.filter((t) => t.id !== id)
    this.notify()
  }

  subscribe(listener: (toasts: Toast[]) => void) {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener)
    }
  }

  private notify() {
    this.listeners.forEach((listener) => listener(this.toasts))
  }

  success(message: string, duration?: number) {
    return this.add(message, 'success', duration)
  }

  error(message: string, duration?: number) {
    return this.add(message, 'error', duration)
  }

  info(message: string, duration?: number) {
    return this.add(message, 'info', duration)
  }

  warning(message: string, duration?: number) {
    return this.add(message, 'warning', duration)
  }
}

export const toast = new ToastManager()
