'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { FiveElementList } from './FiveElementList'
import { BaziCard } from './BaziCard'
import { BaziInputSection } from './BaziInputSection'
import { WeatherSceneSection } from './WeatherSceneSection'
import { useChatStore } from '@/store/chat'
import { useUserStore } from '@/store/user'

interface MobileControlPanelProps {
  onSceneChange: (sceneId: string, element: string, sceneLabel?: string) => void
  onWeatherChange: (weather: any) => void
}

export function MobileControlPanel({ onSceneChange, onWeatherChange }: MobileControlPanelProps) {
  const { radarData, setUserBazi } = useChatStore()
  const { user, isAuthenticated } = useUserStore()
  const [expanded, setExpanded] = useState(false)
  
  const hasBazi = isAuthenticated && user?.bazi

  // 场景选择后自动收起面板：避免展开层遮挡推荐输入框，让用户直接看到场景已带入
  const handleSceneChange = (sceneId: string, element: string, sceneLabel?: string) => {
    onSceneChange(sceneId, element, sceneLabel)
    if (sceneId) {
      setExpanded(false)
    }
  }
  
  return (
    <div className="md:hidden fixed bottom-16 left-0 right-0 z-[45] bg-white/95 backdrop-blur-md border-t border-[var(--brand-border)]/50 safe-bottom">
      {/* 展开/收起按钮 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-center gap-2 py-3 text-sm text-[var(--brand-subtle)] hover:bg-[var(--brand-surface)]/50 transition-colors touch-feedback"
      >
        <span>{expanded ? '收起设置' : '展开设置'}</span>
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
      </button>
      
      {/* 可展开内容 */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-4 max-h-[50vh] overflow-y-auto scrollbar-hide pb-4">
              {/* 八字区域 */}
              {hasBazi ? (
                <BaziCard 
                  onEdit={() => {
                    window.location.hash = '#profile'
                  }}
                />
              ) : (
                <div className="card-secondary p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 bg-gradient-to-br from-[var(--wuxing-wood)] to-[var(--wuxing-water)] rounded-full"></div>
                    <h3 className="font-semibold text-[var(--brand-heading)] text-sm">生辰八字</h3>
                  </div>
                  <BaziInputSection />
                </div>
              )}
              
              {/* 天气和场景 */}
              <div className="card-secondary p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 bg-gradient-to-br from-[var(--wuxing-water)] to-[var(--wuxing-wood)] rounded-full"></div>
                    <h3 className="font-semibold text-[var(--brand-heading)] text-sm">天地气象</h3>
                </div>
                <WeatherSceneSection 
                  onSceneChange={handleSceneChange}
                  onWeatherChange={onWeatherChange}
                />
              </div>
              
              {/* 五行列表 - 仅在没有八字时显示 */}
              {!hasBazi && (
                <div className="card-secondary p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 bg-gradient-to-br from-[var(--wuxing-wood)] to-[var(--wuxing-earth)] rounded-full"></div>
                    <h3 className="font-semibold text-[var(--brand-heading)] text-sm">五行生克</h3>
                  </div>
                  <FiveElementList
                    currentData={radarData.currentData}
                    suggestedData={radarData.suggestedData}
                    xiyongShen={radarData.xiyongShen}
                    pillars={radarData.pillars}
                    dayMaster={radarData.dayMaster}
                  />
                </div>
              )}
              
              {/* 提示信息 */}
              {hasBazi && (
                <div className="card-secondary p-3 bg-gradient-to-br from-[var(--brand-surface)]/80 to-[var(--brand-surface-active)]/60">
                  <p className="text-xs text-[var(--brand-subtle)] text-center leading-relaxed">
                    基于您的八字分析，已为您计算喜用神。
                    <br />
                    智能推荐将以此为依据。
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
