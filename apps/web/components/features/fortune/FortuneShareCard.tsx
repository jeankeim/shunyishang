'use client'

import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { toPng } from 'html-to-image'

// 五行配色
const ELEMENT_COLORS: Record<string, string> = {
  '金': '#9E9E9E', '木': '#4CAF50', '水': '#2196F3',
  '火': '#FF6B6B', '土': '#D4A574',
}

// 维度配置
const DIMENSIONS = [
  { key: 'career', label: '事业', emoji: '💼' },
  { key: 'wealth', label: '财运', emoji: '💰' },
  { key: 'love', label: '桃花', emoji: '💕' },
  { key: 'health', label: '健康', emoji: '🌿' },
  { key: 'study', label: '学业', emoji: '📚' },
]

// 颜色名称到色值
const COLOR_MAP: Record<string, string> = {
  '红色': '#DC2626', '紫色': '#7C3AED', '粉色': '#EC4899',
  '橙色': '#EA580C', '黄色': '#CA8A04', '绿色': '#16A34A',
  '青色': '#0D9488', '蓝色': '#2563EB', '黑色': '#1C1917',
  '白色': '#F5F5F4', '灰色': '#9CA3AF', '银色': '#C0C0C0',
  '金色': '#D4A574', '棕色': '#92400E',
}

interface FortuneData {
  fortune_date: string
  scores: Record<string, number>
  overall_score: number
  lucky_colors?: string[]
  avoid_colors?: string[]
  outfit_suggestion?: string
  advice_text?: string
  day_ganzhi?: string
  day_element?: string
  day_master?: string
  fortune_level?: string
}

interface FortuneShareCardProps {
  fortune: FortuneData
  username?: string
}

export function FortuneShareCard({ fortune, username }: FortuneShareCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [generating, setGenerating] = useState(false)
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  const today = new Date(fortune.fortune_date)
  const dateStr = `${today.getFullYear()}年${today.getMonth() + 1}月${today.getDate()}日`
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  const weekday = `星期${weekdays[today.getDay()]}`

  const levelConfig: Record<string, { label: string; color: string }> = {
    great: { label: '宜搭配', color: '#10B981' },
    good: { label: '可搭配', color: '#3B82F6' },
    normal: { label: '随性搭', color: '#F59E0B' },
    weak: { label: '慎搭配', color: '#78716C' },
  }
  const level = levelConfig[fortune.fortune_level || 'normal'] || levelConfig.normal

  async function handleGenerateImage() {
    if (!cardRef.current) return
    setGenerating(true)
    try {
      const url = await toPng(cardRef.current, {
        pixelRatio: 2,
        backgroundColor: '#FEFDF8',
      })
      setImageUrl(url)
    } catch (e) {
      console.error('生成图片失败:', e)
    } finally {
      setGenerating(false)
    }
  }

  function handleDownload() {
    if (!imageUrl) return
    const link = document.createElement('a')
    link.download = `我的个人穿搭-运势卡片-${today.toISOString().slice(0, 10)}.png`
    link.href = imageUrl
    link.click()
  }

  async function handleShare() {
    if (!imageUrl) return
    // 尝试使用 Web Share API
    if (navigator.share) {
      try {
        const blob = await (await fetch(imageUrl)).blob()
        const file = new File([blob], 'fortune-card.png', { type: 'image/png' })
        await navigator.share({
          title: '今日五行运势',
          text: fortune.advice_text || '查看今日运势',
          files: [file],
        })
      } catch {
        // 分享被取消或失败，回退到下载
        handleDownload()
      }
    } else {
      handleDownload()
    }
  }

  return (
    <div className="space-y-4">
      {/* 卡片预览区 */}
      <div className="flex justify-center">
        <div
          ref={cardRef}
          className="w-[320px] rounded-3xl overflow-hidden shadow-lg"
          style={{
            background: 'linear-gradient(145deg, #FEFDF8 0%, #F8F5EC 30%, #F0EDE4 100%)',
            fontFamily: '"Noto Serif SC", "STSong", "Source Han Serif SC", serif',
          }}
        >
          {/* 顶部装饰 */}
          <div className="h-2 bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-400" />

          <div className="px-6 py-5">
            {/* 品牌标识 */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                  <span className="text-white text-xs font-bold">顺</span>
                </div>
                <span className="text-xs text-stone-500 tracking-wide">我的个人穿搭 · 五行穿搭</span>
              </div>
              <span className="text-[10px] text-stone-400">{dateStr}</span>
            </div>

            {/* 日期和运势等级 */}
            <div className="text-center mb-5">
              <h2 className="text-2xl font-bold text-stone-800 mb-1">今日运势</h2>
              <p className="text-sm text-stone-500">{dateStr} {weekday}</p>
              {fortune.day_ganzhi && (
                <p className="text-xs text-stone-400 mt-1">
                  {fortune.day_ganzhi}日 · 五行属{fortune.day_element}
                </p>
              )}
              <div className="mt-3 inline-flex items-center gap-2 px-4 py-1.5 rounded-full" style={{ backgroundColor: `${level.color}15` }}>
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: level.color }} />
                <span className="text-sm font-semibold" style={{ color: level.color }}>
                  {level.label} · {fortune.overall_score}分
                </span>
              </div>
            </div>

            {/* 五维度分数 */}
            <div className="grid grid-cols-5 gap-1.5 mb-5">
              {DIMENSIONS.map(dim => {
                const score = fortune.scores[dim.key] || 0
                const barColor = score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : '#9CA3AF'
                return (
                  <div key={dim.key} className="text-center">
                    <span className="text-base">{dim.emoji}</span>
                    <p className="text-[10px] text-stone-500 mt-0.5">{dim.label}</p>
                    <div className="mt-1 mx-auto w-4 h-16 bg-stone-100 rounded-full overflow-hidden relative flex flex-col-reverse">
                      <div
                        className="w-full rounded-full transition-all"
                        style={{ height: `${score}%`, backgroundColor: barColor }}
                      />
                    </div>
                    <p className="text-[10px] font-bold text-stone-700 mt-0.5">{score}</p>
                  </div>
                )
              })}
            </div>

            {/* 幸运色和忌讳色 */}
            {(fortune.lucky_colors?.length || fortune.avoid_colors?.length) && (
              <div className="flex items-center justify-center gap-4 mb-4">
                {fortune.lucky_colors && fortune.lucky_colors.length > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-stone-500">幸运色</span>
                    <div className="flex gap-1">
                      {fortune.lucky_colors.map((c, i) => (
                        <div
                          key={i}
                          className="w-5 h-5 rounded-full border border-white shadow-sm"
                          style={{ backgroundColor: COLOR_MAP[c] || '#ccc' }}
                        />
                      ))}
                    </div>
                  </div>
                )}
                {fortune.avoid_colors && fortune.avoid_colors.length > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-stone-500">忌讳</span>
                    <div className="flex gap-1">
                      {fortune.avoid_colors.map((c, i) => (
                        <div
                          key={i}
                          className="w-5 h-5 rounded-full border border-white shadow-sm opacity-40"
                          style={{ backgroundColor: COLOR_MAP[c] || '#ccc' }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 穿搭建议 */}
            {fortune.outfit_suggestion && (
              <div className="bg-white/60 rounded-xl p-3 mb-4 border border-stone-100">
                <p className="text-[10px] font-medium text-emerald-600 mb-1">👔 今日穿搭建议</p>
                <p className="text-xs text-stone-600 leading-relaxed">{fortune.outfit_suggestion}</p>
              </div>
            )}

            {/* 运势建议 */}
            {fortune.advice_text && (
              <div className="text-center mb-4">
                <p className="text-[11px] text-stone-500 leading-relaxed italic">
                  "{fortune.advice_text}"
                </p>
              </div>
            )}

            {/* 底部信息 */}
            <div className="border-t border-stone-200/60 pt-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center">
                  <span className="text-white text-[8px]">五</span>
                </div>
                <span className="text-[10px] text-stone-500">
                  @{username || '五行穿搭'}
                </span>
              </div>
              <p className="text-[9px] text-stone-400">扫码查看你的运势</p>
            </div>

            {/* 免责水印 */}
            <p className="text-center text-[8px] text-stone-400 mt-2 opacity-60">
              文化参考 · 仅供娱乐
            </p>
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3">
        <motion.button
          whileTap={{ scale: 0.98 }}
          onClick={handleGenerateImage}
          disabled={generating}
          className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-[#3DA35D] to-[#4A90C4] text-white text-sm font-medium shadow-sm disabled:opacity-60"
        >
          {generating ? '生成中...' : imageUrl ? '重新生成' : '生成分享图片'}
        </motion.button>
        {imageUrl && (
          <>
            <motion.button
              whileTap={{ scale: 0.98 }}
              onClick={handleDownload}
              className="px-4 py-2.5 rounded-xl border border-stone-200 text-sm text-stone-600 font-medium hover:bg-stone-50"
            >
              下载
            </motion.button>
            <motion.button
              whileTap={{ scale: 0.98 }}
              onClick={handleShare}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-purple-500 text-white text-sm font-medium shadow-sm"
            >
              分享
            </motion.button>
          </>
        )}
      </div>

      {/* 生成的图片预览 */}
      {imageUrl && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <img src={imageUrl} alt="运势分享卡片" className="max-w-[240px] mx-auto rounded-xl shadow-md" />
          <p className="text-[10px] text-stone-400 mt-2">长按图片或右键保存</p>
        </motion.div>
      )}
    </div>
  )
}
