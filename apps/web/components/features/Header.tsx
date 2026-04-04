'use client'

import { useState, useEffect } from 'react'
import { useTheme } from '@/hooks/useTheme'
import { useUserStore } from '@/store/user'
import { Leaf, User, LogOut, Settings, X, Menu } from 'lucide-react'
import { motion } from 'framer-motion'
import { AuthModal } from './AuthModal'

interface HeaderProps {
  sidebarCollapsed?: boolean
  onToggleSidebar?: () => void
}

export function Header({ sidebarCollapsed, onToggleSidebar }: HeaderProps) {
  const { currentTerm, mounted } = useTheme()
  const { user, isAuthenticated, logout, fetchUserInfo } = useUserStore()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)

  // 初始化时获取用户信息（仅在首次挂载时执行一次）
  useEffect(() => {
    // 初始化 token
    const token = localStorage.getItem('wuxing_token')
    if (token && !isAuthenticated) {
      fetchUserInfo()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // 空依赖，只在挂载时执行一次

  const handleLogout = async () => {
    try {
      await logout()
      setShowUserMenu(false)
      // 强制刷新页面确保状态完全清除
      window.location.reload()
    } catch (error) {
      console.error('退出登录失败:', error)
    }
  }

  if (!mounted) {
    return (
      <header className="h-[60px] border-b border-[#E8F0EB]/50 flex items-center justify-between px-4 bg-white/90 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#3DA35D]/20 to-[#4A90C4]/20 flex items-center justify-center shadow-sm">
            <Leaf className="w-5 h-5 text-[#3DA35D]" />
          </div>
          <h1 className="font-semibold text-[#2D4A38] bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] bg-clip-text text-transparent font-serif">顺衣尚</h1>
        </div>
      </header>
    )
  }

  return (
    <>
      <header className="h-[60px] flex items-center justify-between px-4 bg-white/90 backdrop-blur-xl relative z-10 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
        <div className="flex items-center gap-3">
          {/* 菜单按钮 - 点击打开/关闭聊天记录 */}
          <motion.button
            onClick={onToggleSidebar}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="p-2 rounded-lg hover:bg-[#F0F7F4] transition-colors duration-200"
            title="聊天记录"
            aria-label="切换侧边栏"
          >
            <Menu className="h-5 w-5 text-[#4A5F52]" />
          </motion.button>
          {/* 顺衣尚 Logo */}
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#3DA35D]/20 to-[#4A90C4]/20 flex items-center justify-center shadow-sm">
              <Leaf className="w-5 h-5 text-[#3DA35D]" />
            </div>
            <h1 className="font-semibold text-[#2D4A38] text-lg bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] bg-clip-text text-transparent font-serif tracking-tight">顺衣尚</h1>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* 节气显示 */}
          {currentTerm && (
            <motion.div 
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="hidden sm:flex items-center gap-2 text-sm text-[#5A7A66]"
            >
              <Leaf className="h-4 w-4" style={{ color: currentTerm.primaryColor }} />
              <span>当前节气: {currentTerm.name}</span>
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: currentTerm.primaryColor }}
              />
            </motion.div>
          )}

          {/* 用户菜单 */}
          {isAuthenticated && user ? (
            <div className="relative">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-[#F0F7F4] to-[#E8F5EC] hover:from-[#E8F5EC] hover:to-[#D4E8DC] transition-all duration-200 shadow-sm border border-[#E8F0EB]/60"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#3DA35D] to-[#4A90C4] flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <span className="text-sm text-[#2D4A38] hidden sm:inline font-medium">
                  {user.nickname || user.phone || user.email || '用户'}
                </span>
              </motion.button>
            </div>
          ) : (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowAuthModal(true)}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] hover:from-[#359454] hover:to-[#3F84B5] text-white text-sm font-medium transition-all duration-200 shadow-sm hover:shadow-md"
            >
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">登录</span>
            </motion.button>
          )}
        </div>
      </header>

      {/* 用户菜单弹窗 - 使用固定定位 */}
      {showUserMenu && isAuthenticated && user && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[9998]"
          onClick={() => setShowUserMenu(false)}
        >
          <motion.div 
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className="absolute right-4 top-[70px] w-56 bg-white/95 backdrop-blur-xl border border-[#E8F0EB]/60 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.08)] py-1"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 border-b border-[#E8F0EB]/50 flex justify-between items-start">
              <div>
                <p className="text-sm text-[#2D4A38] font-semibold">{user.nickname || '用户'}</p>
                <p className="text-xs text-[#6B7F72] truncate mt-0.5">
                  {user.phone || user.email}
                </p>
              </div>
              <motion.button 
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setShowUserMenu(false)}
                className="text-[#8A9F92] hover:text-[#4A5F52] transition-colors p-0.5"
                aria-label="关闭菜单"
              >
                <X className="w-4 h-4" />
              </motion.button>
            </div>
            <motion.button
              whileHover={{ x: 2 }}
              onClick={() => {
                setShowUserMenu(false)
                // 跳转到用户资料页面
                window.location.hash = '#profile'
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm text-[#2D4A38] hover:bg-[#F0F7F4] transition-colors cursor-pointer"
            >
              <Settings className="w-4 h-4 text-[#5A7A66]" />
              <span className="font-medium">个人中心</span>
            </motion.button>
            <motion.button
              whileHover={{ x: 2 }}
              onClick={() => {
                setShowUserMenu(false)
                handleLogout()
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm text-[#D4656B] hover:bg-[#FDF2F2] transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span className="font-medium">退出登录</span>
            </motion.button>
          </motion.div>
        </motion.div>
      )}

      {/* 认证弹窗 */}
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
    </>
  )
}
