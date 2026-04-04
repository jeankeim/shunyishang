'use client'

import { useState, useEffect, createContext, useContext } from 'react'
import { ToastContainer, toast, type Toast } from '@/components/ui/Toast'

interface ToastContextType {
  toast: typeof toast
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    const unsubscribe = toast.subscribe(setToasts)
    return unsubscribe
  }, [])

  const handleRemove = (id: string) => {
    toast.remove(id)
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={handleRemove} />
    </ToastContext.Provider>
  )
}
