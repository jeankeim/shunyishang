'use client'

import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Crown, Calendar, Zap } from 'lucide-react'
import { useMembershipStore } from '@/store/membership'

const planConfig: Record<string, { label: string; color: string; gradient: string; icon: string }> = {
  free: { label: '免费版', color: 'text-stone-600', gradient: 'from-stone-100 to-stone-200', icon: '🌱' },
  monthly: { label: '月度会员', color: 'text-emerald-700', gradient: 'from-emerald-50 to-teal-100', icon: '⭐' },
  yearly: { label: '年度会员', color: 'text-amber-700', gradient: 'from-amber-50 to-yellow-100', icon: '👑' },
}

export function MembershipCard() {
  const { status, fetchStatus } = useMembershipStore()

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const plan = status?.plan || 'free'
  const config = planConfig[plan] || planConfig.free

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${config.gradient} p-6 shadow-sm border border-white/50`}
    >
      {/* 装饰元素 */}
      <div className="absolute top-0 right-0 w-32 h-32 opacity-10">
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-current to-transparent" />
      </div>

      <div className="relative z-10">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <h3 className={`text-lg font-bold ${config.color}`}>{config.label}</h3>
            <p className="text-sm text-stone-500">
              {status?.status === 'active' ? '已激活' : '未激活'}
            </p>
          </div>
        </div>

        {plan !== 'free' && (
          <div className="space-y-2">
            {status?.days_remaining !== undefined && (
              <div className="flex items-center gap-2 text-sm text-stone-600">
                <Calendar className="w-4 h-4" />
                <span>剩余 {status.days_remaining} 天</span>
              </div>
            )}
            {status?.auto_renew && (
              <div className="flex items-center gap-2 text-sm text-stone-600">
                <Zap className="w-4 h-4" />
                <span>自动续费已开启</span>
              </div>
            )}
            {status?.expires_at && (
              <p className="text-xs text-stone-400">
                到期日：{new Date(status.expires_at).toLocaleDateString('zh-CN')}
              </p>
            )}
          </div>
        )}

        {plan === 'free' && (
          <p className="text-sm text-stone-500 mt-2">
            升级会员解锁无限推荐、AI点评等高级功能
          </p>
        )}
      </div>
    </motion.div>
  )
}
