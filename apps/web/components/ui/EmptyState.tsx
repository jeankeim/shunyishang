'use client'

import { motion } from 'framer-motion'
import { Shirt, MessageSquare, Calendar, Search, AlertCircle, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: 'wardrobe' | 'chat' | 'calendar' | 'search' | 'alert'
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  className?: string
}

const iconMap = {
  wardrobe: Shirt,
  chat: MessageSquare,
  calendar: Calendar,
  search: Search,
  alert: AlertCircle,
}

export function EmptyState({
  icon = 'wardrobe',
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  const Icon = iconMap[icon]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={cn('flex flex-col items-center justify-center py-16 px-4', className)}
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.1, type: 'spring', stiffness: 300, damping: 25 }}
        className="w-24 h-24 mb-6 rounded-full bg-gradient-to-br from-[#F0F7F4] to-[#E8F5EC] flex items-center justify-center shadow-sm"
      >
        <Icon className="w-12 h-12 text-[#3DA35D]/40" />
      </motion.div>
      
      <motion.h3
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="text-lg font-semibold text-[#2D4A38] mb-2 text-center"
      >
        {title}
      </motion.h3>
      
      {description && (
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-sm text-[#6B7F72] mb-6 text-center max-w-xs leading-relaxed"
        >
          {description}
        </motion.p>
      )}
      
      {actionLabel && onAction && (
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onAction}
          className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white font-medium shadow-sm hover:shadow-md transition-all duration-200"
        >
          <Plus className="w-4 h-4" />
          {actionLabel}
        </motion.button>
      )}
    </motion.div>
  )
}
