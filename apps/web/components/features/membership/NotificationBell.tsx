'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, X, Check } from 'lucide-react'
import { useMembershipStore } from '@/store/membership'
import type { PushNotification } from '@/types'

const typeConfig: Record<string, { label: string; icon: string; color: string }> = {
  fortune_daily: { label: '每日运势', icon: '🔮', color: 'bg-violet-100 text-violet-700' },
  diary_reminder: { label: '日记提醒', icon: '📓', color: 'bg-blue-100 text-blue-700' },
  marketing: { label: '活动通知', icon: '🎉', color: 'bg-amber-100 text-amber-700' },
  system: { label: '系统通知', icon: 'ℹ️', color: 'bg-stone-100 text-stone-700' },
}

function NotificationItem({ notification, onRead }: {
  notification: PushNotification
  onRead: (id: number) => void
}) {
  const config = typeConfig[notification.type] || typeConfig.system
  const isUnread = !notification.read_at

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-xl transition-colors ${
        isUnread ? 'bg-white shadow-sm border border-stone-100' : 'bg-stone-50'
      }`}
    >
      <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${config.color} flex items-center justify-center text-base`}>
        {config.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className={`text-sm truncate ${isUnread ? 'font-semibold text-stone-800' : 'font-medium text-stone-600'}`}>
            {notification.title}
          </p>
          {isUnread && (
            <span className="flex-shrink-0 w-2 h-2 bg-emerald-500 rounded-full" />
          )}
        </div>
        {notification.body && (
          <p className="text-xs text-stone-500 mt-0.5 line-clamp-2">{notification.body}</p>
        )}
        <div className="flex items-center gap-2 mt-1">
          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${config.color}`}>
            {config.label}
          </span>
          <span className="text-xs text-stone-400">
            {new Date(notification.sent_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
          </span>
        </div>
      </div>
      {isUnread && (
        <button
          onClick={() => onRead(notification.id)}
          className="flex-shrink-0 p-1 rounded-lg text-stone-400 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
          title="标记已读"
        >
          <Check className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

export function NotificationBell() {
  const { notifications, unreadCount, fetchNotifications, fetchUnreadCount, markAsRead } = useMembershipStore()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchUnreadCount()
    fetchNotifications()
  }, [fetchUnreadCount, fetchNotifications])

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleMarkRead = async (id: number) => {
    await markAsRead(id)
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* 铃铛按钮 */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl hover:bg-stone-100 transition-colors"
        aria-label={`通知${unreadCount > 0 ? `，${unreadCount}条未读` : ''}`}
      >
        <Bell className="w-5 h-5 text-stone-600" />
        {unreadCount > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-white text-xs font-bold px-1 shadow-sm"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </motion.span>
        )}
      </motion.button>

      {/* 下拉通知面板 */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 28 }}
            className="absolute right-0 top-full mt-2 w-80 max-h-[420px] bg-white/98 backdrop-blur-xl rounded-2xl shadow-[0_12px_48px_rgba(0,0,0,0.12)] border border-stone-100 overflow-hidden z-50"
          >
            {/* 头部 */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-stone-100 bg-stone-50/50">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-stone-800">通知</h3>
                {unreadCount > 0 && (
                  <span className="px-1.5 py-0.5 bg-red-100 text-red-600 text-xs font-medium rounded-full">
                    {unreadCount} 未读
                  </span>
                )}
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-lg text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* 通知列表 */}
            <div className="overflow-y-auto max-h-[340px] p-3 space-y-2 scrollbar-thin">
              {notifications.length === 0 ? (
                <div className="py-8 text-center">
                  <Bell className="w-8 h-8 text-stone-300 mx-auto mb-2" />
                  <p className="text-sm text-stone-400">暂无通知</p>
                </div>
              ) : (
                notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onRead={handleMarkRead}
                  />
                ))
              )}
            </div>

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
