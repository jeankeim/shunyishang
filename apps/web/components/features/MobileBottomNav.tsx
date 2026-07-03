'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

type TabId = 'chat' | 'wardrobe' | 'tryon' | 'profile' | 'diary' | 'fortune' | 'destiny' | 'membership' | 'community' | 'cultivation'

interface MobileBottomNavProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
}

// 主导航：高频功能，固定显示
const PRIMARY_ITEMS = [
  { id: 'chat' as const, icon: '✨', label: '推荐' },
  { id: 'wardrobe' as const, icon: '👔', label: '衣橱' },
  { id: 'tryon' as const, icon: '👗', label: '试衣' },
  { id: 'fortune' as const, icon: '🔮', label: '运势' },
]

// 次级功能：通过"更多"展开访问
const SECONDARY_ITEMS = [
  { id: 'diary' as const, icon: '📓', label: '日记' },
  { id: 'destiny' as const, icon: '☯️', label: '命理' },
  { id: 'community' as const, icon: '🏛️', label: '广场' },
  { id: 'cultivation' as const, icon: '🏔️', label: '修炼' },
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
                <div className="grid grid-cols-4 gap-2">
                  {SECONDARY_ITEMS.map((item) => {
                    const isActive = activeTab === item.id
                    return (
                      <button
                        key={item.id}
                        onClick={() => handleSecondaryClick(item.id)}
                        aria-label={`切换到${item.label}页面`}
                        className="flex flex-col items-center gap-2 py-3 px-1 rounded-xl active:bg-stone-100 transition-colors"
                      >
                        <span className={`text-2xl transition-transform ${isActive ? 'scale-110' : ''}`}>
                          {item.icon}
                        </span>
                        <span className={`text-xs font-medium ${isActive ? 'text-[#3DA35D]' : 'text-stone-600'}`}>
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
            return (
              <button
                key={item.id}
                onClick={() => handlePrimaryClick(item.id)}
                aria-label={`切换到${item.label}页面`}
                aria-current={isActive ? 'page' : undefined}
                className={`relative flex flex-col items-center justify-center min-w-[48px] min-h-[48px] gap-0.5 transition-all duration-200 touch-feedback ${
                  isActive ? 'text-[#3DA35D]' : 'text-stone-500'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="bottomNavIndicator"
                    className="absolute -top-px left-1/2 -translate-x-1/2 w-12 h-0.5 rounded-full bg-[#3DA35D]"
                    initial={false}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}
                <motion.span
                  className="text-xl"
                  aria-hidden="true"
                  animate={isActive ? { scale: 1.1 } : { scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  {item.icon}
                </motion.span>
                <span className={`text-xs font-medium transition-all duration-200 ${
                  isActive ? 'text-[#3DA35D]' : 'text-stone-500'
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
              isMoreActive ? 'text-[#3DA35D]' : 'text-stone-500'
            }`}
          >
            {isMoreActive && (
              <div className="absolute -top-px left-1/2 -translate-x-1/2 w-12 h-0.5 rounded-full bg-[#3DA35D]" />
            )}
            <motion.span
              className="text-xl"
              aria-hidden="true"
              animate={isMoreActive ? { scale: 1.1 } : { scale: 1 }}
              transition={{ duration: 0.2 }}
            >
              ☰
            </motion.span>
            <span className={`text-xs font-medium transition-all duration-200 ${
              isMoreActive ? 'text-[#3DA35D]' : 'text-stone-500'
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
