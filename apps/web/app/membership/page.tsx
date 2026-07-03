'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Crown, ArrowLeft, Sparkles, Bell, CreditCard } from 'lucide-react'
import { MembershipCard } from '@/components/features/membership/MembershipCard'
import { PlanComparison } from '@/components/features/membership/PlanComparison'
import { PaymentForm } from '@/components/features/membership/PaymentForm'
import { PushSettings } from '@/components/features/membership/PushSettings'
import { useMembershipStore } from '@/store/membership'
import { useUserStore } from '@/store/user'

type Section = 'overview' | 'subscribe' | 'settings'

export default function MembershipPage() {
  const { isAuthenticated } = useUserStore()
  const { status } = useMembershipStore()
  const [activeSection, setActiveSection] = useState<Section>('overview')
  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly'>('monthly')

  const currentPlan = status?.plan || 'free'

  const sections = [
    { id: 'overview' as const, label: '我的会员', icon: Crown },
    { id: 'subscribe' as const, label: '升级套餐', icon: Sparkles },
    { id: 'settings' as const, label: '推送设置', icon: Bell },
  ]

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back()
    } else {
      window.location.hash = ''
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-20">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-stone-100 to-stone-200 flex items-center justify-center mx-auto mb-4">
            <Crown className="w-8 h-8 text-stone-400" />
          </div>
          <h2 className="text-xl font-bold text-stone-700 mb-2">会员中心</h2>
          <p className="text-sm text-stone-500 mb-6">请先登录后访问会员中心</p>
          <button
            onClick={() => (window.location.hash = '')}
            className="px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium rounded-xl shadow-sm hover:shadow-md transition-shadow"
          >
            返回首页
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleBack}
            className="p-2 rounded-xl hover:bg-white transition-colors shadow-sm border border-stone-200/60"
          >
            <ArrowLeft className="w-5 h-5 text-stone-600" />
          </motion.button>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] bg-clip-text text-transparent font-serif">
              会员中心
            </h1>
            <p className="text-xs text-stone-500 mt-0.5">
              {currentPlan === 'free' ? '解锁更多高级功能' : `当前：${currentPlan === 'monthly' ? '月度会员' : '年度会员'}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-amber-50 to-yellow-50 rounded-full border border-amber-200/60">
          <Crown className="w-4 h-4 text-amber-600" />
          <span className="text-xs font-medium text-amber-700">VIP</span>
        </div>
      </div>

      {/* Section Tabs */}
      <div className="flex gap-2 mb-6 bg-white/80 backdrop-blur-sm p-1.5 rounded-xl border border-stone-200/60 shadow-sm">
        {sections.map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            className={`relative flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeSection === section.id
                ? 'text-emerald-700'
                : 'text-stone-500 hover:text-stone-700'
            }`}
          >
            {activeSection === section.id && (
              <motion.div
                layoutId="membershipSectionIndicator"
                className="absolute inset-0 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-lg"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <section.icon className="w-4 h-4 relative z-10" />
            <span className="relative z-10 hidden sm:inline">{section.label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <motion.div
        key={activeSection}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        {activeSection === 'overview' && (
          <div className="space-y-6">
            {/* 会员状态卡片 */}
            <MembershipCard />

            {/* 快捷操作 */}
            <div className="grid grid-cols-2 gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveSection('subscribe')}
                className="flex items-center gap-3 p-4 bg-white rounded-2xl border border-stone-200/60 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-100 to-teal-100 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-emerald-600" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-stone-700">升级套餐</p>
                  <p className="text-xs text-stone-400">解锁无限推荐和AI点评</p>
                </div>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveSection('settings')}
                className="flex items-center gap-3 p-4 bg-white rounded-2xl border border-stone-200/60 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center">
                  <Bell className="w-5 h-5 text-violet-600" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-stone-700">推送设置</p>
                  <p className="text-xs text-stone-400">管理运势推送和日记提醒</p>
                </div>
              </motion.button>
            </div>

            {/* 当前权益 */}
            <div className="bg-white rounded-2xl border border-stone-200/60 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-stone-100 bg-stone-50/50">
                <h3 className="text-sm font-bold text-stone-700">当前权益</h3>
              </div>
              <div className="p-4 space-y-2">
                {[
                  { label: '每日穿搭推荐', free: '3次/日', monthly: '无限', yearly: '无限', current: currentPlan },
                  { label: '运势分析', free: '基础', monthly: '高级', yearly: '高级', current: currentPlan },
                  { label: 'AI 穿搭点评', free: '—', monthly: '✓', yearly: '✓', current: currentPlan },
                  { label: '穿搭广场优先展示', free: '—', monthly: '—', yearly: '✓', current: currentPlan },
                  { label: '专属客服', free: '—', monthly: '—', yearly: '✓', current: currentPlan },
                ].map((row) => {
                  const value = row[row.current as keyof typeof row] || row.free
                  const isUpgrade = value !== row.free
                  return (
                    <div key={row.label} className="flex items-center justify-between py-1.5">
                      <span className="text-sm text-stone-600">{row.label}</span>
                      <span className={`text-sm font-medium ${isUpgrade ? 'text-emerald-600' : 'text-stone-400'}`}>
                        {String(value)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {activeSection === 'subscribe' && (
          <div className="space-y-6">
            {/* 套餐对比 */}
            <PlanComparison />

            {/* 支付表单 */}
            {currentPlan === 'free' && (
              <div className="bg-white rounded-2xl border border-stone-200/60 shadow-sm p-6">
                <div className="flex items-center gap-2 mb-4">
                  <CreditCard className="w-5 h-5 text-stone-600" />
                  <h3 className="text-base font-bold text-stone-700">选择套餐并支付</h3>
                </div>

                {/* 套餐切换 */}
                <div className="flex gap-2 mb-4">
                  <button
                    onClick={() => setSelectedPlan('monthly')}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                      selectedPlan === 'monthly'
                        ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm'
                        : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                    }`}
                  >
                    月度 ¥19.9/月
                  </button>
                  <button
                    onClick={() => setSelectedPlan('yearly')}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                      selectedPlan === 'yearly'
                        ? 'bg-gradient-to-r from-amber-500 to-yellow-500 text-white shadow-sm'
                        : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                    }`}
                  >
                    年度 ¥168/年
                  </button>
                </div>

                <PaymentForm
                  plan={selectedPlan}
                  price={selectedPlan === 'monthly' ? 19.9 : 168}
                  onSuccess={() => setActiveSection('overview')}
                />
              </div>
            )}

            {currentPlan === 'monthly' && (
              <div className="bg-gradient-to-r from-amber-50 to-yellow-50 rounded-2xl border border-amber-200/60 p-6 text-center">
                <Crown className="w-8 h-8 text-amber-600 mx-auto mb-2" />
                <h3 className="text-base font-bold text-stone-700 mb-1">升级到年度会员</h3>
                <p className="text-sm text-stone-500 mb-4">
                  年度会员 ¥168/年，相当于每月仅 ¥14，比月度会员省 ¥70.8
                </p>
                <PaymentForm plan="yearly" price={168} onSuccess={() => setActiveSection('overview')} />
              </div>
            )}

            {currentPlan === 'yearly' && (
              <div className="bg-gradient-to-r from-amber-50 to-yellow-50 rounded-2xl border border-amber-200/60 p-8 text-center">
                <Crown className="w-10 h-10 text-amber-600 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-stone-700 mb-1">您已是最高级会员</h3>
                <p className="text-sm text-stone-500">年度会员享有全部功能，无需额外升级</p>
              </div>
            )}
          </div>
        )}

        {activeSection === 'settings' && (
          <div className="space-y-6">
            {/* 推送设置 */}
            <div className="bg-white rounded-2xl border border-stone-200/60 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-stone-100 bg-stone-50/50 flex items-center gap-2">
                <Bell className="w-4 h-4 text-stone-500" />
                <h3 className="text-sm font-bold text-stone-700">推送偏好设置</h3>
              </div>
              <div className="p-4">
                <PushSettings />
              </div>
            </div>

            {/* 推送说明 */}
            <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-2xl border border-violet-200/60 p-5">
              <h4 className="text-sm font-semibold text-violet-700 mb-2">推送说明</h4>
              <ul className="space-y-1.5 text-xs text-stone-600">
                <li className="flex items-start gap-2">
                  <span className="text-violet-400 mt-0.5">•</span>
                  <span><strong>每日运势推送</strong>：根据您的八字分析，每天早晨推送当日运势和穿搭建议</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-violet-400 mt-0.5">•</span>
                  <span><strong>日记提醒</strong>：每天晚上提醒您记录当日穿搭，养成穿搭日记习惯</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-violet-400 mt-0.5">•</span>
                  <span><strong>活动通知</strong>：功能更新、优惠活动等重要信息推送</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}
