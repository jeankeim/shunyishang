'use client'

import { useEffect, useState, useMemo } from 'react'
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

// 里程碑配置
const STREAK_MILESTONES = [
  { days: 3, icon: '💪', label: '坚持3天', reward: 0 },
  { days: 7, icon: '🌟', label: '7天连续', reward: 20 },
  { days: 14, icon: '🔥', label: '14天达人', reward: 0 },
  { days: 30, icon: '👑', label: '30天大师', reward: 50 },
  { days: 60, icon: '🏆', label: '60天传奇', reward: 0 },
  { days: 100, icon: '💎', label: '100天神话', reward: 100 },
]

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

  const today = new Date().toISOString().split('T')[0]
  const alreadyCheckedIn = !!profile && profile.last_checkin_date === today

  // 计算下一个里程碑（必须在提前 return 之前，保证 hooks 调用顺序稳定）
  const nextMilestone = useMemo(() => {
    if (!profile) return null
    return STREAK_MILESTONES.find(m => m.days > profile.streak_days) || null
  }, [profile])

  // 计算最近一个未解锁成就
  const nextAchievement = useMemo(() => {
    if (!profile) return null
    const locked = profile.all_achievements.filter(a => !a.is_unlocked)
    if (locked.length === 0) return null
    // 按 requirement_value 升序排列，找到最近的一个
    locked.sort((a, b) => a.requirement_value - b.requirement_value)
    return locked[0]
  }, [profile])

  // 过去7天日历数据
  const weekDays = useMemo(() => {
    const weekdays = ['一', '二', '三', '四', '五', '六', '日']
    const now = new Date()
    const streak = profile?.streak_days ?? 0
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(now)
      d.setDate(now.getDate() - (6 - i))
      const dayIndex = (d.getDay() + 6) % 7
      return {
        date: d,
        dayLabel: weekdays[dayIndex],
        isToday: i === 6,
        isCheckedIn: i >= 6 - streak + 1 && (alreadyCheckedIn || i < 6),
      }
    })
  }, [profile, alreadyCheckedIn])

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

      {/* ── 连续打卡日历 + 里程碑 ──────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* 7日打卡日历 */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl border border-stone-200/60 p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-stone-700">📅 近7日打卡</h3>
            <span className="text-xs text-stone-400">连续 {profile.streak_days} 天</span>
          </div>
          <div className="flex justify-between items-center">
            {weekDays.map((day, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <span className="text-[10px] text-stone-400">{day.dayLabel}</span>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
                    day.isCheckedIn
                      ? 'bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-sm'
                      : day.isToday
                        ? 'bg-amber-50 border-2 border-amber-300 text-amber-500'
                        : 'bg-stone-100 text-stone-300'
                  }`}
                >
                  {day.isCheckedIn ? '✓' : day.isToday ? '今' : '·'}
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* 下一个里程碑 */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-white rounded-xl border border-stone-200/60 p-4"
        >
          <h3 className="text-sm font-semibold text-stone-700 mb-3">🎯 打卡里程碑</h3>
          {nextMilestone ? (
            <>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{nextMilestone.icon}</span>
                <div className="flex-1">
                  <p className="text-sm font-medium text-stone-700">{nextMilestone.label}</p>
                  <p className="text-xs text-stone-500">
                    还需 {nextMilestone.days - profile.streak_days} 天
                    {nextMilestone.reward > 0 && ` · 奖励 +${nextMilestone.reward} 积分`}
                  </p>
                </div>
              </div>
              <div className="h-2 bg-stone-100 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, (profile.streak_days / nextMilestone.days) * 100)}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  className="h-full bg-gradient-to-r from-amber-400 to-orange-400 rounded-full"
                />
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-2xl">🎉</span>
              <div>
                <p className="text-sm font-medium text-stone-700">全部里程碑已达成！</p>
                <p className="text-xs text-stone-500">你是穿搭修炼的传奇</p>
              </div>
            </div>
          )}

          {/* 里程碑节点 */}
          <div className="flex justify-between mt-3 pt-3 border-t border-stone-100">
            {STREAK_MILESTONES.slice(0, 5).map((m, i) => {
              const achieved = profile.streak_days >= m.days
              return (
                <div key={i} className="flex flex-col items-center gap-0.5">
                  <span className={`text-xs ${achieved ? '' : 'opacity-30'}`}>{m.icon}</span>
                  <span className={`text-[10px] ${achieved ? 'text-amber-600 font-medium' : 'text-stone-300'}`}>
                    {m.days}天
                  </span>
                  {achieved && <div className="w-1 h-1 rounded-full bg-amber-400" />}
                </div>
              )
            })}
          </div>
        </motion.div>
      </div>

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

      {/* 下一个成就进度 */}
      {nextAchievement && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl border border-stone-200/60 p-4 mb-6"
        >
          <h3 className="text-sm font-semibold text-stone-700 mb-3">🎖️ 下一个成就</h3>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{nextAchievement.icon}</span>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-stone-700">{nextAchievement.name}</span>
                <span className="text-xs text-amber-600">+{nextAchievement.points_reward} 积分</span>
              </div>
              <p className="text-xs text-stone-500">
                {nextAchievement.description}
                <span className="text-stone-400"> · 需要 {nextAchievement.requirement_value} 次，继续加油！</span>
              </p>
            </div>
          </div>
        </motion.div>
      )}

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
