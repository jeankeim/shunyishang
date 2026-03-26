'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Eye, EyeOff, User, Lock, Phone, Mail } from 'lucide-react'
import { useUserStore } from '@/store/user'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
}

type AuthMode = 'login' | 'register'
type LoginType = 'phone' | 'email'

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [loginType, setLoginType] = useState<LoginType>('phone')
  const [showPassword, setShowPassword] = useState(false)
  
  // 表单状态
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [gender, setGender] = useState<'男' | '女'>('男')
  
  const { login, loginWithEmail, register, isLoading, error, clearError } = useUserStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    try {
      if (mode === 'login') {
        if (loginType === 'phone') {
          await login(phone, password)
        } else {
          await loginWithEmail(email, password)
        }
      } else {
        await register({
          phone: phone || undefined,
          email: email || undefined,
          password,
          nickname: nickname || undefined,
          gender,
        })
      }
      onClose()
      // 重置表单
      setPhone('')
      setEmail('')
      setPassword('')
      setNickname('')
    } catch (err) {
      // 错误已在 store 中处理
    }
  }

  const switchMode = (newMode: AuthMode) => {
    setMode(newMode)
    clearError()
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-md overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 头部 */}
          <div className="flex items-center justify-between p-6 border-b border-slate-700">
            <h2 className="text-xl font-semibold text-white">
              {mode === 'login' ? '欢迎回来' : '创建账户'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-800 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>

          {/* 内容 */}
          <div className="p-6">
            {/* 标签切换 */}
            <div className="flex gap-2 mb-6 bg-slate-800 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => switchMode('login')}
                className={`flex-1 py-2 text-sm rounded-md transition-colors ${
                  mode === 'login'
                    ? 'bg-primary text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                登录
              </button>
              <button
                type="button"
                onClick={() => switchMode('register')}
                className={`flex-1 py-2 text-sm rounded-md transition-colors ${
                  mode === 'register'
                    ? 'bg-primary text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                注册
              </button>
            </div>

            {mode === 'login' ? (
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* 登录方式切换 */}
                <div className="flex gap-2 mb-4">
                  <button
                    type="button"
                    onClick={() => setLoginType('phone')}
                    className={`flex-1 py-2 text-sm rounded-lg transition-colors ${
                      loginType === 'phone'
                        ? 'bg-primary text-white'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    手机号
                  </button>
                  <button
                    type="button"
                    onClick={() => setLoginType('email')}
                    className={`flex-1 py-2 text-sm rounded-lg transition-colors ${
                      loginType === 'email'
                        ? 'bg-primary text-white'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    邮箱
                  </button>
                </div>

                {/* 手机号/邮箱输入 */}
                {loginType === 'phone' ? (
                  <div className="space-y-2">
                    <label className="text-sm text-slate-300">手机号</label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <input
                        type="tel"
                        placeholder="请输入手机号"
                        value={phone}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPhone(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                        required
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="text-sm text-slate-300">邮箱</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                      <input
                        type="email"
                        placeholder="请输入邮箱"
                        value={email}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                        required
                      />
                    </div>
                  </div>
                )}

                {/* 密码 */}
                <div className="space-y-2">
                  <label className="text-sm text-slate-300">密码</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="请输入密码"
                      value={password}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-10 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* 错误提示 */}
                {error && (
                  <div className="p-3 bg-red-500/10 text-red-400 text-sm rounded-lg">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isLoading}
                >
                  {isLoading ? '登录中...' : '登录'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* 昵称 */}
                <div className="space-y-2">
                  <label className="text-sm text-slate-300">昵称</label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      placeholder="请输入昵称（可选）"
                      value={nickname}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNickname(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>

                {/* 手机号 */}
                <div className="space-y-2">
                  <label className="text-sm text-slate-300">手机号</label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="tel"
                      placeholder="请输入手机号（手机号或邮箱至少填一个）"
                      value={phone}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPhone(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>

                {/* 邮箱 */}
                <div className="space-y-2">
                  <label className="text-sm text-slate-300">邮箱</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="email"
                      placeholder="请输入邮箱"
                      value={email}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>

                {/* 密码 */}
                <div className="space-y-2">
                  <label className="text-sm text-slate-300">密码</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="请输入密码（至少6位）"
                      value={password}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg py-2.5 pl-10 pr-10 text-white placeholder-slate-500 focus:outline-none focus:border-primary"
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* 性别 */}
                <div className="space-y-2">
                  <label className="text-sm text-slate-300">性别</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        value="男"
                        checked={gender === '男'}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGender(e.target.value as '男' | '女')}
                        className="w-4 h-4 text-primary"
                      />
                      <span className="text-slate-300">男</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        value="女"
                        checked={gender === '女'}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGender(e.target.value as '男' | '女')}
                        className="w-4 h-4 text-primary"
                      />
                      <span className="text-slate-300">女</span>
                    </label>
                  </div>
                </div>

                {/* 错误提示 */}
                {error && (
                  <div className="p-3 bg-red-500/10 text-red-400 text-sm rounded-lg">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={isLoading || (!phone && !email)}
                >
                  {isLoading ? '注册中...' : '注册'}
                </button>
              </form>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
