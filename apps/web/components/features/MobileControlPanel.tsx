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
  onSceneChange: (sceneId: string, element: string) => void
  onWeatherChange: (weather: any) => void
}

export function MobileControlPanel({ onSceneChange, onWeatherChange }: MobileControlPanelProps) {
  const { radarData, setUserBazi } = useChatStore()
  const { user, isAuthenticated } = useUserStore()
  const [expanded, setExpanded] = useState(false)
  
  const hasBazi = isAuthenticated && user?.bazi
  
  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-[#E8F0EB]/50 safe-bottom">
      {/* 展开/收起按钮 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-center gap-2 py-3 text-sm text-[#5A7A66] hover:bg-[#F0F7F4]/50 transition-colors touch-feedback"
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
            <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto scrollbar-hide pb-20">
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
                    <div className="w-2 h-2 bg-gradient-to-br from-[#3DA35D] to-[#4A90C4] rounded-full"></div>
                    <h3 className="font-semibold text-[#2D4A38] text-sm">生辰八字</h3>
                  </div>
                  <BaziInputSection />
                </div>
              )}
              
              {/* 天气和场景 */}
              <div className="card-secondary p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 bg-gradient-to-br from-[#4A90C4] to-[#3DA35D] rounded-full"></div>
                  <h3 className="font-semibold text-[#2D4A38] text-sm">天地气象</h3>
                </div>
                <WeatherSceneSection 
                  onSceneChange={onSceneChange}
                  onWeatherChange={onWeatherChange}
                />
              </div>
              
              {/* 五行列表 - 仅在没有八字时显示 */}
              {!hasBazi && (
                <div className="card-secondary p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-2 h-2 bg-gradient-to-br from-[#3DA35D] to-[#B89B5E] rounded-full"></div>
                    <h3 className="font-semibold text-[#2D4A38] text-sm">五行生克</h3>
                  </div>
                  <FiveElementList
                    currentData={radarData.currentData}
                    suggestedData={radarData.suggestedData}
                    xiyongShen={radarData.xiyongShen}
                  />
                </div>
              )}
              
              {/* 提示信息 */}
              {hasBazi && (
                <div className="card-secondary p-3 bg-gradient-to-br from-[#F8FAF9]/80 to-[#F5F9F7]/60">
                  <p className="text-xs text-[#5A7A66] text-center leading-relaxed">
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
