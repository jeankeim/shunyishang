'use client'

import { useState, useEffect, useMemo } from 'react'
import Image from 'next/image'
import { motion } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { Calendar, MapPin, User, Save, Loader2, X, Sparkles, LogOut, Compass, Sun } from 'lucide-react'
import DatePicker, { registerLocale } from 'react-datepicker'
import { zhCN } from 'date-fns/locale'
import 'react-datepicker/dist/react-datepicker.css'
import { getUserProfile, calculateBazi, updateUserBazi, deleteAccount } from '@/lib/api'
import { formatLocalDate } from '@/lib/date'
import { cn } from '@/lib/utils'
import { PreferenceRadar } from './PreferenceRadar'
import { SkinSettings } from './SkinSettings'
import { AuthModal } from './AuthModal'

// 日历纯中文化：月份/星期/头部均显示中文（2026年8月 / 日 一 二 ...）
registerLocale('zh-CN', zhCN)

interface UserProfileData {
  nickname: string | null
  gender: string | null
  birth_date: string | null
  birth_time: string | null
  birth_location: string | null
  preferred_city: string | null
  avatar_url: string | null
  skin_tone: string | null
  style_preference: string | null
  body_type: string | null
  aesthetic_tags: string[] | null
}

interface FullUserProfile extends UserProfileData {
  id: number
  user_code: string
  phone?: string
  email?: string
  bazi?: any
  xiyong_elements?: string[]
  created_at: string
  updated_at: string
}

interface UserProfileProps {
  onClose?: () => void
}

// 城市列表：优先从后端 /weather/cities 动态拉取（120+ 城市，单一数据源），
// 拉取失败时使用本地小列表兜底
const FALLBACK_CITIES = ['北京', '上海', '广州', '深圳', '杭州', '成都']

// 出生日期可选范围（模块级常量，避免每次渲染重建 Date 对象）
const MIN_BIRTH_DATE = new Date(1900, 0, 1)
const MAX_BIRTH_DATE = new Date()

// 时辰快捷选择：取各时辰中点时刻（子时取 00:00 晚子，避免跨日歧义）
const SHICHEN_OPTIONS = [
  { label: '子时 (23:00-00:59)', value: '00:00' },
  { label: '丑时 (01:00-02:59)', value: '02:00' },
  { label: '寅时 (03:00-04:59)', value: '04:00' },
  { label: '卯时 (05:00-06:59)', value: '06:00' },
  { label: '辰时 (07:00-08:59)', value: '08:00' },
  { label: '巳时 (09:00-10:59)', value: '10:00' },
  { label: '午时 (11:00-12:59)', value: '12:00' },
  { label: '未时 (13:00-14:59)', value: '14:00' },
  { label: '申时 (15:00-16:59)', value: '16:00' },
  { label: '酉时 (17:00-18:59)', value: '18:00' },
  { label: '戌时 (19:00-20:59)', value: '20:00' },
  { label: '亥时 (21:00-22:59)', value: '22:00' },
]

export function UserProfile({ onClose }: UserProfileProps) {
  const { user, isAuthenticated, updateProfile, fetchUserInfo, logout } = useUserStore()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [fullProfile, setFullProfile] = useState<FullUserProfile | null>(null)
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false)
  // 注销账号：两步确认（展开确认区 + 输入“注销”二次确认）
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [formData, setFormData] = useState<UserProfileData>({
    nickname: '',
    gender: '',
    birth_date: '',
    birth_time: '',
    birth_location: '',
    preferred_city: '',
    avatar_url: '',
    skin_tone: '',
    style_preference: '',
    body_type: '',
    aesthetic_tags: null
  })
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCityDropdown, setShowCityDropdown] = useState(false)
  // 城市列表：优先从后端 /weather/cities 动态拉取（与后端单一数据源一致）
  const [cities, setCities] = useState<string[]>(FALLBACK_CITIES)

  useEffect(() => {
    const API_BASE = typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    fetch(`${API_BASE}/api/v1/weather/weather/cities`)
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data?.cities?.length) setCities(data.cities) })
      .catch(() => {})
  }, [])
  // PIPL 敏感信息处理同意（修改出生信息时必须勾选）
  const [sensitiveConsent, setSensitiveConsent] = useState(false)

  // 获取完整用户资料（带请求去重）
  useEffect(() => {
    // 防止重复请求的标志
    let isCancelled = false
    
    const fetchFullProfile = async () => {
      if (isAuthenticated && user) {
        setLoading(true)
        try {
          const profile = await getUserProfile()
          // 如果请求被取消，不更新状态
          if (isCancelled) return
          
          setFullProfile(profile)
          setFormData({
            nickname: profile.nickname || user.nickname || '',
            gender: profile.gender || user.gender || '',
            birth_date: profile.birth_date || '',
            birth_time: profile.birth_time || '',
            birth_location: profile.birth_location || '',
            preferred_city: profile.preferred_city || '',
            avatar_url: profile.avatar_url || '',
            skin_tone: profile.skin_tone || '',
            style_preference: profile.style_preference || '',
            body_type: profile.body_type || '',
            aesthetic_tags: profile.aesthetic_tags || null
          })
        } catch (error) {
          if (isCancelled) return
          console.error('获取完整资料失败:', error)
          // 如果获取失败，使用已有的 user 数据
          if (user) {
            setFormData({
              nickname: user.nickname || '',
              gender: user.gender || '',
              birth_date: user.birth_date || '',
              birth_time: user.birth_time || '',
              birth_location: user.birth_location || '',
              preferred_city: user.preferred_city || '',
              avatar_url: user.avatar_url || '',
              skin_tone: (user as any).skin_tone || '',
              style_preference: (user as any).style_preference || '',
              body_type: (user as any).body_type || '',
              aesthetic_tags: (user as any).aesthetic_tags || null
            })
          }
          setMessage({ type: 'error', text: '获取完整资料失败，请刷新页面重试' })
        } finally {
          if (!isCancelled) {
            setLoading(false)
          }
        }
      }
    }

    fetchFullProfile()
    
    // 清理函数：标记请求已取消
    return () => {
      isCancelled = true
    }
  }, [isAuthenticated, user])

  const handleChange = (field: keyof UserProfileData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  // 审美标签切换（多选）
  const toggleAestheticTag = (tag: string) => {
    setFormData(prev => {
      const current = prev.aesthetic_tags || []
      const next = current.includes(tag)
        ? current.filter(t => t !== tag)
        : [...current, tag]
      return { ...prev, aesthetic_tags: next.length > 0 ? next : null }
    })
  }

  // 自动分析八字
  const autoAnalyzeBazi = async () => {
    if (!formData.birth_date || !formData.birth_time || !formData.gender) {
      return false
    }

    setAnalyzing(true)
    try {
      const birthDate = new Date(formData.birth_date)
      const [hours, minutes] = formData.birth_time.split(':').map(Number)
      
      // 调用八字计算API
      const baziResult = await calculateBazi({
        birth_year: birthDate.getFullYear(),
        birth_month: birthDate.getMonth() + 1,
        birth_day: birthDate.getDate(),
        birth_hour: hours,
        gender: formData.gender as '男' | '女'
      })

      // 更新用户八字到后端
      await updateUserBazi({
        birth_year: birthDate.getFullYear(),
        birth_month: birthDate.getMonth() + 1,
        birth_day: birthDate.getDate(),
        birth_hour: hours,
        gender: formData.gender as '男' | '女',
        sensitive_consent: true, // 已在保存资料时勾选敏感信息同意
      })

      // 刷新用户信息
      await fetchUserInfo()
      
      return true
    } catch (error) {
      console.error('八字分析失败:', error)
      return false
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    try {
      // 过滤掉空值，只提交有变化的字段
      const updateData: any = {}
      Object.keys(formData).forEach(key => {
        const field = key as keyof UserProfileData
        const currentValue = formData[field]
        const originalValue = fullProfile?.[field]
        // 数组类型特殊处理（aesthetic_tags）
        if (Array.isArray(currentValue) || Array.isArray(originalValue)) {
          const a = currentValue || []
          const b = originalValue || []
          if (JSON.stringify(a) !== JSON.stringify(b)) {
            updateData[field] = currentValue
          }
        } else if (currentValue !== (originalValue || '')) {
          updateData[field] = currentValue || null
        }
      })

      if (Object.keys(updateData).length === 0) {
        setMessage({ type: 'success', text: '没有需要更新的信息' })
        setTimeout(() => setMessage(null), 3000)
        return
      }

      // PIPL：修改出生信息属敏感个人信息，需单独同意
      const touchesSensitive = updateData.birth_date !== undefined ||
                               updateData.birth_time !== undefined ||
                               updateData.birth_location !== undefined
      if (touchesSensitive) {
        if (!sensitiveConsent) {
          setMessage({ type: 'error', text: '请先勾选同意将出生信息用于八字穿搭分析' })
          return
        }
        updateData.sensitive_consent = true
      }

      await updateProfile(updateData)
      
      // 自动分析八字逻辑：
      // 1. 如果用户有出生信息变更，或者
      // 2. 用户之前没有八字，但现在有完整的出生信息
      let baziAnalyzed = false
      const hasBirthInfoChanged = updateData.birth_date !== undefined || 
                                   updateData.birth_time !== undefined || 
                                   updateData.gender !== undefined
      const hasCompleteBirthInfo = formData.birth_date && formData.birth_time && formData.gender
      const hasNoExistingBazi = !user?.bazi
      
      if ((hasBirthInfoChanged || hasNoExistingBazi) && hasCompleteBirthInfo) {
        baziAnalyzed = await autoAnalyzeBazi()
      }
      
      setMessage({ 
        type: 'success', 
        text: baziAnalyzed ? '资料更新成功，八字分析已完成' : '资料更新成功' 
      })
      
      // 刷新完整资料
      const refreshedProfile = await getUserProfile()
      setFullProfile(refreshedProfile)
      
      // 3秒后清除消息
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      console.error('更新失败:', error)
      setMessage({ 
        type: 'error', 
        text: error.message || '更新失败，请稍后重试' 
      })
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    // 重置表单到初始状态
    if (fullProfile) {
      setFormData({
        nickname: fullProfile.nickname || '',
        gender: fullProfile.gender || '',
        birth_date: fullProfile.birth_date || '',
        birth_time: fullProfile.birth_time || '',
        birth_location: fullProfile.birth_location || '',
        preferred_city: fullProfile.preferred_city || '',
        avatar_url: fullProfile.avatar_url || '',
        skin_tone: fullProfile.skin_tone || '',
        style_preference: fullProfile.style_preference || '',
        body_type: fullProfile.body_type || '',
        aesthetic_tags: fullProfile.aesthetic_tags || null
      })
    }
    setMessage(null)
    onClose?.()
  }

  const handleLogout = async () => {
    try {
      await logout()
      setShowLogoutConfirm(false)
      // 强制刷新页面确保状态完全清除
      window.location.reload()
    } catch (error) {
      console.error('退出登录失败:', error)
      setMessage({ type: 'error', text: '退出登录失败，请重试' })
    }
  }

  // 注销账号（PIPL：不可逆删除全部个人数据）
  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== '注销') return
    setDeleting(true)
    try {
      await deleteAccount()
      // 后端已删除账号，清空本地状态并刷新
      await logout().catch(() => {})
      window.location.href = '/'
    } catch (error) {
      console.error('注销账号失败:', error)
      setMessage({ type: 'error', text: error instanceof Error ? error.message : '注销账号失败，请重试' })
      setDeleting(false)
    }
  }

  const handleCitySelect = (city: string) => {
    handleChange('preferred_city', city)
    setShowCityDropdown(false)
  }

  const filteredCities = cities.filter(city =>
    city.toLowerCase().includes(formData.preferred_city?.toLowerCase() || '')
  )

  // 稳定化 Date 引用：react-datepicker 的 componentDidUpdate 按引用比较 selected，
  // 若每次渲染都 new Date() 会触发 setPreSelection→setState 无限循环（React #185）
  const selectedBirthDate = useMemo(
    () => (formData.birth_date ? new Date(formData.birth_date) : null),
    [formData.birth_date]
  )

  if (!isAuthenticated || !user) {
    const valueProps = [
      { Icon: Compass, color: 'var(--wuxing-wood)', title: '八字五行 · 命理定制', desc: '精准解析你的五行喜忌' },
      { Icon: Sparkles, color: 'var(--wuxing-water)', title: 'AI 智能推荐 · 千人千面', desc: '每套搭配为你量身定制' },
      { Icon: Sun, color: 'var(--wuxing-fire)', title: '每日运势 · 顺时而搭', desc: '顺应天时，日日好运' },
    ]

    return (
      <>
        <div className="min-h-full flex items-center justify-center bg-gradient-to-br from-[var(--brand-surface)] via-white to-[#F0F7FA] px-6 py-10">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="w-full max-w-xs text-center"
          >
            {/* 品牌图标 - 采用 App 图标叶枝式样 */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1, type: 'spring', stiffness: 260, damping: 20 }}
              className="mx-auto mb-4 w-16 h-16 rounded-[22px] bg-gradient-to-br from-[#F7F5EF] to-[#ECE8DE] border border-white/70 flex items-center justify-center shadow-sm"
            >
              <span className="text-[34px] leading-none">🌿</span>
            </motion.div>

            {/* 专业背书徽章 */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1 mb-3 rounded-full bg-white/70 border border-[#3DA35D]/20 text-[11px] text-[var(--brand-body)] shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#3DA35D]" />
              传统命理 × 现代 AI
            </div>

            <h2 className="text-2xl font-bold bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] bg-clip-text text-transparent font-serif tracking-tight">
              我的个人衣橱
            </h2>
            <p className="mt-1.5 text-sm text-[var(--brand-body)] tracking-wide">
              天人合一 · 五行穿搭 · 每日灵感
            </p>

            {/* 核心价值主张 */}
            <div className="mt-6 space-y-3.5 text-left">
              {valueProps.map((p, i) => {
                const { Icon } = p
                return (
                  <motion.div
                    key={p.title}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.35 + i * 0.1 }}
                    className="flex items-center gap-3"
                  >
                    <div
                      className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
                      style={{ background: `${p.color}1A` }}
                    >
                      <Icon className="w-[18px] h-[18px]" style={{ color: p.color }} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[var(--brand-heading)] truncate">{p.title}</p>
                      <p className="text-xs text-[var(--brand-subtle)] truncate">{p.desc}</p>
                    </div>
                  </motion.div>
                )
              })}
            </div>

            {/* 登录 CTA */}
            <motion.button
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowAuthModal(true)}
              className="mt-7 w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white font-semibold text-base shadow-lg hover:shadow-xl transition-shadow"
            >
              <Sparkles className="w-5 h-5" />
              免费开启五行穿搭
            </motion.button>

            <p className="mt-3 text-xs text-[var(--brand-subtle)]">
              登录即可解锁专属于你的命理穿搭方案
            </p>
          </motion.div>
        </div>

        <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      </>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[var(--brand-subtle)]">加载中...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto h-full overflow-y-auto bg-gradient-to-br from-[var(--brand-surface)] to-white">
      <div className="p-4 md:p-6 space-y-6">
        {/* 头部区域 */}
        <div className="flex justify-between items-start pb-4 border-b border-[var(--brand-border)]/60">
          <div className="flex-1">
            <h2 className="text-xl md:text-2xl font-bold flex items-center gap-3 text-[var(--brand-heading)]">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--wuxing-wood)] to-[var(--wuxing-water)] flex items-center justify-center shadow-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              <div>
                <span>个人资料</span>
                <p className="text-sm font-normal text-[var(--brand-subtle)] mt-1">
                  管理您的个人信息，用于精准的五行推荐
                </p>
              </div>
            </h2>
          </div>
          <button
            onClick={handleCancel}
            className="p-2.5 rounded-xl hover:bg-[var(--brand-surface)] transition-all text-[var(--brand-subtle)] hover:text-[var(--brand-body)] hover:scale-105 active:scale-95"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <div>
          {message && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mb-4 p-4 rounded-xl border ${
                message.type === 'success' 
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700' 
                  : 'bg-red-50 border-red-200 text-red-700'
              }`}
            >
              {message.text}
            </motion.div>
          )}

          {/* 八字分析状态 */}
          {analyzing && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-4 rounded-xl bg-[var(--brand-surface)]/60 text-[var(--brand-body)] flex items-center gap-3 shadow-sm"
            >
              <Sparkles className="h-5 w-5 animate-pulse" />
              <span className="font-medium">正在分析八字...</span>
            </motion.div>
          )}

          <form id="profile-form" onSubmit={handleSubmit} className="space-y-6">
            {/* 基本信息 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
              <h3 className="text-lg font-semibold text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
                基本信息
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label htmlFor="nickname" className="block text-sm font-medium text-[var(--brand-body)]">
                    昵称
                  </label>
                  <input
                    id="nickname"
                    type="text"
                    value={formData.nickname || ''}
                    onChange={(e) => handleChange('nickname', e.target.value)}
                                                            placeholder="请输入昵称"
                    className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-[var(--brand-border)] bg-white text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] focus:border-transparent transition-all hover:border-[var(--wuxing-wood)]/40"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="gender" className="block text-sm font-medium text-[var(--brand-body)]">
                    性别
                  </label>
                  <select
                    id="gender"
                    value={formData.gender || ''}
                    onChange={(e) => handleChange('gender', e.target.value)}
                    className="input-elegant w-full px-3 py-2.5 text-sm text-[var(--brand-heading)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] transition-all"
                  >
                    <option value="">请选择</option>
                    <option value="男">男</option>
                    <option value="女">女</option>
                  </select>
                </div>
              </div>
            </section>

            {/* 出生信息 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
                <Calendar className="h-5 w-5 text-[var(--wuxing-earth)]" />
                出生信息
              </h3>
              <p className="text-sm text-[var(--brand-subtle)] mb-5">
                完善后可用于更精确的八字分析
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-[var(--brand-body)]">
                    出生日期
                  </label>
                  <div className="relative">
                    <DatePicker
                      selected={selectedBirthDate}
                      onChange={(date: Date | null) => {
                        // 用本地时区格式化（toISOString 按 UTC 计算，东八区会少一天）
                        handleChange('birth_date', date ? formatLocalDate(date) : '')
                      }}
                      dateFormat="yyyy/MM/dd"
                      locale="zh-CN"
                                            placeholderText="请选择出生日期"
                      // 年/月下拉选择：出生年份久远，逐月翻页不可用
                      showMonthDropdown
                      showYearDropdown
                      dropdownMode="select"
                      scrollableYearDropdown
                      yearDropdownItemNumber={100}
                      minDate={MIN_BIRTH_DATE}
                      maxDate={MAX_BIRTH_DATE}
                      className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-[var(--brand-border)] bg-white text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] focus:border-transparent transition-all hover:border-[var(--wuxing-wood)]/40"
                      calendarClassName="bg-white rounded-lg shadow-lg"
                    />
                    <Calendar className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-[var(--brand-subtle)] pointer-events-none" />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="birth_time" className="block text-sm font-medium text-[var(--brand-body)]">
                    出生时间
                  </label>
                  <input
                    id="birth_time"
                    type="time"
                    value={formData.birth_time || ''}
                                        onChange={(e) => handleChange('birth_time', e.target.value)}
                    className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-[var(--brand-border)] bg-white text-[var(--brand-heading)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] focus:border-transparent transition-all hover:border-[var(--wuxing-wood)]/40"
                  />
                  {/* 时辰快捷选择：八字场景下用户多只记得时辰，选中后填充对应中点时刻 */}
                  <select
                    aria-label="时辰快捷选择"
                    value={SHICHEN_OPTIONS.find(o => o.value === formData.birth_time)?.value ?? ''}
                    onChange={(e) => { if (e.target.value) handleChange('birth_time', e.target.value) }}
                    className="w-full mt-2 px-3 py-2 text-xs rounded-lg border border-[var(--brand-border)] bg-[var(--brand-surface)]/40 text-[var(--brand-body)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] transition-all"
                  >
                    <option value="">不确定具体几点？按时辰快捷选择</option>
                    {SHICHEN_OPTIONS.map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2 mt-5">
                <label htmlFor="birth_location" className="block text-sm font-medium text-[var(--brand-body)]">
                  出生地点
                </label>
                <input
                  id="birth_location"
                  type="text"
                  value={formData.birth_location || ''}
                  onChange={(e) => handleChange('birth_location', e.target.value)}
                                    placeholder="请输入出生地（省市区）"
                  className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-[var(--brand-border)] bg-white text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] focus:border-transparent transition-all hover:border-[var(--wuxing-wood)]/40"
                />
              </div>

              {/* PIPL 敏感信息单独同意 */}
              <label className="flex items-start gap-2 mt-5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={sensitiveConsent}
                  onChange={(e) => setSensitiveConsent(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-[var(--wuxing-wood)]"
                />
                <span className="text-xs text-[var(--brand-subtle)] leading-relaxed">
                  我同意将出生日期、时辰、地点（敏感个人信息）用于八字穿搭分析，详见
                  <a
                    href="/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--wuxing-wood)] hover:underline mx-0.5"
                  >
                    《隐私政策》
                  </a>
                  （修改出生信息时必勾）
                </span>
              </label>
            </section>

            {/* 偏好设置 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
                <MapPin className="h-5 w-5 text-[var(--wuxing-wood)]" />
                偏好设置
              </h3>
              
              <div className="space-y-2">
                <label htmlFor="preferred_city" className="block text-sm font-medium text-[var(--brand-body)]">
                  常驻城市
                </label>
                <div className="relative">
                  <input
                    id="preferred_city"
                    type="text"
                    value={formData.preferred_city || ''}
                    onChange={(e) => {
                      handleChange('preferred_city', e.target.value)
                      setShowCityDropdown(true)
                    }}
                    onFocus={() => setShowCityDropdown(true)}
                                        placeholder="请输入或选择城市"
                    className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-[var(--brand-border)] bg-white text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] focus:border-transparent transition-all hover:border-[var(--wuxing-wood)]/40"
                  />
                  <MapPin className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-[var(--brand-subtle)] pointer-events-none" />
                  
                  {/* 城市下拉选项 */}
                  {showCityDropdown && (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute z-20 w-full mt-2 bg-white rounded-xl shadow-lg border border-[var(--brand-border)] max-h-60 overflow-auto"
                    >
                      {filteredCities.length > 0 ? (
                        filteredCities.map((city) => (
                          <button
                            key={city}
                            type="button"
                            onClick={() => handleCitySelect(city)}
                            className={cn(
                              "w-full text-left px-4 py-3 text-sm hover:bg-[var(--brand-surface)]/60 transition-colors first:rounded-t-xl last:rounded-b-xl",
                              formData.preferred_city === city 
                                ? "bg-[var(--brand-surface)] text-[var(--wuxing-wood)] font-medium" 
                                : "text-[var(--brand-body)]"
                            )}
                          >
                            {city}
                          </button>
                        ))
                      ) : (
                        <div className="px-4 py-3 text-sm text-[var(--brand-subtle)]">
                          未找到匹配的城市
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              </div>
            </section>

            {/* 偏好画像（雷达图） */}
            <PreferenceRadar />

            {/* 审美偏好（渐进式收集，非强制填写） */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
                <Sparkles className="h-5 w-5 text-[var(--wuxing-fire)]" />
                审美偏好
              </h3>
              <p className="text-sm text-[var(--brand-subtle)] mb-5">
                选填，帮助我们为您推荐更贴合个人风格的穿搭
              </p>

              {/* 肤色选择器 */}
              <div className="space-y-3 mb-6">
                <label className="block text-sm font-medium text-[var(--brand-body)]">
                  肤色类型
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {[
                    { value: '冷白皮', color: 'bg-[#FDE8E0]', label: '冷白皮' },
                    { value: '暖白皮', color: 'bg-[#FCEBD2]', label: '暖白皮' },
                    { value: '自然色', color: 'bg-[#E8C9A0]', label: '自然色' },
                    { value: '小麦色', color: 'bg-[#C49A6C]', label: '小麦色' },
                    { value: '黑皮',   color: 'bg-[#8B6348]', label: '黑皮' },
                  ].map(tone => (
                    <button
                      key={tone.value}
                      type="button"
                      onClick={() => handleChange('skin_tone', formData.skin_tone === tone.value ? '' : tone.value)}
                      className={cn(
                        'flex flex-col items-center gap-1.5 p-2.5 rounded-xl border-2 transition-all hover:scale-105 active:scale-95',
                        formData.skin_tone === tone.value
                          ? 'border-[var(--wuxing-wood)] bg-[var(--brand-surface)]/60 shadow-sm'
                          : 'border-transparent hover:border-[var(--brand-border)]'
                      )}
                    >
                      <div className={cn('w-8 h-8 rounded-full shadow-inner border border-white/60', tone.color)} />
                      <span className="text-xs font-medium text-[var(--brand-body)]">{tone.label}</span>
                    </button>
                  ))}
                </div>
                {formData.skin_tone && (
                  <p className="text-xs text-[var(--brand-subtle)]">
                    {formData.skin_tone === '冷白皮' && '适合冷色调（蓝/紫/银灰），推荐金、水元素服饰'}
                    {formData.skin_tone === '暖白皮' && '适合暖色调（橙/黄/米色），推荐火、土元素服饰'}
                    {formData.skin_tone === '自然色' && '适合中性色调，多数颜色均可驾驭'}
                    {formData.skin_tone === '小麦色' && '适合大地色系、高饱和度，推荐土、火元素服饰'}
                    {formData.skin_tone === '黑皮' && '适合亮色系、金属色，推荐金、火元素服饰'}
                  </p>
                )}
              </div>

              {/* 风格偏好多选标签 */}
              <div className="space-y-3 mb-6">
                <label className="block text-sm font-medium text-[var(--brand-body)]">
                  风格偏好
                  <span className="text-xs text-[var(--brand-subtle)] ml-2">（可多选）</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {['简约', '韩系', '日系', '国潮', '复古', '商务', '休闲', '运动', '文艺', '森系', '法式', '中式'].map(style => (
                    <button
                      key={style}
                      type="button"
                      onClick={() => {
                        const current = formData.aesthetic_tags || []
                        // 风格标签存为 "style:简约" 格式，便于后续扩展
                        const tag = `style:${style}`
                        toggleAestheticTag(tag)
                        // 同时更新 style_preference 字段（取第一个选中的风格）
                        const next = current.includes(tag)
                          ? current.filter(t => t !== tag)
                          : [...current, tag]
                        const styleTags = next.filter(t => t.startsWith('style:'))
                        handleChange('style_preference', styleTags.length > 0 ? styleTags[0].replace('style:', '') : '')
                      }}
                      className={cn(
                        'px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all hover:scale-105 active:scale-95',
                        (formData.aesthetic_tags || []).includes(`style:${style}`)
                          ? 'bg-[var(--wuxing-wood)] text-white border-[var(--wuxing-wood)] shadow-sm'
                          : 'bg-white text-[var(--brand-body)] border-[var(--brand-border)] hover:border-[var(--wuxing-wood)]/40'
                      )}
                    >
                      {style}
                    </button>
                  ))}
                </div>
              </div>

              {/* 体型选择 */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-[var(--brand-body)]">
                  体型
                </label>
                <div className="flex gap-2">
                  {['偏瘦', '标准', '偏胖'].map(bt => (
                    <button
                      key={bt}
                      type="button"
                      onClick={() => handleChange('body_type', formData.body_type === bt ? '' : bt)}
                      className={cn(
                        'flex-1 py-2.5 rounded-xl text-sm font-medium border-2 transition-all hover:scale-105 active:scale-95',
                        formData.body_type === bt
                          ? 'border-[var(--wuxing-wood)] bg-[var(--brand-surface)]/60 text-[var(--brand-heading)] shadow-sm'
                          : 'border-transparent bg-[var(--brand-surface)]/30 text-[var(--brand-body)] hover:border-[var(--brand-border)]'
                      )}
                    >
                      {bt}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* 头像设置 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-[var(--brand-border)]/40">
              <h3 className="text-lg font-semibold text-[var(--brand-heading)] pb-3 mb-4 border-b border-[var(--brand-border)]/40">
                头像设置
              </h3>
              
              <div className="space-y-2">
                <label htmlFor="avatar_url" className="block text-sm font-medium text-[var(--brand-body)]">
                  头像URL
                </label>
                <input
                  id="avatar_url"
                  type="text"
                  value={formData.avatar_url || ''}
                  onChange={(e) => handleChange('avatar_url', e.target.value)}
                                    placeholder="请输入头像图片链接"
                  className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-[var(--brand-border)] bg-white text-[var(--brand-heading)] placeholder:text-[var(--brand-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--wuxing-wood)] focus:border-transparent transition-all hover:border-[var(--wuxing-wood)]/40"
                />
                {formData.avatar_url && (
                  <div className="mt-4 p-4 bg-[var(--brand-surface)] rounded-xl">
                    <p className="text-sm text-[var(--brand-subtle)] mb-3">头像预览：</p>
                    <Image
                      src={formData.avatar_url}
                      alt="预览头像"
                      width={80}
                      height={80}
                      unoptimized
                      className="w-20 h-20 rounded-full object-cover border-2 border-white shadow-md"
                      onError={(e) => {
                        const target = e.currentTarget as HTMLImageElement;
                        target.src = 'https://placehold.co/80x80?text=Avatar';
                      }}
                    />
                  </div>
                )}
              </div>
            </section>

          </form>

          {/* 应用设置 - 皮肤切换 */}
          <div className="mt-6">
            <SkinSettings />
          </div>

          {/* 操作按钮 - 保存 / 取消 */}
          <div className="flex justify-end gap-3 pt-6 mt-6 border-t border-[var(--brand-border)]/60">
            <button
              type="button"
              onClick={handleCancel}
              className="px-6 py-3 text-[var(--brand-subtle)] hover:bg-[var(--brand-surface)] rounded-xl font-medium transition-all hover:scale-105 active:scale-95"
            >
              取消
            </button>
            <button
              type="submit"
              form="profile-form"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] hover:opacity-90 disabled:from-stone-300 disabled:to-stone-400 text-white rounded-xl font-medium transition-all shadow-md hover:shadow-lg hover:scale-105 active:scale-95 disabled:scale-100"
            >
              {saving ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="h-5 w-5" />
                  保存更改
                </>
              )}
            </button>
          </div>

          {/* 退出登录 */}
          <div className="pt-6 mt-6 border-t border-[var(--brand-border)]/60">
            {showLogoutConfirm ? (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50/80 rounded-xl p-4 border border-red-200/60"
              >
                <p className="text-sm text-red-700 mb-3 font-medium">确认退出登录？</p>
                <div className="flex gap-2">
                  <button
                    onClick={handleLogout}
                    className="flex-1 px-4 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm rounded-xl font-medium transition-all active:scale-95"
                  >
                    确认退出
                  </button>
                  <button
                    onClick={() => setShowLogoutConfirm(false)}
                    className="flex-1 px-4 py-2.5 bg-white hover:bg-stone-50 text-stone-600 text-sm rounded-xl font-medium border border-stone-200 transition-all active:scale-95"
                  >
                    取消
                  </button>
                </div>
              </motion.div>
            ) : (
              <button
                type="button"
                onClick={() => setShowLogoutConfirm(true)}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 text-red-500 hover:bg-red-50 hover:text-red-600 rounded-xl font-medium transition-all active:scale-95 border border-red-200/40"
              >
                <LogOut className="h-4 w-4" />
                退出登录
              </button>
            )}
          </div>

          {/* 注销账号（PIPL 删除权入口） */}
          <div className="pt-4 mt-4">
            {showDeleteConfirm ? (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50/80 rounded-xl p-4 border border-red-200/60"
              >
                <p className="text-sm text-red-700 font-medium mb-2">注销账号后将立即且不可恢复地删除：</p>
                <ul className="text-xs text-red-600/90 list-disc pl-4 space-y-0.5 mb-3">
                  <li>账号信息与出生信息（含八字分析结果）</li>
                  <li>衣橱数据及上传的全部照片</li>
                  <li>穿搭日记、收藏与历史推荐记录</li>
                </ul>
                <input
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  placeholder='请输入“注销”以确认'
                  className="w-full px-3 py-2.5 mb-3 text-sm rounded-xl border border-red-200 bg-white text-red-700 placeholder:text-red-300 focus:outline-none focus:ring-2 focus:ring-red-400"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleDeleteAccount}
                    disabled={deleteConfirmText !== '注销' || deleting}
                    className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 disabled:bg-red-300 disabled:cursor-not-allowed text-white text-sm rounded-xl font-medium transition-all active:scale-95"
                  >
                    {deleting ? '注销中...' : '确认永久注销'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowDeleteConfirm(false)
                      setDeleteConfirmText('')
                    }}
                    className="flex-1 px-4 py-2.5 bg-white hover:bg-stone-50 text-stone-600 text-sm rounded-xl font-medium border border-stone-200 transition-all active:scale-95"
                  >
                    取消
                  </button>
                </div>
              </motion.div>
            ) : (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full text-center text-xs text-[var(--brand-subtle)] hover:text-red-500 transition-colors py-2"
              >
                注销账号（彻底删除全部个人数据）
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}