'use client'

/**
 * 场景急救搭配
 *
 * 临时要出门、不知道穿什么时，选一个场景即从自有衣橱秒出成套方案。
 * 后端在通用打分之上叠加场景加成（纯规则、不调 LLM），因此响应是即时的；
 * 场景表与「常用场景」共用同一份常量与使用频率排序。
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Loader2, Zap, Check, Sparkles } from 'lucide-react'
import { postSceneRescue, type DailyOutfitItem, type SceneRescue } from '@/lib/api'
import { hasTodayDiary, logOutfitAsDiary, loggedFlagKey } from '@/lib/outfit-diary'
import { getWuxingConfig } from '@/lib/wuxing-config'
import { requestChatInputAutofill } from '@/lib/chatAutofill'
import { getSortedScenes, recordSceneUsage, type SceneOption } from '@/lib/scene-config'
import { toast } from '@/components/ui/Toast'
import { ItemDetailModal } from './ItemDetailModal'
import { OutfitPiecesView } from './OutfitPiecesView'

interface SceneRescueModalProps {
  open: boolean
  onClose: () => void
  /** 前端定位城市（与首页天气保持一致） */
  city?: string
}

export function SceneRescueModal({ open, onClose, city }: SceneRescueModalProps) {
  const [scenes, setScenes] = useState<SceneOption[]>([])
  const [selected, setSelected] = useState<string>('')
  const [result, setResult] = useState<SceneRescue | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [logging, setLogging] = useState(false)
  const [logged, setLogged] = useState(false)
  const [selectedItem, setSelectedItem] = useState<DailyOutfitItem | null>(null)

  // 打开时按当前时段与使用频率排场景，并向服务端核对今日是否已记日记
  useEffect(() => {
    if (!open) return
    setScenes(getSortedScenes())
    setLogged(localStorage.getItem(loggedFlagKey()) === '1')
    let cancelled = false
    hasTodayDiary().then((exists) => {
      if (cancelled || exists === null) return
      setLogged(exists)
    })
    return () => {
      cancelled = true
    }
  }, [open])

  const requestScene = useCallback(
    async (scene: string) => {
      setSelected(scene)
      setLoading(true)
      setFailed(false)
      try {
        const res = await postSceneRescue(scene, city || undefined)
        if (res) {
          setResult(res)
        } else {
          setResult(null)
          setFailed(true)
        }
      } catch {
        setResult(null)
        setFailed(true)
      } finally {
        setLoading(false)
      }
    },
    [city]
  )

  /** 选场景：记录使用频率并立即出方案 */
  function handlePick(scene: SceneOption) {
    recordSceneUsage(scene.id)
    setScenes(getSortedScenes())
    requestScene(scene.id)
  }

  /** 「就穿这套记一笔」：与今日穿搭卡共用一键日记链路 */
  async function handleLog() {
    const items = result?.outfit_items || []
    if (!items.length || logging) return
    if (logged) {
      toast.info('今日已记入穿搭日记，去日记里看看或继续补充')
      window.location.hash = '#diary'
      onClose()
      return
    }
    setLogging(true)
    try {
      const res = await logOutfitAsDiary(items.map((i) => ({ id: i.id, category: i.category })))
      if (res.ok) {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.success('已记入今日穿搭日记')
      } else if (res.reason === 'exists') {
        localStorage.setItem(loggedFlagKey(), '1')
        setLogged(true)
        toast.info('今日已有穿搭日记，去日记里看看吧')
      } else {
        toast.error(res.message || '记录失败，请稍后重试')
        return
      }
      window.location.hash = '#diary'
      onClose()
    } finally {
      setLogging(false)
    }
  }

  if (!open) return null

  const activeScene = scenes.find((s) => s.id === selected)

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="场景急救搭配">
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94 }}
        transition={{ duration: 0.22 }}
        className="relative w-full max-w-sm bg-white rounded-2xl shadow-xl p-5 max-h-[85vh] overflow-y-auto"
      >
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--wuxing-wood)]/20 to-[var(--wuxing-water)]/20 flex items-center justify-center">
              <Zap className="w-4 h-4 text-[var(--wuxing-wood)]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[var(--brand-heading)]">场景急救搭配</h3>
              <p className="text-[10px] text-[var(--brand-subtle)]">选个场合，衣橱里马上给你一套</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-[var(--brand-surface)] transition-colors"
            aria-label="关闭"
          >
            <X className="w-4 h-4 text-[var(--brand-subtle)]" />
          </button>
        </div>

        {/* 场景宫格 */}
        <div className="grid grid-cols-3 gap-2">
          {scenes.map((scene) => {
            const Icon = scene.icon
            const isActive = selected === scene.id
            return (
              <button
                key={scene.id}
                onClick={() => handlePick(scene)}
                aria-pressed={isActive}
                className={`flex flex-col items-center gap-1 py-2.5 rounded-xl border transition-colors ${
                  isActive
                    ? 'border-[var(--wuxing-wood)]/50 bg-[var(--wuxing-wood)]/5'
                    : 'border-[var(--brand-border)]/60 hover:bg-[var(--brand-surface-active)]/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-[var(--wuxing-wood)]' : 'text-[var(--brand-subtle)]'}`} />
                <span className="text-[11px] font-medium text-[var(--brand-heading)] leading-none">{scene.label}</span>
                <span className="text-[9px] text-[var(--brand-subtle)] leading-none">
                  {scene.element} · {scene.desc}
                </span>
              </button>
            )
          })}
        </div>

        {/* 方案区 */}
        {!selected && (
          <p className="mt-4 text-xs text-[var(--brand-subtle)] text-center py-4">
            上面选一个场景，立刻从你自己的衣橱里配好一套
          </p>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-2 py-8">
            <Loader2 className="w-4 h-4 animate-spin text-[var(--brand-subtle)]" />
            <span className="text-xs text-[var(--brand-subtle)]">正在按场景重排你的衣橱...</span>
          </div>
        )}

        {!loading && failed && (
          <div className="mt-4 flex flex-col items-center gap-2 py-4">
            <p className="text-xs text-[var(--brand-subtle)]">急救方案取不到了，稍后再试</p>
            <button
              onClick={() => requestScene(selected)}
              className="text-xs px-3 py-1.5 rounded-lg bg-[var(--brand-surface)] text-[var(--brand-body)] hover:bg-[var(--brand-surface-active)] transition-colors"
            >
              重试
            </button>
          </div>
        )}

        {!loading && result && (
          <AnimatePresence mode="wait">
            <motion.div
              key={`${result.scene}-${result.date}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-4 space-y-3"
            >
              {/* 场景要点 */}
              <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-[var(--brand-surface)]/60 border border-[var(--brand-border)]/60">
                <Sparkles className="w-3.5 h-3.5 text-[var(--wuxing-wood)] flex-shrink-0 mt-0.5" />
                <p className="text-xs text-[var(--brand-body)] leading-relaxed flex-1">{result.scene_advice}</p>
              </div>

              <div className="flex items-center justify-between">
                <p className="text-[11px] text-[var(--brand-subtle)]">
                  {result.weather_summary?.city} {result.weather_summary?.temperature}°C
                  {activeScene ? ` · ${activeScene.label}` : ''}
                </p>
                <div className="flex items-center gap-1.5">
                  {result.scene_elements.primary.map((el) => (
                    <span
                      key={el}
                      className="text-[10px] px-1.5 py-0.5 rounded-full font-medium text-white"
                      style={{ backgroundColor: getWuxingConfig(el).color }}
                    >
                      {el}
                    </span>
                  ))}
                  {result.match_score > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 font-medium">
                      {result.match_score}分
                    </span>
                  )}
                </div>
              </div>

              {result.outfit_items.length ? (
                <OutfitPiecesView
                  items={result.outfit_items}
                  missing={result.completeness?.missing ?? []}
                  luckyElement={result.fortune_summary?.lucky_elements?.[0]}
                  onSelectItem={setSelectedItem}
                  onFillMissing={(category, luckyElement) => {
                    requestChatInputAutofill(`推荐一件${luckyElement ? luckyElement + '属性的' : ''}${category}`)
                    window.location.hash = '#chat'
                    onClose()
                  }}
                  thumbSize="sm"
                />
              ) : (
                <p className="text-xs text-[var(--brand-subtle)] text-center py-3">
                  {result.reasoning || '衣橱里暂时没有合适的单品'}
                </p>
              )}

              {/* 就穿这套记一笔 */}
              {result.outfit_items.length > 0 && (
                <motion.button
                  whileTap={{ scale: 0.98 }}
                  onClick={handleLog}
                  disabled={logging}
                  className={`w-full py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                    logged
                      ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100'
                      : 'bg-gradient-to-r from-[var(--wuxing-wood)] to-[var(--wuxing-water)] text-white shadow-sm hover:opacity-95 disabled:opacity-60'
                  }`}
                >
                  {logged ? (
                    <>
                      <Check className="w-4 h-4" /> 今日已记入 · 去日记
                    </>
                  ) : logging ? (
                    '记录中...'
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" /> 就穿这套记一笔
                    </>
                  )}
                </motion.button>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </motion.div>

      {/* 单品详情（与今日穿搭卡共用弹窗） */}
      {selectedItem && (
        <ItemDetailModal
          item={{
            item_code: String(selectedItem.id),
            name: selectedItem.name,
            category: selectedItem.category || '',
            primary_element: selectedItem.primary_element || '',
            secondary_element: selectedItem.secondary_element,
            image_url: selectedItem.image_url,
            final_score: selectedItem.match_score,
          }}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  )
}
