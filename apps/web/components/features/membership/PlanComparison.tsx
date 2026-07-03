'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import { useMembershipStore } from '@/store/membership'
import type { PlanInfo } from '@/types'

export function PlanComparison() {
  const { plans, fetchPlans, status, subscribe, upgrade, isLoading } = useMembershipStore()
  const [selectedPlan, setSelectedPlan] = useState<string>('')

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  const currentPlan = status?.plan || 'free'

  const handleAction = async (planKey: string) => {
    if (currentPlan === 'free') {
      await subscribe(planKey, 'mock')
    } else if (planKey === 'yearly' && currentPlan === 'monthly') {
      await upgrade(planKey)
    }
  }

  const planColors: Record<string, { border: string; bg: string; btn: string; badge: string }> = {
    free: {
      border: 'border-stone-200',
      bg: 'bg-white',
      btn: 'bg-stone-100 text-stone-500 cursor-default',
      badge: '',
    },
    monthly: {
      border: 'border-emerald-200',
      bg: 'bg-gradient-to-b from-emerald-50/50 to-white',
      btn: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-600 hover:to-teal-600',
      badge: 'bg-emerald-100 text-emerald-700',
    },
    yearly: {
      border: 'border-amber-200',
      bg: 'bg-gradient-to-b from-amber-50/50 to-white',
      btn: 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white hover:from-amber-600 hover:to-yellow-600',
      badge: 'bg-amber-100 text-amber-700',
    },
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {plans.map((plan, index) => {
        const colors = planColors[plan.plan_key] || planColors.free
        const isCurrent = currentPlan === plan.plan_key
        const isUpgrade =
          (currentPlan === 'free' && plan.plan_key !== 'free') ||
          (currentPlan === 'monthly' && plan.plan_key === 'yearly')

        return (
          <motion.div
            key={plan.plan_key}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`relative rounded-2xl border-2 ${colors.border} ${colors.bg} p-6 flex flex-col`}
          >
            {plan.plan_key === 'yearly' && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-gradient-to-r from-amber-400 to-yellow-400 text-white text-xs font-bold rounded-full">
                最划算
              </div>
            )}

            <div className="text-center mb-4">
              <h3 className="text-lg font-bold text-stone-800">{plan.name}</h3>
              <div className="mt-2">
                {plan.plan_key === 'free' ? (
                  <span className="text-3xl font-bold text-stone-600">免费</span>
                ) : (
                  <div>
                    <span className="text-3xl font-bold text-stone-800">
                      ¥{plan.plan_key === 'monthly' ? plan.price_monthly : plan.price_yearly}
                    </span>
                    <span className="text-sm text-stone-500">
                      /{plan.plan_key === 'monthly' ? '月' : '年'}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <ul className="space-y-2 mb-6 flex-1">
              {plan.features.map((feature, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-stone-600">
                  <Check className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleAction(plan.plan_key)}
              disabled={!isUpgrade || isLoading || plan.plan_key === 'free'}
              className={`w-full py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                isCurrent
                  ? 'bg-stone-100 text-stone-500 cursor-default'
                  : isUpgrade
                  ? `${colors.btn} shadow-sm hover:shadow-md`
                  : 'bg-stone-50 text-stone-400 cursor-default'
              }`}
            >
              {isCurrent ? '当前套餐' : isUpgrade ? (currentPlan === 'free' ? '立即订阅' : '立即升级') : '无需操作'}
            </button>
          </motion.div>
        )
      })}
    </div>
  )
}
