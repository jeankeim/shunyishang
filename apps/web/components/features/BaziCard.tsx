'use client'

import { motion } from 'framer-motion'
import { useUserStore } from '@/store/user'
import { Sparkles, Calendar, Clock, Edit3 } from 'lucide-react'

interface BaziCardProps {
  onEdit?: () => void
}

// 五行颜色映射
const elementColors: Record<string, { bg: string; text: string; border: string; light: string }> = {
  '木': { bg: 'bg-green-500', text: 'text-green-700', border: 'border-green-200', light: 'bg-green-50' },
  '火': { bg: 'bg-red-500', text: 'text-red-700', border: 'border-red-200', light: 'bg-red-50' },
  '土': { bg: 'bg-yellow-600', text: 'text-yellow-700', border: 'border-yellow-200', light: 'bg-yellow-50' },
  '金': { bg: 'bg-gray-400', text: 'text-gray-700', border: 'border-gray-200', light: 'bg-gray-50' },
  '水': { bg: 'bg-blue-500', text: 'text-blue-700', border: 'border-blue-200', light: 'bg-blue-50' },
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
      className="bg-gradient-to-br from-amber-50/80 to-yellow-50/60 rounded-2xl p-5 shadow-sm border border-amber-200/40"
    >
      {/* 标题 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-amber-400 to-orange-400 rounded-lg flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-stone-700 text-lg">我的八字</h2>
            <p className="text-xs text-stone-500">已为您自动分析</p>
          </div>
        </div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="flex items-center gap-1 px-3 py-1.5 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-100/50 rounded-lg transition-all"
          >
            <Edit3 className="h-3 w-3" />
            修改
          </button>
        )}
      </div>
      
      {/* 八字四柱 */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {pillars.map((pillar, idx) => (
          <div key={idx} className="text-center">
            <div className="text-xs text-stone-400 mb-1">{pillar.name}</div>
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
        <div className="bg-white/60 rounded-xl p-3 mb-3">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-3 w-3 text-amber-500" />
            <span className="text-xs font-medium text-stone-600">喜用神</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {xiyong.map((element: string, idx: number) => {
              const style = getElementStyle(element)
              return (
                <span
                  key={idx}
                  className={`px-3 py-1 rounded-full text-sm font-medium ${style.light} ${style.text} border ${style.border}`}
                >
                  {element}
                </span>
              )
            })}
          </div>
          <p className="text-xs text-stone-500 mt-2 flex items-center gap-1">
            <span className="w-1 h-1 bg-amber-400 rounded-full"></span>
            后续推荐将以此为依据
          </p>
        </div>
      )}
      
      {/* 忌用神 */}
      {avoidElements && avoidElements.length > 0 && (
        <div className="bg-stone-50/60 rounded-xl p-3">
          <div className="text-xs text-stone-500 mb-2">需避免</div>
          <div className="flex flex-wrap gap-2">
            {avoidElements.map((element: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 rounded-full text-sm text-stone-500 bg-stone-100 border border-stone-200"
              >
                {element}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* 出生信息 */}
      {(user.birth_date || user.birth_time) && (
        <div className="mt-3 pt-3 border-t border-amber-200/30 flex items-center gap-4 text-xs text-stone-400">
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
