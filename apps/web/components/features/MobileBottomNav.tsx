'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Shirt, Users, User, Menu, Scan, BookOpen, Compass, CircleDot, Mountain } from 'lucide-react'

type TabId = 'chat' | 'wardrobe' | 'tryon' | 'profile' | 'diary' | 'fortune' | 'destiny' | 'community' | 'cultivation'

interface MobileBottomNavProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
}

// 主导航（4个）：推荐 | 衣橱 | 广场 | 我的
const PRIMARY_ITEMS = [
  { id: 'chat' as const, Icon: Sparkles, label: '推荐' },
  { id: 'wardrobe' as const, Icon: Shirt, label: '衣橱' },
  { id: 'community' as const, Icon: Users, label: '广场' },
  { id: 'profile' as const, Icon: User, label: '我的' },
]

// 次级功能（通过"更多"展开）：试衣 | 日记 | 运势 | 命理 | 修炼
const SECONDARY_ITEMS = [
  { id: 'tryon' as const, Icon: Scan, label: '试衣' },
  { id: 'diary' as const, Icon: BookOpen, label: '日记' },
  { id: 'fortune' as const, Icon: Compass, label: '运势' },
  { id: 'destiny' as const, Icon: CircleDot, label: '命理' },
  { id: 'cultivation' as const, Icon: Mountain, label: '修炼' },
]

const SECONDARY_IDS: TabId[] = SECONDARY_ITEMS.map(i => i.id)

export function MobileBottomNav({ activeTab, onTabChange }: MobileBottomNavProps) {
  const [showMore, setShowMore] = useState(false)

  const isSecondaryActive = SECONDARY_IDS.includes(activeTab)
  const isMoreActive = showMore || isSecondaryActive

  const handlePrimaryClick = (id: TabId) => {
    setShowMore(false)
    onTabChange(id)
  }

  const handleSecondaryClick = (id: TabId) => {
    setShowMore(false)
    onTabChange(id)
  }

  return (
    <>
      {/* 更多 — 底部弹出Sheet */}
      <AnimatePresence>
        {showMore && (
          <>
            {/* 遮罩层 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowMore(false)}
              className="md:hidden fixed inset-0 bg-black/40 z-[60]"
            />
            {/* Sheet主体 */}
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 400, damping: 35 }}
              className="md:hidden fixed bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl z-[60] pb-safe"
            >
              {/* 拖拽指示器 */}
              <div className="flex justify-center pt-3 pb-1">
                <div className="w-10 h-1 bg-stone-300 rounded-full" />
              </div>
              <div className="px-6 pb-6 pt-2">
                <h3 className="text-sm font-semibold text-stone-400 mb-4">更多功能</h3>
                <div className="grid grid-cols-5 gap-2">
                  {SECONDARY_ITEMS.map((item) => {
                    const isActive = activeTab === item.id
                    const { Icon } = item
                    return (
                      <button
                        key={item.id}
                        onClick={() => handleSecondaryClick(item.id)}
                        aria-label={`切换到${item.label}页面`}
                        className="flex flex-col items-center gap-2 py-3 px-1 rounded-xl active:bg-stone-100 transition-colors"
                      >
                        <Icon className={`w-6 h-6 transition-transform ${isActive ? 'scale-110 text-[hsl(var(--primary))]' : 'text-stone-500'}`} />
                        <span className={`text-xs font-medium ${isActive ? 'text-[hsl(var(--primary))]' : 'text-stone-600'}`}>
                          {item.label}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-xl border-t border-stone-200/60 safe-area-bottom z-50"
        role="navigation"
        aria-label="移动端主导航"
      >
        <div className="flex justify-around items-center h-16 px-1">
          {/* 主Tab */}
          {PRIMARY_ITEMS.map((item) => {
            const isActive = activeTab === item.id
            const { Icon } = item
            return (
              <button
                key={item.id}
                onClick={() => handlePrimaryClick(item.id)}
                aria-label={`切换到${item.label}页面`}
                aria-current={isActive ? 'page' : undefined}
                className={`relative flex flex-col items-center justify-center min-w-[48px] min-h-[48px] gap-0.5 transition-all duration-200 touch-feedback ${
                  isActive ? 'text-[hsl(var(--primary))]' : 'text-stone-500'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="bottomNavIndicator"
                    className="absolute -top-px left-1/2 -translate-x-1/2 w-12 h-0.5 rounded-full bg-[hsl(var(--primary))]"
                    initial={false}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}
                <motion.div
                  aria-hidden="true"
                  animate={isActive ? { scale: 1.1 } : { scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-[hsl(var(--primary))]' : 'text-stone-500'}`} strokeWidth={isActive ? 2.5 : 2} />
                </motion.div>
                <span className={`text-xs font-medium transition-all duration-200 ${
                  isActive ? 'text-[hsl(var(--primary))]' : 'text-stone-500'
                }`}>
                  {item.label}
                </span>
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-xl"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.08 }}
                    style={{ background: 'linear-gradient(135deg, #3DA35D20, #4A90C420)' }}
                  />
                )}
              </button>
            )
          })}

          {/* 更多按钮 */}
          <button
            onClick={() => setShowMore(!showMore)}
            aria-label="更多功能"
            aria-expanded={showMore}
            aria-current={isMoreActive ? 'page' : undefined}
            className={`relative flex flex-col items-center justify-center min-w-[48px] min-h-[48px] gap-0.5 transition-all duration-200 touch-feedback ${
              isMoreActive ? 'text-[hsl(var(--primary))]' : 'text-stone-500'
            }`}
          >
            {isMoreActive && (
              <div className="absolute -top-px left-1/2 -translate-x-1/2 w-12 h-0.5 rounded-full bg-[hsl(var(--primary))]" />
            )}
            <motion.div
              aria-hidden="true"
              animate={isMoreActive ? { scale: 1.1 } : { scale: 1 }}
              transition={{ duration: 0.2 }}
            >
              <Menu className={`w-5 h-5 ${isMoreActive ? 'text-[hsl(var(--primary))]' : 'text-stone-500'}`} strokeWidth={isMoreActive ? 2.5 : 2} />
            </motion.div>
            <span className={`text-xs font-medium transition-all duration-200 ${
              isMoreActive ? 'text-[hsl(var(--primary))]' : 'text-stone-500'
            }`}>
              更多
            </span>
            {isMoreActive && (
              <motion.div
                className="absolute inset-0 rounded-xl"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.08 }}
                style={{ background: 'linear-gradient(135deg, #3DA35D20, #4A90C420)' }}
              />
            )}
          </button>
        </div>
      </nav>
    </>
  )
}
