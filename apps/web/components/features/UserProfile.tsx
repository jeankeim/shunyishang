'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { Calendar, MapPin, User, Save, Loader2, X, Sparkles } from 'lucide-react'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'
import { getUserProfile, calculateBazi, updateUserBazi } from '@/lib/api'
import { cn } from '@/lib/utils'

interface UserProfileData {
  nickname: string | null
  gender: string | null
  birth_date: string | null
  birth_time: string | null
  birth_location: string | null
  preferred_city: string | null
  avatar_url: string | null
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

// 常用城市列表
const COMMON_CITIES = [
  '北京', '上海', '广州', '深圳', '杭州', '南京', '苏州', '成都', 
  '武汉', '西安', '重庆', '天津', '青岛', '大连', '厦门', '福州',
  '长沙', '郑州', '沈阳', '长春', '哈尔滨', '石家庄', '太原', '合肥',
  '南昌', '南宁', '海口', '贵阳', '昆明', '拉萨', '银川', '乌鲁木齐'
]

export function UserProfile({ onClose }: UserProfileProps) {
  const { user, isAuthenticated, updateProfile, fetchUserInfo } = useUserStore()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [fullProfile, setFullProfile] = useState<FullUserProfile | null>(null)
  const [formData, setFormData] = useState<UserProfileData>({
    nickname: '',
    gender: '',
    birth_date: '',
    birth_time: '',
    birth_location: '',
    preferred_city: '',
    avatar_url: ''
  })
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [showCityDropdown, setShowCityDropdown] = useState(false)

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
            avatar_url: profile.avatar_url || ''
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
              avatar_url: user.avatar_url || ''
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
        gender: formData.gender as '男' | '女'
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
        const currentValue = fullProfile?.[field] || ''
        if (formData[field] !== currentValue) {
          updateData[field] = formData[field] || null
        }
      })

      if (Object.keys(updateData).length === 0) {
        setMessage({ type: 'success', text: '没有需要更新的信息' })
        setTimeout(() => setMessage(null), 3000)
        return
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
      
      console.log('[UserProfile] 八字分析检查:', {
        hasBirthInfoChanged,
        hasCompleteBirthInfo,
        hasNoExistingBazi,
        birth_date: formData.birth_date,
        birth_time: formData.birth_time,
        gender: formData.gender,
        userBazi: user?.bazi
      })
      
      if ((hasBirthInfoChanged || hasNoExistingBazi) && hasCompleteBirthInfo) {
        console.log('[UserProfile] 触发八字分析')
        baziAnalyzed = await autoAnalyzeBazi()
      } else {
        console.log('[UserProfile] 未触发八字分析，条件不满足')
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
        avatar_url: fullProfile.avatar_url || ''
      })
    }
    setMessage(null)
    onClose?.()
  }

  const handleCitySelect = (city: string) => {
    handleChange('preferred_city', city)
    setShowCityDropdown(false)
  }

  const filteredCities = COMMON_CITIES.filter(city => 
    city.toLowerCase().includes(formData.preferred_city?.toLowerCase() || '')
  )

  if (!isAuthenticated || !user) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[#6B7F72]">请先登录</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-[#6B7F72]">加载中...</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto h-full overflow-y-auto bg-gradient-to-br from-stone-50 to-white">
      <div className="p-4 md:p-6 space-y-6">
        {/* 头部区域 */}
        <div className="flex justify-between items-start pb-4 border-b border-stone-200">
          <div className="flex-1">
            <h2 className="text-xl md:text-2xl font-bold flex items-center gap-3 text-stone-900">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              <div>
                <span>个人资料</span>
                <p className="text-sm font-normal text-stone-500 mt-1">
                  管理您的个人信息，用于精准的五行推荐
                </p>
              </div>
            </h2>
          </div>
          <button
            onClick={handleCancel}
            className="p-2.5 rounded-xl hover:bg-stone-100 transition-all text-stone-500 hover:text-stone-700 hover:scale-105 active:scale-95"
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
              className="mb-4 p-4 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 text-amber-700 flex items-center gap-3 shadow-sm"
            >
              <Sparkles className="h-5 w-5 animate-pulse" />
              <span className="font-medium">正在分析八字...</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 基本信息 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
              <h3 className="text-lg font-semibold text-stone-800 pb-3 mb-4 border-b border-stone-100">
                基本信息
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label htmlFor="nickname" className="block text-sm font-medium text-stone-700">
                    昵称
                  </label>
                  <input
                    id="nickname"
                    type="text"
                    value={formData.nickname || ''}
                    onChange={(e) => handleChange('nickname', e.target.value)}
                    placeholder="请输入昵称"
                    className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all hover:border-stone-300"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="gender" className="block text-sm font-medium text-stone-700">
                    性别
                  </label>
                  <select
                    id="gender"
                    value={formData.gender || ''}
                    onChange={(e) => handleChange('gender', e.target.value)}
                    className="input-elegant w-full px-3 py-2.5 text-sm text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 transition-all"
                  >
                    <option value="">请选择</option>
                    <option value="男">男</option>
                    <option value="女">女</option>
                  </select>
                </div>
              </div>
            </section>

            {/* 出生信息 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-stone-800 pb-3 mb-4 border-b border-stone-100">
                <Calendar className="h-5 w-5 text-amber-500" />
                出生信息
              </h3>
              <p className="text-sm text-stone-500 mb-5">
                完善后可用于更精确的八字分析
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-stone-700">
                    出生日期
                  </label>
                  <div className="relative">
                    <DatePicker
                      selected={formData.birth_date ? new Date(formData.birth_date) : null}
                      onChange={(date: Date | null) => {
                        handleChange('birth_date', date ? date.toISOString().split('T')[0] : '')
                      }}
                      dateFormat="yyyy/MM/dd"
                      placeholderText="请选择出生日期"
                      className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all hover:border-stone-300"
                      calendarClassName="bg-white rounded-lg shadow-lg"
                    />
                    <Calendar className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-stone-400 pointer-events-none" />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="birth_time" className="block text-sm font-medium text-stone-700">
                    出生时间
                  </label>
                  <input
                    id="birth_time"
                    type="time"
                    value={formData.birth_time || ''}
                    onChange={(e) => handleChange('birth_time', e.target.value)}
                    className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all hover:border-stone-300"
                  />
                </div>
              </div>

              <div className="space-y-2 mt-5">
                <label htmlFor="birth_location" className="block text-sm font-medium text-stone-700">
                  出生地点
                </label>
                <input
                  id="birth_location"
                  type="text"
                  value={formData.birth_location || ''}
                  onChange={(e) => handleChange('birth_location', e.target.value)}
                  placeholder="请输入出生地（省市区）"
                  className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all hover:border-stone-300"
                />
              </div>
            </section>

            {/* 偏好设置 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-stone-800 pb-3 mb-4 border-b border-stone-100">
                <MapPin className="h-5 w-5 text-emerald-500" />
                偏好设置
              </h3>
              
              <div className="space-y-2">
                <label htmlFor="preferred_city" className="block text-sm font-medium text-stone-700">
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
                    className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all hover:border-stone-300"
                  />
                  <MapPin className="absolute right-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-stone-400 pointer-events-none" />
                  
                  {/* 城市下拉选项 */}
                  {showCityDropdown && (
                    <motion.div 
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute z-20 w-full mt-2 bg-white rounded-xl shadow-lg border border-stone-200 max-h-60 overflow-auto"
                    >
                      {filteredCities.length > 0 ? (
                        filteredCities.map((city) => (
                          <button
                            key={city}
                            type="button"
                            onClick={() => handleCitySelect(city)}
                            className={cn(
                              "w-full text-left px-4 py-3 text-sm hover:bg-amber-50 transition-colors first:rounded-t-xl last:rounded-b-xl",
                              formData.preferred_city === city 
                                ? "bg-amber-50 text-amber-700 font-medium" 
                                : "text-stone-700"
                            )}
                          >
                            {city}
                          </button>
                        ))
                      ) : (
                        <div className="px-4 py-3 text-sm text-stone-500">
                          未找到匹配的城市
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              </div>
            </section>

            {/* 头像设置 */}
            <section className="bg-white rounded-2xl p-5 shadow-sm border border-stone-100">
              <h3 className="text-lg font-semibold text-stone-800 pb-3 mb-4 border-b border-stone-100">
                头像设置
              </h3>
              
              <div className="space-y-2">
                <label htmlFor="avatar_url" className="block text-sm font-medium text-stone-700">
                  头像URL
                </label>
                <input
                  id="avatar_url"
                  type="text"
                  value={formData.avatar_url || ''}
                  onChange={(e) => handleChange('avatar_url', e.target.value)}
                  placeholder="请输入头像图片链接"
                  className="w-full px-4 py-3 text-base md:text-sm rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent transition-all hover:border-stone-300"
                />
                {formData.avatar_url && (
                  <div className="mt-4 p-4 bg-stone-50 rounded-xl">
                    <p className="text-sm text-stone-600 mb-3">头像预览：</p>
                    <img 
                      src={formData.avatar_url} 
                      alt="预览头像" 
                      className="w-20 h-20 rounded-full object-cover border-2 border-white shadow-md"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = 'https://placehold.co/80x80?text=Avatar';
                      }}
                    />
                  </div>
                )}
              </div>
            </section>

            {/* 操作按钮 */}
            <div className="flex justify-end gap-3 pt-6 border-t border-stone-200">
              <button
                type="button"
                onClick={handleCancel}
                className="px-6 py-3 text-stone-600 hover:bg-stone-100 rounded-xl font-medium transition-all hover:scale-105 active:scale-95"
              >
                取消
              </button>
              <button 
                type="submit" 
                disabled={saving}
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-500 hover:to-orange-500 disabled:from-stone-300 disabled:to-stone-400 text-white rounded-xl font-medium transition-all shadow-md hover:shadow-lg hover:scale-105 active:scale-95 disabled:scale-100"
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
          </form>
        </div>
      </div>
    </div>
  )
}