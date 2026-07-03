'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { getCultivationProfile, dailyCheckin } from '@/lib/api'

interface Achievement {
  id: number
  code: string
  name: string
  description: string
  icon: string
  category: string
  requirement_value: number
  points_reward: number
  is_unlocked: boolean
  unlocked_at?: string
}

interface Profile {
  total_points: number
  current_points: number
  cultivation_level: number
  level_name: string
  level_icon: string
  next_level_name: string
  next_level_min_points: number
  level_progress: number
  streak_days: number
  last_checkin_date: string
  unlocked_achievements: Achievement[]
  all_achievements: Achievement[]
}

export default function CultivationPage() {
  const { isAuthenticated } = useUserStore()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(false)
  const [checkingIn, setCheckingIn] = useState(false)
  const [checkinResult, setCheckinResult] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) fetchProfile()
  }, [isAuthenticated])

  const fetchProfile = async () => {
    setLoading(true)
    try {
      const data = await getCultivationProfile()
      setProfile(data)
    } catch (e) {
      console.error('获取修炼档案失败:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleCheckin = async () => {
    if (checkingIn) return
    setCheckingIn(true)
    try {
      const result = await dailyCheckin()
      setCheckinResult(
        result.points_earned > 0
          ? `签到成功！+${result.points_earned} 积分，连续 ${result.streak_days} 天`
          : result.message
      )
      if (result.new_achievements?.length > 0) {
        setCheckinResult(prev => `${prev}\n🎉 解锁成就：${result.new_achievements.map((a: any) => a.name).join('、')}`)
      }
      fetchProfile()
    } catch (e: any) {
      setCheckinResult(e.message || '签到失败')
    } finally {
      setCheckingIn(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <p className="text-5xl mb-4">🏔️</p>
        <h2 className="text-lg font-semibold text-stone-800 mb-2">五行修炼</h2>
        <p className="text-sm text-stone-500">登录后可查看修炼等级与成就</p>
      </div>
    )
  }

  if (loading || !profile) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-amber-500 border-t-transparent" />
      </div>
    )
  }

  const today = new Date().toISOString().split('T')[0]
  const alreadyCheckedIn = profile.last_checkin_date === today

  return (
    <div className="max-w-4xl mx-auto pb-8">
      {/* 修炼等级卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 rounded-2xl p-6 border border-amber-200/60 shadow-sm mb-6"
      >
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-200 to-orange-300 flex items-center justify-center text-3xl shadow-inner">
            {profile.level_icon}
          </div>
          <div>
            <h2 className="text-xl font-bold text-stone-800">
              {profile.level_name} · Lv.{profile.cultivation_level}
            </h2>
            <p className="text-sm text-stone-500">五行修炼等级</p>
          </div>
        </div>

        {/* 进度条 */}
        <div className="mb-2">
          <div className="flex justify-between text-xs text-stone-500 mb-1">
            <span>{profile.level_name}</span>
            <span>{profile.next_level_name} ({profile.next_level_min_points} 积分)</span>
          </div>
          <div className="h-3 bg-white/60 rounded-full overflow-hidden border border-amber-200/40">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${profile.level_progress * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="h-full bg-gradient-to-r from-amber-400 to-orange-500 rounded-full"
            />
          </div>
        </div>

        <div className="flex items-center justify-between mt-4">
          <div className="flex gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">{profile.total_points}</p>
              <p className="text-xs text-stone-500">累计积分</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">{profile.current_points}</p>
              <p className="text-xs text-stone-500">可用积分</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-rose-600">{profile.streak_days}</p>
              <p className="text-xs text-stone-500">连续打卡</p>
            </div>
          </div>

          <button
            onClick={handleCheckin}
            disabled={alreadyCheckedIn || checkingIn}
            className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
              alreadyCheckedIn
                ? 'bg-stone-100 text-stone-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md hover:shadow-lg hover:-translate-y-0.5'
            }`}
          >
            {alreadyCheckedIn ? '✓ 今日已签到' : checkingIn ? '签到中...' : '每日签到'}
          </button>
        </div>

        {checkinResult && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 text-sm text-amber-700 bg-amber-100/60 px-3 py-2 rounded-lg whitespace-pre-line"
          >
            {checkinResult}
          </motion.p>
        )}
      </motion.div>

      {/* 成就徽章 */}
      <div className="mb-6">
        <h3 className="text-base font-semibold text-stone-800 mb-3">
          成就徽章 ({profile.unlocked_achievements.length}/{profile.all_achievements.length})
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {profile.all_achievements.map((ach, idx) => (
            <motion.div
              key={ach.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 }}
              className={`relative p-3 rounded-xl border text-center transition-all ${
                ach.is_unlocked
                  ? 'bg-white border-amber-200 shadow-sm'
                  : 'bg-stone-50 border-stone-200/60 opacity-50'
              }`}
            >
              <span className="text-2xl">{ach.icon}</span>
              <p className="text-xs font-medium text-stone-700 mt-1">{ach.name}</p>
              <p className="text-xs text-stone-400 mt-0.5">{ach.description}</p>
              {ach.is_unlocked && (
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-amber-400 rounded-full flex items-center justify-center text-xs text-white">
                  ✓
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* 积分获取规则 */}
      <div className="bg-white rounded-xl border border-stone-200/60 p-4">
        <h3 className="text-base font-semibold text-stone-800 mb-3">积分获取方式</h3>
        <div className="space-y-2 text-sm">
          {[
            { action: '发布穿搭日记', points: '+10' },
            { action: '获得社区点赞', points: '+2' },
            { action: '每日签到', points: '+5' },
            { action: '连续签到 7 天', points: '+20' },
            { action: '连续签到 30 天', points: '+50' },
          ].map((rule, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-stone-100 last:border-0">
              <span className="text-stone-600">{rule.action}</span>
              <span className="font-medium text-amber-600">{rule.points}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
