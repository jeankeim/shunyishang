'use client'

import { motion } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { Sparkles, Calendar, Clock, Edit3 } from 'lucide-react'

interface BaziCardProps {
  onEdit?: () => void
}

// 五行颜色映射 - 春分优化版 (WCAG 4.5:1+)
const elementColors: Record<string, { bg: string; text: string; border: string; light: string }> = {
  '木': { bg: 'bg-[#3DA35D]', text: 'text-[#2D7A45]', border: 'border-[#3DA35D]/30', light: 'bg-[#F0F9F4]' },
  '火': { bg: 'bg-[#D4656B]', text: 'text-[#B5494F]', border: 'border-[#D4656B]/30', light: 'bg-[#FDF2F2]' },
  '土': { bg: 'bg-[#B89B5E]', text: 'text-[#9A7E47]', border: 'border-[#B89B5E]/30', light: 'bg-[#F9F5EC]' },
  '金': { bg: 'bg-[#8A9BA8]', text: 'text-[#6B7F8C]', border: 'border-[#8A9BA8]/30', light: 'bg-[#F5F7F9]' },
  '水': { bg: 'bg-[#4A90C4]', text: 'text-[#3570A0]', border: 'border-[#4A90C4]/30', light: 'bg-[#F0F7FA]' },
}

// 天干五行映射
const ganElement: Record<string, string> = {
  '甲': '木', '乙': '木',
  '丙': '火', '丁': '火',
  '戊': '土', '己': '土',
  '庚': '金', '辛': '金',
  '壬': '水', '癸': '水',
}

// 地支五行映射
const zhiElement: Record<string, string> = {
  '子': '水', '丑': '土',
  '寅': '木', '卯': '木',
  '辰': '土', '巳': '火',
  '午': '火', '未': '土',
  '申': '金', '酉': '金',
  '戌': '土', '亥': '水',
}

export function BaziCard({ onEdit }: BaziCardProps) {
  const { user } = useUserStore()
  
  if (!user?.bazi) return null
  
  const bazi = typeof user.bazi === 'string' ? JSON.parse(user.bazi) : user.bazi
  
  // 从 bazi.suggested_elements 或 user.xiyong_elements 获取喜用神
  const xiyong = bazi.suggested_elements || user.xiyong_elements || []
  const avoidElements = bazi.avoid_elements || []
  
  // 解析八字四柱 - 后端返回格式: pillars: {year: "甲子", month: "乙丑", ...}
  const pillarsData = bazi.pillars || {}
  const pillars = [
    { name: '年柱', gan: pillarsData.year?.[0] || '', zhi: pillarsData.year?.[1] || '' },
    { name: '月柱', gan: pillarsData.month?.[0] || '', zhi: pillarsData.month?.[1] || '' },
    { name: '日柱', gan: pillarsData.day?.[0] || '', zhi: pillarsData.day?.[1] || '' },
    { name: '时柱', gan: pillarsData.hour?.[0] || '', zhi: pillarsData.hour?.[1] || '' },
  ]
  
  // 获取天干地支的五行颜色
  const getGanColor = (gan: string) => elementColors[ganElement[gan]]?.bg || 'bg-gray-300'
  const getZhiColor = (zhi: string) => elementColors[zhiElement[zhi]]?.bg || 'bg-gray-300'
  
  // 获取喜用神颜色样式
  const getElementStyle = (element: string) => elementColors[element] || elementColors['木']
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-[#F8FAF9] to-[#F5F9F7] rounded-xl p-5 shadow-sm border border-[#E8F0EB]/60"
    >
      {/* 标题 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <motion.div 
            whileHover={{ scale: 1.05, rotate: 5 }}
            className="w-8 h-8 bg-gradient-to-br from-[#3DA35D] to-[#4A90C4] rounded-lg flex items-center justify-center shadow-sm"
          >
            <Sparkles className="h-4 w-4 text-white" />
          </motion.div>
          <div>
            <h2 className="font-semibold text-[#2D4A38] text-base font-serif">我的八字</h2>
            <p className="text-xs text-[#6B7F72]">已为您自动分析</p>
          </div>
        </div>
        {onEdit && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onEdit}
            className="flex items-center gap-1 px-3 py-1.5 text-xs text-[#3DA35D] hover:text-[#2D7A45] hover:bg-[#F0F7F4] rounded-lg transition-all duration-200"
          >
            <Edit3 className="h-3 w-3" />
            修改
          </motion.button>
        )}
      </div>
      
      {/* 八字四柱 */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {pillars.map((pillar, idx) => (
          <div key={idx} className="text-center">
            <div className="text-xs text-[#6B7F72] font-medium mb-1">{pillar.name}</div>
            <div className="space-y-1">
              <div className={`w-9 h-9 mx-auto rounded-lg ${getGanColor(pillar.gan)} text-white flex items-center justify-center font-bold text-sm shadow-sm`}>
                {pillar.gan}
              </div>
              <div className={`w-9 h-9 mx-auto rounded-lg ${getZhiColor(pillar.zhi)} text-white flex items-center justify-center font-bold text-sm shadow-sm`}>
                {pillar.zhi}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* 喜用神 */}
      {xiyong && xiyong.length > 0 && (
        <motion.div 
          whileHover={{ scale: 1.01 }}
          className="bg-white/80 rounded-xl p-3 mb-3 border border-[#E8F0EB]/40"
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-3 w-3 text-[#B89B5E]" />
            <span className="text-xs font-medium text-[#4A5F52]">喜用神</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {xiyong.map((element: string, idx: number) => {
              const style = getElementStyle(element)
              return (
                <motion.span
                  key={idx}
                  whileHover={{ scale: 1.05 }}
                  className={`px-3 py-1 rounded-full text-sm font-medium ${style.light} ${style.text} border ${style.border} cursor-default`}
                >
                  {element}
                </motion.span>
              )
            })}
          </div>
          <p className="text-xs text-[#6B7F72] mt-2 flex items-center gap-1">
            <span className="w-1 h-1 bg-[#B89B5E] rounded-full"></span>
            后续推荐将以此为依据
          </p>
        </motion.div>
      )}
      
      {/* 忌用神 */}
      {avoidElements && avoidElements.length > 0 && (
        <motion.div 
          whileHover={{ scale: 1.01 }}
          className="bg-[#F5F7F9]/60 rounded-xl p-3 border border-[#E8F0EB]/40"
        >
          <div className="text-xs text-[#6B7F72] mb-2 font-medium">需避免</div>
          <div className="flex flex-wrap gap-2">
            {avoidElements.map((element: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 rounded-full text-sm text-[#6B7F8C] bg-[#F0F2F5] border border-[#D0D8E0]"
              >
                {element}
              </span>
            ))}
          </div>
        </motion.div>
      )}
      
      {/* 出生信息 */}
      {(user.birth_date || user.birth_time) && (
        <div className="mt-3 pt-3 border-t border-[#E8F0EB]/40 flex items-center gap-4 text-xs text-[#8A9F92]">
          {user.birth_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {user.birth_date}
            </span>
          )}
          {user.birth_time && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {user.birth_time}
            </span>
          )}
        </div>
      )}
    </motion.div>
  )
}
