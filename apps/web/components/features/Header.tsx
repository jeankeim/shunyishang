'use client'

import { useState, useEffect } from 'react'
import { useTheme } from '@/hooks/useTheme'
import { useUserStore } from '@/store/user'
import { Leaf, User, LogOut, Settings, X, Menu } from 'lucide-react'
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
      <header className="h-[60px] border-b border-amber-200/30 flex items-center justify-between px-4 bg-gradient-to-r from-amber-50/80 to-orange-50/60 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-200/80 to-orange-200/60 flex items-center justify-center shadow-sm">
            <span className="text-xl">🌿</span>
          </div>
          <h1 className="font-semibold text-stone-700 bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">顺衣裳</h1>
        </div>
      </header>
    )
  }

  return (
    <>
      <header className="h-[60px] border-b border-amber-200/30 flex items-center justify-between px-4 bg-gradient-to-r from-amber-50/80 to-orange-50/60 backdrop-blur-sm relative z-10">
        <div className="flex items-center gap-3">
          {/* 菜单按钮 - 点击打开/关闭聊天记录 */}
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg hover:bg-amber-100/60 transition-colors"
            title="聊天记录"
          >
            <Menu className="h-5 w-5 text-stone-600" />
          </button>
          {/* 顺衣裳 Logo */}
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-200/80 to-orange-200/60 flex items-center justify-center shadow-sm">
              <span className="text-xl">🌿</span>
            </div>
            <h1 className="font-semibold text-stone-700 text-lg bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">顺衣裳</h1>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* 节气显示 */}
          {currentTerm && (
            <div className="hidden sm:flex items-center gap-2 text-sm text-stone-600">
              <Leaf className="h-4 w-4" style={{ color: currentTerm.primaryColor }} />
              <span>当前节气: {currentTerm.name}</span>
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: currentTerm.primaryColor }}
              />
            </div>
          )}

          {/* 用户菜单 */}
          {isAuthenticated && user ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-100/60 to-orange-100/40 hover:from-amber-200/60 hover:to-orange-200/40 transition-all shadow-sm border border-amber-200/30"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-amber-300 to-orange-300 flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <span className="text-sm text-stone-700 hidden sm:inline">
                  {user.nickname || user.phone || user.email || '用户'}
                </span>
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-500 hover:to-orange-500 text-white text-sm font-medium transition-all shadow-sm hover:shadow-md"
            >
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">登录</span>
            </button>
          )}
        </div>
      </header>

      {/* 用户菜单弹窗 - 使用固定定位 */}
      {showUserMenu && isAuthenticated && user && (
        <div 
          className="fixed inset-0 z-[9998]"
          onClick={() => setShowUserMenu(false)}
        >
          <div 
            className="absolute right-4 top-[70px] w-48 bg-white/80 backdrop-blur-md border border-amber-200/30 rounded-xl shadow-xl py-1"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-2 border-b border-amber-200/20 flex justify-between items-center">
              <div>
                <p className="text-sm text-stone-700 font-medium">{user.nickname || '用户'}</p>
                <p className="text-xs text-stone-500 truncate">
                  {user.phone || user.email}
                </p>
              </div>
              <button 
                onClick={() => setShowUserMenu(false)}
                className="text-stone-400 hover:text-stone-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div
              onClick={() => {
                setShowUserMenu(false)
                // 跳转到用户资料页面
                window.location.hash = '#profile'
              }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-stone-700 hover:bg-amber-50/60 transition-colors cursor-pointer"
            >
              <Settings className="w-4 h-4" />
              个人中心
            </div>
            <div
              onClick={() => {
                setShowUserMenu(false)
                handleLogout()
              }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50/60 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              退出登录
            </div>
          </div>
        </div>
      )}

      {/* 认证弹窗 */}
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
    </>
  )
}
