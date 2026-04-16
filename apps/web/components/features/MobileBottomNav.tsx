'use client'

import { motion } from 'framer-motion'

interface MobileBottomNavProps {
  activeTab: 'chat' | 'wardrobe' | 'profile'
  onTabChange: (tab: 'chat' | 'wardrobe' | 'profile') => void
}

export function MobileBottomNav({ activeTab, onTabChange }: MobileBottomNavProps) {
  const navItems = [
    { 
      id: 'chat' as const, 
      icon: '✨', 
      label: '推荐',
      color: 'from-[#3DA35D] to-[#4A90C4]'
    },
    { 
      id: 'wardrobe' as const, 
      icon: '👔', 
      label: '衣橱',
      color: 'from-[#D4656B] to-[#B89B5E]'
    },
    { 
      id: 'profile' as const, 
      icon: '👤', 
      label: '我的',
      color: 'from-[#4A90C4] to-[#3DA35D]'
    },
  ]

  return (
    <nav 
      className="md:hidden fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-xl border-t border-stone-200/60 safe-area-bottom z-50"
      role="navigation"
      aria-label="移动端主导航"
    >
      <div className="flex justify-around items-center h-16 px-2">
        {navItems.map((item) => {
          const isActive = activeTab === item.id
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              aria-label={`切换到${item.label}页面`}
              aria-current={isActive ? 'page' : undefined}
              className={`relative flex flex-col items-center justify-center min-w-[64px] min-h-[48px] gap-1 transition-all duration-200 touch-feedback ${
                isActive ? 'text-[#3DA35D]' : 'text-stone-500'
              }`}
            >
              {/* 顶部指示器 */}
              {isActive && (
                <motion.div
                  layoutId="bottomNavIndicator"
                  className="absolute -top-px left-1/2 -translate-x-1/2 w-12 h-0.5 rounded-full"
                  style={{
                    background: `linear-gradient(to right, var(--tw-gradient-stops))`,
                  }}
                  initial={false}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              )}
              
              {/* 图标 */}
              <motion.span 
                className="text-xl"
                aria-hidden="true"
                animate={isActive ? { scale: 1.1 } : { scale: 1 }}
                transition={{ duration: 0.2 }}
              >
                {item.icon}
              </motion.span>
              
              {/* 标签 */}
              <span className={`text-xs font-medium transition-all duration-200 ${
                isActive ? 'text-[#3DA35D]' : 'text-stone-500'
              }`}>
                {item.label}
              </span>
              
              {/* 激活背景 */}
              {isActive && (
                <motion.div
                  className="absolute inset-0 rounded-xl"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.08 }}
                  style={{
                    background: `linear-gradient(135deg, #3DA35D20, #4A90C420)`,
                  }}
                />
              )}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
