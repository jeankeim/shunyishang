'use client'

import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Bell, Clock, BookOpen, Sparkles, Megaphone } from 'lucide-react'
import { useMembershipStore } from '@/store/membership'

function ToggleSwitch({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${
        enabled ? 'bg-emerald-500' : 'bg-stone-300'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
          enabled ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

export function PushSettings() {
  const { pushSettings, fetchPushSettings, updatePushSettings } = useMembershipStore()

  useEffect(() => {
    fetchPushSettings()
  }, [fetchPushSettings])

  if (!pushSettings) {
    return (
      <div className="animate-pulse space-y-4 p-4">
        <div className="h-4 bg-stone-200 rounded w-1/3" />
        <div className="h-10 bg-stone-100 rounded" />
        <div className="h-10 bg-stone-100 rounded" />
      </div>
    )
  }

  const toggle = (key: string) => {
    updatePushSettings({ [key]: !(pushSettings as any)[key] })
  }

  const settings = [
    {
      key: 'enabled',
      label: '推送通知',
      description: '接收所有推送通知',
      icon: Bell,
      color: 'text-emerald-600',
    },
    {
      key: 'fortune_push',
      label: '每日运势',
      description: `每天 ${pushSettings.fortune_push_time?.slice(0, 5) || '08:00'} 推送运势`,
      icon: Sparkles,
      color: 'text-violet-600',
    },
    {
      key: 'diary_reminder',
      label: '日记提醒',
      description: `每天 ${pushSettings.diary_reminder_time?.slice(0, 5) || '21:00'} 提醒记录穿搭`,
      icon: BookOpen,
      color: 'text-blue-600',
    },
    {
      key: 'marketing',
      label: '活动通知',
      description: '接收优惠活动和功能更新',
      icon: Megaphone,
      color: 'text-amber-600',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-1"
    >
      {settings.map((setting, index) => (
        <motion.div
          key={setting.key}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.05 }}
          className="flex items-center justify-between p-3 rounded-xl hover:bg-stone-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center">
              <setting.icon className={`w-4 h-4 ${setting.color}`} />
            </div>
            <div>
              <p className="text-sm font-medium text-stone-700">{setting.label}</p>
              <p className="text-xs text-stone-400">{setting.description}</p>
            </div>
          </div>
          <ToggleSwitch
            enabled={(pushSettings as any)[setting.key]}
            onToggle={() => toggle(setting.key)}
          />
        </motion.div>
      ))}
    </motion.div>
  )
}
